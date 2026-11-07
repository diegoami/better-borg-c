import argparse,importlib.util,json,subprocess,time
from pathlib import Path
ROOT=Path.cwd()
p=argparse.ArgumentParser();p.add_argument('--trial',type=int);a=p.parse_args()
s=importlib.util.spec_from_file_location('measure',ROOT/'tools/measure-native.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
series=json.loads((ROOT/'patches/series.json').read_text());
def result(n):
 return Path('/tmp/zoo1045-run-'+('pristine' if n==0 else 'p'+str(n))+'/result.json')
if a.trial is not None:
 n=a.trial;b=Path('/tmp/zoo1045-'+('pristine' if n==0 else 'p'+str(n)));out=result(n).parent
 ref=series['baseline'] if n==0 else series['patches'][n-1]['merge_commit']
 if isinstance(ref,dict): ref=ref.get('commit') or ref.get('ref')
 m.prepare(argparse.Namespace(output=b,ref=ref,retry=False,observe=True,recording=False))
 m.run(argparse.Namespace(build=b,output=out,seed=1045,cap=100000,timeout=900,stall_timeout=90,load=None,no_saves=True,configuration='borg_munchkin_start = TRUE'))
else:
 def trial(n):
  subprocess.run(['flock','/tmp/angband-validation.lock','python3',__file__,'--trial',str(n)],check=True,cwd=ROOT)
  d=json.loads(result(n).read_text());print('TRIAL',n,d['outcome'],d['states'][-1]['turn'],flush=True)
  if d['outcome'] not in ['stalled','turn_cap']: raise RuntimeError('unclassifiable trial')
  return d['outcome']=='stalled'
 # An original native control is required even though zoo already reports it.
 assert not trial(0)
 r=Path('/tmp/zoo1045-run-m3/result.json')
 while not r.exists() or 'wall_seconds' not in json.loads(r.read_text()): time.sleep(5)
 d=json.loads(r.read_text());assert d['outcome'] in ['turn_cap','stalled']
 lo,hi=(0,34) if d['outcome']=='stalled' else (34,42)
 samples={0:'turn_cap',34:d['outcome'],42:'stalled'}
 while hi-lo>1:
  mid=(lo+hi)//2; bad=trial(mid); samples[mid]='stalled' if bad else 'turn_cap'
  if bad: hi=mid
  else: lo=mid
 Path('/tmp/zoo1045-bisect.json').write_text(json.dumps({'last_good':lo,'first_bad':hi,'samples':samples},indent=2)+'\n');print('BOUNDARY',lo,hi,flush=True)
