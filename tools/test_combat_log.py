"""Native fighting events are frame-qualified and never inferred from Borg notes."""
import importlib.util
import json
import io
from unittest import mock
from contextlib import redirect_stderr
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
viewer=load('combat_viewer_tests',ROOT/'tools/borg-replay-viewer.py')
observer=load('combat_observer_tests',ROOT/'tools/replay-observation.py')


class CombatLog(unittest.TestCase):
    def test_damage_and_speed_do_not_appear_before_their_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'trace.txt').write_text('BORG 10 # Attacking monster\n')
            rows=[{'kind':'speed','frame':1,'turn':1,'speed':110,'gain':10,'move':100},
                  {'kind':'message','frame':2,'turn':11,'type':'MON_HIT','text':'The kobold hits you.'},
                  {'kind':'message','frame':2,'turn':11,'type':'GENERIC','text':'# HIT_BY note'},
                  {'kind':'damage','frame':3,'turn':11,'before':15,'after':7,'requested':8,'cause':'a kobold'},
                  {'kind':'speed','frame':4,'turn':12,'speed':120,'gain':20,'move':100}]
            (d/'combat.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            from types import SimpleNamespace
            frames=SimpleNamespace(messages=[],index=[0,0,0,0])
            log=viewer.ReplayLog(d,frames)
            def text(index):
                rows,_=log.window({'index':index+1,'turn':11},index,12,100,mode=3)
                return '\n'.join(x[0] for x in rows)
            self.assertNotIn('kobold',text(0))
            self.assertIn('MON_HIT',text(1));self.assertNotIn('15 -> 7',text(1))
            self.assertIn('15 -> 7 (-8)',text(2));self.assertIn('~10 ticks',text(2))
            self.assertNotIn('HIT_BY note',text(2));self.assertIn('~5 ticks',text(3))

    def test_missing_combat_channel_is_labeled_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            from types import SimpleNamespace
            d=Path(tmp);(d/'trace.txt').write_text('BORG 10 # HIT_BY:The kobold (3)\n')
            log=viewer.ReplayLog(d,SimpleNamespace(messages=[],index=[0]))
            rows,_=log.window({'index':1,'turn':10},0,10,100,mode=3)
            self.assertIn('--combat-log','\n'.join(r[0] for r in rows))
            self.assertEqual(log.combat,[])

    def test_wide_terminal_detection_uses_actual_recorded_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);p=d/'events.txt';p.write_text('1 1 0 4 0 0 0 0 0 0 0 0 424 104\n')
            self.assertTrue(observer.wide_geometry(d))
            p.write_text('1 1 0 4 0 0 0 0 0 0 0 0 80 24\n');self.assertFalse(observer.wide_geometry(d))


class ReplayModes(unittest.TestCase):
    def test_view_only_does_not_parse_input_geometry_or_build(self):
        replay=load('combat_cli_test',ROOT/'replay-borg.py')
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'frames.jsonl').write_text('{"inventory":{},"spells":{}}\n')
            observation=mock.Mock();observation.cached.return_value=None
            with mock.patch.object(replay.sys,'argv',['replay-borg.py',str(d),'--view-only']), \
                 mock.patch.object(replay,'resolve_recording',return_value=d), \
                 mock.patch.object(replay.recordings,'validate'), \
                 mock.patch.object(replay,'tool',return_value=observation), \
                 mock.patch.object(replay.viewer,'show') as show:
                self.assertEqual(replay.main(),0)
                observation.needs_wide_reader.assert_not_called()
                observation.prepare.assert_not_called();show.assert_called_once()


if __name__=='__main__':unittest.main()
