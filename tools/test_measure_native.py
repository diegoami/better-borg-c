"""Fail-closed result and watchdog controls; no native game required."""
import importlib.util
from pathlib import Path
import json
import signal
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('measure', Path(__file__).with_name('measure-native.py'))
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


class Results(unittest.TestCase):
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
