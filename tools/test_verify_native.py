"""Controls for the native runner's zero-exit/partial-summary failure modes."""
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location("native", Path(__file__).with_name("verify-native.py"))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NumericalGateTests(unittest.TestCase):
    def test_complete_colored_output(self):
        result = native.check_summaries("Total: \x1b[32m965/965\x1b[0m passed (100%)\nTotal: 5/5 passed (100%)")
        self.assertEqual(result["unit"]["total"], 965)

    def test_zero_exit_assertion_failure_is_red(self):
        with self.assertRaises(ValueError):
            native.check_summaries("Total: 964/965 passed\nTotal: 5/5 passed")

    def test_frontend_failure_is_red(self):
        with self.assertRaises(ValueError):
            native.check_summaries("Total: 965/965 passed\nTotal: 4/5 passed")

    def test_missing_or_empty_gate_is_red(self):
        for output in ("", "Total: 965/965 passed", "Total: 0/0 passed\nTotal: 5/5 passed",
                       "Total: 965/965 passed\nTotal: 0/0 passed"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                native.check_summaries(output)

    def test_new_tests_can_increase_count(self):
        native.check_summaries("Total: 966/966 passed\nTotal: 6/6 passed")


if __name__ == "__main__":
    unittest.main()
