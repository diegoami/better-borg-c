"""Recording integrity, replay divergence and random-access viewer controls."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


records = load('recording_tests', ROOT / 'tools/borg-recordings.py')
replay = load('replay_tests', ROOT / 'replay-borg.py')
viewer = replay.viewer


def frame(index, turn, full, cells, **fields):
    return {'index': index, 'turn': turn, 'phase': 'command', 'full': full,
            'width': 2, 'height': 1, 'cells': cells, 'palette': [[0, 0, 0], [255, 255, 255]] if full else None,
            'hp': 20, 'sp': 0, 'level': 1, 'depth': 0, **fields}


def streams(folder, frames):
    folder.mkdir(parents=True, exist_ok=True)
    for name in ('events.txt', 'actions.txt', 'clock.txt', 'file-inputs.txt'):
        (folder / name).write_text('1\n')
    (folder / 'frames.jsonl').write_text(''.join(json.dumps(f) + '\n' for f in frames))


class FrameInspection(unittest.TestCase):
    def test_seek_reconstructs_deltas_and_diagnostic_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            detail = {'gear': [{'quantity': 1}], 'monsters': []}
            streams(root, [frame(1, 1, 1, [[0, 64, 1], [1, 46, 1]], details=detail),
                           frame(2, 2, 0, [[0, 46, 1], [1, 64, 1]], details=None),
                           frame(3, 3, 1, [[0, 35, 1], [1, 64, 1]], details=detail)])
            frames = viewer.Frames(root)
            try:
                self.assertEqual(frames.at_turn(2), 1)
                self.assertEqual(frames.get(1)[1], [46, 64])
                self.assertEqual(frames.get(1)[0]['diagnostics'], detail)
                self.assertEqual(frames.get(2)[1], [35, 64])
                self.assertEqual(frames.at_turn(0), 0)
                self.assertEqual(frames.at_turn(999), 2)
            finally:
                frames.close()

    def test_missing_first_full_frame_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            streams(root, [frame(1, 1, 0, [[0, 64, 1]])])
            with self.assertRaisesRegex(ValueError, 'without a full'):
                viewer.Frames(root)

    def test_truncated_last_frame_is_not_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            streams(root, [frame(1, 1, 1, [[0, 64, 1], [1, 46, 1]])])
            with (root / 'frames.jsonl').open('a') as out:
                out.write('{"turn":')
            frames = viewer.Frames(root)
            try:
                self.assertEqual(len(frames.index), 1)
            finally:
                frames.close()


class ReplayIntegrity(unittest.TestCase):
    def fixture(self, root):
        streams(root, [frame(1, 1, 1, [[0, 64, 1], [1, 46, 1]])])
        (root / 'engine').write_bytes(b'fixture engine')
        (root / 'origin.save').write_bytes(b'original character')
        (root / 'record-complete.json').write_text(json.dumps({'inputs': 1, 'frames': 1}))
        (root / 'recording.json').write_text(json.dumps({'schema': records.SCHEMA,
            'status': 'recording', 'immutable_sha256': {'origin.save': records.sha(root / 'origin.save')}}))
        return root

    def test_finalize_compresses_losslessly_and_detects_changed_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(Path(tmp))
            original = (root / 'frames.jsonl').read_bytes()
            records.finalize(root, {'outcome': 'turn_cap'})
            self.assertFalse((root / 'frames.jsonl').exists())
            with gzip.open(root / 'frames.jsonl.gz', 'rb') as source:
                self.assertEqual(source.read(), original)
            self.assertEqual(records.validate(root)['status'], 'complete')
            (root / 'origin.save').write_bytes(b'changed input')
            with self.assertRaisesRegex(ValueError, 'file changed'):
                records.validate(root)

    def test_changed_engine_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(Path(tmp))
            records.finalize(root, {'outcome': 'saved'})
            (root / 'engine').write_bytes(b'wrong engine')
            with self.assertRaisesRegex(ValueError, 'engine'):
                records.validate(root)

    def test_incomplete_recording_is_viewable_but_not_verifiable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(Path(tmp))
            (root / 'record-complete.json').unlink()
            records.finalize(root, {'outcome': 'wall_timeout'})
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                records.validate(root)
            self.assertEqual(records.validate(root, require_complete=False)['status'], 'incomplete')

    def test_frozen_input_mutation_is_detected_before_compression(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.fixture(Path(tmp))
            (root / 'origin.save').write_bytes(b'mutated')
            with self.assertRaisesRegex(ValueError, 'Frozen recording input'):
                records.finalize(root, {'outcome': 'saved'})
            self.assertTrue((root / 'frames.jsonl').exists())

    def test_state_and_action_divergence_have_first_mismatch_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            left, right = Path(tmp) / 'original', Path(tmp) / 'rerun'
            streams(left, [frame(1, 1, 1, [[0, 64, 1]])])
            streams(right, [frame(1, 1, 1, [[0, 64, 1]], hp=19)])
            mismatch = replay.first_difference(left, right)
            self.assertEqual(mismatch['stream'], 'frames')
            self.assertEqual(mismatch['fields'], ['hp'])
            (right / 'actions.txt').write_text('different action\n')
            self.assertEqual(replay.first_difference(left, right)['stream'], 'actions.txt')

    def test_legacy_seed_only_record_does_not_get_a_verified_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'predates full recording'):
                records.validate(Path(tmp))

    def test_parent_link_uses_snapshot_hash_instead_of_character_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / 'artifacts/headless/runs/parent'
            parent.mkdir(parents=True)
            (parent / 'recording.json').write_text(json.dumps({'status': 'complete',
                'files_sha256': {'recent.save': 'verified-snapshot'}}))
            with mock.patch.object(records, '__file__', str(root / 'tools/borg-recordings.py')):
                self.assertIsNone(records.parent_recording('wrong-snapshot'))
                link = records.parent_recording('verified-snapshot')
                self.assertEqual(link['snapshot'], 'recent.save')
                self.assertEqual(link['recording'], str(parent))

    def test_recording_cache_cannot_be_refreshed_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'build.json').write_text(json.dumps({'recording_schema': records.SCHEMA}))
            before = (root / 'build.json').read_bytes()
            with self.assertRaisesRegex(ValueError, 'immutable'):
                replay.measurement.refresh_observer(SimpleNamespace(output=root))
            self.assertEqual((root / 'build.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
