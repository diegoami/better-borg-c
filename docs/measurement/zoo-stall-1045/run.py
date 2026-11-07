import importlib.util,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('build');p.add_argument('out');p.add_argument('--seed',type=int,default=1045);p.add_argument('--config',default='borg_munchkin_start = TRUE');a=p.parse_args()
s=importlib.util.spec_from_file_location('measure',Path.cwd()/'tools/measure-native.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
raise SystemExit(m.run(argparse.Namespace(build=Path(a.build),output=Path(a.out),seed=a.seed,cap=100000,timeout=900,stall_timeout=90,load=None,no_saves=True,configuration=a.config)))
