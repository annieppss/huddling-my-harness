import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.harness import Harness, PROJECT, read_json, save, invoke, sha
from harness.gates import validate


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(PROJECT / 'harness', self.root / 'harness', ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('PRD.md', 'design.md', 'story-service.md', 'story-work.md', 'harness-purpose.md'):
            shutil.copy(PROJECT / name, self.root / name)
        self.rules = read_json(self.root / 'harness/rules.json')
        self.brief = {'title': 'Synthetic test only', 'screen_ids': ['library', 'detail'],
                      'references': [{'id': 'r1', 'source': 'test-fixture', 'excerpt': 'Cards group related learning materials.'}],
                      'operator_feedback': ''}
        save(self.root / 'input.json', self.brief)
        self.runner = Harness(self.root, 'test')
        self.runner.init(self.root / 'input.json')
        component = {'id': 'cta', 'kind': 'button', 'fill': 'colors.primary',
                     'text_color': 'colors.on-primary', 'radius': 'rounded.full',
                     'typography': 'typography.link', 'spacing': 'spacing.md', 'shadow': False,
                     'accent_usage': 'none', 'variant': 'primary'}
        self.outputs = {
            'research': {'references': [{'id': 'r1', 'observation': 'Cards group learning materials.',
                                        'apply': 'Group library content by topic.', 'evidence': self.brief['references'][0]['excerpt']}]},
            'plan': {'screens': [{'id': s, 'title': s, 'purpose': 'Browse learning material',
                                  'roles': ['free'], 'story_ids': [1]} for s in self.brief['screen_ids']],
                     'flows': [{'id': 'browse', 'screen_ids': self.brief['screen_ids'], 'description': 'Library to detail'}],
                     'asset_policy': copy.deepcopy(self.rules['policy'])},
            'concept': {'frames': [{'id': f'frame-{s}', 'screen_id': s, 'width': 390, 'height': 844,
                                    'description': 'Synthetic key screen layout'} for s in self.brief['screen_ids']]},
            'design': {'tokens': copy.deepcopy(self.rules['tokens']), 'components': [component],
                       'screens': [{'id': s, 'width': 390, 'height': 844, 'component_ids': ['cta'],
                                    'description': 'Synthetic design specification'} for s in self.brief['screen_ids']],
                       'asset_policy': copy.deepcopy(self.rules['policy'])},
            'review': {'checks': [{'id': c, 'status': 'pass', 'evidence': 'Synthetic test assertion; not a real design review.'}
                                  for c in self.rules['review_checks']], 'findings': []},
        }

    def reach(self, stage):
        for previous in self.rules['stages'][:self.rules['stages'].index(stage)]:
            if previous == 'design' and self.runner.status()['status'] == 'awaiting_approval':
                self.runner.approve('TEST FIXTURE ONLY', self.runner.status()['approval_key'])
            result = self.runner.accept(previous, self.outputs[previous])
            self.assertNotEqual(result['status'], 'rejected', result)
        if stage == 'design':
            self.runner.approve('TEST FIXTURE ONLY', self.runner.status()['approval_key'])

    def test_complete_pipeline_and_resume(self):
        self.reach('review')
        result = self.runner.accept('review', self.outputs['review'])
        self.assertEqual(result['status'], 'structured_design_passed')
        before = sha(self.runner.run / 'state.json')
        resumed = Harness(self.root, 'test').status()
        self.assertEqual(resumed, result)
        self.assertEqual(before, sha(self.runner.run / 'state.json'))

    def test_cannot_skip_to_design(self):
        with self.assertRaises(ValueError):
            self.runner.accept('design', self.outputs['design'])
        self.assertFalse(self.runner.artifact('design').exists())

    def test_approval_gate_blocks_agent_and_accept(self):
        self.reach('concept')
        result = self.runner.accept('concept', self.outputs['concept'])
        self.assertEqual(result['status'], 'awaiting_approval')
        with self.assertRaises(ValueError):
            self.runner.prompt()
        with self.assertRaises(ValueError):
            self.runner.accept('design', self.outputs['design'])

    def test_changed_concept_revokes_approval(self):
        self.reach('design')
        self.outputs['concept']['frames'][0]['description'] = 'Changed design'
        save(self.runner.artifact('concept'), self.outputs['concept'])
        self.assertEqual(self.runner.status()['status'], 'stale')
        result = self.runner.accept('concept', self.outputs['concept'])
        self.assertEqual(result['status'], 'awaiting_approval')

    def test_stale_approval_key_rejected(self):
        self.reach('concept')
        old = self.runner.accept('concept', self.outputs['concept'])['approval_key']
        self.runner.rewind('concept')
        self.outputs['concept']['frames'][0]['description'] += ' revised'
        self.runner.accept('concept', self.outputs['concept'])
        with self.assertRaises(ValueError):
            self.runner.approve('TEST', old)

    def test_design_rewind_preserves_concept_approval(self):
        self.reach('review')
        result = self.runner.rewind('design')
        self.assertEqual(result['stage'], 'design')
        self.assertEqual(result['status'], 'ready')
        self.assertTrue(self.runner.artifact('design').exists())

    def test_plan_change_invalidates_downstream(self):
        self.reach('review')
        self.outputs['plan']['screens'][0]['purpose'] = 'Revised purpose'
        save(self.runner.artifact('plan'), self.outputs['plan'])
        self.assertEqual(self.runner.status()['stage'], 'plan')
        self.runner.accept('plan', self.outputs['plan'])
        state = read_json(self.runner.run / 'state.json')
        self.assertEqual(set(state['receipts']), {'research', 'plan'})
        self.assertIsNone(state['approval'])

    def test_service_privacy_and_sale_review_cannot_be_disabled(self):
        self.reach('plan')
        for field, value in [('default_visibility', 'member_only'),
                             ('publish_requires_owner_choice', False), ('sale_requires_review', False),
                             ('sale_request_roles', ['free'])]:
            candidate = copy.deepcopy(self.outputs['plan'])
            candidate['asset_policy'][field] = value
            result = self.runner.accept('plan', candidate)
            self.assertEqual(result['status'], 'rejected', field)
            self.assertIn('service invariant', ' '.join(result['errors']))
        self.assertFalse(self.runner.artifact('plan').exists())

    def test_unprovided_reference_evidence_fails(self):
        self.outputs['research']['references'][0]['evidence'] = 'Invented competitor claim'
        self.assertEqual(self.runner.accept('research', self.outputs['research'])['status'], 'rejected')

    def test_missing_screen_and_unknown_flow_fail(self):
        self.reach('plan')
        self.outputs['plan']['screens'][0]['id'] = 'invented'
        self.assertEqual(self.runner.accept('plan', self.outputs['plan'])['status'], 'rejected')

    def test_wrong_frame_and_duplicate_key_screen_fail(self):
        self.reach('concept')
        for mutate in ('width', 'duplicate'):
            candidate = copy.deepcopy(self.outputs['concept'])
            if mutate == 'width': candidate['frames'][0]['width'] = 391
            else: candidate['frames'][1]['screen_id'] = 'library'
            self.assertEqual(self.runner.accept('concept', candidate)['status'], 'rejected')

    def test_token_and_component_violations_fail(self):
        self.reach('design')
        mutations = [lambda d: d['tokens'].update({'colors.accent': '#ff0000'}),
                     lambda d: d['components'][0].update(shadow=True),
                     lambda d: d['components'][0].update(radius='rounded.md'),
                     lambda d: d['components'][0].update(fill='colors.accent', accent_usage='popular'),
                     lambda d: d['components'][0].update(typography='typography.invented')]
        for mutate in mutations:
            candidate = copy.deepcopy(self.outputs['design']); mutate(candidate)
            self.assertEqual(self.runner.accept('design', candidate)['status'], 'rejected')

    def test_unknown_review_and_missing_checks_fail(self):
        self.reach('review')
        candidate = copy.deepcopy(self.outputs['review'])
        candidate['checks'][0]['status'] = 'unknown'
        self.assertEqual(self.runner.accept('review', candidate)['status'], 'rejected')
        candidate = copy.deepcopy(self.outputs['review']); candidate['checks'].pop()
        self.assertEqual(self.runner.accept('review', candidate)['status'], 'rejected')

    def test_reviewer_cannot_edit_artifacts_via_response(self):
        self.reach('review')
        before = sha(self.runner.artifact('design'))
        candidate = copy.deepcopy(self.outputs['review'])
        candidate['files'] = {'../design/artifact.json': {}}
        self.assertEqual(self.runner.accept('review', candidate)['status'], 'rejected')
        self.assertEqual(before, sha(self.runner.artifact('design')))

    def test_review_routes_to_earliest_failed_stage(self):
        self.reach('review')
        candidate = copy.deepcopy(self.outputs['review'])
        candidate['findings'] = [{'message': 'Wrong design', 'return_to': 'design'},
                                 {'message': 'Missing flow', 'return_to': 'plan'}]
        result = self.runner.accept('review', candidate)
        self.assertEqual(result['return_to'], 'plan')
        self.assertEqual(result['violation_count'], 2)

    def test_unknown_review_requests_input_and_malformed_review_is_rejected(self):
        self.reach('review')
        candidate = copy.deepcopy(self.outputs['review'])
        candidate['checks'][0]['status'] = 'unknown'
        result = self.runner.accept('review', candidate)
        self.assertEqual(result['return_to'], 'needs_user_input')
        self.assertEqual(result['unknown_count'], 1)
        self.assertEqual(self.runner.accept('review', {'checks': None, 'findings': None})['status'], 'rejected')

    def test_approval_from_pipe_fails(self):
        with patch('scripts.harness.PROJECT', self.root), patch('sys.argv',
                ['harness', '--run', 'test', 'approve', '--reviewer', 'TEST']), patch('sys.stdin.isatty', return_value=False):
            self.reach('concept'); self.runner.accept('concept', self.outputs['concept'])
            from scripts.harness import main
            self.assertEqual(main(), 1)
            self.assertIsNone(read_json(self.runner.run / 'state.json')['approval'])

    def test_snapshot_change_is_stale_original_change_is_pinned(self):
        self.runner.accept('research', self.outputs['research'])
        (self.root / 'PRD.md').write_text('Updated original')
        self.assertEqual(self.runner.status()['stage'], 'plan')
        (self.runner.run / 'context/PRD.md').write_text('Changed snapshot')
        self.assertEqual(self.runner.status()['status'], 'stale')
        self.assertEqual(self.runner.status()['stage'], 'research')

    def test_response_from_old_input_rejected(self):
        expected = self.runner.fingerprint('research')
        self.brief['operator_feedback'] = 'Changed input'
        save(self.runner.run / 'brief.json', self.brief)
        with self.assertRaises(ValueError):
            self.runner.accept('research', self.outputs['research'], expected)

    def test_input_change_during_prompt_does_not_dispatch(self):
        original = Harness.prompt
        def changed_prompt(runner):
            text = original(runner)
            brief = read_json(runner.run / 'brief.json')
            brief['operator_feedback'] = 'Edited while preparing prompt'
            save(runner.run / 'brief.json', brief)
            return text
        with patch('scripts.harness.PROJECT', self.root), patch('sys.argv',
                ['harness', '--run', 'test', 'next', '--provider', 'codex']), \
                patch.object(Harness, 'prompt', changed_prompt), patch('scripts.harness.invoke') as mocked:
            from scripts.harness import main
            self.assertEqual(main(), 1)
            mocked.assert_not_called()

    def test_path_escape_and_symlink_rejected(self):
        with self.assertRaises(ValueError): Harness(self.root, '../outside')
        with self.assertRaises(ValueError): self.runner.artifact('../../outside')
        (self.runner.run / 'escape').symlink_to(self.root / 'PRD.md')
        with self.assertRaises(ValueError): self.runner.status()

    def test_duplicate_json_keys_and_bool_dimensions_rejected(self):
        bad = self.root / 'bad.json'; bad.write_text('{"x":1,"x":2}')
        with self.assertRaises(ValueError): read_json(bad)
        self.reach('concept')
        self.outputs['concept']['frames'][0]['width'] = True
        self.assertEqual(self.runner.accept('concept', self.outputs['concept'])['status'], 'rejected')

    def test_lock_prevents_write(self):
        (self.runner.run / '.lock').write_text('test')
        with self.assertRaises(ValueError): self.runner.accept('research', self.outputs['research'])
        self.assertFalse(self.runner.artifact('research').exists())

    def test_placeholder_brief_and_reinit_rejected(self):
        self.brief['references'][0]['excerpt'] = 'REPLACE_ME'
        save(self.root / 'bad-brief.json', self.brief)
        other = Harness(self.root, 'bad')
        with self.assertRaises(ValueError): other.init(self.root / 'bad-brief.json')
        self.assertFalse(other.run.exists())
        with self.assertRaises(ValueError): self.runner.init(self.root / 'input.json')

    def test_cli_provider_failure_and_timeout(self):
        with patch('scripts.harness.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'error')):
            with self.assertRaises(ValueError): invoke('claude', 'test', 1)
        with patch('scripts.harness.subprocess.run', side_effect=subprocess.TimeoutExpired('claude', 1)):
            with self.assertRaises(subprocess.TimeoutExpired): invoke('claude', 'test', 1)
        self.assertEqual(self.runner.status()['stage'], 'research')

    def test_provider_adapters_use_stdin_and_restricted_flags(self):
        def fake(cmd, **kwargs):
            self.assertEqual(kwargs['input'], 'test prompt')
            self.assertNotIn('shell', kwargs)
            self.assertNotEqual(Path(kwargs['cwd']), PROJECT)
            if cmd[0] == 'codex':
                self.assertIn('read-only', cmd)
                Path(cmd[cmd.index('--output-last-message')+1]).write_text('{"ok":true}')
                return subprocess.CompletedProcess(cmd, 0, '', '')
            self.assertIn('--safe-mode', cmd)
            self.assertEqual(cmd[cmd.index('--tools')+1], '')
            return subprocess.CompletedProcess(cmd, 0, '{"ok":true}', '')
        with patch('scripts.harness.subprocess.run', side_effect=fake):
            self.assertEqual(invoke('codex', 'test prompt', 1), {'ok': True})
            self.assertEqual(invoke('claude', 'test prompt', 1), {'ok': True})


if __name__ == '__main__':
    unittest.main()
