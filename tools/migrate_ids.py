"""One-off migration (PLAN step 9c-1): rewrite data/new/*.json and tools/trace_cases.json from Chinese names to
English ids.  Everything is driven by tools/i18n_map.json (the Chinese names live only there).

What it changes:
  * field names (keys of every JSON object) -> English snake_case
  * identifiers inside values: attribute / skill / road / NPC / tag / item / flag ... names, the variable names in
    conditions, the names in effect strings (``stamina+20``, ``favor.sil+5``, ``flag.member=1``)
  * records that used their Chinese name as the id get an English ``id`` plus the Chinese ``name``
  * developer notes (``note``, ``source`` ...) are replaced by their English translation (map section ``notes``)
  * the rows of items.json are put in the old sort order (see ``migrate``), the easter-egg rival gets a flag,
    roles.json gets a ``tags`` table (id + Chinese name)
Display fields (``name``, ``text``, ``body``, ``question``, ``film_title`` ...) keep their Chinese original.

The data files are English after the migration, so running it again fails; it stays in the repository as a record
of what was renamed.  ``--glossary`` writes design/GLOSSARY.md from the map and can be run at any time.

    python3 tools/migrate_ids.py [--dry]     # rewrite the files (--dry only reports problems)
    python3 tools/migrate_ids.py --glossary  # regenerate design/GLOSSARY.md
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CJK = re.compile(r'[\u4e00-\u9fff]')
TOKEN = re.compile(r'[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff·]*')
PREV_TOKEN = re.compile(r'([A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff·]*)$')


class Mapper:
    def __init__(self, path):
        m = json.load(open(path, encoding='utf-8'))
        self.F = m['field']                 # dict keys
        self.TOP = m['top']                 # top-level keys per file
        self.tag_ids = m['ids']['tag']
        self.V = {}                         # identifiers in values (and keys that are ids)
        for sec in m['ids'].values():
            for z, e in sec.items():
                self.V.setdefault(z, e)
        self.P = m['prefix']                # prefixes of dotted names
        self.C = m['counter']               # second segment of count.<...>
        self.CV = m['class_value']          # values of the class / slot fields
        self.X = m['exact']                 # whole-string replacements
        self.N = m['notes']                 # developer-note translations
        c = m['migrate']
        self.display = set(c['display_keys'])
        self.note_keys = set(c['note_keys'])
        self.period = c['period']
        self.c = c
        self.errors = []
        self.jobname = {}

    def err(self, where, s):
        self.errors.append((where, s))

    # ---- keys ----
    def key(self, k, file, depth, v):
        if depth == 0 and k in self.TOP.get(file, {}):
            return self.TOP[file][k]
        if k == self.c['sick_key'] and isinstance(v, str):
            return 'when_sick'
        if k in self.F:
            return self.F[k]
        if k in self.V:
            return self.V[k]
        if CJK.search(k):
            self.err(file + ' key', k)
        return k

    # ---- structured strings (effects, conditions, ids) ----
    def sub(self, s, where):
        def rep(m):
            t = m.group(0)
            before, after = s[:m.start()], s[m.end():m.end() + 1]
            prev = None
            if before.endswith('.'):
                pm = PREV_TOKEN.search(before[:-1])
                prev = pm.group(1) if pm else None
            if prev is None and after == '.' and t in self.P:
                return self.P[t]
            if prev == self.c['count_prefix'] and t in self.C:
                return self.C[t]
            if t in self.V:
                return self.V[t]
            return t
        out = TOKEN.sub(rep, s)
        if CJK.search(out):
            self.err(where, s)
        return out

    def value(self, k, v, where):
        if isinstance(v, str):
            if k in self.display and not v.startswith('null='):      # display text stays Chinese
                return None if v == self.c['blank'] else v
            if v in self.N:
                return self.N[v]
            if v in self.X:
                x = self.X[v]
                return None if x == '__null__' else x
            if not CJK.search(v):
                return self.sub(v, where) if v in self.V else v
            if k in self.note_keys:
                self.err(where + ' note', v)
                return v
            if k == self.c['met_via_key'] and v in self.jobname:
                return self.jobname[v]
            if k in self.c['class_keys'] and v in self.CV:
                return self.CV[v]
            return self.sub(v, where)
        return v

    # ---- walk ----
    def walk(self, o, file, depth, pk, path):
        name_key, note_key = self.c['name_key'], self.c['note_key']
        if isinstance(o, dict):
            out = {}
            rec_name = o.get(name_key)
            for k, v in o.items():
                nk = self.key(k, file, depth, v)
                if k == 'id':
                    out['id'] = self.rec_id(file, v, rec_name, path)
                    continue
                if k == self.c['periods_key'] and isinstance(v, list) and v and isinstance(v[0], str):
                    out[nk] = [self.period[x] for x in v]
                    continue
                if nk in out:
                    self.err(file + path, f'key collision: {k} -> {nk}')
                out[nk] = self.walk(v, file, depth + 1, k, path + '/' + k)
            if file == 'rivals' and str(o.get(note_key, '')).startswith(self.c['egg_prefix']):
                out['easter_egg'] = True        # code used to test the first word of the note
            if name_key in o and 'id' not in o:
                nid = self.V.get(rec_name) or self.F.get(rec_name)
                if nid is None:
                    self.err(file + path + ' (no id for record)', rec_name)
                    nid = rec_name
                out = {'id': nid, **out}
            return out
        if isinstance(o, list):
            return [self.walk(x, file, depth, pk, path) for x in o]
        return self.value(pk, o, file + path)

    def rec_id(self, file, old, rec_name, path):
        if isinstance(old, str) and CJK.search(old):          # item / chain ids: id == Chinese name
            return self.X.get(old) or self.V.get(old) or self.err(file + path, old) or old
        if file == self.c['stats_file'] and rec_name:         # pinyin / numeric placeholder ids
            return self.V.get(rec_name) or self.F.get(rec_name) or old
        return old


def migrate(dry):
    mp = Mapper(os.path.join(ROOT, 'tools', 'i18n_map.json'))
    c = mp.c
    docs = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'new', '*.json'))):
        docs[os.path.basename(f)[:-5]] = json.load(open(f, encoding='utf-8'))
    mp.jobname = {j[c['name_key']]: j['id'] for j in docs['jobs'][c['jobs_top']]}
    trace_path = os.path.join(ROOT, 'tools', 'trace_cases.json')
    docs['trace_cases'] = json.load(open(trace_path, encoding='utf-8'))
    out = {n: mp.walk(d, n, 0, '', '') for n, d in docs.items()}
    # Row order of items.json is significant (ties between items go to the earlier row).  Before the migration the
    # code sorted by the Chinese id; keep exactly that order so the simulation results do not change.
    old_order = {mp.V[i['id']]: n for n, i in enumerate(sorted(docs['items'][c['items_top']], key=lambda i: i['id']))}
    out['items']['items'].sort(key=lambda i: old_order[i['id']])
    # film tags had no record of their own; give them one (id + Chinese name) so that they have a display name
    r = out['roles']
    out['roles'] = {'note': r['note'], 'tags': [{'id': e, 'name': z} for z, e in mp.tag_ids.items()],
                    'roles': r['roles'], 'defaults': r['defaults']}
    if mp.errors:
        seen = set()
        for w, s in mp.errors:
            if (w, s) not in seen:
                seen.add((w, s))
                print('UNMAPPED', w, '|', s)
        print(len(seen), 'problems; nothing written')
        return 1
    if not dry:
        for n, d in out.items():
            path = trace_path if n == 'trace_cases' else os.path.join(ROOT, 'data', 'new', n + '.json')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(dump(d, n) + '\n')
        print('rewrote', len(out), 'files')
    return 0


def dump(d, name):
    """data/new/*.json: indent 1 (what tools/check.py expects); trace_cases.json: one step per line."""
    if name != 'trace_cases':
        return json.dumps(d, ensure_ascii=False, indent=1)

    def fmt(o, ind):
        pad = ' ' * ind
        if isinstance(o, dict):
            if not o:
                return '{}'
            return '{\n' + ',\n'.join(f'{pad} {json.dumps(k, ensure_ascii=False)}: {fmt(v, ind + 1)}'
                                       for k, v in o.items()) + '\n' + pad + '}'
        if isinstance(o, list) and o and any(isinstance(x, (dict, list)) for x in o) and ind < 3:
            return '[\n' + ',\n'.join(f'{pad} {fmt(x, ind + 1)}' for x in o) + '\n' + pad + ']'
        return json.dumps(o, ensure_ascii=False)
    return fmt(d, 0)


def glossary():
    m = json.load(open(os.path.join(ROOT, 'tools', 'i18n_map.json'), encoding='utf-8'))
    cat_title = {
        'attr': 'Base attributes', 'skill': 'Skills', 'road': 'Roads (reputation)', 'npc': 'NPCs',
        'tag': 'Film tags', 'tag_family': 'Tag families', 'street': 'Street entries', 'service': 'Street services',
        'item': 'Items', 'index': 'Indices', 'status': 'Status flags (state.status)', 'derived': 'Derived variables',
        'flag': 'Flags (flag.<id>)', 'enum': 'Enumerated values', 'fame_tier': 'Fame tiers',
        'book_tier': 'Book tiers', 'category': 'Ending categories', 'misc': 'Other values',
        'internal': 'Internal keys and values (state, saves, bots, trace)',
    }
    lines = ['# Glossary: Chinese name | id | category', '',
             'Generated from `tools/i18n_map.json` (`python3 tools/migrate_ids.py --glossary`). Ids are the English',
             'snake_case names used in data, code, saves and effect/condition strings; Chinese appears only in display',
             'fields (`name`, `text`, `body`, ...). The design documents (GDD, DESIGN_NOTES ...) still use the Chinese',
             'names; look them up here. Source tags in notes: `[orig ...]` original game, `[inferred N..]` was',
             '`[\u63a8N..]` (inferred, see DESIGN_NOTES), `[user]` was `[\u7528]` (user decision), `[user material]` was',
             '`[\u7528\u7d20\u6750]`.', '',
             '## Name prefixes in effects and conditions', '', '| Chinese | id | category |', '|---|---|---|']
    lines += [f'| {z}. | `{e}.` | prefix |' for z, e in m['prefix'].items()]
    lines += ['', '## Second segment of `count.<...>`', '', '| Chinese | id | category |', '|---|---|---|']
    lines += [f'| {z} | `{e}` | counter |' for z, e in m['counter'].items()]
    for sec, title in cat_title.items():
        if sec not in m['ids']:
            continue
        lines += ['', f'## {title}', '', '| Chinese | id | category |', '|---|---|---|']
        lines += [f'| {z} | `{e}` | {sec} |' for z, e in m['ids'][sec].items()]
    lines += ['', '## Item class / slot values', '', '| Chinese | id | category |', '|---|---|---|']
    lines += [f'| {z} | `{e}` | class |' for z, e in m['class_value'].items()]
    lines += ['', '## Field names (JSON keys)', '', '| Chinese | id | category |', '|---|---|---|']
    lines += [f'| {z} | `{e}` | field |' for z, e in m['field'].items()]
    for fl, d in m['top'].items():
        lines += [f'| {z} (`{fl}.json` top level) | `{e}` | field |' for z, e in d.items()
                  if m['field'].get(z) != e]
    with open(os.path.join(ROOT, 'design', 'GLOSSARY.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--glossary', action='store_true')
    a = ap.parse_args()
    if a.glossary:
        glossary()
    else:
        sys.exit(migrate(a.dry))
