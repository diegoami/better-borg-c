"""Save preservation and explicit replay controls; no native game required."""
import importlib.util
from pathlib import Path
import tempfile
import json
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


saves = load('borg_saves_test', ROOT / 'tools/borg-saves.py')
runner = load('named_headless_test', ROOT / 'run-borg-headless.py')


class SaveSafety(unittest.TestCase):
    def test_living_checkpoint_backup_leaves_dead_save_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            save, checkpoint = Path(tmp) / 'Hero', Path(tmp) / 'recent.save'
            save.write_bytes(b'dead final character')
            checkpoint.write_bytes(b'living checkpoint')
            saves.backup(save, checkpoint)
            self.assertEqual(save.read_bytes(), b'dead final character')
            self.assertEqual((save.parent / 'backups/Hero/save.1').read_bytes(), b'living checkpoint')
            saves.restore(save)
            self.assertEqual(save.read_bytes(), b'living checkpoint')
            self.assertEqual(next((save.parent / 'backups/Hero').glob('before-restore-*.save')).read_bytes(), b'dead final character')

    def test_rolling_backup_and_restore_preserve_current_character(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / 'A Name'
            for version in range(1, 8):
                save.write_text(str(version))
                saves.backup(save)
                self.assertEqual(save.read_text(), str(version))
            folder = save.parent / 'backups' / save.name
            self.assertEqual([p.read_text() for p in [folder / f'save.{i}' for i in range(1, 6)]],
                             ['7', '6', '5', '4', '3'])
            saves.restore(save, 3)
            self.assertEqual(save.read_text(), '5')
            self.assertEqual(next(folder.glob('before-restore-*.save')).read_text(), '7')

    def test_missing_backup_does_not_touch_live_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            save = Path(tmp) / 'Hero'
            save.write_bytes(b'live')
            with self.assertRaisesRegex(ValueError, 'does not exist'):
                saves.restore(save)
            self.assertEqual(save.read_bytes(), b'live')

    def test_outside_writer_prevents_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            save, final = Path(tmp) / 'Hero', Path(tmp) / 'final'
            save.write_bytes(b'old')
            original = saves.digest(save)
            final.write_bytes(b'headless')
            save.write_bytes(b'manual session')
            with self.assertRaisesRegex(ValueError, 'changed during'):
                saves.publish(save, final, original)
            self.assertEqual(save.read_bytes(), b'manual session')
            self.assertEqual(final.read_bytes(), b'headless')

    def test_failed_atomic_replace_preserves_save_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            save, final = Path(tmp) / 'Hero', Path(tmp) / 'final'
            save.write_bytes(b'old')
            final.write_bytes(b'new')
            with mock.patch.object(saves.os, 'replace', side_effect=OSError('injected full disk')):
                with self.assertRaises(OSError):
                    saves.publish(save, final, saves.digest(save))
            self.assertEqual(save.read_bytes(), b'old')
            self.assertEqual(final.read_bytes(), b'new')
            self.assertFalse(list(Path(tmp).glob('.borg-save-*')))

    def test_rename_publishes_exact_final_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            save, final = Path(tmp) / 'Hero', Path(tmp) / 'final'
            final.write_bytes(b'new')
            saves.publish(save, final, None)
            self.assertEqual(save.read_bytes(), final.read_bytes())

    def test_save_locks_exclude_same_name_but_allow_other_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'Hero.lock', Path(tmp) / 'Other.lock'
            with runner.locked(first, blocking=False):
                with self.assertRaises(BlockingIOError):
                    with runner.locked(first, blocking=False):
                        self.fail('same save lock acquired twice')
                with runner.locked(second, blocking=False):
                    pass


class NamedRunSafety(unittest.TestCase):
    def run_fixture(self, root, outcome, code):
        save = root / 'build/native/game/lib/save/Hero'
        save.parent.mkdir(parents=True)
        save.write_bytes(b'original character')
        options = SimpleNamespace(character='Hero', turns=100, seed=1, timeout=1,
                                  stall_timeout=1, from_backup=None, death_issue='fixture discussion')
        outputs = []
        def native(options):
            out = options.output
            out.mkdir()
            outputs.append(out)
            (out / 'start.save').write_bytes(b'birth')
            (out / 'recent.save').write_bytes(b'living checkpoint')
            (out / 'final.save').write_bytes(b'final native save')
            (out / 'result.json').write_text(json.dumps({'outcome': outcome, 'states': [
                {'kind': 'checkpoint', 'turn': 50, 'dead': 0},
                {'kind': outcome, 'turn': 100, 'dead': int(outcome == 'death')}]}))
            return code
        original_locked = runner.locked
        def isolated_lock(path, blocking=True):
            return original_locked(root / 'validation.lock' if path.name == 'angband-validation.lock' else path, blocking)
        with mock.patch.object(runner, 'ROOT', root), \
             mock.patch.object(runner, 'prepared_build', return_value=root / 'unused-build'), \
             mock.patch.object(runner, 'locked', side_effect=isolated_lock), \
             mock.patch.object(runner.measurement, 'run', side_effect=native), \
             mock.patch.object(runner, 'record_natural_death') as record:
            if code:
                with self.assertRaisesRegex(ValueError, 'original save preserved'):
                    runner.run(options)
            else:
                self.assertEqual(runner.run(options), 0)
            return save, outputs[0], record.call_args_list

    def test_death_publishes_native_save_keeps_living_backup_and_exports_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            save, out, calls = self.run_fixture(Path(tmp), 'death', 0)
            self.assertEqual(save.read_bytes(), b'final native save')
            self.assertEqual((save.parent / 'backups/Hero/save.1').read_bytes(), b'living checkpoint')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].args, (out, 'fixture discussion'))
            result = json.loads((out / 'result.json').read_text())
            self.assertEqual(result['recovery_backup']['turn'], 50)
            self.assertEqual(result['publication'], 'published')

    def test_timeout_never_publishes_even_if_a_final_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            save, out, calls = self.run_fixture(Path(tmp), 'wall_timeout', 1)
            self.assertEqual(save.read_bytes(), b'original character')
            self.assertFalse(calls)
            self.assertEqual(json.loads((out / 'result.json').read_text())['publication'], 'not published')

    def test_cap_publishes_without_exporting_a_death(self):
        with tempfile.TemporaryDirectory() as tmp:
            save, _, calls = self.run_fixture(Path(tmp), 'turn_cap', 0)
            self.assertEqual(save.read_bytes(), b'final native save')
            self.assertFalse(calls)


if __name__ == '__main__':
    unittest.main()
