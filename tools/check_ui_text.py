"""Checks the screen code against data/locale/ui.csv (run by tools/check.py, or alone: python3 tools/check_ui_text.py).

1. No Chinese (or other CJK text, full-width punctuation) in a string literal of game/silentstar/ui/*.gd: text lives in ui.csv
   and the code says tr("key"). Comments are not checked.
2. Every tr("key") literal in the screen code has a row in ui.csv.
3. Every row of ui.csv is used by some tr("key") literal or is listed as used by a computed key (prefix in DYNAMIC_PREFIXES).
Returns a list of problems; the exit code is 1 when there are any.
"""
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(ROOT, 'game', 'silentstar', 'ui')
CSV_PATH = os.path.join(ROOT, 'data', 'locale', 'ui.csv')
CJK = re.compile('[⺀-鿿＀-￯　-〿 -⁯×→←−≥≤·—]')
LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
TR_KEY = re.compile(r'tr\("([^"]+)"\)')
# keys built at run time ("ui.reason." + id): the rows under these prefixes need no literal use
DYNAMIC_PREFIXES = ('ui.reason.',)
# keys that sit in dictionaries and are passed to tr() later
KEY_LITERAL = re.compile(r'"(ui\.[a-z_0-9]+(?:\.[a-z_0-9]+)+)"')


def check():
    problems = []
    used = set()
    for path in sorted(glob.glob(os.path.join(UI_DIR, '*.gd'))):
        name = os.path.basename(path)
        with open(path, encoding='utf8') as fh:
            for no, line in enumerate(fh, 1):
                if line.lstrip().startswith('#'):
                    continue
                for m in LITERAL.finditer(line):
                    if CJK.search(m.group(1)):
                        problems.append('%s:%d: text in code: "%s" (move it to data/locale/ui.csv)' % (name, no, m.group(1)[:40]))
                used.update(TR_KEY.findall(line))
                used.update(KEY_LITERAL.findall(line))
    rows = {}
    with open(CSV_PATH, encoding='utf8', newline='') as fh:
        for row in csv.reader(fh):
            if row and row[0] != 'key':
                rows[row[0]] = row
    for k in sorted(used):
        if k not in rows:
            problems.append('ui.csv has no row for the key %s' % k)
    for k in sorted(rows):
        if k not in used and not k.startswith(DYNAMIC_PREFIXES):
            problems.append('ui.csv row %s is not used by the code' % k)
        elif rows[k][1] == '':
            problems.append('ui.csv row %s has no Chinese text' % k)
    return problems


if __name__ == '__main__':
    probs = check()
    for p in probs:
        print(p)
    print('ui text: %d problem(s)' % len(probs))
    sys.exit(1 if probs else 0)
