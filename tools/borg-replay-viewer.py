"""Local, reversible inspection of original terminal frames; no game execution."""
from bisect import bisect_right
from contextlib import contextmanager
import curses
import gzip
import json
import re
import tempfile


@contextmanager
def frame_lines(directory):
    path = directory / 'frames.jsonl.gz'
    with (gzip.open(path, 'rt') if path.exists() else (directory / 'frames.jsonl').open()) as stream:
        yield stream


class Frames:
    """Index to disk, then reconstruct at most 100 delta frames per seek."""
    def __init__(self, directory):
        self.file = tempfile.TemporaryFile()
        self.index = []
        self.turns = []
        try:
            self._build_index(directory)
        except BaseException:
            self.file.close()
            raise

    def _build_index(self, directory):
        last_full = 0
        with frame_lines(directory) as stream:
            for line in stream:
                try:
                    frame = json.loads(line)
                except json.JSONDecodeError:
                    # An interrupted recorder may leave one incomplete tail row.
                    if stream.read(1):
                        raise ValueError('Malformed recording frame before the stream end')
                    break
                if frame['full']:
                    last_full = len(self.index)
                if not self.index and not frame['full']:
                    raise ValueError('Recording starts without a full terminal frame')
                offset = self.file.tell()
                self.file.write(line.encode())
                self.index.append((offset, last_full))
                self.turns.append(frame['turn'])
        if not self.index:
            raise ValueError('No game frames recorded')

    def close(self):
        self.file.close()

    def at_turn(self, turn):
        return max(0, min(len(self.index) - 1, bisect_right(self.turns, turn) - 1))

    def get(self, index):
        first = self.index[index][1]
        self.file.seek(self.index[first][0])
        chars, attrs, palette, details, inventory, spells = [], [], None, None, None, None
        for _ in range(first, index + 1):
            frame = json.loads(self.file.readline())
            size = frame['width'] * frame['height']
            if frame['full']:
                chars, attrs = [32] * size, [0] * size
            if size != len(chars):
                raise ValueError('Geometry changed without a full frame')
            for at, character, attribute in frame['cells']:
                if not 0 <= at < size:
                    raise ValueError('Invalid recorded cell offset')
                chars[at], attrs[at] = character, attribute
            if frame['palette'] is not None:
                palette = frame['palette']
            if frame.get('details') is not None:
                details = frame['details']
            if frame.get('inventory') is not None:
                inventory = frame['inventory']
            if frame.get('spells') is not None:
                spells = frame['spells']
        frame['diagnostics'] = details
        frame['inventory'] = inventory
        frame['spells'] = spells
        return frame, chars, attrs, palette


def glyph(code):
    # Legacy X11 font control glyphs are represented portably for inspection.
    if code == 31:
        return '·'
    if code == 1:
        return '♦'
    if code < 32:
        return ' '
    return chr(code) if code <= 0x10ffff else '�'


def inventory_rows(frame, equipment=False):
    """Only native player-known descriptions; never infer them from actual gear."""
    inventory = frame.get('inventory')
    if inventory is None:
        return [('Inventory was not captured in this older movie.', 1),
                ('Reopen without --view-only to recover the native inventory.', 1)]
    rows = [('Equipment' if equipment else 'Inventory', 1)]
    total, remaining = inventory['total_weight'], inventory['remaining_weight']
    rows += [(f"Burden {total / 10:.1f} lb ({abs(remaining) / 10:.1f} lb " +
              ('overweight)' if remaining < 0 else 'remaining)'), 1), ('', 1)]
    sections = ('equipment', 'quiver') if equipment else ('pack',)
    for section in sections:
        if section == 'quiver':
            rows += [('', 1), ('Quiver', 1)]
        for item in inventory[section]:
            description = (item['slot'] + ': ' if item.get('slot') else '') + item['description']
            weight = f"{item['weight'] / 10:5.1f} lb" if item['weight'] else ''
            rows.append((f"{item['label']}) {description:<55} {weight}", item.get('attr', 1)))
        if not inventory[section]:
            rows.append(('(empty)', 1))
    return rows


def spell_rows(frame):
    spells = frame.get('spells')
    if spells is None and frame.get('caster') is False:
        return [('Spells / prayers', 1), ('This class has no spells or prayers.', 1)]
    if spells is None:
        return [('Spell data was not captured in this older movie.', 1),
                ('Reopen normally to recover native spell availability.', 1)]
    rows = [(f"Spells / prayers — {spells['class']} — Mana {spells['mana']}/{spells['max_mana']}", 1), ('', 1)]
    if not spells['caster']:
        return rows + [('This class has no spells or prayers.', 1)]
    if not spells['learned']:
        return rows + [('No learned spells at this moment.', 1)]
    rows += [('Name                           Lv  MP Fail  Status', 1)]
    for spell in spells['learned']:
        color = 13 if spell['status'] == 'Ready' else 11
        rows.append((f"{spell['label']}) {spell['name']:<27} {spell['level']:2} {spell['mana']:3} {spell['fail']:3}%  {spell['status']}", color))
        if spell['book']:
            label = 'on floor' if spell['book_label'] == '-' else spell['book_label'] + ')'
            rows.append((f"  {label} {spell['book']}", 1))
    return rows + [('', 1), ('Low mana: an overexertion attempt is possible, as in the game.', 1)]


def color_attribute(color, palette):
    color %= 32
    if palette and color < len(palette) and curses.COLORS >= 256:
        red, green, blue = palette[color]
        ansi = 16 + 36 * round(red / 255 * 5) + 6 * round(green / 255 * 5) + round(blue / 255 * 5)
        curses.init_pair(color + 1, ansi, curses.COLOR_BLACK)
        return curses.color_pair(color + 1)
    return 0


def sidebar_vitals(frame, chars):
    """Read the recorded sidebar; terminal redraw can lag actual state at rest."""
    vitals = {}
    for row in range(frame['height']):
        start = row * frame['width']
        text = ''.join(glyph(c) for c in chars[start:start + min(22, frame['width'])])
        match = re.match(r'^\s*(HP|SP)\s+(-?\d+)\s*/\s*(\d+)\b', text)
        if match:
            vitals[match[1]] = (int(match[2]), int(match[3]))
    return vitals


def playback_status(frame, chars, total, sidebar_visible=True):
    mismatches = []
    vitals = sidebar_vitals(frame, chars) if sidebar_visible else {}
    for label, (shown, shown_max) in vitals.items():
        field = label.lower()
        current, maximum = frame[field], frame.get('max_' + field)
        if shown != current or (maximum is not None and shown_max != maximum):
            actual = f"{current}/{maximum}" if maximum is not None else str(current)
            mismatches.append(f"{label} {shown}/{shown_max}; recorded {label} {actual}")
    prefix = f"Frame {frame['index']}/{total}"
    if mismatches:
        return prefix + ' | Sidebar awaiting redraw: ' + ', '.join(mismatches), True
    return prefix + ' | j/k scroll  [] pan | m monsters  d debug', False


def read_key(screen, playing=False):
    """Accept both normal CSI and application-cursor sequences used by terminals."""
    key = screen.getch()
    if key != 27:
        return key
    screen.timeout(40)
    try:
        first = screen.getch()
        if first not in (ord('['), ord('O')):
            if first != -1:
                curses.ungetch(first)
            return 27
        sequence = chr(first)
        for _ in range(6):
            part = screen.getch()
            if part == -1:
                break
            sequence += chr(part)
            if chr(part).isalpha() or part == ord('~'):
                break
        return {'[A': curses.KEY_UP, 'OA': curses.KEY_UP,
                '[B': curses.KEY_DOWN, 'OB': curses.KEY_DOWN,
                '[C': curses.KEY_RIGHT, 'OC': curses.KEY_RIGHT,
                '[D': curses.KEY_LEFT, 'OD': curses.KEY_LEFT,
                '[H': curses.KEY_HOME, 'OH': curses.KEY_HOME, '[1~': curses.KEY_HOME,
                '[F': curses.KEY_END, 'OF': curses.KEY_END, '[4~': curses.KEY_END,
                '[5~': curses.KEY_PPAGE, '[6~': curses.KEY_NPAGE}.get(sequence, -1)
    finally:
        screen.timeout(100 if playing else -1)


def show(directory, turn=None, verified=False, dump=False, caster=None):
    frames = Frames(directory)
    index = frames.at_turn(turn if turn is not None else frames.turns[-1] - 105)
    try:
        if dump:
            frame, chars, _, _ = frames.get(index)
            print(('VERIFIED' if verified else 'RECORDING ONLY / NOT RERUN-VERIFIED'),
                  f"turn={frame['turn']} phase={frame['phase']} level={frame['level']} depth={frame['depth']} HP={frame['hp']}")
            for row in range(frame['height']):
                print(''.join(glyph(c) for c in chars[row * frame['width']:(row + 1) * frame['width']]))
            return

        def interactive(screen):
            nonlocal index
            curses.curs_set(0)
            curses.start_color()
            screen.keypad(True)
            playing = False
            panel = 'screen'
            scroll = 0
            horizontal = 0
            while True:
                frame, chars, attrs, palette = frames.get(index)
                frame['caster'] = caster
                height, width = screen.getmaxyx()
                screen.erase()
                badge = 'VERIFIED' if verified else 'RECORDING ONLY / UNVERIFIED'
                hp = f"{frame['hp']}/{frame['max_hp']}" if 'max_hp' in frame else str(frame['hp'])
                sp = f"{frame['sp']}/{frame['max_sp']}" if 'max_sp' in frame else str(frame['sp'])
                header = f"{badge} | turn {frame['turn']} ({frame['phase']}) | HP {hp} SP {sp} level {frame['level']} depth {frame['depth']}"
                screen.addnstr(0, 0, header, max(0, width - 1))
                for row in range(max(0, min(frame['height'] - scroll, height - 3)) if panel == 'screen' else 0):
                    for col in range(max(0, min(frame['width'] - horizontal, width - 1))):
                        at = (row + scroll) * frame['width'] + col + horizontal
                        attribute = color_attribute(attrs[at], palette)
                        try:
                            screen.addstr(row + 1, col, glyph(chars[at]), attribute)
                        except curses.error:
                            pass
                if panel != 'screen':
                    detail = frame.get('diagnostics') or {}
                    rows = ['DIAGNOSTIC ACTUAL STATE (includes unknown/unseen information)',
                            'This data was never supplied to the Borg as additional input.', '']
                    if panel in ('inventory', 'equipment'):
                        rows = inventory_rows(frame, panel == 'equipment')
                    elif panel == 'spells':
                        rows = spell_rows(frame)
                    elif panel == 'gear':
                        for item in detail.get('gear', []):
                            rows.append(f"{item['quantity']} x {item['actual_kind']} [aware={item['aware']}; known={item['known_kind']}]")
                            rows.append(f"  pval={item['pval']} timeout={item['timeout']} hit/damage/AC={item['to_h']}/{item['to_d']}/{item['to_a']} {item['inscription']}")
                        rows += ['', 'Timed effects: ' + str(detail.get('timed', {}))]
                        rows += ['Borg state: ' + str(detail.get('borg', {}))]
                    else:
                        monsters = sorted(detail.get('monsters', []), key=lambda m: abs(m['x'] - frame['x']) + abs(m['y'] - frame['y']))
                        rows += [f"{'visible' if m['visible'] else 'UNSEEN ':7} {m['name']} HP {m['hp']}/{m['max_hp']} at({m['x']},{m['y']}) speed {m['speed']}" for m in monsters]
                    for row, line in enumerate(rows[scroll:scroll + height - 3], 1):
                        text, color = line if isinstance(line, tuple) else (line, 1)
                        screen.addnstr(row, 0, text[horizontal:], max(0, width - 1), color_attribute(color, palette))
                screen.addnstr(height - 2, 0, '←/→ step g turn Space play | i pack e equipment s magic | Esc back q quit', max(0, width - 1))
                status, pending = playback_status(frame, chars, len(frames.index), panel == 'screen')
                screen.addnstr(height - 1, 0, status, max(0, width - 1), color_attribute(11, palette) if pending else 0)

                screen.refresh()
                screen.timeout(100 if playing else -1)
                key = read_key(screen, playing)
                if key == ord('q'):
                    break
                if key == 27:
                    panel = 'screen'
                    scroll = horizontal = 0
                elif key in (ord('i'), ord('e'), ord('s'), ord('d'), ord('m'), ord('v')):
                    panel = {ord('i'): 'inventory', ord('e'): 'equipment', ord('s'): 'spells', ord('d'): 'gear', ord('m'): 'monsters', ord('v'): 'screen'}[key]
                    if panel != 'screen':
                        playing = False
                    scroll = horizontal = 0
                elif key == ord('j'):
                    scroll += 1
                elif key == ord('k'):
                    scroll = max(0, scroll - 1)
                elif key == ord('['):
                    horizontal = max(0, horizontal - 10)
                elif key == ord(']'):
                    horizontal = min(frame['width'] - 1, horizontal + 10)
                elif key == ord(' '):
                    playing = not playing
                elif key in (curses.KEY_RIGHT, ord('l')) or (key == -1 and playing):
                    index = min(len(frames.index) - 1, index + 1)
                elif key in (curses.KEY_LEFT, ord('h')):
                    index = max(0, index - 1)
                elif key == curses.KEY_DOWN:
                    index = min(len(frames.index) - 1, index + 10)
                elif key == curses.KEY_UP:
                    index = max(0, index - 10)
                elif key == curses.KEY_NPAGE:
                    index = min(len(frames.index) - 1, index + 100)
                elif key == curses.KEY_PPAGE:
                    index = max(0, index - 100)
                elif key == curses.KEY_HOME:
                    index = 0
                elif key == curses.KEY_END:
                    index = len(frames.index) - 1
                elif key == ord('g'):
                    playing = False
                    screen.timeout(-1)
                    curses.echo()
                    screen.addstr(height - 1, 0, 'Engine turn: ')
                    try:
                        index = frames.at_turn(int(screen.getstr(height - 1, 13, 15)))
                    except ValueError:
                        pass
                    curses.noecho()
        curses.wrapper(interactive)
    finally:
        frames.close()
