import importlib.util,argparse
from pathlib import Path
s=importlib.util.spec_from_file_location('measure',Path.cwd()/'tools/measure-native.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.run(argparse.Namespace(build=Path('/tmp/zoo1045-pristine'),output=Path('/tmp/zoo1045-replay-pristine-named'),seed=1045,cap=100000,timeout=900,stall_timeout=90,load=Path('/tmp/zoo1045-frozen.save'),play_turns=1000,no_saves=True,configuration='borg_munchkin_start = TRUE'))
