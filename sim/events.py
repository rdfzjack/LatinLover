"""事件（GDD 5.4 接口、5.5.2 外出、6.5 Duv、11、12）。

事件数据在 events.json 和 outing.json，一个事件可以有：
    效果（直接执行）→ 判定（事件级，成功/失败效果）→ 分支（取第一个条件满足的）→ 选项（问玩家）→ 代码（`代码:true` 的按“说明”写在 CODE 里）
效果里的 `触发.<id>` 在最后依次触发。

频次：每局一次 / 每年一次 / 每季度一次 / null；外出事件的 一次性:true 同每局一次。

随机数的消耗顺序（Godot 照抄）：
- 月末：按 顺序 逐个看，条件满足且频次允许时才掷概率；机遇排在前辈认可（顺序 9）之后，按表的顺序。触发满 2 个就停。
- 旬初：临时换角、抢角，同上。
- 外出：有人在场且有链事件时不掷；常驻事件、随机表按权重 below(权重和)。
- 打工：每期随机按表的顺序各掷一次，然后看里程碑（不掷）。
- 家教旬：Duv 好感 ≥30 时掷 1/10 告密。
- 年度大事：先 r0(50) 我的分，再按排序后的对手各 r0(50)。
"""
from . import board, film, rules
from .schedule import add_stat

SCANDAL_PAY = 200          # 报馆线：花 200 压下丑闻（5.4）
ARREST_FINE = 500          # 被捕罚款上限（11.2）
HELP_YIQI = 150            # 义气 ≥150 有人帮（10.1）
HELP_COST = 30
SCANDAL_YIQI = 200
SLOTS = ('上', '中', '下')


# ---------- 频次 ----------
def can_fire(st, e):
    n = st.fired.get(e['id'], 0)
    if e.get('一次性') and n:
        return False
    f = e.get('频次')
    if not f or not n:
        return True
    last = st.story['末次'].get(e['id'], -99)
    if f == '每局一次':
        return False
    if f == '每年一次':
        return last // 12 != st.ym // 12
    if f == '每季度一次':
        return last // 3 != st.ym // 3
    raise ValueError(f)


def ready(st, e):
    return can_fire(st, e) and rules.cond(st, e.get('条件'))


# ---------- 触发 ----------
def fire(story, st, eid, depth=0):
    """触发一个事件并结算。返回 {'id', '选项', '判定'}。"""
    if depth > 8:
        raise RuntimeError(f'事件触发链太深：{eid}')
    d = st.d
    e = d.events[eid]
    st.fired[eid] = st.fired.get(eid, 0) + 1
    st.story['末次'][eid] = st.ym
    rec = {'id': eid, '月': st.date}
    trig = []
    if e.get('效果'):
        trig += rules.apply_effect(st, e['效果'], source='event')
    if e.get('判定'):
        ok = rules.check(st, e['判定'])
        rec['判定'] = ok
        trig += rules.apply_effect(st, e['成功效果' if ok else '失败效果'], source='event')
    for br in e.get('分支') or []:
        if rules.cond(st, br['条件']):
            trig += rules.apply_effect(st, br['效果'], source='event')
            break
    choice = None
    opts = e.get('选项') or []
    if opts:
        avail = [k for k, o in enumerate(opts) if rules.cond(st, o.get('条件'))]
        if avail:
            choice = story.agent.option(st, e, avail)
            if choice not in avail:
                raise ValueError(f'{eid} 选了不能选的选项 {choice}')
            o = opts[choice]
            ok = rules.check(st, o.get('判定') or None)
            rec['判定'] = ok
            trig += rules.apply_effect(st, o['成功效果' if ok else '失败效果'], source='event')
        rec['选项'] = choice
    h = CODE.get(eid)
    if h:
        trig += h(story, st, e, choice) or []
    story.log.append(rec)
    for t in trig:
        fire(story, st, t, depth + 1)
    return rec


# ---------- 代码事件 ----------
def fame_pct(st, pct):
    st.attr['名气'] = max(0, st.attr['名气'] + st.attr['名气'] * pct // 100)


def h_missing(story, st, e, ch):
    """失踪：下月日程作废，四项声望修正各减去当前声望的 10%。"""
    st.void_next = 1
    b = st.bonus()
    for r in st.d.roads:
        st.corr[r] -= st.rep(r, b) * 10 // 100
    film.breach_month(st, st.ym + 1)


def h_arrest(story, st, e, ch):
    """被捕：罚款 min(金钱, 500)，犯罪 +20，曝光。义气 ≥150 有人保释（罚款减半、不曝光、义气 -30）；
    酒吧老板的里程碑也让罚款减半（两者不叠加）。生病状态不会被捕（GDD 10）。"""
    if st.status['生病']:
        return
    fine = max(0, min(st.money, ARREST_FINE))
    bail = st.val('义气') >= HELP_YIQI
    if bail or st.flags.get('保释减半'):
        fine //= 2
    st.money -= fine
    add_stat(st, '犯罪', 20)
    if bail:
        add_stat(st, '义气', -HELP_COST)
    else:
        st.exposed = 1
    st.inc('计数.被捕')


def h_scandal(story, st, e, ch):
    """丑闻曝光：报馆线可压下（免费每年一次 / 花 200）；反派＋犯罪 ≥3 名气 +10%，否则 -15%
    （官方警告后加倍，义气 ≥200 减半）。"""
    y = st.ym // 12
    sv = st.story
    if st.flags.get('免费压丑闻') and sv['压丑闻年'] != y + 1 and story.agent.suppress(st, '免费'):
        sv['压丑闻年'] = y + 1
        st.inc('计数.压下丑闻')
        return
    if st.flags.get('丑闻预知') and st.money >= SCANDAL_PAY and story.agent.suppress(st, '花钱'):
        st.money -= SCANDAL_PAY
        st.inc('计数.压下丑闻')
        return
    st.exposed = 1
    st.inc('计数.丑闻')
    if st.tags.get('反派', 0) + st.tags.get('犯罪', 0) >= 3:
        fame_pct(st, 10)
        return
    pct = 15
    if st.flags.get('警告'):
        pct *= 2
        st.flags['警告'] = 0
    if st.val('义气') >= SCANDAL_YIQI:
        pct //= 2
    fame_pct(st, -pct)


def h_contract(story, st, e, ch):
    if ch == 1:
        st.story['长约拒绝'] = st.ym


def h_creditor(story, st, e, ch):
    """债主：码头同乡挡一次 → 义气 ≥150 朋友垫上 → 打斗 ≥50 赶走 → 拿走最贵的物品 → 名气 -10% 并曝光。"""
    if st.flags.get('同乡挡债') == 1:
        st.flags['同乡挡债'] = 2
        st.money = max(st.money, 0)
        st.debt_months = 0
        return
    if st.val('义气') >= HELP_YIQI:
        add_stat(st, '义气', -HELP_COST)
        st.money = max(st.money, 0)
        st.debt_months = 0
        return
    st.debt_months = 0
    if st.val('打斗') >= 50:
        add_stat(st, '犯罪', 10)
        return
    its = [i for i in st.items if st.d.items[i]['价格'] > 0]
    if its:
        top = max(its, key=lambda i: (st.d.items[i]['价格'], -its.index(i)))
        rules.remove_item(st, top)
        st.money = min(0, st.money + st.d.items[top]['价格'])
        return
    fame_pct(st, -10)
    st.exposed = 1


def h_drug_deeper(story, st, e, ch):
    if st.drug >= 3:
        add_stat(st, '体力', -30)
        add_stat(st, '犯罪', 20)


def h_detox(story, st, e, ch):
    """戒断：占掉整个下月。Sil 好感 ≥60（他在场）时 Sil +10。"""
    if st.favor.get('Sil', 0) >= 60:
        rules.apply_effect(st, '好感.Sil+10', source='event')
    st.void_next = 1
    film.breach_month(st, st.ym + 1)


def h_tip(story, st, e, ch):
    """Duv 的告密：下一块板上随机一个中片或大片角色显示完整场风和标签。"""
    if st.flags.get('告密'):
        st.flags['告密'] = 0
        st.story['告密'] += 1


def h_transform(story, st, e, ch):
    """片厂老板“支持转型”：之后 3 块板各多一个玩家指定戏路族的中片角色。"""
    fam = story.agent.family(st)
    if fam not in st.d.tag_families:
        raise ValueError(fam)
    st.story['转型'] = [board.cfg(st.d)['转型板数'], fam]


def h_birthday(story, st, e, ch):
    rules.apply_effect(st, '好感.女明星+3', source='event')


CODE = {
    'evt_missing': h_missing, 'evt_arrest': h_arrest, 'evt_scandal': h_scandal, 'evt_contract': h_contract,
    'evt_creditor': h_creditor, 'evt_drug_deeper': h_drug_deeper, 'evt_detox': h_detox,
    'outing_duv_tip': h_tip, 'job_studio_m2': h_transform, 'evt_birthday': h_birthday,
}
# 其余 代码:true 的事件只要数据里的效果、旗标就够了，由别的模块读旗标：
#   evt_swap_role / evt_steal_role（旬初，period_start）、evt_accent（旗标）、era_valen_death（board 读旗标）、
#   era_talkie（日期已在表里）、job_studio_m1（长约概率已按好感分档写在 evt_contract）。


# ---------- 月末（11.2、12.2） ----------
def month_end_list(d):
    evs = sorted((e for e in d.events.values() if e.get('类') == '月末' and e.get('时机') == '月末'),
                 key=lambda e: e['顺序'])
    out = []
    for e in evs:
        out.append(('事件', e))
    k = max(i for i, (_, e) in enumerate(out) if e['顺序'] <= 9)
    return out[:k + 1] + [('机遇', o) for o in d.opps] + out[k + 1:]


def month_end(story, st):
    d = st.d
    if st.status['长约']:
        st.add_money(d.contract['长约']['月薪'])
    lim = d.t['events']['月末上限']
    n = 0
    for kind, e in month_end_list(d):
        if n >= lim:
            break
        if kind == '机遇':
            if st.fired.get(e['剧情']) or not rules.cond(st, e['条件']):
                continue
            if not rules.prob(st, e['每月概率']):
                continue
            fire(story, st, e['剧情'])
            rules.apply_effect(st, e['效果'], source='event')   # 机遇的效果写在 opportunities.json，剧情事件只管剧情
            st.inc('计数.机遇')
            if e['占月']:
                st.void_next = 1
                film.breach_month(st, st.ym + 1)
            n += 1
            continue
        if not ready(st, e):
            continue
        if e['id'] == 'evt_contract' and st.ym - st.story['长约拒绝'] < d.contract['长约']['拒绝后月数']:
            continue
        if not rules.prob(st, e['概率']):
            continue
        fire(story, st, e['id'])
        n += 1


# ---------- 旬初（11.1） ----------
def period_start(story, st, i, entry):
    if entry.startswith('rest_'):
        return
    d = st.d
    e = d.events['evt_swap_role']
    nxt = film.next_period(st, i)
    if (ready(st, e) and not film.is_locked(st, *nxt) and nxt[0] < len(d.months)
            and rules.prob(st, e['概率'])):
        fire(story, st, e['id'])
        board.swap_role(st, i, story.agent)
    e = d.events['evt_steal_role']
    if ready(st, e) and rules.prob(st, e['概率']):
        fire(story, st, e['id'])
        board.steal_role(st, story.agent)


def period_end(story, st, i, entry, out):
    d = st.d
    if entry == 'class_tutor' and out.get('上课日'):
        e = d.events['outing_duv_script']
        if ready(st, e):
            fire(story, st, e['id'])
        if st.favor.get('Duv', 0) >= 30 and st.rng.logic.chance(1, 10):
            fire(story, st, 'outing_duv_tip')
    duv = d.npcs['Duv'].get('教育里程碑')
    if duv and 'Duv' in st.known:
        for line in duv['线']:
            k = f'Duv教育{line}'
            if not st.flags.get(k) and st.val('教育') >= line:
                st.flags[k] = 1
                rules.apply_effect(st, duv['效果'], source='event')


# ---------- 外出（5.5.2） ----------
def meet(st, npc):
    if npc not in st.known:
        st.known.append(npc)
        st.known.sort()
    st.inc('计数.遇见.' + npc)


def present(st, place, i):
    m = int(st.date[5:])
    y = int(st.date[:4])
    out = []
    for s in st.d.schedule_npc:
        if (s['地点'] == place and s['年份'][0] <= y <= s['年份'][1] and m in s['月份']
                and SLOTS[i] in s['旬'] and rules.cond(st, s['条件']) and s['npc'] not in out):
            out.append(s['npc'])
    return out


def weighted(st, pairs):
    """pairs：[(权重, 值)]，按权重抽一个；空表返回 None。"""
    tot = sum(w for w, _ in pairs)
    if tot <= 0:
        return None
    v = st.rng.logic.below(tot)
    for w, x in pairs:
        if v < w:
            return x
        v -= w
    raise AssertionError


def npc_event(st, npc):
    """在场 NPC 的下一个链事件（没看过、条件满足）；没有返回 None。"""
    d = st.d
    for ch in d.chains:
        if ch['npc'] == npc and ch['触发'] == '外出':
            for eid in ch['链']:
                if ready(st, d.events[eid]):
                    return eid
    return None


def npc_resident(st, npc):
    d = st.d
    pairs = []
    for ch in d.chains:
        if ch['npc'] == npc and ch['触发'] == '外出':
            pairs += [(c['权重'], c['事件']) for c in ch['常驻'] if ready(st, d.events[c['事件']])]
    return pairs


def outing(story, st, place):
    """外出的旬中触发恰好一个事件。有人在场且他有链事件或常驻事件就出他的，否则抽地点的随机表。"""
    d = st.d
    i = story.cur_period
    people = present(st, place, i)
    for npc in people:
        meet(st, npc)
    eid = None
    for npc in people:
        eid = npc_event(st, npc)
        if eid:
            break
    if eid is None:
        for npc in people:
            pairs = npc_resident(st, npc)
            if pairs:
                eid = weighted(st, pairs)
                break
    if eid is None:
        pairs = [(x['权重'], x['事件']) for x in d.places[place]['随机表'] if ready(st, d.events[x['事件']])]
        eid = weighted(st, pairs)
    if eid:
        fire(story, st, eid)
    return eid


def class_chain(story, st, chain, n):
    """家教第 1、4、7、10 旬：Duv 的家教链，按顺序出下一个没看过的。"""
    d = st.d
    ch = next(c for c in d.chains if c['id'] == chain)
    meet(st, ch['npc'])
    for eid in ch['链']:
        if ready(st, d.events[eid]):
            fire(story, st, eid)
            return eid
    return None


def book_done(story, st, bid):
    eid = st.d.books[bid].get('读完事件')
    if eid and ready(st, st.d.events[eid]):
        fire(story, st, eid)


# ---------- 打工接口（5.4） ----------
def job_period(story, st, jid, good):
    d = st.d
    j = d.jobs[jid]
    if good and j['npc']:
        meet(st, j['npc'])
    for r in j['每期随机']:
        if st.rng.logic.chance(*r['概率']):
            fire(story, st, r['事件'])
    for m in j['里程碑']:
        e = d.events[m['事件']]
        if not st.fired.get(e['id']) and rules.cond(st, m['条件']):
            fire(story, st, e['id'])


# ---------- 生日 ----------
def day(story, st, dd):
    e = st.d.events['evt_birthday']
    bd = e.get('日期')
    if bd and st.date[5:] == bd[:2] and dd == int(bd[3:]):
        fire(story, st, e['id'])


# ---------- 时代、年度大事（11.3、12.1） ----------
def era(story, st, ids):
    for eid in ids:
        fire(story, st, eid)


def annual_rivals(st, road):
    """当年在场的有名对手（不含彩蛋）里取该路等级最高的 5 人：[(id, 等级)]。"""
    d = st.d
    k = d.roads.index(road)
    out = []
    for rid, r in d.rivals_named.items():
        if r.get('说明', '').startswith('彩蛋') or not (r['在场'][0] <= st.date <= r['在场'][1]):
            continue
        lv = None
        for s in r['阶段']:
            if st.date >= s['自']:
                lv = s['等级'][k]
        out.append((rid, lv))
    out.sort(key=lambda x: -x[1])
    return out[:5]


def annual(story, st):
    """12 月：四个场合选一个参加，或休息（疲劳清零）。排名：我的分 = 该路声望 + r0(50)；
    对手分 = 5L(L+1) + r0(50)；对手分 ≥ 我的分算在我前面。"""
    d = st.d
    a = d.t['annual']
    opts = [x for x in a['场合'] if rules.cond(st, x['条件'])]
    pick = story.agent.annual(st, opts)
    rec = {'月': st.date, '场合': pick}
    if pick is None:
        st.attr['疲劳'] = 0
        story.annuals.append(rec)
        return rec
    occ = next(x for x in opts if x['id'] == pick)
    g = st.rng.logic
    me = st.rep(occ['路']) + g.r0(50)
    rank = 1
    for rid, L in annual_rivals(st, occ['路']):
        if 5 * L * (L + 1) + g.r0(50) >= me:
            rank += 1
    rec['名次'] = rank
    for rw in a['排名']['奖励']:
        if rw['名次'] == rank:
            st.corr[occ['路']] += rw['修正']
            st.add_money(rw['奖金'])
    st.inc(f'计数.年度名次.{rank}')
    story.annuals.append(rec)
    return rec
