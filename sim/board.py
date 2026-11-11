"""选片板（GDD 3.3、6.1–6.5、11.1 的临时换角和抢角、11.3 瓦伦去世后的多一个角色）。数字在 roles.json 的 默认。

板上的一项（角色快照，st.story['板']['角色'] 里）：
    {'id', '名字', '档次', '名气门槛', '场风概率'(本次实际用的), '基础场风', '路', '看重', '标签', '加分技能',
     '有声', '谈吐线', '片酬', '女主', '对手': [对手…], '本厂', '来源', '情报': {…}}
'路' 是基础场风最高的那条路（上映时加声望修正用）。'情报' 只给界面用：标签/场风/习惯 是否显示，排除的一色。

组板的随机数顺序（Godot 照抄）：
  1. 按 大、中、小 抽角色：基本张数，再加人脉多出的中片、大片；1926-01 第二个小片位放教学角色。
     池里抽：下标 below(权重和)；池里没有合适的就生成占位角色：主色 below(4)、看重的技能 below(3)、标签 below(n)。
  2. 多出的角色依次是：待上板（剧本）、富婆投资的中片、转型的中片、瓦伦去世后的小片。
  3. 有声：1927-10 那块板 below(候选数) 选 1 个；之后每个候选 chance(百分比)。
  4. 对手：逐个角色按 对手 列表生成（无名对手见 audition.unnamed_rival；有名对手的瓦伦替换 below(2)；
     占位大片的有名对手按权重抽 below(10)）。
  5. 长约：在可报名的角色里 below 选 3 个标为本厂。
  6. 侍者情报：below(角色数) 选一个；告密：在中、大片里 below 选。
"""
from . import audition, film, rules

TIERS = ('小', '中', '大')
RANK = {'小': 0, '中': 1, '大': 2}


def cfg(d):
    return d.role_cfg['选片板']


def board(st):
    return st.story['板']


# ---------- 角色 ----------
def snapshot(st, r, src='池'):
    d = st.d
    df = d.role_cfg
    t = r['档次']
    probs = r['场风概率']
    return {'id': r['id'], '名字': r['名字'], '档次': t,
            '名气门槛': r['名气门槛'] if r.get('名气门槛') is not None else df['名气门槛'][t],
            '场风概率': list(probs) if probs else None, '基础场风': list(probs) if probs else None,
            '路': None, '看重': [dict(k) for k in r['看重']], '标签': list(r['标签']),
            '加分技能': r.get('加分技能') or df['加分技能'], '有声': r.get('有声'),
            '谈吐线': r.get('谈吐线'), '片酬': r.get('片酬') or df['片酬'][t], '女主': r.get('女主'),
            '对手规格': [dict(o) for o in r['对手']], '对手': [], '本厂': False, '来源': src, '情报': {}}


def set_probs(e, probs):
    e['场风概率'] = list(probs)
    e['基础场风'] = list(probs)
    e['路'] = None


def main_of(probs):
    return max(range(4), key=lambda c: (probs[c], -c))


def split_probs(main, top):
    """主色 top%，其余三色平分，除不尽的余数给顺序靠前的颜色。"""
    rest = 100 - top
    p = [rest // 3] * 4
    p[main] = top
    left = rest - rest // 3 * 3
    for c in range(4):
        if c != main and left:
            p[c] += 1
            left -= 1
    return p


def placeholder(st, tier, tags=None):
    """池里没有合适的角色时生成一个占位角色（roles.json 默认.占位生成）。"""
    d = st.d
    g = st.rng.logic
    c = d.role_cfg['占位生成']
    main = g.below(4)
    road = d.roads[main]
    sk = d.road_skills[road]
    skill = sk[g.below(len(sk))]
    pool = [t for t in (tags or c['标签按主色'][road])]
    tag = pool[g.below(len(pool))]
    probs = [c['其余场风']] * 4
    probs[main] = c['主色场风']
    st.story['序号'] += 1
    opp = [{'无名': True}] + ([{'有名占位': True}] if tier == '大' else [])
    r = {'id': f"gen{st.story['序号']}", '名字': f'占位角色（{tier}）', '档次': tier, '名气门槛': None,
         '场风概率': probs, '看重': [{'项': skill, '目标': c['看重目标'][tier]}], '标签': [tag],
         '加分技能': None, '有声': None, '谈吐线': None, '片酬': None, '对手': opp}
    return snapshot(st, r, '占位')


def in_years(st, r):
    y = int(st.date[:4])
    return r['出现年份'][0] <= y <= r['出现年份'][1]


def role_weight(st, r):
    w = sum(st.weights.get(t, 0) for t in r['标签'])
    return 1 + min(w, cfg(st.d)['权重上限'])


def draw(st, tier, taken, tags=None):
    """从池里按档次抽一个角色；没有就生成占位。小片按上板权重抽（6.1），其余等概率。"""
    d = st.d
    lim = cfg(d)['同角色上板上限'][tier]
    seen = st.story['上过板']
    cands = [r for r in d.roles.values()
             if r['档次'] == tier and not r.get('教学') and in_years(st, r) and r['id'] not in taken
             and seen.get(r['id'], 0) < lim and (tags is None or set(r['标签']) & set(tags))]
    if not cands:
        return placeholder(st, tier, tags)
    ws = [role_weight(st, r) if tier == '小' else 1 for r in cands]
    v = st.rng.logic.below(sum(ws))
    for r, w in zip(cands, ws):
        if v < w:
            return snapshot(st, r)
        v -= w
    raise AssertionError


def tutorial(st):
    d = st.d
    r = next(x for x in d.roles.values() if x.get('教学'))
    e = snapshot(st, r, '教学')
    set_probs(e, split_probs(audition.player_main(st), 60))
    e['对手规格'] = [{'无名': True, '主色等级': d.t['rivals']['教学']['主色等级']}]
    return e


# ---------- 对手 ----------
def named_for_placeholder(st, probs):
    """占位大片的第二场：当年在场（不含彩蛋）、该角色主色等级最高的 3 人里按 5:3:2 抽。"""
    d = st.d
    c = d.role_cfg['占位生成']['大片有名对手']
    main = main_of(probs)
    ids = [rid for rid, r in d.rivals_named.items() if not r.get('说明', '').startswith('彩蛋')
           and audition.rival_present(st, rid)]
    lv = {}
    for rid in ids:
        r = d.rivals_named[rid]
        for s in r['阶段']:
            if st.date >= s['自']:
                lv[rid] = s['等级'][main]
    top = sorted(ids, key=lambda x: (-lv[x], ids.index(x)))[:c['取前']]
    w = c['权重'][:len(top)]
    v = st.rng.logic.below(sum(w))
    for rid, x in zip(top, w):
        if v < x:
            return rid
        v -= x
    raise AssertionError


def make_rivals(st, e):
    out = []
    for o in e['对手规格']:
        if o.get('无名'):
            out.append(audition.unnamed_rival(st, e['档次'], o.get('主色等级'), e['场风概率']))
        elif o.get('有名'):
            out.append(audition.named_rival(st, o['有名']))
        else:
            out.append(audition.named_rival(st, named_for_placeholder(st, e['场风概率'])))
    e['对手'] = out


# ---------- 组板 ----------
def compose(st):
    """本块板的角色快照列表（还没有对手、有声、本厂、情报）。"""
    d = st.d
    c = cfg(d)
    sv = st.story
    n = dict(c['每板'])
    if st.val('人脉') >= c['人脉多一个中片']:
        n['中'] += 1
    if st.val('人脉') >= c['人脉多一个大片']:
        n['大'] += 1
    out = []
    taken = set()
    tut = st.ym == 0
    for t in ('大', '中', '小'):
        for k in range(n[t]):
            if tut and t == '小' and k == n[t] - 1:
                e = tutorial(st)
            else:
                e = draw(st, t, taken)
            taken.add(e['id'])
            out.append(e)
    # 多出的角色
    for r in sv['待上板']:
        out.append(r)
    sv['待上板'] = []
    if st.flags.get('富婆投资') == 1:
        st.flags['富婆投资'] = 2
        e = draw(st, '中', taken)
        e['来源'] = '富婆投资' if e['来源'] == '池' else e['来源']
        taken.add(e['id'])
        out.append(e)
    left, fam = sv['转型']
    if left > 0:
        e = draw(st, '中', taken, d.tag_families[fam])
        taken.add(e['id'])
        out.append(e)
        sv['转型'][0] -= 1
    v = c['瓦伦去世后多一个']
    if st.flags.get('瓦伦去世') and st.date <= v['至']:
        e = draw(st, v['档次'], taken, v['标签'])
        taken.add(e['id'])
        out.append(e)
    for e in out:
        if e['来源'] in ('池', '富婆投资'):
            sv['上过板'][e['id']] = sv['上过板'].get(e['id'], 0) + 1
    return out


def assign_talkie(st, entries):
    d = st.d
    c = d.role_cfg['有声']
    g = st.rng.logic
    if st.date < c['开始']:
        for e in entries:
            e['有声'] = False
        return
    rule = None
    for x in c['比例']:
        if st.date >= x['自']:
            rule = x
    cand = [e for e in entries if e['有声'] is None]
    for e in entries:
        if e['有声'] is None:
            e['有声'] = False
    if '个数' in rule:
        for _ in range(min(rule['个数'], len(cand))):
            e = cand.pop(g.below(len(cand)))
            e['有声'] = True
    else:
        for e in cand:
            e['有声'] = g.chance(rule['百分比'], 100)
    for e in entries:
        if e['有声'] and e['谈吐线'] is None:
            e['谈吐线'] = d.role_cfg['谈吐线'][e['档次']]


def fame_gate(st, e):
    g = e['名气门槛']
    if e['档次'] == '大' and film.low_budget(st):
        g += cfg(st.d)['低成本大片门槛加']
    return g


def eligible(st, e):
    """能不能报名：名气够、道德条款、长约只能报本厂。返回 None 或原因。"""
    if st.attr['名气'] < fame_gate(st, e):
        return '够不着'
    if e['档次'] == '大' and st.val('犯罪') >= cfg(st.d)['道德条款犯罪']:
        return '道德条款'
    if st.status['长约'] and not e['本厂']:
        return '不是本厂的角色'
    return None


def make(st):
    """出板：组角色、定场风、生成对手、有声、本厂、情报。结果存在 st.story['板']。"""
    d = st.d
    c = cfg(d)
    g = st.rng.logic
    entries = compose(st)
    for e in entries:
        if e['路'] is None:
            e['路'] = d.roads[main_of(e['基础场风'])]
        key = '记住.' + e['id']
        if st.flags.get(key):           # 被导演记住：这次出现时玩家主色 +10（7.4）
            e['场风概率'] = audition.remembered_probs(e['场风概率'], audition.player_main(st),
                                                    d.t['habits']['试镜']['结果']['记住']['主色场风加百分点'])
            st.flags[key] = 0
            e['情报']['记住'] = True
    assign_talkie(st, entries)
    for e in entries:
        make_rivals(st, e)
    if st.status['长约']:
        k = d.contract['长约']
        cand = [e for e in entries if st.attr['名气'] >= fame_gate(st, e)]
        for _ in range(min(k['本厂角色数'], len(cand))):
            e = cand.pop(g.below(len(cand)))
            e['本厂'] = True
            e['场风概率'] = audition.remembered_probs(e['场风概率'], audition.player_main(st), k['本厂场风加'])
    # 情报
    ic = c['情报']
    for e in entries:
        e['情报']['标签'] = st.val('审美') >= ic['标签审美']
        e['情报']['习惯'] = [st.val('人脉') >= ic['习惯人脉'] or
                           (rv['id'] is not None and st.cnt('交手次数.' + rv['id']) >= ic['习惯交手次数'])
                           for rv in e['对手']]
        if st.val('人脉') >= ic['排除一色人脉']:
            p = e['场风概率']
            e['情报']['排除'] = min(range(4), key=lambda x: (p[x], x))
    if st.flags.get('侍者情报') and entries:
        e = entries[g.below(len(entries))]
        e['情报']['习惯'] = [True] * len(e['对手'])
    while st.story['告密'] > 0:
        st.story['告密'] -= 1
        cand = [e for e in entries if e['档次'] in ('中', '大') and not e['情报'].get('场风')]
        if cand:
            e = cand[g.below(len(cand))]
            e['情报']['场风'] = True
            e['情报']['标签'] = True
    for e in entries:
        e['情报']['资格'] = eligible(st, e)
    st.story['板'] = {'月': st.ym, '角色': entries, '试过': [], '拿到': None}
    return st.story['板']


# ---------- 试镜 ----------
def can_try(st, idx):
    b = board(st)
    if b is None or b['月'] != st.ym:
        return '没有本月的选片板'
    if b['拿到'] is not None:
        return '这块板已经拿到角色'
    if len(b['试过']) >= cfg(st.d)['试镜次数']:
        return '这块板已经试过两次'
    if idx in b['试过']:
        return '已经试过这个角色'
    e = b['角色'][idx]
    if b['试过'] and RANK[e['档次']] >= RANK[b['角色'][b['试过'][-1]]['档次']]:
        return '第二次的档次必须比第一次低'
    return eligible(st, e)


def try_role(st, idx, agent):
    """报名板上第 idx 个角色并打完试镜。拿到或惜败接配角时生成片约。返回 audition 的结果。"""
    why = can_try(st, idx)
    if why:
        raise ValueError(why)
    b = board(st)
    e = b['角色'][idx]
    b['试过'].append(idx)
    res = audition.audition(st, e, agent, e['对手'], e['场风概率'])
    support = False
    if res['结果'] == '惜败' and agent.accept_support(st, e):
        support = True
    if res['结果'] == '拿到' or support:
        b['拿到'] = idx
        pers = (not support) and film.can_go_personally(st, e) and agent.go_personally(st, e)
        res['片约'] = film.new_film(st, e, film.board_locks(st, e['档次'], support), support, pers)['id']
    res['配角'] = support
    st.inc('计数.试镜')
    if res['结果'] == '拿到':
        st.inc('计数.试镜拿到')
        st.inc('计数.试镜拿到.' + e['档次'])
    st.inc('计数.试镜.' + e['档次'])
    return res


def run(st, agent):
    """出板后让玩家逐个报名，直到放弃、拿到角色或试满两次。"""
    out = []
    while True:
        b = board(st)
        ok = [i for i in range(len(b['角色'])) if can_try(st, i) is None]
        if not ok:
            break
        i = agent.pick_role(st, b, ok)
        if i is None:
            break
        out.append(try_role(st, i, agent))
    return out


# ---------- 板外的试镜（11.1） ----------
def one_match(st, agent, role, rival):
    """一场单打（临时换角、抢角）。返回 True 表示玩家赢。"""
    ctx = {'角色': role, '场次': 0, '对手': rival, '等级': audition.player_levels(st)}
    colors = agent.deck(st, ctx)
    m = audition.match(st, audition.build_deck(ctx['等级'], colors), rival, role['场风概率'], agent)
    if rival['id']:
        st.inc('交手次数.' + rival['id'])
    return m['比分'][0] >= audition.cfg(st.d)['赢轮数']


def swap_role(st, i, agent):
    """临时换角：打一场中片试镜，赢了占下一旬拍摄。下一旬已被占时不触发（调用方先查）。"""
    d = st.d
    c = d.role_cfg['拍摄']['临时换角']
    e = draw(st, c['档次'], set())
    if e['来源'] == '池':
        st.story['上过板'][e['id']] = st.story['上过板'].get(e['id'], 0) + 1
    e['路'] = d.roads[main_of(e['基础场风'])]
    e['有声'] = bool(e['有声']) and st.date >= d.role_cfg['有声']['开始']
    if e['有声'] and e['谈吐线'] is None:
        e['谈吐线'] = d.role_cfg['谈吐线'][e['档次']]
    rv = audition.unnamed_rival(st, e['档次'], None, e['场风概率'])
    win = one_match(st, agent, e, rv)
    if win:
        nxt = film.next_period(st, i)
        pers = film.can_go_personally(st, e) and agent.go_personally(st, e)
        film.new_film(st, e, [nxt][:c['旬数']], False, pers)
    return win


def steal_role(st, agent):
    """抢角：无名对手来抢一个未开拍的角色，输了片约作废。"""
    f = next(x for x in film.films(st) if x['状态'] == '待拍')
    role = f['角色']
    rv = audition.unnamed_rival(st, role['档次'], None, role['场风概率'])
    win = one_match(st, agent, role, rv)
    if not win:
        f['状态'] = '被抢'
        film.update_status(st)
    return win


# ---------- 剧本（6.5） ----------
def script_ok(st, kind):
    d = st.d
    c = d.role_cfg['剧本']
    sv = st.story['剧本']
    y = int(st.date[:4])
    if not rules.cond(st, c[kind]['条件']):
        return False
    if kind == '合写':
        return not sv['合写'] and sv['自己写'] != y and sv['Duv写'] != y
    return sv[kind] != y


def write_script(st, kind, color=None):
    """月初操作：自己写 / Duv写 / 合写。下一块板多一个角色。color：自己写、合写时玩家指定的颜色（0–3）。"""
    d = st.d
    c = d.role_cfg['剧本']
    if not script_ok(st, kind):
        raise ValueError(f'现在不能{kind}')
    sv = st.story['剧本']
    y = int(st.date[:4])
    tier = c[kind]['档次']
    st.story['序号'] += 1
    if kind == 'Duv写':
        main = audition.player_main(st)
        b = st.bonus()
        names = ['体力', '教育', '义气', '相貌', '自律', '犯罪']
        top = sorted(names, key=lambda n: (-st.val(n, b), names.index(n)))[:2]
        want = [{'项': n, '目标': max(1, st.val(n, b) * c['Duv写']['看重百分比'] // 100)} for n in top]
        rules.apply_effect(st, c['Duv写']['好感'], source='event')
        sv['Duv写'] = y
    else:
        if color is None or not 0 <= color < 4:
            raise ValueError('要指定颜色')
        main = color
        want = [{'项': d.road_skills[d.roads[main]][0], '目标': d.role_cfg['占位生成']['看重目标'][tier]}]
        if kind == '合写':
            sv['合写'] = 1
            sv['自己写'] = sv['Duv写'] = y
        else:
            sv['自己写'] = y
    opp = [{'无名': True}] + ([{'有名占位': True}] if tier == '大' else [])
    r = {'id': f"script{st.story['序号']}", '名字': f'剧本角色（{kind}）', '档次': tier, '名气门槛': None,
         '场风概率': split_probs(main, c['主色场风']), '看重': want, '标签': [], '加分技能': None,
         '有声': None, '谈吐线': None, '片酬': None, '对手': opp}
    st.story['待上板'].append(snapshot(st, r, '剧本'))
