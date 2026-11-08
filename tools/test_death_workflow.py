"""Owner-review queue isolation and bounded natural-death collection controls."""
import importlib.util
from contextlib import nullcontext
import json
import io
import shlex
from contextlib import redirect_stdout
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
            turns=100, timeout=2, stall_timeout=1, death_issue='issue', build=None, munchkin=kw.get('munchkin',False))

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

    def simulate(self, outcomes, export_error=False, result_error=None, munchkin=False, native_code=None):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'collection'
            output.mkdir()
            build = Path(d) / 'build'
            build.mkdir()
            (build / 'build.json').write_text('{}')
            seeds = list(range(3, 3 + max(3, len(outcomes))))
            args = self.options(seeds=seeds, munchkin=munchkin)
            calls = []
            def native(options):
                # Contract is frozen before ANY outcomes and before build starts.
                plan = producer.workflow.read(output / 'collection.json')
                self.assertEqual(plan['seeds'], seeds)
                self.assertTrue(options.random_birth)
                self.assertEqual(plan['borg_parameters']['borg_munchkin_start'],munchkin)
                if munchkin:
                    self.assertIn('borg_munchkin_start = TRUE',options.configuration)
                else:
                    self.assertEqual(options.configuration,'borg_save_death = 1\n')
                calls.append(options.seed)
                outcome = outcomes[len(calls)-1]
                options.output.mkdir()
                producer.workflow.write(options.output / 'result.json', {'outcome': outcome, 'states': [], 'cause': 'a foe', 'error': result_error})
                producer.workflow.write(options.output / 'recording.json', {'status':'incomplete' if outcome=='wall_timeout' else 'complete', 'outcome':outcome,'files_sha256':{}})
                return native_code if native_code is not None else int(outcome in ('stall', 'stalled', 'wall_timeout', 'crash', 'harness_failure'))
            def prepared(*_):
                self.assertEqual(producer.workflow.read(output / 'collection.json')['status'], 'preparing')
                return build
            dossiers = []
            def exported(run, issue):
                if export_error:
                    raise ValueError('export failed')
                dossier = Path(d) / f'D{len(dossiers)+1:04d}-collected'
                dossiers.append(dossier)
                return dossier
            # These are simulated games. The outer native gate may already own
            # the real validation lock; unit controls must not reacquire it.
            with mock.patch.object(producer.workflow, 'locked', return_value=nullcontext()), \
                 mock.patch.object(producer, 'prepare_build', side_effect=prepared), \
                 mock.patch.object(producer.measurement, 'run', side_effect=native), \
                 mock.patch.object(producer, 'export_death', side_effect=exported) as export:
                try:
                    code = producer.collect(args, output, seeds, 'pin')
                except ValueError:
                    code = 1
                return code, calls, producer.workflow.read(output / 'collection.json'), export.call_count

    def test_munchkin_is_frozen_before_runs_without_changing_bounds(self):
        code,calls,plan,exports=self.simulate(['turn_cap']*3,munchkin=True)
        self.assertEqual((code,calls,exports),(0,[3,4,5],0))
        self.assertTrue(plan['borg_parameters']['borg_munchkin_start'])
        self.assertEqual((plan['turn_cap'],plan['wall_limit_per_game_seconds']),(100,2))

    def test_death_continues_and_exports_every_death_without_relabelling_caps(self):
        code, calls, plan, exports = self.simulate(['death', 'turn_cap', 'death'])
        self.assertEqual((code, calls, exports), (0, [3,4,5], 2))
        self.assertEqual(plan['counts'], {'turn_cap': 1, 'death': 2})
        self.assertEqual(plan['status'], 'completed_with_deaths')
        dossiers = [e['dossier'] for e in plan['runs'] if e.get('dossier')]
        self.assertEqual(len(set(dossiers)), 2)
        self.assertNotIn('dossier', plan['runs'][1])

    def test_batch_export_allocates_distinct_ids_after_existing_dossier(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            records=root/'docs/deaths'
            (records/'D0010-collected').mkdir(parents=True)
            def command(argv,**kwargs):
                if '--output' in argv:
                    directory=Path(argv[argv.index('--output')+1])
                    directory.mkdir(exist_ok=False)
                    self.assertEqual(argv[argv.index('--id')+1],directory.name[:5])
            with mock.patch.object(producer,'ROOT',root), \
                 mock.patch.object(producer.workflow,'primary_root',return_value=root), \
                 mock.patch.object(producer.workflow,'locked',return_value=nullcontext()), \
                 mock.patch.object(producer.subprocess,'run',side_effect=command):
                exports=[producer.export_death(root/f'run-{n}','issue') for n in range(10)]
            self.assertEqual([p.name for p in exports],[f'D{n:04d}-collected' for n in range(11,21)])

    def test_ten_fresh_characters_export_all_ten_deaths(self):
        code, calls, plan, exports = self.simulate(['death'] * 10)
        self.assertEqual((code, calls, exports), (0, list(range(3,13)), 10))
        self.assertEqual(plan['counts'], {'death':10})
        self.assertEqual(len({e['directory'] for e in plan['runs']}),10)
        self.assertEqual(len({e['dossier'] for e in plan['runs']}),10)
        self.assertTrue(all(e.get('report') and e.get('replay_command') for e in plan['runs']))
        self.assertEqual(plan['status'],'completed_with_deaths')

    def test_death_with_native_error_is_exported_then_stops(self):
        for options in ({'result_error':'recording failed'}, {'native_code':1}):
            with self.subTest(options=options):
                code,calls,plan,exports=self.simulate(['death'],**options)
                self.assertEqual((code,calls,exports),(1,[3],1))
                self.assertEqual(plan['status'],'failed')
                self.assertIn('dossier',plan['runs'][0])

    def test_crash_after_death_preserves_earlier_dossier_and_stops(self):
        code,calls,plan,exports=self.simulate(['death','crash'])
        self.assertEqual((code,calls,exports),(1,[3,4],1))
        self.assertEqual(plan['counts'],{'death':1,'crash':1})
        self.assertIn('dossier',plan['runs'][0])
        self.assertEqual(plan['status'],'failed')

    def test_no_death_is_bounded_no_seed_or_cap_escalation(self):
        code, calls, plan, exports = self.simulate(['turn_cap']*3)
        self.assertEqual((code, calls, exports), (0, [3,4,5], 0))
        self.assertEqual(plan['status'], 'limits_reached_without_death')

    def test_wall_timeout_tries_fresh_seed_then_exports_first_death(self):
        code, calls, plan, exports = self.simulate(['wall_timeout', 'turn_cap', 'death'])
        self.assertEqual((code, calls, exports), (0, [3,4,5], 1))
        self.assertEqual(plan['counts'], {'wall_timeout': 1, 'turn_cap': 1, 'death': 1})
        self.assertIn('--view-only', plan['runs'][0]['replay_command'])
        self.assertIn('--from-turn latest', plan['runs'][0]['manual_play_command'])
        self.assertNotIn('--view-only', plan['runs'][1]['replay_command'])
        self.assertEqual(plan['status'], 'completed_with_deaths')

    def test_all_wall_timeouts_exhaust_declared_seeds_without_escalating(self):
        code, calls, plan, exports = self.simulate(['wall_timeout'] * 3)
        self.assertEqual((code, calls, exports), (0, [3,4,5], 0))
        self.assertEqual(plan['counts'], {'wall_timeout': 3})
        self.assertTrue(all(e['report'].endswith('/reports/summary.md') for e in plan['runs']))
        self.assertEqual(plan['status'], 'limits_reached_without_death')

    def test_wall_timeout_with_recorded_error_stops(self):
        code, calls, plan, exports = self.simulate(['wall_timeout'], result_error='reader failed')
        self.assertEqual((code, calls, exports), (1, [3], 0))
        self.assertEqual(plan['status'], 'failed')

    def test_crash_harness_failure_and_native_stall_stop(self):
        for outcome in ('crash', 'harness_failure', 'stalled'):
            with self.subTest(outcome=outcome):
                code, calls, plan, exports = self.simulate([outcome])
                self.assertEqual((code, calls, exports), (1, [3], 0))
                self.assertEqual(plan['status'], 'failed')

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


class CollectionCommands(unittest.TestCase):
    def fixture(self, root, status, outcome):
        run = root / 'game with spaces'
        run.mkdir()
        (run / 'recording.json').write_text(json.dumps({'status':status,'outcome':outcome,'files_sha256':{}}))
        result = {'outcome':outcome,'error':None}
        (run / 'result.json').write_text(json.dumps(result))
        return run, result

    def test_timeout_prints_view_only_and_safe_manual_prefix_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            run, result = self.fixture(Path(temp),'incomplete','wall_timeout')
            commands = producer.recording_commands(run,result)
            self.assertEqual(shlex.split(commands['replay_command']),['./replay-borg.py',str(run),'--view-only'])
            self.assertEqual(shlex.split(commands['manual_play_command']),['./play-from-replay.py',str(run),'--from-turn','latest'])

    def test_completed_survivor_and_death_have_replay_and_manual_commands(self):
        for outcome in ('turn_cap','death'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temp:
                run, result = self.fixture(Path(temp),'complete',outcome)
                commands = producer.recording_commands(run,result)
                self.assertNotIn('--view-only',commands['replay_command'])
                self.assertIn('manual_play_command',commands)

    def test_crash_has_view_only_but_no_manual_takeover(self):
        with tempfile.TemporaryDirectory() as temp:
            run, result = self.fixture(Path(temp),'incomplete','crash')
            commands = producer.recording_commands(run,result)
            self.assertIn('--view-only',commands['replay_command'])
            self.assertNotIn('manual_play_command',commands)

    def test_reports_mode_backfills_summary_and_index_without_new_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run,result=self.fixture(root,'incomplete','wall_timeout')
            (root/'collection.json').write_text(json.dumps({'runs':[{'seed':4,'directory':str(run)}]}))
            with mock.patch.object(producer.sys,'argv',['produce_death.py','--reports',str(root)]), \
                 mock.patch.object(producer.workflow,'locked',return_value=nullcontext()), \
                 mock.patch.object(producer,'choose_build') as build, \
                 mock.patch.object(producer,'collect') as collect, redirect_stdout(io.StringIO()):
                self.assertEqual(producer.main(),0)
                build.assert_not_called();collect.assert_not_called()
            self.assertTrue((run/'reports/summary.md').is_file())
            self.assertTrue((root/'reports.md').is_file())

    def test_commands_mode_does_not_build_lock_or_start_games(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run,result=self.fixture(root,'incomplete','wall_timeout')
            (root/'collection.json').write_text(json.dumps({'runs':[{'seed':4,'directory':str(run)}]}))
            output=io.StringIO()
            with mock.patch.object(producer.sys,'argv',['produce_death.py','--commands',str(root)]), \
                 mock.patch.object(producer,'choose_build') as build, \
                 mock.patch.object(producer,'collect') as collect, redirect_stdout(output):
                self.assertEqual(producer.main(),0)
                build.assert_not_called();collect.assert_not_called()
            self.assertIn('Watch:',output.getvalue())
            self.assertIn('Play yourself (verifies prefix first):',output.getvalue())


if __name__ == '__main__':
    unittest.main()
