"""Moves Chinese string literals of game/silentstar/ui/*.gd into data/locale/ui.csv.

Write the new screen text in Chinese straight into the code while developing, then run
    python3 tools/ui_text_import.py [--prune]      (--prune also deletes the rows no code uses)
Every string literal with Chinese in it becomes tr("ui.<file>.<function>.<n>") and gets a row (zh_CN filled, en empty). A text that is
already in ui.csv reuses its key. Comments are left alone. tools/check_ui_text.py checks the result.
Rename a key by hand (code and ui.csv) when a better name is worth it, e.g. ui.common.wide_space.
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
DYNAMIC_PREFIXES = ('ui.reason.',)      # keys built at run time (same list as check_ui_text.py)
FUNC = re.compile(r'\s*(?:static )?func (\w+)')


def unescape(t):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(m.group(1), m.group(1)), t)


def main():
    rows = {}
    with open(CSV_PATH, encoding='utf8', newline='') as fh:
        for row in csv.reader(fh):
            if row and row[0] != 'key':
                rows[row[0]] = row
    by_text = {r[1]: k for k, r in rows.items()}
    counters = {}
    for k in rows:
        m = re.match(r'ui\.(\w+)\.(\w+)\.(\d+)$', k)
        if m:
            counters[(m.group(1), m.group(2))] = max(counters.get((m.group(1), m.group(2)), 0), int(m.group(3)))
    added = 0
    for path in sorted(glob.glob(os.path.join(UI_DIR, '*.gd'))):
        base = os.path.basename(path)[:-3].replace('_view', '').replace('ui_story', 'story')
        with open(path, encoding='utf8') as fh:
            lines = fh.read().split('\n')
        cur = 'top'
        out = []
        for line in lines:
            m = FUNC.match(line)
            if m:
                cur = m.group(1).lstrip('_')
            if line.lstrip().startswith('#'):
                out.append(line)
                continue

            def rep(mo):
                nonlocal added
                raw = mo.group(1)
                if not CJK.search(raw):
                    return mo.group(0)
                text = unescape(raw)
                if text in by_text:
                    return 'tr("%s")' % by_text[text]
                ck = (base, cur)
                counters[ck] = counters.get(ck, 0) + 1
                key = 'ui.%s.%s.%d' % (base, cur, counters[ck])
                by_text[text] = key
                rows[key] = [key, text, '']
                added += 1
                return 'tr("%s")' % key
            out.append(LITERAL.sub(rep, line))
        with open(path, 'w', encoding='utf8') as fh:
            fh.write('\n'.join(out))
    if '--prune' in sys.argv:       # drop the rows no code uses any more
        used = set()
        for path in glob.glob(os.path.join(UI_DIR, '*.gd')):
            with open(path, encoding='utf8') as fh:
                text = fh.read()
            used.update(re.findall(r'"(ui\.[a-z_0-9]+(?:\.[a-z_0-9]+)+)"', text))
        for k in [k for k in rows if k not in used and not k.startswith(DYNAMIC_PREFIXES)]:
            del rows[k]
            print('pruned', k)
    with open(CSV_PATH, 'w', encoding='utf8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['key', 'zh_CN', 'en'])
        for k in sorted(rows):
            w.writerow(rows[k])
    print('added %d row(s); ui.csv has %d' % (added, len(rows)))


if __name__ == '__main__':
    main()
