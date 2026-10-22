import importlib.util
import tempfile
import unittest
import shutil
from pathlib import Path

spec = importlib.util.spec_from_file_location('harness', Path(__file__).with_name('harness.py'))
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class HarnessTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / 'run'
        h.init(self.run, '테스트 주제')

    def test_revision_budget_survives_resume(self):
        h.revise(self.run, 'QA-01 근거 수정')
        h.revise(self.run, 'QA-04 가독성 수정')
        with self.assertRaises(ValueError): h.revise(self.run, '세 번째 수정')
        self.assertEqual(h.read(self.run / 'state.json')['version'], 2)
        with self.assertRaises(FileExistsError): h.init(self.run, '같은 실행')

    def test_uncertain_write_requires_read_and_preserves_retry_budget(self):
        h.operation(self.run, 'render:v0', 'uncertain')
        with self.assertRaises(ValueError): h.operation(self.run, 'render:v0', 'transient')
        h.operation(self.run, 'render:v0', 'read')
        h.operation(self.run, 'render:v0', 'transient')
        with self.assertRaises(ValueError): h.operation(self.run, 'render:v0', 'transient')

    def test_missing_output_never_ready(self):
        result = h.check(self.run)
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(result['errors'])

    def test_unsupported_claim_and_empty_summary_rejected(self):
        content = {'slides': []}
        sources = {'sources': [], 'claims': [{'claim_id':'C1','kind':'fact','source_ids':[]}]}
        errors = h.content_errors(content, sources)
        self.assertTrue(any('근거' in error for error in errors))
        self.assertTrue(any('장수' in error for error in errors))

    def test_recovered_write_does_not_consume_another_attempt(self):
        h.operation(self.run, 'render:v0', 'uncertain')
        h.operation(self.run, 'render:v0', 'read')
        h.operation(self.run, 'render:v0', 'recovered')
        op = h.read(self.run / 'state.json')['operations']['render:v0']
        self.assertEqual(op['attempts'], 1)
        with self.assertRaises(ValueError): h.operation(self.run, 'render:v0', 'success')

    def test_revision_never_reuses_seed_or_inherits_review(self):
        h.write(self.run / 'v0/content.json', {'use_seed_frames': True})
        h.write(self.run / 'v0/review.json', {'status':'pass'})
        h.revise(self.run, 'QA-04 수정')
        self.assertFalse(h.read(self.run / 'v1/content.json')['use_seed_frames'])
        self.assertFalse((self.run / 'v1/review.json').exists())

    def test_revision_preserves_sources_per_version(self):
        h.write(self.run / 'sources.json', {'sources': ['최초 출처']})
        h.revise(self.run, '추가 예시의 출처 구분')
        h.write(self.run / 'v1/sources.json', {'sources': ['새 출처']})
        self.assertEqual(h.read(h.sources_path(self.run, self.run / 'v0')), {'sources': ['최초 출처']})
        self.assertEqual(h.read(h.sources_path(self.run, self.run / 'v1')), {'sources': ['새 출처']})

    def test_visual_plan_required_and_long_text_rejected(self):
        policy = h.read(self.run / 'settings/harness-config.json')['visual_policy']
        slides = []
        for order in range(1, 7):
            slides.append(dict(order=order, role='cover' if order == 1 else 'saveable_summary' if order == 6 else 'example',
                role_reason='synthetic fixture', key_message='test', title='test', body_blocks=['short explanation'],
                visual_intent='process', panels=[{'title':'test'}], mascot_required=False, summary_items=['test'],
                visual_explanation=dict(kind='process_diagram', communicates='input to output', elements=['input','arrow','output'], ramy_role='diagram instead')))
        content = {'slides':slides}
        self.assertEqual(h.content_errors(content, {'sources':[], 'claims':[]}, policy), [])
        slides[1]['visual_explanation']['kind'] = 'text_boxes'
        slides[1]['body_blocks'] = ['one','two','three']
        errors = h.content_errors(content, {'sources':[], 'claims':[]}, policy)
        self.assertIn('2: 설명 그림 계획 누락·텍스트 중심 구성', errors)
        self.assertIn('2: 본문 풀이 줄 수 초과', errors)


if __name__ == '__main__': unittest.main()
