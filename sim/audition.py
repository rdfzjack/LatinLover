"""试镜（GDD 7、9）：组牌、有效点数、出牌习惯、对手组牌、结果分档。

颜色用 0–3 表示，顺序 硬汉/情人/文化/手腕（habits.json 的 试镜.颜色顺序）。
一张牌是 (颜色, 点数)。有效点数按 ×100 的整数算（GDD 16）。

随机数的消耗顺序（Godot 照抄）：
- 生成无名对手：r(主色等级随机)，然后习惯 below(6)。
- 一场：先抽场风 below(100)；之后每轮先由对手出牌（习惯不是随性时先掷 80% 是否照习惯，
  不照或随性时 below(剩余张数)），再问玩家出牌。
- 演砸：掷上报概率。
玩家怎么组牌、怎么出牌不由这里决定：传入一个 Player（界面或机器人）。
"""
from . import rules

COLORS = 4


def cfg(d):
    return d.t['habits']['试镜']


def color_names(d):
    return cfg(d)['颜色顺序']


def beats(d):
    """克制环：beats[a] = 被 a 克的颜色。"""
    c = cfg(d)
    names = c['颜色顺序']
    return [names.index(c['克制'][n]) for n in names]


# ---------- 牌 ----------
def build_deck(levels, colors):
    """玩家选 5 张的颜色；同色第 k 张（k 从 0 起）点数 = max(0, 该路等级 − k)（7.2）。"""
    seen = [0] * COLORS
    out = []
    for c in colors:
        out.append((c, max(0, levels[c] - seen[c])))
        seen[c] += 1
    return out


def deck_of(levels, main, k, sub, n=5):
    """主色 k 张加副色 5−k 张。"""
    return build_deck(levels, [main] * k + [sub] * (n - k))


def effective(d, a, b, field):
    """一轮里两张牌的有效点数 (va, vb)，×100 整数（7.3）。"""
    c = cfg(d)
    bt = beats(d)
    (ca, pa), (cb, pb) = a, b
    va, vb = pa * 100, pb * 100
    if ca == field:
        va = va * c['场风百分比'] // 100
    if cb == field:
        vb = vb * c['场风百分比'] // 100
    if bt[ca] == cb and cb != field:
        va = va * c['克制方百分比'] // 100
        vb = vb * c['被克方百分比'] // 100
    elif bt[cb] == ca and ca != field:
        vb = vb * c['克制方百分比'] // 100
        va = va * c['被克方百分比'] // 100
    return va, vb


def round_winner(d, mine, theirs, field, fame_me, fame_them):
    """返回 True 表示玩家赢这一轮。相等看名气，仍相等对手胜（7.3）。"""
    va, vb = effective(d, mine, theirs, field)
    if va != vb:
        return va > vb
    return fame_me > fame_them


def solo_value(d, card, field):
    """排“大小”用：只算场风，不计克制（7.6）。"""
    v = card[1] * 100
    if card[0] == field:
        v = v * cfg(d)['场风百分比'] // 100
    return v


# ---------- 对手 ----------
def guard_color(d, main):
    """克星的克星：克 main 的那一色被谁克，就是谁（情人 -> 手腕，硬汉 -> 文化）。"""
    bt = beats(d)
    beater = bt.index(main)
    return bt.index(beater)


def opponent_colors(d, levels, probs):
    """对手的 (主色, 副色)（7.5）：主色按 等级 × (1 + 0.3 × 场风概率) 最大，并列取靠前的；
    副色取克星的克星，防被克制。"""
    co = cfg(d)['对手组牌']['场风系数百分比']
    key = [levels[c] * (10000 + co * probs[c]) for c in range(COLORS)]
    main = min(range(COLORS), key=lambda c: (-key[c], c))
    return main, guard_color(d, main)


def opponent_deck(d, rival, probs):
    main, sub = opponent_colors(d, rival['等级'], probs)
    return deck_of(rival['等级'], main, rival['k'], sub)


def half_years(st):
    return st.ym // 6


def unnamed_rival(st, tier, main_level=None, probs=None):
    """无名对手（9.2）。主色 = 场风概率最高的颜色，副色 = 克星的克星（等级 主色−2），其余两色 1 级。"""
    d = st.d
    g = st.rng.logic
    r = d.t['rivals']['无名']
    t = next(x for x in r['档'] if x['档次'] == tier)
    h = half_years(st)
    if main_level is None:
        L = t['主色等级']['基'] + sum(1 for m in t['主色等级']['涨级月'] if st.date >= m) + g.r(*t['主色等级']['随机'])
    else:
        L = main_level
    L = max(1, L)
    probs = probs or [25, 25, 25, 25]
    main = min(range(COLORS), key=lambda c: (-probs[c], c))
    lv = [1] * COLORS
    lv[main] = L
    lv[guard_color(d, main)] = max(1, L - t['副色差'])
    habits = d.t['habits']['习惯']
    hb = habits[g.below(len(habits))]['id']
    return {'id': None, '名字': f'无名（{tier}）', '等级': lv,
            '名气': t['名气']['基'] + t['名气']['每半年'] * h, '习惯': hb, 'k': t['k']}


def named_rival(st, rid):
    """有名对手在当前月份的数据（9.1）。瓦伦 1927-09 起由诺瓦或吉尔伯替换（9.3），抽一个。"""
    d = st.d
    rv = d.t['rivals']
    date = st.date
    for x in rv['替换']:
        if x['原'] == rid and date >= x['自']:
            rid = x['改为'][st.rng.logic.below(len(x['改为']))]
    r = next(x for x in rv['有名'] if x['id'] == rid)
    lv = fame = None
    for s in r['阶段']:
        if date >= s['自']:
            lv = s['等级']
            fame = s.get('名气', fame)
    return {'id': rid, '名字': r['名字'], '等级': list(lv), '名气': fame, '习惯': r['习惯'], 'k': r['k']}


def rival_present(st, rid):
    r = next(x for x in st.d.t['rivals']['有名'] if x['id'] == rid)
    return r['在场'][0] <= st.date <= r['在场'][1]


# ---------- 出牌习惯 ----------
def opponent_pick(st, habit, hand, field, rnd, my_last, score):
    """对手这一轮出哪张（hand 里的下标）。score = (玩家胜轮, 对手胜轮)。"""
    d = st.d
    g = st.rng.logic
    if habit != 'habit_random':
        follow = g.chance(d.t['habits']['遵循概率'], 100)
    else:
        follow = False
    if not follow:
        return g.below(len(hand))
    order = sorted(range(len(hand)), key=lambda i: (solo_value(d, hand[i], field), i))   # 小到大
    small, big = order[0], order[-1]
    if habit == 'habit_lead':
        return big
    if habit == 'habit_finish':
        return small
    if habit == 'habit_open':
        return big if rnd == 0 else small
    if habit == 'habit_follow':
        if rnd == 0:
            return order[len(order) // 2]
        for i in order:
            va, vb = effective(d, my_last, hand[i], field)
            if vb > va:
                return i
        return small
    if habit == 'habit_score':
        me, them = score
        return big if them <= me else small
    raise ValueError(habit)


# ---------- 玩家 ----------
class Player:
    """界面或机器人实现这两个方法。"""

    def deck(self, st, ctx):
        """返回 5 个颜色（0–3）。ctx：角色、场次、对手（只给能看到的情报）、自己的等级。"""
        raise NotImplementedError

    def play(self, st, ctx):
        """返回自己手牌的下标。ctx：手牌、对手剩余手牌、场风、轮次、比分、历史。"""
        raise NotImplementedError


class FixedRandomPlayer(Player):
    """固定组牌、随机出牌（测试和粗算用）。出牌用逻辑流。"""

    def __init__(self, colors):
        self.colors = colors

    def deck(self, st, ctx):
        return list(self.colors)

    def play(self, st, ctx):
        return st.rng.logic.below(len(ctx['手牌']))


# ---------- 一场 ----------
def roll_field(st, probs):
    v = st.rng.logic.below(100)
    acc = 0
    for c in range(COLORS):
        acc += probs[c]
        if v < acc:
            return c
    return COLORS - 1


def match(st, my_deck, rival, probs, player, field=None):
    """打一场。返回 {'比分': (我, 对手), '场风', '轮': [(我的牌, 对手的牌, 我赢)]}。"""
    d = st.d
    need = cfg(d)['赢轮数']
    their_deck = opponent_deck(d, rival, probs)
    if field is None:
        field = roll_field(st, probs)
    mine, theirs = list(my_deck), list(their_deck)
    me = them = 0
    hist = []
    my_last = None
    fame_me = st.attr['名气']
    rnd = 0
    while me < need and them < need and mine:
        oi = opponent_pick(st, rival['习惯'], theirs, field, rnd, my_last, (me, them))
        ctx = {'手牌': list(mine), '对手手牌': list(theirs), '场风': field, '轮次': rnd,
               '比分': (me, them), '历史': list(hist), '对手': rival}
        mi = player.play(st, ctx)
        a, b = mine.pop(mi), theirs.pop(oi)
        win = round_winner(d, a, b, field, fame_me, rival['名气'])
        me += win
        them += not win
        hist.append((a, b, win))
        my_last = a
        rnd += 1
    return {'比分': (me, them), '场风': field, '轮': hist, '对手牌': their_deck, '我的牌': list(my_deck)}


# ---------- 结果 ----------
def player_levels(st):
    b = st.bonus()
    lv = []
    for r in st.d.roads:
        rep = st.rep(r, b)
        L = 0
        for i, g in enumerate(st.d.level_gate):
            if rep >= g:
                L = i
        lv.append(L)
    return lv


def player_main(st):
    """玩家主色：当前声望最高的路，并列取靠前的。"""
    b = st.bonus()
    reps = [st.rep(r, b) for r in st.d.roads]
    return max(range(COLORS), key=lambda c: (reps[c], -c))


def remembered_probs(probs, main, pts):
    """被导演记住：玩家主色 +pts 个百分点，从其他色里最高的那一色扣（7.4）。"""
    p = list(probs)
    others = [c for c in range(COLORS) if c != main]
    top = max(others, key=lambda c: (p[c], -c))
    move = min(pts, p[top])
    p[main] += move
    p[top] -= move
    return p


def classify(d, score):
    me, them = score
    if me >= cfg(d)['赢轮数']:
        return '记住' if them == 0 else '拿到'
    if (me, them) == tuple(cfg(d)['结果']['惜败']['比分']):
        return '惜败'
    if me == 0:
        return '演砸'
    return '落选'


def audition(st, role, player, rivals, probs=None):
    """一次试镜。rivals：对手列表（小、中片 1 个，大片 2 个；由选片板生成）。
    probs：本次的场风概率（默认取角色的；被记住、教学角色等由调用方先算好）。
    返回 {'结果': 拿到/惜败/落选/演砸, '记住': bool, '场次': [match…]}，并结算 7.4 的名气、上报、交手次数。"""
    d = st.d
    probs = probs or role['场风概率']
    res = cfg(d)['结果']
    out = {'角色': role['id'], '场次': [], '记住': False}
    final = None
    for n, rv in enumerate(rivals):
        ctx = {'角色': role, '场次': n, '对手': rv, '等级': player_levels(st)}
        colors = player.deck(st, ctx)
        if len(colors) != cfg(d)['张数'] or any(not 0 <= c < COLORS for c in colors):
            raise ValueError(f'牌组不对：{colors}')
        m = match(st, build_deck(ctx['等级'], colors), rv, probs, player)
        out['场次'].append(m)
        if rv['id']:
            st.inc('交手次数.' + rv['id'])
        kind = classify(d, m['比分'])
        if n == 0:
            final = kind
            out['记住'] = kind == '记住'
            if kind not in ('拿到', '记住'):
                break
        else:   # 大片第二场：赢了才算拿到，输了一律惜败
            final = final if kind in ('拿到', '记住') else '惜败'
            out['记住'] = out['记住'] and kind in ('拿到', '记住')
    if final == '记住':
        final = '拿到'
    if final == '演砸':
        x = res['演砸']
        rules.apply_effect(st, x['效果'], source='schedule')
        rules.apply_effect(st, x['好感'], source='schedule')
        if st.rng.logic.chance(*x['上报概率']):
            st.exposed = 1
            rules.apply_effect(st, x['上报效果'], source='schedule')
            out['上报'] = True
    if out['记住']:
        st.flags['记住.' + role['id']] = 1
    out['结果'] = final
    return out


# ---------- GDD 7.7 的试算表 ----------
# 贴近实际的局面：一个情人角色（场风 15/60/10/15），对手按 9.2 的无名规则组牌
# （3 张情人 + 2 张手腕，副色低 2 级）；场风按角色概率抽；双方随机出牌。
# 玩家在“纯色 / 主色 4 或 3 张 + 一种副色”里取胜率最高的一副。颜色 0 硬汉 1 情人 2 文化 3 手腕。
ROLE_77 = [15, 60, 10, 15]
OPP_77 = 6
CASES_77 = [
    ('同路同级', [2, 6, 2, 2]),
    ('同路低 1 级', [2, 5, 2, 2]),
    ('同路高 1 级', [2, 7, 2, 2]),
    ('同路高 2 级', [2, 8, 2, 2]),
    ('同路同级，副路硬汉 4', [4, 6, 2, 2]),
    ('硬汉路玩家（硬 6 情 2）', [6, 2, 2, 2]),
    ('文化路玩家（文 6 情 2）', [2, 2, 6, 2]),
    ('手腕路玩家（手 6 情 2）', [2, 2, 2, 6]),
]


def opp_77(d, L=OPP_77, probs=ROLE_77):
    t = d.t['rivals']['无名']['档'][1]
    main = min(range(COLORS), key=lambda c: (-probs[c], c))
    lv = [1] * COLORS
    lv[main] = L
    lv[guard_color(d, main)] = max(1, L - t['副色差'])
    return {'id': None, '名字': '无名', '等级': lv, '名气': 100, '习惯': 'habit_random', 'k': t['k']}


def exact_win(d, my_deck, their_deck, field, fame_me=0, fame_them=100):
    """双方都随机出牌时的胜率：枚举对手出牌顺序的 120 种排列（我的顺序固定不影响结果）。"""
    import itertools
    need = cfg(d)['赢轮数']
    win = total = 0
    for p in itertools.permutations(range(len(their_deck))):
        me = them = 0
        for i, j in enumerate(p):
            if me >= need or them >= need:
                break
            if round_winner(d, my_deck[i], their_deck[j], field, fame_me, fame_them):
                me += 1
            else:
                them += 1
        win += me >= need
        total += 1
    return win / total


def candidate_decks(levels):
    """主色 = 等级最高的颜色；纯色，或主色 4/3 张加一种副色。返回 {名字: 颜色列表}。"""
    names = ['硬', '情', '文', '手']
    main = max(range(COLORS), key=lambda c: (levels[c], -c))
    out = {'纯色': [main] * 5}
    for k in (4, 3):
        for s in range(COLORS):
            if s != main:
                out[f'{k}+{5 - k}{names[s]}'] = [main] * k + [s] * (5 - k)
    return out


def table_77(d, fame_hi=False):
    """每行：(局面, 最佳牌组, 胜率, 场风=情人时, 场风为其他色时)，胜率是 0–1。"""
    fm, ft = (200, 100) if fame_hi else (0, 100)
    rv = opp_77(d)
    theirs = opponent_deck(d, rv, ROLE_77)
    out = []
    for name, lv in CASES_77:
        best = None
        for dn, cols in candidate_decks(lv).items():
            mine = build_deck(lv, cols)
            per = [exact_win(d, mine, theirs, f, fm, ft) for f in range(COLORS)]
            tot = sum(ROLE_77[f] * per[f] for f in range(COLORS)) / 100
            if best is None or tot > best[2]:
                main_f = max(range(COLORS), key=lambda c: (ROLE_77[c], -c))
                rest = sum(ROLE_77[f] * per[f] for f in range(COLORS) if f != main_f) / (100 - ROLE_77[main_f])
                best = (name, dn, tot, per[main_f], rest, cols)
        out.append(best)
    return out


if __name__ == '__main__':
    from .data import load
    d = load()
    rv = opp_77(d)
    names = ['硬', '情', '文', '手']
    print(f'GDD 7.7：情人角色（场风 {ROLE_77}），对手牌 '
          + ' '.join(f'{names[c]}{p}' for c, p in opponent_deck(d, rv, ROLE_77)) + '；双方随机出牌')
    a, b = table_77(d), table_77(d, fame_hi=True)
    for x, y in zip(a, b):
        print(f'{x[0]:<16} {x[1]:<5} 对手名气高 {x[2]*100:3.0f}%（情人场风 {x[3]*100:3.0f}% / 其他 {x[4]*100:3.0f}%）'
              f'  我名气高 {y[2]*100:3.0f}%')
