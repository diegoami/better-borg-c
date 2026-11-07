"""Build selection/approval controls; no native games or compiler invocation."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('producer_offer_tests', ROOT / 'produce_death.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class BuildOffer(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for patch in (mock.patch.object(producer.workflow, 'artifacts', return_value=self.root / 'artifacts'),
                      mock.patch.object(producer.workflow, 'primary_root', return_value=self.root)):
            patch.start()
            self.addCleanup(patch.stop)
        self.commit = 'a' * 40
        self.args = SimpleNamespace(build=None, yes=False, no_build=False)

    def cache(self, commit=None):
        source = commit or self.commit
        build, hashes = producer.build_identity(source)
        binary = build / 'build/game/angband'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'nonexecuted fixture engine')
        data = build / 'source/lib/gamedata/class.txt'
        data.parent.mkdir(parents=True)
        data.write_text('fixture data')
        manifest = {'complete': True, 'instrumented': True, 'recording_schema': 'borg-recording@1',
                    'source_commit': source, 'tools_sha256': hashes,
                    'binary_sha256': producer.workflow.sha(binary),
                    'data_sha256': {'lib/gamedata/class.txt': producer.workflow.sha(data)}}
        producer.workflow.write(build / 'build.json', manifest)
        return build

    def test_current_cache_runs_without_offer_or_rebuild(self):
        build = self.cache()
        choice = producer.choose_build(self.args, self.commit)
        with mock.patch('builtins.input') as ask, mock.patch.object(producer.measurement, 'prepare') as compile:
            self.assertFalse(producer.approve_build(self.args, choice))
            self.assertEqual(producer.prepare_build(self.args, self.commit), build)
        ask.assert_not_called()
        compile.assert_not_called()

    def test_equivalent_source_reuse_reports_actual_build_commit(self):
        build = self.cache()
        requested = 'b' * 40
        with mock.patch.object(producer, 'source_matches', return_value=True), \
             mock.patch.object(producer.measurement, 'git', return_value='Documentation update'):
            choice = producer.choose_build(self.args, requested)
            output = io.StringIO()
            with redirect_stdout(output):producer.announce_build(choice, requested)
        self.assertEqual(choice.path, build)
        self.assertEqual(choice.manifest['source_commit'], self.commit)
        self.assertIn(self.commit[:12], output.getvalue())
        self.assertIn(requested[:12], output.getvalue())
        self.assertIn('carry ledger match', output.getvalue())

    def test_changed_source_does_not_select_old_build_and_requires_approval(self):
        self.cache()
        with mock.patch.object(producer, 'source_matches', return_value=False):
            choice = producer.choose_build(self.args, 'b' * 40)
            self.assertFalse(choice.reuse)
            with mock.patch.object(producer.measurement, 'prepare') as compile:
                with self.assertRaisesRegex(ValueError, 'after preflight'):
                    producer.prepare_build(self.args, 'b' * 40)
            compile.assert_not_called()

    def test_corrupt_exact_cache_is_preserved_and_rejected(self):
        build = self.cache()
        data = build / 'source/lib/gamedata/class.txt'
        data.write_text('changed')
        with mock.patch.object(producer.measurement, 'prepare') as compile:
            with self.assertRaisesRegex(ValueError, 'data changed'):
                producer.choose_build(self.args, self.commit)
        compile.assert_not_called()
        self.assertEqual(data.read_text(), 'changed')

    def test_declining_offer_creates_no_collection_and_never_locks_or_runs(self):
        choice = SimpleNamespace(path=self.root / 'missing', reuse=False, manifest=None)
        output = self.root / 'not-created'
        argv = ['produce_death.py', '--output', str(output)]
        with mock.patch.object(sys, 'argv', argv), \
             mock.patch.object(producer.measurement, 'git', return_value=self.commit), \
             mock.patch.object(producer, 'choose_build', return_value=choice), \
             mock.patch.object(sys.stdin, 'isatty', return_value=True), \
             mock.patch('builtins.input', return_value='n'), \
             mock.patch.object(producer.workflow, 'locked') as lock, \
             mock.patch.object(producer, 'collect') as collect:
            self.assertEqual(producer.main(), 0)
        self.assertFalse(output.exists())
        lock.assert_not_called()
        collect.assert_not_called()

    def test_noninteractive_missing_build_needs_yes_and_no_build_rejects(self):
        choice = SimpleNamespace(reuse=False)
        with mock.patch.object(sys.stdin, 'isatty', return_value=False), mock.patch('builtins.input') as ask:
            with self.assertRaisesRegex(ValueError, '--yes'):
                producer.approve_build(self.args, choice)
        ask.assert_not_called()
        self.args.yes = True
        self.assertTrue(producer.approve_build(self.args, choice))
        self.args.no_build = True
        with self.assertRaisesRegex(ValueError, '--no-build'):
            producer.approve_build(self.args, choice)

    def test_build_approved_before_lock_is_revalidated_and_compiled_once(self):
        target, _ = producer.build_identity(self.commit)
        self.args._build_approved = True
        def compile(options):
            self.assertEqual(options.ref, self.commit)
            self.assertEqual(options.output, target)
            self.cache()
        with mock.patch.object(producer.measurement, 'prepare', side_effect=compile) as build:
            self.assertEqual(producer.prepare_build(self.args, self.commit), target)
        build.assert_called_once()

    def test_check_build_never_creates_output_or_runs_a_game(self):
        self.cache()
        output = self.root / 'not-created'
        with mock.patch.object(sys, 'argv', ['produce_death.py', '--check-build', '--output', str(output)]), \
             mock.patch.object(producer.measurement, 'git', return_value=self.commit), \
             mock.patch.object(producer, 'collect') as collect, \
             mock.patch.object(producer.workflow, 'locked') as lock:
            self.assertEqual(producer.main(), 0)
        self.assertFalse(output.exists())
        collect.assert_not_called()
        lock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
