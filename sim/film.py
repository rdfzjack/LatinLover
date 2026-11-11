"""Film contracts, shooting, breaches, releases (GDD 5.6, 8, 10 breach when very sick). Numbers are in roles.json defaults.shoot / defaults.release.

One film contract (an entry of st.story['films']):
    {'id', 'role': role snapshot, 'size', 'support', 'stunt_self', 'locks': [[month index, period], ...], 'shoot_days', 'ok_days',
     'perf', 'fee', 'status', 'release', 'result'}
status: to_shoot -> shooting -> to_release -> released; plus breached (very sick, missing etc.) and stolen (lost a steal role).

Random-number order (Godot copies this): on each shooting day first r0(fatigue), then roll in_love and reckless slacking per schedule._extra_fail,
with stunt_self the injury 1/40 is rolled last. Releases roll no random numbers.
"""
from . import rules
from .schedule import add_stat, _extra_fail

TIERS = ('small', 'medium', 'big')


def shoot_cfg(d):
    return d.role_cfg['shoot']


def rel_cfg(d):
    return d.role_cfg['release']


def films(st):
    return st.story['films']


# ---------- tags ----------
def typecast_tags(st):
    """Typed content tags (count >= typed_line)."""
    line = rel_cfg(st.d)['typed_line']
    return [t for t in st.d.content_tags if st.tags.get(t, 0) >= line]


def low_budget(st):
    """Low-budget typed: lowbudget count >= 4 (it is released when the count drops to 3 or below, so no extra state is kept)."""
    return int(st.cnt('count.lowbudget') >= rel_cfg(st.d)['lowbudget']['typed_line'])


def undefined(st):
    """Undefined: at least 6 content tags have a count and none has >= 3 (8.4)."""
    c = rel_cfg(st.d)
    have = [t for t in st.d.content_tags if st.tags.get(t, 0) > 0]
    return int(len(have) >= c['undefined_kinds'] and not typecast_tags(st))


# ---------- film contracts ----------
def new_film(st, role, locks, support=False, personally=False):
    st.story['seq'] += 1
    f = {'id': f"film{st.story['seq']}", 'roles': role, 'size': role['size'], 'support': bool(support),
         'stunt_self': bool(personally), 'locks': [list(x) for x in locks], 'shoot_days': 0, 'ok_days': 0,
         'perf': None, 'fee': None, 'status': 'to_shoot', 'release': None, 'result': None}
    films(st).append(f)
    update_status(st)
    return f


def board_locks(st, tier, support=False):
    """The role won from the board: locks the first few periods of next month (small 1, medium 2, big 3; support -1, at least 1)."""
    n = st.d.role_cfg['shoot_periods'][tier]
    if support:
        x = st.d.t['habits']['audition']['result']['narrow_loss']
        n = max(x['shoot_periods_min'], n - x['shoot_periods_cut'])
    return [[st.ym + 1, k] for k in range(n)]


def next_period(st, i):
    return [st.ym, i + 1] if i < 2 else [st.ym + 1, 0]


def is_locked(st, ym, i):
    return any([ym, i] in f['locks'] for f in films(st) if f['status'] in ('to_shoot', 'shooting'))


def locked(st, i):
    for f in films(st):
        if f['status'] in ('to_shoot', 'shooting') and [st.ym, i] in f['locks']:
            return f
    return None


def update_status(st):
    st.status['has_pending_role'] = int(any(f['status'] == 'to_shoot' for f in films(st)))


def can_go_personally(st, role):
    """stunt_self: the role has any of the western, action_adventure, war tags and nerve >= 60 (50 after 4 periods of stunt double)."""
    c = shoot_cfg(st.d)['stunt_self']
    if not set(role['tags']) & set(c['tags']):
        return False
    line = c['nerve_line']
    if st.flags.get(c['nerve_line_flag']['flags']):
        line = c['nerve_line_flag']['line']
    return st.val('nerve') >= line


# ---------- shooting ----------
def shoot(st, i, f, days):
    """One shooting period. After the last period it pays the fee, computes the performance and fixes the release month."""
    d = st.d
    c = shoot_cfg(d)
    g = st.rng.logic
    t = f['size']
    f['status'] = 'shooting'
    update_status(st)
    for day, sun in days:
        if sun:
            continue
        f['shoot_days'] += 1
        st.exposed = 1
        add_stat(st, 'fatigue', c['fatigue'][t])
        b = st.bonus()
        ok = st.val('stamina', b) - g.r0(st.val('fatigue', b)) >= c['success_lines'][t]
        if _extra_fail(st, True):
            ok = False
        if ok:
            f['ok_days'] += 1
        if f['stunt_self'] and g.chance(*c['stunt_self']['injury_prob']):
            rules.apply_effect(st, c['stunt_self']['injury_effect'], source='schedule')
            st.inc('count.injury')
    if [st.ym, i] == f['locks'][-1]:
        finish(st, f)


def performance(st, f):
    """P x1000: 500 + ok_days x 500 / shoot_days + bonus skill x 2 (stunt_self +100), clamped to 500-1200."""
    c = shoot_cfg(st.d)
    days = f['shoot_days']
    p = c['perf_min'] + (f['ok_days'] * 500 // days if days else 500)
    p += st.val(f['roles']['bonus_skill']) * 1000 // 500
    if f['stunt_self']:
        p += c['stunt_self']['perf_add']
    return max(c['perf_min'], min(c['perf_max'], p))


def fee(st, f):
    """Fee = base x (stunt_self 130%) x (support 40%) x (400+negotiation)/400 x contract coefficient, rounded down at each step."""
    d = st.d
    c = shoot_cfg(d)
    v = f['roles']['fee']
    if f['stunt_self']:
        v = v * c['stunt_self']['fee_pct'] // 100
    if f['support']:
        v = v * d.t['habits']['audition']['result']['narrow_loss']['fee_pct'] // 100
    v = v * (c['negotiation_div'] + st.val('negotiation')) // c['negotiation_div']
    k = d.contract
    if st.val('education') < k['education_below'] and not rules.cond(st, k['exempt_cond']):
        v = v * k['fee_coef_pct'] // 100
    return v


def finish(st, f):
    f['perf'] = performance(st, f)
    f['fee'] = fee(st, f)
    st.add_money(f['fee'])
    f['status'] = 'to_release'
    f['release'] = st.ym + rel_cfg(st.d)['delay_months']
    if f['stunt_self']:
        st.inc('count.stunt_self')
    update_status(st)


# ---------- breaches ----------
def breach_month(st, ym):
    """All film contracts locked in month ym breach: fee 0, fame -10%, no release (GDD 10 very sick; missing, withdrawal and month-taking opportunities are handled the same way)."""
    out = []
    pct = -st.d.rest_forced[0]['shoot_breach']['fame_pct']
    for f in films(st):
        if f['status'] in ('to_shoot', 'shooting') and any(x[0] == ym for x in f['locks']):
            f['status'] = 'breached'
            st.attr['fame'] = max(0, st.attr['fame'] - st.attr['fame'] * pct // 100)
            st.inc('count.breach')
            out.append(f)
    update_status(st)
    return out


# ---------- release ----------
def fit(st, role):
    """Fit F x1000 = 600 + 400 x average(min(value/target, 1.5))."""
    c = rel_cfg(st.d)['fit']
    b = st.bonus()
    rs = [min(st.val(k['stat'], b) * 1000 // k['target'], c['item_cap_pct'] * 10) for k in role['wants']]
    avg = sum(rs) // len(rs) if rs else 1000
    return c['floor'] + c['coef'] * avg // 1000


def familiarity(st, role, tier):
    """Tag familiarity T x1000 = 1000 + 30 x min(sum of the role's tag counts, 5); small films get the maximum when a tag is typed or lowbudget is typed.
        Returns (T, whether the untyped x0.9 applies)."""
    c = rel_cfg(st.d)
    full = 1000 + c['tag_familiarity']['per_tag'] * c['tag_familiarity']['cap_count']
    tc = typecast_tags(st)
    mine = [t for t in role['tags'] if t in tc]
    if mine or (low_budget(st) and tier == 'small'):
        return full, False
    n = sum(st.tags.get(t, 0) for t in role['tags'])
    T = 1000 + c['tag_familiarity']['per_tag'] * min(n, c['tag_familiarity']['cap_count'])
    return T, bool(tc)


def talk_line(st, role):
    line = role['speech_line']
    if st.flags.get('talkie_speech_line_minus_10'):
        line -= rel_cfg(st.d)['radio_speech_line_cut']
    return line


def release_one(st, f):
    d = st.d
    c = rel_cfg(d)
    role, t = f['roles'], f['size']
    B = c['box_base'][t]
    P = f['perf']
    F = fit(st, role)
    T, off = familiarity(st, role, t)
    S = B * P * F * T // 1000000            # S ×1000
    if off:
        S = S * c['untyped_pct'] // 100
    accent = False
    if role.get('talkie'):
        st.inc('count.talkie_count')
        if st.val('speech') < talk_line(st, role):
            S = S * c['talkie_penalty_pct'] // 100
            accent = True
            st.flags['accent_pending'] = 1
    hit = S >= B * c['hit_pct'] * 10
    flop = S < B * c['flop_pct'] * 10
    k = d.t['habits']['audition']['result']['narrow_loss']['release_pct'] if f['support'] else 100
    fame = S * c['fame_pct'] // 100000
    if flop:
        fame //= 2
    fame = fame * k // 100
    money = S * c['dividend_mult'] // 1000 * k // 100
    add_stat(st, 'fame', fame)
    st.add_money(money)
    corr = 0
    if not flop:
        corr = c['rep_bonus'][t] * (2 if hit else 1) * k // 100
        st.corr[role['road']] += corr
    for tag in role['tags']:
        st.tags[tag] = st.tags.get(tag, 0) + 1
    if not f['support']:
        n = st.cnt('count.lowbudget') + c['lowbudget']['delta'][t]
        st.count['count.lowbudget'] = max(0, n)
        st.inc('count.lead.' + t)
        if role.get('lead'):
            rules.apply_effect(st, f"favor.{role['lead']}+{c['lead_favor']}", source='event')
    else:
        st.inc('count.support')
    st.inc('count.release')
    if hit:
        st.inc('count.hit')
        if set(role['tags']) & {'romance', 'exotic_lover'}:
            st.inc('count.romance_hits')
    if flop:
        st.inc('count.flop')
    st.exposed = 1
    f['status'] = 'released'
    f['result'] = {'S': S, 'B': B, 'P': P, 'F': F, 'T': T, 'untyped': off, 'accent': accent, 'hit': hit,
                 'flop': flop, 'fame': fame, 'dividend': money, 'rep_bonus': corr, 'month': st.ym}
    return f['result']


def release(st):
    """Month-end step 2: the films to release this month. Also updates the "big-film hits in the last 12 months" count (for the 1929-05 awards)."""
    out = [release_one(st, f) for f in films(st) if f['status'] == 'to_release' and f['release'] == st.ym]
    st.count['count.big_hits_12m'] = sum(
        1 for f in films(st) if f['status'] == 'released' and f['size'] == 'big' and f['result']['hit']
        and f['result']['month'] > st.ym - 12)
    return out
