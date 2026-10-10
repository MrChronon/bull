import json
from pathlib import Path
import unittest
import zipfile


class BilingualScorerTests(unittest.TestCase):
    core=None
    def score(self,prose,language='ru',revision=2):
        item={'expected_language':language,'reference':{'ok':True},'score_type':f'bilingual_language_contract_v{revision}'}
        return self.core.benchmark_score('language',item,prose+'\nBENCHMARK_RESULT\n'+json.dumps({'ok':True}))

    def test_english_in_russian_track_is_penalized(self):
        result=self.score('The service is deployed internally and cloud synchronization is disabled. '*2)
        self.assertFalse(result['language']['language_ok']); self.assertLess(result['value'],1)

    def test_russian_in_english_track_is_penalized(self):
        result=self.score('Сервис развёрнут во внутренней сети, облачная синхронизация отключена. '*2,'en')
        self.assertFalse(result['language']['language_ok']); self.assertLess(result['value'],1)

    def test_chinese_in_russian_prose_is_penalized_without_changing_v1(self):
        text='Среднее время ответа уменьшилось, но причинность не доказана. '*5+'另一半'
        old=self.score(text,revision=1); new=self.score(text)
        self.assertEqual(old['value'],1); self.assertEqual(new['value'],.9)
        self.assertEqual(new['language']['other_script_letters'],3)
        self.assertFalse(new['language']['purity_ok'])

    def test_json_english_keys_are_not_language_switching(self):
        result=self.score('Подтверждено внутреннее размещение сервиса, синхронизация отключена. '*3)
        self.assertEqual(result['value'],1); self.assertEqual(result['language']['other_script_letters'],0)

    def test_both_prompt_and_reference_are_frozen_from_previous_pack(self):
        root=Path(self.core.__file__).parent
        build=(root/'Build-Release.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('$releaseZipPaths -ccontains $rel',build)
        self.assertIn('Mandatory release file excluded from inventory',build)
        with zipfile.ZipFile(root/'Tests/Fixtures/bull_language_comparison@1.0.0.zip') as archive:
            old=json.loads(archive.read('cases.json'))
        new=json.loads((root/'BenchmarkPacks/bull_language_comparison/cases.json').read_text(encoding='utf-8'))
        self.assertEqual([x['id'] for x in old],[x['id'] for x in new])
        for before,after in zip(old,new):
            for key in ('prompt','result_instruction','reference','primary_predict','num_ctx'):
                self.assertEqual(before['definition'][key],after['definition'][key])
            self.assertEqual(after['scorer_ref'],'bilingual_language_contract_v2')
            self.assertEqual(after['version'],2)


def run_suite(core):
    BilingualScorerTests.core=core
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(BilingualScorerTests))
    if not result.wasSuccessful():raise AssertionError('Bilingual scorer revision regression failed')
    return result.testsRun
