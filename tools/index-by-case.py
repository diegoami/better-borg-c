#!/usr/bin/env python3
"""Index existing replay/branch/recording directories under by-case/DEATH/ with symlinks.

Nothing is renamed or moved, so saved --resume paths keep working. Safe to rerun."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('index_workflow', ROOT / 'tools/death-workflow.py')
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def original_of(path):
    try:
        return workflow.read(path)['original']
    except (OSError, ValueError, KeyError):
        return None


def main():
    base = workflow.artifacts()
    cases = workflow.recorded_cases()
    made, unknown = [], []

    def add(kind, directory, original, name=None):
        case = cases.get(Path(original).resolve()) if original else None
        if case is None:
            unknown.append(directory)
            return
        link = workflow.link_case(case, kind, directory, name)
        made.append(link)

    for branch in sorted((base / 'takeover/branches').glob('*/branch.json')):
        receipt = workflow.read(branch)
        folder = branch.parent
        if folder.name[:1] == 'D':
            continue  # already named by death
        add('branches', folder, receipt.get('original'), f't{receipt.get("actual_turn")}-{folder.name}')
    for verification in sorted((base / 'replays').glob('*/verification.json')):
        folder = verification.parent
        if folder.name[:1] != 'D':
            add('replays', folder, original_of(verification))
    for directory, case in sorted((str(k), v) for k, v in cases.items()):
        if (Path(directory) / 'recording.json').is_file():
            made.append(workflow.link_case(case, 'recording', directory))
    print(f'{len(made)} links under {base / "by-case"}')
    for folder in unknown:
        print(f'  not matched to a known death: {folder}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
