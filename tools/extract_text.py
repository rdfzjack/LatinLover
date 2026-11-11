"""Builds data/locale/text.csv (Godot translation CSV: key,zh_CN,en) from the display fields of the data tables.

    python3 tools/extract_text.py                  rewrite text.csv (zh_CN is regenerated, en is kept)
    python3 tools/extract_text.py --prune          also drop rows whose record no longer exists
    python3 tools/extract_text.py --ack KEY...     mark the English of these keys as checked against the current Chinese
                                                   (a key prefix such as item. acknowledges every key starting with it)

Key format: <category>.<id>.<field>, nested lists add .<kind>.<index or id>, e.g.
    item.gold_watch.name   event.evt_deposit_2000.option.0.text   street.restaurant.service.steak.name
Chinese lives only in the display fields below; tools/check.py calls check() so a stray Chinese string elsewhere is reported.
The Chinese an English line was written against is kept in data/locale/en_basis.json; when the Chinese changes the English is
reported as stale until it is edited and acknowledged with --ack.
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'new')
LOCALE = os.path.join(ROOT, 'data', 'locale')
CSV_PATH = os.path.join(LOCALE, 'text.csv')
BASIS_PATH = os.path.join(LOCALE, 'en_basis.json')
CJK = re.compile('[㐀-鿿＀-￯　-〿]')

# (file, path of the list or record in the file, category, fields, nested lists)
# a nested list is (key in the record, label in the key, fields); its items are keyed by their id, or by index when they have none.
# fields in OPTIONAL may be missing or null; all others must hold Chinese.
SPEC = [
    ('stats.json', ['attrs'], 'attr', ['name'], []),
    ('stats.json', ['money'], 'money', ['name'], []),
    ('stats.json', ['roads'], 'road', ['name'], []),
    ('stats.json', ['fame_tiers'], 'fame', ['name'], []),
    ('stats.json', ['hidden'], 'hidden', ['name'], []),
    ('skills.json', ['skills'], 'skill', ['name'], []),
    ('classes.json', ['classes'], 'class', ['name'], []),
    ('books.json', ['tiers'], 'book_tier', ['name'], []),
    ('books.json', ['books'], 'book', ['name'], []),
    ('jobs.json', ['jobs'], 'job', ['name'], []),
    ('rest.json', ['rests'], 'rest', ['name'], []),
    ('places.json', ['places'], 'place', ['name'], []),
    ('lifestyle.json', ['lifestyles'], 'lifestyle', ['name'], []),
    ('street.json', ['entries'], 'street', ['name'], [('services', 'service', ['name'])]),
    ('items.json', ['items'], 'item', ['name'], []),
    ('habits.json', ['habits'], 'habit', ['name'], []),
    ('origins.json', ['questions'], 'origin', ['question'], [('options', 'option', ['text'])]),
    ('events.json', ['events'], 'event', ['name', 'body'], [('options', 'option', ['text'])]),
    ('outing.json', ['events'], 'event', ['name', 'body'], [('options', 'option', ['text'])]),
    ('opportunities.json', ['opportunities'], 'opp', ['name'], []),
    ('annual.json', ['occasions'], 'annual', ['name'], []),
    ('romance.json', ['npcs'], 'npc', ['name', 'identity'], []),
    ('rivals.json', ['named'], 'rival', ['name'], []),
    ('roles.json', ['roles'], 'role', ['name', 'film_title'], []),
    ('roles.json', ['tags'], 'tag', ['name'], []),
    ('endings.json', ['forced'], 'ending', ['name', 'body'], []),
    ('endings.json', ['special'], 'ending', ['name', 'body'], []),
    ('endings.json', ['categories'], 'ending_category', ['name'], []),
    ('endings.json', ['endings'], 'ending', ['name', 'content', 'body'], []),
]
OPTIONAL = {'body', 'identity', 'content'}      # may be missing or null (body until the story is written); the other fields must hold text


def _load(name):
    with open(os.path.join(DATA, name), encoding='utf-8-sig') as fh:
        return json.load(fh)


def _fields(rec, fields, prefix, rows, covered, problems, where):
    for f in fields:
        covered.add((id(rec), f))
        v = rec.get(f)
        if f in OPTIONAL and (v is None or v == ''):
            continue
        if not isinstance(v, str) or not v.strip():
            problems.append(f'missing Chinese: {prefix}.{f} ({where} has no text in field "{f}")')
            continue
        rows.append((f'{prefix}.{f}', v))


def collect():
    """Returns (rows [(key, zh)], covered {(id(record), field)}, problems)."""
    rows, covered, problems = [], set(), []
    tables = {}
    for file, path, cat, fields, nested in SPEC:
        tables.setdefault(file, _load(file))
        node = tables[file]
        for p in path:
            node = node[p]
        for i, rec in enumerate(node if isinstance(node, list) else [node]):
            rid = rec.get('id')
            where = f'{file} {"/".join(path)}[{i}]'
            if not rid:
                problems.append(f'{where}: record has no id')
                continue
            prefix = f'{cat}.{rid}'
            dyn = rec.get('dynamic_name')
            if dyn and '{' + dyn + '}' not in str(rec.get('name')):
                problems.append(f'{prefix}.name must contain the placeholder {{{dyn}}} (field dynamic_name is {dyn})')
            _fields(rec, fields, prefix, rows, covered, problems, where + f' {rid}')
            for sub_key, label, sub_fields in nested:
                for j, sub in enumerate(rec.get(sub_key) or []):
                    sid = sub.get('id', j)
                    _fields(sub, sub_fields, f'{prefix}.{label}.{sid}', rows, covered, problems, where + f' {rid} {sub_key}[{j}]')
    return rows, covered, problems, tables


def stray_chinese(tables, covered):
    """Chinese in a field that is not a display field."""
    out = []

    def walk(v, where):
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, str) and CJK.search(x) and (id(v), k) not in covered:
                    out.append(f'{where}.{k}: Chinese text outside the display fields: {x[:30]}')
                else:
                    walk(x, f'{where}.{k}')
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str) and CJK.search(x):
                    out.append(f'{where}[{i}]: Chinese text outside the display fields: {x[:30]}')
                else:
                    walk(x, f'{where}[{i}]')
    for file in sorted(os.listdir(DATA)):
        if file.endswith('.json'):
            walk(tables.get(file) or _load(file), file)
    return out


def read_csv():
    """Returns ({key: (zh, en)}, duplicate keys, header problem or None)."""
    old, dup = {}, []
    if not os.path.exists(CSV_PATH):
        return old, dup, None
    with open(CSV_PATH, encoding='utf-8', newline='') as fh:
        rd = csv.reader(fh)
        head = next(rd, None)
        if head != ['key', 'zh_CN', 'en']:
            return old, dup, f'text.csv header must be key,zh_CN,en, found {head}'
        for row in rd:
            if len(row) != 3:
                return old, dup, f'text.csv: a row has {len(row)} columns: {row[:1]}'
            if row[0] in old:
                dup.append(row[0])
            old[row[0]] = (row[1], row[2])
    return old, dup, None


def read_basis():
    if os.path.exists(BASIS_PATH):
        with open(BASIS_PATH, encoding='utf-8') as fh:
            return json.load(fh)
    return {}


def sync(prune=False, write=True):
    """Regenerates text.csv from the tables. Returns (errors, notes).
    Errors: missing Chinese, duplicate keys, extra keys (unless prune), stale English, stray Chinese."""
    rows, covered, errors, tables = collect()
    old, dup, bad = read_csv()
    if bad:
        errors.append(bad)
    seen = {}
    for k, _ in rows:
        seen[k] = seen.get(k, 0) + 1
    errors += [f'duplicate key in the tables: {k} (two records with the same id?)' for k, n in seen.items() if n > 1]
    errors += [f'duplicate key in text.csv: {k}' for k in dup]
    errors += stray_chinese(tables, covered)

    keys = {k for k, _ in rows}
    extra = [k for k in old if k not in keys]
    if extra and not prune:
        errors += [f'extra key in text.csv (no such record any more): {k}' for k in extra]
        errors.append('  run: python3 tools/extract_text.py --prune   (drops them together with their English)')

    basis = read_basis()
    out, stale, added, changed = [], [], 0, 0
    for k, zh in rows:
        was_zh, en = old.get(k, (None, ''))
        if was_zh is None:
            added += 1
        elif was_zh != zh:
            changed += 1
        if en:
            basis.setdefault(k, zh)
            if basis[k] != zh:
                stale.append(k)
        out.append((k, zh, en))
    errors += [f'stale translation (the Chinese changed): {k}' for k in stale]
    if stale:
        errors.append('  edit the en column of text.csv, then: python3 tools/extract_text.py --ack <key or prefix>')
    basis = {k: v for k, v in basis.items() if k in keys}

    notes = []
    if added or changed or (prune and extra):
        notes.append(f'text.csv updated: {added} new, {changed} changed, {len(extra) if prune else 0} removed')
    missing_en = [k for k, _, en in out if not en]
    if missing_en:
        by_cat = {}
        for k in missing_en:
            by_cat[k.split('.')[0]] = by_cat.get(k.split('.')[0], 0) + 1
        notes.append(f'{len(missing_en)} of {len(out)} lines have no English yet (shown as the key): '
                     + ', '.join(f'{c} {n}' for c, n in sorted(by_cat.items())))
    if write and not bad:
        os.makedirs(LOCALE, exist_ok=True)
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh, lineterminator='\n')
            w.writerow(['key', 'zh_CN', 'en'])
            w.writerows(out)
        with open(BASIS_PATH, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(basis, fh, ensure_ascii=False, indent=0, sort_keys=True)
            fh.write('\n')
    return errors, notes


def ack(prefixes):
    rows, _, _, _ = collect()
    basis = read_basis()
    n = 0
    for k, zh in rows:
        if any(k == p or k.startswith(p) for p in prefixes) and basis.get(k) != zh:
            basis[k] = zh
            n += 1
    with open(BASIS_PATH, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(basis, fh, ensure_ascii=False, indent=0, sort_keys=True)
        fh.write('\n')
    print(f'acknowledged {n} keys')


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    if argv and argv[0] == '--ack':
        ack(argv[1:])
    errors, notes = sync(prune='--prune' in argv)
    print('\n'.join(notes + errors))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
