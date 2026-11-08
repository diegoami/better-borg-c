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

    def test_latest_selects_first_command_at_last_living_command_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            original, _, expected = self.fixture(Path(temp))
            self.assertEqual(takeover.boundary(original, 'latest'), expected)
            self.assertEqual(takeover.parse_turn('latest'), 'latest')
            self.assertEqual(takeover.parse_turn('103'), 103)
            for value in ('0', '-1', 'bad'):
                with self.assertRaises(takeover.argparse.ArgumentTypeError):
                    takeover.parse_turn(value)

    def timeout_manifest(self, original, status='incomplete', outcome='wall_timeout', error=None):
        (original / 'engine').write_text('frozen engine')
        (original / 'geometry.json').write_text('{}')
        files = {p.name:takeover.records.sha(p) for p in original.iterdir()
                 if p.is_file() and p.name not in ('recording.json', 'result.json')}
        value = {'schema':takeover.records.SCHEMA, 'status':status,
                 'outcome':outcome, 'files_sha256':files}
        (original / 'recording.json').write_text(json.dumps(value))
        (original / 'result.json').write_text(json.dumps({'outcome':outcome,'error':error}))
        return value

    def test_finalized_timeout_accepts_prefix_without_relabeling_original(self):
        with tempfile.TemporaryDirectory() as temp:
            original, _, _ = self.fixture(Path(temp))
            self.timeout_manifest(original)
            initial = (original / 'recording.json').read_bytes()
            record = takeover.validate_recording(original)
            self.assertEqual(record['status'], 'incomplete')
            self.assertEqual((original / 'recording.json').read_bytes(), initial)
            # Full ordinary replay remains strict.
            with self.assertRaises(ValueError):
                takeover.records.validate(original)

    def test_partial_takeover_refuses_active_crashed_errored_or_changed_recordings(self):
        for status, outcome, error in [('recording','wall_timeout',None),
                                      ('incomplete','crash',None),
                                      ('incomplete','wall_timeout','reader failed')]:
            with self.subTest(status=status,outcome=outcome,error=error), tempfile.TemporaryDirectory() as temp:
                original, _, _ = self.fixture(Path(temp))
                self.timeout_manifest(original,status,outcome,error)
                with self.assertRaises(ValueError):
                    takeover.validate_recording(original)
        with tempfile.TemporaryDirectory() as temp:
            original, _, _ = self.fixture(Path(temp))
            self.timeout_manifest(original)
            (original / 'events.txt').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'Recording file changed'):
                takeover.validate_recording(original)

    def test_timeout_needs_complete_input_manifest_and_consistent_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            original, _, _ = self.fixture(Path(temp))
            record = self.timeout_manifest(original)
            del record['files_sha256']['engine']
            (original / 'recording.json').write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'missing finalized replay inputs'):
                takeover.validate_recording(original)
            self.timeout_manifest(original)
            (original / 'result.json').write_text('{"outcome":"crash"}')
            with self.assertRaisesRegex(ValueError,'conflicting outcome'):
                takeover.validate_recording(original)

    def test_external_takeover_and_replay_settings_do_not_leak(self):
        with mock.patch.dict(takeover.os.environ, {'BORG_TAKEOVER_TURN':'100',
                'BORG_REPLAY_DIR':'old', 'BORG_MEASURE_PLAY_TURNS':'10', 'DISPLAY':':88'}):
            env = takeover.clean_environment()
            self.assertEqual(env['DISPLAY'], ':88')
            self.assertFalse(any(k.startswith(('BORG_TAKEOVER_', 'BORG_REPLAY_', 'BORG_MEASURE_')) for k in env))

    def test_declining_build_never_starts_capture_or_changes_original(self):
        with tempfile.TemporaryDirectory() as temp:
            original, _, frame = self.fixture(Path(temp))
            record = {'status':'complete', 'build': {'source_commit':'a'*40, 'binary_sha256':'b'*64}}
            with mock.patch.object(takeover.replay, 'resolve_recording', return_value=original), \
                 mock.patch.object(takeover.records, 'validate', return_value=record), \
                 mock.patch.object(takeover, 'boundary', return_value=frame), \
                 mock.patch.object(takeover, 'cache', return_value=Path(temp)/'build'), \
                 mock.patch.object(takeover, 'existing_build', return_value=None), \
                 mock.patch.object(takeover, 'select_x11_font', return_value='fixed'), \
                 mock.patch.object(takeover, 'capture') as capture, \
                 mock.patch.object(takeover, 'build') as build, \
                 mock.patch.object(takeover.sys.stdin, 'isatty', return_value=False), \
                 mock.patch.object(takeover.sys, 'argv', ['play-from-replay.py', str(original), '--from-turn', '103']):
                self.assertEqual(takeover.main(), 1)
                capture.assert_not_called(); build.assert_not_called()


class TakeoverFonts(unittest.TestCase):
    def library(self, accepted):
        lib=mock.Mock()
        lib.XOpenDisplay.return_value=11
        lib.XLoadQueryFont.side_effect=lambda display,name: 22 if name.decode() in accepted else None
        return lib

    def test_readable_misc_fixed_is_tried_before_smaller_aliases(self):
        fallback=takeover.FONT_CANDIDATES[2]
        lib=self.library({fallback})
        with mock.patch.object(takeover,'x11_library',return_value=lib):
            self.assertEqual(takeover.select_x11_font({'DISPLAY':':91'}),fallback)
        self.assertEqual(lib.XLoadQueryFont.call_count,3)
        lib.XFreeFont.assert_called_once_with(11,22)
        lib.XCloseDisplay.assert_called_once_with(11)

    def test_minimal_server_with_only_fixed_still_loads(self):
        lib=self.library({'fixed'});lib.XGetFontPath.return_value=None
        with mock.patch.object(takeover,'x11_library',return_value=lib):
            self.assertEqual(takeover.select_x11_font({'DISPLAY':':91'}),'fixed')
        lib.XCloseDisplay.assert_called_once_with(11)

    def test_explicit_font_is_honored_and_not_silently_replaced(self):
        lib=self.library({'custom'});lib.XGetFontPath.return_value=None
        with mock.patch.object(takeover,'x11_library',return_value=lib):
            self.assertEqual(takeover.select_x11_font({'DISPLAY':':91','BORG_PLAY_FONT':'custom',
                'ANGBAND_X11_FONT_0':'other'}),'custom')
            with self.assertRaisesRegex(ValueError,'unavailable'):
                takeover.select_x11_font({'DISPLAY':':91','BORG_PLAY_FONT':'missing'})
        lib.XCloseDisplay.assert_has_calls([mock.call(11),mock.call(11)])

    def test_missing_display_or_unreachable_server_fails_early(self):
        with self.assertRaisesRegex(ValueError,'DISPLAY required'):
            takeover.select_x11_font({})
        lib=self.library(set());lib.XOpenDisplay.return_value=None
        with mock.patch.object(takeover,'x11_library',return_value=lib), \
             self.assertRaisesRegex(ValueError,'Cannot open'):
            takeover.select_x11_font({'DISPLAY':':91'})
        lib.XLoadQueryFont.assert_not_called()

    def test_installed_readable_font_is_registered_before_small_fallback(self):
        lib=self.library(set());readable=takeover.FONT_CANDIDATES[1]
        with mock.patch.object(takeover,'x11_library',return_value=lib), \
             mock.patch.object(takeover,'registered_font',return_value=readable) as register:
            self.assertEqual(takeover.select_x11_font({'DISPLAY':':91'}),readable)
            register.assert_called_once()
        self.assertNotIn(mock.call(11,b'fixed'),lib.XLoadQueryFont.call_args_list)

    def test_failed_registration_restores_every_original_font_path(self):
        lib=self.library(set())
        paths=(takeover.ctypes.c_char_p*1)(b'built-ins')
        def get(display,count):
            takeover.ctypes.cast(count,takeover.ctypes.POINTER(takeover.ctypes.c_int))[0]=1
            return paths
        lib.XGetFontPath.side_effect=get
        changes=[]
        lib.XSetFontPath.side_effect=lambda display,values,n: changes.append([values[i] for i in range(n)])
        self.assertIsNone(takeover.registered_font(lib,11,('missing',)))
        self.assertEqual(changes[-1],[b'built-ins'])
        self.assertEqual(changes[1],[b'built-ins'])
        lib.XSetErrorHandler.assert_called()

    def test_bad_font_prevents_build_or_reconstruction(self):
        record={'status':'complete','build':{'source_commit':'a'*40,'binary_sha256':'b'*64}}
        with mock.patch.object(takeover.sys,'argv',['play-from-replay.py','original','--from-turn','latest']), \
             mock.patch.object(takeover.replay,'resolve_recording',return_value=Path('/tmp/original')), \
             mock.patch.object(takeover,'validate_recording',return_value=record), \
             mock.patch.object(takeover,'cache',return_value=Path('/tmp/helper')), \
             mock.patch.object(takeover,'select_x11_font',side_effect=ValueError('font unavailable')), \
             mock.patch.object(takeover,'build') as build, \
             mock.patch.object(takeover,'capture') as capture, \
             mock.patch.object(takeover,'boundary') as boundary:
            self.assertEqual(takeover.main(),1)
            build.assert_not_called();capture.assert_not_called();boundary.assert_not_called()


if __name__ == '__main__':
    unittest.main()
