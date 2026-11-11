"""Build data/tables/*.json from the game files (PM2.EXE + decoded scripts in data/scripts).
usage: python3 tools/extract_tables.py game_sample/PM2 data/scripts data/tables"""
import sys, os, re, json, glob, struct
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from logic_view import logic_lines
from pm2sim.vm import DS_SEG, EXE_HEADER, SYM_NAMES_OFF, SYM_PTRS_OFF
from pm2sim.save import BLOCKS

ZH = dict(B_TAIRYOKU='體力', B_KINRYOKU='腕力', B_CHINOH='智力', B_KIHIN='氣質', B_IROKE='魅力', B_MORALS='道德',
    B_SHINKOH='信仰', B_INGYO='罪孽', B_KANJUSEI='感受', B_STRESS='疲勞', H_SENSHI='戰士評價', H_MAHO='魔法評價',
    H_SYAKOH='社交評價', H_KAJI='家事評價', V_SENTOH='戰鬥技術', V_KOUGEKI='攻擊能力', V_BOUGYO='防禦能力',
    V_MAHOGIJUTSU='魔法技術', V_MARYOKU='魔法能力', V_KOHMARYOKU='抗魔能力', V_REIGI='禮儀表現', V_GEIJYUTSU='藝術修養',
    V_WAJYUTU='談話技巧', V_RYOURI='烹飪技術', V_SOUJISENTAKU='掃除洗衣', V_KIDATE='待人接物',
    GOLD_GIRL='金錢(32位)', NAME_FIRST='女兒名(指標)', NAME_FAMILY='姓氏(指標)', P_BLOOD='血型', P_NENREI='年齡([1]=父親)',
    P_BORTHDAY='生日-日', P_BORTHMONTH='生日-月', P_BORTHYEAR='生日-年', P_SHIKYU='星座', P_SYUGOSEI='守護星',
    P_SHINCHO='身高x100', P_TAIJYU='體重x100', P_BUST='胸圍x100', P_WAIST='腰圍x100', P_HIP='臀圍x100',
    W_HP_MAX='HP上限', W_MP_MAX='MP上限', W_HP='HP', W_MP='MP', W_SENI='戰意', S_BYOUKI='疾病指數', S_HIKOUKA='不良指數',
    S_JINMYAKU='人脈', FLAG_BYOUKI='生病旗標', FLAG_HIKOUKA='不良旗標', FLAG_RENAI='戀愛旗標', FLAG_KENKO='飲食方針',
    GIRL_BODY='體型(2=肥胖)', GIRL_FACE='表情', GIRL_BREAST='胸型圖', GIRL_DAMEG='重病', RUN_OSHIRO='王城拜訪次數[]',
    RUN_MACHI='街道次數[]', RUN_TALK='談話次數[]', RUN_KENKOH='健康次數[]', RUN_SYUGOSEI='守護神次數[]',
    RUN_KITAERU='上課次數[]', RUN_ARBEIT='打工次數[]', GRA_ARBEIT='打工薪資等級[]', RUN_MUSYA='武者修行次數[]',
    RUN_BACANCE='度假次數[]', RUN_SYUKAKUSAI='收穫祭紀錄[]', RUN_MONTH='月份/事件計數[]', URA_BREAST_TYPE='隱藏:胸型',
    URA_HIP_TYPE='隱藏:臀型', URA_PRINCE='隱藏:王子好感', URA_FATHER='隱藏:父女關係', URA_STEWARD='隱藏:管家好感',
    URA_MOTHER_LOVE='隱藏:母性', URA_KILL_MONSTR='隱藏:殺怪數', E_RIVAL='事件:對手', E_KAISIN='會心一擊武器',
    E_PROPOSAL='事件:求婚', E_RWAY='離家出走中', E_ETC='雜項事件旗標[]', VAL_YEAR='年', VAL_MONTH='月', VAL_WEEK='星期(0=日)',
    VAL_DAY='日', TM_SEASON='季節(1春2夏3秋4冬)', T_SENTOH='戰鬥技術(訓練值)', T_KOUGEKI='攻擊(訓練值,含腕力/10)',
    T_BOUGYO='防禦(訓練值)', T_MAHOGIJUTSU='魔法技術(訓練值)', T_MARYOKU='魔力(訓練值)', T_KOHMARYOKU='抗魔(訓練值)',
    T_REIGI='禮儀(訓練值)', T_GEIJYUTSU='藝術(訓練值)', T_WAJYUTU='談話(訓練值)', T_RYOURI='烹飪(訓練值)',
    T_SOUJISENTAKU='掃除洗衣(訓練值)', T_KIDATE='待人接物(訓練值)', ITEM_MAX='持有物數量', ROOM_PIC='房間圖', DRESS_NUM='服裝編號')

def variables(exe):
    file_off = {}; p = 0x3A + 2
    for a, n in BLOCKS:
        p += 2
        for k in range(n): file_off[a + 2*k] = p; p += 2
    out = []; a = SYM_NAMES_OFF; i = 0
    while exe[a]:
        n = exe[a]; name = exe[a+1:a+1+n].decode(); a += 1 + n
        off, seg = struct.unpack_from('<HH', exe, SYM_PTRS_OFF + i*4); i += 1
        kind = 'variable' if seg == DS_SEG else 'command'
        e = dict(name=name, kind=kind, address='%04X:%04X' % (seg, off))
        if name in ZH: e['zh'] = ZH[name]
        if kind == 'variable' and off in file_off: e['save_offset'] = file_off[off]
        out.append(e)
    return out

def read(path): return open(path, encoding='utf-8').read()
def indent(l): return len(l) - len(l.lstrip('\t'))

def levels(lines):
    lv = {}; cur = None
    for l in lines:
        m = re.match(r'\t*IF \( NOW_LEVEL = (\d) \)', l)
        if m: cur = int(m.group(1)); lv[cur] = {}; continue
        if cur is not None and indent(l) >= 1:
            for k, v in re.findall(r'([A-Z_]+) ?= ?(-?\d+)', l): lv[cur][k] = int(v)
        elif indent(l) == 0: cur = None
    return [lv[k] for k in sorted(lv)]

def classes(sd):
    out = []
    for f in sorted(glob.glob(sd + '/TXTR/TRG0*.TXT')):
        src = read(f); main = re.search(r'^\*(R_[A-Z_0-9]+)', src, re.M).group(1)
        L = logic_lines(f, {main}); lv = levels(L); eff = []
        for i, l in enumerate(L):
            m = re.search(r'IRAND2\(X_([A-Z]+),W_([A-Z]+)\)', l)
            if m and i + 1 < len(L):
                m2 = re.search(r'([A-Z]_[A-Z]+) ?([+-])= ?AX', L[i+1])
                if m2: eff.append(dict(stat=m2.group(1), zh=ZH.get(m2.group(1), ''), sign=m2.group(2), key=m.group(1)))
        for e in eff:
            e['range_by_level'] = [[v.get('X_' + e['key'], 0), v.get('W_' + e['key'], 0)] for v in lv]; del e['key']
        fixed = [l.strip() for l in L if re.match(r'\t+(B_|URA_)[A-Z_]+ ?(\+\+|--|[+-]=)', l) and 'AX' not in l]
        out.append(dict(id=int(f[-7:-4]), file=os.path.basename(f), name=re.search(r'TITLES="([^"]*)"', src).group(1),
                        cost_per_day_by_level=[v.get('USE_GOLD') for v in lv], level_thresholds='times<=5:0, <=10:1, <=15:2, else 3 (CK_LVL 0000:03D6)',
                        success_effects=eff, daily_effects=fixed,
                        success_check=[l.strip() for l in logic_lines(f, {'SUCCESS_CHK'})][1:-1]))
    return out

def jobs(sd):
    out = []
    for f in sorted(glob.glob(sd + '/TXJO/JOB0*.TXT')):
        src = read(f); main = re.search(r'^\*(R_[A-Z_0-9]+)', src, re.M).group(1)
        L = logic_lines(f, {main})
        e = dict(id=int(f[-7:-4]), file=os.path.basename(f), name=re.search(r'TITLES="([^"]*)"', src).group(1))
        m = re.search(r'GUARA_BASE ?= ?(\d+)', '\n'.join(L)); e['base_wage'] = int(m.group(1)) if m else 0
        e['wage_ranks'] = 'times worked <10:x1, <30:+20%, <60:+44%, <90:+73%, else +108% (CK_GUARA 0000:0429)'
        keep = re.compile(r'(B_|T_|V_|H_|URA_|S_|E_|P_|FLAG_|IRAND|RANDAM|IRNDPAR|SUCCESS_|IF|C[1-8] ?[-+*/]?=|P1X100|GUARA_ALL|GOLD|RUN_|LOAD|CK_|CHK_|CLENDER|RET)')
        e['rules'] = [l for l in L if keep.match(l.strip()) and 'BORTH' not in l and 'DAY_COUNTER' not in l]
        for lab in ('CHK_RENAI', 'CHK_HIKOUKA'):
            r = [l for l in logic_lines(f, {lab})]
            if len(r) > 2: e[lab] = r[1:]
        out.append(e)
    return out

def items(sd):
    out = []; seen = set()
    for f in sorted(glob.glob(sd + '/*/*.TXT')):
        if '/TXTX/' in f: continue
        cur = {}
        def flush():
            if cur.get('name') and (cur['name'], cur.get('price')) not in seen:
                seen.add((cur['name'], cur.get('price'))); out.append(dict(cur, file=os.path.basename(f)))
            cur.clear()
        for l in open(f, encoding='utf-8'):
            s = l.strip()
            m = re.match(r'ITEMID_TBL([1-7])\[[A-Z0-9]+\] ?= ?(?:"([^"]*)"|(-?\d+))', s)
            if m:
                k = int(m.group(1))
                if k == 1: flush()
                key = {1: 'name', 2: 'icon', 3: 'price', 4: 'help', 5: 'tbl5', 6: 'tbl6', 7: 'tbl7'}[k]
                cur[key] = m.group(2) if m.group(2) is not None else int(m.group(3)); continue
            m = re.match(r'ITEM_(KOUKA|ATTRBUTE)\[[A-Z0-9]+\] ?= ?(?:"([^"]*)"|(-?\d+))', s)
            if m and cur: cur['effect' if m.group(1) == 'KOUKA' else 'attr'] = m.group(2) if m.group(2) is not None else int(m.group(3))
        flush()
    return out

def monsters(sd):
    out = []
    for f in sorted(glob.glob(sd + '/TXRP/RP[ZY]*N.TXT')):
        L = logic_lines(f); e = dict(file=os.path.basename(f), kind='monster' if 'RPZ' in f else 'person'); rng = None
        for l in L:
            s = l.strip()
            m = re.match(r'RDM\((\d+),(\d+)\)', s)
            if m: rng = [int(m.group(1)), int(m.group(2))]; continue
            m = re.match(r'(R_[A-Z_]+) ?= ?(?:"([^"]*)"|(-?\d+)|AX)$', s)
            if m and m.group(1) not in e:
                e[m.group(1)] = m.group(2) if m.group(2) is not None else int(m.group(3)) if m.group(3) else rng
        if len(e) > 3: out.append(e)
    return out

def labelled(f, pat):
    res = {}; cur = None
    for l in logic_lines(f):
        if l.startswith('*'):
            cur = l[1:].split()[0]
            if re.match(pat, cur): res[cur] = []
            else: cur = None
            continue
        if cur: res[cur].append(l)
    return res

def zodiac(sd):
    src = read(sd + '/TXRT/PARAINIT.TXT'); tabs = {}
    for name, vals in re.findall(r'\.Q_([A-Z]+)\[12\]\s*=\s*([-0-9,\s]+)', src):
        tabs[name] = [int(x) for x in vals.replace('\n', ' ').split(',') if x.strip()]
    L = logic_lines(sd + '/TXRT/PARAINIT.TXT')
    return dict(initial_by_sign=tabs, rules=[l for l in L if re.search(r'P_SHIKYU|P_SYUGOSEI|P_BORTH|URA_|P_SHINCHO|P_TAIJYU|P_BUST|P_WAIST|P_HIP|RANDAM|P1X100|GOLDADD|FLAG_KENKO|C1 ?=', l)])

if __name__ == '__main__':
    game, sd, dst = sys.argv[1:4]; os.makedirs(dst, exist_ok=True)
    exe = open(os.path.join(game, 'PM2.EXE'), 'rb').read()
    endings = dict(titles={os.path.basename(f)[:-4]: (re.search(r'TTL\$\("([^"]*)"\)', read(f)) or [None, ''])[1]
                           for f in sorted(glob.glob(sd + '/TXEE/EE*.TXT'))},
                   rules=labelled(sd + '/TXEE/EECALC.TXT', r'.*'))
    events = {}
    for name in ('MAINEVNT', 'RUNNING', 'MAINBORN', 'MAINLOOP'):
        events[name] = labelled('%s/TXRT/%s.TXT' % (sd, name), r'(EVENT|EVNT|BORTH|CALC_|FAT_|VACA_|MAINBORN|CHK_)')
    tables = dict(variables=variables(exe), classes=classes(sd), jobs=jobs(sd), items=items(sd), monsters=monsters(sd),
                  zodiac=zodiac(sd), endings=endings, events=events)
    for k, v in tables.items():
        json.dump(v, open(os.path.join(dst, k + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(k, len(v))
