"""日程：上课、看书、打工、休息（GDD 5.1–5.5）。一旬一项，逐日结算。

日程项写成字符串：课 'class_boxing'、书 'book_tantu_1'、工 'job_dock'、休息 'rest_home'，
外出带去处 'rest_outing@place_dock'。休息只有两种：在家（Sil 陪着）和外出；疗养院只在重病时由月流程强制。

随机数的消耗顺序（Godot 移植要照抄）：
- 上课、看书：每个上课日先 r0(疲劳)、再 r0(体力/2)；恋爱状态再掷一次 20%；成功日按表的顺序掷各项收益。
- 打工：每个工作日先按表的顺序掷每天效果（含疲劳），再按成功线顺序各掷一次 r0(疲劳)，
  然后恋爱 20%、失控偷懒 40%/80%（各自只在该状态下掷）。
"""
from . import rules


class ScheduleError(Exception):
    pass


def parse_entry(e):
    """'rest_outing@place_dock' -> ('rest', 'rest_outing', 'place_dock')"""
    base, _, place = e.partition('@')
    kind = base.split('_', 1)[0]
    if kind not in ('class', 'book', 'job', 'rest'):
        raise ScheduleError(f'日程项不认识：{e}')
    return kind, base, place or None


def add_stat(st, name, v):
    """给属性或技能训练值加 v，夹在范围内。"""
    d = st.d
    if name in st.attr:
        lo, hi = d.attr_range[name]
        st.attr[name] = max(lo, min(hi, st.attr[name] + v))
    elif name in st.skill:
        lo, hi = d.skill_range[name]
        st.skill[name] = max(lo, min(hi, st.skill[name] + v))
    else:
        raise KeyError(name)


def days_of(st, i):
    """第 i 旬（0 上、1 中、2 下）的日子：[(日, 是否周日)]。"""
    m = st.month
    a, b = m['旬'][i]
    sun = set(m['周日'])
    return [(x, x in sun) for x in range(a, b + 1)]


def class_level(st, cid):
    """本旬的课程等级 1–4：上过的旬数（含本旬）≤3 为 1 级，≤6 为 2 级，≤9 为 3 级（GDD 5.2）。"""
    n = st.cnt('旬数.' + cid) + 1
    L = 1
    for step in st.d.class_steps:
        if n > step:
            L += 1
    return L


# ---------- 能不能选 ----------
def job_unlocked(st, jid):
    j = st.d.jobs[jid]
    return st.ym >= st.d.month_index[j['最早时间']] and rules.cond(st, j['前置'])


def job_refused(st, jid):
    r = st.d.job_rules['拒绝']
    return jid not in r['例外'] and rules.cond(st, r['条件'])


def book_on_shelf(st, bid):
    b = st.d.books[bid]
    s = b.get('上架')
    return s is None or st.ym >= st.d.month_index[s]


def validate(st, e):
    """返回 None（可以选）或不能选的原因。钱不够上课不算不能选：没钱的那天不上（GDD 5.3，原版“金額不足”）。"""
    try:
        kind, iid, place = parse_entry(e)
    except ScheduleError as x:
        return str(x)
    d = st.d
    if kind == 'class':
        return None if iid in d.classes else f'没有这门课 {iid}'
    if kind == 'book':
        if iid not in d.books:
            return f'没有这本书 {iid}'
        if iid not in st.books:
            return '没有这本书，或已经读完'
        if st.val('教育') < d.books[iid]['教育门槛']:
            return '教育不到门槛'
        return None
    if kind == 'job':
        if iid not in d.jobs:
            return f'没有这种工 {iid}'
        if not job_unlocked(st, iid):
            return '还没解锁'
        if job_refused(st, iid):
            return '失控指数 ≥60，雇主拒绝'
        return None
    r = d.rests.get(iid)
    if r is None:
        return f'没有这种休息 {iid}'
    if not r.get('玩家可选', True):
        return '只在重病时强制'
    if st.status['生病'] and not r['生病可选']:
        return '生病状态只能在家休息'
    if iid == 'rest_outing':
        if place not in d.places:
            return '外出要选去处'
    elif place:
        return '只有外出带去处'
    return None


def options(st):
    """本月能选的日程项（给界面和机器人用）。"""
    d = st.d
    out = [c for c in d.classes]
    out += [b for b in st.books if validate(st, b) is None]
    out += [j for j in d.jobs if validate(st, j) is None]
    for r in d.rests:
        if r == 'rest_outing':
            out += [f'{r}@{p}' for p in d.places if validate(st, f'{r}@{p}') is None]
        elif validate(st, r) is None:
            out.append(r)
    return out


def place_cost(st, place):
    """外出一天的花费：去处的 花费，或 花费按名气档（度假村）。"""
    p = st.d.places[place]
    if '花费按名气档' in p:
        return p['花费按名气档'][st.fame_tier()]
    return p['花费']


# ---------- 判定 ----------
def _extra_fail(st, job):
    """恋爱 20%（上课、看书、打工、拍摄都有）；失控偷懒只对打工和拍摄（GDD 5.1）。返回 True 表示当天失败。"""
    g = st.rng.logic
    fail = False
    if st.status['恋爱'] and g.chance(20, 100):
        fail = True
    if job:
        w = st.idx['失控指数']
        if w >= 30:
            fail = g.chance(80, 100) or fail
        elif w >= 10:
            fail = g.chance(40, 100) or fail
    return fail


def practice_ok(st):
    """体力/2 + r0(体力/2) >= r0(疲劳)（GDD 5.1）。"""
    g = st.rng.logic
    b = st.bonus()
    line = g.r0(st.val('疲劳', b))
    hp = st.val('体力', b)
    ok = hp // 2 + g.r0(hp // 2) >= line
    return (not _extra_fail(st, False)) and ok


def job_lines(st, j):
    """成功线，含 `成功线修正`（如旗标“文凭”让报馆、片厂办公室的教育线 -20）。"""
    lines = [[c['项'], c['值']] for c in j['成功线']]
    for m in j.get('成功线修正', []):
        if rules.cond(st, m['条件']):
            for x in lines:
                if x[0] == m['项']:
                    x[1] += m['值']
    return lines


def job_day_ok(st, lines):
    g = st.rng.logic
    b = st.bonus()
    tired = st.val('疲劳', b)
    ok = True
    for k, v in lines:
        if st.val(k, b) - g.r0(tired) < v:
            ok = False
    return (not _extra_fail(st, True)) and ok


def wage_of(st, jid):
    """日薪 = 基数 × 加薪档，向下取整；加薪档按本期之前成功过的期数（GDD 5.4）。"""
    j = st.d.jobs[jid]
    n = st.cnt('成功期数.' + jid)
    for t in st.d.job_rules['加薪档']:
        if n < t['期数小于']:
            return j['日薪'] * (100 + t['加成百分比']) // 100
    return j['日薪']


def accent_on(st):
    return st.flags.get('口音期', 0) > 0


# ---------- 执行 ----------
def run_class(st, cid, days, hooks):
    c = st.d.classes[cid]
    L = class_level(st, cid)
    fee = c['学费'][L - 1]
    g = st.rng.logic
    talk = any(e['项'] == '谈吐' for e in c['收益'])
    went = ok_days = 0
    for day, sun in days:
        if sun:
            continue
        if st.money < fee:
            st.inc('计数.没钱上课日')
            continue
        went += 1
        if practice_ok(st):
            ok_days += 1
            for e in c['收益']:
                if '条件' in e and not rules.cond(st, e['条件']):
                    continue
                add_stat(st, e['项'], g.r(*e['各级'][L - 1]))
            if talk and accent_on(st):
                add_stat(st, '谈吐', 1)
        add_stat(st, '疲劳', 1)
        st.money -= fee
    if went:
        st.inc('旬数.' + cid)
        road = st.d.class_road(cid)
        if road:
            st.inc('期数.' + road)
        if c.get('每旬效果'):
            rules.apply_effect(st, c['每旬效果'], source='schedule')
        ch = c.get('剧情链')
        n = st.cnt('旬数.' + cid)
        if ch and n in ch['触发旬数']:
            hooks.class_chain(st, ch['链'], n)
    return {'上课日': went, '成功日': ok_days, '等级': L}


def run_book(st, bid, days, hooks):
    b = st.d.books[bid]
    sk = b['技能']
    g = st.rng.logic
    ok_days = 0
    for day, sun in days:
        if sun:
            continue
        if practice_ok(st):
            ok_days += 1
            left = st.books.get(bid, 0)
            room = b['技能上限'] - st.skill[sk]
            if left > 0 and room > 0:
                v = min(g.r(*b['收益']), left, room)
                add_stat(st, sk, v)
                st.books[bid] = left - v
            if sk == '谈吐' and accent_on(st):
                add_stat(st, '谈吐', 1)
        add_stat(st, '疲劳', 1)
    st.inc('计数.看书旬数')
    st.inc('期数.' + st.d.skill_road[sk])
    if st.books.get(bid, 1) <= 0:
        del st.books[bid]
        st.read_books.append(bid)
        hooks.book_done(st, bid)
    return {'成功日': ok_days}


def run_job(st, jid, days, hooks):
    j = st.d.jobs[jid]
    g = st.rng.logic
    lines = job_lines(st, j)
    wage = wage_of(st, jid)
    work = ok_days = 0
    for day, sun in days:
        if sun:
            continue
        work += 1
        for e in j['每天效果']:
            add_stat(st, e['项'], g.r(*e['加']))
        if job_day_ok(st, lines):
            ok_days += 1
    pay = wage * ok_days
    if work and ok_days == work:
        pay = pay * (100 + st.d.job_rules['全勤加成百分比']) // 100
    st.add_money(pay)
    good = ok_days > 0   # 原版：这一期有一天成功就算成功一期（JOB*.TXT 的 RUN_ARBEIT[1]）
    if good:
        st.inc('成功期数.' + jid)
        for r in st.d.job_roads(jid):
            st.inc('期数.' + r)
        if j['曝光']:
            st.exposed = 1
        if j['每期效果']:
            rules.apply_effect(st, j['每期效果'], source='schedule')
    hooks.job_period(st, jid, good)
    return {'工作日': work, '成功日': ok_days, '薪水': pay}


def run_rest(st, rid, place, days, hooks):
    d = st.d
    r = d.rests[rid]
    spent = 0
    mid = len(days) // 2
    for k, (day, sun) in enumerate(days):
        if rid == 'rest_outing':
            cost = place_cost(st, place)
            if st.money >= cost:
                st.money -= cost
                spent += cost
                add_stat(st, '疲劳', d.places[place]['疲劳每天'])
            else:
                add_stat(st, '疲劳', d.rests['rest_home']['疲劳每天'])
            if k == mid - 1:
                st.inc('计数.逛街.' + place)
                hooks.outing(st, place)
        elif rid == 'rest_sanatorium':
            if st.money >= r['花费']:
                st.money -= r['花费']
                spent += r['花费']
                add_stat(st, '疲劳', r['疲劳每天'])
        else:
            add_stat(st, '疲劳', r['疲劳每天'])
            if r.get('每天效果'):
                rules.apply_effect(st, r['每天效果'], source='schedule')
    if r.get('每旬效果'):
        rules.apply_effect(st, r['每旬效果'], source='schedule')
    return {'花费': spent}


def run_period(st, i, e, hooks):
    """执行第 i 旬的日程项 e。返回一条小结（给日志和报告）。"""
    days = days_of(st, i)
    kind, iid, place = parse_entry(e)
    st.inc('计数.旬.' + iid)
    if kind == 'class':
        out = run_class(st, iid, days, hooks)
    elif kind == 'book':
        out = run_book(st, iid, days, hooks)
    elif kind == 'job':
        out = run_job(st, iid, days, hooks)
    else:
        out = run_rest(st, iid, place, days, hooks)
    for day, sun in days:      # 生日这类按日的事件：在这一旬结算完之后依次检查
        hooks.day(st, day)
    out['日程'] = e
    return out
