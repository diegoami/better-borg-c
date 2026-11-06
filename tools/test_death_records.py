"""Version fidelity, immutable attempts and non-inflated death aggregation."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


record = module('record', 'record-death.py')
index = module('index', 'aggregate-deaths.py')


class Records(unittest.TestCase):
    def fixture(self, root, name, source='old', outcome='death'):
        path = root / name
        (path / 'archive').mkdir(parents=True)
        (path / 'archive/Measure.map').write_text('native map\n[Last Messages]\nmessage\n')
        (path / 'start.save').write_bytes(b'same initial state')
        (path / 'recent.save').write_bytes(b'living checkpoint')
        (path / 'trace.txt').write_text('CHARACTER Test Human Warrior\nOPTIONS cheat_live=0\nBORG 90 attack\nSTATE death turn=100 dead=1\nCAUSE monster\n')
        data = {'outcome': outcome, 'cause': 'monster', 'states': [{'kind': 'death', 'dead': 1, 'turn': 100}],
                'seed': 11, 'configuration_sha256': 'config', 'input_sha256': 'input',
                'build': {'source_commit': source, 'binary_sha256': 'binary-' + source},
                'harness_commit': 'harness', 'runner_sha256': 'runner', 'wall_seconds': 1,
                'character': 'Human Warrior', 'command': ['native', str(path)], 'environment': {}, 'cwd': '/fixture',
                'turn_cap': 400000, 'wall_limit_seconds': 180, 'stall_limit_seconds': 30}
        (path / 'result.json').write_text(json.dumps(data))
        return path

    def args(self, run, out, **kwargs):
        return SimpleNamespace(run=run, output=out, id='D1', repeat=kwargs.get('repeat', []),
                               reference=kwargs.get('reference', []), window=[], issue='pilot', investigation='question')

    def ledger(self, source):
        return {'baseline': 'base-' + source, 'patches': [{'source': source}]}

    def test_caps_are_not_exported_as_deaths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                record.capture(self.args(self.fixture(root, 'cap', outcome='turn_cap'), root / 'dossier'))

    def test_actual_old_build_is_pinned_and_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(record, 'source_ledger', side_effect=self.ledger):
            root = Path(tmp)
            old = self.fixture(root, 'old')
            out = root / 'dossier'
            result = record.capture(self.args(old, out))
            self.assertEqual(result['identity']['source'], 'old')
            self.assertEqual(result['carried_patches'], [{'source': 'old'}])
            before = (out / 'record.json').read_bytes()
            with self.assertRaises(ValueError):
                record.capture(self.args(self.fixture(root, 'new', source='new'), out))
            self.assertEqual(before, (out / 'record.json').read_bytes())

    def test_repeat_must_match_and_existing_attempt_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(record, 'source_ledger', side_effect=self.ledger):
            root = Path(tmp)
            original = self.fixture(root, 'original')
            repeat = self.fixture(root, 'repeat')
            out = root / 'dossier'
            record.capture(self.args(original, out, repeat=[repeat]))
            with self.assertRaises(ValueError):
                record.capture(self.args(original, out))
            (repeat / 'trace.txt').write_text('different trajectory\n')
            with self.assertRaises(ValueError):
                record.capture(self.args(original, root / 'other', repeat=[repeat]))

    def test_changed_input_is_rejected_before_creating_dossier(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(record, 'source_ledger', side_effect=self.ledger):
            root = Path(tmp)
            run = self.fixture(root, 'run')
            (run / 'input.txt').write_text('unrecorded input')
            out = root / 'dossier'
            with self.assertRaises(ValueError):
                record.capture(self.args(run, out))
            self.assertFalse(out.exists())

    def test_window_from_another_build_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(record, 'source_ledger', side_effect=self.ledger):
            root = Path(tmp)
            run = self.fixture(root, 'run')
            window = self.fixture(root, 'window', source='different', outcome='turn_cap')
            options = self.args(run, root / 'dossier')
            options.window = [window]
            with self.assertRaises(ValueError):
                record.capture(options)

    def test_recorded_calendar_is_preserved_and_legacy_is_not_backfilled(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(record, 'source_ledger', side_effect=self.ledger):
            root = Path(tmp)
            run = self.fixture(root, 'recorded')
            data = json.loads((run / 'result.json').read_text())
            context = {'status': 'recorded', 'start': {'local': '2026-12-25T10:00:00+01:00'}}
            data['calendar_context'] = context
            (run / 'result.json').write_text(json.dumps(data))
            result = record.capture(self.args(run, root / 'new'))
            self.assertEqual(result['calendar_context'], context)
            self.assertEqual(result['attempts'][0]['calendar_context'], context)
            legacy = self.fixture(root, 'legacy')
            old = record.capture(self.args(legacy, root / 'old'))
            self.assertEqual(old['calendar_context']['status'], 'not captured by legacy runner')
            self.assertNotIn('start', old['calendar_context'])

    def test_references_repeats_and_duplicate_dossiers_do_not_inflate_starts(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(record, 'source_ledger', side_effect=self.ledger):
            root = Path(tmp)
            original = self.fixture(root, 'original')
            repeat = self.fixture(root, 'repeat')
            reference = self.fixture(root, 'reference', source='pristine')
            folder = root / 'records'
            for name in ('a', 'b'):
                out = folder / name
                record.capture(self.args(original, out, repeat=[repeat], reference=[reference]))
                (out / 'assessment.json').write_text(json.dumps({'classification': 'unproved', 'actions': [
                    {'issue': 'issue22', 'key': 'stock', 'summary': 'Investigate stock', 'status': 'open'}]}))
            summary, text = index.aggregate(folder)
            self.assertEqual(summary['cases'], 2)
            self.assertEqual(summary['distinct_starting_conditions'], 1)
            self.assertEqual(summary['death_process_attempts'], 3)
            self.assertEqual(len(summary['actions']), 1)
            self.assertEqual(summary['actions'][0]['issue'], 'issue22')
            self.assertIn('(issue22)', text)
            self.assertEqual(len(summary['versions']), 2)


if __name__ == '__main__':
    unittest.main()
