"""Historical replay prefix and isolated manual branch controls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('takeover_tests', ROOT / 'tools/borg-takeover.py')
takeover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(takeover)


class Takeover(unittest.TestCase):
    def fixture(self, root):
        original, output = root / 'original', root / 'prefix'
        original.mkdir(); output.mkdir()
        for name in ('events.txt', 'actions.txt', 'clock.txt', 'file-inputs.txt', 'trace.txt'):
            (original / name).write_text('first\nsecond\n')
            (output / name).write_text('first\n')
        data = b'native save for selected command'
        (output / 'world-fingerprint.save').write_bytes(data)
        value = 14695981039346656037
        for byte in data:
            value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
        frames = [{'index': 1, 'turn': 100, 'phase': 'tick', 'dead': 0},
                  {'index': 2, 'turn': 103, 'phase': 'command', 'dead': 0, 'input': 1, 'world': f'{value:016x}'},
                  {'index': 3, 'turn': 103, 'phase': 'command', 'dead': 0},
                  {'index': 4, 'turn': 110, 'phase': 'death', 'dead': 1}]
        lines = [json.dumps(f)+'\n' for f in frames]
        (original / 'frames.jsonl').write_text(''.join(lines))
        (output / 'frames.jsonl').write_text(''.join(lines[:2]))
        (output / 'record-complete.json').write_text('{"frames":2,"inputs":1}')
        return original, output, frames[1]

    def test_turn_selects_first_living_command_boundary_not_tick_or_later_same_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            original, _, expected = self.fixture(Path(temp))
            self.assertEqual(takeover.boundary(original, 103), expected)
            with self.assertRaises(ValueError):
                takeover.boundary(original, 102)
            with self.assertRaises(ValueError):
                takeover.boundary(original, 111)

    def test_prefix_and_exact_native_snapshot_qualify(self):
        with tempfile.TemporaryDirectory() as temp:
            original, output, expected = self.fixture(Path(temp))
            difference, counts = takeover.prefix_difference(original, output, expected)
            self.assertIsNone(difference)
            self.assertEqual(counts['events.txt'], 1)

    def test_different_or_empty_prefix_cannot_qualify(self):
        for stream in ('events.txt', 'actions.txt', 'clock.txt', 'file-inputs.txt', 'trace.txt', 'frames.jsonl'):
            with self.subTest(stream=stream), tempfile.TemporaryDirectory() as temp:
                original, output, expected = self.fixture(Path(temp))
                (output / stream).write_text('{}\n' if stream == 'frames.jsonl' else 'wrong\n')
                difference, _ = takeover.prefix_difference(original, output, expected)
                self.assertIsNotNone(difference)
        with tempfile.TemporaryDirectory() as temp:
            original, output, expected = self.fixture(Path(temp))
            (output / 'frames.jsonl').write_text('')
            self.assertIsNotNone(takeover.prefix_difference(original, output, expected)[0])

    def test_wrong_snapshot_or_footer_cannot_qualify(self):
        for name, content in [('world-fingerprint.save', 'wrong'),
                              ('record-complete.json', '{"frames":2,"inputs":0}')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                original, output, expected = self.fixture(Path(temp))
                (output / name).write_text(content)
                self.assertIsNotNone(takeover.prefix_difference(original, output, expected)[0])

    def test_external_takeover_and_replay_settings_do_not_leak(self):
        with mock.patch.dict(takeover.os.environ, {'BORG_TAKEOVER_TURN':'100',
                'BORG_REPLAY_DIR':'old', 'BORG_MEASURE_PLAY_TURNS':'10', 'DISPLAY':':88'}):
            env = takeover.clean_environment()
            self.assertEqual(env['DISPLAY'], ':88')
            self.assertFalse(any(k.startswith(('BORG_TAKEOVER_', 'BORG_REPLAY_', 'BORG_MEASURE_')) for k in env))

    def test_declining_build_never_starts_capture_or_changes_original(self):
        with tempfile.TemporaryDirectory() as temp:
            original, _, frame = self.fixture(Path(temp))
            record = {'build': {'source_commit':'a'*40, 'binary_sha256':'b'*64}}
            with mock.patch.object(takeover.replay, 'resolve_recording', return_value=original), \
                 mock.patch.object(takeover.records, 'validate', return_value=record), \
                 mock.patch.object(takeover, 'boundary', return_value=frame), \
                 mock.patch.object(takeover, 'cache', return_value=Path(temp)/'build'), \
                 mock.patch.object(takeover, 'existing_build', return_value=None), \
                 mock.patch.object(takeover, 'capture') as capture, \
                 mock.patch.object(takeover, 'build') as build, \
                 mock.patch.object(takeover.sys.stdin, 'isatty', return_value=False), \
                 mock.patch.object(takeover.sys, 'argv', ['play-from-replay.py', str(original), '--from-turn', '103']):
                self.assertEqual(takeover.main(), 1)
                capture.assert_not_called(); build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
