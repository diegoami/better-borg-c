"""Verified replay of D0012 through the diagnostic engine (issue #324).
Non-interference proof: the stream comparison must come back clean
(verified=true) with the diagnostic logging active."""
import sys
from pathlib import Path
from importlib.machinery import SourceFileLoader

ROOT = Path('/home/diego/projects/angband/better-borg-c')
loader = SourceFileLoader('replay_borg', str(ROOT / 'replay-borg.py'))
spec = loader.load_module

replay = spec()
recordings = replay.recordings

dossier = ROOT / 'docs/deaths/D0012-collected'
original = replay.resolve_recording(dossier)
recordings.validate(original)
print('recording:', original)

output = Path('/tmp/opencode/d324/diag-run')
if output.exists():
    import shutil; shutil.rmtree(output)

import os
os.environ['BORG_DIAG324'] = str(output.parent / 'diag-324.txt')
if (output.parent / 'diag-324.txt').exists():
    os.remove(output.parent / 'diag-324.txt')

result = replay.verify(original, output, 3600, engine=Path('/tmp/opencode/d324/build/game/angband'))
result['engine_mode'] = 'diagnostic rebuild with #324 observation hooks'
print('verified:', result['verified'])
print('first_difference:', result['first_difference'])
import json
(output.parent / 'diag-verification.json').write_text(json.dumps(result, indent=2) + '\n')
sys.exit(0 if result['verified'] else 1)
