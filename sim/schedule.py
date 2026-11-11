"""Schedule: classes, books, jobs, rest (GDD 5.1-5.5). One entry per period, settled day by day.

Schedule entries are strings: class 'class_boxing', book 'book_tantu_1', job 'job_dock', rest 'rest_home',
an outing carries its place 'rest_outing@place_dock'. There are only two rests: at home (Sil keeps company) and outing; the sanatorium is forced by the month flow only when very sick.

Random-number order (Godot must copy it):
- Class, book: each class day first r0(fatigue), then r0(stamina/2); in_love rolls one more 20%; on a successful day the gains are rolled in table order.
- Job: each work day first rolls the daily effects in table order (fatigue included), then r0(fatigue) once per success line in order,
  then in_love 20% and reckless slacking 40%/80% (each only rolled in that state).
"""
from . import rules


class ScheduleError(Exception):
    pass


def parse_entry(e):
    """'rest_outing@place_dock' -> ('rest', 'rest_outing', 'place_dock')"""
    base, _, place = e.partition('@')
    kind = base.split('_', 1)[0]
    if kind not in ('class', 'book', 'job', 'rest'):
        raise ScheduleError(f'unknown schedule entry: {e}')
    return kind, base, place or None


def add_stat(st, name, v):
    """Adds v to an attribute or skill training value, clamped to the range."""
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
    """Days of period i (0 early, 1 mid, 2 late): [(day, is_sunday)]."""
    m = st.month
    a, b = m['periods'][i]
    sun = set(m['sundays'])
    return [(x, x in sun) for x in range(a, b + 1)]


def class_level(st, cid):
    """The class level 1-4 of this period: periods taken so far (including this one) <=3 is level 1, <=6 level 2, <=9 level 3 (GDD 5.2)."""
    n = st.cnt('class_periods.' + cid) + 1
    L = 1
    for step in st.d.class_steps:
        if n > step:
            L += 1
    return L


# ---------- can it be picked ----------
def job_unlocked(st, jid):
    j = st.d.jobs[jid]
    return st.ym >= st.d.month_index[j['earliest']] and rules.cond(st, j['prereq'])


def job_refused(st, jid):
    r = st.d.job_rules['refuse']
    return jid not in r['except'] and rules.cond(st, r['cond'])


def book_on_shelf(st, bid):
    b = st.d.books[bid]
    s = b.get('on_shelf')
    return s is None or st.ym >= st.d.month_index[s]


def validate(st, e):
    """Returns None (can be picked) or the reason it cannot. Not having the money for a class is not a reason: on a day without money you skip it (GDD 5.3, original "insufficient funds")."""
    try:
        kind, iid, place = parse_entry(e)
    except ScheduleError as x:
        return str(x)
    d = st.d
    if kind == 'class':
        return None if iid in d.classes else f'no such class {iid}'
    if kind == 'book':
        if iid not in d.books:
            return f'no such book {iid}'
        if iid not in st.books:
            return 'no such book, or already finished'
        if st.val('education') < d.books[iid]['education_gate']:
            return 'education below the gate'
        return None
    if kind == 'job':
        if iid not in d.jobs:
            return f'no such job {iid}'
        if not job_unlocked(st, iid):
            return 'not unlocked yet'
        if job_refused(st, iid):
            return 'reckless_index >= 60, the employer refuses'
        return None
    r = d.rests.get(iid)
    if r is None:
        return f'no such rest {iid}'
    if not r.get('player_choice', True):
        return 'forced only when very sick'
    if st.status['sick'] and not r['sick_allowed']:
        return 'when sick you can only rest at home'
    if iid == 'rest_outing':
        if place not in d.places:
            return 'an outing needs a place'
    elif place:
        return 'only an outing takes a place'
    return None


def options(st):
    """The schedule entries available this month (for the UI and bots)."""
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
    """Cost of one outing day: the place's cost, or cost_by_fame_tier (resort)."""
    p = st.d.places[place]
    if 'cost_by_fame_tier' in p:
        return p['cost_by_fame_tier'][st.fame_tier()]
    return p['cost']


# ---------- checks ----------
def _extra_fail(st, job):
    """in_love 20% (classes, books, jobs and shooting all have it); reckless slacking only for jobs and shooting (GDD 5.1). Returns True when the day fails."""
    g = st.rng.logic
    fail = False
    if st.status['in_love'] and g.chance(20, 100):
        fail = True
    if job:
        w = st.idx['reckless_index']
        if w >= 30:
            fail = g.chance(80, 100) or fail
        elif w >= 10:
            fail = g.chance(40, 100) or fail
    return fail


def practice_ok(st):
    """stamina/2 + r0(stamina/2) >= r0(fatigue) (GDD 5.1)."""
    g = st.rng.logic
    b = st.bonus()
    line = g.r0(st.val('fatigue', b))
    hp = st.val('stamina', b)
    ok = hp // 2 + g.r0(hp // 2) >= line
    return (not _extra_fail(st, False)) and ok


def job_lines(st, j):
    """The success lines including `success_line_mods` (e.g. flag diploma lowers the education line of the newspaper and studio office jobs by 20)."""
    lines = [[c['stat'], c['value']] for c in j['success_lines']]
    for m in j.get('success_line_mods', []):
        if rules.cond(st, m['cond']):
            for x in lines:
                if x[0] == m['stat']:
                    x[1] += m['value']
    return lines


def job_day_ok(st, lines):
    g = st.rng.logic
    b = st.bonus()
    tired = st.val('fatigue', b)
    ok = True
    for k, v in lines:
        if st.val(k, b) - g.r0(tired) < v:
            ok = False
    return (not _extra_fail(st, True)) and ok


def wage_of(st, jid):
    """Daily wage = base x raise tier, rounded down; the raise tier is by the periods that succeeded before this one (GDD 5.4)."""
    j = st.d.jobs[jid]
    n = st.cnt('job_periods.' + jid)
    for t in st.d.job_rules['raise_tiers']:
        if n < t['periods_below']:
            return j['daily_wage'] * (100 + t['bonus_pct']) // 100
    return j['daily_wage']


def accent_on(st):
    return st.flags.get('accent_period', 0) > 0


# ---------- execution ----------
def run_class(st, cid, days, hooks):
    c = st.d.classes[cid]
    L = class_level(st, cid)
    fee = c['fee'][L - 1]
    g = st.rng.logic
    talk = any(e['stat'] == 'speech' for e in c['gain'])
    went = ok_days = 0
    for day, sun in days:
        if sun:
            continue
        if st.money < fee:
            st.inc('count.broke_class_days')
            continue
        went += 1
        if practice_ok(st):
            ok_days += 1
            for e in c['gain']:
                if 'cond' in e and not rules.cond(st, e['cond']):
                    continue
                add_stat(st, e['stat'], g.r(*e['per_level'][L - 1]))
            if talk and accent_on(st):
                add_stat(st, 'speech', 1)
        add_stat(st, 'fatigue', 1)
        st.money -= fee
    if went:
        st.inc('class_periods.' + cid)
        road = st.d.class_road(cid)
        if road:
            st.inc('road_periods.' + road)
        if c.get('period_effect'):
            rules.apply_effect(st, c['period_effect'], source='schedule')
        ch = c.get('story_chain')
        n = st.cnt('class_periods.' + cid)
        if ch and n in ch['trigger_periods']:
            hooks.class_chain(st, ch['chain'], n)
    return {'class_days': went, 'ok_days': ok_days, 'levels': L}


def run_book(st, bid, days, hooks):
    b = st.d.books[bid]
    sk = b['skills']
    g = st.rng.logic
    ok_days = 0
    for day, sun in days:
        if sun:
            continue
        if practice_ok(st):
            ok_days += 1
            left = st.books.get(bid, 0)
            room = b['skill_cap'] - st.skill[sk]
            if left > 0 and room > 0:
                v = min(g.r(*b['gain']), left, room)
                add_stat(st, sk, v)
                st.books[bid] = left - v
            if sk == 'speech' and accent_on(st):
                add_stat(st, 'speech', 1)
        add_stat(st, 'fatigue', 1)
    st.inc('count.book_periods')
    st.inc('road_periods.' + st.d.skill_road[sk])
    if st.books.get(bid, 1) <= 0:
        del st.books[bid]
        st.read_books.append(bid)
        hooks.book_done(st, bid)
    return {'ok_days': ok_days}


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
        for e in j['daily_effect']:
            add_stat(st, e['stat'], g.r(*e['add']))
        if job_day_ok(st, lines):
            ok_days += 1
    pay = wage * ok_days
    if work and ok_days == work:
        pay = pay * (100 + st.d.job_rules['full_attendance_bonus_pct']) // 100
    st.add_money(pay)
    good = ok_days > 0   # Original: one successful day makes the period successful (RUN_ARBEIT[1] of JOB*.TXT)
    if good:
        st.inc('job_periods.' + jid)
        for r in st.d.job_roads(jid):
            st.inc('road_periods.' + r)
        if j['exposure']:
            st.exposed = 1
        if j['job_period_effect']:
            rules.apply_effect(st, j['job_period_effect'], source='schedule')
    hooks.job_period(st, jid, good)
    return {'work_days': work, 'ok_days': ok_days, 'pay': pay}


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
                add_stat(st, 'fatigue', d.places[place]['fatigue_per_day'])
            else:
                add_stat(st, 'fatigue', d.rests['rest_home']['fatigue_per_day'])
            if k == mid - 1:
                st.inc('count.outing.' + place)
                hooks.outing(st, place)
        elif rid == 'rest_sanatorium':
            if st.money >= r['cost']:
                st.money -= r['cost']
                spent += r['cost']
                add_stat(st, 'fatigue', r['fatigue_per_day'])
        else:
            add_stat(st, 'fatigue', r['fatigue_per_day'])
            if r.get('daily_effect'):
                rules.apply_effect(st, r['daily_effect'], source='schedule')
    if r.get('period_effect'):
        rules.apply_effect(st, r['period_effect'], source='schedule')
    return {'cost': spent}


def run_period(st, i, e, hooks):
    """Runs schedule entry e of period i. Returns a summary (for the log and the report)."""
    days = days_of(st, i)
    kind, iid, place = parse_entry(e)
    st.inc('count.period.' + iid)
    if kind == 'class':
        out = run_class(st, iid, days, hooks)
    elif kind == 'book':
        out = run_book(st, iid, days, hooks)
    elif kind == 'job':
        out = run_job(st, iid, days, hooks)
    else:
        out = run_rest(st, iid, place, days, hooks)
    for day, sun in days:      # Per-day events such as birthdays: checked in order after this period is settled
        hooks.day(st, day)
    out['schedule'] = e
    return out
