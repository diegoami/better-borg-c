"""Fail-closed result and watchdog controls; no native game required."""
import importlib.util
from pathlib import Path
import json
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('measure', Path(__file__).with_name('measure-native.py'))
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


class Results(unittest.TestCase):
    def test_random_birth_is_opt_in_to_frozen_measurement_and_uses_native_choices(self):
        self.assertEqual(measure.birth_keys(), measure.INPUT)
        self.assertTrue(measure.birth_keys().startswith('key space\nkey a\nkey a\nkey a\n'))
        self.assertTrue(measure.birth_keys(True).startswith('key space\nkey *\nkey *\nkey a\n'))
        self.assertEqual(measure.birth_keys(True).split('key C-z')[1], measure.INPUT.split('key C-z')[1])

    def test_no_result_is_failure_even_on_zero_exit(self):
        self.assertEqual(measure.classify(0, []), 'harness_failure')

    def test_signal_overrides_terminal_survival(self):
        self.assertEqual(measure.classify(-signal.SIGSEGV, [{'kind': 'turn_cap'}]), 'crash')

    def test_nonzero_overrides_death(self):
        self.assertEqual(measure.classify(1, [{'kind': 'death'}]), 'harness_failure')

    def test_completed_outcomes(self):
        for kind in ('death', 'completion', 'turn_cap'):
            self.assertEqual(measure.classify(0, [{'kind': kind}]), kind)

    def test_timeout_does_not_become_survival(self):
        self.assertEqual(measure.classify(-15, [{'kind': 'turn_cap'}], 'wall_timeout'), 'wall_timeout')

    def test_preflight_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'attempt'
            code = subprocess.run([sys.executable, str(Path(__file__).with_name('measure-native.py')),
                                   'run', '--build', str(Path(tmp) / 'missing-build'),
                                   '--output', str(out), '--seed', '11', '--cap', '2000'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode
            self.assertEqual(code, 1)
            self.assertEqual(json.loads((out / 'result.json').read_text())['outcome'], 'harness_failure')

    def test_partial_record_keeps_watchdog_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / 'trace'
            trace.write_text('STATE progress turn=123 decisions=99\nSTATE progress tur')
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
            try:
                self.assertEqual(measure.monitor(child, trace, 2, 0.2), 'stalled')
                self.assertIsNotNone(child.poll())
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()

    def test_run_error_reaps_owned_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build = root / 'build'
            binary = build / 'build/game/angband'
            binary.parent.mkdir(parents=True)
            (build / 'source').mkdir()
            binary.write_text('#!' + sys.executable + '\nimport time\ntime.sleep(10)\n')
            binary.chmod(0o700)
            (build / 'build.json').write_text(json.dumps({'complete': True, 'instrumented': True,
                'binary_sha256': measure.sha(binary), 'data_sha256': {}}))
            options = SimpleNamespace(build=build, output=root / 'run', seed=11, cap=2000,
                                      timeout=2, stall_timeout=1, no_saves=False, load=None)
            created = []
            real_popen = subprocess.Popen
            def spawn(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                created.append(process)
                return process
            try:
                with mock.patch.object(measure.subprocess, 'Popen', side_effect=spawn), \
                     mock.patch.object(measure, 'monitor', side_effect=ValueError('injected bad trace')):
                    self.assertEqual(measure.run(options), 1)
                self.assertIsNotNone(created[-1].poll())
                result = json.loads((options.output / 'result.json').read_text())
                self.assertEqual(result['outcome'], 'harness_failure')
                self.assertEqual(result['error'], 'injected bad trace')
                self.assertEqual(result['calendar_context']['status'], 'recorded')
                self.assertIn('end', result['calendar_context'])
            finally:
                for process in created:
                    if process.poll() is None:
                        process.kill()
                        process.wait()

    def test_real_watchdog_keeps_missing_progress_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / 'trace'
            for expected in ('wall_timeout', 'stalled'):
                if expected == 'stalled':
                    trace.write_text('STATE progress turn=123 decisions=99\n')
                child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])
                self.assertEqual(measure.monitor(child, trace, 0.2 if expected == 'wall_timeout' else 2, 0.2), expected)
                self.assertIsNotNone(child.poll())


if __name__ == '__main__':
    unittest.main()
