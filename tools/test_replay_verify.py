"""Controls for surfacing the replay engine's own divergence receipt."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('replay_verify', Path(__file__).resolve().parents[1] / 'replay-borg.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class EngineDivergence(unittest.TestCase):
    def test_engines_without_a_receipt_surface_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(replay.engine_divergence(Path(tmp)))

    def test_divergence_receipt_is_surfaced_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / 'replay-divergence.json'
            record = {'stream': 'actions', 'turn': 27516, 'decisions': 81204,
                      'expected': '27516 81204 2 115 0', 'actual': '27516 81204 0 0 0'}
            receipt.write_text(json.dumps(record) + '\n')
            self.assertEqual(replay.engine_divergence(Path(tmp)), record)

    def test_unreadable_receipt_is_recorded_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'replay-divergence.json').write_text('{broken')
            self.assertEqual(replay.engine_divergence(Path(tmp)),
                             {'stream': 'unreadable replay-divergence.json'})


if __name__ == '__main__':
    unittest.main()
