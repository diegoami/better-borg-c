"""Curate identity/outcome receipts; full raw runs remain outside Git."""
from pathlib import Path
import hashlib,json,argparse
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
runs=[]
for path in sorted(Path('/tmp').glob('zoo1045-*/result.json')):
 d=json.loads(path.read_text())
 if 'wall_seconds' not in d: continue
 b=d['build'];t=path.parent/'trace.txt';lines=t.read_text().splitlines()
 runs.append({'run':path.parent.name,'gameplay_valid':d['states'][-1]['decisions']>0,'diagnostic_load':d.get('starting_save_sha256') is not None,'source':b['source_commit'],'harness':d['harness_commit'],
  'runner_sha256':d['runner_sha256'],'compiler':b['compiler'],'binary_sha256':b['binary_sha256'],
  'outcome':d['outcome'],'wall_seconds':d['wall_seconds'],'cap':d['turn_cap'],
  'configuration':(path.parent/'user/borg.txt').read_text(),
  'starting_save_sha256':d['starting_save_sha256'],
  'trace_sha256':hashlib.sha256(t.read_bytes()).hexdigest(),
  'final':{k:v for k,v in d['states'][-1].items() if k!='rng'},
  'turn59893_notes':sum(l.startswith('BORG 59893 ') for l in lines)})
a.output.write_text(json.dumps({'schema':'zoo1045-investigation@1','runs':runs},indent=2)+'\n')
