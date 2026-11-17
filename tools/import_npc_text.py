"""Builds data/new/npc_events.json and data/new/npc_lines.json from design/NPC_TEXT.md (the planner's text draft).
Usage: python3 tools/import_npc_text.py
The markdown stays the place where the text is edited; run this again after every edit. Hand-written parts (the encounter schedule,
the conditions the markdown only describes in words) live in data/new/npc_encounters.json and in COND below."""
import json, os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'design', 'NPC_TEXT.md')
OUT_EV = os.path.join(ROOT, 'data', 'new', 'npc_events.json')
OUT_LN = os.path.join(ROOT, 'data', 'new', 'npc_lines.json')

NPC = {'诺瓦': 'novaro', '库普': 'cooper', '甜心': 'sweetheart', '蛇蝎': 'vamp', '舞池女王': 'dancequeen', '女王': 'diva',
       '冰山': 'iceberg', '吉尔伯': 'gilbert', '圣女': 'saint', '飞行女郎': 'aviator'}
STAGE = {'前期': 'early', '中期': 'mid', '后期': 'late'}
STAGE_ZH = {'early': '前期', 'mid': '中期', 'late': '后期'}
# flags the markdown names in Chinese quotes
FLAG_ZH = {'替你背过锅': 'novaro.carried_blame', '去过皮克费尔': 'pickfair', '验过珍珠': 'negri.pearl'}
# anchors fixed by the user (2026-11): not bound to the casting-board months, only for players in the line
ANCHOR_FIX = {('dancequeen', 5): '1927-10', ('aviator', 3): '1928-01'}
# conditions the markdown gives only in words: (npc, kind, option label start) -> condition
def C(*inner): return [[list(x) for x in inner]]
COND = {
    '有“去过皮克费尔”标记才出现': C(('flag.pickfair', '>=', 1)),
    '有“验过珍珠”标记才出现': C(('flag.negri.pearl', '>=', 1)),
    '好感 45 以上才出现': None,      # filled per NPC below
    '只有冰山线 active 时出现': C(('line.iceberg', '==', 'active')),
}
TAG = re.compile(r'（([^（）]*)）\s*$')


def favor_cond(npc, n): return C((f'favor.{npc}', '>=', n))


def parse_tags(npc, s):
    """The trailing （+5，人样−，标记 x） group -> (effect string, line action, extra effects)."""
    eff, line = [], None
    for tok in [t.strip() for t in s.split('，')]:
        m = re.fullmatch(r'([+＋−\-])(\d+)', tok)
        if m:
            sign = '+' if m.group(1) in '+＋' else '-'
            if int(m.group(2)):
                eff.append(f'favor.{npc}{sign}{m.group(2)}')
            continue
        if tok in ('人样−', '人样-'): eff.append('renyang-1')
        elif tok in ('人样＋', '人样+'): eff.append('renyang+1')
        elif tok == '光−': eff.append(f'flag.{npc}.light-1')
        elif tok == '颜值−': eff.append('looks-20')
        elif tok.startswith('标记'):
            f = tok[2:].strip().strip('“”')
            f = FLAG_ZH.get(f, f)
            eff.append(f'flag.{f}=1')
        elif tok == '越线': line = 'active'
        elif tok == '停在同事': line = 'stay'
        elif tok == '搞砸': line = 'botched'
        elif tok == '线结束': line = 'end'
        elif tok: return None, None     # not a tag group
    return ' '.join(eff), line


def parse_option(npc, text):
    """'A「label」：result（tags）' -> option dict."""
    body = re.sub(r'^[ABC]\s*', '', text.strip())
    eff, line = '', None
    cond = None
    m = TAG.search(body)
    if m:
        e, l = parse_tags(npc, m.group(1))
        if e is not None:
            eff, line = e, l
            body = body[:m.start()].rstrip()
    # a condition note right after the label: （好感 45 以上才出现）
    cm = re.search(r'（([^（）]*(才出现|时出现))）', body)
    if cm:
        key = cm.group(1)
        if key == '好感 45 以上才出现': cond = favor_cond(npc, 45)
        else: cond = COND.get(key)
        body = body.replace(cm.group(0), '')
    if '：' in body:
        label, result = body.split('：', 1)
    else:
        label, result = body, ''
    o = {'text': label.strip(), 'check': None, 'success_effect': eff, 'fail_effect': ''}
    if result.strip(): o['result'] = result.strip()
    if cond: o['cond'] = cond
    if line: o['line'] = line
    return o


def event(eid, npc, typ, name, body, options, stage=None, **extra):
    e = {'id': eid, 'name': name, 'npc': npc, 'type': typ, 'body': body, 'cond': [], 'freq': None, 'once': True,
         'effect': '', 'options': options}
    if stage: e['stage'] = stage
    e.update(extra)
    return e


def main():
    lines = open(SRC, encoding='utf-8').read().split('\n')
    events, npc_lines = [], {}
    npc = zh = sect = None
    cur = None            # current text block: dict(label, body, opts)
    blocks = []
    def flush():
        nonlocal cur
        if cur is not None: blocks.append((npc, zh, sect, cur))
        cur = None
    for raw in lines:
        s = raw.rstrip()
        if s.startswith('## '):
            flush(); zh = s[3:].strip(); npc = NPC.get(zh); sect = None
            if npc: npc_lines[npc] = {'name': zh, 'type': 'accept', 'ending': {'override': [], 'tier': {}, 'variant': []}, 'showdown': {}}
            continue
        if npc is None: continue
        if s.startswith('### '):
            flush(); sect = s[4:].strip(); continue
        if s.startswith('**好感逻辑**'):
            m = re.search(r'修罗场类型：([\w\\]+)', s)
            if m: npc_lines[npc]['type'] = m.group(1).replace('\\', '')
            continue
        if sect is None or not s.strip(): continue
        m = re.match(r'\*\*(.+?)\*\*[：:]?(.*)$', s)
        if m and not s.startswith('- '):
            flush(); cur = {'label': m.group(1), 'body': m.group(2).strip(), 'opts': [], 'extra': []}
            if m.group(1) in ('标记覆盖（优先）', '按状态'): cur['body'] = ''
            continue
        if s.startswith('- '):
            if cur is None: cur = {'label': '', 'body': '', 'opts': [], 'extra': []}
            cur['opts'].append(s[2:].strip()); continue
        # a plain paragraph: the text of a block without a bold label (party, year-end, crossline), or an extra line
        if cur is None:
            cur = {'label': '', 'body': s.strip(), 'opts': [], 'extra': []}
        elif cur['opts']:
            cur['extra'].append(s.strip())
        else:
            cur['body'] = (cur['body'] + '\n' + s.strip()).strip()
    flush()
    for npc, zh, sect, b in blocks:
        L = npc_lines[npc]
        label, body, opts = b['label'], b['body'], b['opts']
        if sect.startswith('结算'):
            for t in opts:
                k, _, v = t.partition('：')
                k = k.strip()
                if k.startswith('变体'):
                    L['ending']['variant'].append({'flag': re.search(r'（(.+?)）', k).group(1), 'text': v.strip()})
                elif k in ('红了', '糊了', '进去了', '回码头', '犯罪皇帝'):
                    L['ending']['tier'][k] = v.strip()
                else:
                    L['ending']['override'].append({'flags': [x.strip() for x in k.split('且')], 'text': v.strip()})
            continue
        if sect.startswith('修罗场'):
            for t in opts:
                k, _, v = t.partition('：')
                L['showdown'][k.strip()] = v.strip()
            continue
        os_ = [parse_option(npc, t) for t in opts]
        if sect.startswith('戏中寒暄'):
            key = {'对手戏（他赢）': 'rival_win', '对手戏（你赢）': 'rival_lose', '对手戏（他输了）': 'rival_lose', '对手戏（你输了）': 'rival_win', '搭档戏': 'costar', '合作 1': 'costar_1', '合作 2': 'costar_2', '合作': 'costar_1'}.get(label)
            if key is None: print('unknown film block', npc, label); continue
            kind = 'filmRival' if key.startswith('rival') else 'filmCostar'
            events.append(event(f'film_{npc}_{key}', npc, kind, f'{zh} · 戏中寒暄', body, os_))
        elif sect.startswith('偶遇'):
            st = STAGE[label[:2]]
            events.append(event(f'enc_{npc}_{st}', npc, 'encounter', f'{zh} · 偶遇（{STAGE_ZH[st]}）', body, os_, stage=st))
        elif sect.startswith('派对'):
            events.append(event(f'party_{npc}_1', npc, 'party', f'{zh} · 派对', body, os_))
        elif sect.startswith('年度聚会'):
            events.append(event(f'yearend_{npc}_1', npc, 'yearEnd', f'{zh} · 年度聚会', body, os_))
        elif sect.startswith('越线'):
            events.append(event(f'cross_{npc}', npc, 'crossLine', f'{zh} · 越线', body, os_, beat=1))
        elif sect.startswith('线内拍'):
            m = re.match(r'第 (\d) 拍 · (.+)$', label)
            if not m: print('unknown beat', npc, label); continue
            n, title = int(m.group(1)), m.group(2)
            am = re.search(r'（锚点 (\d{4}-\d{2})', title)
            anchor = ANCHOR_FIX.get((npc, n)) or (am.group(1) if am else None)
            title = re.sub(r'（[^）]*）', '', title).strip()
            extra = {}
            eff = ''
            for x in b['extra']:
                fm = re.search(r'（标记 ([\w.]+)）', x)
                if fm: eff += f'flag.{fm.group(1)}=1'
            if npc == 'iceberg' and n == 5: eff = (eff + ' looks-20').strip()      # user: the punch really costs 20 looks
            if anchor: extra['anchor'] = anchor
            e = event(f'beat_{npc}_{n}', npc, 'beat', f'{zh} · 第 {n} 拍 · {title}', body, os_, beat=n, **extra)
            e['effect'] = eff
            events.append(e)
        else:
            print('skipped section', npc, sect)
    # texts for a person who has none yet (placeholders, no favor change)
    events.append(event('party_generic', None, 'party', '派对 · 寒暄', '你们寒暄了几句，没聊出什么特别的。', []))
    events.append(event('yearend_generic', None, 'yearEnd', '年度聚会 · 寒暄', '你们碰了碰杯，说了几句新年的话。', []))
    note = ('Generated by tools/import_npc_text.py from design/NPC_TEXT.md; edit the markdown, not this file. '
            'Option fields: text, result (shown after picking), cond, success_effect, line (active = cross the line, stay, botched, end).')
    json.dump({'note': note, 'enabled': True, 'events': events}, open(OUT_EV, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if '--lines' in sys.argv:    # showdown lines and ending rumors: switched on when the showdown / ending steps read them
        json.dump({'note': 'Generated by tools/import_npc_text.py: showdown lines and ending rumors per NPC.', 'npcs': npc_lines},
                  open(OUT_LN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(events), 'events,', len(npc_lines), 'npcs')


main()
