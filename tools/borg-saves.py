#!/usr/bin/env python3
"""Rolling native-save backups and explicit restore, called under a save lock."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def backup(save, source=None):
    source = source if source is not None else save
    if not source.exists():
        return None
    expected = digest(source)
    folder = save.parent / 'backups' / save.name
    folder.mkdir(parents=True, exist_ok=True)
    for slot in range(5, 1, -1):
        previous = folder / f'save.{slot - 1}'
        if previous.exists():
            shutil.copy2(previous, folder / f'save.{slot}')
    shutil.copy2(source, folder / 'save.1')
    if digest(folder / 'save.1') != expected:
        raise ValueError('Backup hash differs; refusing to run')
    return expected


def publish(save, final, original_digest):
    """Refuse to overwrite a save changed by an outside/manual session."""
    current = digest(save) if save.exists() else None
    if current != original_digest:
        raise ValueError('Named save changed during this run; final.save retained without overwriting it')
    descriptor, path = tempfile.mkstemp(prefix='.borg-save-', dir=save.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output, final.open('rb') as source:
            shutil.copyfileobj(source, output)
            output.flush()
            os.fsync(output.fileno())
        if digest(Path(path)) != digest(final):
            raise ValueError('Save copy hash differs; original preserved')
        os.replace(path, save)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def restore(save, slot=1):
    if slot not in range(1, 6):
        raise ValueError('Backup slot must be 1 through 5')
    folder = save.parent / 'backups' / save.name
    selected = folder / f'save.{slot}'
    if not selected.is_file():
        raise ValueError(f'Backup does not exist: {selected}')
    original = digest(save) if save.exists() else None
    if original:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        preserved = folder / f'before-restore-{stamp}.save'
        shutil.copy2(save, preserved)
        if digest(preserved) != original:
            raise ValueError('Could not preserve current save before restore')
        print(f'Preserved current save: {preserved}', flush=True)
    publish(save, selected, original)
    print(f'Restored backup slot {slot}: {save}', flush=True)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 4 or sys.argv[1] != 'restore':
            raise ValueError('Usage: borg-saves.py restore SAVE_PATH SLOT')
        restore(Path(sys.argv[2]), int(sys.argv[3]))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
