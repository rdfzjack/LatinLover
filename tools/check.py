"""Run this after editing the data tables: one command finds all the problems.

    python3 tools/check.py          (Windows: double-click check_data.bat in the repository root)

In order:
1. JSON format: missing commas, extra commas, curly quotes and the like, with the line number.
2. Duplicates: two records of one table with the same id, or one field written twice in one record.
3. Content: all checks of tools/check_data.py (fields complete, referenced things exist, conditions and effects well written).
4. Text: data/locale/text.csv is regenerated from the display fields (tools/extract_text.py); missing Chinese, duplicate or extra keys,
   stray Chinese outside the display fields and stale English are errors.
5. Screen text: no Chinese in the string literals of game/silentstar/ui/*.gd; every tr("key") has a row in data/locale/ui.csv
   (tools/check_ui_text.py).
6. Playthrough and guard (Godot, from step 12c): every bot plays 30 games; a crash is an error; design/targets.json is checked
   (PASS / FAIL per target, widened by 10%). FAIL lines are printed but do not fail the check. Skipped when Godot is not found.
"""
import json
import os
import sys
import runpy
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'new')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

JSON_HINTS = [
    ('Illegal trailing comma', 'extra comma here: no comma is allowed after the last item of a list [ ] or { }'),
    ("Expecting ',' delimiter", 'a comma , is missing here (items must be separated by commas)'),
    ('Expecting property name enclosed in double quotes', 'most likely the previous line ends with an extra comma (no comma after the last item of a list or {}), or a field name is not wrapped in double quotes'),
    ('Expecting value', 'a value is missing here: maybe an extra comma, or curly quotes were used, or null / true / false is misspelled'),
    ("Expecting ':' delimiter", 'a colon : must follow the field name'),
    ('Unterminated string', 'unclosed quote: double quotes " must come in pairs'),
    ('Invalid control character', 'a string cannot contain a raw line break; use two fields or keep it on one line'),
    ('Extra data', 'extra content at the end of the file: one bracket too many, or something after the outermost }'),
]


def json_problem(path, e):
    lines = open(path, encoding='utf-8').read().split('\n')
    ln = e.lineno
    line = lines[ln - 1] if 0 < ln <= len(lines) else ''
    hint = next((h for k, h in JSON_HINTS if e.msg.startswith(k)), e.msg)
    out = [f'{os.path.basename(path)} line {ln}, char {e.colno}: {hint}']
    if ln > 1:
        out.append(f'    {ln - 1:>5} | {lines[ln - 2]}')
    out.append(f'    {ln:>5} | {line}')
    out.append('            ' + ' ' * (e.colno - 1) + '^ about here')
    for s in (lines[ln - 2] if ln > 1 else '', line):
        if any(c in s for c in '“”‘’：，'):
            out.append('    non-ASCII punctuation near here (curly quotes, colons, commas); JSON needs plain ASCII quotes, colons and commas')
            break
    return '\n'.join(out)


def load_strict(path, problems):
    """Reads JSON and also finds a field written twice in one record."""
    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                who = dict(pairs).get('id') or dict(pairs).get('name') or ''
                problems.append(f'{os.path.basename(path)}: {("record " + str(who) + ": ") if who else "a record: "}field "{k}" appears twice, keep only one')
            seen[k] = v
        return seen
    with open(path, encoding='utf-8-sig') as fh:
        return json.load(fh, object_pairs_hook=hook)


def step_json():
    problems, tables = [], {}
    for n in sorted(os.listdir(DATA)):
        if not n.endswith('.json'):
            continue
        p = os.path.join(DATA, n)
        raw = open(p, 'rb').read()
        if raw.startswith(b'\xef\xbb\xbf'):
            problems.append(f'{n}: the file starts with a BOM (some editors save as "UTF-8 with BOM"); save as UTF-8 without BOM')
        try:
            tables[n] = load_strict(p, problems)
        except json.JSONDecodeError as e:
            problems.append(json_problem(p, e))
        except UnicodeDecodeError:
            problems.append(f'{n}: not UTF-8, please save as UTF-8')
    return problems, tables


def step_dup(tables):
    problems = []
    seen_event = {}
    for n, t in tables.items():
        if not isinstance(t, dict):
            continue
        for k, v in t.items():
            if not (isinstance(v, list) and v and all(isinstance(x, dict) for x in v)):
                continue
            key = 'id' if any('id' in x for x in v) else ('name' if all('name' in x for x in v) else None)
            if key is None:
                continue
            ids = {}
            for x in v:
                i = x.get(key)
                if i is None:
                    continue
                if i in ids:
                    problems.append(f'{n} "{k}": two entries have the same {key} {i}; when copying an entry remember to change its {key}')
                ids[i] = 1
                if n in ('events.json', 'outing.json') and k == 'event' and key == 'id':
                    if i in seen_event and seen_event[i] != n:
                        problems.append(f'event id {i} is in both events.json and outing.json; event ids must be globally unique')
                    seen_event[i] = n
    return problems


KIND = {bool: 'boolean (true / false)', int: 'number (no quotes)', str: 'string (in double quotes)', list: 'list [ ]', dict: '{ } block'}


def kind(v):
    return type(v) if type(v) in KIND else None


def step_types(tables):
    """For the same field of one table, the other records have numbers but this one has a string and the like: most likely a typo.
        Only compares numbers, strings and booleans; null, lists and {} blocks are ignored (prob, cond and the like legitimately have several forms)."""
    problems = []
    for n, t in tables.items():
        if not isinstance(t, dict):
            continue
        for k, v in t.items():
            if not (isinstance(v, list) and len(v) >= 3 and all(isinstance(x, dict) for x in v)):
                continue
            fields = {}
            for x in v:
                for f, val in x.items():
                    if val is not None:
                        fields.setdefault(f, []).append((kind(val), x))
            for f, lst in fields.items():
                count = {}
                for kd, _ in lst:
                    count[kd] = count.get(kd, 0) + 1
                if len(count) < 2:
                    continue
                main, m = max(count.items(), key=lambda a: a[1])
                if m < 3 or m < len(lst) * 0.8:
                    continue      # fields that are legitimately mixed (for example cond may be [] or something else) are ignored
                if main not in (int, str, bool):
                    continue
                for kd, x in lst:
                    if kd != main and kd in (int, str, bool):
                        who = x.get('id') or x.get('name') or 'a record'
                        problems.append(f'{n}: {who} field "{f}" is a {KIND.get(kd, "?")}, but the other records of this table use {KIND[main]},'
                                        f'the current value is {json.dumps(x[f], ensure_ascii=False)}')
    return problems


def step_content():
    """Runs check_data.py and brings its output back unchanged."""
    import io
    import contextlib
    buf = io.StringIO()
    ok = True
    try:
        with contextlib.redirect_stdout(buf):
            runpy.run_path(os.path.join(ROOT, 'tools', 'check_data.py'), run_name='__main__')
    except SystemExit as e:
        ok = not e.code
    except KeyError as e:
        ok = False
        buf.write(f'a record is missing field {e}. Compare it with the other records of the same table to see which field is missing.\n')
        buf.write(_where())
    except Exception as e:
        ok = False
        buf.write(f'error while checking: {type(e).__name__}: {e}\nMost likely a field has the wrong value type (for example a "string" where a number belongs, or a single value where a list [] belongs).\n')
        buf.write(_where())
    lines = [x for x in buf.getvalue().split('\n') if x.strip()]
    errs = [x for x in lines if not x.startswith(('passed', 'note: ', 'failed: '))]
    return ok, errs, lines


def _where():
    tb = traceback.extract_tb(sys.exc_info()[2])
    fr = [f for f in tb if f.filename.endswith('check_data.py')]
    if fr:
        return f'(the failing check is at tools/check_data.py line {fr[-1].lineno}: {fr[-1].line})\n'
    return ''


def find_godot():
    """The Godot 4 executable: $GODOT, or godot / godot4 on the PATH; None when there is none."""
    import shutil
    for c in (os.environ.get('GODOT'), shutil.which('godot'), shutil.which('godot4')):
        if c and os.path.exists(c):
            return c
    return None


def step_play():
    """Step 5 (from step 12c, sim/ is frozen): Godot plays 30 games per bot and checks design/targets.json (the guard).
    Returns (crash problems, guard lines). Without Godot the step is skipped with a note."""
    import subprocess
    godot = find_godot()
    if godot is None:
        return None, ['note: Godot was not found (set GODOT or put godot on the PATH), so the bot playthrough and the guard were skipped']
    out = os.path.join(ROOT, 'work', 'check_guard.txt')
    cmd = [godot, '--headless', '--path', os.path.join(ROOT, 'game', 'silentstar'), '--script', 'res://tools/report.gd', '--',
           '--n=30', '--bots=all', '--no-buy', '--guard=design/targets.json', '--widen=10', '--out=work/check_guard.txt']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
    except subprocess.TimeoutExpired:
        return ['the Godot playthrough did not finish within an hour'], []
    errs = [x for x in (r.stderr or '').split('\n') if 'SCRIPT ERROR' in x or 'ERROR:' in x]
    if r.returncode not in (0, 2) or not os.path.exists(out):
        return [f'the game crashed while the bots were playing (exit code {r.returncode}):'] + errs[:10], []
    with open(out, encoding='utf-8') as f:
        lines = [x for x in f.read().split('\n') if x.startswith(('PASS', 'FAIL'))]
    return (errs[:10] if errs else []), lines


def main():
    print('1/6 checking JSON format...')
    problems, tables = step_json()
    if problems:
        print('\n\n'.join(problems))
        print('\nFAILED: fix the format errors above, then run again.')
        return 1
    print('2/6 checking duplicates and types...')
    problems = step_dup(tables) + step_types(tables)
    if problems:
        print('\n'.join(problems))
        print('\nFAILED: fix the problems above, then run again.')
        return 1
    print('3/6 checking content...')
    ok, errs, lines = step_content()
    if not ok:
        print('\n'.join(errs))
        print(f'\nFAILED: {len(errs)} content problems. Each line starts with the file name, then which record and what is wrong.')
        return 1
    print('4/6 checking text.csv...')
    import extract_text
    problems, notes = extract_text.sync()
    print('\n'.join(notes))
    if problems:
        print('\n'.join(problems))
        print('\nFAILED: fix the problems above, then run again.')
        return 1
    print('5/6 checking the screen text (ui.csv)...')
    import check_ui_text
    problems = check_ui_text.check()
    if problems:
        print('\n'.join(problems))
        print('\nFAILED: fix the problems above, then run again.')
        return 1
    print('6/6 bot playthrough and guard (Godot, 30 games per bot; takes a few minutes)...')
    problems, guard = step_play()
    if problems is None:
        print('\n'.join(guard))
        print('\nAll checks passed (without the playthrough), ready to commit.')
        return 0
    if problems:
        print('\n'.join(problems))
        print('\nFAILED: the tables are fine but the game crashed while running. Most likely newly added content uses something the code does not support yet; send the text above to the model.')
        return 1
    fails = [x for x in guard if x.startswith('FAIL')]
    print(f'guard: {len(guard) - len(fails)} PASS, {len(fails)} FAIL (full report in work/check_guard.txt)')
    if fails:
        print('\n'.join(fails))
        print('\nThe tables are fine, but some balance targets are off. If you only added content, halve the effects of this batch and run again;'
              ' if they still fail, leave it to a balance round (design/BALANCE_WORKFLOW.md). Do not change other numbers to make them pass.')
        return 0
    print('\nAll checks passed, ready to commit.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
