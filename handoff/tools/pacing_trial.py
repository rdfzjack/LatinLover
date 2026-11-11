"""节奏粗算：按 GDD 的规则逐日跑一局，看四条路的练满时间、现金、声望和试镜。

用法：python3 pacing_trial.py [--n 400] [--buy] [--contract]
  --buy       机器人买本路装备（ITEMS）
  --contract  名气和声望够了就签长约
模型算了什么、没算什么、怎么读输出，见 README.md 的“复现粗算”。
"""
import random, datetime, statistics, itertools, functools

PATHS = ['硬汉', '情人', '文化', '手腕']
SK = {'硬汉': ['打斗', '骑马', '胆识'], '情人': ['演技', '打扮', '体态'],
      '文化': ['创作', '审美', '谈吐'], '手腕': ['谈判', '人脉', '生意']}
ALLSK = [s for p in PATHS for s in SK[p]]

def lvl(p):
    L = 0
    while L < 9 and 5 * (L + 1) * (L + 2) <= p: L += 1
    return L

# ---------- 配置：GDD 里和节奏有关的数值。改 GDD 时在这里同步改 ----------
def _rival(tier, m):  # GDD 9.2，m 是月序（1–48）
    h = (m - 1) // 6
    return [2, 4, 5][tier] + h // 3 + [random.randint(-1, 0), random.randint(-1, 1), random.randint(0, 1)][tier]
CFG = dict(
    start=1926, months=48,
    thr=(3, 6, 9),                    # 5.2 课程等级门槛（旬）
    raise_steps=(5, 15, 30, 45),      # 5.4 加薪台阶（成功期数）
    classes={                         # 5.3.1：学费/天、主收益、副收益、是否体力+1
        '拳馆': dict(fee=(12, 16, 20, 24), main=('打斗', [(1, 1), (1, 1), (1, 2), (1, 3)]), side=[('胆识', [(0, 0), (0, 1), (0, 1), (0, 1)])], sta=1),
        '马术': dict(fee=(16, 26, 38, 50), main=('骑马', [(1, 1), (1, 2), (1, 3), (1, 4)]), side=[('胆识', [(0, 1)] * 4)], sta=0),
        '表演': dict(fee=(12, 16, 20, 24), main=('演技', [(1, 1), (1, 2), (1, 3), (2, 4)]), side=[('谈吐', [(0, 1)] * 4)], sta=0),
        '舞蹈': dict(fee=(10, 14, 18, 24), main=('体态', [(1, 1), (1, 2), (1, 3), (2, 4)]), side=[], sta=1),
        '礼仪': dict(fee=(10, 14, 18, 22), main=('打扮', [(1, 1), (1, 2), (1, 3), (2, 4)]), side=[('谈吐', [(0, 1)] * 4)], sta=0),
        '家教': dict(fee=(8, 10, 12, 14), main=('教育', [(1, 4), (2, 6), (3, 8), (4, 12)]), side=[], sta=0,
                   edu_side=('创作', [(0, 1), (1, 2), (1, 3), (1, 4)])),
    },
    books={'入门': dict(edu=100, cap=40, pts=35, gain=(1, 1), price=5),   # 5.3.2
           '进阶': dict(edu=200, cap=70, pts=35, gain=(1, 2), price=25),
           '专著': dict(edu=300, cap=100, pts=35, gain=(1, 2), price=90)},
    # 5.4（只放了机器人会用到的工）：m 解锁月序，w 日薪，need 成功线，sk 每天 +0/1 的技能（元组为固定区间），at 属性效果，fat 疲劳
    jobs={
        '助理': dict(m=1, w=3, need={'体力': 5}, sk=['谈判', '人脉', '生意'], at={}, fat=1),
        '侍者': dict(m=1, w=5, need={'体力': 20}, sk=['谈判'], at={}, fat=2),
        '码头': dict(m=1, w=6, need={'体力': 30}, sk=[], at={'体力': 1, '相貌': -1}, fat=3),
        '模特': dict(m=1, w=3, need={'体力': 20}, sk=['审美'], at={}, fat=3),
        '教堂': dict(m=1, w=1, need={'体力': 10}, sk=[], at={'自律': 2, '犯罪': -2}, fat=1),
        '看场子': dict(m=1, w=8, need={'体力': 60}, sk=['胆识'], at={'犯罪': 1, '自律': -1}, fat=4),
        '办公室': dict(m=4, w=6, need={'教育': 60}, sk=['生意', ('人脉', (1, 1))], at={}, fat=4),
        '报馆': dict(m=4, w=5, need={'教育': 60}, sk=['创作'], at={}, fat=3),
        '替身': dict(m=7, w=15, need={'体力': 80, '胆识': 30}, sk=['胆识'], at={'体力': 2, '相貌': -1}, fat=3),
        '画报': dict(m=16, w=12, need={'打扮': 40}, sk=[], at={'相貌': 1}, fat=3, expo=True),
    },
    job_gain=(0, 1),
    living=(100, 150, 220, 400, 700),                 # 5.7 普通档，按名气档
    fee=(300, 800, 2500), nego=400,                   # 6.2 片酬；5.6 谈判系数的分母
    B=(40, 100, 250), corr=(2, 5, 10),                # 8.2 票房基数、声望修正
    fame_gate=(0, 100, 250),
    rival=_rival, rival_fame=lambda tier, m: [40, 150, 300][tier] + 15 * ((m - 1) // 6),
    val_end=(1927, 8),                                # 瓦伦在场到这个月
    annual=(40, 20, 10), talkie_start=(1927, 10), talk_line=(30, 50, 70),
    start_money=500, start_fame=120,
    outing_gain=2,                                    # 粗略：逛街一半的旬给一项技能 +2
    guard=35,                                         # 机器人：自律低于此去教堂义工
    salary=250, long_contract=False, buy=False,       # --contract / --buy 打开
)

# 9.1 有名对手：每年 [(名字, 硬汉/情人/文化/手腕等级, 名气, k)]，下标 0 = 1926
NAMED = {
 0: [('瓦伦', (5, 9, 2, 3), 700, 5), ('范班克', (9, 5, 3, 6), 750, 4), ('吉尔伯', (4, 7, 3, 2), 500, 4), ('诺瓦', (5, 7, 4, 2), 450, 3), ('巴里', (3, 7, 8, 4), 600, 3), ('钱宁', (6, 2, 7, 3), 550, 4), ('库普', (4, 3, 1, 2), 100, 5)],
 1: [('瓦伦', (5, 9, 2, 3), 700, 5), ('范班克', (9, 5, 3, 6), 750, 4), ('吉尔伯', (4, 8, 3, 2), 650, 4), ('诺瓦', (5, 7, 4, 2), 450, 3), ('巴里', (3, 7, 8, 4), 600, 3), ('钱宁', (6, 2, 7, 3), 550, 4), ('库普', (5, 4, 1, 2), 250, 5)],
 2: [('范班克', (8, 5, 3, 6), 750, 4), ('吉尔伯', (4, 8, 3, 2), 650, 4), ('诺瓦', (5, 8, 4, 2), 550, 3), ('巴里', (3, 7, 9, 4), 600, 3), ('钱宁', (6, 2, 7, 3), 550, 4), ('库普', (7, 5, 2, 2), 400, 5), ('乔森', (1, 4, 6, 7), 600, 4)],
 3: [('范班克', (7, 5, 3, 6), 750, 4), ('吉尔伯', (4, 6, 2, 2), 400, 4), ('诺瓦', (5, 8, 4, 2), 550, 3), ('巴里', (3, 7, 9, 4), 600, 3), ('钱宁', (6, 2, 7, 3), 550, 4), ('库普', (8, 5, 2, 3), 550, 5), ('乔森', (1, 4, 6, 7), 600, 4)],
}

# 开局：底值 + 三问（按路挑自然的选项）
BASE_AT = dict(体力=80, 教育=5, 义气=40, 相貌=120, 自律=40, 犯罪=10)
BASE_SK = dict(打斗=10, 骑马=10, 胆识=5, 演技=20, 打扮=10, 体态=20, 创作=0, 审美=5, 谈吐=5, 谈判=10, 人脉=10, 生意=0)
ORIGIN = {
    '硬汉': (dict(体力=20, 自律=-15), dict(打斗=20, 骑马=10, 胆识=15), 0),       # 逃兵 + 硬汉派
    '情人': (dict(相貌=25, 自律=-10), dict(体态=20, 打扮=10, 谈判=5), 20),       # 男妓 + 大众情人
    '文化': (dict(教育=40, 义气=-10), dict(演技=20, 谈吐=5, 创作=5, 骑马=5), -20),  # 农学院 + 演技派
    '手腕': (dict(犯罪=30), dict(骑马=5, 谈判=5, 生意=5, 演技=20, 谈吐=5, 创作=5), -20),  # 走私 + 演技派
}

# ---------- 试镜（GDD 7.2–7.5，随机配对，不利用出牌习惯） ----------
BEAT = {0: 1, 1: 2, 2: 3, 3: 0}  # 硬汉克情人，情人克文化，文化克手腕，手腕克硬汉
PERMS = list(itertools.permutations(range(5)))
def deck(levels, main, k, sub):
    return tuple([(main, max(0, levels[main] - i)) for i in range(k)] + [(sub, max(0, levels[sub] - i)) for i in range(5 - k)])
def eff(a, b, f):
    (ca, pa), (cb, pb) = a, b
    va = pa * 100; vb = pb * 100
    if ca == f: va = va * 130 // 100
    if cb == f: vb = vb * 130 // 100
    if BEAT[ca] == cb and cb != f: va = va * 150 // 100; vb = vb * 70 // 100
    elif BEAT[cb] == ca and ca != f: vb = vb * 150 // 100; va = va * 70 // 100
    return va, vb
@functools.lru_cache(maxsize=None)
def duel(A, B, f, fame_hi):
    M = [[(lambda v: 1 if v[0] > v[1] or (v[0] == v[1] and fame_hi) else 0)(eff(a, b, f)) for b in B] for a in A]
    w = [0] * 6
    for p in PERMS: w[M[0][p[0]] + M[1][p[1]] + M[2][p[2]] + M[3][p[3]] + M[4][p[4]]] += 1
    return (w[3] + w[4] + w[5]) / 120, w[2] / 120, w[0] / 120
def opp_deck(levels, k, probs):
    sc = sorted(range(4), key=lambda c: -levels[c] * (100 + 30 * probs[c] // 100))
    return deck(levels, sc[0], k, sc[1])
@functools.lru_cache(maxsize=None)
def best_play(my, B, probs, fame_hi):
    """懂规则的玩家：在主色 k 张 + 一种副色里挑期望胜率最高的一副。返回 (胜率, 惜败率, 0:3 率)"""
    a = max(range(4), key=lambda c: my[c]); best = None
    for k in (5, 4, 3, 2):
        for b in range(4):
            if b == a or (k == 5 and b != (a + 1) % 4): continue
            A = deck(my, a, k, b); r = [0, 0, 0]
            for f in range(4):
                d = duel(A, B, f, fame_hi)
                for i in range(3): r[i] += d[i] * probs[f] / 100
            if best is None or r[0] > best[0]: best = r
    return tuple(best)
def unnamed(tier, L, main):
    lv = [1, 1, 1, 1]; lv[main] = max(1, L); sub = random.choice([c for c in range(4) if c != main]); lv[sub] = max(1, L - 2)
    return tuple(lv), 4
def role_probs(main):
    p = [15, 15, 15, 15]; p[main] = 55; return tuple(p)

# 本路装备：(价格, 声望增量)，按顺序买
ITEMS = {'硬汉': [(6, 10), (70, 10), (300, 10), (1500, 5)], '情人': [(90, 0), (100, 10), (150, 0), (200, 0), (800, 0)],
         '文化': [(60, 15), (60, 15), (100, 5)], '手腕': [(30, 5), (40, 5), (1500, 10), (6000, 10)]}
class G:
    def __init__(s, cfg, path, seed, second=None):
        random.seed(seed)
        s.c = cfg; s.path = path
        s.at = dict(BASE_AT); s.sk = dict(BASE_SK)
        a, k, f = ORIGIN[path]
        for x, v in a.items(): s.at[x] += v
        for x, v in k.items(): s.sk[x] += v
        s.money = cfg['start_money']; s.fame = cfg['start_fame'] + f; s.fat = 0
        s.corr = {p: 0 for p in PATHS}; s.annual = {p: 0 for p in PATHS}
        s.cls_n = {c: 0 for c in cfg['classes']}; s.job_n = {j: 0 for j in cfg['jobs']}
        s.book = {}  # (skill,tier)->剩余点数
        s.lock = {}  # (月序,旬)->film
        s.release = {}  # 月序->[film]
        s.debt_m = 0; s.films = [0, 0, 0]; s.aud = [0, 0]; s.bigtry = [0, 0]
        s.full = {}; s.milestone = {}; s.yearend = []; s.wild = 0; s.expo = False
        s.contract = False; s.fame_hist = []; s.tag = {p: 0 for p in PATHS}
        s.use = dict(课=0, 书=0, 工=0, 休=0, 拍=0); s.talk_pen = 0
        s.skfull = {}; s.cash_at_full = None; s.equip = 0; s.owned = 0; s.spent = 0
        s.second = second or {'硬汉': '情人', '情人': '硬汉', '文化': '情人', '手腕': '情人'}[path]

    def train(s, p): return sum(min(100, s.sk[k]) for k in SK[p])
    def pres(s, p): return s.train(p) + s.corr[p] + s.annual[p] + (s.equip if p == s.path else 0)
    def tier(s): return 0 if s.fame < 50 else 1 if s.fame < 150 else 2 if s.fame < 300 else 3 if s.fame < 500 else 4
    def add_sk(s, k, v): s.sk[k] = min(100, s.sk[k] + v)
    def val(s, k): return s.at[k] if k in s.at else s.sk[k]

    # ---------- 日程 ----------
    def practice_ok(s): return s.at['体力'] // 2 + random.randint(0, s.at['体力'] // 2) >= random.randint(0, max(0, s.fat))
    def do_class(s, name, days):
        c = s.c['classes'][name]; n = s.cls_n[name]; t = s.c['thr']
        L = 0 if n < t[0] else 1 if n < t[1] else 2 if n < t[2] else 3
        for d in days:
            if d.weekday() == 6: continue
            if s.money < c['fee'][L]: continue
            s.money -= c['fee'][L]; s.fat += 1
            if s.practice_ok():
                k, g = c['main']
                if k == '教育': s.at['教育'] = min(999, s.at['教育'] + random.randint(*g[L]))
                else: s.add_sk(k, random.randint(*g[L]))
                for k2, g2 in c['side']: s.add_sk(k2, random.randint(*g2[L]))
                if c['sta']: s.at['体力'] += 1
                if 'edu_side' in c and s.at['教育'] >= 100:
                    k2, g2 = c['edu_side']; s.add_sk(k2, random.randint(*g2[L]))
        s.cls_n[name] += 1; s.use['课'] += 1
    def do_book(s, key, days):
        k, tr = key; b = s.c['books'][tr]
        for d in days:
            if d.weekday() == 6: continue
            s.fat += 1
            if s.book[key] > 0 and s.sk[k] < b['cap'] and s.practice_ok():
                g = min(random.randint(*b['gain']), s.book[key], b['cap'] - s.sk[k])
                s.sk[k] += g; s.book[key] -= g
        s.use['书'] += 1
    def do_job(s, name, days):
        j = s.c['jobs'][name]; n = s.job_n[name]; rs = s.c['raise_steps']
        mult = 100 if n < rs[0] else 120 if n < rs[1] else 144 if n < rs[2] else 173 if n < rs[3] else 208
        wage = j['w'] * mult // 100; ok = 0; wd = 0; pay = 0
        for d in days:
            if d.weekday() == 6: continue
            wd += 1
            suc = all(s.val(k) - random.randint(0, max(0, s.fat)) >= v for k, v in j['need'].items())
            if suc and s.wild and random.random() < (0.4 if s.wild < 30 else 0.8): suc = False
            if suc: ok += 1; pay += wage
            for k in j['sk']:
                if isinstance(k, tuple): s.add_sk(k[0], random.randint(*k[1]))
                else: s.add_sk(k, random.randint(*s.c['job_gain']))
            for k, v in j['at'].items(): s.at[k] = max(0, s.at[k] + v)
            s.fat += j['fat']
        if ok == wd: pay = pay * 3 // 2
        s.money += pay
        if ok * 2 >= wd:
            s.job_n[name] += 1
            if j.get('expo'): s.expo = True
        s.use['工'] += 1
    def do_rest(s, days):
        out = s.money >= 2 * len(days)
        for d in days:
            if out: s.money -= 2; s.fat = max(0, s.fat - 10)
            else: s.fat = max(0, s.fat - 5)
        if out and s.c['outing_gain']:  # 逛街事件：粗略算成手腕或主路一项 +n
            pool = [k for k in SK['手腕'] + SK[s.path] if s.sk[k] < 100]
            if pool and random.random() < 0.5: s.add_sk(random.choice(pool), s.c['outing_gain'])
        s.use['休'] += 1
    def do_film(s, f, days):
        for d in days:
            if d.weekday() == 6: continue
            f['days'] += 1; s.fat += 2 + f['tier']; s.expo = True
            suc = s.at['体力'] - random.randint(0, max(0, s.fat)) >= 20 + 10 * f['tier']
            if suc and s.wild and random.random() < (0.4 if s.wild < 30 else 0.8): suc = False
            if suc: f['ok'] += 1
        f['left'] -= 1; s.use['拍'] += 1
        if f['left'] == 0:
            fee = s.c['fee'][f['tier']] * (s.c['nego'] + s.sk['谈判']) // s.c['nego']
            if s.at['教育'] < 100: fee = fee * 85 // 100
            if f['support']: fee = fee * 4 // 10
            s.money += fee
            f['P'] = 0.5 + f['ok'] / max(1, f['days']) / 2 + s.sk['演技'] / 500  # 5.6
            s.release.setdefault(s.mi + 2, []).append(f)

    # ---------- 选片板 ----------
    def board(s, y, m):
        roles = [(2, random.randrange(4)), (1, random.randrange(4)), (1, random.randrange(4)),
                 (0, random.randrange(4)), (0, random.randrange(4))]
        ts = s.c['talkie_start']; date = (s.c['start'] + y, m)
        if date < ts: pt = 0
        elif date == ts: pt = 0.2
        elif date[0] == ts[0] + 1: pt = 0.3
        else: pt = 0.8
        my = tuple(lvl(s.pres(p)) for p in PATHS); bi = max(range(4), key=lambda c: my[c])
        ny = y
        named = [r for r in NAMED[ny] if not (r[0] == '瓦伦' and (s.c['start'] + y, m) > s.c['val_end'])]
        tried = 0; last_tier = 3
        for tier in (2, 1, 0):
            if tried >= 2 or tier >= last_tier: continue
            if s.fame < s.c['fame_gate'][tier]: continue
            best = None
            for r in roles:
                if r[0] != tier: continue
                probs = role_probs(r[1])
                lv, k = unnamed(tier, s.c['rival'](tier, s.mi), r[1]); ofame = s.c['rival_fame'](tier, s.mi)
                e1 = best_play(my, opp_deck(lv, k, probs), probs, s.fame > ofame); e2 = (1.0, 0, 0)
                if tier == 2:
                    top = sorted(named, key=lambda x: -x[1][r[1]])[:3]
                    nm = random.choices(top, weights=(5, 3, 2))[0]
                    e2 = best_play(my, opp_deck(nm[1], nm[3], probs), probs, s.fame > nm[2])
                if best is None or e1[0] * e2[0] > best[0][0] * best[1][0]: best = (e1, e2, r)
            e1, e2, r = best
            if e1[0] * e2[0] < (0.12 if tier == 2 else 0.2) and tier > 0: continue
            tried += 1; last_tier = tier; s.aud[0] += 1
            if tier == 2: s.bigtry[0] += 1
            u = random.random(); support = False
            if u < e1[0]:
                win = random.random() < e2[0]
                if not win: support = True
            else:
                win = False
                if u < e1[0] + e1[1]: support = True
                elif u > 1 - e1[2]: s.fame -= s.fame * 5 // 100
            if not win and not support: continue
            if win:
                s.aud[1] += 1
                if tier == 2: s.bigtry[1] += 1
            n = max(1, [1, 2, 3][tier] - (1 if support else 0))
            f = dict(tier=tier, path=PATHS[r[1]], support=support, left=n, days=0, ok=0, talk=random.random() < pt, on=(r[1] == bi))
            for i in range(n): s.lock[(s.mi + 1, i)] = f
            if not support: s.films[tier] += 1
            return

    def settle_release(s, f):
        t = f['tier']; B = s.c['B'][t]
        F = random.uniform(0.95, 1.15) if f['on'] else random.uniform(0.75, 1.0)
        T = 1 + 0.03 * min(s.tag[f['path']], 5)
        S = B * f['P'] * F * T
        if f['talk'] and s.sk['谈吐'] < s.c['talk_line'][t]: S *= 0.6; s.talk_pen += 1
        k = 0.3 if f['support'] else 1.0
        flop = S < 0.7 * B
        s.fame += int(S * 0.3 * k * (0.5 if flop else 1)); s.money += int(S * 2 * k)
        s.rel = getattr(s, 'rel', 0) + 1; s.hit = getattr(s, 'hit', 0) + (S >= 1.3 * B)
        if not flop:
            c = s.c['corr'][t] * (2 if S >= 1.3 * B else 1)
            s.corr[f['path']] += int(c * k) if f['support'] else c
        s.tag[f['path']] += 1; s.expo = True

    # ---------- 机器人 ----------
    def plan(s, path):
        """返回 (种类, 名字, 现金需求)。None 表示这条路练满"""
        if s.train(path) >= 300: return None
        sk = s.sk; ed = s.at['教育']; av = lambda j: s.c['jobs'][j]['m'] <= s.mi
        if path == '情人':
            for k, c in (('演技', '表演'), ('打扮', '礼仪'), ('体态', '舞蹈')):
                if sk[k] < 100: return ('class', c)
        if path == '硬汉':
            for k, c in (('打斗', '拳馆'), ('骑马', '马术')):
                if sk[k] < 100: return ('class', c)
            if av('替身') and sk['胆识'] >= 30: return ('job', '替身')
            return ('job', '看场子')
        if path == '文化':
            if sk['创作'] < 100 or ed < 300: return ('class', '家教')
            for k in ('审美', '谈吐'):
                for tr in ('入门', '进阶', '专著'):
                    if sk[k] < s.c['books'][tr]['cap']: return ('book', (k, tr))
        if path == '手腕':
            if ed < 200 and (sk['谈判'] < 70 or sk['生意'] < 70): return ('class', '家教')
            for tr in ('入门', '进阶'):
                for k in ('谈判', '生意'):
                    if sk[k] < s.c['books'][tr]['cap'] and ed >= s.c['books'][tr]['edu']: return ('book', (k, tr))
            need = [k for k in SK['手腕'] if sk[k] < 100]
            if len(need) == 3 or '人脉' in need and not av('办公室'): return ('job', '助理')
            if ('生意' in need or '人脉' in need) and av('办公室') and ed >= 60: return ('job', '办公室')
            if need == ['谈判']: return ('job', '侍者')
            return ('job', '助理')
        return None
    def money_job(s):
        av = lambda j: s.c['jobs'][j]['m'] <= s.mi and all(s.val(k) - 10 >= v for k, v in s.c['jobs'][j]['need'].items())
        pref = {'硬汉': ['替身', '看场子', '码头'], '情人': ['画报', '侍者'], '文化': ['画报', '报馆', '侍者'], '手腕': ['画报', '办公室', '侍者']}[s.path]
        for j in pref:
            if av(j): return j
        return '侍者'
    def choose(s, xun, living):
        act = s.plan(s.path) or s.plan(s.second)
        if act is None: act = ('job', s.money_job())
        g = 9 if act[0] != 'job' else 9 * s.c['jobs'][act[1]]['fat']
        if s.fat >= 45 or (s.fat + g >= 50 + s.at['自律'] - 40 and s.fat >= 20): return ('rest', None)
        if act[0] == 'job' and s.at['自律'] < s.c['guard']: act = ('job', '教堂')
        reserve = living if xun == 2 else 0
        if act[0] == 'class':
            c = s.c['classes'][act[1]]; n = s.cls_n[act[1]]; t = s.c['thr']
            L = 0 if n < t[0] else 1 if n < t[1] else 2 if n < t[2] else 3
            if s.money - c['fee'][L] * 9 < reserve: act = ('job', s.money_job())
        elif act[0] == 'book':
            if s.book.get(act[1], 0) <= 0:
                price = s.c['books'][act[1][1]]['price']
                if s.money - price < reserve: act = ('job', s.money_job())
                else: s.money -= price; s.book[act[1]] = s.c['books'][act[1][1]]['pts']
        return act

    # ---------- 主循环 ----------
    def run(s):
        c = s.c
        for mi in range(1, c['months'] + 1):
            s.mi = mi; y = (mi - 1) // 12; m = (mi - 1) % 12 + 1; year = c['start'] + y
            living = c['living'][s.tier()]; s.money -= living
            if s.contract: s.money += c['salary']
            s.expo = False
            if c['buy']:
                it = ITEMS[s.path]
                if s.owned < len(it) and s.money - it[s.owned][0] >= 2 * living and (it[s.owned][1] > 0 or s.path in s.full):
                    s.money -= it[s.owned][0]; s.spent += it[s.owned][0]; s.equip += it[s.owned][1]; s.owned += 1
            if m in (1, 4, 7, 10): s.board(y, m)
            last = (datetime.date(year + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1)).day
            xs = [(1, 10), (11, 20), (21, last)]
            for xi, (a, b) in enumerate(xs):
                days = [datetime.date(year, m, d) for d in range(a, b + 1)]
                f = s.lock.get((mi, xi))
                if f: s.do_film(f, days); continue
                act = s.choose(xi, living)
                if act[0] == 'rest': s.do_rest(days)
                elif act[0] == 'class': s.do_class(act[1], days)
                elif act[0] == 'book': s.do_book(act[1], days)
                else: s.do_job(act[1], days)
            for f in s.release.get(mi, []): s.settle_release(f)
            if not s.expo: s.fame -= max(1, s.fame * 2 // 100)
            w = s.fat - s.at['自律']; s.wild = w if w >= 10 else 0
            s.debt_m += s.money < 0
            if c['long_contract'] and not s.contract and s.fame >= 300 and max(s.pres(p) for p in PATHS) >= 200 and random.random() < 1 / 6: s.contract = True
            if m == 12:
                p = s.path; my = s.pres(p) + random.randint(0, 50)
                ny = y; pi = PATHS.index(p)
                opp = sorted((5 * L * (L + 1) + random.randint(0, 50) for L in sorted((r[1][pi] for r in NAMED[ny]), reverse=True)[:5]), reverse=True)
                rank = sum(o > my for o in opp)
                if rank < 3: s.annual[p] += c['annual'][rank]; s.money += (1000, 500, 200)[rank]
                s.yearend.append(s.money)
            for p in PATHS:
                if s.train(p) >= 300 and p not in s.full: s.full[p] = mi
            for line in (150, 210):
                if s.pres(s.path) >= line and line not in s.milestone: s.milestone[line] = mi
            s.fame_hist.append(s.fame)
            for k in SK[s.path]:
                if s.sk[k] >= 100 and k not in s.skfull: s.skfull[k] = mi
            if s.path in s.full and s.cash_at_full is None: s.cash_at_full = s.money
        return s

def med(x): return statistics.median(x) if x else float('nan')
def report(cfg, n=200, label=''):
    print(f'== {label}  ({cfg["months"]} 个月, {n} 局/路)')
    print('路   满(中位/10%/90%) 满率 | 150月 210月 | 第二路满 | 年末现金中位数 | 负债月 | 期末现金 中位/90% | 练满+上映 中位(≥311率) | +年度 | 片 小/中/大 试镜胜率 大片过 | 期末名气 | 谈吐@满 | 口音罚 | 旬:课/书/工/休/拍')
    for p in PATHS:
        gs = [G(cfg, p, 1000 + i).run() for i in range(n)]
        fm = sorted(g.full.get(p, 999) for g in gs)
        q = lambda a: fm[int(len(fm) * a)]
        rate = sum(x < 999 for x in fm) / n
        ye = [int(med([g.yearend[i] for g in gs])) for i in range(cfg['months'] // 12)]
        endc = sorted(g.money for g in gs)
        base = [g.train(p) + g.corr[p] for g in gs]
        tot = [g.pres(p) for g in gs]
        sec = [g.full.get(g.second, 999) for g in gs]
        fl = [sum(g.films[i] for g in gs) / n for i in range(3)]
        aw = sum(g.aud[1] for g in gs) / max(1, sum(g.aud[0] for g in gs))
        bw = sum(g.bigtry[1] for g in gs) / max(1, sum(g.bigtry[0] for g in gs))
        use = [sum(g.use[k] for g in gs) / n for k in ('课', '书', '工', '休', '拍')]
        print(f'{p} {q(.5):>3}/{q(.1)}/{q(.9)} {rate:.0%} | {med([g.milestone.get(150, 99) for g in gs]):.0f} {med([g.milestone.get(210, 99) for g in gs]):.0f} | {med(sec):.0f} | {ye} | {statistics.mean(g.debt_m for g in gs):.1f} | {endc[n // 2]}/{endc[int(n * .9)]} | {med(base):.0f} ({sum(b >= 311 for b in base) / n:.0%}) | {med(tot):.0f} | {fl[0]:.1f}/{fl[1]:.1f}/{fl[2]:.1f} {aw:.0%} {bw:.0%} | {med([g.fame for g in gs]):.0f} | {med([g.sk["谈吐"] for g in gs]):.0f} | {statistics.mean(g.talk_pen for g in gs):.1f} | ' + '/'.join(f'{u:.0f}' for u in use))
        print('      各项满月', {k: med([g.skfull.get(k, 99) for g in gs]) for k in SK[p]}, '大卖率 %.0f%%' % (100 * sum(getattr(g, 'hit', 0) for g in gs) / max(1, sum(getattr(g, 'rel', 0) for g in gs))), '年末名气', [int(med([g.fame_hist[i * 12 + 11] for g in gs])) for i in range(cfg['months'] // 12)], '练满时现金', med([g.cash_at_full or 0 for g in gs]), '期末体力', med([g.at['体力'] for g in gs]), '自律', med([g.at['自律'] for g in gs]), '装备花费', med([g.spent for g in gs]))

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=400); ap.add_argument('--buy', action='store_true'); ap.add_argument('--contract', action='store_true')
    a = ap.parse_args()
    CFG['buy'] = a.buy; CFG['long_contract'] = a.contract
    report(CFG, n=a.n, label='GDD 当前数值' + ('，买本路装备' if a.buy else '') + ('，签长约' if a.contract else ''))
