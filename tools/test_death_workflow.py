"""Owner-review queue isolation and bounded natural-death collection controls."""
import importlib.util
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load('test_death_helpers', ROOT / 'tools/death-workflow.py')
queue = load('test_death_queue', ROOT / 'replay_next_death.py')
producer = load('test_death_producer', ROOT / 'produce_death.py')


class OwnerQueue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'docs/deaths').mkdir(parents=True)
        (self.root / 'docs/deaths/owner-reviews.json').write_text(json.dumps({'reviews': {}}))
        for patch in (mock.patch.object(helper, 'ROOT', self.root),
                      mock.patch.object(helper, 'artifacts', return_value=self.root / 'artifacts'),
                      mock.patch.object(queue, 'workflow', helper)):
            patch.start()
            self.addCleanup(patch.stop)

    def case(self, name, family, recorded=True, verified_family=None):
        p = self.root / 'docs/deaths' / name
        p.mkdir()
        r = {'id': name[:5], 'encounter_family': family, 'raw_cause': 'a foe', 'identity': {'turn': 77}}
        if recorded:
            bundle = self.root / (name + '-raw')
            bundle.mkdir()
            (bundle / 'recording.json').write_text('{}')
            r['recording'] = {'raw_directory': str(bundle), 'manifest_sha256': helper.sha(bundle / 'recording.json')}
        (p / 'record.json').write_text(json.dumps(r))
        a = {'classification': 'unassessed'}
        if verified_family:
            a.update(encounter_family=verified_family, encounter_family_qualification={'status': 'verified'})
        (p / 'assessment.json').write_text(json.dumps(a))
        return p

    def test_deduplicates_qualified_family_and_mark_is_separate_from_assessment(self):
        self.case('D0001-first', 'a', False)
        second = self.case('D0002-repeat', 'b', True, 'a')
        original = (second / 'assessment.json').read_bytes()
        self.assertEqual(len(helper.queue()), 1)
        self.assertEqual(helper.queue()[0]['playable']['case'], 'D0002')
        helper.mark('D0002', True)
        self.assertTrue(helper.queue()[0]['reviewed'])
        self.assertEqual((second / 'assessment.json').read_bytes(), original)
        helper.mark('D0001', False)
        self.assertFalse(helper.queue()[0]['reviewed'])

    def test_missing_movie_and_viewer_exit_do_not_complete_owner_review(self):
        self.case('D0001-old', 'legacy', False)
        self.case('D0002-new', 'new')
        args = SimpleNamespace(mark_reviewed=None, mark_unreviewed=None, list=False,
            case=None, timeout=90, from_turn=0, view_only=False, verify_only=False)
        with mock.patch.object(queue.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(queue.run(args), 0)
        self.assertIn(str(self.root / 'docs/deaths/D0002-new'), run.call_args.args[0])
        self.assertIn('0', run.call_args.args[0])
        self.assertFalse(any(g['reviewed'] for g in helper.queue()))
        self.assertFalse((self.root / 'artifacts/owner-reviews.json').exists())

    def test_manifest_tampering_is_unavailable_and_not_marked_reviewed(self):
        p = self.case('D0001-new', 'a')
        bundle = Path(json.loads((p / 'record.json').read_text())['recording']['raw_directory'])
        (bundle / 'recording.json').write_text('changed')
        self.assertIsNone(helper.queue()[0]['playable'])
        self.assertFalse(helper.queue()[0]['reviewed'])

    def test_local_unreviewed_override_wins_over_committed_receipt(self):
        self.case('D0001-new', 'a')
        (self.root / 'docs/deaths/owner-reviews.json').write_text(json.dumps({'reviews': {'a': {'reviewed': True}}}))
        self.assertTrue(helper.queue()[0]['reviewed'])
        helper.mark('D0001', False)
        self.assertFalse(helper.queue()[0]['reviewed'])


class Collection(unittest.TestCase):
    def options(self, **kw):
        return SimpleNamespace(games=kw.get('games'), seed=kw.get('seed'), seeds=kw.get('seeds'),
            turns=100, timeout=2, stall_timeout=1, death_issue='issue', build=None)

    def test_prospective_seeds_unique_and_no_mixed_seed_modes(self):
        self.assertEqual(producer.seeds_for(self.options(games=2, seed=0xffffffff)), [0xffffffff, 0])
        for args in (self.options(seeds=[2, 2]), self.options(seeds=[3], games=1), self.options(seeds=[])):
            with self.assertRaises(ValueError):
                producer.seeds_for(args)

    def test_nonrecording_build_is_rejected_before_native_execution(self):
        with tempfile.TemporaryDirectory() as d:
            build = Path(d)
            (build / 'build.json').write_text(json.dumps({'complete': True, 'instrumented': True}))
            args = self.options()
            args.build = build
            with mock.patch.object(producer.measurement, 'run') as native:
                with self.assertRaises(ValueError):
                    producer.prepare_build(args, 'pin')
            native.assert_not_called()

    def simulate(self, outcomes, export_error=False):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'collection'
            output.mkdir()
            build = Path(d) / 'build'
            build.mkdir()
            (build / 'build.json').write_text('{}')
            args = self.options(seeds=[3, 4, 5])
            calls = []
            def native(options):
                # Contract is frozen before ANY outcomes and before build starts.
                plan = producer.workflow.read(output / 'collection.json')
                self.assertEqual(plan['seeds'], [3, 4, 5])
                calls.append(options.seed)
                outcome = outcomes[len(calls)-1]
                options.output.mkdir()
                producer.workflow.write(options.output / 'result.json', {'outcome': outcome, 'states': [], 'cause': 'a foe'})
                return int(outcome == 'stall')
            def prepared(*_):
                self.assertEqual(producer.workflow.read(output / 'collection.json')['status'], 'preparing')
                return build
            # These are simulated games. The outer native gate may already own
            # the real validation lock; unit controls must not reacquire it.
            with mock.patch.object(producer.workflow, 'locked', return_value=nullcontext()), \
                 mock.patch.object(producer, 'prepare_build', side_effect=prepared), \
                 mock.patch.object(producer.measurement, 'run', side_effect=native), \
                 mock.patch.object(producer, 'export_death', side_effect=ValueError('export failed') if export_error else None,
                                   return_value=Path(d) / 'D0006-collected') as export:
                try:
                    code = producer.collect(args, output, [3,4,5], 'pin')
                except ValueError:
                    code = 1
                return code, calls, producer.workflow.read(output / 'collection.json'), export.call_count

    def test_first_death_stops_and_exports_without_relabelling_caps(self):
        code, calls, plan, exports = self.simulate(['turn_cap', 'death'])
        self.assertEqual((code, calls, exports), (0, [3,4], 1))
        self.assertEqual(plan['counts'], {'turn_cap': 1, 'death': 1})
        self.assertEqual(plan['status'], 'natural_death_recorded')

    def test_no_death_is_bounded_no_seed_or_cap_escalation(self):
        code, calls, plan, exports = self.simulate(['turn_cap']*3)
        self.assertEqual((code, calls, exports), (0, [3,4,5], 0))
        self.assertEqual(plan['status'], 'limits_reached_without_death')

    def test_stall_stops_and_remains_operational_failure(self):
        code, calls, plan, exports = self.simulate(['stall'])
        self.assertEqual((code, calls, exports), (1, [3], 0))
        self.assertEqual(plan['counts'], {'stall': 1})
        self.assertEqual(plan['status'], 'failed')

    def test_export_failure_keeps_real_death_and_error_without_next_game(self):
        code, calls, plan, exports = self.simulate(['death'], export_error=True)
        self.assertEqual((code, calls, exports), (1, [3], 1))
        self.assertEqual(plan['counts'], {'death': 1})
        self.assertEqual(plan['status'], 'failed')
        self.assertIn('export failed', plan['error'])


if __name__ == '__main__':
    unittest.main()
