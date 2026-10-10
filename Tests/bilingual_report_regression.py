from copy import deepcopy
import contextlib
import io
import unittest
from unittest.mock import patch


def record(track,score=1,seed=42,run=1,**options):
    return {'record_schema_version':4,'execution_status':'ok',
            'identity':{'model':'model','model_digest':'digest','backend':'ollama','language_track':track,
                        'benchmark':'lang_'+track+'_case','bilingual_pair_id':'case','run':run,
                        'benchmark_pack_identity':'pack@1.0.1','benchmark_version':2,'scorer_ref':'v2'},
            'config':{'seed':seed,'think':False,**options},
            'primary':{'task_completed':True,'eval_rate':20,'wall_seconds':2,'load_state':'warm'},
            'score':{'native':{'value':score,'method':'bilingual_language_contract_v2',
                               'language':{'language_ok':score==1,'purity_ok':True}}},
            'final':{'pipeline_wall_seconds':99,'answer':'PRIVATE ANSWER MUST NOT LEAK'},
            'recovery':{'used':True}}


class BilingualReportTests(unittest.TestCase):
    core=None
    def metrics(self,rows):
        from Shared.bull_llm.bilingual_results import language_metrics
        return language_metrics(rows)[0]

    def test_tracks_remain_separate_and_pair_delta_is_matched(self):
        rows=[record('ru',.5),record('en',1)]
        values=self.metrics(rows)
        self.assertEqual(values['tracks']['ru']['score'],.5)
        self.assertEqual(values['tracks']['en']['score'],1)
        self.assertEqual(values['score_delta'],-.5); self.assertEqual(values['matched_pairs'],1)
        self.assertEqual(values['en_only_pass'],1)

    def test_unmatched_seeds_and_changed_configuration_do_not_make_pairs(self):
        for en in (record('en',seed=43),record('en',temperature=.5)):
            values=self.metrics([record('ru'),en])
            self.assertEqual(values['matched_pairs'],0); self.assertIsNone(values['score_delta'])

    def test_duplicate_attempts_are_ambiguous_not_extra_observations_in_pairs(self):
        values=self.metrics([record('ru'),record('ru'),record('en')])
        self.assertEqual(values['matched_pairs'],0); self.assertEqual(values['ambiguous_pairs'],1)

    def test_missing_language_and_cold_speed_stay_unknown(self):
        row=record('ru'); row['score']['native']['language']={}; row['primary']['load_state']='cold'
        values=self.metrics([row])['tracks']['ru']
        self.assertIsNone(values['language_ok']); self.assertIsNone(values['warm_tok_s'])
        self.assertEqual(values['language_checked'],0)

    def test_native_time_does_not_absorb_recovery_time_and_input_is_immutable(self):
        rows=[record('ru'),record('en')]; before=deepcopy(rows)
        values=self.metrics(rows)
        self.assertEqual(values['tracks']['ru']['native_seconds'],2); self.assertEqual(rows,before)

    def test_html_has_specialized_primary_view_without_raw_answers(self):
        from Shared.bull_llm.bilingual_results import language_metrics
        from Shared.bull_llm.results_report import render_report
        rows=[record('ru'),record('en')]; values=language_metrics(rows)
        values[0]['model']='<script>alert(1)</script>'
        document=render_report([],[],language='ru',bilingual=values)
        self.assertIn('id="bilingual"',document); self.assertIn('Сопоставленные пары RU/EN',document)
        self.assertLess(document.index('id="bilingual"'),document.index('id="rankings"'))
        self.assertIn('&lt;script&gt;',document); self.assertNotIn('<script>',document)
        self.assertNotIn('PRIVATE ANSWER',document)

    def test_terminal_language_summary_does_not_rank_merged_quality(self):
        out=io.StringIO()
        with patch.object(self.core,'ui_section'),contextlib.redirect_stdout(out):
            self.core.benchmark_summary([record('ru'),record('en')])
        self.assertIn('RU · Native',out.getvalue()); self.assertIn('EN · Native',out.getvalue())
        self.assertNotIn('Top 3',out.getvalue())


def run_suite(core):
    BilingualReportTests.core=core
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(BilingualReportTests))
    if not result.wasSuccessful():raise AssertionError('Specialized bilingual report regression failed')
    return result.testsRun
