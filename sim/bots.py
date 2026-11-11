"""策略机器人（PLAN 第 7 步）：接在 story.Agent 上，用来批量跑整局。

机器人 = 开局三问的选项 + 每月排三旬的 plan(g) + Agent 的各个决定。
    from sim.bots import BOTS, play
    rec = play(BOTS['专练情人'], seed=1)      # 跑完一局，返回一份记录（sim.report 汇总它）

八种机器人（BOTS 里的名字）：
    专练硬汉 / 专练情人 / 专练文化 / 专练手腕   练满一路再练一条副路，剩下的旬打工赚钱
    两路（硬汉+情人）                           两路里训练值低的先练
    乱选                                        日程、试镜、事件选项全随机（用自己的随机流，不动游戏的）
    犯罪线                                      只打犯罪类的工：运私酒、看场子、码头
    只读书文化                                  不上课，只读书；教育不够读下一本时才上家教

日程的做法照 tools/pacing_trial.py 的机器人：疲劳高了就休息，钱不够上课就去打工，钱够就买书。
决定都在月初（排日程时）做；本月内的疲劳、钱用估计值往前推。

试镜：组牌和选角色用一个快速的胜率估计（双方随机出牌时，主色/副色各种组法的胜率按场风加权），
出牌用“能赢几张对手的牌”的贪心（`smart_play=False` 时随机出，对照 N60 的随机配对用）。
"""
import itertools
import random

from . import audition, rules, schedule, street
from .story import SimpleAgent, fit_plan, new_game
from . import film

# ---------- 试镜的快速估计 ----------
_PERMS = list(itertools.permutations(range(5)))


class Est:
    """胜率估计，按 Data 缓存常量。"""

    def __init__(self, d):
        c = audition.cfg(d)
        self.d = d
        self.bt = audition.beats(d)
        self.fp = c['场风百分比']
        self.win_pct = c['克制方百分比']
        self.lose_pct = c['被克方百分比']
        self.need = c['赢轮数']
        self.cache = {}

    def beat(self, a, b, field, fame_hi):
        (ca, pa), (cb, pb) = a, b
        va, vb = pa * 100, pb * 100
        if ca == field:
            va = va * self.fp // 100
        if cb == field:
            vb = vb * self.fp // 100
        if self.bt[ca] == cb and cb != field:
            va, vb = va * self.win_pct // 100, vb * self.lose_pct // 100
        elif self.bt[cb] == ca and ca != field:
            vb, va = vb * self.win_pct // 100, va * self.lose_pct // 100
        return va > vb if va != vb else fame_hi

    def p_field(self, mine, theirs, field, fame_hi):
        """双方随机出牌时我方先赢够 need 轮的概率（枚举对手出牌顺序的 120 种排列）。"""
        m = [[self.beat(a, b, field, fame_hi) for b in theirs] for a in mine]
        need, n = self.need, 0
        for p in _PERMS:
            w = 0
            for i in range(5):
                if m[i][p[i]]:
                    w += 1
                    if w >= need:
                        n += 1
                        break
                elif i - w + 1 >= need:
                    break
        return n / 120

    def best(self, levels, rival, probs, fame_me):
        """对 rival 的最佳牌组：(胜率, 颜色列表)。候选 = 纯色，或主色 4/3 张加一种副色。"""
        d = self.d
        fame_hi = fame_me > rival['名气']
        key = (tuple(levels), tuple(rival['等级']), rival['k'], tuple(probs), fame_hi)
        r = self.cache.get(key)
        if r is None:
            theirs = audition.opponent_deck(d, rival, probs)
            r = (-1, None)
            for cols in audition.candidate_decks(levels).values():
                mine = audition.build_deck(levels, cols)
                p = sum(probs[f] * self.p_field(mine, theirs, f, fame_hi) for f in range(4) if probs[f]) / 100
                if p > r[0]:
                    r = (p, cols)
            if len(self.cache) > 20000:
                self.cache.clear()
            self.cache[key] = r
        return r


_EST = {}


def est_of(d):
    e = _EST.get(id(d))
    if e is None:
        e = _EST[id(d)] = Est(d)
    return e


# ---------- 日程的小工具 ----------
CRIME_JOBS = ('job_bootleg', 'job_escort', 'job_bar')    # 赚钱用的工里先排除的
THRESH = {'大': 0.12, '中': 0.2, '小': 0.0}                # 选角色：胜率估计低于这条线就不去
ROAD_PLACE = {'硬汉': 'place_dock', '情人': 'place_downtown', '文化': 'place_downtown', '手腕': 'place_studio'}
ROAD_JOBS = {'文化': ('job_news', 'job_model_art')}      # 缺钱时先打本路的工（文化路的两个机遇要这两种工的期数）


def workdays(st, i):
    return sum(1 for _, sun in schedule.days_of(st, i) if not sun)


def alldays(st, i):
    return len(schedule.days_of(st, i))


def job_fat(j):
    return sum(e['加'][0] for e in j['每天效果'] if e['项'] == '疲劳')


def can_do_job(st, jid, margin=10):
    """能选、且显示值比成功线高出 margin（疲劳会扣）。"""
    if schedule.validate(st, jid) is not None:
        return False
    j = st.d.jobs[jid]
    return all(st.val(k) - margin >= v for k, v in schedule.job_lines(st, j))


def best_equip(st, road):
    """把持有的服装、配饰换成让 road 声望最高的一套，返回换完的声望。"""
    d = st.d
    cl = [None] + sorted({i for i in st.items if d.items[i]['槽'] == '服装'})
    ac = sorted({i for i in st.items if d.items[i]['槽'] == '配饰'})
    n = d.t['items']['规则']['配饰槽']
    best = None
    for c in cl:
        for k in range(min(n, len(ac)), -1, -1):
            for a in itertools.combinations(ac, k):
                st.equip = {'服装': c, '配饰': list(a)}
                r = st.rep(road)
                if best is None or r > best[0]:
                    best = (r, c, list(a))
    st.equip = {'服装': best[1], '配饰': best[2]}
    return best[0]


class Bot(SimpleAgent):
    name = '?'
    origin = (0, 0, 3)          # 开局三问；第三问选“戒指”：只给一个旗标，不改数值，方便和 N60 对
    smart_play = True
    crime = False
    buy = True                  # 月初买本路装备（report 的 --no-buy 关掉）
    gear_road = None            # 买哪条路的装备；None = 不买

    def __init__(self, seed=1):
        self.rnd = random.Random(seed * 1000003 + 17)   # 机器人自己的随机流，不动游戏的
        self.seed = seed

    # ---------- 试镜 ----------
    def deck(self, st, ctx):
        rv, role = ctx['对手'], ctx['角色']
        return est_of(st.d).best(ctx['等级'], rv, role['场风概率'], st.attr['名气'])[1]

    def play(self, st, ctx):
        hand = ctx['手牌']
        if not self.smart_play:
            return st.rng.logic.below(len(hand))
        d, field = st.d, ctx['场风']
        fame_me, fame_them = st.attr['名气'], ctx['对手']['名气']
        best, bi = None, 0
        for i, a in enumerate(hand):
            w = sum(audition.round_winner(d, a, b, field, fame_me, fame_them) for b in ctx['对手手牌'])
            k = (w, -a[1])          # 能赢的多的优先，一样多时先出点数小的
            if best is None or k > best:
                best, bi = k, i
        return bi

    def role_p(self, st, e):
        """报名这个角色的胜率估计：各场相乘。"""
        est = est_of(st.d)
        lv = audition.player_levels(st)
        p = 1.0
        for rv in e['对手']:
            p *= est.best(lv, rv, e['场风概率'], st.attr['名气'])[0]
        return p

    def pick_role(self, st, b, ok):
        """从高档往低档看：最好的那个角色胜率过线就去，否则往下一档。"""
        by = {}
        for i in ok:
            by.setdefault(b['角色'][i]['档次'], []).append(i)
        for t in ('大', '中', '小'):
            if t not in by:
                continue
            ps = [(self.role_p(st, b['角色'][i]), -i) for i in by[t]]
            p, ni = max(ps)
            if p >= THRESH[t]:
                return -ni
        return None

    # ---------- 买装备 ----------
    def month_start(self, story, st):
        """月初买本路装备：每次挑“每块钱加的声望最多”的一件，留两个月生活费加 200。"""
        road = self.gear_road
        if not self.buy or road is None:
            return
        reserve = 2 * self.living(st) + 200
        for _ in range(4):
            base, best = st.rep(road), None
            for entry in ('服装店', '杂货店'):
                for iid in street.shelf(st, entry):
                    it = st.d.items[iid]
                    if it['类'] == '消耗' or iid in st.items:
                        continue
                    p = street.price(st, entry, it['价格'])
                    if st.money - p < reserve:
                        continue
                    old = dict(st.equip, 配饰=list(st.equip['配饰']))
                    st.items.append(iid)
                    gain = best_equip(st, road) - base
                    st.items.remove(iid)
                    st.equip = old
                    if gain > 0 and (best is None or gain / p > best[0]):
                        best = (gain / p, entry, iid)
            if best is None:
                break
            street.buy(st, best[1], best[2])
            st.inc('计数.买装备花费', street.price(st, best[1], st.d.items[best[2]]['价格']))
        best_equip(st, road)

    # ---------- 日程 ----------
    def plan(self, g):
        st = g.st
        if st.forced_rest or st.void_next:
            return ['rest_home'] * 3
        P = {'fat': st.val('疲劳'), 'money': st.money, 'cls': {}}
        out = []
        for i in range(3):
            f = g.hooks.locked(st, i)
            if f:
                P['fat'] += workdays(st, i) * film.shoot_cfg(st.d)['疲劳'][f['档次']]
                out.append('rest_home')
                continue
            e = self.pick(g, P, i)
            self.apply(g, P, i, e)
            out.append(e)
        return out

    def living(self, st):
        return st.d.lifestyles[st.lifestyle]['月费'][st.fame_tier()]

    def delta(self, g, P, i, e):
        """估计这一旬的 (疲劳变化, 钱变化)。"""
        st, d = g.st, g.d
        kind, iid, place = schedule.parse_entry(e)
        w, n = workdays(st, i), alldays(st, i)
        if kind == 'class':
            k = st.cnt('旬数.' + iid) + P['cls'].get(iid, 0) + 1
            L = 1 + sum(1 for s in d.class_steps if k > s)
            return w, -d.classes[iid]['学费'][L - 1] * w
        if kind == 'book':
            return w, 0
        if kind == 'job':
            return w * job_fat(d.jobs[iid]), int(schedule.wage_of(st, iid) * w * 0.7)
        if iid == 'rest_outing':
            return -10 * n, -d.places[place]['花费'] * n
        if iid == 'rest_sanatorium':
            return -11 * n, -8 * n
        if iid == 'rest_vacation':
            return -P['fat'], -schedule.vacation_cost(st)
        return -5 * n, 0

    def apply(self, g, P, i, e):
        df, dm = self.delta(g, P, i, e)
        P['fat'] = max(0, P['fat'] + df)
        P['money'] += dm
        kind, iid, _ = schedule.parse_entry(e)
        if kind == 'class':
            P['cls'][iid] = P['cls'].get(iid, 0) + 1

    def rest_entry(self, g, P, i):
        st = g.st
        place = self.place
        if st.status['生病'] or P['money'] < 60 + g.d.places[place]['花费'] * 10:
            return 'rest_home'
        return 'rest_outing@' + place

    place = 'place_downtown'

    def pick(self, g, P, i):
        st, d = g.st, g.d
        want = self.want(g, P, i)
        if want is None:
            want = self.money_job(g, P)
        if want is None:
            return self.rest_entry(g, P, i)
        kind = schedule.parse_entry(want)[0]
        # 钱不够上课、买书：去打工
        df, dm = self.delta(g, P, i, want)
        reserve = self.living(st) if i == 2 else 0
        if kind == 'class' and P['money'] + dm < reserve:
            want = self.money_job(g, P)
            if want is None:
                return self.rest_entry(g, P, i)
            df, dm = self.delta(g, P, i, want)
            kind = 'job'
        # 疲劳高了就休息（照 pacing_trial：≥45，或加上这旬会过“自律线”）
        fat = P['fat']
        sta, disc = st.val('体力'), st.val('自律')
        if fat >= 45 or (fat >= 20 and (fat + df >= 10 + disc or fat + df >= sta + 5)):
            return self.rest_entry(g, P, i)
        # 自律低了去教堂义工
        if kind == 'job' and not self.crime and disc < 35 and can_do_job(st, 'job_church', 0):
            return 'job_church'
        return want

    # ---------- 找活 ----------
    def want(self, g, P, i):
        raise NotImplementedError

    def job_for(self, g, P, need, crime_ok=False):
        """每天给 need 里还没满的技能加得最多的工（扣疲劳、犯罪、自律的代价）。"""
        st, d = g.st, g.d
        best = None
        for jid, j in d.jobs.items():
            if not can_do_job(st, jid):
                continue
            if not crime_ok and jid in CRIME_JOBS and jid != 'job_bar':
                continue
            gain = sum((e['加'][0] + e['加'][1]) / 2 for e in j['每天效果']
                       if e['项'] in need and st.skill.get(e['项'], 100) < 100)
            if gain <= 0:
                continue
            pen = 0.05 * job_fat(j)
            for e in j['每天效果']:
                if e['项'] == '犯罪' and e['加'][0] > 0 and not crime_ok:
                    pen += 0.15 * e['加'][0]
                if e['项'] == '自律' and e['加'][1] < 0:
                    pen += 0.1 * -e['加'][1]
            score = gain - pen + 0.01 * schedule.wage_of(st, jid)
            if best is None or score > best[0]:
                best = (score, jid)
        return best[1] if best else None

    def money_job(self, g, P, allow=None):
        """赚钱：日薪减 1.5×每天疲劳，排除犯罪类的工。本路有对口的工（ROAD_JOBS）先打它。"""
        st, d = g.st, g.d
        for jid in ROAD_JOBS.get(getattr(self, 'road', None), ()):
            if can_do_job(st, jid):
                return jid
        best = None
        for jid, j in d.jobs.items():
            if jid in CRIME_JOBS and not self.crime:
                continue
            if not can_do_job(st, jid):
                continue
            score = schedule.wage_of(st, jid) - 1.5 * job_fat(j)
            if best is None or score > best[0]:
                best = (score, jid)
        return best[1] if best else None

    def book_for(self, st, skill):
        """这个技能下一本值得读的书：(档, 书 id) 或 None。教育不够时返回 ('教育', 门槛)。"""
        d = st.d
        caps = {1: 40, 2: 70, 3: 100}
        for t in (1, 2, 3):
            if st.skill[skill] >= caps[t]:
                continue
            b = next((x for x in d.books.values() if x['技能'] == skill and x['档'] == t), None)
            if b is None:
                return None
            if b['id'] in st.read_books:
                continue
            if b['id'] not in street.shelf(st, '书店') and b['id'] not in st.books:
                return None
            if st.val('教育') < b['教育门槛']:
                return ('教育', b['教育门槛'])
            return (t, b['id'])
        return None

    def book_entry(self, g, P, skill):
        """要读的书的日程项（没有就先买）；书不可读、买不起返回 None。"""
        st, d = g.st, g.d
        r = self.book_for(st, skill)
        if r is None or r[0] == '教育':
            return None
        bid = r[1]
        if bid not in st.books:
            price = street.price(st, '书店', d.books[bid]['价格'])
            if P['money'] - price < self.living(st):
                return None
            street.buy(st, '书店', bid)
            P['money'] -= price
        return bid

    def want_road(self, g, P, road):
        st = g.st
        sk, ed = st.skill, st.val('教育')
        if road == '情人':
            for s, c in (('演技', 'class_acting'), ('打扮', 'class_etiquette'), ('体态', 'class_dance')):
                if sk[s] < 100:
                    return c
        elif road == '硬汉':
            for s, c in (('打斗', 'class_boxing'), ('骑马驾驶', 'class_riding')):
                if sk[s] < 100:
                    return c
            if sk['胆识'] < 100:
                return self.job_for(g, P, ['胆识'])
        elif road == '文化':
            if sk['创作'] < 100 or ed < 300:
                return 'class_tutor'
            for s in ('审美', '谈吐'):
                e = self.book_entry(g, P, s)
                if e:
                    return e
        elif road == '手腕':
            if ed < 200 and (sk['谈判'] < 70 or sk['生意'] < 70):
                return 'class_tutor'
            for s in ('谈判', '生意'):
                e = self.book_entry(g, P, s)
                if e:
                    return e
            need = [s for s in g.d.road_skills['手腕'] if sk[s] < 100]
            if need:
                return self.job_for(g, P, need)
        return None


class RoadBot(Bot):
    """专练一路，练满后练副路。"""
    road = second = None

    def want(self, g, P, i):
        return self.want_road(g, P, self.road) or self.want_road(g, P, self.second)

    @property
    def place(self):
        return ROAD_PLACE[self.road]

    @property
    def gear_road(self):
        return self.road


class Hard(RoadBot):
    name, road, second, origin = '专练硬汉', '硬汉', '情人', (0, 0, 3)


class Lover(RoadBot):
    name, road, second, origin = '专练情人', '情人', '硬汉', (3, 2, 3)


class Culture(RoadBot):
    name, road, second, origin = '专练文化', '文化', '情人', (4, 1, 3)


class Wrist(RoadBot):
    name, road, second, origin = '专练手腕', '手腕', '情人', (1, 1, 3)


class Two(Bot):
    name, origin = '两路（硬汉+情人）', (0, 2, 3)
    roads = ('硬汉', '情人')
    gear_road = '硬汉'
    place = 'place_studio'

    def want(self, g, P, i):
        st = g.st
        tr = lambda r: sum(st.skill[s] for s in g.d.road_skills[r])
        for r in sorted(self.roads, key=tr):
            w = self.want_road(g, P, r)
            if w:
                return w
        return None


class Crime(Bot):
    name, origin, crime = '犯罪线', (1, 0, 3), True
    place = 'place_dock'

    def want(self, g, P, i):
        st = g.st
        # 每月上旬去拳馆（黑帮头目、打手头子要硬汉 210），其余时间打犯罪类的工
        if i == 0 and st.skill['打斗'] < 100 and st.cnt('成功期数.job_bar') >= 3:
            return 'class_boxing'
        for jid in ('job_bootleg', 'job_bar', 'job_dock'):
            if can_do_job(st, jid):
                return jid
        return None


class BookCulture(Bot):
    name, origin = '只读书文化', (4, 1, 3)
    place = 'place_downtown'
    gear_road = '文化'

    def want(self, g, P, i):
        st = g.st
        sk = st.skill
        blocked = False
        for s in sorted(('创作', '审美', '谈吐'), key=lambda s: sk[s]):
            r = self.book_for(st, s)
            if r is None:
                continue
            if r[0] == '教育':
                blocked = True
                continue
            e = self.book_entry(g, P, s)
            if e:
                return e
        return 'class_tutor' if blocked else None


class Random(Bot):
    name = '乱选'

    def __init__(self, seed=1):
        super().__init__(seed)
        self.origin = tuple(self.rnd.randrange(n) for n in (5, 4, 6))
        self.smart_play = False

    def plan(self, g):
        st = g.st
        ops = schedule.options(st)
        return [self.rnd.choice(ops) for _ in range(3)]

    def deck(self, st, ctx):
        return [self.rnd.randrange(4) for _ in range(5)]

    def play(self, st, ctx):
        return self.rnd.randrange(len(ctx['手牌']))

    def pick_role(self, st, b, ok):
        return self.rnd.choice(ok) if self.rnd.random() < 0.6 else None

    def accept_support(self, st, role):
        return self.rnd.random() < 0.5

    def go_personally(self, st, role):
        return self.rnd.random() < 0.5

    def option(self, st, ev, avail):
        return self.rnd.choice(avail)

    def annual(self, st, opts):
        return self.rnd.choice([None] + [x['id'] for x in opts])

    def suppress(self, st, kind):
        return self.rnd.random() < 0.5


BOTS = {c.name: c for c in (Hard, Lover, Culture, Wrist, Two, Crime, BookCulture, Random)}
PURE = ('专练硬汉', '专练情人', '专练文化', '专练手腕')


# ---------- 跑一局 ----------
def play(cls, seed, data=None, smart_play=None, buy=None):
    """跑完一局，返回记录。记录里的数组下标 = 月序（月结后的值）。"""
    bot = cls(seed)
    if smart_play is not None:
        bot.smart_play = smart_play
    if buy is not None:
        bot.buy = buy
    g = new_game(seed, bot.origin, bot, data)
    st, d = g.st, g.d
    rec = {'bot': cls.name, 'seed': seed, 'origin': bot.origin,
           'train': [], 'rep': [], 'money': [], 'fame': [], 'debt': 0}
    while not st.finished:
        g.start_month()
        g.run_month(fit_plan(g, bot.plan(g)))
        rec['train'].append([sum(st.skill[s] for s in d.road_skills[r]) for r in d.roads])
        b = st.bonus()
        rec['rep'].append([st.rep(r, b) for r in d.roads])
        rec['money'].append(st.money)
        rec['fame'].append(st.attr['名气'])
        rec['debt'] += st.money < 0
    rec.update(summarize(g))
    return rec


def summarize(g):
    st, d = g.st, g.d
    res = st.story['结局']
    c = st.count
    rec = {'结局': res['结局'], '大类': res.get('大类'), '档次': res.get('档次'), '总分': res.get('总分'),
           '月数': len(g.hooks.boards) and st.ym,
           '名气': st.attr['名气'], '名气档': st.fame_tier(),
           '最高声望': rules.get_var(st, '最高声望')}
    for k in ('计数.试镜', '计数.试镜拿到', '计数.试镜.大', '计数.试镜.中', '计数.试镜.小',
              '计数.试镜拿到.大', '计数.试镜拿到.中', '计数.试镜拿到.小', '计数.上映', '计数.大卖',
              '计数.扑街', '计数.配角', '计数.违约', '计数.主演.大', '计数.主演.中', '计数.主演.小',
              '计数.被捕', '计数.丑闻', '计数.机遇'):
        rec[k] = c.get(k, 0)
    # 年度大事给的声望修正，算“练满加普通上映”时要减掉
    ann = {r: 0 for r in d.roads}
    rw = {x['名次']: x['修正'] for x in d.t['annual']['排名']['奖励']}
    occ = {x['id']: x['路'] for x in d.t['annual']['场合']}
    for a in g.hooks.annuals:
        if a.get('场合') and a.get('名次') in rw:
            ann[occ[a['场合']]] += rw[a['名次']]
    b = st.bonus()
    rec['无年度声望'] = max(st.rep(r, b) - ann[r] for r in d.roads)
    rec['年度修正'] = sum(ann.values())
    # 主路（期末声望最高的路）的声望拆开：训练值 / 装备和体力加成 / 上映 / 年度 / 其余（机遇、事件）
    top = max(d.roads, key=lambda r: st.rep(r, b))
    tr = sum(st.skill[s] for s in d.road_skills[top])
    rel = sum(f['结果']['修正'] for f in st.story['片'] if f.get('结果') and f['角色']['路'] == top)
    rec['拆'] = {'训练': tr, '加成': sum(st.val(s, b) for s in d.road_skills[top]) - tr, '上映': rel,
                '年度': ann[top], '机遇': st.corr[top] - rel - ann[top]}
    rec['普通声望'] = tr + rec['拆']['加成'] + rel       # “练满加普通上映”（含装备）
    rec['买装备'] = c.get('计数.买装备花费', 0)
    rec['片酬'] = sum(f.get('片酬', 0) for f in st.story['片'] if f.get('结果'))
    rec['年度名次'] = [a.get('名次') for a in g.hooks.annuals]
    return rec
