"""Character progress uses native saved counters, never duplicated Borg notes."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('run_report_tests',ROOT/'tools/run-report.py')
report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)


def block(name,data,version=1):
    return struct.pack('<16sIII',name.encode(),version,len(data),sum(data)&0xffffffff)+data+b'x'*(-len(data)%4)


def save_bytes(version=1):
    strings=b'Measure\0(alive and well)\0history\0Human\0normal\0Warrior\0'
    p=strings+bytes(9)+b'\x06'+bytes(48+10)+b'Humanoid\0'+struct.pack('<H',0)+bytes(4)
    p+=struct.pack('<IIIHhhhHhhHhh',47,120,110,0,3,30,25,0,10,8,0,3,2)
    p+=bytes(16)+b'\0'+struct.pack('<II',10000,400)
    lore=b'\x01orc\0'+struct.pack('<HH',3,0)+b'bat\0'+struct.pack('<HH',2,0)+b'No more monsters\0'
    misc=struct.pack('<IIHHBi',0,0,0,0,0,1000)
    return b'SaveVNLA'+block('player',p,version)+block('misc',misc)+block('monster memory',lore)


class RunReports(unittest.TestCase):
    def fixture(self,root):
        p=root/'world-fingerprint.save';p.write_bytes(save_bytes())
        r={'character':'Measure Human Warrior','outcome':'wall_timeout','seed':4,
           'build':{'source_commit':'pin'},'wall_seconds':120,'states':[{
               'turn':1000,'level':3,'max_level':3,'max_depth':2,'decisions':99}]}
        (root/'recording.json').write_text(json.dumps({'files_sha256':{p.name:report.sha(p)}}))
        return p,r

    def test_native_player_and_lifetime_kill_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            p,_=self.fixture(Path(temp));r=report.saved_character(p)
            self.assertEqual((r['level'],r['max_depth'],r['gold'],r['experience']),(3,2,47,110))
            self.assertEqual(r['recorded_kills'],5)
            self.assertEqual(r['kills_by_race'],{'orc':3,'bat':2})
            self.assertEqual((r['turn'],r['energy']),(1000,10000))

    def test_checksums_truncation_and_unknown_versions_are_rejected(self):
        for data in (save_bytes()[:-1],save_bytes(version=2),b'bad format'):
            with self.subTest(size=len(data)),tempfile.TemporaryDirectory() as temp:
                p=Path(temp)/'save';p.write_bytes(data)
                with self.assertRaises(ValueError):report.saved_character(p)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'save';data=bytearray(save_bytes());data[40]^=1;p.write_bytes(data)
            with self.assertRaises(ValueError):report.saved_character(p)

    def test_summary_is_progress_only_and_keeps_original_files_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,r=self.fixture(root);before=(root/'recording.json').read_bytes()
            path,data=report.create(root,r,format_character=False)
            text=path.read_text();self.assertIn('| Recorded monster kills | 5 |',text)
            self.assertIn('Alive at wall-time limit',text)
            self.assertNotIn('Character Inventory',text);self.assertNotIn('map',text)
            self.assertEqual((root/'recording.json').read_bytes(),before)
            self.assertEqual(p.read_bytes(),save_bytes())

    def test_stale_checkpoint_is_labeled_and_bad_snapshot_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,r=self.fixture(root);r['states'][-1]['turn']=1200
            path,_=report.create(root,r,format_character=False)
            self.assertIn('predates the final outcome',path.read_text())
            p.write_bytes(b'changed')
            path,data=report.create(root,r,format_character=False)
            self.assertIsNone(data['recorded_kills']);self.assertIn('unavailable',path.read_text())

    def test_native_dump_is_reused_without_running_engine_again(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,r=self.fixture(root);(root/'engine').write_text('frozen')
            m=json.loads((root/'recording.json').read_text());m['files_sha256']['engine']=report.sha(root/'engine');(root/'recording.json').write_text(json.dumps(m))
            def dump(run,snapshot,info,target):
                target.mkdir();p=target/'character.txt';p.write_text('native character');return p
            with mock.patch.object(report,'native_dump',side_effect=dump) as native:
                first,data=report.create(root,r);report.create(root,r)
                self.assertEqual(native.call_count,1)
                self.assertIsNotNone(data['native_character_dump'])

    def test_changed_frozen_data_prevents_native_formatting(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);_,r=self.fixture(root);(root/'engine').write_text('frozen')
            data=root/'data/gamedata/class.txt';data.parent.mkdir(parents=True);data.write_text('original')
            m=json.loads((root/'recording.json').read_text());m['files_sha256'].update({
                'engine':report.sha(root/'engine'),'data/gamedata/class.txt':report.sha(data)})
            (root/'recording.json').write_text(json.dumps(m));data.write_text('changed')
            with mock.patch.object(report,'native_dump') as native:
                _,result=report.create(root,r)
                native.assert_not_called()
                self.assertIn('Frozen runtime data changed',result['character_dump_error'])
                self.assertEqual(result['recorded_kills'],5)

    def test_formatting_refuses_a_dump_at_a_different_game_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,_=self.fixture(root);info=report.saved_character(p)
            def child(cmd,**kwargs):
                out=Path(kwargs['cwd']);(out/'user/Measure.txt').write_text('[Angband Character Dump]\nGame 1001\n')
                return SimpleNamespace(returncode=0)
            with mock.patch.object(report.subprocess,'run',side_effect=child),self.assertRaisesRegex(ValueError,'snapshot turn'):
                report.native_dump(root,p,info,root/'format')


if __name__=='__main__':unittest.main()
