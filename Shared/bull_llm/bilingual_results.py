"""Descriptive native RU/EN metrics; never rescore, merge tracks or read prompts."""
from collections import defaultdict
import json
import math


def number(value):
    return float(value) if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None


def mean(values):
    values=[value for value in values if value is not None]
    return sum(values)/len(values) if values else None


def language_metrics(records):
    groups=defaultdict(list)
    for record in records:
        identity=record.get('identity') or {}
        if identity.get('language_track') in ('ru','en'):
            groups[identity.get('model','?')].append(record)
    output=[]
    for model,rows in sorted(groups.items()):
        tracks={}
        pairs=defaultdict(lambda:defaultdict(list))
        legacy=False
        for track in ('ru','en'):
            observed=[r for r in rows if r['identity']['language_track']==track]
            valid=[r for r in observed if r.get('execution_status','ok')=='ok']
            scores=[]; languages=[]; purity=[]; walls=[]; speeds=[]; tasks=[]
            seeds=defaultdict(list)
            for r in valid:
                identity=r['identity']; config=r.get('config') or {}; primary=r.get('primary') or {}
                score=(r.get('score') or {}).get('native') or {}
                language=score.get('language') or {}
                value=number(score.get('value')); scores.append(value)
                languages.append(float(language['language_ok']) if isinstance(language.get('language_ok'),bool) else None)
                purity.append(float(language['purity_ok']) if isinstance(language.get('purity_ok'),bool) else None)
                tasks.append(float(primary['task_completed']) if isinstance(primary.get('task_completed'),bool) else None)
                walls.append(number(primary.get('wall_seconds')))
                speeds.append(number(primary.get('eval_rate')) if primary.get('load_state')=='warm' else None)
                if value is not None:seeds[config.get('seed')].append(value)
                legacy |= score.get('method')=='bilingual_language_contract_v1'
                pair=identity.get('bilingual_pair_id')
                # Exact model/digest, pack/definition family, scorer, seed/run and
                # effective settings. Exclude prompt hashes: translated prompts differ.
                comparison={k:config.get(k) for k in (
                    'benchmark_mode','seed_mode','seed','think','primary_mode','ctx','threads',
                    'primary_predict','temperature','top_p','top_k','min_p','repeat_penalty',
                    'sampling_source','sent_runtime_options','backend_runtime_fingerprint')}
                key=(pair,identity.get('backend'),identity.get('model_digest'),
                     identity.get('benchmark_pack_identity'),identity.get('benchmark_version'),
                     identity.get('scorer_ref'),identity.get('run'),
                     json.dumps(comparison,sort_keys=True,separators=(',',':'),allow_nan=False))
                if pair and config.get('seed') is not None:
                    pairs[key][track].append(r)
            seed_means=[mean(values) for seed,values in seeds.items() if seed is not None]
            tracks[track]={
                'observed':len(observed),'valid':len(valid),'errors':len(observed)-len(valid),
                'scored':len([v for v in scores if v is not None]),'score':mean(scores),
                'language_ok':mean(languages),'language_checked':len([v for v in languages if v is not None]),
                'purity_ok':mean(purity),'task_completed':mean(tasks),
                'native_seconds':mean(walls),'warm_tok_s':mean(speeds),
                'warm_samples':len([v for v in speeds if v is not None]),
                'seed_min':min(seed_means) if seed_means else None,
                'seed_max':max(seed_means) if seed_means else None,
                'seeds':len(seed_means),
            }
        matched=[]; ambiguous=0
        for pair in pairs.values():
            if len(pair['ru'])!=1 or len(pair['en'])!=1:
                ambiguous+=int(len(pair['ru'])>1 or len(pair['en'])>1); continue
            matched.append((pair['ru'][0],pair['en'][0]))
        deltas=[]; wall_deltas=[]; successes=defaultdict(int)
        for ru,en in matched:
            def successful(r):
                score=(r.get('score') or {}).get('native') or {}
                lang=score.get('language') or {}
                value=number(score.get('value'))
                return value is not None and value>=1-1e-9 and lang.get('language_ok') is True and lang.get('purity_ok') is True and (r.get('primary') or {}).get('task_completed') is True
            a=number(((ru.get('score') or {}).get('native') or {}).get('value'))
            b=number(((en.get('score') or {}).get('native') or {}).get('value'))
            if a is not None and b is not None:deltas.append(a-b)
            a=number((ru.get('primary') or {}).get('wall_seconds'))
            b=number((en.get('primary') or {}).get('wall_seconds'))
            if a is not None and b is not None:wall_deltas.append(a-b)
            successes[(successful(ru),successful(en))]+=1
        output.append({'model':model,'tracks':tracks,'matched_pairs':len(matched),
                       'ambiguous_pairs':ambiguous,'score_pairs':len(deltas),
                       'score_delta':mean(deltas),'native_seconds_delta':mean(wall_deltas),
                       'both_pass':successes[(True,True)],'ru_only_pass':successes[(True,False)],
                       'en_only_pass':successes[(False,True)],'neither_pass':successes[(False,False)],
                       'legacy_language_scorer':legacy})
    return output
