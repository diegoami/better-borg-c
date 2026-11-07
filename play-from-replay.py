#!/usr/bin/env python3
"""Play a separate manual branch from a verified historical replay boundary."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('borg_takeover', ROOT / 'tools/borg-takeover.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if __name__ == '__main__':
    raise SystemExit(module.main())
