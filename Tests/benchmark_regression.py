from __future__ import annotations
import os
import sys

# Windows may start Python with a legacy code page such as cp1251.
# Reconfigure before any test can print Unicode progress bars/checkmarks.
os.environ['PYTHONUTF8']='1'
os.environ['PYTHONIOENCODING']='utf-8'
for _stream_name in ('stdout','stderr'):
    _stream=getattr(sys,_stream_name,None)
    if _stream is not None and hasattr(_stream,'reconfigure'):
        try:
            _stream.reconfigure(encoding='utf-8',errors='replace')
        except Exception:
            pass

import ast
import base64
import csv
import hashlib
import importlib.util
import json
import io
import contextlib
import math
import urllib.error
import re
import tempfile
import shutil
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CLIENT=ROOT/'bull_client_v0.29.0.1.py'
SCORER_V3_FIXTURE=ROOT/'Tests'/'Fixtures'/'benchmark_scorer_v3.json'
RU_LANGUAGE_STRESS_V176_FIXTURE=ROOT/'Tests'/'Fixtures'/'ru_language_stress_sanitized_v3.json'

spec=importlib.util.spec_from_file_location('bull_v024_core',CLIENT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
# Most legacy behavior contracts assert the original Russian copy. English UI
# coverage lives in Tests/ux_regression.py and opts in explicitly.
mod.set_language('ru')

# Legacy assertions intentionally receive an explicit reference catalog. The
# application itself must never discover these bundled source directories.
# Individual tests can still replace the factory with an empty/custom registry.
PRODUCTION_LOAD_BENCHMARKS=mod.load_benchmarks
PRODUCTION_PACK_REGISTRY=mod.benchmark_pack_registry
def reference_registry(built=None):
    return mod.PackRegistry([ROOT/'BenchmarkPacks'],[],mod.benchmark_registry_policy())
def reference_benchmarks():
    registered,_=mod._registry_benchmarks()
    for name,item in mod.load_user_benchmarks().items():
        if name in registered:
            raise mod.PackValidationError('USER_CASE_CONFLICT','user task conflicts with reference fixture: '+name)
        registered[name]=item
    return registered
mod.benchmark_pack_registry=reference_registry
mod.load_benchmarks=reference_benchmarks
mod.benchmark_pack_selection_menu=lambda **kwargs:True

passed=[]
STARTUP_CHECK_TOTAL=668
print('BULL_STARTUP_TOTAL\t'+str(STARTUP_CHECK_TOTAL),flush=True)

def test(name,fn):
    # The startup splash reads this explicit, line-buffered marker from the
    # offline child process. It is emitted before the check, never inferred
    # from a completed result or an assumed test count.
    print('BULL_STARTUP_TEST\t'+name,flush=True)
    fn(); passed.append(name); print('BULL_STARTUP_COMPLETE\t'+str(len(passed)),flush=True); print('OK  '+name)


def startup_suite(name):
    """Expose an imported contract suite before it begins running."""
    print('BULL_STARTUP_TEST\t'+str(name),flush=True)


def startup_suite_complete():
    print('BULL_STARTUP_COMPLETE\t'+str(len(passed)),flush=True)

def eq(a,b,msg=''):
    assert a==b, msg or f'{a!r} != {b!r}'

def close(a,b,tol=1e-9):
    assert a is not None and abs(float(a)-float(b))<=tol,(a,b)


def test_ast():
    tree=ast.parse(CLIENT.read_text(encoding='utf-8'))
    names=[x.name for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))]
    dup=[k for k,v in Counter(names).items() if v>1]
    assert not dup,dup


def retention_payload(correct=True,extra_cohort=False):
    if correct:
        obj={
            'technical_issue':'dt_accessor_on_object',
            'date_dtype_strategy':'pandas_datetime_like',
            'd7_rule':'exact_calendar_day_plus_7',
            'user_grain':'one_row_per_user',
            'no_activity_in_denominator':True,
            'registration_rule':'earliest',
            'cohorts':[
                {'reg_date':'2026-01-01','users_registered':4,'users_retained_d7':2,'retention_d7':0.5},
                {'reg_date':'2026-01-02','users_registered':3,'users_retained_d7':2,'retention_d7':0.666667},
            ],
        }
    else:
        obj={
            'technical_issue':'none','date_dtype_strategy':'other','d7_rule':'day7_or_later',
            'user_grain':'activity_event_rows','no_activity_in_denominator':False,'registration_rule':'latest',
            'cohorts':[
                {'reg_date':'2026-01-01','users_registered':9,'users_retained_d7':9,'retention_d7':1.0},
                {'reg_date':'2026-01-02','users_registered':7,'users_retained_d7':7,'retention_d7':1.0},
            ],
        }
    if extra_cohort:
        obj['cohorts'].append({
            'reg_date':'2026-01-03','users_registered':999,
            'users_retained_d7':999,'retention_d7':1.0
        })
    return obj


CORRECT_RETENTION_CODE=r"""```python
import pandas as pd

def calculate_retention_d7(events) -> pd.DataFrame:
    regs = (
        events.loc[events["event_name"].eq("registration"), ["user_id","event_time"]]
        .groupby("user_id", as_index=False)["event_time"].min()
        .rename(columns={"event_time":"reg_time"})
    )
    regs["reg_date"] = regs["reg_time"].dt.normalize()

    acts = events.loc[events["event_name"].eq("activity"), ["user_id","event_time"]].copy()
    acts["activity_date"] = acts["event_time"].dt.normalize()

    df = regs.merge(acts[["user_id","activity_date"]], on="user_id", how="left")
    df["is_d7"] = df["activity_date"].eq(df["reg_date"] + pd.Timedelta(days=7))

    user = (
        df.groupby(["reg_date","user_id"], as_index=False)
        .agg(retained_d7=("is_d7","any"))
    )
    result = (
        user.groupby("reg_date", as_index=False)
        .agg(
            users_registered=("user_id","size"),
            users_retained_d7=("retained_d7","sum"),
        )
    )
    result["retention_d7"] = result["users_retained_d7"] / result["users_registered"]
    return result
```"""

WRONG_RETENTION_CODE=r"""```python
import pandas as pd

def calculate_retention_d7(events) -> pd.DataFrame:
    return pd.DataFrame()
```"""


def retention_answer(correct=True,code_correct=None,extra_cohort=False,prefix=''):
    if code_correct is None:
        code_correct=correct
    code=CORRECT_RETENTION_CODE if code_correct else WRONG_RETENTION_CODE
    return (
        prefix+code+'\nBENCHMARK_RESULT\n'
        +json.dumps(retention_payload(correct,extra_cohort),ensure_ascii=False)
    )


def test_scorer():
    item=mod.builtin_benchmarks()['retention_d7']

    good=mod.benchmark_score('retention_d7',item,retention_answer(True,True))
    eq(good['value'],1.0)
    assert good['code_result_valid'] is True
    eq(good['code_execution']['row_count'],2)

    # Critical regression: correct self-reported JSON cannot hide wrong Python.
    dishonest=mod.benchmark_score('retention_d7',item,retention_answer(True,False))
    assert dishonest['value']<=0.50,dishonest
    assert dishonest['cap_applied']=='code_result_not_verified_max_50pct'
    assert dishonest['code_result_valid'] is False

    bad=mod.benchmark_score('retention_d7',item,retention_answer(False,False))
    assert bad['value']<0.2,bad

    extra=mod.benchmark_score(
        'retention_d7',item,retention_answer(True,True,extra_cohort=True)
    )
    assert extra['value']<1.0,extra

    long_prefix=('слово '*700)+'\n'
    long_answer=mod.benchmark_score(
        'retention_d7',item,retention_answer(True,True,prefix=long_prefix)
    )
    assert long_answer['value']<1.0
    assert long_answer['word_count']>650

    # Implementation independence remains: scorer verifies result, not .normalize() itself.
    assert dict((x['name'],x['ok']) for x in good['checks'])['valid calendar date representation'] is True


def simpson_v3_payload():
    return {
        'a_total':0.14,'b_total':0.45,
        'mobile_a':0.10,'mobile_b':0.09,
        'desktop_a':0.50,'desktop_b':0.49,
        'segment_point_winner':'A',
        'aggregate_winner':'B',
        'product_decision':'inconclusive',
        'phenomenon':'simpson_paradox',
        'should_check_randomization_balance':True,
        'observed_balance_ok':False,
        'needs_significance_check':True,
    }


def test_terminal_json():
    item=mod.builtin_benchmarks()['simpson']
    ans='Краткий анализ.\nBENCHMARK_RESULT\n'+json.dumps(
        simpson_v3_payload(),ensure_ascii=False
    )+'\nextra'
    score=mod.benchmark_score('simpson',item,ans)
    eq(score['parse_error'],'trailing_text_after_json')
    assert score['value']<1.0


def test_seed_modes():
    eq([mod.benchmark_seed(i,'fixed') for i in (1,2,3)],[42,42,42])
    eq([mod.benchmark_seed(i,'sweep') for i in (1,2,3)],[42,43,44])
    eq(mod.parse_bench_options(['3','client','sweep']),(3,'client','sweep'))


def test_gpu_parser():
    x=mod.GpuSampler.parse_line('10308, 12288, 62, 67, 119.2')
    eq(x['vram_used_mib'],10308.0); eq(x['gpu_util'],62.0); eq(x['gpu_power_w'],119.2)


def test_native_and_client_pipeline():
    class Sampler:
        def start(self):return self
        def stop(self):return {'samples':2,'vram_peak_mib':1000,'gpu_util_avg':70}
    old_sampler,old_stream,old_rt,old_digest=mod.GpuSampler,mod.stream_chat,mod._runtime_telemetry,mod.model_digest
    mod.GpuSampler=Sampler
    mod._runtime_telemetry=lambda model:{'gpu_offload_pct':50,'context_length':8192}
    mod.model_digest=lambda model,catalog=None:'digest'
    mod.NUM_CTX=8192;mod.NUM_THREAD=12
    cfg={'model':'x','think':True,'think_value':True,'num_predict':3200,'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42}
    item=mod.builtin_benchmarks()['retention_d7']
    calls=[]
    def native_stream(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,tools=None,response_format=None,silent=False,progress=None):
        calls.append((think_override,predict_override))
        return '', 'reasoning', {'done_reason':'length','eval_count':predict_override,'eval_duration':10_000_000_000,'prompt_eval_count':100,'prompt_eval_duration':1_000_000_000}
    mod.stream_chat=native_stream
    r=mod.benchmark_record('retention_d7',item,cfg,True,1,1,bench_mode='native',catalog={'x':{'digest':'digest'}})
    eq(calls,[(True,5000)])
    assert not r['recovery']['used'] and not r['final']['completed']

    calls=[]
    def client_stream(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,tools=None,response_format=None,silent=False,progress=None):
        calls.append((think_override,predict_override))
        if think_override is True:
            return '', 'reasoning', {'done_reason':'length','eval_count':5000,'eval_duration':10_000_000_000,'prompt_eval_count':100,'prompt_eval_duration':1_000_000_000}
        return retention_answer(True),'',{'done_reason':'stop','eval_count':900,'eval_duration':9_000_000_000,'prompt_eval_count':500,'prompt_eval_duration':1_000_000_000}
    mod.stream_chat=client_stream
    r=mod.benchmark_record('retention_d7',item,cfg,True,1,1,bench_mode='client',catalog={'x':{'digest':'digest'}})
    eq(len(calls),2)
    eq(calls[1][0],False)
    assert r['recovery']['used'] and r['recovery']['completed'] and r['final']['completed']
    eq(r['score']['final']['value'],1.0)
    mod.GpuSampler,mod.stream_chat,mod._runtime_telemetry,mod.model_digest=old_sampler,old_stream,old_rt,old_digest


def test_nested_json_csv():
    root=Path(tempfile.mkdtemp()); old_dir=mod.benchmark_dir; mod.benchmark_dir=lambda create=True:root
    rec={'record_schema_version':5,'execution_status':'ok','completion_status':'completed','identity':{'benchmark':'x','model':'m','model_digest':'abc'},'config':{'seed':42},'primary':{'eval_rate':12.3,'answer':'a\nb','completed':True},'recovery':{'used':False},'final':{'answer':'done','completed':True,'pipeline_wall_seconds':2},'score':{'native':{'value':1.0},'final':{'value':1.0}},'telemetry':{'gpu':{'samples':2},'runtime':{}}}
    jp,cp=mod.save_benchmark_results('x',[rec])
    eq(json.loads(jp.read_text(encoding='utf-8'))[0]['identity']['model_digest'],'abc')
    with cp.open(encoding='utf-8-sig',newline='') as f: row=next(csv.DictReader(f))
    eq(row['identity.model'],'m'); eq(row['primary.answer'],'a\nb')
    mod.benchmark_dir=old_dir


def test_checkpoint_resume():
    root=Path(tempfile.mkdtemp()); old_dir=mod.benchmark_dir; mod.benchmark_dir=lambda create=True:root
    old_set,old_unload,old_norm,old_make,old_cat,old_digest,old_prof,old_rec=(mod.set_active_model,mod.unload_model,mod.normalize_think_value,mod.make_cfg,mod.model_catalog,mod.model_digest,mod.model_profile,mod.benchmark_record)
    current=['m1']; mod.set_active_model=lambda name:(current.__setitem__(0,name) or name); mod.unload_model=lambda name:True
    mod.normalize_think_value=lambda name,v:(v,None)
    mod.make_cfg=lambda mode,v:{'model':current[0],'think':True,'think_value':v,'num_predict':3200,'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42}
    catalog={'m1':{'name':'m1','digest':'d1'},'m2':{'name':'m2','digest':'d2'}}; mod.model_catalog=lambda:catalog; mod.model_digest=lambda name,catalog=None:(catalog or catalog).get(name,{}).get('digest','')
    mod.model_profile=lambda name:{'ctx':8192,'threads':12,'think':{'num_predict':3200,'temperature':1,'top_p':.95,'top_k':20,'min_p':0,'seed':42},'fast':{'num_predict':512,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42}}
    calls={}
    def fake_record(name,item,cfg,tv,ri,total,**kw):
        key=(name,cfg['model'],ri); calls[key]=calls.get(key,0)+1
        if key==('simpson','m1',1) and calls[key]==1:raise RuntimeError('transient')
        return {'record_schema_version':5,'execution_status':'ok','completion_status':'completed','identity':{'benchmark':name,'model':cfg['model'],'run':ri,'attempt':kw.get('attempt',1)},'config':{'seed':cfg['seed']},'primary':{'completed':True,'eval_rate':10},'recovery':{'used':False},'final':{'completed':True,'pipeline_wall_seconds':1},'score':{'native':{'value':1},'final':{'value':1}},'telemetry':{'runtime':{},'gpu':{}}}
    mod.benchmark_record=fake_record
    spec=mod.make_benchmark_spec(['simpson'],['m1','m2'],1,True,'native','fixed','test',catalog=catalog)
    path,checkpoint=mod.new_checkpoint(spec)
    mod.execute_benchmark_checkpoint(path,checkpoint,catalog)
    eq(checkpoint['suite_status'],'execution_complete_with_errors')
    _,checkpoint=mod.load_checkpoint(path)
    mod.execute_benchmark_checkpoint(path,checkpoint,catalog)
    eq(checkpoint['suite_status'],'execution_complete')
    eq(calls[('simpson','m1',1)],2); eq(calls[('simpson','m2',1)],1)
    mod.benchmark_dir=old_dir
    mod.set_active_model,mod.unload_model,mod.normalize_think_value,mod.make_cfg,mod.model_catalog,mod.model_digest,mod.model_profile,mod.benchmark_record=old_set,old_unload,old_norm,old_make,old_cat,old_digest,old_prof,old_rec


def _checkpoint_recovery_harness(root):
    old={
        'benchmark_dir':mod.benchmark_dir,'set_active_model':mod.set_active_model,
        'unload_model':mod.unload_model,'normalize_think_value':mod.normalize_think_value,
        'make_cfg':mod.make_cfg,'model_catalog':mod.model_catalog,
        'model_digest':mod.model_digest,'model_profile':mod.model_profile,
        'benchmark_record':mod.benchmark_record,
    }
    current=['m1']; catalog={'m1':{'name':'m1','digest':'d1'},'m2':{'name':'m2','digest':'d2'}}
    mod.benchmark_dir=lambda create=True:root
    mod.set_active_model=lambda name:(current.__setitem__(0,name) or name)
    mod.unload_model=lambda name:True
    mod.normalize_think_value=lambda name,v:(v,None)
    mod.make_cfg=lambda mode,v:{
        'model':current[0],'think':True,'think_value':v,'num_predict':3200,
        'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42,
    }
    mod.model_catalog=lambda:catalog
    mod.model_digest=lambda name,catalog_arg=None:catalog.get(name,{}).get('digest','')
    mod.model_profile=lambda name:{
        'ctx':8192,'threads':12,
        'think':{'num_predict':3200,'temperature':1,'top_p':.95,'top_k':20,'min_p':0,'seed':42},
        'fast':{'num_predict':512,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42},
    }

    def restore():
        for name,value in old.items():setattr(mod,name,value)
    return catalog,current,restore


def _checkpoint_ok_record(name,cfg,ri,attempt):
    return {
        'record_schema_version':mod.BENCH_RECORD_SCHEMA_VERSION,
        'execution_status':'ok','completion_status':'completed',
        'identity':{'benchmark':name,'benchmark_version':3,'model':cfg['model'],'run':ri,'attempt':attempt},
        'config':{'seed':cfg['seed'],'effective_config_fingerprint':'cfg'},
        'primary':{'completed':True,'eval_rate':10,'load_seconds':1.0,'answer':'ok'},
        'recovery':{'used':False},
        'final':{'answer':'ok','completed':True,'pipeline_wall_seconds':1},
        'score':{'native':{'value':1},'final':{'value':1}},
        'telemetry':{'runtime':{},'gpu':{}},
    }


def test_checkpoint_hard_restart_replays_only_active_job_from_start():
    root=Path(tempfile.mkdtemp()); catalog,current,restore=_checkpoint_recovery_harness(root)
    calls=[]
    try:
        def crash_once(name,item,cfg,tv,ri,total,**kw):
            calls.append((name,cfg['model'],ri,kw.get('attempt')))
            if len(calls)==1:raise SystemExit('synthetic power loss')
            return _checkpoint_ok_record(name,cfg,ri,kw.get('attempt'))
        mod.benchmark_record=crash_once
        spec=mod.make_benchmark_spec(['simpson'],['m1'],1,True,'native','fixed','restart',catalog=catalog)
        path,cp=mod.new_checkpoint(spec)
        try:mod.execute_benchmark_checkpoint(path,cp,catalog)
        except SystemExit:pass
        else:raise AssertionError('synthetic hard stop did not propagate')
        _,disk=mod.load_checkpoint(path)
        eq(disk['active_job']['key'],'simpson|m1|1')
        eq(disk['attempt_history'][0]['status'],'running')
        mod.execute_benchmark_checkpoint(path,disk,catalog)
        rec=disk['records']['simpson|m1|1']
        eq(rec['identity']['attempt'],2)
        assert rec['client_recovery']['resumed_after_interruption'] is True
        eq([x['status'] for x in disk['attempt_history']],['abandoned','completed'])
        eq(disk['recovery_metrics']['interrupted_attempts'],1)
        eq(calls,[('simpson','m1',1,1),('simpson','m1',1,2)])
    finally:
        restore(); shutil.rmtree(root,ignore_errors=True)


def test_checkpoint_transport_failure_pauses_without_cascade_and_resumes():
    root=Path(tempfile.mkdtemp()); catalog,current,restore=_checkpoint_recovery_harness(root)
    calls=[]
    try:
        def disconnected(name,item,cfg,tv,ri,total,**kw):
            calls.append((cfg['model'],kw.get('attempt')))
            raise ConnectionResetError('connection reset by peer')
        mod.benchmark_record=disconnected
        spec=mod.make_benchmark_spec(['simpson'],['m1','m2'],1,True,'native','fixed','transport',catalog=catalog)
        path,cp=mod.new_checkpoint(spec)
        try:mod.execute_benchmark_checkpoint(path,cp,catalog)
        except mod.BenchmarkConnectivityPause:pass
        else:raise AssertionError('transport failure must pause the suite')
        eq(cp['suite_status'],'paused_connectivity')
        eq(cp['records'],{})
        eq(len(calls),1)
        interrupted_model=calls[0][0]
        eq(cp['attempt_history'][0]['status'],'transport_error')
        eq(cp['recovery_metrics']['transport_pauses'],1)

        def connected(name,item,cfg,tv,ri,total,**kw):
            calls.append((cfg['model'],kw.get('attempt')))
            return _checkpoint_ok_record(name,cfg,ri,kw.get('attempt'))
        mod.benchmark_record=connected
        mod.execute_benchmark_checkpoint(path,cp,catalog)
        eq(cp['suite_status'],'execution_complete')
        eq(len(cp['records']),2)
        other_model='m2' if interrupted_model=='m1' else 'm1'
        first=cp['records'][f'simpson|{interrupted_model}|1']
        second=cp['records'][f'simpson|{other_model}|1']
        eq(first['identity']['attempt'],2)
        eq(second['identity']['attempt'],1)
        assert first['client_recovery']['resumed_after_interruption'] is True
        assert second['client_recovery']['resumed_after_interruption'] is False
        summary={row['model']:row for row in mod.benchmark_summary_rows(list(cp['records'].values()))}
        eq(summary[interrupted_model]['client_retry_attempts'],1)
        eq(summary[interrupted_model]['client_transport_failures'],1)
        eq(summary[interrupted_model]['native_score_avg'],1.0)
        assert summary[interrupted_model]['client_recovery_excluded_from_model_score'] is True
    finally:
        restore(); shutil.rmtree(root,ignore_errors=True)


def test_checkpoint_finalize_is_idempotent_and_recovers_missing_output():
    root=Path(tempfile.mkdtemp()); catalog,current,restore=_checkpoint_recovery_harness(root)
    try:
        mod.benchmark_record=lambda name,item,cfg,tv,ri,total,**kw:_checkpoint_ok_record(name,cfg,ri,kw.get('attempt'))
        spec=mod.make_benchmark_spec(['simpson'],['m1'],1,True,'native','fixed','finalize',catalog=catalog)
        path,cp=mod.new_checkpoint(spec)
        mod.execute_benchmark_checkpoint(path,cp,catalog)
        mod.finalize_checkpoint(path,cp)
        eq(cp['suite_status'],'complete')
        eq(set(cp['output_integrity']),{
            'json','csv','summary_json','summary_csv','tested_profiles_json','report_html',
            'evidence_private_json','evidence_share_safe_json',
        })
        assert all(re.fullmatch(r'[0-9a-f]{64}',row['sha256']) for row in cp['output_integrity'].values())
        missing=Path(cp['outputs']['summary_csv']); missing.unlink()
        eq(mod.latest_resumable_checkpoint(),path)
        mod.finalize_checkpoint(path,cp)
        assert missing.is_file()
        eq(cp['suite_status'],'complete')
        assert mod.latest_resumable_checkpoint() is None
    finally:
        restore(); shutil.rmtree(root,ignore_errors=True)


def test_legacy_summary():
    old={'benchmark':'retention_d7','model':'old','answer':'partial','native_completed':False,'fallback_used':True,'final_completed':False,'sanity_score':None,'primary_eval_rate':10.0,'pipeline_wall_seconds':2.0,'seed':42,'vram_used_mib':1000,'gpu_util':0,'gpu_offload_pct':50}
    rows=mod.benchmark_summary_rows([old]); eq(len(rows),1); eq(rows[0]['model'],'old')




def test_all_builtin_scorers():
    sim=mod.builtin_benchmarks()['simpson']
    sim_ans=(
        'A выше по точечной конверсии внутри обоих сегментов, B выше только агрегированно. '
        'Наблюдаемый состав трафика несбалансирован, поэтому нужно проверить рандомизацию и '
        'статистическую неопределённость до продуктового решения.\n'
        'BENCHMARK_RESULT\n'
        +json.dumps(simpson_v3_payload(),ensure_ascii=False)
    )
    score=mod.benchmark_score('simpson',sim,sim_ans)
    eq(score['method'],'simpson_v3')
    eq(score['value'],1.0)

    fun=mod.builtin_benchmarks()['funnel']
    fun_obj={
        'view_to_save':0.40,
        'save_to_apply':0.50,
        'apply_to_interview':0.25,
        'interview_to_offer':0.30,
        'largest_relative_loss_stage':'apply_to_interview',
    }
    fun_ans=(
        '1. Конверсии: 40%, 50%, 25%, 30%.\n'
        '2. Наибольшая относительная потеря: отклик к интервью, потеря 75%.\n'
        '3. Возможные причины:\n'
        'Причина 1: нерелевантные отклики повышают отсев.\n'
        'Причина 2: резюме могут не соответствовать требованиям.\n'
        'Причина 3: длительный ответ работодателя повышает отток.\n'
        '4. Данные для проверки:\n'
        'Проверка 1: причины отказов после отклика.\n'
        'Проверка 2: время до первого ответа работодателя.\n'
        'BENCHMARK_RESULT\n'
        +json.dumps(fun_obj,ensure_ascii=False)
    )
    score=mod.benchmark_score('funnel',fun,fun_ans)
    eq(score['method'],'funnel_v3')
    eq(score['value'],1.0)

    ret=mod.builtin_benchmarks()['retention_d7']
    eq(mod.benchmark_score('retention_d7',ret,retention_answer(True))['value'],1.0)

    ins=mod.builtin_benchmarks()['instruction']
    ins_ans=(
        '1. Преимущество: локальная модель сохраняет рабочие данные на собственном компьютере.\n'
        '2. Преимущество: локальная модель позволяет работать без подключения к внешнему сервису.\n'
        '3. Преимущество: локальная модель даёт полный контроль над настройками обработки данных.\n'
        '4. Риск: высокие требования к оборудованию могут потребовать значительных инвестиций.'
    )
    score=mod.benchmark_score('instruction',ins,ins_ans)
    eq(score['method'],'instruction_v4')
    eq(score['value'],1.0)


def test_v174_category_scorers_and_code_sandbox():
    built=mod.builtin_benchmarks()
    code='''Ошибки исправлены сортировкой нормализованных копий и объединением соседних интервалов.
```python
def normalize_intervals(intervals):
    normalized = sorted([[min(a, b), max(a, b)] for a, b in intervals])
    merged = []
    for start, end in normalized:
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```
BENCHMARK_RESULT
{"algorithm":"sort_and_sweep","complexity":"O(n log n)","mutates_input":false}'''
    score=mod.benchmark_score('python_debug',built['python_debug'],code)
    eq(score['method'],'python_debug_v1'); eq(score['value'],1.0)
    eq(score['execution']['passed'],5)

    unsafe='''```python
def normalize_intervals(intervals):
    return open("secret.txt").read()
```
BENCHMARK_RESULT
{"algorithm":"sort_and_sweep","complexity":"O(n log n)","mutates_input":false}'''
    bad=mod.benchmark_score('python_debug',built['python_debug'],unsafe)
    assert bad['value']<.5 and bad['safety_error']

    for name in ('logic_constraints','dialogue_state','russian_editing','groundedness'):
        item=built[name]
        answer='Краткое обоснование.\nBENCHMARK_RESULT\n'+json.dumps(item['reference'],ensure_ascii=False)
        score=mod.benchmark_score(name,item,answer)
        eq(score['method'],'structured_reference_v1'); eq(score['value'],1.0)

    expected_categories={
        'python_debug':'code_python','logic_constraints':'formal_logic',
        'dialogue_state':'dialogue_consistency','russian_editing':'linguistics_ru',
        'groundedness':'groundedness_security',
    }
    for name,category in expected_categories.items(): eq(built[name]['category'],category)


def test_benchmark_schema_matches_scorer():
    required={
        'simpson':[
            'a_total','b_total','mobile_a','mobile_b',
            'desktop_a','desktop_b','segment_point_winner',
            'aggregate_winner','product_decision','phenomenon',
            'should_check_randomization_balance','observed_balance_ok',
            'needs_significance_check'
        ],
        'funnel':[
            'view_to_save','save_to_apply',
            'apply_to_interview','interview_to_offer',
            'largest_relative_loss_stage'
        ],
        'retention_d7':[
            'technical_issue','date_dtype_strategy','d7_rule',
            'user_grain','no_activity_in_denominator',
            'registration_rule','cohorts'
        ],
        'analytics_case':[
            'dedupe_latest','latest_status_paid_only','half_open_july_window',
            'user_level_conversion','zero_revenue_users_in_denominator',
            'conversion_diff','z_stat','z_p_value','ci_low','ci_high',
            'arpu_diff','welch_t','welch_p','decision'
        ],
        'python_debug':['algorithm','complexity','mutates_input'],
        'logic_constraints':['monday_person','monday_task','tuesday_person','tuesday_task','wednesday_person','wednesday_task','solution_count'],
        'dialogue_state':['project','deadline','language','cloud_allowed','superseded_deadline','unsupported_assistant_deadline'],
        'russian_editing':['corrected_text','preserved_token','preserved_number'],
        'groundedness':['supported','contradicted','unknown','ignored_embedded_instruction'],
    }
    built=mod.builtin_benchmarks()
    eq(built['simpson']['version'],3)
    eq(built['funnel']['version'],3)
    eq(built['instruction']['version'],4)
    for name,fields in required.items():
        instr=built[name].get('result_instruction','')
        missing=[x for x in fields if x not in instr]
        assert not missing,(name,missing)


def test_client_rescue_is_bounded_and_continues_partial_answer():
    class Sampler:
        def start(self): return self
        def stop(self): return {'samples':1,'vram_peak_mib':1000}

    old_sampler=mod.GpuSampler
    old_stream=mod.stream_chat
    old_rt=mod._runtime_telemetry
    old_digest=mod.model_digest

    mod.GpuSampler=Sampler
    mod._runtime_telemetry=lambda model:{'gpu_offload_pct':50,'context_length':8192}
    mod.model_digest=lambda model,catalog=None:'digest'
    mod.NUM_CTX=8192
    mod.NUM_THREAD=12

    cfg={
        'model':'x','think':True,'think_value':True,
        'num_predict':3200,'temperature':1.0,'top_p':.95,
        'top_k':20,'min_p':0.0,'seed':42
    }
    item=mod.builtin_benchmarks()['retention_d7']
    calls=[]

    def fake_stream(msgs,cfg,show_thinking=True,think_override=None,
                    predict_override=None,tools=None,response_format=None,
                    silent=False):
        payload='\n'.join(str(m.get('content','')) for m in msgs)
        calls.append({
            'think':think_override,
            'predict':predict_override,
            'payload':payload,
        })
        if think_override is True:
            return '', 'PRIMARY_REASONING_SENTINEL', {
                'done_reason':'length','eval_count':5000,
                'eval_duration':10_000_000_000,
                'prompt_eval_count':100,'prompt_eval_duration':1_000_000_000
            }
        if len(calls)==2:
            return 'VERY_LONG_RECOVERY_SENTINEL', '', {
                'done_reason':'length','eval_count':1900,
                'eval_duration':9_000_000_000,
                'prompt_eval_count':500,'prompt_eval_duration':1_000_000_000
            }
        return retention_answer(True), '', {
            'done_reason':'stop','eval_count':1000,
            'eval_duration':8_000_000_000,
            'prompt_eval_count':500,'prompt_eval_duration':1_000_000_000
        }

    mod.stream_chat=fake_stream
    r=mod.benchmark_record(
        'retention_d7',item,cfg,True,1,1,
        bench_mode='client',catalog={'x':{'digest':'digest'}}
    )

    eq(len(calls),3)
    eq(calls[0]['think'],True)
    eq(calls[1]['think'],False)
    eq(calls[2]['think'],False)
    assert 'VERY_LONG_RECOVERY_SENTINEL' in calls[2]['payload']
    eq(r['recovery']['strategy'],'continue_then_targeted_rescue_v3')
    eq(len(r['recovery']['passes']),2)
    assert r['recovery']['completed']
    assert r['final']['completed']
    eq(r['score']['final']['value'],1.0)

    mod.GpuSampler=old_sampler
    mod.stream_chat=old_stream
    mod._runtime_telemetry=old_rt
    mod.model_digest=old_digest


def test_benchmark_identity_reproducibility():
    built=mod.builtin_benchmarks()
    for name,item in built.items():
        h=mod.benchmark_prompt_sha256(item)
        assert re.fullmatch(r'[0-9a-f]{64}',h),(name,h)
        assert int(item.get('version',0))>=1,name
    cat={'m:latest':{'name':'m:latest','digest':'sha256:0123456789abcdef'}}
    eq(mod.model_digest('m:latest',cat),'sha256:0123456789abcdef')




def test_profile_fingerprint_and_resume_guard():
    old_profile=mod.model_profile
    old_norm=mod.normalize_think_value
    try:
        profiles={
            'm':{
                'ctx':8192,'threads':12,
                'fast':{'temperature':0.2,'top_p':0.85,'top_k':40,'min_p':0.05,'seed':42,'num_predict':512},
                'think':{'temperature':1.0,'top_p':0.95,'top_k':20,'min_p':0.0,'seed':42,'num_predict':3200},
            }
        }
        mod.model_profile=lambda name:profiles[name]
        mod.normalize_think_value=lambda name,v:(v,None)

        h1=mod.benchmark_profile_fingerprint('m',True,'native')
        h2=mod.benchmark_profile_fingerprint('m',True,'native')
        eq(h1,h2)
        assert re.fullmatch(r'[0-9a-f]{64}',h1)

        cp={
            'spec':{
                'client_version':mod.APP_VERSION,
                'think_value':True,
                'mode':'native',
                'test_fingerprints':{},
                'model_digests':{'m':'digest'},
                'model_profile_fingerprints':{'m':h1},
            },
            'records':{},
        }
        catalog={'m':{'name':'m','digest':'digest'}}
        eq(mod.validate_checkpoint_environment(cp,catalog,force=False),[])

        profiles['m']['think']['temperature']=0.6
        try:
            mod.validate_checkpoint_environment(cp,catalog,force=False)
        except RuntimeError as e:
            assert 'model profile changed: m' in str(e)
        else:
            raise AssertionError('profile change was not detected')
    finally:
        mod.model_profile=old_profile
        mod.normalize_think_value=old_norm


def test_resume_detects_missing_model():
    cp={
        'spec':{
            'client_version':mod.APP_VERSION,
            'think_value':True,
            'mode':'native',
            'test_fingerprints':{},
            'model_digests':{'missing-model':'sha256:abc'},
            'model_profile_fingerprints':{},
        },
        'records':{},
    }
    try:
        mod.validate_checkpoint_environment(cp,{},force=False)
    except RuntimeError as e:
        assert 'model missing: missing-model' in str(e)
    else:
        raise AssertionError('missing model was not detected')




def test_v161_summary_semantics():
    rec={
        'record_schema_version':5,
        'execution_status':'ok',
        'completion_status':'truncated',
        'identity':{
            'benchmark':'retention_d7','benchmark_version':5,
            'benchmark_prompt_sha256':'abc','model':'m','model_digest':'digest'
        },
        'config':{'benchmark_mode':'native','seed_mode':'fixed','seed':42},
        'primary':{'eval_rate':10.0,'completed':False},
        'recovery':{'used':False},
        'final':{'completed':False,'done_reason':'length','pipeline_wall_seconds':2.0},
        'score':{'native':{'value':None},'final':{'value':None}},
        'telemetry':{'gpu':{},'runtime':{}},
    }
    row=mod.benchmark_summary_rows([rec])[0]
    eq(row['runs_planned'],1)
    eq(row['runs_executed'],1)
    eq(row['runs_completed'],0)
    eq(row['runs_truncated'],1)
    eq(row['runs_scorable'],0)
    eq(row['primary_eval_warm_avg'],None)
    assert 'runs_ok' not in row


def _v174_summary_record(seed,score,rate,load_seconds,wall_seconds,run_fp,profile_fp):
    return {
        'record_schema_version':7,
        'execution_status':'ok',
        'completion_status':'completed',
        'identity':{
            'benchmark':'quality_case','benchmark_version':1,
            'benchmark_prompt_sha256':'prompt','benchmark_reference_sha256':'reference',
            'backend':'ollama','model':'model-a','model_digest':'digest-a',
        },
        'config':{
            'benchmark_mode':'client','backend':'ollama','seed_mode':'manual','seed':seed,
            'effective_config_fingerprint':run_fp,
            'effective_profile_fingerprint':profile_fp,
        },
        'primary':{
            'eval_rate':rate,'load_seconds':load_seconds,
            'load_state':mod.benchmark_load_state(load_seconds),'completed':True,
        },
        'recovery':{'used':False},
        'final':{
            'completed':True,'done_reason':'stop','pipeline_wall_seconds':wall_seconds,
            'pipeline_eval_tokens':100,
        },
        'score':{
            'native':{'value':score},'final':{'value':score},
            'partial':None,'best_verified_partial':None,
        },
        'telemetry':{'gpu':{},'runtime':{}},
    }


def test_summary_v5_groups_seeds_and_reports_uncertainty():
    records=[
        _v174_summary_record(42,.4,10.0,12.0,2.0,'run-42','profile-a'),
        _v174_summary_record(43,.8,20.0,.2,4.0,'run-43','profile-a'),
    ]
    rows=mod.benchmark_summary_rows(records)
    eq(len(rows),1)
    row=rows[0]
    eq(row['summary_schema_version'],11)
    eq(row['effective_profile_fingerprint'],'profile-a')
    eq(row['run_fingerprints'],['run-42','run-43'])
    eq(row['seeds'],[42,43])
    eq(row['cold_runs'],1)
    eq(row['warm_runs'],1)
    close(row['primary_eval_warm_avg'],20.0)
    close(row['final_score_avg'],.6)
    close(row['final_score_sd'],math.sqrt(.08))
    close(row['final_score_min'],.4)
    close(row['final_score_max'],.8)
    eq(row['final_score_worst_seed'],42)
    close(row['pipeline_wall_sd'],math.sqrt(2.0))
    close(row['pipeline_wall_min'],2.0)
    close(row['pipeline_wall_max'],4.0)


def test_profile_fingerprint_excludes_seed_but_run_fingerprint_does_not():
    old_profile=mod.model_profile; old_caps=mod.cached_model_capabilities
    try:
        mod.model_profile=lambda name:_benchmark_test_profile()
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        item=mod.builtin_benchmarks()['simpson']
        a=mod.benchmark_effective_config('m','simpson',item,False,42,'fair_default',None,'client')
        b=mod.benchmark_effective_config('m','simpson',item,False,43,'fair_default',None,'client')
        assert a['fingerprint']!=b['fingerprint']
        eq(a['profile_fingerprint'],b['profile_fingerprint'])
    finally:
        mod.model_profile=old_profile; mod.cached_model_capabilities=old_caps


def test_balanced_execution_layout_is_deterministic_and_rotates_tests():
    spec={
        'models':['m1','m2','m3'],'tests':['a','b','c'],
        'order_policy':'balanced','schedule_seed':123,
    }
    first=mod.benchmark_execution_layout(spec)
    second=mod.benchmark_execution_layout(spec)
    eq(first,second)
    blocks={}
    for row in first:
        blocks.setdefault(row['model'],[]).append(row['test'])
    eq(sorted(blocks),['m1','m2','m3'])
    assert len({tuple(v) for v in blocks.values()})==3
    for position in range(3):
        eq(sorted(v[position] for v in blocks.values()),['a','b','c'])


def test_recovery_candidate_selection_penalizes_regression_and_repetition():
    repeated='\n'.join(['Повторяемая длинная строка для проверки восстановления.']*8)
    clean='Короткий проверенный частичный ответ.'
    candidates=[
        {'stage':'primary','answer':clean,'completed':False,'score':{'value':.4}},
        {'stage':'rescue','answer':repeated,'completed':False,'score':{'value':.1}},
    ]
    best=mod.select_benchmark_candidate(candidates)
    eq(best['stage'],'primary')
    assert mod.benchmark_repetition_metrics(repeated)['duplicate_line_ratio']>0
    eq(mod.benchmark_repetition_metrics(clean)['duplicate_line_ratio'],0.0)


def test_retention_executor_preflight_and_safety():
    ok,info=mod._retention_executor_preflight()
    assert ok,info

    safe,err=mod._retention_code_safety(
        'import pandas as pd\n'
        'def calculate_retention_d7(events):\n'
        '    x=events.rename(columns={"event_time":"t"})\n'
        '    return x\n'
    )
    assert safe,err

    safe,err=mod._retention_code_safety(
        'import os\n'
        'def calculate_retention_d7(events):\n'
        '    os.system("echo unsafe")\n'
        '    return events\n'
    )
    assert not safe

    # Import aliases must not bypass the filesystem/network deny-list.
    for code in (
        'from pandas import read_csv as rc\n'
        'def calculate_retention_d7(events):\n    return rc("secret.csv")\n',
        'import pandas as os\n'
        'def calculate_retention_d7(events):\n    return events\n',
        'import pandas as pd\n'
        'def calculate_retention_d7(events):\n    return pd.io.common.os.system("whoami")\n',
    ):
        safe,err=mod._retention_code_safety(code)
        assert not safe,(code,err)


def test_generated_scorers_reject_extended_library_io():
    retention=(
        'import pandas as pd\n'
        'def calculate_retention_d7(events):\n'
        '    _ = pd.read_fwf("C:/sensitive.txt")\n'
        '    return events\n'
    )
    safe,reason=mod._retention_code_safety(retention)
    assert not safe,reason

    analytics=(
        'import pandas as pd\n'
        'def analyze_ab(users, orders):\n'
        '    _ = pd.read_clipboard()\n'
        '    return users, {"x": len(orders)}, None\n'
    )
    safe,reason=mod._analytics_python_safety(analytics)
    assert not safe,reason


def test_checkpoint_v7_state_machine():
    spec={
        'label':'x','tests':[],'models':[],'runs':1,'think_value':True,
        'mode':'native','seed_mode':'fixed'
    }
    root=Path(tempfile.mkdtemp())
    old_dir=mod.benchmark_dir
    mod.benchmark_dir=lambda create=True:root
    try:
        path,cp=mod.new_checkpoint(spec)
        eq(cp['checkpoint_schema_version'],mod.BENCH_CHECKPOINT_SCHEMA_VERSION)
        eq(cp['suite_status'],'running')
        eq(cp['active_job'],None)
        eq(cp['attempt_history'],[])
        eq(cp['resume_history'],[])
        eq(cp['recovery_metrics'],{
            'interrupted_attempts':0,'transport_pauses':0,'resumed_jobs':0,
            'reconnect_attempts':0,'reconnect_failures':0,
        })
        assert 'status' not in cp
    finally:
        mod.benchmark_dir=old_dir




def _with_inputs(values,fn):
    old=mod.read_user_input
    seq=iter(values)
    mod.read_user_input=lambda prompt='':next(seq)
    try:
        return fn()
    finally:
        mod.read_user_input=old


def test_startup_home_menu_routes():
    old_clear=mod.clear_console
    old_sleep=mod.time.sleep
    mod.clear_console=lambda:None
    mod.time.sleep=lambda x:None
    try:
        eq(_with_inputs(['2','1'],lambda:mod.startup_home_menu('0.32.14','18/18')),'chat')
        eq(_with_inputs(['1'],lambda:mod.startup_home_menu('0.32.14','18/18')),'benchmark')
        eq(_with_inputs(['2','2'],lambda:mod.startup_home_menu('0.32.14','18/18')),'load')
        eq(_with_inputs(['agent'],lambda:mod.startup_home_menu('0.32.14','18/18')),'agent')
        eq(_with_inputs(['4'],lambda:mod.startup_home_menu('0.32.14','18/18')),'connections')
        eq(_with_inputs(['6','1'],lambda:mod.startup_home_menu('0.32.14','18/18')),'/dashboard')
        eq(_with_inputs(['/ui'],lambda:mod.startup_home_menu('0.32.14','18/18')),'/ui')
        eq(_with_inputs(['0'],lambda:mod.startup_home_menu('0.32.14','18/18')),'exit')
    finally:
        mod.clear_console=old_clear
        mod.time.sleep=old_sleep


def test_startup_benchmark_wizard_commands():
    old_clear=mod.clear_console
    old_sleep=mod.time.sleep
    old_load=mod.load_benchmarks
    mod.clear_console=lambda:None
    mod.time.sleep=lambda x:None
    mod.load_benchmarks=lambda:{
        'retention_d7':{
            'version':5,'description':'test',
            'prompt':'x','score_type':'retention_d7_v5'
        },
        'simpson':{
            'version':3,'description':'test2',
            'prompt':'x','score_type':'simpson_v3'
        },
    }
    try:
        cmd,home=_with_inputs(['4'],mod.startup_benchmark_wizard)
        eq(cmd,'/bench resume')
        assert home is True

        cmd,home=_with_inputs(['0'],mod.startup_benchmark_wizard)
        eq(cmd,'/home')
        assert home is False
    finally:
        mod.clear_console=old_clear
        mod.time.sleep=old_sleep
        mod.load_benchmarks=old_load


def test_startup_regression_missing_file_fails_closed():
    old=mod._startup_regression_path
    mod._startup_regression_path=lambda:Path('/definitely/missing/benchmark_regression.py')
    try:
        r=mod.run_startup_regression()
        assert r['ok'] is False
        assert 'missing' in r['summary']
    finally:
        mod._startup_regression_path=old




def test_red_color_helper_exists():
    assert callable(mod.red)
    old=mod._COLOR_ENABLED
    mod._COLOR_ENABLED=False
    try:
        mod.red()  # must never raise even when colors are disabled
    finally:
        mod._COLOR_ENABLED=old


def test_startup_regression_failure_path_does_not_crash():
    old_stream=mod._stream_startup_regression
    old_path=mod._startup_regression_path
    old_color=mod._COLOR_ENABLED
    try:
        mod._COLOR_ENABLED=False
        mod._startup_regression_path=lambda:Path(__file__)
        mod._stream_startup_regression=lambda *a,**k:(1,'FAIL synthetic regression\nsynthetic stderr',False)
        result=mod.run_startup_regression(force=True)
        assert result['ok'] is False
        assert 'synthetic regression' in result['output']
        # This was the exact v16.2 crash site.
        mod.show_startup_regression_failure(result)
    finally:
        mod._stream_startup_regression=old_stream
        mod._startup_regression_path=old_path
        mod._COLOR_ENABLED=old_color


def test_startup_regression_failure_excerpt_keeps_root_cause():
    output='\n'.join(
        ['noisy successful check']*300+
        ['FAIL configured backend settings: values differ',
         'Traceback (most recent call last):',
         'AssertionError: expected local template']
    )
    excerpt=mod._startup_regression_failure_excerpt(output)
    assert 'FAIL configured backend settings' in excerpt
    assert 'AssertionError: expected local template' in excerpt
    assert len(excerpt)<=6200
    assert excerpt.count('noisy successful check')<40


def test_startup_regression_cache_is_exact_and_avoids_repeat_suite():
    root=Path(tempfile.mkdtemp())
    test_file=root/'regression.py'
    test_file.write_text('print("PASS 7/7")\n',encoding='utf-8')
    old_stream=mod._stream_startup_regression
    old_path=mod._startup_regression_path
    old_cache=mod._startup_regression_cache_path
    calls=[]
    try:
        mod._startup_regression_path=lambda:test_file
        mod._startup_regression_cache_path=lambda:root/'Runtime'/'cache.json'
        def fake_stream(path,on_line=None,timeout=120):
            calls.append((path,timeout))
            return 0,'PASS 7/7\n',False
        mod._stream_startup_regression=fake_stream
        first=mod.run_startup_regression()
        second=mod.run_startup_regression()
        assert first['ok'] is True and first.get('cached') is False
        assert second['ok'] is True and second.get('cached') is True
        eq(len(calls),1)
        test_file.write_text('print("changed")\n',encoding='utf-8')
        third=mod.run_startup_regression()
        assert third.get('cached') is False
        eq(len(calls),2)
    finally:
        mod._stream_startup_regression=old_stream
        mod._startup_regression_path=old_path
        mod._startup_regression_cache_path=old_cache
        shutil.rmtree(root,ignore_errors=True)


def test_startup_regression_reports_truthful_stage_progress():
    root=Path(tempfile.mkdtemp())
    test_file=root/'regression.py'
    test_file.write_text(
        "print('BULL_STARTUP_TOTAL\\t7',flush=True)\n"
        "print('BULL_STARTUP_TEST\\tstreamed active check',flush=True)\n"
        "print('BULL_STARTUP_COMPLETE\\t1',flush=True)\n"
        "print('PASS 7/7')\n",
        encoding='utf-8',
    )
    old_path=mod._startup_regression_path
    old_cache=mod._startup_regression_cache_path
    updates=[]
    try:
        mod._startup_regression_path=lambda:test_file
        mod._startup_regression_cache_path=lambda:root/'Runtime'/'cache.json'
        result=mod.run_startup_regression(force=True,progress_callback=lambda *args:updates.append(args))
        assert result['ok'] is True
        eq(updates,[
            ('Подготовка проверки запуска\nПроверяются обязательные файлы и манифест регрессии',1,3),
            ('Запуск офлайн-регрессии\nОжидание первой проверки',2,3),
            ('Запуск офлайн-регрессии\nОжидание первой проверки',0,7),
            ('Запуск офлайн-регрессии\nТекущая проверка: streamed active check',0,7),
            ('Запуск офлайн-регрессии\nТекущая проверка завершена',1,7),
            ('Проверка запуска пройдена\nВсе проверки завершены успешно',7,7),
        ])
    finally:
        mod._startup_regression_path=old_path
        mod._startup_regression_cache_path=old_cache
        shutil.rmtree(root,ignore_errors=True)


def test_startup_regression_active_check_marker_is_explicit_and_bounded():
    eq(mod._startup_active_check_from_output('OK normal output\n'),'')
    eq(
        mod._startup_active_check_from_output('BULL_STARTUP_TEST\tcritical scorer contract\n'),
        'critical scorer contract',
    )
    eq(
        mod._startup_active_check_from_output('x BULL_STARTUP_TEST\t'+'a'*200),
        'a'*140,
    )
    eq(mod._startup_count_from_output('BULL_STARTUP_TOTAL\t390\n',mod._STARTUP_TOTAL_MARKER),390)
    eq(mod._startup_count_from_output('BULL_STARTUP_COMPLETE\t-1\n',mod._STARTUP_COMPLETE_MARKER),None)




def test_utf8_subprocess_environment():
    env=mod._utf8_subprocess_env()
    eq(env.get('PYTHONUTF8'),'1')
    eq(env.get('PYTHONIOENCODING'),'utf-8')


def test_unicode_progress_bar_under_forced_utf8_child():
    # Reproduce the Windows failure shape: a child process prints the same
    # full-block progress characters. PYTHONUTF8/PYTHONIOENCODING must make it safe.
    code=(
        "import sys\n"
        "print('Benchmark    ██████████████████████████ 1/1')\n"
        "print('✓ Regression Unicode OK')\n"
    )
    cp=mod.subprocess.run(
        [sys.executable,'-c',code],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='strict',
        env=mod._utf8_subprocess_env(),
        timeout=20,
    )
    eq(cp.returncode,0,cp.stderr)
    assert '████' in cp.stdout
    assert '✓ Regression Unicode OK' in cp.stdout




def test_benchmark_result_menu_home():
    old=mod.read_user_input
    old_color=mod._COLOR_ENABLED
    mod._COLOR_ENABLED=False
    mod.read_user_input=lambda prompt='':'0'
    try:
        eq(mod.benchmark_result_menu('/bench compare simpson all 1 native fixed','x.json'),'/home')
    finally:
        mod.read_user_input=old
        mod._COLOR_ENABLED=old_color


def test_benchmark_result_menu_answers_stays_on_screen():
    old_input=mod.read_user_input
    old_show=mod.show_benchmark_answers
    old_color=mod._COLOR_ENABLED
    seq=iter(['5','','0'])
    seen=[]
    mod._COLOR_ENABLED=False
    mod.read_user_input=lambda prompt='':next(seq)
    mod.show_benchmark_answers=lambda path:seen.append(path)
    try:
        action=mod.benchmark_result_menu(
            '/bench compare simpson all 1 native fixed',
            'result.json'
        )
        eq(action,'/home')
        eq(seen,['result.json'])
    finally:
        mod.read_user_input=old_input
        mod.show_benchmark_answers=old_show
        mod._COLOR_ENABLED=old_color


def test_benchmark_result_menu_repeat_and_resume_guard():
    old=mod.read_user_input
    old_color=mod._COLOR_ENABLED
    mod._COLOR_ENABLED=False
    try:
        cmd='/bench compare simpson all 3 client sweep'
        mod.read_user_input=lambda prompt='':'6'
        eq(mod.benchmark_result_menu(cmd,'result.json'),cmd)

        seq=iter(['6','0'])
        mod.read_user_input=lambda prompt='':next(seq)
        # Repeat must not pretend that a completed resume can simply be run again.
        eq(mod.benchmark_result_menu('/bench resume','result.json'),'/home')
    finally:
        mod.read_user_input=old
        mod._COLOR_ENABLED=old_color


def test_benchmark_result_menu_benchmark_route():
    old=mod.read_user_input
    old_color=mod._COLOR_ENABLED
    mod._COLOR_ENABLED=False
    mod.read_user_input=lambda prompt='':'7'
    try:
        eq(
            mod.benchmark_result_menu('/bench all 1 native fixed','result.json'),
            '__benchmark_menu__'
        )
    finally:
        mod.read_user_input=old
        mod._COLOR_ENABLED=old_color




def test_benchmark_result_menu_interrupt_goes_home():
    old=mod.read_user_input
    old_color=mod._COLOR_ENABLED
    mod._COLOR_ENABLED=False
    def boom(prompt=''):
        raise KeyboardInterrupt()
    mod.read_user_input=boom
    try:
        eq(
            mod.benchmark_result_menu('/bench compare simpson all 1 native fixed','result.json'),
            '/home'
        )
    finally:
        mod.read_user_input=old
        mod._COLOR_ENABLED=old_color


def test_benchmark_result_menu_opens_visual_report_and_stays():
    old_input=mod.read_user_input
    old_open=mod.open_benchmark_visual_report
    old_color=mod._COLOR_ENABLED
    seq=iter(['3','','0']); seen=[]
    mod._COLOR_ENABLED=False
    mod.read_user_input=lambda prompt='':next(seq)
    mod.open_benchmark_visual_report=lambda path:seen.append(Path(path)) or True
    try:
        action=mod.benchmark_result_menu(
            '/bench compare simpson all 1 native fixed',
            'result.json'
        )
        eq(action,'/home')
        eq(seen,[Path('result_report.html')])
    finally:
        mod.read_user_input=old_input
        mod.open_benchmark_visual_report=old_open
        mod._COLOR_ENABLED=old_color




def test_simpson_v3_disambiguates_balance_and_check():
    item=mod.builtin_benchmarks()['simpson']
    obj=simpson_v3_payload()
    ans=(
        'Трафик явно несбалансирован, поэтому баланс нельзя считать корректным; '
        'при этом рандомизацию и статистическую неопределённость нужно проверить.\n'
        'BENCHMARK_RESULT\n'+json.dumps(obj,ensure_ascii=False)
    )
    good=mod.benchmark_score('simpson',item,ans)
    eq(good['value'],1.0)

    # This is the old ambiguity: observed balance can be false while the need to check is true.
    assert obj['observed_balance_ok'] is False
    assert obj['should_check_randomization_balance'] is True

    wrong=dict(obj); wrong['should_check_randomization_balance']=False
    bad=mod.benchmark_score(
        'simpson',item,
        'Анализ.\nBENCHMARK_RESULT\n'+json.dumps(wrong,ensure_ascii=False)
    )
    assert bad['value']<good['value']


def test_simpson_v3_product_decision_separate_from_point_winner():
    item=mod.builtin_benchmarks()['simpson']
    obj=simpson_v3_payload()
    wrong=dict(obj); wrong['product_decision']='A'
    score=mod.benchmark_score(
        'simpson',item,
        'A имеет более высокую точечную конверсию, но это ещё не статистическое доказательство.\n'
        'BENCHMARK_RESULT\n'+json.dumps(wrong,ensure_ascii=False)
    )
    checks={x['name']:x['ok'] for x in score['checks']}
    assert checks['segment point winner A'] is True
    assert checks['product decision inconclusive'] is False


def test_simpson_v3_word_limit_scored():
    item=mod.builtin_benchmarks()['simpson']
    ans=('слово '*301)+'\nBENCHMARK_RESULT\n'+json.dumps(
        simpson_v3_payload(),ensure_ascii=False
    )
    score=mod.benchmark_score('simpson',item,ans)
    assert score['word_count']>300
    assert score['value']<1.0


def test_instruction_v3_realistic_risk_phrases():
    item=mod.builtin_benchmarks()['instruction']
    variants=[
        '4. Риск: высокие требования к оборудованию могут потребовать значительных инвестиций.',
        '4. Риск: ограниченная вычислительная мощность компьютера может заметно снижать скорость работы.',
        '4. Риск: без регулярного обновления локальные знания могут постепенно устаревать.',
    ]
    for last in variants:
        ans=(
            '1. Преимущество: данные остаются на локальном компьютере.\n'
            '2. Преимущество: работа не зависит от подключения к внешнему сервису.\n'
            '3. Преимущество: параметры обработки можно настраивать под собственные задачи.\n'
            +last
        )
        eq(mod.benchmark_score('instruction',item,ans)['value'],1.0)

    wrong=(
        '1. Преимущество: данные остаются на локальном компьютере.\n'
        '2. Преимущество: работа не зависит от подключения к внешнему сервису.\n'
        '3. Преимущество: параметры обработки можно настраивать под собственные задачи.\n'
        '4. Преимущество: оборудование можно выбирать самостоятельно.'
    )
    assert mod.benchmark_score('instruction',item,wrong)['value']<1.0


def test_instruction_v3_latin_rule_matches_prompt():
    item=mod.builtin_benchmarks()['instruction']
    ans=(
        '1. Преимущество: данные остаются на локальном компьютере.\n'
        '2. Преимущество: работа возможна без облачного API.\n'
        '3. Преимущество: параметры обработки можно менять самостоятельно.\n'
        '4. Риск: слабое оборудование может снижать скорость.'
    )
    score=mod.benchmark_score('instruction',item,ans)
    checks={x['name']:x['ok'] for x in score['checks']}
    assert checks['no Latin letters'] is False


def test_funnel_v3_requires_full_analytic_shape():
    item=mod.builtin_benchmarks()['funnel']
    obj={
        'view_to_save':0.40,'save_to_apply':0.50,
        'apply_to_interview':0.25,'interview_to_offer':0.30,
        'largest_relative_loss_stage':'apply_to_interview',
    }
    # Correct JSON alone must not mean 100% quality.
    thin='1. Конверсии: верно.\nBENCHMARK_RESULT\n'+json.dumps(obj,ensure_ascii=False)
    thin_score=mod.benchmark_score('funnel',item,thin)
    assert thin_score['value']<0.75,thin_score

    full=(
        '1. Конверсии: 40%, 50%, 25%, 30%.\n'
        '2. Наибольшая относительная потеря: отклик к интервью, 75%.\n'
        '3. Возможные причины:\n'
        'Причина 1: часть откликов нерелевантна требованиям вакансий.\n'
        'Причина 2: профили кандидатов могут быть заполнены недостаточно полно.\n'
        'Причина 3: работодатели могут слишком долго отвечать на отклики.\n'
        '4. Данные для проверки:\n'
        'Проверка 1: причины отказов по каждому отклику.\n'
        'Проверка 2: время между откликом и ответом работодателя.\n'
        'BENCHMARK_RESULT\n'+json.dumps(obj,ensure_ascii=False)
    )
    eq(mod.benchmark_score('funnel',item,full)['value'],1.0)

    four_reasons=full.replace(
        '4. Данные для проверки:',
        'Причина 4: пользователи могут отзывать отклик самостоятельно.\n4. Данные для проверки:'
    )
    score=mod.benchmark_score('funnel',item,four_reasons)
    eq(score['reason_count'],4)
    eq(score['reason_labels'],[1,2,3,4])
    assert score['value']<1.0
    checks={x['name']:x['ok'] for x in score['checks']}
    assert checks['exactly three labeled reasons'] is False


def test_funnel_v3_word_limit():
    item=mod.builtin_benchmarks()['funnel']
    obj={
        'view_to_save':0.40,'save_to_apply':0.50,
        'apply_to_interview':0.25,'interview_to_offer':0.30,
        'largest_relative_loss_stage':'apply_to_interview',
    }
    prefix=(
        '1. Конверсии: 40%, 50%, 25%, 30%.\n'
        '2. Наибольшая относительная потеря: отклик к интервью.\n'
        '3. Возможные причины:\n'
        'Причина 1: первая гипотеза.\nПричина 2: вторая гипотеза.\nПричина 3: третья гипотеза.\n'
        '4. Данные для проверки:\nПроверка 1: первая проверка.\nПроверка 2: вторая проверка.\n'
    )
    ans=prefix+('слово '*451)+'\nBENCHMARK_RESULT\n'+json.dumps(obj,ensure_ascii=False)
    score=mod.benchmark_score('funnel',item,ans)
    assert score['word_count']>450
    assert score['value']<1.0


def test_summary_completion_adjusted_score():
    def rec(run,completed,score=None,partial=None,done='stop'):
        return {
            'record_schema_version':5,'execution_status':'ok',
            'completion_status':'completed' if completed else 'truncated',
            'identity':{
                'benchmark':'x','benchmark_version':1,'benchmark_prompt_sha256':'h',
                'model':'m','model_digest':'d','run':run
            },
            'config':{'benchmark_mode':'client','seed_mode':'sweep','seed':41+run},
            'primary':{'eval_rate':10.0,'completed':False},
            'recovery':{'used':True},
            'final':{'completed':completed,'done_reason':done,'pipeline_wall_seconds':2.0},
            'score':{
                'native':{'value':None},
                'final':{'value':score},
                'partial':partial,
            },
            'telemetry':{'gpu':{},'runtime':{}},
        }
    records=[
        rec(1,True,0.94),
        rec(2,True,0.50),
        rec(3,False,None,{'value':0.8,'code_result_valid':True},'length'),
    ]
    row=mod.benchmark_summary_rows(records)[0]
    eq(row['runs_completed'],2)
    assert abs(row['completion_rate']-2/3)<1e-9
    assert abs(row['final_score_avg']-0.72)<1e-9
    assert abs(row['final_completion_adjusted_score']-0.48)<1e-9
    assert abs(row['scorable_score_avg']-0.72)<1e-9
    assert abs(row['completion_adjusted_score']-0.48)<1e-9
    eq(row['partial_score_valid_runs'],1)
    eq(row['partial_code_checked_runs'],1)
    eq(row['partial_code_valid_runs'],1)
    eq(row['summary_schema_version'],11)


def test_legacy_v2_scorers_still_available():
    sim={'score_type':'simpson_v2'}
    ans='BENCHMARK_RESULT\n'+json.dumps({
        'a_total':.14,'b_total':.45,'mobile_a':.1,'mobile_b':.09,
        'desktop_a':.5,'desktop_b':.49,'preferred':'A',
        'phenomenon':'simpson_paradox','randomization_check':True
    })
    eq(mod.benchmark_score('simpson',sim,ans)['value'],1.0)




def _patch_stream_chat(responses):
    old=mod.stream_chat
    calls=[]
    seq=iter(responses)
    def fake(msgs,cfg,**kwargs):
        calls.append({'msgs':msgs,'cfg':cfg,'kwargs':kwargs})
        return next(seq)
    mod.stream_chat=fake
    return old,calls


def test_chat_think_length_with_final_continues_without_verify():
    old,calls=_patch_stream_chat([
        (' продолжение', '', {'done_reason':'stop','eval_count':80})
    ])
    try:
        ans,th,meta,details=mod.finish_if_needed(
            [{'role':'user','content':'Сложный вопрос'}],
            {'think_value':True},
            'Начало ответа',
            'длинное reasoning',
            {'done_reason':'length','eval_count':3200},
            silent=True,
            return_details=True,
        )
        eq(ans,'Начало ответа продолжение')
        eq(th,'длинное reasoning')
        eq(details['type'],'think_continue_final')
        assert details['automatic_verification_think'] is False
        eq(len(calls),1)
        assert calls[0]['kwargs'].get('think_override') is False
        assert any(
            m.get('role')=='assistant' and m.get('content')=='Начало ответа'
            for m in calls[0]['msgs']
        )
        assert not any('Проверочный THINK' in str(m.get('content','')) for m in calls[0]['msgs'])
    finally:
        mod.stream_chat=old


def test_chat_think_length_without_final_finalizes_reasoning_once():
    old,calls=_patch_stream_chat([
        ('Готовый итоговый ответ.', '', {'done_reason':'stop','eval_count':120})
    ])
    try:
        ans,th,meta,details=mod.finish_if_needed(
            [{'role':'user','content':'Сложный вопрос'}],
            {'think_value':True},
            '',
            'Проверенные вычисления и вывод из первого THINK.',
            {'done_reason':'length','eval_count':3200},
            silent=True,
            return_details=True,
        )
        eq(ans,'Готовый итоговый ответ.')
        eq(details['type'],'think_finalize_from_reasoning')
        eq(len(calls),1)
        assert calls[0]['kwargs'].get('think_override') is False
        prompt=calls[0]['msgs'][-1]['content']
        assert 'Проверенные вычисления' in prompt
        assert 'НЕ начинай новое рассуждение' in prompt
    finally:
        mod.stream_chat=old


def test_chat_think_finalizer_can_continue_without_new_think():
    old,calls=_patch_stream_chat([
        ('Часть', '', {'done_reason':'length','eval_count':1200}),
        (' и конец.', '', {'done_reason':'stop','eval_count':60}),
    ])
    try:
        ans,th,meta,details=mod.finish_if_needed(
            [{'role':'user','content':'Сложный вопрос'}],
            {'think_value':True},
            '',
            'Готовый reasoning.',
            {'done_reason':'length','eval_count':3200},
            silent=True,
            return_details=True,
        )
        eq(ans,'Часть и конец.')
        eq(len(calls),2)
        assert all(c['kwargs'].get('think_override') is False for c in calls)
        eq(details['continuation_passes'],1)
    finally:
        mod.stream_chat=old


def test_chat_completed_answer_never_invokes_fallback():
    old=mod.stream_chat
    def boom(*a,**k):
        raise AssertionError('stream_chat must not be called')
    mod.stream_chat=boom
    try:
        ans,th,meta,details=mod.finish_if_needed(
            [{'role':'user','content':'x'}],
            {'think_value':True},
            'Готово.',
            'reasoning',
            {'done_reason':'stop'},
            silent=True,
            return_details=True,
        )
        eq(ans,'Готово.')
        assert details['used'] is False
    finally:
        mod.stream_chat=old


def test_legacy_audit_fixes_simpson_boolean_ambiguity():
    obj={
        'a_total':.14,'b_total':.45,'mobile_a':.1,'mobile_b':.09,
        'desktop_a':.5,'desktop_b':.49,'preferred':'A',
        'phenomenon':'simpson_paradox','randomization_check':False
    }
    ans=(
        'A выше внутри обоих сегментов. Агрегированный результат меняется из-за структуры трафика. '
        'Нужно проверить баланс и корректность рандомизации между группами.\n'
        'BENCHMARK_RESULT\n'+json.dumps(obj,ensure_ascii=False)
    )
    score=mod._legacy_simpson_v2_audit(ans)
    eq(score['value'],1.0)
    assert 'randomization_check' in score['ignored_ambiguous_legacy_fields']


def test_legacy_instruction_risk_is_not_keyword_false_negative():
    ans=(
        '1. Данные остаются на локальном компьютере.\n'
        '2. Работа возможна без внешнего сервиса.\n'
        '3. Настройки можно менять под собственную задачу.\n'
        '4. Высокие требования к оборудованию могут потребовать значительных инвестиций.'
    )
    score=mod._legacy_instruction_v2_audit(ans)
    eq(score['risk_audit_status'],'explicit_negative_consequence_signal')
    eq(score['value'],1.0)


def test_legacy_instruction_unknown_risk_is_na_not_false():
    ans=(
        '1. Данные остаются на локальном компьютере.\n'
        '2. Работа возможна без внешнего сервиса.\n'
        '3. Настройки можно менять под собственную задачу.\n'
        '4. Этот фактор следует учитывать при выборе модели.'
    )
    score=mod._legacy_instruction_v2_audit(ans)
    assert score['manual_review_required'] is True
    risk=[x for x in score['checks'] if x['name'].startswith('last item')][0]
    assert risk['ok'] is None
    # Unknown semantic risk must not silently reduce the objective-format score.
    eq(score['value'],1.0)
    assert score['audit_coverage']<1.0


def test_rescore_raw_is_offline_and_preserves_original_score():
    root=Path(tempfile.mkdtemp())
    old_dir=mod.benchmark_dir
    old_stream=mod.stream_chat
    mod.benchmark_dir=lambda create=True:root
    def boom(*a,**k):
        raise AssertionError('Ollama/stream_chat must never be called by rescore')
    mod.stream_chat=boom
    try:
        obj={
            'a_total':.14,'b_total':.45,'mobile_a':.1,'mobile_b':.09,
            'desktop_a':.5,'desktop_b':.49,'preferred':'A',
            'phenomenon':'simpson_paradox','randomization_check':False
        }
        answer=(
            'A выше внутри обоих сегментов. Разница агрегата объясняется структурой трафика. '
            'Нужно проверить баланс и рандомизацию.\nBENCHMARK_RESULT\n'
            +json.dumps(obj,ensure_ascii=False)
        )
        rec={
            'record_schema_version':5,'execution_status':'ok',
            'identity':{
                'timestamp':'2026-08-21T00:00:00','client_version':'v16.2.3',
                'benchmark':'simpson','benchmark_version':2,
                'benchmark_prompt_sha256':'old','model':'m','model_digest':'d',
                'run':1,'attempt':1,
            },
            'config':{'benchmark_mode':'client','seed_mode':'fixed','seed':42},
            'primary':{'completed':False,'answer':'','eval_rate':10.0},
            'recovery':{'used':True,'answer':answer},
            'final':{
                'completed':True,'answer':answer,'done_reason':'stop',
                'pipeline_wall_seconds':1.0
            },
            'score':{
                'native':{'value':None},
                'final':{'value':0.9,'method':'old'},
                'partial':None,
            },
            'telemetry':{'gpu':{},'runtime':{}},
            'completion_status':'completed',
        }
        src=root/'old.json'
        src.write_text(json.dumps([rec],ensure_ascii=False),encoding='utf-8')
        records,jp,cp,sj,sc=mod.rescore_benchmark_raw(src)
        eq(len(records),1)
        eq(records[0]['score']['original']['final']['value'],0.9)
        eq(records[0]['score']['final']['value'],1.0)
        assert records[0]['rescore']['inference_rerun'] is False
        assert Path(jp).exists() and Path(cp).exists() and Path(sj).exists() and Path(sc).exists()
        rows=json.loads(Path(sj).read_text(encoding='utf-8'))
        eq(rows[0]['rescore_source'],'legacy_raw')
        assert rows[0]['inference_rerun'] is False
    finally:
        mod.benchmark_dir=old_dir
        mod.stream_chat=old_stream
        shutil.rmtree(root,ignore_errors=True)




def test_instruction_v4_runs_native_fast_inside_think_suite():
    class Sampler:
        def start(self): return self
        def stop(self): return {'samples':1,'vram_peak_mib':1000}

    old_sampler=mod.GpuSampler
    old_stream=mod.stream_chat
    old_rt=mod._runtime_telemetry
    old_digest=mod.model_digest
    try:
        mod.GpuSampler=Sampler
        mod._runtime_telemetry=lambda model:{'gpu_offload_pct':50,'context_length':8192}
        mod.model_digest=lambda model,catalog=None:'digest'

        cfg={
            'model':'x','think':True,'think_value':True,
            'num_ctx':8192,'num_thread':12,'num_predict':3200,
            'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42
        }
        item=mod.builtin_benchmarks()['instruction']
        calls=[]
        answer=(
            '1. Преимущество: данные остаются на локальном компьютере.\n'
            '2. Преимущество: работа не зависит от подключения к внешнему сервису.\n'
            '3. Преимущество: настройки можно менять под собственные задачи.\n'
            '4. Риск: слабое оборудование может снижать скорость обработки.'
        )
        def fake_stream(msgs,cfg,show_thinking=True,think_override=None,
                        predict_override=None,tools=None,response_format=None,silent=False):
            calls.append({
                'think':think_override,
                'temperature':cfg.get('temperature'),
                'top_p':cfg.get('top_p'),
                'top_k':cfg.get('top_k'),
                'min_p':cfg.get('min_p'),
            })
            return answer,'', {
                'done_reason':'stop','eval_count':90,'eval_duration':1_000_000_000,
                'prompt_eval_count':100,'prompt_eval_duration':1_000_000_000
            }
        mod.stream_chat=fake_stream
        r=mod.benchmark_record(
            'instruction',item,cfg,True,1,1,
            bench_mode='client',catalog={'x':{'digest':'digest'}}
        )
        eq(len(calls),1)
        assert calls[0]['think'] is False
        eq(calls[0]['temperature'],mod.FAST['temperature'])
        eq(calls[0]['top_p'],mod.FAST['top_p'])
        eq(calls[0]['top_k'],mod.FAST['top_k'])
        eq(calls[0]['min_p'],mod.FAST['min_p'])
        eq(r['config']['suite_think'],True)
        assert r['config']['think'] is False
        eq(r['config']['primary_mode'],'fast')
        assert r['config']['think_override'] is False
        assert r['primary']['completed'] is True
        assert r['recovery']['used'] is False
        eq(r['score']['final']['value'],1.0)
    finally:
        mod.GpuSampler=old_sampler
        mod.stream_chat=old_stream
        mod._runtime_telemetry=old_rt
        mod.model_digest=old_digest


def test_recovery_preserves_exact_format_and_conditional_result_marker():
    old_stream=mod.stream_chat
    calls=[]
    try:
        def fake_stream(msgs,cfg,show_thinking=True,think_override=None,
                        predict_override=None,tools=None,response_format=None,silent=False):
            payload='\n'.join(str(m.get('content','')) for m in msgs)
            calls.append(payload)
            return 'ok','',{'done_reason':'stop'}
        mod.stream_chat=fake_stream

        base=[{'role':'user','content':'Исходное задание'}]
        cfg={'model':'x','seed':42}

        item_no={
            'recovery_predict':800,
            'max_words':None,
            'result_instruction':'',
        }
        r=mod._benchmark_recovery(base,cfg,item_no,'reasoning')
        eq(r['strategy'],'continue_then_targeted_rescue_v3')
        assert r['result_marker_required'] is False
        assert 'Строго сохрани ВСЕ требования' in calls[-1]
        assert 'не требует BENCHMARK_RESULT' in calls[-1]

        item_yes={
            'recovery_predict':800,
            'max_words':300,
            'result_instruction':'BENCHMARK_RESULT + JSON',
        }
        r2=mod._benchmark_recovery(base,cfg,item_yes,'reasoning')
        assert r2['result_marker_required'] is True
        assert 'требует BENCHMARK_RESULT' in calls[-1]
        assert 'после JSON ничего не пиши' in calls[-1]
    finally:
        mod.stream_chat=old_stream


def test_rescue_preserves_format_and_continues_failed_partial():
    old_stream=mod.stream_chat
    calls=[]
    try:
        def fake_stream(msgs,cfg,show_thinking=True,think_override=None,
                        predict_override=None,tools=None,response_format=None,silent=False):
            payload='\n'.join(str(m.get('content','')) for m in msgs)
            calls.append(payload)
            if len(calls)==1:
                return 'FAILED_RECOVERY_SENTINEL','',{'done_reason':'length'}
            return 'done','',{'done_reason':'stop'}
        mod.stream_chat=fake_stream
        item={'recovery_predict':800,'max_words':None,'result_instruction':''}
        r=mod._benchmark_recovery(
            [{'role':'user','content':'Ровно четыре строки с обязательными префиксами'}],
            {'model':'x','seed':42},
            item,
            'PRIMARY_REASONING_SENTINEL'
        )
        eq(len(calls),2)
        assert 'FAILED_RECOVERY_SENTINEL' in calls[1]
        assert 'Строго сохрани ВСЕ требования' in calls[1]
        assert 'не требует BENCHMARK_RESULT' in calls[1]
        assert r['completed'] is True
    finally:
        mod.stream_chat=old_stream


def test_checkpoint_fingerprints_instruction_execution_policy():
    old_profile=mod.model_profile
    old_norm=mod.normalize_think_value
    old_load=mod.load_benchmarks
    try:
        profile={
            'ctx':8192,'threads':12,
            'fast':{'temperature':0.2,'top_p':0.85,'top_k':40,'min_p':0.05,'seed':42,'num_predict':512},
            'think':{'temperature':1.0,'top_p':0.95,'top_k':20,'min_p':0.0,'seed':42,'num_predict':3200},
        }
        mod.model_profile=lambda name:profile
        mod.normalize_think_value=lambda name,v:(v,None)
        built=mod.builtin_benchmarks()
        item=dict(built['instruction'])
        fp=mod.benchmark_test_profile_fingerprint('m',item,True,'native')
        exec_fp=mod.benchmark_test_execution_fingerprint(item)
        assert re.fullmatch(r'[0-9a-f]{64}',fp)
        assert re.fullmatch(r'[0-9a-f]{64}',exec_fp)

        cp={
            'spec':{
                'client_version':mod.APP_VERSION,
                'think_value':True,'mode':'native',
                'test_fingerprints':{
                    'instruction':{
                        'version':item['version'],
                        'prompt_sha256':mod.benchmark_prompt_sha256(item),
                        'execution_sha256':exec_fp,
                        'think_override':False,
                    }
                },
                'model_digests':{},
                'model_profile_fingerprints':{},
                'model_test_profile_fingerprints':{'m':{'instruction':fp}},
            },
            'records':{},
        }
        mod.load_benchmarks=lambda:{'instruction':item}
        eq(mod.validate_checkpoint_environment(cp,{'m':{'name':'m','digest':''}},False),[])

        changed=dict(item); changed['think_override']=True
        mod.load_benchmarks=lambda:{'instruction':changed}
        try:
            mod.validate_checkpoint_environment(cp,{'m':{'name':'m','digest':''}},False)
        except RuntimeError as e:
            assert 'test execution policy changed: instruction' in str(e)
        else:
            raise AssertionError('instruction execution policy change not detected')
    finally:
        mod.model_profile=old_profile
        mod.normalize_think_value=old_norm
        mod.load_benchmarks=old_load


def test_rescore_instruction_v3_remains_supported():
    answer=(
        '1. Преимущество: данные остаются на локальном компьютере.\n'
        '2. Преимущество: работа не зависит от внешнего сервиса.\n'
        '3. Преимущество: настройки можно менять самостоятельно.\n'
        '4. Риск: слабое оборудование может снижать скорость.'
    )
    score=mod._legacy_rescore_one('instruction',3,answer)
    eq(score['method'],'instruction_v3')
    eq(score['value'],1.0)




def analytics_gold_answer(plot_metric='arpu',bad_stats=False,bad_sql=False):
    sql="""WITH ranked AS (
    SELECT order_id, user_id, order_time, amount, status, updated_at,
           ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC) AS rn
    FROM orders_raw%s
), valid_orders AS (
    SELECT order_id, user_id, amount
    FROM ranked
    WHERE rn = 1
      AND status = 'paid'
      AND order_time >= '2026-07-01 00:00:00'
      AND order_time < '2026-08-01 00:00:00'
), user_revenue AS (
    SELECT user_id, SUM(amount) AS revenue FROM valid_orders GROUP BY user_id
), user_level AS (
    SELECT u.user_id, u.variant, COALESCE(r.revenue, 0) AS revenue,
           CASE WHEN COALESCE(r.revenue, 0) > 0 THEN 1 ELSE 0 END AS purchaser
    FROM users u LEFT JOIN user_revenue r ON u.user_id = r.user_id
)
SELECT variant, COUNT(*) AS users, SUM(purchaser) AS purchasers,
       1.0 * SUM(purchaser) / COUNT(*) AS conversion,
       SUM(revenue) AS revenue, 1.0 * SUM(revenue) / COUNT(*) AS arpu,
       CASE WHEN SUM(purchaser) > 0 THEN 1.0 * SUM(revenue) / SUM(purchaser) END AS arppu
FROM user_level GROUP BY variant ORDER BY variant""" % (" WHERE status='paid'" if bad_sql else '')

    stat_line=(
        "stats={'conversion_diff':0.25,'z_stat':0.0,'z_p_value':1.0,'ci_low':-0.1,'ci_high':0.6,'arpu_diff':8.333333333333336,'welch_t':0.0,'welch_p':1.0}"
        if bad_stats else
        "stats={'conversion_diff':float(diff),'z_stat':float(z),'z_p_value':float(z_p),'ci_low':float(ci[0]),'ci_high':float(ci[1]),'arpu_diff':float(br.mean()-ar.mean()),'welch_t':float(welch.statistic),'welch_p':float(welch.pvalue)}"
    )
    py=f"""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm, ttest_ind

def analyze_ab(users, orders):
    o=orders.copy(); o['order_time']=pd.to_datetime(o['order_time']); o['updated_at']=pd.to_datetime(o['updated_at'])
    o=o.sort_values(['order_id','updated_at']).drop_duplicates('order_id',keep='last')
    o=o[(o['status'].eq('paid')) & (o['order_time']>=pd.Timestamp('2026-07-01')) & (o['order_time']<pd.Timestamp('2026-08-01'))]
    rev=o.groupby('user_id',as_index=False)['amount'].sum().rename(columns={{'amount':'revenue'}})
    ul=users[['user_id','variant']].merge(rev,on='user_id',how='left'); ul['revenue']=ul['revenue'].fillna(0.0); ul['purchaser']=(ul['revenue']>0).astype(int)
    metrics=ul.groupby('variant',as_index=False).agg(users=('user_id','size'),purchasers=('purchaser','sum'),revenue=('revenue','sum'))
    metrics['conversion']=metrics['purchasers']/metrics['users']; metrics['arpu']=metrics['revenue']/metrics['users']; metrics['arppu']=metrics['revenue']/metrics['purchasers']
    metrics=metrics[['variant','users','purchasers','conversion','revenue','arpu','arppu']]
    x=metrics.set_index('variant'); a=x.loc['A']; b=x.loc['B']; diff=b.conversion-a.conversion
    pool=(a.purchasers+b.purchasers)/(a.users+b.users); se=np.sqrt(pool*(1-pool)*(1/a.users+1/b.users)); z=diff/se; z_p=2*norm.sf(abs(z))
    seu=np.sqrt(a.conversion*(1-a.conversion)/a.users+b.conversion*(1-b.conversion)/b.users); ci=(diff-1.96*seu,diff+1.96*seu)
    ar=ul.loc[ul.variant.eq('A'),'revenue'].to_numpy(float); br=ul.loc[ul.variant.eq('B'),'revenue'].to_numpy(float); welch=ttest_ind(br,ar,equal_var=False)
    {stat_line}
    fig,axes=plt.subplots(1,2); axes[0].bar(['A','B'],x.loc[['A','B'],'conversion']); axes[1].bar(['A','B'],x.loc[['A','B'],'{plot_metric}'])
    return metrics,stats,fig"""
    obj={
        'dedupe_latest':True,'latest_status_paid_only':True,'half_open_july_window':True,
        'user_level_conversion':True,'zero_revenue_users_in_denominator':True,
        'conversion_diff':0.25,'z_stat':1.2290197355980537,'z_p_value':0.21906440661100834,
        'ci_low':-0.1359416094772964,'ci_high':0.6359416094772963,
        'arpu_diff':8.333333333333336,'welch_t':0.4394519058191579,'welch_p':0.6649329866857383,
        'decision':'inconclusive'
    }
    return (
        'Ловушки: дедупликация перед статусом, полуоткрытое окно, user grain и нулевые пользователи.\n\n'
        +'```sql\n'+sql+'\n```\n\n```python\n'+py+'\n```\n\n'
        +'B выше по conversion и ARPU, A выше по ARPPU. Оба теста незначимы, CI включает ноль, вывод inconclusive.\n\n'
        +'BENCHMARK_RESULT\n'+json.dumps(obj,ensure_ascii=False)
    )


def test_analytics_case_gold_is_exact_and_executable():
    item=mod.builtin_benchmarks()['analytics_case']
    score=mod.benchmark_score('analytics_case',item,analytics_gold_answer())
    eq(score['method'],'analytics_case_v3')
    eq(score['value'],1.0)
    assert score['sql_result_valid'] is True
    assert score['python_metrics_valid'] is True
    assert score['python_stats_valid'] is True
    assert score['figure_valid'] is True
    assert score['core_result_valid'] is True


def _replace_analytics_python(answer,replacement):
    code,error=mod._analytics_python_block(answer)
    assert error is None and code
    old='```python\n'+code+'\n```'
    assert old in answer
    return answer.replace(old,'```python\n'+replacement.strip()+'\n```',1)


def test_analytics_case_accepts_semantic_argument_names():
    item=mod.builtin_benchmarks()['analytics_case']
    answer=analytics_gold_answer()
    code,error=mod._analytics_python_block(answer)
    assert error is None
    class RenameInputs(ast.NodeTransformer):
        names={'users':'users_df','orders':'orders_df'}
        def visit_arg(self,node):
            node.arg=self.names.get(node.arg,node.arg)
            return node
        def visit_Name(self,node):
            node.id=self.names.get(node.id,node.id)
            return node
    tree=RenameInputs().visit(ast.parse(code)); ast.fix_missing_locations(tree)
    code=ast.unparse(tree)
    score=mod.benchmark_score('analytics_case',item,_replace_analytics_python(answer,code))
    eq(score['value'],1.0)
    assert score['execution']['python_safe'] is True


def test_analytics_case_scores_sql_when_python_runtime_fails():
    item=mod.builtin_benchmarks()['analytics_case']
    broken='''
def analyze_ab(users_df, orders_df):
    if users_df is orders_df:
        pass
    raise ValueError("synthetic runtime failure")
'''
    answer=_replace_analytics_python(analytics_gold_answer(),broken)
    score=mod.benchmark_score('analytics_case',item,answer)
    eq(score['execution']['status'],'partial')
    assert score['sql_result_valid'] is True
    assert score['python_metrics_valid'] is False
    assert score['value']>=0.22
    sql_check=[c for c in score['checks'] if c['name'].startswith('SQL executes')][0]
    assert sql_check['ok'] is True


def test_analytics_case_wrong_dedupe_sql_is_capped():
    item=mod.builtin_benchmarks()['analytics_case']
    score=mod.benchmark_score('analytics_case',item,analytics_gold_answer(bad_sql=True))
    assert score['sql_result_valid'] is False
    assert score['value']<=0.60
    eq(score['cap_applied'],'core_sql_python_stats_not_verified_max_60pct')


def test_analytics_case_wrong_stats_is_capped():
    item=mod.builtin_benchmarks()['analytics_case']
    score=mod.benchmark_score('analytics_case',item,analytics_gold_answer(bad_stats=True))
    assert score['sql_result_valid'] is True
    assert score['python_metrics_valid'] is True
    assert score['python_stats_valid'] is False
    assert score['value']<=0.60


def test_analytics_case_wrong_plot_loses_visualization_points_only():
    item=mod.builtin_benchmarks()['analytics_case']
    score=mod.benchmark_score('analytics_case',item,analytics_gold_answer(plot_metric='arppu'))
    assert score['core_result_valid'] is True
    assert score['figure_valid'] is False
    assert abs(score['value']-0.90)<1e-9


def test_all_builtins_have_reference_without_prompt_leakage():
    built=mod.builtin_benchmarks()
    assert set(built)=={
        'simpson','funnel','retention_d7','analytics_case','instruction',
        'python_debug','logic_constraints','dialogue_state','russian_editing','groundedness','groundedness_adversarial',
        'ru_context_corrections','ru_causality_precision','ru_semantic_negation',
        'ru_business_tone','ru_debureaucratize',
    }
    for name,item in built.items():
        assert item.get('reference') is not None,name
        assert re.fullmatch(r'[0-9a-f]{64}',mod.benchmark_reference_sha256(item)),name
        ref_blob=json.dumps(item['reference'],ensure_ascii=False,sort_keys=True,separators=(',',':'))
        assert ref_blob not in mod.benchmark_effective_prompt(item)


def test_analytics_reference_values_and_preflight():
    ref=mod.builtin_benchmarks()['analytics_case']['reference']
    a,b=ref['metrics']
    eq((a['users'],a['purchasers'],a['revenue']),(12,5,500.0))
    eq((b['users'],b['purchasers'],b['revenue']),(12,8,600.0))
    assert abs(ref['conversion_diff']-.25)<1e-12
    assert abs(ref['z_p_value']-0.21906440661100834)<1e-12
    assert abs(ref['welch_p']-0.6649329866857383)<1e-12
    eq(ref['decision'],'inconclusive')
    ok,info=mod.benchmark_scorer_preflight(['analytics_case'],mod.builtin_benchmarks())
    assert ok,(ok,info)


def test_backend_settings_roundtrip_and_validation():
    td=Path(tempfile.mkdtemp())
    old=mod.backend_settings_path
    try:
        mod.backend_settings_path=lambda:td/'backend_settings.json'
        st=mod.load_backend_settings(); eq(st['active'],'ollama')
        mod.save_backend_settings(st)
        eq(mod.set_llama_setting('flash_attn','on'),'on')
        eq(mod.set_llama_setting('spec_draft_n_max','4'),4)
        eq(mod.load_backend_settings()['llama_cpp']['flash_attn'],'on')
        try: mod.set_llama_setting('flash_attn','maybe')
        except ValueError: pass
        else: raise AssertionError('invalid flash_attn accepted')
    finally:
        mod.backend_settings_path=old; shutil.rmtree(td,ignore_errors=True)


def test_llama_request_mapping_think_and_fast():
    old=mod.llama_settings
    mod.llama_settings=lambda:{'reasoning_format':'deepseek'}
    try:
        cfg={'model':'m.gguf','num_predict':123,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42}
        think=mod._llama_request_from_cfg([{'role':'user','content':'x'}],cfg,True,123,stream=True)
        assert think['chat_template_kwargs']['enable_thinking'] is True
        assert 'reasoning_effort' not in think
        eq(think['model'],'m.gguf'); eq(think['max_tokens'],123); eq(think['top_k'],40)
        fast=mod._llama_request_from_cfg([{'role':'user','content':'x'}],cfg,False,123,stream=True)
        assert fast['chat_template_kwargs']['enable_thinking'] is False
        eq(fast['reasoning_effort'],'none')
    finally: mod.llama_settings=old


def test_llama_timings_and_draft_acceptance_mapping():
    data={'choices':[{'finish_reason':'stop'}], 'usage':{'prompt_tokens':100,'completion_tokens':50},
          'timings':{'prompt_ms':200,'predicted_ms':1000,'draft_n':40,'draft_n_accepted':30}}
    meta=mod._llama_meta_from_response(data,mod.time.time()-1)
    eq(meta['prompt_eval_count'],100); eq(meta['eval_count'],50); eq(meta['done_reason'],'stop')
    eq(meta['_draft_n'],40); eq(meta['_draft_n_accepted'],30); assert abs(meta['_draft_acceptance']-.75)<1e-12


def test_llama_router_model_catalog_parse():
    old=mod.llama_api_get
    mod.llama_api_get=lambda path,timeout=12:{'data':[{
        'id':'Qwen-Test-IQ2_M.gguf','path':'C:/Models/Qwen-Test-IQ2_M.gguf','status':{'value':'unloaded'},
        'meta':{'size':123456,'n_params':27_000_000_000,'architecture':'qwen'},
        'architecture':{'input_modalities':['text']}
    }]}
    try:
        rows=mod.llama_installed_models(); eq(len(rows),1); r=rows[0]
        eq(r['name'],'Qwen-Test-IQ2_M.gguf'); eq(r['status'],'unloaded'); eq(r['parameter_size'],'27.0B')
        assert r['digest_kind']=='router_metadata' and len(r['digest'])==64
    finally: mod.llama_api_get=old


def test_llama_sse_stream_parser():
    class Resp:
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def __iter__(self):
            rows=[
                {'choices':[{'delta':{'reasoning_content':'мысль '}}]},
                {'choices':[{'delta':{'content':'ответ'},'finish_reason':'stop'}]},
                {'choices':[],'usage':{'prompt_tokens':7,'completion_tokens':3},'timings':{'prompt_ms':10,'predicted_ms':20,'draft_n':2,'draft_n_accepted':1}},
            ]
            for x in rows: yield ('data: '+json.dumps(x)+'\n').encode()
            yield b'data: [DONE]\n'
    old_post,old_settings,old_ensure=mod.llama_api_post,mod.llama_settings,mod.ensure_llama_runtime
    mod.llama_api_post=lambda *a,**k:Resp(); mod.llama_settings=lambda:{'reasoning_format':'deepseek'}; mod.ensure_llama_runtime=lambda:None
    try:
        cfg={'model':'m','num_predict':10,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42,'think_value':True}
        ans,th,meta=mod._llama_stream_chat([{'role':'user','content':'x'}],cfg,silent=True)
        eq(ans,'ответ'); eq(th,'мысль '); eq(meta['eval_count'],3); eq(meta['_draft_acceptance'],.5)
    finally:
        mod.llama_api_post,mod.llama_settings,mod.ensure_llama_runtime=old_post,old_settings,old_ensure


def test_benchmark_spec_contains_backend_and_reference_provenance():
    old_backend=mod.ACTIVE_BACKEND; old_fp=mod.backend_runtime_fingerprint; old_prof=mod.model_profile; old_digest=mod.model_digest
    try:
        mod.ACTIVE_BACKEND='llama_cpp'; mod.backend_runtime_fingerprint=lambda:'b'*64
        mod.model_profile=lambda name:{'ctx':8192,'threads':12,'fast':{'num_predict':512,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42},'think':{'num_predict':3200,'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42}}
        mod.model_digest=lambda name,catalog=None:'d'*64
        spec=mod.make_benchmark_spec(['analytics_case'],['m'],1,True,'native','fixed','x',catalog={'m':{'name':'m','digest':'d'*64}})
        eq(spec['backend'],'llama_cpp'); eq(spec['backend_runtime_fingerprint'],'b'*64)
        eq(spec['resume_environment_fingerprint'],'b'*64)
        eq(spec['suite_launch_fingerprint'],'b'*64)
        fp=spec['test_fingerprints']['analytics_case']; assert fp['reference_sha256']==mod.benchmark_reference_sha256(mod.builtin_benchmarks()['analytics_case'])
        assert re.fullmatch(r'[0-9a-f]{64}',fp['scorer_sha256'])
        assert re.fullmatch(r'[0-9a-f]{64}',fp['verifier_sha256'])
        eq(fp['verifier_ref'],'benchmark_contract_v1')
    finally:
        mod.ACTIVE_BACKEND=old_backend; mod.backend_runtime_fingerprint=old_fp; mod.model_profile=old_prof; mod.model_digest=old_digest



def test_llama_response_format_schema_mapping():
    raw={'type':'object','properties':{'x':{'type':'integer'}},'required':['x']}
    eq(mod._llama_response_format(raw),{'type':'json_object','schema':raw})
    shorthand={'type':'json_schema','schema':raw}
    got=mod._llama_response_format(shorthand)
    eq(got['type'],'json_schema')
    eq(got['schema'],raw)
    openai_style={'type':'json_schema','json_schema':{'name':'x','strict':True,'schema':raw}}
    eq(mod._llama_response_format(openai_style),{'type':'json_schema','schema':raw})


def test_llama_sse_preserves_length_and_merges_tool_fragments():
    class Resp:
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def __iter__(self):
            rows=[
                {'choices':[{'delta':{'tool_calls':[{'index':0,'id':'call_1','type':'function','function':{'name':'read_','arguments':'{"pa'}}]}}]},
                {'choices':[{'delta':{'tool_calls':[{'index':0,'function':{'name':'text_file','arguments':'th":"a.txt"}'}}]},'finish_reason':'length'}]},
                {'choices':[],'usage':{'prompt_tokens':11,'completion_tokens':9},'timings':{'prompt_ms':12,'predicted_ms':30}},
            ]
            for x in rows:
                yield ('data: '+json.dumps(x)+'\n').encode()
            yield b'data: [DONE]\n'
    old_post,old_settings,old_ensure=mod.llama_api_post,mod.llama_settings,mod.ensure_llama_runtime
    mod.llama_api_post=lambda *a,**k:Resp()
    mod.llama_settings=lambda:{'reasoning_format':'deepseek'}
    mod.ensure_llama_runtime=lambda:None
    try:
        cfg={'model':'m','num_predict':10,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42,'think_value':False}
        ans,th,meta=mod._llama_stream_chat([{'role':'user','content':'x'}],cfg,silent=True)
        eq(meta['done_reason'],'length')
        eq(meta['eval_count'],9)
        calls=meta['_tool_calls']; eq(len(calls),1)
        eq(calls[0]['id'],'call_1')
        eq(calls[0]['function']['name'],'read_text_file')
        eq(calls[0]['function']['arguments'],'{"path":"a.txt"}')
    finally:
        mod.llama_api_post,mod.llama_settings,mod.ensure_llama_runtime=old_post,old_settings,old_ensure


def test_llama_message_conversion_tool_and_reasoning():
    msgs=[
        {'role':'assistant','content':'','thinking':'мысль','tool_calls':[{'id':'c1','type':'function','function':{'name':'calculator','arguments':'{}'}}]},
        {'role':'tool','tool_call_id':'c1','tool_name':'calculator','content':'42'},
    ]
    out=mod._llama_convert_messages(msgs)
    eq(out[0]['reasoning_content'],'мысль')
    assert 'thinking' not in out[0]
    eq(out[1]['tool_call_id'],'c1')
    assert 'tool_name' not in out[1]


def test_analytics_case_rejects_trivial_hardcoded_code_shapes():
    sql="SELECT 'A' AS variant, 12 AS users, 5 AS purchasers, 0.4166666667 AS conversion, 500 AS revenue, 41.6666667 AS arpu, 100 AS arppu UNION ALL SELECT 'B',12,8,0.6666666667,600,50,75"
    safe,reason=mod._analytics_sql_safety(sql)
    assert safe is False
    assert str(reason).startswith('required_sql_semantics_missing:')

    code=(
        "def analyze_ab(users, orders):\n"
        "    import pandas as pd\n"
        "    import matplotlib.pyplot as plt\n"
        "    metrics=pd.DataFrame([])\n"
        "    return metrics, {}, plt.figure()\n"
    )
    safe2,reason2=mod._analytics_python_safety(code)
    assert safe2 is False
    assert reason2 in ('analyze_ab_input_not_used:users','analyze_ab_input_not_used:orders')


def test_summary_separates_backends_and_records_reference_hash():
    def rec(backend):
        return {
            'record_schema_version':5,'execution_status':'ok','completion_status':'completed',
            'identity':{
                'benchmark':'x','benchmark_version':1,'benchmark_prompt_sha256':'p',
                'benchmark_reference_sha256':'r','model':'same','model_digest':'d','backend':backend,'run':1,
            },
            'config':{'benchmark_mode':'client','seed_mode':'fixed','seed':42,'backend':backend},
            'primary':{'completed':True,'eval_rate':10.0},'recovery':{'used':False},
            'final':{'completed':True,'done_reason':'stop','pipeline_wall_seconds':1.0},
            'score':{'native':{'value':1.0},'final':{'value':1.0},'partial':None},
            'telemetry':{'gpu':{},'runtime':{}},
        }
    rows=mod.benchmark_summary_rows([rec('ollama'),rec('llama_cpp')])
    eq(len(rows),2)
    eq({r['backend'] for r in rows},{'ollama','llama_cpp'})
    assert all(r['benchmark_reference_sha256']=='r' for r in rows)
    assert all(r['summary_schema_version']==11 for r in rows)


def test_llama_setting_extended_validation():
    root=Path(tempfile.mkdtemp())
    old_path=mod.backend_settings_path
    try:
        mod.backend_settings_path=lambda:root/'backend_settings.json'
        eq(mod.set_llama_setting('n_gpu_layers','all'),'all')
        eq(mod.set_llama_setting('models_max','0'),0)
        eq(mod.set_llama_setting('reasoning_budget','-1'),-1)
        eq(mod.set_llama_setting('extra_args','["--no-mmap","--mlock"]'),['--no-mmap','--mlock'])
        args=mod._llama_server_args(mod.llama_settings())
        assert '--reasoning-format' in args and '--reasoning-budget' in args
        eq(args[args.index('--models-max')+1],'0')
        eq(args[args.index('--reasoning-budget')+1],'-1')
        try:
            mod.set_llama_setting('local_port','70000')
        except ValueError:
            pass
        else:
            raise AssertionError('invalid port accepted')
        try:
            mod.set_llama_setting('n_gpu_layers','invalid')
        except ValueError:
            pass
        else:
            raise AssertionError('invalid n_gpu_layers accepted')
        for raw in ('["--host=0.0.0.0"]','["--api-key","secret"]','["--agent"]'):
            try:
                mod.set_llama_setting('extra_args',raw)
            except ValueError:
                pass
            else:
                raise AssertionError('unsafe extra_args accepted: '+raw)
    finally:
        mod.backend_settings_path=old_path
        shutil.rmtree(root,ignore_errors=True)



def test_ultimate_profile_and_cfg_exist():
    prof=mod.model_profile('model-without-explicit-profile')
    assert 'ultimate' in prof
    eq(prof['ultimate']['num_predict'],5000)
    cfg=mod.make_cfg('ultimate',True)
    eq(cfg['run_mode'],'ultimate')
    assert cfg['think'] is True
    eq(cfg['num_predict'],5000)


def test_ultimate_continues_reasoning_until_answer_without_total_cycle_cap():
    old=mod.stream_chat
    calls=[]
    responses=[]
    # More than the old short continuation limits: seven unfinished reasoning chunks, then answer.
    for i in range(7):
        responses.append(('',f'reasoning progress {i} unique checkpoint {i}',{'done_reason':'length','eval_count':5000,'eval_duration':1_000_000_000}))
    responses.append(('Готовый ответ.','final reasoning',{'done_reason':'stop','eval_count':80,'eval_duration':1_000_000_000}))
    it=iter(responses)
    def fake(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,tools=None,response_format=None,silent=False,progress=None):
        calls.append({'msgs':msgs,'think_override':think_override,'cfg':dict(cfg)})
        return next(it)
    mod.stream_chat=fake
    try:
        ans,th,meta=mod.ultimate_chat(
            [{'role':'user','content':'Реши сложную задачу'}],
            mod.make_cfg('ultimate',True),False,
            {'tools_mode':'off','response_format':None},silent=True
        )
        eq(ans,'Готовый ответ.')
        eq(meta['_ultimate_cycles'],8)
        eq(meta['_ultimate_stop'],'completed')
        assert all(c['cfg'].get('run_mode')=='ultimate' for c in calls)
        assert 'reasoning progress 6' in th
    finally:
        mod.stream_chat=old


def test_ultimate_final_length_continues_without_new_think():
    old=mod.stream_chat
    calls=[]
    seq=iter([
        ('Начало ответа','длинное reasoning',{'done_reason':'length','eval_count':5000,'eval_duration':1_000_000_000}),
        (' и завершение.','',{'done_reason':'stop','eval_count':60,'eval_duration':1_000_000_000}),
    ])
    def fake(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,tools=None,response_format=None,silent=False,progress=None):
        calls.append({'think_override':think_override,'msgs':msgs})
        return next(seq)
    mod.stream_chat=fake
    try:
        ans,th,meta=mod.ultimate_chat(
            [{'role':'user','content':'Задача'}],mod.make_cfg('ultimate',True),False,
            {'tools_mode':'off','response_format':None},silent=True
        )
        eq(ans,'Начало ответа и завершение.')
        eq(meta['_ultimate_cycles'],1)
        eq(meta['_ultimate_final_continuations'],1)
        assert calls[1]['think_override'] is False
        assert 'ULTIMATE: финальный ответ уже начат' in calls[1]['msgs'][-1]['content']
    finally:
        mod.stream_chat=old


def test_ultimate_tool_work_can_exceed_normal_tool_loop_limit():
    old_stream=mod.stream_chat
    old_exec=mod.execute_tool_call
    calls=[]
    count={'n':0}
    def fake_stream(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,tools=None,response_format=None,silent=False,progress=None):
        calls.append(msgs)
        count['n']+=1
        if count['n']<=7:
            return '',f'tool reasoning {count["n"]}',{
                'done_reason':'stop',
                '_tool_calls':[{'id':f'c{count["n"]}','type':'function','function':{'name':'calculator','arguments':json.dumps({'expression':f'{count["n"]}+1'})}}]
            }
        return 'После инструментов задача решена.','',{'done_reason':'stop'}
    mod.stream_chat=fake_stream
    mod.execute_tool_call=lambda call,mode:'2'
    try:
        ans,th,meta=mod.ultimate_chat(
            [{'role':'user','content':'Используй инструменты пока не решишь'}],mod.make_cfg('ultimate',True),False,
            {'tools_mode':'safe','response_format':None},silent=True
        )
        eq(ans,'После инструментов задача решена.')
        eq(meta['_ultimate_tool_loops'],7)
        assert meta['_ultimate_tool_loops']>mod.TOOL_MAX_LOOPS
        eq(meta['_ultimate_stop'],'completed')
    finally:
        mod.stream_chat=old_stream
        mod.execute_tool_call=old_exec


def test_ultimate_session_roundtrip_preserves_mode():
    root=Path(tempfile.mkdtemp())
    try:
        path=root/'u.json'
        session=mod.new_session_meta('m')
        session['run_mode']='ultimate'; session['think_value']=True; session['reasoning_visible']=True
        mod.save_session(path,'ultimate',[{'role':'user','content':'x'}],'',[],{},session)
        loaded=mod.read_session(path)
        eq(loaded['mode'],'ultimate')
        eq(loaded['session']['run_mode'],'ultimate')
        assert loaded['session']['think_value'] is True
        assert loaded['session']['reasoning_visible'] is True
    finally:
        shutil.rmtree(root,ignore_errors=True)



def test_benchmark_capability_fallback_think_to_fast():
    old=mod.cached_model_capabilities
    try:
        item=mod.builtin_benchmarks()['analytics_case']
        mod.cached_model_capabilities=lambda model_name,refresh=False:['completion','tools']
        p=mod.benchmark_reasoning_policy('nonthink-model',item,True)
        assert p['requested'] is True
        assert p['actual'] is False
        eq(p['mode'],'fast')
        eq(p['reason'],'model_no_thinking_capability')

        mod.cached_model_capabilities=lambda model_name,refresh=False:['completion','tools','thinking']
        p2=mod.benchmark_reasoning_policy('think-model',item,True)
        assert p2['actual'] is True
        eq(p2['mode'],'think')

        instruction=mod.builtin_benchmarks()['instruction']
        p3=mod.benchmark_reasoning_policy('think-model',instruction,True)
        assert p3['actual'] is False
        eq(p3['mode'],'fast')
    finally:
        mod.cached_model_capabilities=old


def test_benchmark_record_provenance_for_nonthinking_model():
    class Sampler:
        def start(self): return self
        def latest(self): return {'gpu_util':50,'vram_used_mib':1000,'vram_total_mib':12000,'gpu_temp':55}
        def stop(self): return {'samples':1,'vram_peak_mib':1000}

    old_caps=mod.cached_model_capabilities
    old_stream=mod.stream_chat
    old_sampler=mod.GpuSampler
    old_rt=mod._runtime_telemetry
    old_digest=mod.model_digest
    try:
        mod.cached_model_capabilities=lambda model_name,refresh=False:['completion','tools']
        mod.GpuSampler=Sampler
        mod._runtime_telemetry=lambda model:{'context_length':8192}
        mod.model_digest=lambda model,catalog=None:'digest'
        calls=[]
        answer='1. Преимущество: локально.\n2. Преимущество: быстро.\n3. Преимущество: гибко.\n4. Риск: оборудование может замедлить работу.'
        def fake(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,tools=None,response_format=None,silent=False,progress=None):
            calls.append((think_override,cfg['temperature'],cfg['top_p'],cfg['top_k']))
            return answer,'',{'done_reason':'stop','eval_count':50,'eval_duration':1_000_000_000}
        mod.stream_chat=fake
        item=dict(mod.builtin_benchmarks()['instruction'])
        item.pop('think_override',None)
        r=mod.benchmark_record(
            'instruction',item,
            {'model':'x','seed':42,'think':True,'think_value':True},
            True,1,1,bench_mode='native',catalog={'x':{'digest':'digest'}}
        )
        assert calls and calls[0][0] is False
        eq(r['config']['think_requested'],True)
        assert r['config']['think'] is False
        eq(r['config']['primary_mode'],'fast')
        eq(r['config']['reasoning_mode_reason'],'model_no_thinking_capability')
        assert 'thinking' not in r['config']['model_capabilities']
        assert re.fullmatch(r'[0-9a-f]{64}',r['identity']['scorer_sha256'])
        assert re.fullmatch(r'[0-9a-f]{64}',r['identity']['verifier_sha256'])
        eq(r['identity']['scorer_ref'],'instruction_v4')
        eq(r['identity']['verifier_ref'],'benchmark_contract_v1')
    finally:
        mod.cached_model_capabilities=old_caps
        mod.stream_chat=old_stream
        mod.GpuSampler=old_sampler
        mod._runtime_telemetry=old_rt
        mod.model_digest=old_digest


def test_qwen3_coder_next_profile_uses_official_nonthink_sampling():
    p=mod.model_profile('qwen3-coder-next-80b-iq2m-8k:latest')
    eq(p['fast']['temperature'],1.0)
    eq(p['fast']['top_p'],0.95)
    eq(p['fast']['top_k'],40)
    eq(p['fast']['min_p'],0.0)
    eq(p['ctx'],8192)
    eq(p['threads'],12)


def test_live_progress_renders_heartbeat_and_gpu():
    class S:
        def latest(self):
            return {
                'gpu_util':82,'vram_used_mib':10186,'vram_total_mib':12288,'gpu_temp':52,
                'cpu_util':37,'ram_used_bytes':12*1024**3,'ram_total_bytes':32*1024**3,
            }
    out=io.StringIO()
    with contextlib.redirect_stdout(out):
        live=mod.LiveInferenceProgress('analytics | model',5600,S(),interval=.01)
        live.reset('THINK',5600)
        live({'stage':'THINK','reasoning_chars':5000,'answer_chars':0,'predict':5600})
        live.finish({'eval_count':2000,'eval_duration':100_000_000_000},'score 90%')
    text=out.getvalue()
    assert 'analytics | model' in text
    assert 'THINK' in text
    assert 'GPU 82%' in text
    assert 'VRAM 9.9/12.0G' in text
    assert 'CPU 37%' in text
    assert 'RAM 12.0/32.0G' in text
    assert 'score 90%' in text
    class NoSystemReading:
        def latest(self):
            return {'gpu_util':50.0,'vram_used_mib':4096.0,'vram_total_mib':8192.0}
    missing=mod.LiveInferenceProgress('fixture',1000,NoSystemReading(),interval=99)._gpu_text()
    assert 'CPU N/A' in missing and 'RAM N/A' in missing
    command=mod._system_sampler_command(777)
    script=base64.b64decode(command[-1]).decode('utf-16le')
    assert '[Console]::Out.Flush()' in script
    eq(mod.SystemSampler.parse_line('37,12884901888,34359738368'),{
        'cpu_util':37.0,'ram_used_bytes':12884901888.0,'ram_total_bytes':34359738368.0,
    })
    assert mod.SystemSampler.parse_line('not,a,reading') is None


def test_ollama_http_error_exposes_server_body():
    old_post=mod.post
    try:
        def fake_post(payload,stream=False,timeout=900):
            fp=io.BytesIO(b'{"error":"model does not support thinking"}')
            raise urllib.error.HTTPError(
                url='http://127.0.0.1/api/chat',code=400,msg='Bad Request',
                hdrs=None,fp=fp
            )
        mod.post=fake_post
        cfg={'model':'x','think':True,'think_value':True,'num_predict':10,
             'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42}
        try:
            mod._ollama_stream_chat([{'role':'user','content':'x'}],cfg,silent=True)
        except RuntimeError as e:
            text=str(e)
            assert 'HTTP 400' in text
            assert 'does not support thinking' in text
        else:
            raise AssertionError('HTTP 400 was not surfaced')
    finally:
        mod.post=old_post


def test_remote_auto_prefers_working_profile_and_caches():
    old_load=mod.load_backend_settings
    old_save=mod.save_backend_settings
    old_test=mod._test_ssh_endpoint
    state=mod.default_backend_settings()
    state['target_mode']='remote'
    state['remote_access']['mode']='auto'
    state['remote_access']['profiles']['vpn'].update({'enabled':True,'host':'192.168.1.50','user':'u'})
    state['remote_access']['profiles']['direct'].update({'enabled':True,'host':'203.0.113.10','user':'u'})
    state['remote_access']['last_working_profile']=''
    saved=[]
    try:
        mod.load_backend_settings=lambda:json.loads(json.dumps(state))
        def save(x):
            saved.append(json.loads(json.dumps(x)))
            state.clear(); state.update(json.loads(json.dumps(x)))
        mod.save_backend_settings=save
        mod._test_ssh_endpoint=lambda ep:(ep['name']=='vpn','ok' if ep['name']=='vpn' else 'no')
        mod.reset_remote_endpoint_cache()
        ep=mod.resolve_remote_endpoint(force=True)
        eq(ep['name'],'vpn')
        eq(mod.ACTIVE_REMOTE_PROFILE,'vpn')
        eq(state['remote_access']['last_working_profile'],'vpn')
        # Cached endpoint should not need the probe again.
        mod._test_ssh_endpoint=lambda ep:(_ for _ in ()).throw(AssertionError('cache not used'))
        ep2=mod.resolve_remote_endpoint()
        eq(ep2['name'],'vpn')
    finally:
        mod.load_backend_settings=old_load
        mod.save_backend_settings=old_save
        mod._test_ssh_endpoint=old_test
        mod.reset_remote_endpoint_cache()


def test_direct_ssh_profile_is_batch_key_only_client_side():
    ep={'host':'203.0.113.10','port':48222,'user':'lab-user',
        'identity_file':r'C:\Users\me\.ssh\id_ed25519','kind':'direct_ssh','enabled':True}
    args=mod._ssh_base_args(ep,batch=True,connect_timeout=4)
    joined=' '.join(args)
    assert 'BatchMode=yes' in joined
    assert '-p 48222' in joined
    assert '-l lab-user' in joined
    assert joined.endswith('203.0.113.10')
    assert 'IdentitiesOnly=yes' in joined
    assert 'id_ed25519' in joined


def test_direct_profile_kind_cannot_be_downgraded_by_json():
    old_load=mod.load_backend_settings
    try:
        st=mod.default_backend_settings()
        st['remote_access']['profiles']['direct'].update({
            'enabled':True,'host':'203.0.113.10','user':'u','kind':'lan'
        })
        mod.load_backend_settings=lambda:st
        ep=mod._remote_profile('direct')
        eq(ep['kind'],'direct_ssh')
        args=mod._ssh_base_args(ep,batch=False,connect_timeout=4)
        assert 'BatchMode=yes' in args
    finally:
        mod.load_backend_settings=old_load


def test_llama_and_ollama_bind_remote_apis_to_loopback():
    args=mod._llama_server_args(mod.default_backend_settings()['llama_cpp'])
    joined=' '.join(args)
    assert '--host 127.0.0.1' in joined
    # Ollama tunnel explicitly targets remote loopback, never public bind.
    src=CLIENT.read_text(encoding='utf-8')
    assert "127.0.0.1:{remote_port}" in src
    assert "127.0.0.1:{local_port}:127.0.0.1:{remote_port}" in src

    for extra in (
        ['--host','0.0.0.0'],['--host=0.0.0.0'],['--api-key','secret'],
        ['--media-path',r'C:\\Users'],['--agent']
    ):
        st=mod.default_backend_settings()['llama_cpp']
        st['extra_args']=extra
        try:
            mod._llama_server_args(st)
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe managed extra_args accepted: '+repr(extra))




def test_bench_alias_and_root_route_do_not_fall_through_to_chat():
    eq(mod.normalize_console_command('bench'),'/bench')
    eq(mod.normalize_console_command('BENCH'),'/bench')
    eq(mod.normalize_console_command('bench compare analytics_case'),'/bench compare analytics_case')
    eq(mod.normalize_console_command('/bench'),'/bench')
    src=CLIENT.read_text(encoding='utf-8')
    assert "if u=='/bench':" in src
    assert "cmd,return_home=startup_benchmark_wizard(runtime_guard=ensure_runtime_ready)" in src
    assert "if u=='/bench list':" in src
    assert "if u=='/bench' or u=='/bench list':" not in src




def _with_fake_inputs(values,fn):
    old=mod.read_user_input
    it=iter(values)
    mod.read_user_input=lambda prompt='': next(it)
    try:
        return fn()
    finally:
        mod.read_user_input=old


def test_advanced_bench_slash_bench_stays_inside_lab():
    result=_with_fake_inputs(['/bench','1'],mod.benchmark_advanced_menu)
    eq(result,('/bench list',True))


def test_startup_advanced_never_returns_none_command_mode():
    result=_with_fake_inputs(['arbitrary chat text','0'],mod.startup_benchmark_wizard)
    eq(result,('/home',False))
    assert result[0] is not None


def test_advanced_rejects_arbitrary_chat_text():
    result=_with_fake_inputs(['привет модели','1'],mod.benchmark_advanced_menu)
    eq(result,('/bench list',True))




def test_single_benchmark_setup_selected_model_and_parameters():
    old_test=mod._startup_choose_test
    old_model=mod.choose_model_interactive
    old_opts=mod._startup_bench_options
    old_load=mod.load_benchmarks
    old_policy=mod.benchmark_reasoning_policy
    old_profile=mod.model_profile
    old_input=mod.read_user_input
    try:
        mod._startup_choose_test=lambda:'analytics_case'
        mod.choose_model_interactive=lambda current=None,prompt_title='':'qwen38-27b-iq4xs-8k:latest'
        mod._startup_bench_options=lambda default_runs=1:(3,'client','sweep')
        mod.load_benchmarks=lambda:{'analytics_case':{'version':1,'primary_predict':5600}}
        mod.benchmark_reasoning_policy=lambda model,item,req:{'mode':'think','reason':None,'actual':True,'requested':True}
        mod.model_profile=lambda model:{
            'ctx':8192,'threads':12,
            'think':{'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'num_predict':3200},
            'fast':{'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'num_predict':512},
        }
        vals=iter(['1','y'])
        mod.read_user_input=lambda prompt='':next(vals)
        sel=mod.benchmark_single_setup('x')
        eq(sel['benchmark'],'analytics_case')
        eq(sel['model'],'qwen38-27b-iq4xs-8k:latest')
        eq(sel['runs'],3)
        eq(sel['benchmark_mode'],'client')
        eq(sel['seed_mode'],'sweep')
        assert sel['think_value'] is True
        eq(sel['effective_mode'],'think')
    finally:
        mod._startup_choose_test=old_test
        mod.choose_model_interactive=old_model
        mod._startup_bench_options=old_opts
        mod.load_benchmarks=old_load
        mod.benchmark_reasoning_policy=old_policy
        mod.model_profile=old_profile
        mod.read_user_input=old_input


def test_single_benchmark_setup_fast_choice_and_cancel():
    old_test=mod._startup_choose_test
    old_model=mod.choose_model_interactive
    old_opts=mod._startup_bench_options
    old_load=mod.load_benchmarks
    old_policy=mod.benchmark_reasoning_policy
    old_profile=mod.model_profile
    old_input=mod.read_user_input
    try:
        mod._startup_choose_test=lambda:'instruction'
        mod.choose_model_interactive=lambda current=None,prompt_title='':'model-x'
        mod._startup_bench_options=lambda default_runs=1:(1,'native','fixed')
        mod.load_benchmarks=lambda:{'instruction':{'version':4,'primary_predict':1200}}
        mod.benchmark_reasoning_policy=lambda model,item,req:{'mode':'fast','reason':None,'actual':False,'requested':req}
        mod.model_profile=lambda model:{
            'ctx':8192,'threads':12,
            'think':{'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'num_predict':3200},
            'fast':{'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'num_predict':512},
        }
        vals=iter(['2','n'])
        mod.read_user_input=lambda prompt='':next(vals)
        assert mod.benchmark_single_setup('x') is None
    finally:
        mod._startup_choose_test=old_test
        mod.choose_model_interactive=old_model
        mod._startup_bench_options=old_opts
        mod.load_benchmarks=old_load
        mod.benchmark_reasoning_policy=old_policy
        mod.model_profile=old_profile
        mod.read_user_input=old_input


def test_advanced_menu_exposes_single_model_route():
    result=_with_fake_inputs(['2'],mod.benchmark_advanced_menu)
    eq(result,('/bench single',True))




def test_benchmark_limit_cause_context_vs_predict():
    eq(mod.benchmark_limit_cause(
        {'done_reason':'length','prompt_eval_count':2781,'eval_count':5411},
        8192,5600
    ),'context_window')
    eq(mod.benchmark_limit_cause(
        {'done_reason':'length','prompt_eval_count':500,'eval_count':5600},
        8192,5600
    ),'predict_budget')
    eq(mod.benchmark_limit_cause(
        {'done_reason':'stop','prompt_eval_count':2781,'eval_count':5411},
        8192,5600
    ),None)


def test_parse_bench_options_accepts_ultimate():
    eq(mod.parse_bench_options(['1','ultimate','fixed'],'native'),(1,'ultimate','fixed'))
    eq(mod.parse_bench_options(['3','client','sweep'],'native'),(3,'client','sweep'))


def test_analytics_case_recommends_client_pipeline():
    item=mod.builtin_benchmarks()['analytics_case']
    eq(item.get('recommended_benchmark_mode'),'client')
    eq(item.get('primary_predict'),5600)
    eq(item.get('min_context'),16384)
    assert item.get('force_final_answer') is True
    eq(mod.benchmark_context_size(item,8192),16384)
    eq(mod.benchmark_context_size(item,32768),32768)


def test_analytics_case_native_requires_fast_finalizer():
    class Sampler:
        def start(self): return self
        def stop(self): return {'samples':1,'vram_peak_mib':1000}

    old_sampler=mod.GpuSampler
    old_stream=mod.stream_chat
    old_rt=mod._runtime_telemetry
    old_digest=mod.model_digest
    old_caps=mod.cached_model_capabilities
    old_score=mod.benchmark_score
    calls=[]
    try:
        mod.GpuSampler=Sampler
        mod._runtime_telemetry=lambda model:{'gpu_offload_pct':50,'context_length':16384}
        mod.model_digest=lambda model,catalog=None:'digest'
        mod.cached_model_capabilities=lambda model_name,refresh=False:['completion','thinking']
        mod.benchmark_score=lambda name,item,answer:{
            'method':item.get('score_type'),'parse_error':None,
            'structured_result':None,'value':0.5,'checks':[]
        }
        def fake_stream(msgs,cfg,show_thinking=True,think_override=None,
                        predict_override=None,tools=None,response_format=None,
                        silent=False,progress=None):
            calls.append(think_override)
            if len(calls)==1:
                return '', 'reasoning only', {
                    'done_reason':'length','eval_count':5600,'prompt_eval_count':2743,
                    'eval_duration':1_000_000_000,'prompt_eval_duration':1_000_000_000
                }
            return analytics_gold_answer(), '', {
                'done_reason':'stop','eval_count':120,'prompt_eval_count':500,
                'eval_duration':1_000_000_000,'prompt_eval_duration':1_000_000_000
            }
        mod.stream_chat=fake_stream
        cfg={'model':'x','seed':42,'think':True,'think_value':True,'num_predict':5600}
        item=mod.builtin_benchmarks()['analytics_case']
        rec=mod.benchmark_record(
            'analytics_case',item,cfg,True,1,1,bench_mode='native',
            catalog={'x':{'digest':'digest'}}
        )
        eq(calls,[True,False])
        assert rec['recovery']['used'] is True
        eq(rec['final']['source'],'required_fast_finalizer')
        assert rec['final']['completed'] is True
        eq(rec['completion_status'],'completed')
        assert rec['config']['force_final_answer'] is True
    finally:
        mod.GpuSampler=old_sampler
        mod.stream_chat=old_stream
        mod._runtime_telemetry=old_rt
        mod.model_digest=old_digest
        mod.cached_model_capabilities=old_caps
        mod.benchmark_score=old_score


def test_analytics_context_override_is_applied_and_restored():
    old_load=mod.load_benchmarks
    old_preflight=mod.benchmark_scorer_preflight
    old_set=mod.set_active_model
    old_record=mod.benchmark_record
    old_unload=mod.unload_model
    old_atomic=mod._atomic_json
    old_ctx=mod.NUM_CTX
    root=Path(tempfile.mkdtemp())
    seen=[]; unloaded=[]
    item=mod.builtin_benchmarks()['analytics_case']
    try:
        mod.load_benchmarks=lambda:{'analytics_case':item}
        mod.benchmark_scorer_preflight=lambda tests,benches:(True,None)
        mod.set_active_model=lambda model:mod._apply_runtime_context(8192)
        def fake_record(name,item,cfg,*args,**kwargs):
            seen.append((mod.NUM_CTX,cfg.get('profile_ctx'),cfg.get('benchmark_ctx')))
            return {'execution_status':'ok','identity':{'benchmark':name,'model':cfg.get('model')}}
        mod.benchmark_record=fake_record
        mod.unload_model=lambda model:unloaded.append((model,mod.NUM_CTX))
        mod._atomic_json=lambda path,obj:None
        cp={
            'spec':{'tests':['analytics_case'],'models':['m'],'runs':1,'think_value':True,
                    'mode':'native','seed_mode':'fixed'},
            'records':{},'error_history':[],'suite_status':'running'
        }
        mod.execute_benchmark_checkpoint(
            root/'cp.json',cp,catalog={'m':{'digest':'digest'}}
        )
        eq(seen,[(16384,8192,16384)])
        eq(unloaded,[('m',8192)])
        eq(mod.NUM_CTX,8192)
    finally:
        mod.load_benchmarks=old_load
        mod.benchmark_scorer_preflight=old_preflight
        mod.set_active_model=old_set
        mod.benchmark_record=old_record
        mod.unload_model=old_unload
        mod._atomic_json=old_atomic
        mod._apply_runtime_context(old_ctx)
        shutil.rmtree(root,ignore_errors=True)


def test_benchmark_ultimate_reasoning_rollover_completes():
    old_stream=mod.stream_chat
    calls=[]
    try:
        final_answer='FINISHED\nBENCHMARK_RESULT\n{}'
        def fake(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,
                 tools=None,response_format=None,silent=False,progress=None):
            calls.append({'think':think_override,'predict':predict_override,'messages':msgs})
            n=len(calls)
            if n==1:
                return '', 'reasoning cycle two progress', {
                    'done_reason':'length','prompt_eval_count':3900,'eval_count':3900,
                    'eval_duration':1_000_000_000
                }
            return final_answer, 'done reasoning', {
                'done_reason':'stop','prompt_eval_count':4000,'eval_count':800,
                'eval_duration':1_000_000_000
            }
        mod.stream_chat=fake
        item={'primary_predict':5600,'recovery_predict':2600,'max_words':1200,'result_instruction':'BENCHMARK_RESULT'}
        cfg={'model':'x','seed':42,'think':True,'think_value':True,'num_predict':5600}
        primary_meta={'done_reason':'length','prompt_eval_count':2781,'eval_count':5411}
        r=mod._benchmark_ultimate_continue(
            [{'role':'user','content':'heavy benchmark'}],cfg,item,
            'initial reasoning checkpoint',primary_meta,'',live=None
        )
        assert r['completed'] is True
        eq(r['answer'],final_answer)
        assert r['cycles']>=2
        assert r['reasoning_rollovers']>=1
        assert r['total_eval_tokens']>5411
    finally:
        mod.stream_chat=old_stream


def test_benchmark_ultimate_final_continuation_is_fast():
    old_stream=mod.stream_chat
    calls=[]
    try:
        def fake(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,
                 tools=None,response_format=None,silent=False,progress=None):
            calls.append(think_override)
            return '{}','',{'done_reason':'stop','prompt_eval_count':1000,'eval_count':100}
        mod.stream_chat=fake
        item={'primary_predict':5600,'recovery_predict':2600,'max_words':1200,'result_instruction':'BENCHMARK_RESULT'}
        cfg={'model':'x','seed':42,'think':True,'think_value':True,'num_predict':5600}
        r=mod._benchmark_ultimate_continue(
            [{'role':'user','content':'heavy benchmark'}],cfg,item,
            'reasoning',{'done_reason':'length','prompt_eval_count':2781,'eval_count':5411},
            'partial final\nBENCHMARK_RESULT\n',live=None
        )
        assert r['completed'] is True
        assert calls and calls[0] is False
        assert r['final_continuations']==1
        assert r['answer'].startswith('partial final')
    finally:
        mod.stream_chat=old_stream


def test_ultimate_incomplete_contract_uses_v3_recovery():
    class Sampler:
        def start(self): return self
        def stop(self): return {'samples':1,'vram_peak_mib':1000}

    old_sampler=mod.GpuSampler; old_stream=mod.stream_chat
    old_rt=mod._runtime_telemetry; old_digest=mod.model_digest
    old_caps=mod.cached_model_capabilities; old_score=mod.benchmark_score
    old_ultimate=mod._benchmark_ultimate_continue; old_recovery=mod._benchmark_recovery
    calls=[]
    try:
        mod.GpuSampler=Sampler
        mod._runtime_telemetry=lambda model:{'gpu_offload_pct':50,'context_length':16384}
        mod.model_digest=lambda model,catalog=None:'digest'
        mod.cached_model_capabilities=lambda model_name,refresh=False:['completion']
        mod.benchmark_score=lambda name,item,answer:{
            'method':'fake','parse_error':None,'structured_result':{},
            'value':.8 if answer.endswith('{}') else (.2 if answer=='NATIVE_PARTIAL' else .1),
            'checks':[]
        }
        def fake_stream(*args,**kwargs):
            return 'NATIVE_PARTIAL','',{
                'done_reason':'length','eval_count':500,'prompt_eval_count':100,
                'eval_duration':1_000_000_000,'prompt_eval_duration':1_000_000_000
            }
        def fake_ultimate(*args,**kwargs):
            calls.append('ultimate')
            return {
                'used':True,'strategy':'benchmark_ultimate_rollover_v1','wall_seconds':1.0,
                'passes':[],'completed':False,'stop_cause':'contract_incomplete',
                'answer':'MALFORMED_FINAL','done_reason':'stop','cycles':2,
                'reasoning_rollovers':0,'final_continuations':1,
                'total_eval_tokens':100,'total_prompt_tokens':100,
            }
        def fake_recovery(base,cfg,item,primary_th,primary_ans='',name='',live=None,recovery_config=None):
            calls.append(('recovery',primary_ans))
            return {
                'used':True,'strategy':'continue_then_targeted_rescue_v3','wall_seconds':1.0,
                'passes':[],'completed':True,'stop_cause':'completed',
                'answer':'VALID\nBENCHMARK_RESULT\n{}','done_reason':'stop',
                'best_candidate_stage':'targeted_rescue','best_candidate_score':.8,
                'total_eval_tokens':50,'total_prompt_tokens':50,
            }
        mod.stream_chat=fake_stream
        mod._benchmark_ultimate_continue=fake_ultimate
        mod._benchmark_recovery=fake_recovery
        item={
            'version':1,'score_type':'fake','primary_predict':500,'recovery_predict':200,
            'result_instruction':'BENCHMARK_RESULT then JSON','reference':{},'prompt':'task'
        }
        cfg={'model':'x','seed':42,'think':False,'think_value':False,'num_predict':500}
        rec=mod.benchmark_record(
            'contract_case',item,cfg,False,1,1,bench_mode='ultimate',
            catalog={'x':{'digest':'digest'}}
        )
        eq(calls,['ultimate',('recovery','MALFORMED_FINAL')])
        eq(rec['final']['source'],'contract_recovery')
        assert rec['final']['completed'] is True
        assert rec['final']['structural_completion'] is True
        eq(rec['completion_status'],'completed')
        eq(rec['score']['final']['value'],.8)
        assert rec['recovery']['required_finalizer']['completed'] is True
    finally:
        mod.GpuSampler=old_sampler; mod.stream_chat=old_stream
        mod._runtime_telemetry=old_rt; mod.model_digest=old_digest
        mod.cached_model_capabilities=old_caps; mod.benchmark_score=old_score
        mod._benchmark_ultimate_continue=old_ultimate; mod._benchmark_recovery=old_recovery


def test_summary_v4_reports_context_truncation_and_ultimate_tokens():
    rec={
        'record_schema_version':5,'execution_status':'ok',
        'identity':{'benchmark':'analytics_case','model':'m','backend':'ollama','benchmark_version':1,
                    'benchmark_prompt_sha256':'p','benchmark_reference_sha256':'r','model_digest':'d'},
        'config':{'benchmark_mode':'ultimate','seed_mode':'fixed','seed':42},
        'primary':{'completed':False,'eval_rate':20.0,'limit_cause':'context_window'},
        'recovery':{'used':True},
        'final':{'completed':True,'done_reason':'stop','pipeline_wall_seconds':10.0,
                 'pipeline_eval_tokens':9000,'ultimate_cycles':2,'ultimate_reasoning_rollovers':1},
        'score':{'native':{'value':None},'final':{'value':0.9},'partial':None},
        'telemetry':{'gpu':{},'runtime':{}},
    }
    row=mod.benchmark_summary_rows([rec])[0]
    eq(row['summary_schema_version'],11)
    eq(row['context_window_truncations'],1)
    eq(row['predict_budget_truncations'],0)
    eq(row['pipeline_eval_tokens_avg'],9000)
    eq(row['ultimate_cycles_avg'],2)
    eq(row['ultimate_reasoning_rollovers_avg'],1)
    eq(row['completion_adjusted_score'],0.9)




def test_tools_chat_agent_no_undefined_silent():
    old_stream=mod.stream_chat
    try:
        def fake(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,
                 tools=None,response_format=None,silent=False,progress=None):
            return 'ok','',{'done_reason':'stop','eval_count':1,'eval_duration':1}
        mod.stream_chat=fake
        session={'tools_mode':'safe','response_format':None}
        ans,th,meta=mod.chat_agent([{'role':'user','content':'x'}],{'model':'m'},False,session)
        eq(ans,'ok')
    finally:
        mod.stream_chat=old_stream


def test_safe_tools_require_read_confirmation_outside_workspace():
    old_read=mod.read_user_input
    old_reader=mod.read_text_attachment
    try:
        mod.read_user_input=lambda prompt='':'NO'
        mod.read_text_attachment=lambda p:{'content':'SECRET'}
        call={'function':{'name':'read_file','arguments':{'path':str(mod.appdir()/'outside.txt')}}}
        out=mod.execute_tool_call(call,'safe')
        assert 'отклонил' in out.lower()
    finally:
        mod.read_user_input=old_read
        mod.read_text_attachment=old_reader


def test_workspace_read_needs_no_confirmation():
    old_read=mod.read_user_input
    old_reader=mod.read_text_attachment
    old_workspace=mod.workspace_dir
    root=Path(tempfile.mkdtemp())
    try:
        mod.workspace_dir=lambda:root
        mod.read_user_input=lambda prompt='':(_ for _ in ()).throw(AssertionError('confirmation should not happen'))
        mod.read_text_attachment=lambda p:{'content':'OK'}
        path=mod.workspace_dir()/'allowed.txt'
        call={'function':{'name':'read_file','arguments':{'path':str(path)}}}
        eq(mod.execute_tool_call(call,'safe'),'OK')
    finally:
        mod.read_user_input=old_read
        mod.read_text_attachment=old_reader
        mod.workspace_dir=old_workspace
        shutil.rmtree(root,ignore_errors=True)


def test_safe_child_env_strips_common_secrets():
    old=dict(mod.os.environ)
    try:
        mod.os.environ['OPENAI_API_KEY']='secret'
        mod.os.environ['HF_TOKEN']='secret'
        mod.os.environ['AWS_SECRET_ACCESS_KEY']='secret'
        env=mod.safe_child_env()
        assert 'OPENAI_API_KEY' not in env
        assert 'HF_TOKEN' not in env
        assert 'AWS_SECRET_ACCESS_KEY' not in env
        eq(env['HF_HUB_OFFLINE'],'1')
        eq(env['PYTHONNOUSERSITE'],'1')
    finally:
        mod.os.environ.clear(); mod.os.environ.update(old)


def test_ssh_host_rejects_option_injection():
    for bad in ('-oProxyCommand=calc.exe','host name','x;rm'):
        try:
            mod._validate_ssh_host(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe host accepted: '+bad)
    eq(mod._validate_ssh_host('lab-node.local'),'lab-node.local')
    eq(mod._validate_ssh_host('203.0.113.10'),'203.0.113.10')


def test_ssh_probe_uses_encoded_powershell_and_oem_decode():
    class CP:
        returncode=0
        stdout='LAB-PC\r\n'.encode('cp866')
        stderr=b''
    old_run=mod.subprocess.run
    seen={}
    try:
        def fake_run(cmd,**kwargs):
            seen['cmd']=list(cmd); seen['kwargs']=dict(kwargs)
            return CP()
        mod.subprocess.run=fake_run
        ep={'host':'LAB-PC','port':22,'user':'','identity_file':'','kind':'lan','enabled':True}
        ok,detail=mod._test_ssh_endpoint(ep,timeout=4)
        assert ok is True
        eq(detail,'LAB-PC')
        cmd=seen['cmd']
        assert '-EncodedCommand' in cmd
        assert '-Command' not in cmd
        encoded=cmd[cmd.index('-EncodedCommand')+1]
        script=mod.base64.b64decode(encoded).decode('utf-16le')
        assert '$env:COMPUTERNAME' in script
        assert '[Console]::OutputEncoding' in script
        assert seen['kwargs'].get('text') is None
        assert seen['kwargs'].get('encoding') is None
    finally:
        mod.subprocess.run=old_run

    russian='Имя "LAB-PC" не распознано как имя командлета'
    eq(mod._decode_subprocess_output(russian.encode('cp866')),russian)
    assert '�' not in mod._decode_subprocess_output(russian.encode('cp866'))


def test_external_llama_http_requires_explicit_override():
    eq(mod._validate_external_base_url('http://127.0.0.1:8080',False),'http://127.0.0.1:8080')
    eq(mod._validate_external_base_url('http://127.0.0.2:8080',False),'http://127.0.0.2:8080')
    eq(mod._validate_external_base_url('http://[::1]:8080',False),'http://[::1]:8080')
    eq(mod._validate_external_base_url('https://llm.example.com',False),'https://llm.example.com')
    try:
        mod._validate_external_base_url('http://203.0.113.10:8080',False)
    except ValueError:
        pass
    else:
        raise AssertionError('insecure remote HTTP accepted')
    eq(mod._validate_external_base_url('http://203.0.113.10:8080',True),'http://203.0.113.10:8080')
    for bad in (
        'https://user:password@llm.example.com','https://llm.example.com/?token=secret',
        'https://llm.example.com:70000','https://llm.example.com/path name'
    ):
        try:
            mod._validate_external_base_url(bad,False)
        except ValueError:
            pass
        else:
            raise AssertionError('credential/query URL accepted: '+bad)


def test_llama_redirects_are_blocked_before_bearer_forwarding():
    req=mod.urllib.request.Request(
        'https://llm.example.com/v1/chat/completions',
        headers={'Authorization':'Bearer secret'}
    )
    try:
        mod._NoLlamaRedirect().redirect_request(
            req,None,302,'Found',{},'https://evil.example/steal'
        )
    except mod.urllib.error.HTTPError as e:
        assert 'redirect blocked' in str(e).casefold()
    else:
        raise AssertionError('llama redirect accepted')


def test_llama_capabilities_do_not_fake_thinking():
    old=mod.llama_installed_models
    try:
        mod.llama_installed_models=lambda refresh=False:[
            {'name':'m','architecture':{'input_modalities':['text']}}
        ]
        caps=mod.llama_model_capabilities('m')
        assert 'tools' in caps
        assert 'thinking' not in caps
    finally:
        mod.llama_installed_models=old


def test_unknown_slash_command_guard_present():
    src=CLIENT.read_text(encoding='utf-8')
    assert "elif u.startswith('/'):" in src
    assert "Неизвестная команда" in src
    assert "if u.startswith('//')" in src


def test_help_topics_and_backend_migration_commands_present():
    src=CLIENT.read_text(encoding='utf-8')
    for token in (
        "def backend_setup_wizard()",
        "def backend_doctor()",
        "def backend_export_config()",
        "/help prompts",
        "/help modes",
        "Docs/BACKEND_SETUP.md",
        "Docs/PROMPTING_GUIDE.md",
    ):
        assert token in src


def test_backend_and_profile_store_cache_roundtrip():
    # Structural regression: load functions must use mtime caches and still return copies.
    src=CLIENT.read_text(encoding='utf-8')
    assert "_BACKEND_SETTINGS_CACHE" in src
    assert "_PROFILE_STORE_CACHE" in src
    assert "return deepcopy(_BACKEND_SETTINGS_CACHE['data'])" in src
    assert "return deepcopy(_PROFILE_STORE_CACHE['data'])" in src





def test_backend_import_rejects_unknown_keys_and_insecure_url():
    import tempfile
    old_read=mod.read_user_input
    try:
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json'
            p.write_text(json.dumps({'evil':1}),encoding='utf-8')
            try:
                mod.backend_import_config(p)
            except ValueError as e:
                assert 'top-level' in str(e)
            else:
                raise AssertionError('unknown backend config key accepted')

            p2=Path(td)/'http.json'
            p2.write_text(json.dumps({
                'active':'llama_cpp',
                'llama_cpp':{
                    'transport':'external',
                    'base_url':'http://203.0.113.10:8080',
                    'allow_insecure_external':False
                }
            }),encoding='utf-8')
            try:
                mod.backend_import_config(p2)
            except ValueError as e:
                assert 'HTTP' in str(e) or 'HTTPS' in str(e)
            else:
                raise AssertionError('insecure external URL imported')

            for name,payload in (
                ('secret.json',{'llama_cpp':{'api_key':'must-not-be-stored'}}),
                ('nested-unknown.json',{'llama_cpp':{'unknown_runtime_switch':True}}),
                ('unsafe-extra.json',{'llama_cpp':{'extra_args':['--host=0.0.0.0']}}),
                ('string-bool.json',{'llama_cpp':{
                    'transport':'external','base_url':'http://203.0.113.10:8080',
                    'allow_insecure_external':'false'
                }}),
            ):
                bad=Path(td)/name
                bad.write_text(json.dumps(payload),encoding='utf-8')
                try:
                    mod.backend_import_config(bad)
                except ValueError:
                    pass
                else:
                    raise AssertionError('unsafe backend config accepted: '+name)
    finally:
        mod.read_user_input=old_read


def test_release_gate_reverifies_manifest_and_new_docs():
    build=(ROOT/'Build-Release.ps1').read_text(encoding='utf-8-sig')
    for doc in (
        'Docs\\PROMPTING_GUIDE.md',
        'Docs\\BACKEND_SETUP.md',
        'Docs\\CODE_AUDIT.md',
        'Docs\\SECURITY.md',
        'Docs\\RELEASE_NOTES_0.29.0.1.md',
    ):
        assert doc in build
    assert 'Manifest hash mismatch before packaging' in build
    assert 'Staged manifest hash mismatch' in build
    assert '$allowedVersioned' in build
    assert 'v0.29.0.1' in build
    assert 'Apps\\benchmark_lab_v0_29_0_1.py' in build
    assert 'Shared\\bull_llm\\runtime\\__init__.py' in build
    assert 'Shared\\bull_llm\\schemas.py' in build
    assert '$rootExcludedDirs' in build and '$anywhereExcludedDirs' in build
    assert 'client_debug.log' in build
    assert 'ui_settings.json' in build
    assert '-AuditReleaseCandidatesOnly' in build
    assert 'Runtime/cache data: excluded without deleting source files' in build
    assert 'ZipFileExtensions]::CreateEntryFromFile' in build
    assert 'Add-Type -AssemblyName System.IO.Compression\n' in build.replace('\r\n','\n')
    assert '$entryName="BULL-$version-Bundle/"' in build
    assert (ROOT/'Build-Release.ps1').read_bytes().startswith(b'\xef\xbb\xbf')
    assert "Remove-Item -LiteralPath $p -Recurse" not in build


def test_v174_documentation_set_exists():
    for rel in (
        'Docs/USER_GUIDE.md',
        'Docs/AI_CONTEXT.yaml',
        'Docs/PROMPTING_GUIDE.md',
        'Docs/BACKEND_SETUP.md',
        'Docs/REMOTE_ACCESS.md',
        'Docs/CODE_AUDIT.md',
        'Docs/SECURITY.md',
        'Docs/RELEASE_NOTES_0.21.0.0.md',
    ):
        assert (ROOT/rel).is_file(), rel




def test_generated_scorer_subprocesses_use_scrubbed_environment():
    src=CLIENT.read_text(encoding='utf-8')
    # Tool Python + retention preflight/executor + analytics preflight/executor.
    assert src.count('env=safe_child_env()') >= 5
    retention=src[src.index('def _execute_retention_code'):src.index('def _analytics_sql_block')]
    analytics=src[src.index('def _analytics_executor_preflight'):src.index('def _analytics_metric_rows_ok')]
    assert 'env=safe_child_env()' in retention
    assert analytics.count('env=safe_child_env()') >= 2




def test_external_llama_api_key_required_and_header_from_env():
    old_load=mod.load_backend_settings
    old_env=dict(os.environ)
    try:
        st=mod.default_backend_settings()
        ll=st['llama_cpp']
        ll.update({
            'transport':'external',
            'base_url':'https://llm.example.com',
            'allow_insecure_external':False,
            'allow_unauthenticated_external':False,
            'api_key_env':'BULL_LLAMA_API_KEY',
        })
        mod.load_backend_settings=lambda:st
        os.environ.pop('BULL_LLAMA_API_KEY',None)
        try:
            mod.llama_api_headers()
        except RuntimeError as e:
            assert 'API key' in str(e)
        else:
            raise AssertionError('external non-loopback llama accepted without API key')

        os.environ['BULL_LLAMA_API_KEY']='secret-test-key'
        headers=mod.llama_api_headers()
        eq(headers.get('Authorization'),'Bearer secret-test-key')
        assert 'secret-test-key' not in json.dumps(st,ensure_ascii=False)
    finally:
        mod.load_backend_settings=old_load
        os.environ.clear(); os.environ.update(old_env)


def test_benchmark_wizard_multi_model_route_prompts_selector():
    old_choose=mod._startup_choose_test
    old_read=mod.read_user_input
    try:
        mod._startup_choose_test=lambda:'analytics_case'
        seq=iter(['3'])
        mod.read_user_input=lambda prompt='':next(seq)
        cmd,ret=mod.benchmark_advanced_menu()
        eq(cmd,'/bench compare analytics_case')
        assert ret is True
        assert ' all ' not in (' '+cmd+' ')
    finally:
        mod._startup_choose_test=old_choose
        mod.read_user_input=old_read


def test_backend_menu_exposes_import_portable_config():
    src=CLIENT.read_text(encoding='utf-8')
    segment=src[src.index('def backend_runtime_menu'):src.index('def print_benchmark_reference')]
    assert 'Import portable config' in segment
    assert "backend_import_config(raw)" in segment
    assert '/backend import' in src


def test_actionable_error_hints_cover_network_and_hostkey():
    h1=mod.error_hint(ConnectionRefusedError('10061'))
    assert '/backend doctor' in h1 and '/remote reconnect' in h1
    h2=mod.error_hint(RuntimeError('Host key verification failed'))
    assert 'fingerprint' in h2.casefold()
    h3=mod.error_hint(RuntimeError('llama API key missing'))
    assert 'BULL_LLAMA_API_KEY' in h3


def _benchmark_test_profile(ctx=8192,threads=12,temp=1.0):
    return {
        'ctx':ctx,'threads':threads,
        'capabilities':{'supports_thinking':False,'supports_completion':True,'native_context':ctx},
        'fast':{'num_predict':1024,'temperature':temp,'top_p':.95,'top_k':40,'min_p':0.0,'seed':42},
        'think':{'num_predict':3200,'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42},
        'ultimate':{'num_predict':5000,'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42},
    }


def test_effective_config_precedence_constraints_and_capability():
    old_profile=mod.model_profile; old_caps=mod.cached_model_capabilities
    try:
        mod.model_profile=lambda name:_benchmark_test_profile()
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        item=mod.builtin_benchmarks()['analytics_case']
        eff=mod.benchmark_effective_config(
            'coder','analytics_case',item,True,44,'analytics_fair_v1',
            {'ctx':8192,'temperature':.31,'num_predict':6100,'think':True},'client'
        )
        eq(eff['ctx'],16384)
        eq(eff['temperature'],.31)
        eq(eff['num_predict'],6100)
        eq(eff['seed'],44)
        assert eff['think'] is False
        eq(eff['constraint_overrides'][0]['reason'],'benchmark_min_context')
        eq(eff['capability_overrides'][0]['reason'],'model_no_thinking_capability')
        assert re.fullmatch(r'[0-9a-f]{64}',eff['fingerprint'])
    finally:
        mod.model_profile=old_profile; mod.cached_model_capabilities=old_caps


def test_native_effective_config_marks_recovery_suppressed():
    old_profile=mod.model_profile; old_caps=mod.cached_model_capabilities
    try:
        mod.model_profile=lambda name:_benchmark_test_profile()
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        item=mod.builtin_benchmarks()['instruction']
        native=mod.benchmark_effective_config(
            'model','instruction',item,False,42,'fair_default',None,'native'
        )
        assert native['recovery']['requested_enabled'] is True
        assert native['recovery']['enabled'] is False
        eq(native['recovery']['suppressed_reason'],'native_pipeline')
        client=mod.benchmark_effective_config(
            'model','instruction',item,False,42,'fair_default',None,'client'
        )
        assert client['recovery']['requested_enabled'] is True
        assert client['recovery']['enabled'] is True
        assert client['recovery']['suppressed_reason'] is None
    finally:
        mod.model_profile=old_profile; mod.cached_model_capabilities=old_caps


def test_fair_compare_normalizes_model_defaults():
    old_profile=mod.model_profile; old_caps=mod.cached_model_capabilities
    old_runtime=mod.backend_runtime_fingerprint; old_digest=mod.model_digest
    try:
        mod.model_profile=lambda name:_benchmark_test_profile(8192 if name=='m1' else 32768,8 if name=='m1' else 16,1.0 if name=='m1' else .2)
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        mod.backend_runtime_fingerprint=lambda:'runtime'
        mod.model_digest=lambda name,catalog=None:'digest-'+name
        spec=mod.make_benchmark_spec(
            ['analytics_case'],['m1','m2'],1,False,'client','fixed',catalog={'m1':{},'m2':{}},
            run_profile='analytics_fair_v1',seeds=[42],fair_compare=True
        )
        report=spec['fairness_by_run']['analytics_case|1']
        assert report['equivalent'] is True
        a=spec['effective_configs']['analytics_case|m1|1']
        b=spec['effective_configs']['analytics_case|m2|1']
        for key in ('ctx','num_thread','num_predict','temperature','top_p','top_k','min_p','seed','think','recovery'):
            eq(a[key],b[key],key)
        assert a['fingerprint']!=b['fingerprint'],'effective fingerprint must retain model digest/profile provenance'
        assert spec['strict_fair_compare'] is True
    finally:
        mod.model_profile=old_profile; mod.cached_model_capabilities=old_caps
        mod.backend_runtime_fingerprint=old_runtime; mod.model_digest=old_digest


def _ollama_benchmark_snapshot(model='m',digest='digest-m',temperature=1.0,ctx=16384):
    return {
        'model':model,'model_digest':digest,'architecture':'qwen3','quantization':'Q4_K_M',
        'parameters':{
            'num_ctx':ctx,'num_thread':12,'temperature':temperature,'top_p':.95,
            'top_k':40,'min_p':0.0,'repeat_penalty':1.0,'stop':['<|end|>'],
        },
        'template':'template','capabilities':['completion'],'retrieved_at':'2026-08-28T12:00:00',
        'ollama_version':'0.11.8',
    }


def test_ollama_profile_parameter_parser_and_digest_cache_invalidation():
    raw='''num_ctx 16384\nnum_thread 12\ntemperature 1\ntop_p 0.95\ntop_k 40\nmin_p 0\nrepeat_penalty 1\nstop "<|end|>"\nstop "<|eot|>"'''
    parsed=mod.parse_ollama_profile_parameters(raw)
    eq(parsed['num_ctx'],16384); eq(parsed['temperature'],1.0)
    eq(parsed['stop'],['<|end|>','<|eot|>'])
    old_post,old_get=mod.api_post_json,mod.api_get
    old_cache=deepcopy(mod.OLLAMA_PROFILE_CACHE); calls=[]
    try:
        mod.OLLAMA_PROFILE_CACHE.clear()
        mod.api_get=lambda path,timeout=5:{'version':'0.11.8'}
        def fake_post(path,payload,timeout=8):
            calls.append((path,payload['model']))
            return {'parameters':raw,'template':'t','capabilities':['completion'],
                    'details':{'family':'qwen3','quantization_level':'Q4_K_M'}}
        mod.api_post_json=fake_post
        a=mod.ollama_profile_snapshot('m',{'m':{'digest':'digest-a'}})
        b=mod.ollama_profile_snapshot('m',{'m':{'digest':'digest-a'}})
        c=mod.ollama_profile_snapshot('m',{'m':{'digest':'digest-b'}})
        eq(len(calls),2); eq(a,b); eq(c['model_digest'],'digest-b')
    finally:
        mod.api_post_json,mod.api_get=old_post,old_get
        mod.OLLAMA_PROFILE_CACHE.clear(); mod.OLLAMA_PROFILE_CACHE.update(old_cache)


def test_sampling_source_model_profile_omits_sampling_options():
    old_profile,old_caps=mod.model_profile,mod.cached_model_capabilities
    try:
        mod.model_profile=lambda name:_benchmark_test_profile(temp=.2)
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        snapshot=_ollama_benchmark_snapshot(temperature=1.0)
        eff=mod.benchmark_effective_config(
            'm','simpson',mod.builtin_benchmarks()['simpson'],False,42,'fair_default',
            {'sampling_source':'model_profile','recovery':{'enabled':False}},'native',snapshot
        )
        eq(eff['sampling_source'],'model_profile'); eq(eff['temperature'],1.0)
        assert 'temperature' not in eff['sent_runtime_options']
        assert 'top_p' not in mod.benchmark_runtime_options(eff)
        eq(eff['parameter_sources']['temperature'],{
            'value':1.0,'source':'model_profile','sent_in_request':False
        })
        eq(eff['profile_ctx'],16384)
    finally:
        mod.model_profile,mod.cached_model_capabilities=old_profile,old_caps


def test_model_profile_serializer_sends_exact_options_without_sampling():
    old_post=mod.post; captured=[]
    class Response:
        def __enter__(self):
            return iter([json.dumps({'message':{'content':'ok'},'done':True}).encode('utf-8')])
        def __exit__(self,*args): return False
    try:
        def fake_post(payload,stream=False,timeout=900):
            captured.append(deepcopy(payload)); return Response()
        mod.post=fake_post
        cfg={
            'model':'m','think':False,'think_value':False,'num_predict':4096,'seed':42,
            'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,
            '_benchmark_sent_runtime_options':{
                'seed':42,'num_predict':4096,'num_ctx':16384,'num_thread':12,
            },
        }
        mod._ollama_stream_chat([{'role':'user','content':'x'}],cfg,silent=True)
        eq(captured[0]['options'],{'seed':42,'num_predict':4096,'num_ctx':16384,'num_thread':12})
        assert not (set(captured[0]['options']) & set(mod.BENCHMARK_SAMPLING_FIELDS))
    finally:
        mod.post=old_post


def test_sampling_source_benchmark_override_preserves_legacy_request():
    old_profile,old_caps=mod.model_profile,mod.cached_model_capabilities
    try:
        mod.model_profile=lambda name:_benchmark_test_profile(temp=1.0)
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        eff=mod.benchmark_effective_config(
            'm','simpson',mod.builtin_benchmarks()['simpson'],False,42,'fair_default',None,
            'native',_ollama_benchmark_snapshot(temperature=1.0)
        )
        eq(eff['sampling_source'],'benchmark_override')
        eq(eff['temperature'],.2); eq(eff['sent_runtime_options']['temperature'],.2)
        eq(eff['parameter_sources']['temperature']['source'],'sampling_preset')
        assert eff['parameter_sources']['temperature']['sent_in_request'] is True
    finally:
        mod.model_profile,mod.cached_model_capabilities=old_profile,old_caps


def test_sampling_source_per_model_has_distinct_requests_and_fingerprints():
    old_profile,old_caps=mod.model_profile,mod.cached_model_capabilities
    try:
        mod.model_profile=lambda name:_benchmark_test_profile()
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        model_sampling={
            'default':{'temperature':.8,'top_p':.9,'top_k':40,'min_p':0.0},
            'official':{'temperature':1.0,'top_p':.95,'top_k':40,'min_p':0.0},
            'precise':{'temperature':.6,'top_p':.95,'top_k':40,'min_p':0.0},
        }
        configs=[]
        for model in model_sampling:
            configs.append(mod.benchmark_effective_config(
                model,'simpson',mod.builtin_benchmarks()['simpson'],False,42,None,
                {'sampling_source':'per_model','model_sampling':model_sampling,
                 'experimental_parameters':['temperature','top_p','top_k','min_p']},
                'native',_ollama_benchmark_snapshot(model=model,digest='digest-'+model)
            ))
        eq([x['sent_runtime_options']['temperature'] for x in configs],[.8,1.0,.6])
        eq(len({x['fingerprint'] for x in configs}),3)
        assert all(x['parameter_sources']['temperature']['source']=='per_model_override' for x in configs)
    finally:
        mod.model_profile,mod.cached_model_capabilities=old_profile,old_caps


def test_sampling_preflight_blocks_no_variation_and_profile_override():
    base={'model':'a','sampling_source':'per_model','experimental_parameters':['temperature'],
          'temperature':.8,'sent_runtime_options':{'temperature':.8},'parameter_sources':{}}
    spec={'models':['a','b'],'tests':['simpson'],'run_matrix':[{'run':1}],
          'sampling_source':'per_model','experimental_parameters':['temperature'],
          'effective_configs':{'simpson|a|1':deepcopy(base),'simpson|b|1':{**deepcopy(base),'model':'b'}}}
    try:
        mod.benchmark_sampling_preflight(spec)
        raise AssertionError('no-variation experiment must be rejected')
    except RuntimeError as exc:
        assert 'SAMPLING_EXPERIMENT_HAS_NO_VARIATION' in str(exc)
    profile=deepcopy(base); profile['sampling_source']='model_profile'
    profile['sent_runtime_options']={'temperature':.8}
    spec2={'models':['a'],'tests':['simpson'],'run_matrix':[{'run':1}],
           'sampling_source':'model_profile','experimental_parameters':[],
           'effective_configs':{'simpson|a|1':profile}}
    try:
        mod.benchmark_sampling_preflight(spec2)
        raise AssertionError('model-profile serializer leak must be rejected')
    except RuntimeError as exc:
        assert 'MODEL_PROFILE_SAMPLING_OVERRIDDEN' in str(exc)


def test_strict_fair_compare_allows_only_experimental_parameters():
    a={'model':'a','ctx':16384,'num_thread':12,'num_predict':4096,'temperature':.8,
       'top_p':.9,'top_k':40,'min_p':0.0,'repeat_penalty':1.0,'seed':42,
       'think_requested':False,'think':False,'force_final_answer':False,'recovery':{'enabled':False}}
    b={**deepcopy(a),'model':'b','temperature':1.0}
    report=mod.benchmark_fairness_report([a,b],['temperature'])
    assert report['equivalent'] is True and not report['differences']
    eq(report['experimental_differences'][0]['field'],'temperature')
    b['ctx']=8192
    report=mod.benchmark_fairness_report([a,b],['temperature'])
    assert report['equivalent'] is False
    eq(report['differences'][0]['field'],'ctx')


def test_strict_fair_compare_records_ollama_profile_sampler_differences():
    """Profile inheritance is visible evidence, never a hidden fair-compare failure."""
    a={
        'model':'a','sampling_source':'model_profile','allow_mixed_sampling_override':False,
        'ctx':16384,'num_thread':12,'num_predict':4096,'temperature':1.0,
        'top_p':.95,'top_k':40,'min_p':0.0,'repeat_penalty':1.0,
        'repeat_last_n':None,'presence_penalty':None,'frequency_penalty':None,
        'mirostat':None,'mirostat_eta':None,'mirostat_tau':None,
        'seed':42,'think_requested':False,'think':False,'force_final_answer':False,
        'recovery':{'enabled':False},
    }
    b={**deepcopy(a),'model':'b','temperature':.2,'repeat_penalty':None}
    report=mod.benchmark_fairness_report([a,b],[])
    assert report['equivalent'] is True
    assert not report['differences']
    eq({row['field'] for row in report['profile_owned_differences']},{'temperature','repeat_penalty'})
    b['num_thread']=8
    report=mod.benchmark_fairness_report([a,b],[])
    assert report['equivalent'] is False
    eq(report['differences'][0]['field'],'num_thread')


def test_model_profile_spec_preflight_accepts_inherited_sampler_variation():
    old_profile=mod.model_profile; old_caps=mod.cached_model_capabilities
    old_runtime=mod.backend_runtime_fingerprint; old_digest=mod.model_digest
    try:
        mod.model_profile=lambda name:_benchmark_test_profile()
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        mod.backend_runtime_fingerprint=lambda:'runtime'
        mod.model_digest=lambda name,catalog=None:'digest-'+name
        first=_ollama_benchmark_snapshot('first',temperature=1.0)
        second=_ollama_benchmark_snapshot('second',temperature=.2)
        second['parameters'].pop('repeat_penalty')
        spec=mod.make_benchmark_spec(
            ['simpson'],['first','second'],1,False,'native','fixed',
            catalog={'first':{},'second':{}},run_profile='fair_default',seeds=[42],
            fair_compare=True,
            run_overrides={'sampling_source':'model_profile','strict_fair_compare':True},
            profile_snapshots={'first':first,'second':second},
        )
        report=spec['fairness_by_run']['simpson|1']
        assert report['equivalent'] is True
        eq({row['field'] for row in report['profile_owned_differences']},{'temperature','repeat_penalty'})
        preflight=mod.benchmark_sampling_preflight(spec)
        eq(preflight['variation_verified'],None)
    finally:
        mod.model_profile=old_profile; mod.cached_model_capabilities=old_caps
        mod.backend_runtime_fingerprint=old_runtime; mod.model_digest=old_digest


def test_old_benchmark_profile_defaults_to_benchmark_override():
    old_profile,old_caps=mod.model_profile,mod.cached_model_capabilities
    try:
        mod.model_profile=lambda name:_benchmark_test_profile()
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        eff=mod.benchmark_effective_config(
            'm','simpson',mod.builtin_benchmarks()['simpson'],False,42,None,{},'native',
            _ollama_benchmark_snapshot()
        )
        eq(eff['sampling_source'],'benchmark_override')
    finally:
        mod.model_profile,mod.cached_model_capabilities=old_profile,old_caps


def test_all_suite_strict_fair_uses_each_benchmark_predict_budget():
    old_profile=mod.model_profile; old_caps=mod.cached_model_capabilities
    old_runtime=mod.backend_runtime_fingerprint; old_digest=mod.model_digest
    try:
        def varied_profile(name):
            profile=_benchmark_test_profile()
            profile['fast']['num_predict']=512 if name=='m1' else 1024
            profile['think']['num_predict']=2800 if name=='m1' else 3600
            profile['ultimate']['num_predict']=4200 if name=='m1' else 5200
            return profile
        mod.model_profile=varied_profile
        mod.cached_model_capabilities=lambda name,refresh=False:['completion']
        mod.backend_runtime_fingerprint=lambda:'runtime'
        mod.model_digest=lambda name,catalog=None:'digest-'+name
        benches=mod.builtin_benchmarks()
        spec=mod.make_benchmark_spec(
            list(benches),['m1','m2'],3,True,'ultimate','sweep',
            label='all_compare',catalog={'m1':{},'m2':{}},
            run_profile='fair_default',fair_compare=True
        )
        assert spec['strict_fair_compare'] is True
        eq(len(spec['fairness_by_run']),len(benches)*3)
        for test,item in benches.items():
            expected=int(item['primary_predict'])
            for run in range(1,4):
                a=spec['effective_configs'][f'{test}|m1|{run}']
                b=spec['effective_configs'][f'{test}|m2|{run}']
                eq(a['num_predict'],expected,f'{test} m1 predict')
                eq(b['num_predict'],expected,f'{test} m2 predict')
                report=spec['fairness_by_run'][f'{test}|{run}']
                assert report['equivalent'] is True,(test,run,report)
                eq(report['differences'],[])
    finally:
        mod.model_profile=old_profile; mod.cached_model_capabilities=old_caps
        mod.backend_runtime_fingerprint=old_runtime; mod.model_digest=old_digest


def test_manual_seeds_runtime_options_and_sweep_matrix():
    runs,mode,seed_mode,seeds,opt=mod.parse_bench_runtime_options(
        ['client','profile=analytics_fair_v1','seeds=42,44','temperature=0.3','recovery.max_passes=1']
    )
    eq((runs,mode,seed_mode,seeds),(2,'client','manual',[42,44]))
    eq(opt['run_profile'],'analytics_fair_v1')
    eq(opt['overrides']['temperature'],.3)
    key,values=mod.parse_sweep_expression('temperature=0.1,0.2,0.4')
    eq(key,'temperature'); eq(values,[.1,.2,.4])


def test_recovery_keeps_best_verified_partial():
    old_stream=mod.stream_chat; old_score=mod.benchmark_score; old_ctx=mod.NUM_CTX
    calls=[]
    try:
        mod.NUM_CTX=16384
        def fake_stream(msgs,cfg,show_thinking=True,think_override=None,predict_override=None,tools=None,response_format=None,silent=False,progress=None):
            calls.append('\n'.join(str(x.get('content','')) for x in msgs))
            return ' WEAKER_STAGE_'+str(len(calls)),'',{'done_reason':'length','eval_count':100,'prompt_eval_count':100}
        mod.stream_chat=fake_stream
        mod.benchmark_score=lambda name,item,answer:{'method':'fake','value':.9 if answer=='PRIMARY_BEST' else .1,'checks':[]}
        result=mod._benchmark_recovery(
            [{'role':'user','content':'task'}],
            {'model':'m','seed':42,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05},
            {'result_instruction':'BENCHMARK_RESULT JSON','max_words':300},'',
            'PRIMARY_BEST','case',recovery_config={'max_passes':2,'continuation_predict':500,'rescue_predict':400}
        )
        eq(len(calls),2)
        assert 'PRIMARY_BEST' in calls[0]
        assert 'WEAKER_STAGE_1' in calls[1]
        eq(result['answer'],'PRIMARY_BEST')
        eq(result['best_candidate_stage'],'primary')
        eq(result['best_candidate_score'],.9)
        assert result['completed'] is False
    finally:
        mod.stream_chat=old_stream; mod.benchmark_score=old_score; mod.NUM_CTX=old_ctx


def test_structural_completion_and_analytics_v3_contract():
    item=mod.builtin_benchmarks()['analytics_case']
    eq(item['version'],3); eq(item['score_type'],'analytics_case_v3')
    eq(item['max_words'],300)
    prompt=mod.benchmark_effective_prompt(item)
    assert 'не создавай test fixtures' in prompt
    assert 'Python-блок содержит только imports и функцию analyze_ab' in prompt
    assert mod.benchmark_structural_completion('analytics_case',item,analytics_gold_answer()) is True
    assert mod.benchmark_structural_completion('analytics_case',item,'```sql\nselect 1\n```') is False
    assert mod.benchmark_answer_completed('analytics_case',item,'MALFORMED','stop') is False
    assert mod.benchmark_answer_completed('analytics_case',item,analytics_gold_answer(),'length') is True
    instruction=mod.builtin_benchmarks()['instruction']
    assert mod.benchmark_answer_completed('instruction',instruction,'four lines','stop') is True


def test_analytics_tolerance_typing_io_and_contradiction_cap():
    rounded=[
        {'variant':'A','users':12,'purchasers':5,'conversion':.4167,'revenue':500.00,'arpu':41.67,'arppu':100.0},
        {'variant':'B','users':12,'purchasers':8,'conversion':.6667,'revenue':600.00,'arpu':50.0,'arppu':75.0},
    ]
    assert mod._analytics_metric_rows_ok(rounded)
    safe,err=mod._analytics_python_safety(
        'from typing import Dict\nfrom io import StringIO\n'
        'def analyze_ab(users, orders):\n    x: Dict = {}\n    _ = (StringIO(), orders.shape)\n    return users, x, None\n'
    )
    assert safe,err
    answer=analytics_gold_answer()
    head,raw=answer.rsplit('BENCHMARK_RESULT\n',1); obj=json.loads(raw); obj['z_p_value']=.999
    score=mod.benchmark_score('analytics_case',mod.builtin_benchmarks()['analytics_case'],head+'BENCHMARK_RESULT\n'+json.dumps(obj))
    assert score['contradiction_detected'] is True
    assert score['value']<=.78
    eq(score['cap_applied'],'reported_results_contradict_executable_core_max_78pct')


def test_incomplete_outputs_are_scorable_but_completion_adjusted():
    def rec(run,completed,value):
        return {
            'record_schema_version':6,'execution_status':'ok','completion_status':'completed' if completed else 'truncated',
            'identity':{'benchmark':'case','benchmark_version':1,'model':'m','backend':'ollama','run':run},
            'config':{'benchmark_mode':'native','seed_mode':'manual','seed':40+run},
            'primary':{'completed':completed,'eval_rate':10.0},'recovery':{'used':False},
            'final':{'completed':completed,'pipeline_wall_seconds':60.0},
            'score':{'native':{'value':value},'final':{'value':value},'partial':None if completed else {'value':value},'best_verified_partial':None if completed else {'value':value}},
            'telemetry':{'gpu':{},'runtime':{}},
        }
    row=mod.benchmark_summary_rows([rec(1,True,.8),rec(2,False,.6)])[0]
    eq(row['runs_scorable'],2)
    assert abs(row['scorable_score_avg']-.7)<1e-9
    assert abs(row['completion_adjusted_score']-.4)<1e-9
    assert abs(row['best_verified_partial_score_avg']-.6)<1e-9


def test_benchmark_profile_crud_roundtrip():
    old_path=mod.benchmark_profiles_path; old_cache=dict(mod._BENCH_PROFILE_STORE_CACHE)
    root=Path(tempfile.mkdtemp()); path=root/'benchmark_profiles.json'
    try:
        mod.benchmark_profiles_path=lambda:path
        mod._BENCH_PROFILE_STORE_CACHE={'mtime':None,'data':None}
        mod.save_benchmark_profile_store(mod.default_benchmark_profile_store())
        mod.benchmark_profile_action('save','trial',{'temperature':.25,'ctx':20000})
        eq(mod.benchmark_profile_action('show','trial')['ctx'],20000)
        mod.benchmark_profile_action('duplicate','trial','trial_copy')
        mod.benchmark_profile_action('rename','trial_copy','trial_renamed')
        assert 'trial_renamed' in mod.benchmark_profile_action('list')
        mod.benchmark_profile_action('delete','trial_renamed')
        assert 'trial_renamed' not in mod.benchmark_profile_action('list')
    finally:
        mod.benchmark_profiles_path=old_path; mod._BENCH_PROFILE_STORE_CACHE=old_cache
        shutil.rmtree(root)


def test_tested_profile_artifact_and_client_import():
    records=[]
    for seed in (42,43,44):
        rec=_v174_summary_record(seed,.8,20.0,.2,4.0,f'run-{seed}','profile-a')
        rec['identity']['model_digest']='digest-a'
        rec['config']['backend_launch_fingerprint']='launch-a'
        rec['config']['effective_config']={
            'profile_fingerprint':'profile-a','primary_mode':'think','ctx':16384,'num_thread':8,
            'num_predict':2400,'temperature':.7,'top_p':.9,'top_k':30,'min_p':.02,
            'repeat_penalty':1.05,'seed':seed,
        }
        records.append(rec)
    artifact=mod.build_tested_profiles_artifact({'spec_fingerprint':'spec-a'},records)
    eq((artifact['schema'],artifact['schema_version']),('bull-tested-profiles',1))
    eq(len(artifact['profiles']),1)
    exported=artifact['profiles'][0]
    eq(exported['effective_profile_fingerprint'],'profile-a')
    eq(exported['client_profile']['think']['temperature'],.7)
    assert 'seed' not in exported['client_profile']['think']
    assert re.fullmatch(r'[0-9a-f]{64}',exported['client_profile_fingerprint'])
    assert exported['evidence_quality']['seed_imported'] is False
    assert exported['evidence_quality']['import_recommended'] is True

    root=Path(tempfile.mkdtemp()); source=root/'tested.json'
    old_path=mod.profiles_path; old_cache=dict(mod._PROFILE_STORE_CACHE)
    try:
        source.write_text(json.dumps(artifact,ensure_ascii=False),encoding='utf-8')
        mod.profiles_path=lambda:root/'model_profiles.json'
        mod._PROFILE_STORE_CACHE={'mtime':None,'data':None}
        imported=mod.import_tested_profile(source,exported['profile_id'])
        eq(imported['model'],'model-a'); eq(imported['profile']['ctx'],16384)
        eq(imported['profile']['think']['temperature'],.7)
        stored=json.loads((root/'model_profiles.json').read_text(encoding='utf-8'))
        eq(stored['version'],2)
        assert 'seed' not in stored['models']['model-a']['think']
        eq(stored['models']['model-a']['tested_profile_provenance']['effective_profile_fingerprint'],'profile-a')
        eq(stored['models']['model-a']['tested_profile_provenance']['client_profile_fingerprint'],exported['client_profile_fingerprint'])
    finally:
        mod.profiles_path=old_path; mod._PROFILE_STORE_CACHE=old_cache; shutil.rmtree(root,ignore_errors=True)


def test_v174_application_boundaries_and_shared_contracts():
    required=[
        ROOT/'Apps'/'benchmark_lab_v0_29_0_1.py',ROOT/'Apps'/'bull_client_app_v0_29_0_1.py',
        ROOT/'Apps'/'_bootstrap.py',ROOT/'Shared'/'bull_llm'/'schemas.py',
        ROOT/'Shared'/'bull_llm'/'profiles.py',ROOT/'Shared'/'bull_llm'/'telemetry.py',
        ROOT/'Shared'/'bull_llm'/'backends.py',ROOT/'BULL-Benchmark-Lab-v0.29.0.1.cmd',
    ]
    assert all(path.is_file() for path in required),[str(x) for x in required if not x.is_file()]
    sys.path.insert(0,str(ROOT))
    try:
        from Shared.bull_llm import schemas
        eq(schemas.BENCH_RECORD_SCHEMA_VERSION,mod.BENCH_RECORD_SCHEMA_VERSION)
        eq(schemas.BENCH_SUMMARY_SCHEMA_VERSION,11)
        eq(schemas.TESTED_PROFILE_SCHEMA_VERSION,1)
    finally:
        if sys.path and sys.path[0]==str(ROOT): sys.path.pop(0)
    lab=(ROOT/'Apps'/'benchmark_lab_v0_29_0_1.py').read_text(encoding='utf-8')
    client=(ROOT/'Apps'/'bull_client_app_v0_29_0_1.py').read_text(encoding='utf-8')
    assert "BULL_START_SURFACE']='benchmark'" in lab
    assert "BULL_START_SURFACE']='home'" in client


def test_icon_shortcut_and_release_assets():
    ico=ROOT/'BULL-v0.29.0.1.ico'
    data=ico.read_bytes()
    assert data[:4]==b'\x00\x00\x01\x00'
    eq(int.from_bytes(data[4:6],'little'),7)
    shortcut=(ROOT/'Tools/Update-BULL-Shortcuts.ps1').read_text(encoding='utf-8-sig')
    launcher=(ROOT/'BULL-v0.29.0.1.cmd').read_text(encoding='utf-8-sig')
    assert 'IconLocation' in shortcut and 'GetFolderPath("Programs")' in shortcut
    assert 'BULL.exe' in launcher
    assert (ROOT/'Setup.exe').is_file()
    asset_builder=(ROOT/'Tools'/'build_brand_assets.py').read_text(encoding='utf-8')
    assert 'contain(red_mark_source, (256, 256), padding=16).save(' in asset_builder


def test_windows_powershell_launcher_is_ascii_parse_safe():
    # Windows PowerShell 5.1 decodes a BOM-less .ps1 as the active ANSI code
    # page. Keep the tiny entry launcher ASCII-only so parsing cannot fail
    # before it enables UTF-8 for Python and child processes.
    launcher=ROOT/'BULL-v0.29.0.1.ps1'
    raw=launcher.read_bytes()
    assert raw and all(byte < 128 for byte in raw), 'launcher must remain ASCII-safe for powershell.exe 5.1'

    for rel in (
        'Setup.ps1',
        'Tools/Update-BULL-Shortcuts.ps1',
        'Server/Test-BULL-RemoteReadiness.ps1',
        'Client/New-BULL-ClientKey.ps1',
    ):
        payload=(ROOT/rel).read_bytes()
        assert payload.startswith(b'\xef\xbb\xbf') or all(byte < 128 for byte in payload), rel


RU_LANGUAGE_STRESS_GOLD={
    'ru_context_corrections':(
        'Текущее подтверждённое состояние: проект Vega, бюджет 1,65 млн рублей, '
        'дедлайн 7 октября 2026 года. Обработка выполняется только локально, облако '
        'полностью запрещено. Финальный отчёт должен быть на русском языке.\n\n'
        'Более новыми сообщениями пользователя заменены бюджет 1,8 млн рублей на '
        '1,65 млн и дедлайн 3 октября на 7 октября.\n\n'
        'Не подтверждены или противоречат словам пользователя заявления assistant о '
        'резервном копировании в облако и дедлайне 10 октября.\n'
        'BENCHMARK_RESULT\n'
        '{"project":"Vega","budget_rub":1650000,"deadline":"2026-10-07",'
        '"language":"русский","cloud_allowed":false,"superseded_budget_rub":1800000,'
        '"superseded_deadline":"2026-10-03","unsupported_cloud_backup":true,'
        '"unsupported_deadline":"2026-10-10"}'
    ),
    'ru_causality_precision':(
        'Наблюдаемое среднее время до ответа уменьшилось с 14 до 11 минут после запуска '
        'напоминаний. Однако это ещё не доказывает, что изменение вызвали именно '
        'напоминания. Одновременно доля пользователей, заходивших в будние дни, выросла '
        'с 58% до 71%, поэтому изменился состав наблюдаемой группы. Без контрольного '
        'эксперимента нельзя отделить влияние напоминаний от влияния этого сдвига. По '
        'имеющимся данным нельзя уверенно сказать ни что напоминания помогли, ни что они '
        'бесполезны. Более надёжный способ проверки - провести рандомизированный А/Б-тест: '
        'одной сопоставимой группе показывать напоминания, другой нет, а затем сравнить '
        'время до ответа при одинаковом порядке наблюдения.\n'
        'BENCHMARK_RESULT\n'
        '{"observed_time_decrease":true,"causality_proven":false,'
        '"reminders_disproven":false,"composition_changed":true,'
        '"controlled_test_recommended":true}'
    ),
    'ru_semantic_negation':(
        'После обновления среднее время ответа модели уменьшилось с 18 до 13 секунд, но '
        'само по себе это не доказывает роста качества. Средний балл при этом не '
        'снизился, однако из этого нельзя заключить, что в отдельных типах задач '
        'деградации нет. В коротких запросах ошибки стали встречаться реже, тогда как в '
        'длинных диалогах они участились. Скорость, средний балл и распределение ошибок '
        'здесь отражают разные стороны работы модели. Эти изменения направлены '
        'по-разному и не дают оснований для общего вывода. Поэтому нельзя утверждать ни '
        'что обновление однозначно улучшило модель, ни что оно в целом сделало её хуже.\n'
        'BENCHMARK_RESULT\n'
        '{"faster":true,"quality_improvement_proven":false,'
        '"no_degradation_proven":false,"short_errors_down":true,'
        '"long_errors_up":true,"overall_direction_proven":false}'
    ),
    'ru_business_tone':(
        'Коллега, отчёт пришёл с задержкой третий раз подряд. Текущий отчёт принимаем, '
        'переделывать его не нужно. Встреча завтра остаётся в силе. На будущее '
        'договоримся о чётком сроке: отчёт должен приходить до 15:00 за день до встречи. '
        'Так у нас будет время заранее ознакомиться с материалом и подготовиться к '
        'обсуждению. Рассчитываю, что дальше будем придерживаться этого порядка. Спасибо '
        'за понимание. Давайте дальше соблюдать этот срок без дополнительных напоминаний '
        'в каждом следующем рабочем цикле.\n'
        'BENCHMARK_RESULT\n'
        '{"third_consecutive_delay":true,"current_report_accepted":true,'
        '"redo_required":false,"future_deadline":"15:00_previous_day",'
        '"meeting_postponed":false}'
    ),
    'ru_debureaucratize':(
        'Анализ результатов уже проведён. Он показал, что многие пользователи прекращают '
        'регистрацию на этапе подтверждения электронной почты. Причины такого поведения '
        'пока неизвестны. Предлагаем дополнительно исследовать их, чтобы понять, что '
        'происходит на этом этапе. Исследование будет посвящено только причинам '
        'прекращения регистрации, без дополнительных выводов и лишних действий.\n'
        'BENCHMARK_RESULT\n'
        '{"analysis_completed":true,"dropoff_stage":"email_confirmation",'
        '"causes_known":false,"additional_research_proposed":true,'
        '"extra_business_claims":false}'
    ),
}


RU_LANGUAGE_STRESS_FIXTURE=(
    ROOT/'Tests'/'Fixtures'/'ru_language_stress_sanitized_v2.json'
)


def _ru_fixture_record(benchmark,model):
    fixture=json.loads(RU_LANGUAGE_STRESS_FIXTURE.read_text(encoding='utf-8'))
    return next(
        row for row in fixture['records']
        if row['identity']['benchmark']==benchmark and row['identity']['model']==model
    )


def test_ru_language_stress_v2_specs_gold_and_adversarial_contract():
    built=mod.builtin_benchmarks()
    expected={
        'ru_context_corrections','ru_causality_precision','ru_semantic_negation',
        'ru_business_tone','ru_debureaucratize',
    }
    eq({name for name,item in built.items() if item.get('category')=='ru_language_stress'},expected)
    for name in sorted(expected):
        item=built[name]
        eq(item['score_type'],'ru_language_stress_v3')
        assert 'prose_word_range' not in item,name
        constraints=item['constraints']
        eq(constraints['language'],'ru')
        changed=deepcopy(item); changed['constraints']['language']='en'
        assert mod.benchmark_test_execution_fingerprint(changed)!=mod.benchmark_test_execution_fingerprint(item)
        weights=item['scorer_config']['weights']
        assert abs(sum(weights.values())-1.0)<1e-12,(name,weights)
        word_range=constraints.get('word_range')
        if word_range:
            assert f'{word_range[0]}-{word_range[1]} слов' in item['prompt'],name
        else:
            assert not re.search(r'\b\d+\s*[-–]\s*\d+\s+слов',item['prompt']),name
        score=mod.benchmark_score(name,item,RU_LANGUAGE_STRESS_GOLD[name])
        eq(score['method'],'ru_language_stress_v3')
        eq(score['scorer_version'],3)
        eq(score['value'],1.0,(name,score))
        eq(
            set(score['subscores']),
            {
                'structured_semantics','format_constraints','prose_consistency',
                'forbidden_additions','language_quality','repetition',
            },
        )
        assert all(
            check.get('evidence') is not None or check.get('reason')
            for check in score['checks']
        ),(name,score['checks'])
        marker_only='BENCHMARK_RESULT\n'+json.dumps(item['reference'],ensure_ascii=False,separators=(',',':'))
        marker_score=mod.benchmark_score(name,item,marker_only)
        assert marker_score['value']<=.60,(name,marker_score)
        malformed=RU_LANGUAGE_STRESS_GOLD[name].rsplit('BENCHMARK_RESULT',1)[0]+'BENCHMARK_RESULT\n{"broken"'
        malformed_score=mod.benchmark_score(name,item,malformed)
        assert malformed_score['value']<=.45,(name,malformed_score)
        assert 'invalid_terminal_json' in (malformed_score['cap_applied'] or '')

    eq(built['ru_context_corrections']['constraints']['word_range'],None)
    eq(built['ru_business_tone']['constraints']['word_range'],[70,110])
    eq(built['ru_business_tone']['version'],2)

    causal=RU_LANGUAGE_STRESS_GOLD['ru_causality_precision'].replace(
        'нельзя уверенно сказать ни что напоминания помогли, ни что они бесполезны',
        'напоминания точно помогли'
    )
    contradicted=mod.benchmark_score('ru_causality_precision',built['ru_causality_precision'],causal)
    assert contradicted['contradiction_detected'] is True
    assert contradicted['value']<=.55,contradicted

    semantic=RU_LANGUAGE_STRESS_GOLD['ru_semantic_negation'].replace(
        'само по себе это не доказывает роста качества','качество ответов доказанно выросло'
    )
    contradicted=mod.benchmark_score('ru_semantic_negation',built['ru_semantic_negation'],semantic)
    assert contradicted['contradiction_detected'] is True
    assert contradicted['value']<=.55,contradicted


def test_ru_language_stress_v2_real_answers_fix_false_negatives_and_detect_defects():
    positive=[
        ('ru_causality_precision','fixture-model-a'),
        ('ru_semantic_negation','fixture-model-f'),
        ('ru_context_corrections','fixture-model-c'),
    ]
    for benchmark,model in positive:
        row=_ru_fixture_record(benchmark,model)
        rescored=mod._legacy_rescore_one(
            benchmark,row['identity']['benchmark_version'],row['final']['answer']
        )
        eq(rescored['method'],'ru_language_stress_v3')
        assert rescored['structured_exact'] is True
        assert rescored['contradiction_detected'] is False,(benchmark,model,rescored)
        assert rescored['value']>=row['score']['final']['value'],(
            benchmark,model,row['score']['final']['value'],rescored['value']
        )

    english=_ru_fixture_record(
        'ru_business_tone','fixture-model-d'
    )
    english_score=mod._legacy_rescore_one(
        'ru_business_tone',1,english['final']['answer']
    )
    eq(english_score['language']['classification'],'predominantly_non_russian')
    assert english_score['subscores']['language_quality']==0.0
    assert english_score['value']<=.55,english_score

    mixed=_ru_fixture_record(
        'ru_debureaucratize','fixture-model-d'
    )
    mixed_score=mod._legacy_rescore_one(
        'ru_debureaucratize',1,mixed['final']['answer']
    )
    assert mixed_score['language']['classification'] in {
        'mixed_language','predominantly_non_russian'
    }
    assert mixed_score['value']<=.65,mixed_score

    repeated=_ru_fixture_record(
        'ru_business_tone','fixture-model-c'
    )
    repeated_score=mod._legacy_rescore_one(
        'ru_business_tone',1,repeated['final']['answer']
    )
    assert repeated_score['repetition']['strong_repetition'] is True
    assert repeated_score['value']<=.75,repeated_score


def test_ru_language_stress_v2_offline_rescore_real_v1753_fixture():
    fixture=json.loads(RU_LANGUAGE_STRESS_FIXTURE.read_text(encoding='utf-8'))
    eq(len(fixture['records']),35)
    eq(
        {row['score']['final']['method'] for row in fixture['records']},
        {'ru_language_stress_v1'},
    )
    root=Path(tempfile.mkdtemp()); old_dir=mod.benchmark_dir
    try:
        mod.benchmark_dir=lambda create=True:root
        rescored,jp,cp,sj,sc=mod.rescore_benchmark_raw(RU_LANGUAGE_STRESS_FIXTURE)
        eq(len(rescored),35)
        assert jp.is_file() and cp.is_file() and sj.is_file() and sc.is_file()
        for before,after in zip(fixture['records'],rescored):
            eq(after['final']['answer'],before['final']['answer'])
            eq(after['score']['original'],before['score'])
            eq(after['score']['final']['method'],'ru_language_stress_v3')
            eq(after['rescore']['inference_rerun'],False)
            eq(after['rescore']['policy'],'ru_language_stress_v3_offline')
    finally:
        mod.benchmark_dir=old_dir; shutil.rmtree(root,ignore_errors=True)


def test_user_prompt_store_is_versioned_atomic_and_fail_closed():
    root=Path(tempfile.mkdtemp()); old_dir=mod.benchmark_dir
    try:
        mod.benchmark_dir=lambda create=True:root
        first=mod.save_user_benchmark('my_prompt','Первый prompt','Проверка')
        second=mod.save_user_benchmark('my_prompt','Второй prompt','Проверка 2')
        eq((first['version'],second['version']),(1,2))
        index=json.loads((root/'prompts.json').read_text(encoding='utf-8'))
        eq((index['schema'],index['schema_version']),('bull-prompt-index',2))
        entry=index['prompts']['my_prompt']; eq(entry['active_version'],2); eq(len(entry['versions']),2)
        v1=root/entry['versions'][0]['path']; v2=root/entry['versions'][1]['path']
        assert v1.is_file() and v2.is_file() and v1!=v2
        eq(json.loads(v1.read_text(encoding='utf-8'))['prompt'],'Первый prompt')
        eq(json.loads(v2.read_text(encoding='utf-8'))['prompt'],'Второй prompt')
        loaded=mod.load_benchmarks()['my_prompt']
        eq((loaded['version'],loaded['prompt'],loaded['source']),(2,'Второй prompt','user'))
        eq(mod.load_user_benchmark_version('my_prompt',1)['prompt'],'Первый prompt')

        before=list(root.rglob('v*.json'))
        (root/'prompts.json').write_text('{broken',encoding='utf-8')
        try:
            mod.save_user_benchmark('my_prompt','Нельзя потерять историю')
            raise AssertionError('corrupt prompt index must fail closed')
        except ValueError as exc:
            assert 'prompts.json' in str(exc)
        eq(list(root.rglob('v*.json')),before)
    finally:
        mod.benchmark_dir=old_dir; shutil.rmtree(root,ignore_errors=True)


def test_custom_prompt_wizard_builds_simple_standard_command():
    root=Path(tempfile.mkdtemp()); old_dir=mod.benchmark_dir
    old_input,old_models,old_show=mod.read_user_input,mod.installed_models,mod.show_models
    answers=iter(['1','my_prompt','Проверка своего prompt','Сам пользовательский prompt','all','','','y'])
    try:
        mod.benchmark_dir=lambda create=True:root
        mod.read_user_input=lambda prompt='':next(answers)
        mod.installed_models=lambda:[{'name':'m1'},{'name':'m2'}]
        mod.show_models=lambda models,current=None:None
        command=mod.benchmark_custom_prompt_wizard()
        eq(command,'/bench compare my_prompt m1,m2 3 native sweep profile=fair_default sampling_source=benchmark_override')
        eq(mod.benchmark_command_model_selector(['m1','m2']),'m1,m2')
        assert (root/'prompts.json').is_file()
    finally:
        mod.benchmark_dir=old_dir; mod.read_user_input=old_input
        mod.installed_models=old_models; mod.show_models=old_show
        shutil.rmtree(root,ignore_errors=True)


def test_spec_snapshots_exact_custom_prompt():
    root=Path(tempfile.mkdtemp()); old_dir=mod.benchmark_dir
    old_digest,old_profile,old_caps=mod.model_digest,mod.model_profile,mod.cached_model_capabilities
    try:
        mod.benchmark_dir=lambda create=True:root
        mod.save_user_benchmark('snapshot_case','Точный текст prompt')
        mod.model_digest=lambda model,catalog=None:'digest'
        mod.model_profile=lambda model:{
            'ctx':8192,'threads':12,
            'fast':{'num_predict':512,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42},
            'think':{'num_predict':3200,'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42},
            'ultimate':{'num_predict':5000,'temperature':1.0,'top_p':.95,'top_k':20,'min_p':0.0,'seed':42},
        }
        mod.cached_model_capabilities=lambda model,refresh=False:['thinking']
        spec=mod.make_benchmark_spec(['snapshot_case'],['m'],1,False,catalog={'m':{'digest':'digest'}})
        snap=spec['test_snapshots']['snapshot_case']
        eq((snap['prompt'],snap['version'],snap['source']),('Точный текст prompt',1,'user'))
        eq(snap['prompt_sha256'],mod.benchmark_prompt_sha256(mod.load_benchmarks()['snapshot_case']))
    finally:
        mod.benchmark_dir=old_dir; mod.model_digest=old_digest
        mod.model_profile=old_profile; mod.cached_model_capabilities=old_caps
        shutil.rmtree(root,ignore_errors=True)


def test_single_seed_rank_stability_is_insufficient_and_runtime_fingerprints_are_plural():
    a=_v174_summary_record(42,.8,20.0,.2,4.0,'run-a','profile-a')
    b=_v174_summary_record(42,.7,22.0,.2,4.0,'run-b','profile-b')
    b['identity']['model']='model-b'; b['identity']['model_digest']='digest-b'
    a['telemetry']['runtime']['observed_fingerprint']='runtime-a'
    b['telemetry']['runtime']['observed_fingerprint']='runtime-b'
    a['config']['backend_launch_fingerprint']='launch-a'
    b['config']['backend_launch_fingerprint']='launch-b'
    rows=mod.benchmark_summary_rows([a,b])
    for row in rows:
        assert row['rank_stability'] is None
        eq(row['rank_stability_status'],'insufficient_seeds')
        assert len(row['observed_runtime_fingerprints'])==1
        assert len(row['backend_launch_fingerprints'])==1
        assert len(row['effective_runtime_request_fingerprints'])==1
    fp_a=mod.effective_runtime_request_fingerprint('model-a',{'fingerprint':'run-a'},'launch-same')
    fp_b=mod.effective_runtime_request_fingerprint('model-a',{'fingerprint':'run-b'},'launch-same')
    assert fp_a!=fp_b,'effective request fingerprint must change without pretending backend launch changed'


def test_tested_profiles_require_scored_multiseed_evidence():
    unscored=_v174_summary_record(42,None,20.0,.2,4.0,'run-42','profile-u')
    unscored['score']['native']['value']=None; unscored['score']['final']['value']=None
    unscored['config']['effective_config']={'profile_fingerprint':'profile-u','primary_mode':'fast','ctx':8192,'num_thread':12,'num_predict':512,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':42}
    artifact=mod.build_tested_profiles_artifact({'spec_fingerprint':'s'},[unscored])
    eq(artifact['profiles'],[]); assert artifact['excluded_profiles']

    records=[]
    for seed in (42,43,44):
        rec=_v174_summary_record(seed,.8,20.0,.2,4.0,f'run-{seed}','profile-ok')
        rec['identity']['model_digest']='digest-a'; rec['config']['backend_launch_fingerprint']='launch-a'
        rec['config']['effective_config']={'profile_fingerprint':'profile-ok','primary_mode':'fast','ctx':8192,'num_thread':12,'num_predict':512,'temperature':.2,'top_p':.85,'top_k':40,'min_p':.05,'seed':seed}
        records.append(rec)
    artifact=mod.build_tested_profiles_artifact({'spec_fingerprint':'s'},records)
    eq(len(artifact['profiles']),1)
    assert artifact['profiles'][0]['evidence_quality']['import_recommended'] is True


def test_tested_profiles_deduplicate_same_importable_configuration():
    records=[]
    for test,profile_fp in (('case-a','profile-a'),('case-b','profile-b')):
        for seed in (42,43,44):
            rec=_v174_summary_record(seed,.8,20.0,.2,4.0,f'{test}-run-{seed}',profile_fp)
            rec['identity']['benchmark']=test
            rec['identity']['model_digest']='digest-a'
            rec['config']['backend_launch_fingerprint']='launch-a'
            rec['config']['effective_config']={
                'profile_fingerprint':profile_fp,'primary_mode':'fast','ctx':8192,
                'num_thread':12,'num_predict':512,'temperature':.2,'top_p':.85,
                'top_k':40,'min_p':.05,'repeat_penalty':1.0,'seed':seed,
            }
            records.append(rec)
    artifact=mod.build_tested_profiles_artifact({'spec_fingerprint':'s'},records)
    eq(len(artifact['profiles']),1)
    profile=artifact['profiles'][0]
    eq(profile['effective_profile_fingerprints'],['profile-a','profile-b'])
    eq(len(profile['evidence']),2)
    eq(profile['evidence_quality']['executed_runs'],6)
    assert 'seed' not in profile['client_profile']['fast']


def test_csv_export_neutralizes_spreadsheet_formulas_without_changing_json():
    root=Path(tempfile.mkdtemp()); old_dir=mod.benchmark_dir
    try:
        mod.benchmark_dir=lambda create=True:root
        rec={'identity':{'benchmark':'x','model':'=HYPERLINK("http://bad")'},'primary':{'answer':'+cmd|test'},'score':{'final':{'value':1.0}}}
        jp,cp=mod.save_benchmark_results('formula',[rec])
        eq(json.loads(jp.read_text(encoding='utf-8'))[0]['primary']['answer'],'+cmd|test')
        with cp.open(encoding='utf-8-sig',newline='') as f: row=next(csv.DictReader(f))
        assert row['identity.model'].startswith("'=")
        assert row['primary.answer'].startswith("'+")
    finally:
        mod.benchmark_dir=old_dir; shutil.rmtree(root,ignore_errors=True)


def test_matrix_ui_primitives_are_consistent_and_accessible_without_color():
    old_color=mod._COLOR_ENABLED
    mod._COLOR_ENABLED=False
    try:
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            mod.ui_header('CONTROL DECK','Главное меню','NODE ONLINE')
            mod.ui_section('БЫСТРЫЙ СТАРТ')
            mod.ui_menu_item('1','Рабочий чат','Диалог, файлы и инструменты','DAILY')
            mod.ui_status_strip([('NODE','ONLINE','ok'),('MODE','THINK','info')])
            mod.ui_footer('главное меню')
        text=out.getvalue()
        assert 'CONTROL DECK' in text and 'Главное меню' in text
        assert 'MATRIX NODE' not in text and '01001100' not in text
        assert '[1]' in text and 'Рабочий чат' in text and 'DAILY' in text
        assert 'OK · NODE: ONLINE' in text and 'INFO · MODE: THINK' in text
        assert 'Введите номер пункта' in text and '[?] Помощь' not in text
        assert any(line.startswith('━') for line in text.splitlines())
    finally:
        mod._COLOR_ENABLED=old_color


def test_matrix_benchmark_menu_copy_and_advanced_navigation_are_consistent():
    old_clear=mod.clear_console; old_sleep=mod.time.sleep
    mod.clear_console=lambda:None; mod.time.sleep=lambda _x:None
    try:
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            cmd,home=_with_inputs(['0'],mod.startup_benchmark_wizard)
        eq((cmd,home),('/home',False))
        text=out.getvalue()
        assert 'Задача из UserTests' in text and 'Мой промпт' in text
        assert 'Сравнить по набору тестов' in text and 'Восстановить и продолжить' in text
        assert 'Библиотека наборов тестов' not in text
        assert 'Посмотреть результаты' in text and 'Языковые треки' in text
        assert 'Agent Benchmark' not in text and 'GPU Lab' not in text
        eq(_with_fake_inputs(['0'],mod.benchmark_advanced_menu),('__benchmark_menu__',False))
        eq(_with_fake_inputs(['h'],mod.benchmark_advanced_menu),('/home',False))
    finally:
        mod.clear_console=old_clear; mod.time.sleep=old_sleep


def test_main_does_not_shadow_backend_version_probe():
    import symtable
    source=CLIENT.read_text(encoding='utf-8')
    root_table=symtable.symtable(source,str(CLIENT),'exec')
    main_table=next(child for child in root_table.get_children() if child.get_name()=='main')
    version_symbol=main_table.lookup('version')
    assert version_symbol.is_global() and not version_symbol.is_local(),(
        'main() must call the global backend version() probe; '
        'a local variable named version makes startup fail before Ollama connects'
    )


def test_startup_backend_failure_is_offline_first_and_does_not_switch_backend():
    source=CLIENT.read_text(encoding='utf-8')
    startup=source[source.index("initialize_backend_from_settings()",source.index('def main():')):
                   source.index("models=installed_models() if backend_ready else []")]
    assert "backend_info={'backend':ACTIVE_BACKEND,'version':'offline','status':'offline'}" in startup
    assert 'render_startup_connection_result(False)' in startup
    assert "append_client_debug('STARTUP_BACKEND_OFFLINE '" in startup
    assert 'connection_menu()' not in startup
    assert "set_backend('ollama',persist=False)" not in startup


def test_main_reaches_home_when_backend_is_offline():
    names=(
        'console_utf8','initialize_ui_theme','select_ui_language','enable_console_colors','set_console_icon',
        'white','gray','yellow','green','set_console_title','clear_console','newfile',
        'run_startup_regression','initialize_backend_from_settings','connect_active_backend',
        'version','startup_home_menu','installed_models','set_active_model','maybe_save',
        'save_session','benchmark_pack_selection_menu',
    )
    old={name:getattr(mod,name) for name in names}; old_sleep=mod.time.sleep
    noop=lambda *args,**kwargs:None
    try:
        for name in ('console_utf8','initialize_ui_theme','select_ui_language','enable_console_colors','set_console_icon',
                     'white','gray','yellow','green','set_console_title','clear_console','set_active_model'):
            setattr(mod,name,noop)
        mod.newfile=lambda mode:Path('offline-startup-test.json')
        mod.run_startup_regression=lambda **kwargs:{'ok':True,'summary':'208/208','output':''}
        mod.initialize_backend_from_settings=noop
        mod.benchmark_pack_selection_menu=noop
        mod.connect_active_backend=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('offline test'))
        mod.version=lambda timeout=2:None
        mod.startup_home_menu=lambda backend_version,regression_summary:'exit'
        mod.installed_models=lambda:(_ for _ in ()).throw(AssertionError('offline startup queried models'))
        mod.maybe_save=lambda *a,**k:False
        mod.save_session=noop; mod.time.sleep=lambda _x:None
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            eq(mod.main(),0)
        startup_text=out.getvalue()
        assert 'Нет соединения с моделями' in startup_text
        assert 'Остальные функции BULL доступны офлайн' in startup_text
        assert 'offline test' not in startup_text
    finally:
        for name,value in old.items():
            setattr(mod,name,value)
        mod.time.sleep=old_sleep


def test_connection_menu_returns_immediate_reconnect_after_selection():
    old_clear=mod.clear_console; old_sleep=mod.time.sleep
    old_entries=mod.connection_entries; old_summary=mod.remote_access_summary
    old_local=mod.use_local_backend
    called=[]
    mod.clear_console=lambda:None; mod.time.sleep=lambda _x:None
    mod.connection_entries=lambda:[]; mod.remote_access_summary=lambda:'local'
    mod.use_local_backend=lambda:called.append('local') or 'local'
    try:
        result=_with_inputs(['1'],mod.connection_menu)
        eq(result,'__connection_changed__')
        eq(called,['local'])
        source=CLIENT.read_text(encoding='utf-8')
        reconnect=source[source.index("if u=='/remote reconnect':"):source.index("if u in ('/help','/?'):")]
        assert "queued_u='/home'" in reconnect
    finally:
        mod.clear_console=old_clear; mod.time.sleep=old_sleep
        mod.connection_entries=old_entries; mod.remote_access_summary=old_summary
        mod.use_local_backend=old_local


def test_benchmark_runtime_guard_keeps_reports_available_offline():
    old_clear=mod.clear_console; old_sleep=mod.time.sleep
    old_report=mod.benchmark_report_browser; old_resume=mod.checkpoint_resume_menu_state
    guards=[]; reports=[]
    mod.clear_console=lambda:None; mod.time.sleep=lambda _x:None
    mod.benchmark_report_browser=lambda:reports.append('opened')
    mod.checkpoint_resume_menu_state=lambda:('Resume','Незавершённых запусков нет','IDLE')
    try:
        result=_with_inputs(
            ['5'],
            lambda:mod.startup_benchmark_wizard(
                runtime_guard=lambda purpose:guards.append(purpose) or False
            )
        )
        eq(result,('/bench report',False))
        eq(guards,[])
        eq(reports,[])
    finally:
        mod.clear_console=old_clear; mod.time.sleep=old_sleep
        mod.benchmark_report_browser=old_report; mod.checkpoint_resume_menu_state=old_resume


def test_v18_public_defaults_are_local_and_identity_free():
    settings=mod.default_backend_settings()
    eq(settings['version'],3)
    eq(settings['target_mode'],'local')
    eq(settings['remote_access']['mode'],'manual')
    eq(settings['remote_access']['selected_connection_id'],'')
    assert all(not row['enabled'] for row in settings['remote_access']['profiles'].values())
    assert all(not row['host'] and not row['user'] and not row['identity_file']
               for row in settings['remote_access']['profiles'].values())
    eq(settings['ollama']['transport'],'local')
    eq(settings['ollama']['base_url'],'http://127.0.0.1:11434')
    eq(settings['ollama']['auto_tunnel'],False)
    eq(settings['llama_cpp']['transport'],'external')
    eq(settings['llama_cpp']['base_url'],'http://127.0.0.1:8080')
    eq(settings['llama_cpp']['server_path'],'')
    eq(settings['llama_cpp']['models_dir'],'')

    # backend_settings.json becomes user-owned mutable state after install.
    # Runtime regression must therefore validate the code defaults, not demand
    # that a user's selected backend still equals the public release template.
    # The immutable payload is checked separately by both release gates.
    build=(ROOT/'Build-Release.ps1').read_text(encoding='utf-8-sig')
    audit=(ROOT/'Test-Public-Release.ps1').read_text(encoding='utf-8-sig')
    assert 'Public backend_settings.json must be schema v3 with target_mode=local.' in build
    assert 'public backend settings select a remote target' in audit
    source=CLIENT.read_text(encoding='utf-8').casefold()
    assert 'lab-user' not in source
    assert "ssh_host='lab-node'" not in source and "'ssh_host':'lab-node'" not in source


def test_v18_local_ollama_connect_never_opens_ssh():
    old_load,old_version,old_tunnel=mod.load_backend_settings,mod.version,mod.tunnel
    try:
        mod.load_backend_settings=lambda:mod.default_backend_settings()
        mod.version=lambda timeout=1:{'version':'test-local'}
        mod.tunnel=lambda:(_ for _ in ()).throw(AssertionError('local mode opened SSH tunnel'))
        tp,info=mod.connect_active_backend()
        assert tp is None
        eq(info['version'],'test-local')
    finally:
        mod.load_backend_settings,mod.version,mod.tunnel=old_load,old_version,old_tunnel


def test_v18_connection_bundle_keeps_endpoint_and_key_out_of_public_config():
    root=Path(tempfile.mkdtemp())
    old_backend,old_store=mod.backend_settings_path,mod.connection_store_path
    try:
        mod.backend_settings_path=lambda:root/'backend_settings.json'
        mod.connection_store_path=lambda:root/'Runtime'/'connections.json'
        key=root/'id_bull_test'
        key.write_text('test-private-key-placeholder',encoding='utf-8')
        bundle=root/'lab.connection.json'
        host_blob=base64.b64encode(b'unit-test-host-key-material-a'*2).decode('ascii')
        host_fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(host_blob)).digest()).decode('ascii').rstrip('=')
        bundle.write_text(json.dumps({
            'schema':'bull-connection','version':1,'id':'lab-a','name':'Test Lab',
            'route':'overlay','transport':'ssh',
            'endpoint':{'host':'100.64.0.10','port':22,'user':'lab-user'},
            'backend':{'type':'ollama','remote_port':11434},
            'host_public_key':'ssh-ed25519 '+host_blob,
            'host_key_fingerprint':host_fingerprint
        }),encoding='utf-8')
        entry=mod.import_connection_bundle(bundle,key,activate=True)
        eq(entry['id'],'lab-a')
        stored=json.loads(mod.connection_store_path().read_text(encoding='utf-8'))
        eq(stored['active'],'lab-a')
        eq(stored['connections']['lab-a']['identity_file'],str(key.resolve()))
        settings=json.loads(mod.backend_settings_path().read_text(encoding='utf-8'))
        eq(settings['target_mode'],'remote')
        eq(settings['remote_access']['selected_connection_id'],'lab-a')
        serialized=json.dumps(settings,ensure_ascii=False)
        assert '100.64.0.10' not in serialized and 'lab-user' not in serialized
        assert str(key.resolve()) not in serialized
        ep=mod.resolve_remote_endpoint(force=True)
        eq((ep['host'],ep['user'],ep['identity_file'],ep['kind']),
           ('100.64.0.10','lab-user',str(key.resolve()),'vpn'))
        assert not mod.connection_store_path().with_suffix('.json.tmp').exists()
    finally:
        mod.reset_remote_endpoint_cache()
        mod.backend_settings_path,mod.connection_store_path=old_backend,old_store
        shutil.rmtree(root,ignore_errors=True)


def test_v18_connection_bundle_fails_closed_on_secret_or_missing_key():
    root=Path(tempfile.mkdtemp())
    old_backend,old_store=mod.backend_settings_path,mod.connection_store_path
    try:
        mod.backend_settings_path=lambda:root/'backend_settings.json'
        mod.connection_store_path=lambda:root/'Runtime'/'connections.json'
        host_blob=base64.b64encode(b'unit-test-host-key-material-b'*2).decode('ascii')
        host_fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(host_blob)).digest()).decode('ascii').rstrip('=')
        valid={
            'schema':'bull-connection','version':1,'id':'lab-a','name':'Lab',
            'route':'direct','transport':'ssh',
            'endpoint':{'host':'example.test','port':2222,'user':'runner'},
            'backend':{'type':'ollama','remote_port':11434},
            'host_public_key':'ssh-ed25519 '+host_blob,
            'host_key_fingerprint':host_fingerprint
        }
        bundle=root/'connection.json'; bundle.write_text(json.dumps(valid),encoding='utf-8')
        try:
            mod.import_connection_bundle(bundle,root/'missing-key')
        except FileNotFoundError:
            pass
        else:
            raise AssertionError('missing private key accepted')
        bad=deepcopy(valid); bad['password']='must-not-be-stored'
        bundle.write_text(json.dumps(bad),encoding='utf-8')
        key=root/'id'; key.write_text('x',encoding='utf-8')
        try:
            mod.import_connection_bundle(bundle,key)
        except ValueError:
            pass
        else:
            raise AssertionError('secret-bearing connection bundle accepted')
    finally:
        mod.backend_settings_path,mod.connection_store_path=old_backend,old_store
        shutil.rmtree(root,ignore_errors=True)


def test_client_installer_and_release_secret_gate():
    installer=ROOT/'Setup.ps1'
    assert installer.is_file() and (ROOT/'Tools/install_bull.py').is_file()
    text=installer.read_text(encoding='utf-8-sig')
    for retired in ('$Role','AllInOne','RunAs','Install-BULL-Node'):
        assert retired not in text
    assert 'Language' in text and 'install_bull.py' in text
    assert not (ROOT/'Server/Install-BULL-Node.ps1').exists()
    build=(ROOT/'Build-Release.ps1').read_text(encoding='utf-8')
    for marker in ('OPENSSH|RSA|EC|DSA','*.llm-access*','connection*.private.json'):
        assert marker in build


def test_wan_readiness_keeps_inference_private():
    readiness=(ROOT/'Server/Test-BULL-RemoteReadiness.ps1').read_text(encoding='utf-8-sig')
    guide=(ROOT/'Docs/REMOTE_ACCESS.md').read_text(encoding='utf-8')
    assert "LocalPort 22" in guide and "11434" in guide and "8080" in guide
    assert 'не поддерживает автоматическое изменение настроек роутера' in guide
    for marker in ('passwordauthentication no','kbdinteractiveauthentication no',
                   'authenticationmethods publickey','Inference port $port','NOT READY'):
        assert marker.casefold() in readiness.casefold()


def test_wan_ssh_transport_has_keepalive_and_clear_internet_ui():
    ep={'host':'203.0.113.10','port':48222,'user':'lab-user',
        'identity_file':r'C:\\Users\\me\\.ssh\\id_ed25519','kind':'direct_ssh','enabled':True}
    args=mod._ssh_base_args(ep,batch=True,connect_timeout=4)
    joined=' '.join(args)
    for marker in ('BatchMode=yes','TCPKeepAlive=yes','ServerAliveInterval=15',
                   'ServerAliveCountMax=4','ConnectionAttempts=2'):
        assert marker in joined
    source=CLIENT.read_text(encoding='utf-8')
    connection_ui=(ROOT/'Shared/bull_llm/connections_ui.py').read_text(encoding='utf-8')
    assert 'Как подключаться через Интернет' in connection_ui
    assert 'core.show_internet_access_guide()' in connection_ui
    assert 'Ollama остаётся доступна только через SSH-туннель' in source


def test_ru_language_stress_v3_catalog_preserves_prompts_and_scale():
    benches=mod.builtin_benchmarks()
    expected_prompts={
        'ru_context_corrections':'16b7ae7ede77edf20cf6436b63cf82f35a751a0528f5167b3c70fecd4aa8be32',
        'ru_causality_precision':'3cfbfa90d4b065cdfe139d9471f9a8cdbc728883d97861acd41fa1c6e04e6094',
        'ru_semantic_negation':'7fc60cfc94cbaba1920d43f93273616d5a47914903ffbb4d2ecb9b3de924ac93',
        'ru_business_tone':'1943987b9f64044ba4ab1730acede2588d39f8d4fd220dd84bd816f864fe230c',
        'ru_debureaucratize':'bf1101bfd391c72f063fa72987e7c13afebcd407d9fb9f0cdc26cb02426be236',
    }
    old_execution={
        'ru_context_corrections':'ddd54469dd1b4ebeb4e7dd1f4e04c87337933ef383f1515f6b1026a70aedb44c',
        'ru_causality_precision':'b2194a4bb3847501a0644513c0c28b7ed844213a0dfcc86ee0abb768aeb14e76',
        'ru_semantic_negation':'7a73cd3f4554b1ba58b9442d4efb52615ee8cb5a3052358f2ac85645faf1f0dd',
        'ru_business_tone':'9e5ce5852cc75e21fb0cc18f76b87ea61cd9d2661ffb67ef9d0751979a47d3a7',
        'ru_debureaucratize':'30caca7acefc3d3dadce7bc3fbf3f0d548b2175260edb6ef0069bd2340c1e120',
    }
    for name,prompt_sha in expected_prompts.items():
        item=benches[name]
        eq(item['score_type'],'ru_language_stress_v3')
        eq(item['scorer_config']['version'],3)
        eq(item['scorer_config']['weights'],mod.RU_LANGUAGE_STRESS_V2_WEIGHTS)
        eq(item['scorer_config']['caps'],mod.RU_LANGUAGE_STRESS_V2_CAPS)
        eq(mod.benchmark_prompt_sha256(item),prompt_sha)
        assert mod.benchmark_test_execution_fingerprint(item)!=old_execution[name]
    sem=benches['ru_semantic_negation']['constraints']
    eq(sem['required_semantic_numbers'],[18,13])
    assert not sem.get('required_exact_literals')
    eq(benches['ru_business_tone']['constraints']['required_exact_literals'],['15:00'])


def test_ru_language_stress_v3_deterministic_fixture_set():
    fixture=json.loads(SCORER_V3_FIXTURE.read_text(encoding='utf-8'))
    benches=mod.builtin_benchmarks()
    assert len(fixture['cases'])>=10
    for case in fixture['cases']:
        score=mod.benchmark_score(case['benchmark'],benches[case['benchmark']],case['answer'])
        expected=case['expect']
        if case['benchmark'].startswith('ru_'):
            eq(score['method'],'ru_language_stress_v3',case['id'])
        if 'confirmed_contradiction' in expected:
            eq(score['contradiction_status']=='confirmed',expected['confirmed_contradiction'],case['id'])
        if expected.get('cap'):
            assert expected['cap'] in {x['name'] for x in score.get('caps_applied',[])},(case['id'],score)
        if 'semantic_numbers' in expected:
            eq(score['semantic_numeric_values']['missing'],[],case['id'])
            eq(score['semantic_numeric_values']['present'],expected['semantic_numbers'],case['id'])
        if expected.get('critical_forbidden_addition'):
            assert score['critical_forbidden_additions'],(case['id'],score)
        if expected.get('language'):
            eq(score['language']['classification'],expected['language'],case['id'])
        if 'score' in expected:
            close(score['value'],expected['score'])


def test_ru_v3_context_claim_roles_are_tri_state_and_auditable():
    fixture=json.loads(SCORER_V3_FIXTURE.read_text(encoding='utf-8'))
    cases={x['id']:x for x in fixture['cases']}
    item=mod.builtin_benchmarks()['ru_context_corrections']
    good=mod.benchmark_score('ru_context_corrections',item,cases['context_superseded']['answer'])
    contexts={x['context'] for x in good['claim_events']}
    assert {'SUPERSEDED_VALUE','ERROR_DESCRIPTION'}<=contexts,good['claim_events']
    assert not [x for x in good['hard_cap_events'] if x['status']=='confirmed']
    assert all({'name','status','confidence','evidence','sentence','reason'}<=set(x) for x in good['hard_cap_events'])
    bad=mod.benchmark_score('ru_context_corrections',item,cases['context_current_deadline_conflict']['answer'])
    confirmed=[x for x in bad['hard_cap_events'] if x['status']=='confirmed']
    assert confirmed and all(float(x['confidence'])>=0.9 for x in confirmed)
    assert all(x['sentence'] and x['evidence'] and x['reason'] for x in confirmed)


def test_ru_v3_real_v176_false_positives_removed_true_defects_preserved():
    fixture=json.loads(RU_LANGUAGE_STRESS_V176_FIXTURE.read_text(encoding='utf-8'))
    benches=mod.builtin_benchmarks()
    rows={(x['model'],x['benchmark']):x for x in fixture['records']}
    semantic=mod.benchmark_score('ru_semantic_negation',benches['ru_semantic_negation'],rows[('fixture-model-c','ru_semantic_negation')]['answer'])
    eq(semantic['structured_exact'],True)
    assert 'critical_contradiction' not in {x['name'] for x in semantic['caps_applied']}
    eq(semantic['semantic_numeric_values']['missing'],[])
    context=mod.benchmark_score('ru_context_corrections',benches['ru_context_corrections'],rows[('fixture-model-b','ru_context_corrections')]['answer'])
    assert 'critical_contradiction' not in {x['name'] for x in context['caps_applied']}
    causality=mod.benchmark_score('ru_causality_precision',benches['ru_causality_precision'],rows[('fixture-model-c','ru_causality_precision')]['answer'])
    assert 'critical_forbidden_addition' in {x['name'] for x in causality['caps_applied']}
    repeated=mod.benchmark_score('ru_business_tone',benches['ru_business_tone'],rows[('fixture-model-c','ru_business_tone')]['answer'])
    assert repeated['repetition']['strong_repetition'] is True
    assert 'strong_repetition' in {x['name'] for x in repeated['caps_applied']}
    assert 'consistently' in [x.casefold() for x in repeated['language']['unexpected_latin_tokens']]


def test_groundedness_adversarial_catalog_and_deterministic_gold():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    eq((item['category'],item['version'],item['score_type']),('groundedness_security',1,'groundedness_adversarial_v1'))
    fixture=json.loads(SCORER_V3_FIXTURE.read_text(encoding='utf-8'))
    case=next(x for x in fixture['cases'] if x['id']=='groundedness_injection')
    score=mod.benchmark_score('groundedness_adversarial',item,case['answer'])
    close(score['value'],1.0)
    eq(score['embedded_instruction_ignored'],True)
    assert score['structured_exact'] is True


def _groundedness_cases(case_ids=('A','B','C')):
    rows=deepcopy(mod.builtin_benchmarks()['groundedness_adversarial']['reference']['cases'])
    for row,case_id in zip(rows,case_ids):
        row['id']=case_id
    return rows


def _groundedness_answer(payload,prose=''):
    prefix=(str(prose).rstrip()+'\n\n') if prose else ''
    return prefix+'BENCHMARK_RESULT\n'+json.dumps(payload,ensure_ascii=False,indent=2)


def test_chat_scorer_exact_groundedness_object_keeps_full_score():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    score=mod.benchmark_score('groundedness_adversarial',item,_groundedness_answer({'cases':_groundedness_cases()}))
    close(score['value'],1.0)
    assert score['terminal_json_valid'] is True
    assert score['schema_exact'] is True
    close(score['semantic_field_accuracy'],1.0)


def test_chat_scorer_groundedness_root_array_scores_semantics():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    score=mod.benchmark_score('groundedness_adversarial',item,_groundedness_answer(_groundedness_cases()))
    assert score['terminal_json_valid'] is True
    assert score['schema_exact'] is False
    close(score['semantic_field_accuracy'],1.0)
    assert 0.0<score['value']<1.0
    assert score['parse_error'] is None


def test_chat_scorer_groundedness_markdown_json_root():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    payload=json.dumps({'cases':_groundedness_cases()},ensure_ascii=False,indent=2)
    answer='BENCHMARK_RESULT\n```json\n'+payload+'\n```'
    score=mod.benchmark_score('groundedness_adversarial',item,answer)
    assert score['terminal_json_valid'] is True
    assert score['schema_exact'] is True
    close(score['value'],1.0)


def test_chat_scorer_groundedness_rejects_text_after_json():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    answer=_groundedness_answer({'cases':_groundedness_cases()})+'\nлишний текст'
    score=mod.benchmark_score('groundedness_adversarial',item,answer)
    assert score['terminal_json_valid'] is False
    eq(score['parse_error'],'trailing_text_after_json')
    close(score['semantic_field_accuracy'],1.0)


def test_chat_scorer_groundedness_normalizes_case_ids_for_semantics_only():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    score=mod.benchmark_score(
        'groundedness_adversarial',item,
        _groundedness_answer(_groundedness_cases(('CASE A','CASE B','CASE C'))),
    )
    assert score['schema_exact'] is False
    close(score['semantic_field_accuracy'],1.0)


def test_chat_scorer_wrong_groundedness_envelope_does_not_zero_content():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    score=mod.benchmark_score('groundedness_adversarial',item,_groundedness_answer(_groundedness_cases()))
    assert score['structured_exact'] is False
    assert score['content_score']==1.0
    assert score['format_score']<1.0
    assert score['value']>0.75


def test_chat_scorer_groundedness_prose_json_contradiction_is_separate():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    prose='''CASE A
supported: release_date_2026_08_20, offline_mode, cloud_sync_enabled
contradicted: cloud_sync_enabled
unknown: gpu_speedup_40_percent'''
    score=mod.benchmark_score(
        'groundedness_adversarial',item,
        _groundedness_answer({'cases':_groundedness_cases()},prose),
    )
    assert score['terminal_json_valid'] is True
    assert score['schema_exact'] is True
    assert score['prose_consistency'] is False
    assert any(x.get('claim')=='cloud_sync_enabled' for x in score['prose_consistency_events'])
    assert score['value']<1.0


def test_chat_scorer_context_rebuttal_is_not_current_deadline():
    item=mod.builtin_benchmarks()['ru_context_corrections']
    forms=(
        'Утверждение о дедлайне 10 октября было ошибочным.',
        'Assistant указал 10 октября, но пользователь установил 7 октября.',
        'Дедлайн 10 октября не подтверждался пользователем.',
        'Утверждение о дедлайне 10 октября противоречит последнему уточнению пользователя.',
        'Утверждение о дедлайне 10 октября 2026 года (пользователь установил 7 октября).',
    )
    suffix='''
BENCHMARK_RESULT
{"project":"Vega","budget_rub":1650000,"deadline":"2026-10-07","language":"русский","cloud_allowed":false,"superseded_budget_rub":1800000,"superseded_deadline":"2026-10-03","unsupported_cloud_backup":true,"unsupported_deadline":"2026-10-10"}'''
    for prose in forms:
        score=mod.benchmark_score('ru_context_corrections',item,prose+suffix)
        assert not [x for x in score['critical_contradictions'] if x['name']=='current_deadline_10_october_conflict'],(prose,score)


def test_chat_scorer_context_real_current_deadline_conflict_remains():
    item=mod.builtin_benchmarks()['ru_context_corrections']
    answer='''Текущий дедлайн проекта установлен на 10 октября.
BENCHMARK_RESULT
{"project":"Vega","budget_rub":1650000,"deadline":"2026-10-07","language":"русский","cloud_allowed":false,"superseded_budget_rub":1800000,"superseded_deadline":"2026-10-03","unsupported_cloud_backup":true,"unsupported_deadline":"2026-10-10"}'''
    score=mod.benchmark_score('ru_context_corrections',item,answer)
    assert any(x['name']=='current_deadline_10_october_conflict' for x in score['critical_contradictions'])


def _instruction_lines(with_prefixes=True,latin=False):
    if with_prefixes:
        rows=[
            'Преимущество: Данные остаются на локальном компьютере.',
            'Преимущество: Работа не зависит от подключения к интернету.',
            'Преимущество: Настройки можно адаптировать к рабочей задаче.',
            'Риск: Недостаток ресурсов может замедлить ответы.',
        ]
    else:
        rows=[
            'Данные остаются на локальном компьютере.',
            'Работа не зависит от подключения к интернету.',
            'Настройки можно адаптировать к рабочей задаче.',
            'Недостаток ресурсов может замедлить ответы.',
        ]
    if latin:
        rows[0]='Преимущество: Локальный API упрощает интеграцию.'
    return '\n'.join(rows)


def test_chat_scorer_instruction_accepts_required_russian_prefixes():
    item=mod.builtin_benchmarks()['instruction']
    score=mod.benchmark_score('instruction',item,_instruction_lines())
    close(score['value'],1.0)
    assert next(x for x in score['checks'] if x['name']=='required benefit/risk prefixes')['ok'] is True


def test_chat_scorer_instruction_without_prefixes_keeps_penalty():
    item=mod.builtin_benchmarks()['instruction']
    score=mod.benchmark_score('instruction',item,_instruction_lines(False))
    close(score['value'],.75)
    assert next(x for x in score['checks'] if x['name']=='required benefit/risk prefixes')['ok'] is False


def test_chat_scorer_instruction_latin_check_is_independent():
    item=mod.builtin_benchmarks()['instruction']
    score=mod.benchmark_score('instruction',item,_instruction_lines(True,True))
    assert next(x for x in score['checks'] if x['name']=='required benefit/risk prefixes')['ok'] is True
    assert next(x for x in score['checks'] if x['name']=='no Latin letters')['ok'] is False
    close(score['value'],.8)


def test_completion_facets_separate_generation_from_wrong_schema():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    answer=_groundedness_answer(_groundedness_cases())
    score=mod.benchmark_score('groundedness_adversarial',item,answer)
    facets=mod.benchmark_completion_facets('groundedness_adversarial',item,answer,'stop',score)
    assert facets=={
        'generation_completed':True,
        'structural_completion':False,
        'terminal_json_valid':True,
        'schema_exact':False,
        'task_completed':False,
    }


def test_completion_facets_detect_length_context_and_transport_interruptions():
    item=mod.builtin_benchmarks()['groundedness_adversarial']
    answer=_groundedness_answer({'cases':_groundedness_cases()})
    score=mod.benchmark_score('groundedness_adversarial',item,answer)
    for done_reason in ('length','context_length','num_predict'):
        facets=mod.benchmark_completion_facets('groundedness_adversarial',item,answer,done_reason,score)
        assert facets['generation_completed'] is False,(done_reason,facets)
        assert facets['task_completed'] is False,(done_reason,facets)
    error=mod.benchmark_error_record(
        'groundedness_adversarial',item,'model-x',1,'native','fixed',42,False,
        ConnectionError('transport interrupted'),catalog={'model-x':{'name':'model-x','digest':'d'}},
    )
    assert error['primary']['generation_completed'] is False
    assert error['primary']['task_completed'] is False
    eq(error['completion_status'],'not_executed')


def test_completion_summary_reports_generation_and_task_separately():
    record=_chat_record('groundedness_adversarial',42)
    record['primary'].update({
        'completed':True,'generation_completed':True,'task_completed':False,
        'structural_completion':False,'terminal_json_valid':True,'schema_exact':False,
    })
    record['final'].update({
        'completed':True,'generation_completed':True,'task_completed':False,
        'structural_completion':False,'terminal_json_valid':True,'schema_exact':False,
    })
    record['score']['native']['schema_exact']=False
    record['score']['final']['schema_exact']=False
    summary=mod.benchmark_summary_rows([record])[0]
    close(summary['native_generation_completion_rate'],1.0)
    close(summary['native_task_completion_rate'],0.0)
    close(summary['generation_completion_rate'],1.0)
    close(summary['task_completion_rate'],0.0)
    eq(summary['schema_violation_runs'],1)
    model=mod.benchmark_model_summary_rows([record])[0]
    close(model['native_generation_completion_rate'],1.0)
    close(model['native_task_completion_rate'],0.0)


def test_terminal_chat_summary_is_unambiguous_and_adds_comparative_analysis():
    records=[]
    low_tests=set(mod.CHAT_CORE_TESTS[:6])
    for model,base in (('model-alpha',.82),('model-beta',.78)):
        for seed in (42,43,44):
            for name in mod.CHAT_CORE_TESTS:
                score=.50 if model=='model-alpha' and name in low_tests else base
                row=_chat_record(name,seed,native_score=score,assisted_score=score)
                row['identity']['model']=model
                records.append(row)
    out=io.StringIO()
    with contextlib.redirect_stdout(out):
        mod.benchmark_summary(records,detailed=True)
    text=out.getvalue()
    assert 'GEN' in text and 'TASK' in text and 'REC.USED' in text
    assert 'СРАВНИТЕЛЬНАЯ АНАЛИТИКА' in text
    assert 'описательное сравнение' in text
    assert 'ещё ' in text and 'полный список' in text
    assert 'worst test:' in text
    brief=io.StringIO()
    with contextlib.redirect_stdout(brief):
        mod.benchmark_summary(records)
    assert 'ТОП-3' in brief.getvalue() and 'CPU' in brief.getvalue()
    assert 'МЕТРИКИ МОДЕЛЕЙ' in brief.getvalue()


def _chat_record(test,seed,native_score=.8,assisted_score=.9,recovery=False,native_completed=True,final_completed=True,caps=None):
    item=mod.builtin_benchmarks()[test]
    score_base={
        'method':item.get('score_type'),'value':native_score,'caps_applied':list(caps or []),
        'critical_contradictions':[],'critical_forbidden_additions':[],
        'structured_exact':True,
        'language':{'classification':'russian','unexpected_latin_word_count':0,'mixed_script_tokens':[]},
        'repetition':{'strong_repetition':False},
    }
    final_score=deepcopy(score_base);final_score['value']=assisted_score
    return {
        'record_schema_version':mod.BENCH_RECORD_SCHEMA_VERSION,'execution_status':'ok',
        'identity':{
            'benchmark':test,'benchmark_category':item.get('category'),'benchmark_version':item.get('version'),
            'benchmark_prompt_sha256':mod.benchmark_prompt_sha256(item),'benchmark_reference_sha256':mod.benchmark_reference_sha256(item),
            'backend':'ollama','model':'chat-model','model_digest':'digest-a','run':seed-41,
        },
        'config':{
            'benchmark_mode':'native','seed_mode':'sweep','seed':seed,'suite_think':False,
            'think_requested':False,'think':False,'think_override':item.get('think_override','inherit'),
            'ctx':16384,'threads':12,'effective_profile_fingerprint':'profile-a',
            'effective_config_fingerprint':f'cfg-{test}-{seed}',
        },
        'primary':{'completed':native_completed,'eval_rate':20.0+seed-42,'load_state':'warm','load_seconds':0.2,'answer':'Корректный русский ответ.'},
        'recovery':{'used':recovery,'wall_seconds':1.0 if recovery else 0.0,'total_eval_tokens':20 if recovery else 0},
        'final':{'completed':final_completed,'pipeline_wall_seconds':2.0,'answer':'Корректный русский ответ.'},
        'score':{'native':score_base,'final':final_score,'partial':None,'best_verified_partial':None},
        'telemetry':{'gpu':{'vram_peak_mib':4096,'gpu_util_avg':60},'runtime':{'gpu_offload_pct':100,'observed_fingerprint':'runtime-a'}},
        'client_recovery':{'attempt_count':1,'transport_failures':0},
    }


def test_chat_suites_final_preset_and_category_balanced_model_summary():
    expected=[
        'russian_editing','dialogue_state','groundedness','groundedness_adversarial','instruction',
        'ru_context_corrections','ru_causality_precision','ru_semantic_negation','ru_business_tone',
        'ru_debureaucratize','logic_constraints','simpson',
    ]
    eq(mod.benchmark_suite_tests('chat_core'),expected)
    preset=mod.chat_final_preset()
    eq((preset['runs'],preset['seed_mode'],preset['seeds'],preset['think'],preset['strict_fair_compare'],preset['order_policy']),
       (3,'sweep',[42,43,44],False,True,'balanced'))
    assert 'models' not in preset
    records=[]
    for test_name in expected:
        for seed in (42,43,44):
            records.append(_chat_record(test_name,seed,.8,.9,recovery=(test_name=='instruction' and seed==42)))
    model_rows=mod.benchmark_model_summary_rows(records)
    eq(len(model_rows),1)
    row=model_rows[0]
    close(row['chat_native_score'],.8);close(row['chat_assisted_score'],.9)
    close(row['chat_coverage'],1.0)
    eq((row['chat_native_worst_seed'],row['recovery_required_count'],row['recovery_rate']),(42,1,1/36))
    assert row['chat_native_sd'] is not None and row['primary_eval_warm_avg'] is not None
    partial=mod.benchmark_model_summary_rows([r for r in records if r['identity']['benchmark']!='groundedness_adversarial'])[0]
    assert partial['chat_native_score'] is None
    close(partial['chat_native_score_partial'],.8)
    close(partial['chat_coverage'],11/12)
    eq(partial['chat_suite_status'],'incomplete_chat_suite')


def test_native_assisted_attribution_and_failure_origin_are_explicit():
    record=_chat_record('ru_business_tone',42,.4,.9,recovery=True,native_completed=False)
    record['primary']['answer']='Короткий ответ без повторов.'
    record['final']['answer']='Повторяемый ответ. '*30
    record['score']['final']['repetition']={'strong_repetition':True}
    rows=mod.benchmark_summary_rows([record])
    row=rows[0]
    eq((row['native_model_score'],row['assisted_final_score'],row['headline_model_score'],row['headline_assisted_score']),(.4,.9,.4,.9))
    eq(row['recovery_dependency'],'required')
    eq(row['repetition_origin'],'recovery')
    eq(row['scorable_score_source'],'native_model_legacy_mode_selected')
    eq(mod.benchmark_failure_origin({'execution_status':'error','error':{'type':'TimeoutError','message':'SSH timeout'}}),'transport')
    eq(mod.benchmark_failure_origin(record),'model')


def test_chat_final_dry_run_builds_exact_three_seed_plan_without_inference():
    old_stream=mod.stream_chat
    try:
        mod.stream_chat=lambda *a,**k:(_ for _ in ()).throw(AssertionError('dry-run must not call inference'))
        catalog={
            'model-a':{'name':'model-a','digest':'a'*64},
            'model-b':{'name':'model-b','digest':'b'*64},
        }
        spec=mod.make_chat_suite_spec('chat_final',['model-a','model-b'],catalog=catalog)
        eq(spec['tests'],mod.benchmark_suite_tests('chat_core'))
        eq((spec['runs'],spec['seed_values'],spec['think_value'],spec['mode']),
           (3,[42,43,44],False,'native'))
        eq((spec['strict_fair_compare'],spec['fair_compare'],spec['order_policy']),(True,True,'balanced'))
        eq(len(spec['execution_layout']),2*12)
        eq(len(spec['execution_plan']),2*12*3)
        eq(len(spec['run_matrix']),3)
        eq(len(spec['effective_configs']),2*12*3)
        assert all(cfg['think'] is False for cfg in spec['effective_configs'].values())
        assert all(cfg['recovery']['enabled'] is False for cfg in spec['effective_configs'].values())
        assert all(cfg['recovery']['requested_enabled'] is True for cfg in spec['effective_configs'].values())
        keys=[(row['test'],row['model'],row['run']) for row in spec['execution_plan']]
        eq(len(keys),len(set(keys)))
        for model in spec['models']:
            eq({row['model_position'] for row in spec['execution_plan'] if row['model']==model},{0,1})
        for seed in spec['seed_values']:
            eq({row['round_position'] for row in spec['execution_plan'] if row['seed']==seed},{0,1,2})
        for model in spec['models']:
            for test in spec['tests']:
                positions={
                    row['test_position'] for row in spec['execution_plan']
                    if row['model']==model and row['test']==test
                }
                assert len(positions)==3,(model,test,positions)
        assert spec['spec_version']==9
    finally:
        mod.stream_chat=old_stream


def test_language_tracks_are_separate_and_bilingual_pairs_are_contract_equivalent():
    benches=mod.load_benchmarks()
    assert set(mod.benchmark_suite_tests('language_ru'))=={
        'lang_ru_state_update','lang_ru_causal_caution','lang_ru_instruction_precision',
    }
    assert set(mod.benchmark_suite_tests('language_en'))=={
        'lang_en_state_update','lang_en_causal_caution','lang_en_instruction_precision',
    }
    bilingual=mod.benchmark_suite_tests('bilingual')
    assert len(bilingual)==6 and set(bilingual)==set(mod.benchmark_suite_tests('language_ru')+mod.benchmark_suite_tests('language_en'))
    assert benches['lang_ru_state_update']['reference']==benches['lang_en_state_update']['reference']
    assert benches['lang_ru_state_update']['bilingual_pair_id']=='state_update'
    catalog={'model-a':{'name':'model-a','digest':'a'*64}}
    spec=mod.make_named_suite_spec('bilingual',['model-a'],catalog=catalog)
    assert spec['language_comparison']['paired_execution'] is True
    assert spec['tests']==bilingual and spec['runs']==3
    answer=(
        'The latest confirmed budget is 1.7 million rubles. The deadline is 22 November 2026, and cloud use is forbidden. '
        'The old budget and deadline were replaced by the user.\nBENCHMARK_RESULT\n'
        '{"budget_million":1.7,"deadline":"2026-11-22","cloud_allowed":false}'
    )
    score=mod.benchmark_score('lang_en_state_update',benches['lang_en_state_update'],answer)
    assert score['value']==1.0 and score['language']['observed']=='en'
    wrong=mod.benchmark_score('lang_en_state_update',benches['lang_en_state_update'],
        'Текущий бюджет составляет 1,7 миллиона рублей, а облако запрещено полностью.\nBENCHMARK_RESULT\n'
        '{"budget_million":1.7,"deadline":"2026-11-22","cloud_allowed":false}')
    assert wrong['value']<0.75 and wrong['language']['language_ok'] is False
    records=[]
    for name,track,score_value,rate in (
        ('lang_ru_state_update','ru',.9,18.0),('lang_en_state_update','en',.8,24.0),
    ):
        row=_chat_record('instruction',42,score_value,score_value)
        row['identity']['benchmark']=name
        row['identity']['benchmark_category']=benches[name]['category']
        row['identity']['language_track']=track
        row['identity']['bilingual_pair_id']='state_update'
        row['primary']['eval_rate']=rate
        records.append(row)
    model_rows=mod.benchmark_model_summary_rows(records)
    assert set(model_rows[0]['language_tracks'])=={'ru','en'}
    assert model_rows[0]['language_tracks']['ru']['native_score']==.9
    html=mod.benchmark_visual_report_document(records)
    assert ('Russian and English prompt tracks' in html or 'Треки русских и английских prompts' in html)


def test_benchmark_scorer_selftest_section_is_mandatory_and_serializable():
    result=mod.benchmark_scorer_selftest()
    assert result['ok'] is True,result
    assert result['passed']==result['total'] and result['total']>=10
    json.dumps(result,ensure_ascii=False)


def test_ui_theme_defaults_to_bull_red_and_migrates_legacy_brand_atomically():
    root=Path(tempfile.mkdtemp()); old_path=mod.ui_settings_path
    old_theme=mod.UI_THEME; old_override=os.environ.pop('BULL_UI_THEME',None)
    try:
        mod.ui_settings_path=lambda:root/'ui_settings.json'
        eq(mod.normalize_ui_theme(None),'bull_red')
        eq(mod.normalize_ui_theme('bull_brand'),'bull_red')
        eq(mod.set_ui_theme('bull',persist=True),'bull_red')
        document=json.loads((root/'ui_settings.json').read_text(encoding='utf-8'))
        eq((document['schema'],document['version'],document['theme'],document['language']),
           ('bull-ui-settings',4,'bull_red','en'))
        assert not (root/'ui_settings.json.tmp').exists()
        mod.set_ui_theme('matrix_soft',persist=False)
        eq(mod.load_ui_theme(),'bull_red')
        mod.set_ui_theme(mod.load_ui_theme(),persist=False)
        palette=mod.ui_theme_palette()
        assert '\033[2;' not in palette['secondary']
        assert palette['muted']!=mod.ANSI_GRAY
        assert len({palette['text'],palette['action'],palette['success'],palette['muted']})==4
    finally:
        mod.ui_settings_path=old_path
        mod.set_ui_theme(old_theme,persist=False)
        if old_override is not None: os.environ['BULL_UI_THEME']=old_override
        shutil.rmtree(root,ignore_errors=True)


def test_appearance_menu_changes_theme_and_returns():
    root=Path(tempfile.mkdtemp()); old_path=mod.ui_settings_path
    old_clear=mod.clear_console; old_theme=mod.UI_THEME
    try:
        mod.ui_settings_path=lambda:root/'ui_settings.json'
        mod.clear_console=lambda:None
        result=_with_inputs(['2','0'],mod.appearance_menu)
        assert result is None
        eq(mod.UI_THEME,'bull_red')
        document=json.loads((root/'ui_settings.json').read_text(encoding='utf-8'))
        eq(document['theme'],'bull_red')
    finally:
        mod.ui_settings_path=old_path; mod.clear_console=old_clear
        mod.set_ui_theme(old_theme,persist=False)
        shutil.rmtree(root,ignore_errors=True)


def test_resume_reconnects_before_model_catalog_and_records_audit_events():
    root=Path(tempfile.mkdtemp()); path=root/'suite_checkpoint.json'
    cp={
        'checkpoint_schema_version':mod.BENCH_CHECKPOINT_SCHEMA_VERSION,
        'suite_status':'paused_connectivity','records':{},'attempt_history':[],
        'resume_history':[],'resume_pending_keys':['logic|model-a|1'],
        'recovery_metrics':{},'spec':{'tests':['logic'],'models':['model-a'],'runs':1},
    }
    path.write_text(json.dumps(cp),encoding='utf-8')
    old_connect=mod.connect_active_backend; old_catalog=mod.model_catalog
    old_reset=mod.reset_remote_endpoint_cache; old_sleep=mod.time.sleep
    calls=[]; state={'connected':False,'attempt':0}
    class Transport:
        def poll(self): return 0
    try:
        def connect(force_restart=False):
            calls.append('connect'); state['attempt']+=1
            if state['attempt']==1:
                raise urllib.error.URLError('[WinError 10061] refused')
            state['connected']=True
            return Transport(),{'backend':'ollama','version':'test','status':'ok'}
        def catalog():
            assert state['connected'] is True
            calls.append('catalog')
            return {'model-a':{'name':'model-a','digest':'digest-a'}}
        mod.connect_active_backend=connect; mod.model_catalog=catalog
        mod.reset_remote_endpoint_cache=lambda:calls.append('reset')
        mod.time.sleep=lambda seconds:calls.append(('sleep',seconds))
        tp,info,catalog=mod.prepare_benchmark_resume_backend(
            path,cp,current_transport=None,attempts=3,delays=(0,0,0)
        )
        assert tp is not None and info['status']=='ok' and 'model-a' in catalog
        eq([x for x in calls if x in ('connect','catalog')],['connect','connect','catalog'])
        disk=json.loads(path.read_text(encoding='utf-8'))
        events=[x['event'] for x in disk['resume_history']]
        assert 'reconnect_failed' in events and 'connection_restored' in events
        eq(disk['recovery_metrics']['reconnect_attempts'],2)
        eq(disk['recovery_metrics']['reconnect_failures'],1)
        assert not any('100.64.' in json.dumps(x) for x in disk['resume_history'])
    finally:
        mod.connect_active_backend=old_connect; mod.model_catalog=old_catalog
        mod.reset_remote_endpoint_cache=old_reset; mod.time.sleep=old_sleep
        shutil.rmtree(root,ignore_errors=True)


def test_resume_skips_backend_when_only_finalization_is_pending():
    cp={
        'suite_status':'finalization_incomplete',
        'records':{'x|m|1':{'record_schema_version':5,'execution_status':'ok'}},
        'spec':{'tests':['x'],'models':['m'],'runs':1},
    }
    assert mod.benchmark_checkpoint_needs_backend(cp) is False


def test_checkpoint_progress_distinguishes_saved_runs_from_current_slot():
    cp={'records':{
        'a|m|1':{'record_schema_version':5,'execution_status':'ok'},
        'b|m|1':{'record_schema_version':5,'execution_status':'error'},
    }}
    state=mod.benchmark_progress_state(cp,total=12,current_slot=3)
    eq(state,{'saved':1,'failed_records':1,'current_slot':3,'total':12})
    text=mod.benchmark_progress_text(state)
    assert 'Сохранено 1/12' in text and 'текущий запуск 3/12' in text


def test_live_progress_snapshot_is_safe_for_interrupted_attempt_audit():
    class Sampler:
        def latest(self):
            return {'gpu_util':55.0,'vram_used_mib':4096.0,'vram_total_mib':8192.0,'gpu_temp':48.0}
    live=mod.LiveInferenceProgress('fixture',1000,sampler=Sampler(),interval=99)
    live.stage='FINAL'; live.reasoning_chars=250; live.answer_chars=500
    snapshot=live.snapshot()
    eq(snapshot['phase'],'FINAL')
    eq(snapshot['estimated_tokens'],300)
    eq(snapshot['gpu']['gpu_util'],55.0)
    assert 'label' not in snapshot


def test_visual_report_is_offline_graphical_and_excludes_raw_answers():
    root=Path(tempfile.mkdtemp())
    try:
        records=[]
        for model,score,speed in (('<model-a>',.82,21.0),('model-b',.71,33.0)):
            for test_name in mod.CHAT_CORE_TESTS:
                record=_chat_record(test_name,42,score,min(1.0,score+.08))
                record['identity']['model']=model
                record['primary']['eval_rate']=speed
                record['primary']['answer']='<script>PRIVATE_RAW_ANSWER</script>'
                record['final']['answer']='PRIVATE_FINAL_ANSWER'
                records.append(record)
        non_chat=_chat_record('python_debug',42,.64,.70)
        non_chat['identity']['model']='model-non-chat'
        non_chat['primary']['eval_rate']=15.0
        records.append(non_chat)
        raw=root/'fixture.json'
        raw.write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
        sj,sc=mod.save_benchmark_summary(raw,records)
        report=mod.benchmark_visual_report_path(raw)
        evidence_private,evidence_share=mod.evidence_paths(raw)
        assert sj.is_file() and sc.is_file() and report.is_file()
        assert evidence_private.is_file() and evidence_share.is_file()
        html_text=report.read_text(encoding='utf-8')
        assert '<!doctype html>' in html_text.casefold()
        assert 'Сводная таблица' in html_text and 'Шкалы качества' in html_text
        assert 'Native model quality' in html_text and 'Final system quality' in html_text
        assert '95% confidence intervals' in html_text and 'Latency distributions' in html_text
        assert 'Context curves' in html_text
        assert 'Какая модель лучше для задачи' in html_text
        assert 'decision-card' in html_text and 'scatter-point' in html_text
        assert 'Качество' in html_text and 'Баланс' in html_text and 'Мало памяти' in html_text
        assert 'Выбранные тесты' in html_text and '64.0%' in html_text
        assert 'Топ-3 места' in html_text and 'Источник генерации' in html_text
        assert 'Качество, контракт и скорость' in html_text
        assert 'Качество и время задачи' in html_text
        assert 'comparison-card' in html_text and 'stability-track' in html_text
        old_language=mod.get_language()
        try:
            mod.set_language('en')
            english=mod.benchmark_visual_report_document(records)
            assert '<html lang="en">' in english and 'Top 3 places' in english
            assert 'Quality, contract and speed' in english and 'Seed stability' in english
            assert not re.search('[А-Яа-яЁё]',english)
        finally:
            mod.set_language(old_language)
        assert 'metric-bar' in html_text and '<table' in html_text
        assert '&lt;model-a&gt;' in html_text
        assert 'PRIVATE_RAW_ANSWER' not in html_text and 'PRIVATE_FINAL_ANSWER' not in html_text
        assert '<script>' not in html_text.casefold()
        assert 'http://' not in html_text and 'https://' not in html_text
        share=json.loads(evidence_share.read_text(encoding='utf-8'))
        eq(share['schema'],'bull-benchmark-summary')
        eq(share['artifact_classification'],'share_safe')
        share_text=evidence_share.read_text(encoding='utf-8')
        assert 'PRIVATE_RAW_ANSWER' not in share_text and 'PRIVATE_FINAL_ANSWER' not in share_text
    finally:
        shutil.rmtree(root,ignore_errors=True)


def test_public_release_readiness_assets_and_gate_exist():
    for rel in ('README.md','.gitignore','.gitattributes','Docs/PUBLIC_RELEASE_CHECKLIST.md','Docs/RELEASE_NOTES_0.29.0.1.md','Test-Public-Release.ps1'):
        assert (ROOT/rel).is_file(),rel
    build=(ROOT/'Build-Release.ps1').read_text(encoding='utf-8-sig')
    audit=(ROOT/'Test-Public-Release.ps1').read_text(encoding='utf-8-sig')
    assert 'Test-Public-Release.ps1' in build
    attribute_rules=[line.strip() for line in (ROOT/'.gitattributes').read_text(encoding='utf-8').splitlines()
                     if line.strip() and not line.lstrip().startswith('#')]
    eq(attribute_rules,['* -text'])
    assert 'unsupported Git byte-preservation policy' in audit
    for marker in ('PRIVATE KEY','C:\\\\Users\\\\','gh[pousr]_','hf_','AKIA'):
        assert marker in audit,marker
    docs='\n'.join(
        path.read_text(encoding='utf-8-sig',errors='replace')
        for path in (ROOT/'Docs').rglob('*') if path.is_file()
    )
    assert ('mr'+'chr') not in docs.casefold()
    root=Path(tempfile.mkdtemp()); old_appdir=mod.appdir
    try:
        mod.appdir=lambda:root
        assert mod.latest_resumable_checkpoint() is None
        mod.load_benchmarks()
        assert not (root/'Benchmarks').exists(),'read-only checkpoint discovery created a runtime directory'
        if os.name=='nt' and shutil.which('powershell.exe'):
            import subprocess
            policy_root=root/'policy'; policy_root.mkdir()
            shutil.copyfile(ROOT/'backend_settings.json',policy_root/'backend_settings.json')
            attributes=policy_root/'.gitattributes'
            for content,expected_success in (('# exact bytes\n* -text\n',True),
                                              ('* text=auto\n',False)):
                attributes.write_text(content,encoding='utf-8')
                result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive',
                    '-ExecutionPolicy','Bypass','-File',str(ROOT/'Test-Public-Release.ps1'),
                    '-Root',str(policy_root)],capture_output=True,timeout=30)
                eq(result.returncode==0,expected_success)
            attributes.write_text('* -text\n',encoding='utf-8')
            nested=policy_root/'nested'; nested.mkdir()
            (nested/'.gitattributes').write_text('* -text\n',encoding='utf-8')
            result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive',
                '-ExecutionPolicy','Bypass','-File',str(ROOT/'Test-Public-Release.ps1'),
                '-Root',str(policy_root)],capture_output=True,timeout=30)
            assert result.returncode!=0,'nested Git attributes bypassed the exact root allowlist'
    finally:
        mod.appdir=old_appdir; shutil.rmtree(root,ignore_errors=True)


test('AST / no duplicate functions',test_ast)
test('structured scorer discrimination',test_scorer)
test('terminal BENCHMARK_RESULT rule',test_terminal_json)
test('fixed/sweep seeds and option parser',test_seed_modes)
test('GPU sampler parser',test_gpu_parser)
test('native/client pipeline separation',test_native_and_client_pipeline)
test('nested JSON/CSV roundtrip',test_nested_json_csv)
test('checkpoint continue-on-error + resume',test_checkpoint_resume)
test('checkpoint hard restart replays active job',test_checkpoint_hard_restart_replays_only_active_job_from_start)
test('checkpoint transport pause avoids cascade',test_checkpoint_transport_failure_pauses_without_cascade_and_resumes)
test('checkpoint finalize idempotence + missing output recovery',test_checkpoint_finalize_is_idempotent_and_recovers_missing_output)
test('legacy v15.x summary compatibility',test_legacy_summary)
test('all built-in scorer reference answers',test_all_builtin_scorers)
test('v17.4 category scorers + code sandbox',test_v174_category_scorers_and_code_sandbox)
test('benchmark result schema matches scorer',test_benchmark_schema_matches_scorer)
test('bounded client rescue continues partial answer',test_client_rescue_is_bounded_and_continues_partial_answer)
test('benchmark identity reproducibility',test_benchmark_identity_reproducibility)
test('v16.1 summary semantics',test_v161_summary_semantics)
test('summary v5 groups seeds + uncertainty',test_summary_v5_groups_seeds_and_reports_uncertainty)
test('profile fingerprint excludes seed',test_profile_fingerprint_excludes_seed_but_run_fingerprint_does_not)
test('balanced execution layout is deterministic',test_balanced_execution_layout_is_deterministic_and_rotates_tests)
test('recovery candidate selection avoids regression',test_recovery_candidate_selection_penalizes_regression_and_repetition)
test('retention executor preflight + safety',test_retention_executor_preflight_and_safety)
test('generated scorers reject extended library IO',test_generated_scorers_reject_extended_library_io)
test('checkpoint v7 state machine',test_checkpoint_v7_state_machine)
test('startup home menu routes',test_startup_home_menu_routes)
test('startup benchmark wizard commands',test_startup_benchmark_wizard_commands)
test('startup regression fails closed if tests missing',test_startup_regression_missing_file_fails_closed)
test('red color helper exists',test_red_color_helper_exists)
test('startup regression failure path renders safely',test_startup_regression_failure_path_does_not_crash)
test('startup regression failure excerpt keeps root cause',test_startup_regression_failure_excerpt_keeps_root_cause)
test('startup regression exact-byte cache',test_startup_regression_cache_is_exact_and_avoids_repeat_suite)
test('startup regression reports truthful stage progress',test_startup_regression_reports_truthful_stage_progress)
test('startup regression displays only explicit active checks',test_startup_regression_active_check_marker_is_explicit_and_bounded)
test('UTF-8 subprocess environment',test_utf8_subprocess_environment)
test('Unicode progress bar survives child process',test_unicode_progress_bar_under_forced_utf8_child)
test('Simpson v3 separates balance state from check action',test_simpson_v3_disambiguates_balance_and_check)
test('Simpson v3 separates point winner from product decision',test_simpson_v3_product_decision_separate_from_point_winner)
test('Simpson v3 word limit',test_simpson_v3_word_limit_scored)
test('Instruction v3 realistic risk wording',test_instruction_v3_realistic_risk_phrases)
test('Instruction v3 Latin rule matches prompt',test_instruction_v3_latin_rule_matches_prompt)
test('Funnel v3 requires analytic shape',test_funnel_v3_requires_full_analytic_shape)
test('Funnel v3 word limit',test_funnel_v3_word_limit)
test('summary completion-adjusted + partial diagnostics',test_summary_completion_adjusted_score)
test('legacy v2 scorers remain readable',test_legacy_v2_scorers_still_available)
test('chat THINK length + final -> continue without verify',test_chat_think_length_with_final_continues_without_verify)
test('chat THINK length + no final -> finalize reasoning once',test_chat_think_length_without_final_finalizes_reasoning_once)
test('chat THINK finalizer continuation stays FAST',test_chat_think_finalizer_can_continue_without_new_think)
test('chat completed answer has no fallback',test_chat_completed_answer_never_invokes_fallback)
test('legacy Simpson audit fixes boolean ambiguity',test_legacy_audit_fixes_simpson_boolean_ambiguity)
test('legacy Instruction accepts realistic risk wording',test_legacy_instruction_risk_is_not_keyword_false_negative)
test('legacy Instruction unknown risk is N/A',test_legacy_instruction_unknown_risk_is_na_not_false)
test('offline raw rescore preserves original and avoids inference',test_rescore_raw_is_offline_and_preserves_original_score)
test('instruction v4 runs native FAST in THINK suite',test_instruction_v4_runs_native_fast_inside_think_suite)
test('recovery preserves exact format + conditional result marker',test_recovery_preserves_exact_format_and_conditional_result_marker)
test('rescue preserves format and continues failed partial',test_rescue_preserves_format_and_continues_failed_partial)
test('checkpoint fingerprints per-test execution policy',test_checkpoint_fingerprints_instruction_execution_policy)
test('rescore old instruction v3 remains supported',test_rescore_instruction_v3_remains_supported)
test('benchmark result menu -> home',test_benchmark_result_menu_home)
test('benchmark result menu -> visual report -> stays',test_benchmark_result_menu_opens_visual_report_and_stays)
test('benchmark result menu -> answers -> stays',test_benchmark_result_menu_answers_stays_on_screen)
test('benchmark result menu repeat + resume guard',test_benchmark_result_menu_repeat_and_resume_guard)
test('benchmark result menu -> benchmark menu',test_benchmark_result_menu_benchmark_route)
test('benchmark result menu interrupt -> home',test_benchmark_result_menu_interrupt_goes_home)
test('profile fingerprint + resume guard',test_profile_fingerprint_and_resume_guard)
test('resume detects missing model',test_resume_detects_missing_model)
test('analytics case gold SQL/Python/stats/figure = 100%',test_analytics_case_gold_is_exact_and_executable)
test('analytics case accepts semantic Python argument names',test_analytics_case_accepts_semantic_argument_names)
test('analytics case preserves valid SQL on Python runtime failure',test_analytics_case_scores_sql_when_python_runtime_fails)
test('analytics case wrong SQL dedupe is capped',test_analytics_case_wrong_dedupe_sql_is_capped)
test('analytics case wrong stats is capped',test_analytics_case_wrong_stats_is_capped)
test('analytics case wrong plot loses visualization only',test_analytics_case_wrong_plot_loses_visualization_points_only)
test('all built-ins have non-leaking reference metadata',test_all_builtins_have_reference_without_prompt_leakage)
test('analytics reference values + scorer preflight',test_analytics_reference_values_and_preflight)
test('backend settings roundtrip + validation',test_backend_settings_roundtrip_and_validation)
test('llama request maps THINK/FAST correctly',test_llama_request_mapping_think_and_fast)
test('llama timings + speculative acceptance mapping',test_llama_timings_and_draft_acceptance_mapping)
test('llama router model catalog parsing',test_llama_router_model_catalog_parse)
test('llama SSE stream parser',test_llama_sse_stream_parser)
test('benchmark spec stores backend + reference provenance',test_benchmark_spec_contains_backend_and_reference_provenance)
test('llama structured response_format mapping',test_llama_response_format_schema_mapping)
test('llama SSE length + fragmented tools',test_llama_sse_preserves_length_and_merges_tool_fragments)
test('llama message conversion tool_call_id + reasoning',test_llama_message_conversion_tool_and_reasoning)
test('analytics case rejects trivial hardcoded shapes',test_analytics_case_rejects_trivial_hardcoded_code_shapes)
test('summary separates Ollama/llama backends',test_summary_separates_backends_and_records_reference_hash)
test('llama settings extended validation',test_llama_setting_extended_validation)
test('ULTIMATE profile + cfg',test_ultimate_profile_and_cfg_exist)
test('ULTIMATE reasoning continues beyond ordinary limits',test_ultimate_continues_reasoning_until_answer_without_total_cycle_cap)
test('ULTIMATE final length uses non-thinking continuation',test_ultimate_final_length_continues_without_new_think)
test('ULTIMATE tools exceed normal loop limit',test_ultimate_tool_work_can_exceed_normal_tool_loop_limit)
test('ULTIMATE session roundtrip',test_ultimate_session_roundtrip_preserves_mode)
test('benchmark capability fallback THINK -> FAST',test_benchmark_capability_fallback_think_to_fast)
test('benchmark records non-thinking fallback provenance',test_benchmark_record_provenance_for_nonthinking_model)
test('Qwen3-Coder-Next official non-thinking sampling profile',test_qwen3_coder_next_profile_uses_official_nonthink_sampling)
test('live benchmark progress heartbeat + GPU',test_live_progress_renders_heartbeat_and_gpu)
test('Ollama HTTP 400 exposes response body',test_ollama_http_error_exposes_server_body)
test('remote auto selects working LAN/VPN/WAN profile',test_remote_auto_prefers_working_profile_and_caches)
test('direct SSH client path is batch/key-only',test_direct_ssh_profile_is_batch_key_only_client_side)
test('direct profile kind cannot be downgraded',test_direct_profile_kind_cannot_be_downgraded_by_json)
test('inference APIs remain loopback-only behind SSH',test_llama_and_ollama_bind_remote_apis_to_loopback)
test('bench and /bench route to Benchmark Lab',test_bench_alias_and_root_route_do_not_fall_through_to_chat)
test('Advanced /bench stays inside Benchmark Lab',test_advanced_bench_slash_bench_stays_inside_lab)
test('Advanced startup never exposes generic command mode',test_startup_advanced_never_returns_none_command_mode)
test('Advanced rejects arbitrary chat text',test_advanced_rejects_arbitrary_chat_text)
test('benchmark classifies context vs predict truncation',test_benchmark_limit_cause_context_vs_predict)
test('benchmark CLI accepts ultimate mode',test_parse_bench_options_accepts_ultimate)
test('analytics_case recommends client mode',test_analytics_case_recommends_client_pipeline)
test('analytics_case native mode requires FAST finalizer',test_analytics_case_native_requires_fast_finalizer)
test('analytics_case context override is applied and restored',test_analytics_context_override_is_applied_and_restored)
test('benchmark ultimate reasoning rollover completes',test_benchmark_ultimate_reasoning_rollover_completes)
test('benchmark ultimate final continuation is FAST',test_benchmark_ultimate_final_continuation_is_fast)
test('ULTIMATE incomplete contract uses recovery v3',test_ultimate_incomplete_contract_uses_v3_recovery)
test('summary v4 reports ULTIMATE/context metrics',test_summary_v4_reports_context_truncation_and_ultimate_tokens)
test('tools chat_agent has defined silent parameter',test_tools_chat_agent_no_undefined_silent)
test('safe tools confirm reads outside Workspace',test_safe_tools_require_read_confirmation_outside_workspace)
test('Workspace reads remain confirmation-free',test_workspace_read_needs_no_confirmation)
test('generated-code child env strips secrets',test_safe_child_env_strips_common_secrets)
test('generated scorers use scrubbed subprocess env',test_generated_scorer_subprocesses_use_scrubbed_environment)
test('SSH host rejects option injection',test_ssh_host_rejects_option_injection)
test('SSH probe uses encoded PowerShell + OEM decode',test_ssh_probe_uses_encoded_powershell_and_oem_decode)
test('external llama HTTP requires explicit override',test_external_llama_http_requires_explicit_override)
test('external llama redirects are blocked',test_llama_redirects_are_blocked_before_bearer_forwarding)
test('llama capabilities do not fake thinking',test_llama_capabilities_do_not_fake_thinking)
test('unknown slash commands cannot fall through to model',test_unknown_slash_command_guard_present)
test('context help and backend migration commands exist',test_help_topics_and_backend_migration_commands_present)
test('settings stores use safe mtime caches',test_backend_and_profile_store_cache_roundtrip)
test('backend import validates config securely',test_backend_import_rejects_unknown_keys_and_insecure_url)
test('release gate re-verifies manifest hashes',test_release_gate_reverifies_manifest_and_new_docs)
test('v17.4 documentation set exists',test_v174_documentation_set_exists)
test('external llama requires API key by default',test_external_llama_api_key_required_and_header_from_env)
test('benchmark wizard multi-model route prompts selector',test_benchmark_wizard_multi_model_route_prompts_selector)
test('backend menu exposes portable config import',test_backend_menu_exposes_import_portable_config)
test('actionable error hints cover common failures',test_actionable_error_hints_cover_network_and_hostkey)
test('single benchmark setup selects one model + parameters',test_single_benchmark_setup_selected_model_and_parameters)
test('single benchmark setup FAST/cancel path',test_single_benchmark_setup_fast_choice_and_cancel)
test('Advanced exposes single-model benchmark route',test_advanced_menu_exposes_single_model_route)
test('effective config precedence + constraints + capability',test_effective_config_precedence_constraints_and_capability)
test('native config marks requested recovery as suppressed',test_native_effective_config_marks_recovery_suppressed)
test('fair compare normalizes model defaults',test_fair_compare_normalizes_model_defaults)
test('Ollama profile parser + digest cache invalidation',test_ollama_profile_parameter_parser_and_digest_cache_invalidation)
test('model-profile sampling omits API sampler options',test_sampling_source_model_profile_omits_sampling_options)
test('model-profile serializer sends exact non-sampling options',test_model_profile_serializer_sends_exact_options_without_sampling)
test('benchmark-override sampling keeps legacy request',test_sampling_source_benchmark_override_preserves_legacy_request)
test('per-model sampling produces distinct requests',test_sampling_source_per_model_has_distinct_requests_and_fingerprints)
test('sampling preflight blocks fake/leaking experiments',test_sampling_preflight_blocks_no_variation_and_profile_override)
test('strict fair compare permits declared experiment only',test_strict_fair_compare_allows_only_experimental_parameters)
test('strict fair compare records Ollama profile sampler differences',test_strict_fair_compare_records_ollama_profile_sampler_differences)
test('model-profile preflight accepts inherited sampler variation',test_model_profile_spec_preflight_accepts_inherited_sampler_variation)
test('legacy profile defaults to benchmark override',test_old_benchmark_profile_defaults_to_benchmark_override)
test('/bench all strict fair uses benchmark predict budgets',test_all_suite_strict_fair_uses_each_benchmark_predict_budget)
test('manual seeds + runtime options + sweep parser',test_manual_seeds_runtime_options_and_sweep_matrix)
test('recovery keeps best verified partial',test_recovery_keeps_best_verified_partial)
test('structural completion + analytics v3 contract',test_structural_completion_and_analytics_v3_contract)
test('analytics tolerances + safe imports + contradiction cap',test_analytics_tolerance_typing_io_and_contradiction_cap)
test('incomplete outputs remain scorable',test_incomplete_outputs_are_scorable_but_completion_adjusted)
test('benchmark profile CRUD roundtrip',test_benchmark_profile_crud_roundtrip)
test('tested profile artifact + Client import',test_tested_profile_artifact_and_client_import)
test('v17.4 app boundaries + shared contracts',test_v174_application_boundaries_and_shared_contracts)
test('icon + shortcut + release assets',test_icon_shortcut_and_release_assets)
test('Windows PowerShell launcher is ASCII parse-safe',test_windows_powershell_launcher_is_ascii_parse_safe)
test('RU_LANGUAGE_STRESS v2 specs + gold + adversarial semantics',test_ru_language_stress_v2_specs_gold_and_adversarial_contract)
test('RU_LANGUAGE_STRESS v2 real answer fixtures',test_ru_language_stress_v2_real_answers_fix_false_negatives_and_detect_defects)
test('RU_LANGUAGE_STRESS v2 offline rescore real v17.5.3 fixture',test_ru_language_stress_v2_offline_rescore_real_v1753_fixture)
test('RU_LANGUAGE_STRESS v3 catalog preserves prompts + scale',test_ru_language_stress_v3_catalog_preserves_prompts_and_scale)
test('RU_LANGUAGE_STRESS v3 deterministic fixture set',test_ru_language_stress_v3_deterministic_fixture_set)
test('RU v3 claim roles are tri-state + auditable',test_ru_v3_context_claim_roles_are_tri_state_and_auditable)
test('RU v17.6 false positives removed + true defects preserved',test_ru_v3_real_v176_false_positives_removed_true_defects_preserved)
test('groundedness adversarial deterministic gold',test_groundedness_adversarial_catalog_and_deterministic_gold)
test('CHAT scorer exact groundedness object',test_chat_scorer_exact_groundedness_object_keeps_full_score)
test('CHAT scorer groundedness root array',test_chat_scorer_groundedness_root_array_scores_semantics)
test('CHAT scorer groundedness Markdown JSON',test_chat_scorer_groundedness_markdown_json_root)
test('CHAT scorer groundedness trailing text',test_chat_scorer_groundedness_rejects_text_after_json)
test('CHAT scorer groundedness CASE id normalization',test_chat_scorer_groundedness_normalizes_case_ids_for_semantics_only)
test('CHAT scorer separates wrong envelope from content',test_chat_scorer_wrong_groundedness_envelope_does_not_zero_content)
test('CHAT scorer groundedness prose/JSON contradiction',test_chat_scorer_groundedness_prose_json_contradiction_is_separate)
test('CHAT scorer context rebuttal is not current claim',test_chat_scorer_context_rebuttal_is_not_current_deadline)
test('CHAT scorer real current deadline conflict remains',test_chat_scorer_context_real_current_deadline_conflict_remains)
test('CHAT scorer instruction accepts Russian prefixes',test_chat_scorer_instruction_accepts_required_russian_prefixes)
test('CHAT scorer instruction missing-prefix penalty',test_chat_scorer_instruction_without_prefixes_keeps_penalty)
test('CHAT scorer instruction Latin check is independent',test_chat_scorer_instruction_latin_check_is_independent)
test('completion separates generation from wrong schema',test_completion_facets_separate_generation_from_wrong_schema)
test('completion detects length/context/transport interruptions',test_completion_facets_detect_length_context_and_transport_interruptions)
test('completion summary separates generation and task',test_completion_summary_reports_generation_and_task_separately)
test('terminal CHAT summary adds comparative analysis',test_terminal_chat_summary_is_unambiguous_and_adds_comparative_analysis)
test('CHAT suites + category-balanced model summary',test_chat_suites_final_preset_and_category_balanced_model_summary)
test('native/assisted attribution + failure origin',test_native_assisted_attribution_and_failure_origin_are_explicit)
test('CHAT final dry-run exact 3-seed plan',test_chat_final_dry_run_builds_exact_three_seed_plan_without_inference)
test('RU/EN language tracks and bilingual paired contract',test_language_tracks_are_separate_and_bilingual_pairs_are_contract_equivalent)
test('benchmark scorer selftest mandatory + serializable',test_benchmark_scorer_selftest_section_is_mandatory_and_serializable)
test('user prompt store is versioned + fail-closed',test_user_prompt_store_is_versioned_atomic_and_fail_closed)
test('custom prompt wizard builds standard command',test_custom_prompt_wizard_builds_simple_standard_command)
test('checkpoint snapshots exact custom prompt',test_spec_snapshots_exact_custom_prompt)
test('single-seed rank stability + runtime fingerprints',test_single_seed_rank_stability_is_insufficient_and_runtime_fingerprints_are_plural)
test('tested profiles require scored multiseed evidence',test_tested_profiles_require_scored_multiseed_evidence)
test('tested profiles deduplicate importable configuration',test_tested_profiles_deduplicate_same_importable_configuration)
test('CSV export neutralizes spreadsheet formulas',test_csv_export_neutralizes_spreadsheet_formulas_without_changing_json)
test('Matrix UI primitives stay consistent without color',test_matrix_ui_primitives_are_consistent_and_accessible_without_color)
test('Matrix benchmark copy + Advanced navigation',test_matrix_benchmark_menu_copy_and_advanced_navigation_are_consistent)
test('main keeps backend version probe global',test_main_does_not_shadow_backend_version_probe)
test('startup backend failure stays offline without switching',test_startup_backend_failure_is_offline_first_and_does_not_switch_backend)
test('main reaches home with backend offline',test_main_reaches_home_when_backend_is_offline)
test('connection selection reconnects immediately',test_connection_menu_returns_immediate_reconnect_after_selection)
test('benchmark reports stay available offline',test_benchmark_runtime_guard_keeps_reports_available_offline)
test('v18 public defaults are local + identity-free',test_v18_public_defaults_are_local_and_identity_free)
test('v18 local Ollama never opens SSH',test_v18_local_ollama_connect_never_opens_ssh)
test('v18 connection bundle isolates endpoint + key',test_v18_connection_bundle_keeps_endpoint_and_key_out_of_public_config)
test('v18 connection bundle fails closed',test_v18_connection_bundle_fails_closed_on_secret_or_missing_key)
test('client installer + release secret gate',test_client_installer_and_release_secret_gate)
test('WAN readiness keeps inference private',test_wan_readiness_keeps_inference_private)
test('WAN SSH keepalive + clear Internet UI',test_wan_ssh_transport_has_keepalive_and_clear_internet_ui)
test('UI theme defaults to BULL Red + migrates legacy brand atomically',test_ui_theme_defaults_to_bull_red_and_migrates_legacy_brand_atomically)
test('appearance menu changes theme + returns',test_appearance_menu_changes_theme_and_returns)
test('resume reconnects before catalog + audits attempts',test_resume_reconnects_before_model_catalog_and_records_audit_events)
test('resume finalization skips backend reconnect',test_resume_skips_backend_when_only_finalization_is_pending)
test('checkpoint progress separates saved from current slot',test_checkpoint_progress_distinguishes_saved_runs_from_current_slot)
test('interrupted attempt captures safe live progress',test_live_progress_snapshot_is_safe_for_interrupted_attempt_audit)
test('visual report is offline + graphical + privacy-safe',test_visual_report_is_offline_graphical_and_excludes_raw_answers)
test('public release readiness assets + gate',test_public_release_readiness_assets_and_gate_exist)
startup_suite('Benchmark Registry contract checks')
from Tests.registry_regression import run_suite as run_registry_suite
registry_test_count=run_registry_suite(mod)
passed.extend(f'Benchmark Registry {i+1}' for i in range(registry_test_count))
startup_suite_complete()
startup_suite('Engine Boundary contract checks')
from Tests.engine_boundary_regression import run_suite as run_engine_boundary_suite
engine_boundary_test_count=run_engine_boundary_suite(mod)
passed.extend(f'Engine Boundary {i+1}' for i in range(engine_boundary_test_count))
startup_suite_complete()
startup_suite('Pack Library contract checks')
from Tests.pack_library_regression import run_suite as run_pack_library_suite
pack_library_test_count=run_pack_library_suite()
passed.extend(f'Pack Library {i+1}' for i in range(pack_library_test_count))
startup_suite_complete()
startup_suite('Pack selection and offline onboarding checks')
from Tests.pack_selection_regression import run_suite as run_pack_selection_suite
pack_selection_count=run_pack_selection_suite(mod,PRODUCTION_LOAD_BENCHMARKS,PRODUCTION_PACK_REGISTRY)
passed.extend(f'Pack selection {i+1}' for i in range(pack_selection_count))
startup_suite_complete()
startup_suite('Author workshop checks')
from Tests.author_workshop_regression import run_suite as run_author_workshop_suite
author_workshop_count=run_author_workshop_suite()
passed.extend(f'Author workshop {i+1}' for i in range(author_workshop_count))
startup_suite_complete()
startup_suite('Pack snapshot evidence')
from Tests.pack_evidence_regression import run_suite as run_pack_evidence_suite
pack_evidence_count=run_pack_evidence_suite()
passed.extend(f'Pack evidence {i+1}' for i in range(pack_evidence_count))
startup_suite_complete()
startup_suite('Agent Benchmark contract checks')
from Tests.agent_benchmark_regression import run_suite as run_agent_suite
proxy=mod._agent_core_proxy()
previous_api=mod.API
try:
    mod.API='http://127.0.0.1:11435'
    eq(proxy.API,mod.API,'Agent proxy must follow endpoint changes after SSH reconnect')
finally:
    mod.API=previous_api
agent_test_count=run_agent_suite()
passed.extend(f'Agent Benchmark {i+1}' for i in range(agent_test_count))
startup_suite_complete()
startup_suite('Security hardening checks')
from Tests.hardening_regression import run_suite as run_hardening_suite
hardening_test_count=run_hardening_suite(mod)
passed.extend(f'Hardening {i+1}' for i in range(hardening_test_count))
startup_suite_complete()
startup_suite('User experience checks')
from Tests.ux_regression import run_suite as run_ux_suite
ux_test_count=run_ux_suite(mod)
passed.extend(f'UX {i+1}' for i in range(ux_test_count))
startup_suite_complete()
startup_suite('BULL Core bridge checks')
from Tests.bridge_regression import run_suite as run_bridge_suite
bridge_test_count=run_bridge_suite()
passed.extend(f'BULL Core {i+1}' for i in range(bridge_test_count))
startup_suite_complete()
startup_suite('BULL Core contract checks')
from Tests.core_regression import run_suite as run_core_suite
core_test_count=run_core_suite()
passed.extend(f'BULL Core {i+1}' for i in range(core_test_count))
startup_suite_complete()
startup_suite('BULL Evidence contract checks')
from Tests.evidence_regression import run_suite as run_evidence_suite
evidence_test_count=run_evidence_suite()
passed.extend(f'BULL Evidence {i+1}' for i in range(evidence_test_count))
startup_suite_complete()
startup_suite('Russian dialogue contract checks')
from Tests.ru_dialogue_regression import run_suite as run_ru_dialogue_suite
ru_dialogue_test_count=run_ru_dialogue_suite(mod)
passed.extend(f'RU Dialogue {i+1}' for i in range(ru_dialogue_test_count))
startup_suite_complete()
startup_suite('Decision support checks')
from Tests.decision_support_regression import DecisionSupportTests
decision_result=unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(DecisionSupportTests)
)
if not decision_result.wasSuccessful():
    raise AssertionError('BULL decision support regression failed')
passed.extend(f'Decision Support {i+1}' for i in range(decision_result.testsRun))
startup_suite_complete()
startup_suite('User benchmark format checks')
from Tests.user_tests_regression import run_suite as run_user_tests_suite
user_tests_count=run_user_tests_suite()
passed.extend(f'User Tests {i+1}' for i in range(user_tests_count))
startup_suite_complete()
startup_suite('Pack Library usability and Windows persistence checks')
from Tests.usability_patch_regression import run_suite as run_usability_suite
usability_count=run_usability_suite(mod)
passed.extend(f'Usability patch {i+1}' for i in range(usability_count))
startup_suite_complete()
from Tests.setup_regression import run_suite as run_setup_suite
print('BULL_STARTUP_CHECK\tSequential installer and shallow navigation',flush=True)
for index in range(run_setup_suite(mod)):passed.append('client_setup_'+str(index))
print('BULL_STARTUP_COMPLETE\t'+str(len(passed)),flush=True)

from Tests.pack_download_regression import run_suite as run_download_suite
print('BULL_STARTUP_CHECK\tBounded HTTPS pack download',flush=True)
for index in range(run_download_suite()):passed.append('pack_download_'+str(index))
print('BULL_STARTUP_COMPLETE\t'+str(len(passed)),flush=True)

from Tests.theme_setup_regression import run_suite as run_theme_setup_suite
print('BULL_STARTUP_CHECK\tBULL Red / BULL Matrix and Setup',flush=True)
for index in range(run_theme_setup_suite(mod)):passed.append('theme_setup_'+str(index))
print('BULL_STARTUP_COMPLETE\t'+str(len(passed)),flush=True)

from Tests.followup_ui_regression import run_suite as run_followup_ui_suite
startup_suite('Follow-up UI and offline author workflow')
passed.extend(f'Follow-up UI {i+1}' for i in range(run_followup_ui_suite(mod)))
startup_suite_complete()
from Tests.language_route_regression import run_suite as run_language_route_suite
startup_suite('Installed language-pack binding')
passed.extend(f'Language route {i+1}' for i in range(run_language_route_suite(mod)))
startup_suite_complete()

from Tests.runtime_followup_regression import run_suite as run_runtime_followup_suite
startup_suite('Owned process cleanup and delayed client launcher')
passed.extend(f'Runtime follow-up {i+1}' for i in range(run_runtime_followup_suite(mod)))
startup_suite_complete()

from Tests.bilingual_scorer_regression import run_suite as run_bilingual_scorer_suite
startup_suite('Bilingual scorer revision 2, frozen prompts and v1 compatibility')
passed.extend(f'Bilingual scorer {i+1}' for i in range(run_bilingual_scorer_suite(mod)))
startup_suite_complete()

from Tests.bilingual_report_regression import run_suite as run_bilingual_report_suite
startup_suite('Specialized bilingual results and matched-pair metrics')
passed.extend(f'Bilingual report {i+1}' for i in range(run_bilingual_report_suite(mod)))
startup_suite_complete()

if len(passed)!=STARTUP_CHECK_TOTAL:
    raise AssertionError(f'startup check total mismatch: {len(passed)} != {STARTUP_CHECK_TOTAL}')
print(f'PASS {len(passed)}/{len(passed)}')
