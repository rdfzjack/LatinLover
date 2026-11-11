"""Casting board (GDD 3.3, 6.1-6.5, 11.1 swap role and steal role, 11.3 the extra role after Valen's death). Numbers are in roles.json defaults.

One board entry (a role snapshot, in st.story['board']['roles']):
    {'id', 'name', 'size', 'fame_gate', 'style_probs' (the ones actually used), 'base_style', 'road', 'wants', 'tags', 'bonus_skill',
     'talkie', 'speech_line', 'fee', 'lead', 'opponents': [opponent ...], 'house', 'source', 'intel': {...}}
'road' is the road with the highest base style (used for the reputation bonus at release). 'intel' is only for the UI: whether tags/style/habit are shown, and the excluded color.

Random-number order when building a board (Godot copies this):
  1. Draw roles in the order big, medium, small: the base counts, plus the extra medium/big roles from connections; the second small slot of 1926-01 holds the tutorial role.
     Drawing from the pool: index below(sum of weights); if no suitable role is in the pool, a placeholder role is generated: main color below(4), wanted skill below(3), tag below(n).
  2. The extra roles are, in order: pending_board (script), the widow-invested medium film, the transition medium film, the small film after Valen's death.
  3. Talkies: the 1927-10 board picks 1 with below(candidate count); later each candidate gets chance(percent).
  4. Opponents: for each role by its opponents list (unnamed rivals: see audition.unnamed_rival; Valen's replacement below(2);
     the named rival of a placeholder big film is drawn by weight with below(10)).
  5. Long contract: below picks 3 of the roles that can be signed and marks them house.
  6. Waiter intel: below(role count) picks one; tip-off: below picks among the medium and big films.
"""
from . import audition, film, rules

TIERS = ('small', 'medium', 'big')
RANK = {'small': 0, 'medium': 1, 'big': 2}


def cfg(d):
    return d.role_cfg['board']


def board(st):
    return st.story['board']


# ---------- roles ----------
def snapshot(st, r, src='pool'):
    d = st.d
    df = d.role_cfg
    t = r['size']
    probs = r['style_probs']
    return {'id': r['id'], 'name': r['name'], 'size': t,
            'fame_gate': r['fame_gate'] if r.get('fame_gate') is not None else df['fame_gate'][t],
            'style_probs': list(probs) if probs else None, 'base_style': list(probs) if probs else None,
            'road': None, 'wants': [dict(k) for k in r['wants']], 'tags': list(r['tags']),
            'bonus_skill': r.get('bonus_skill') or df['bonus_skill'], 'talkie': r.get('talkie'),
            'speech_line': r.get('speech_line'), 'fee': r.get('fee') or df['fee'][t], 'lead': r.get('lead'),
            'rival_spec': [dict(o) for o in r['opponents']], 'opponents': [], 'house': False, 'source': src, 'intel': {}}


def set_probs(e, probs):
    e['style_probs'] = list(probs)
    e['base_style'] = list(probs)
    e['road'] = None


def main_of(probs):
    return max(range(4), key=lambda c: (probs[c], -c))


def split_probs(main, top):
    """The main color gets top%, the other three colors share the rest equally, and any remainder goes to the earlier colors."""
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
    """Generates a placeholder role when the pool has no suitable role (roles.json defaults.placeholder_gen)."""
    d = st.d
    g = st.rng.logic
    c = d.role_cfg['placeholder_gen']
    main = g.below(4)
    road = d.roads[main]
    sk = d.road_skills[road]
    skill = sk[g.below(len(sk))]
    pool = [t for t in (tags or c['tags_by_color'][road])]
    tag = pool[g.below(len(pool))]
    probs = [c['other_style']] * 4
    probs[main] = c['main_style']
    st.story['seq'] += 1
    opp = [{'unnamed': True}] + ([{'named_placeholder': True}] if tier == 'big' else [])
    r = {'id': f"gen{st.story['seq']}", 'name': f'placeholder role ({tier})', 'size': tier, 'fame_gate': None,
         'style_probs': probs, 'wants': [{'stat': skill, 'target': c['wants_target'][tier]}], 'tags': [tag],
         'bonus_skill': None, 'talkie': None, 'speech_line': None, 'fee': None, 'opponents': opp}
    return snapshot(st, r, 'placeholder')


def in_years(st, r):
    y = int(st.date[:4])
    return r['years_active'][0] <= y <= r['years_active'][1]


def role_weight(st, r):
    w = sum(st.weights.get(t, 0) for t in r['tags'])
    return 1 + min(w, cfg(st.d)['weight_cap'])


def draw(st, tier, taken, tags=None):
    """Draws one role of the given size from the pool; if none, generates a placeholder. Small roles are drawn by board weight (6.1), the rest with equal probability."""
    d = st.d
    lim = cfg(d)['same_role_cap'][tier]
    seen = st.story['boarded']
    cands = [r for r in d.roles.values()
             if r['size'] == tier and not r.get('tutorial') and in_years(st, r) and r['id'] not in taken
             and seen.get(r['id'], 0) < lim and (tags is None or set(r['tags']) & set(tags))]
    if not cands:
        return placeholder(st, tier, tags)
    ws = [role_weight(st, r) if tier == 'small' else 1 for r in cands]
    v = st.rng.logic.below(sum(ws))
    for r, w in zip(cands, ws):
        if v < w:
            return snapshot(st, r)
        v -= w
    raise AssertionError


def tutorial(st):
    d = st.d
    r = next(x for x in d.roles.values() if x.get('tutorial'))
    e = snapshot(st, r, 'tutorial')
    set_probs(e, split_probs(audition.player_main(st), 60))
    e['rival_spec'] = [{'unnamed': True, 'main_level': d.t['rivals']['tutorial']['main_level']}]
    return e


# ---------- rivals ----------
def named_for_placeholder(st, probs):
    """The second match of a placeholder big film: of the 3 named rivals present that year (easter egg excluded) with the highest main-color level for the role, drawn 5:3:2."""
    d = st.d
    c = d.role_cfg['placeholder_gen']['big_named_rivals']
    main = main_of(probs)
    ids = [rid for rid, r in d.rivals_named.items() if not r.get('easter_egg')
           and audition.rival_present(st, rid)]
    lv = {}
    for rid in ids:
        r = d.rivals_named[rid]
        for s in r['stages']:
            if st.date >= s['from']:
                lv[rid] = s['levels'][main]
    top = sorted(ids, key=lambda x: (-lv[x], ids.index(x)))[:c['take_top']]
    w = c['weight'][:len(top)]
    v = st.rng.logic.below(sum(w))
    for rid, x in zip(top, w):
        if v < x:
            return rid
        v -= x
    raise AssertionError


def make_rivals(st, e):
    out = []
    for o in e['rival_spec']:
        if o.get('unnamed'):
            out.append(audition.unnamed_rival(st, e['size'], o.get('main_level'), e['style_probs']))
        elif o.get('named'):
            out.append(audition.named_rival(st, o['named']))
        else:
            out.append(audition.named_rival(st, named_for_placeholder(st, e['style_probs'])))
    e['opponents'] = out


# ---------- building the board ----------
def compose(st):
    """List of this board's role snapshots (no opponents, talkie, house or intel yet)."""
    d = st.d
    c = cfg(d)
    sv = st.story
    n = dict(c['per_board'])
    if st.val('connections') >= c['connections_extra_medium']:
        n['medium'] += 1
    if st.val('connections') >= c['connections_extra_big']:
        n['big'] += 1
    out = []
    taken = set()
    tut = st.ym == 0
    for t in ('big', 'medium', 'small'):
        for k in range(n[t]):
            if tut and t == 'small' and k == n[t] - 1:
                e = tutorial(st)
            else:
                e = draw(st, t, taken)
            taken.add(e['id'])
            out.append(e)
    # extra roles
    for r in sv['pending_board']:
        out.append(r)
    sv['pending_board'] = []
    if st.flags.get('widow_invest') == 1:
        st.flags['widow_invest'] = 2
        e = draw(st, 'medium', taken)
        e['source'] = 'widow_invest' if e['source'] == 'pool' else e['source']
        taken.add(e['id'])
        out.append(e)
    left, fam = sv['transition']
    if left > 0:
        e = draw(st, 'medium', taken, d.tag_families[fam])
        taken.add(e['id'])
        out.append(e)
        sv['transition'][0] -= 1
    v = c['after_valen_extra']
    if st.flags.get('valen_dead') and st.date <= v['until']:
        e = draw(st, v['size'], taken, v['tags'])
        taken.add(e['id'])
        out.append(e)
    for e in out:
        if e['source'] in ('pool', 'widow_invest'):
            sv['boarded'][e['id']] = sv['boarded'].get(e['id'], 0) + 1
    return out


def assign_talkie(st, entries):
    d = st.d
    c = d.role_cfg['talkie']
    g = st.rng.logic
    if st.date < c['start']:
        for e in entries:
            e['talkie'] = False
        return
    rule = None
    for x in c['ratio']:
        if st.date >= x['from']:
            rule = x
    cand = [e for e in entries if e['talkie'] is None]
    for e in entries:
        if e['talkie'] is None:
            e['talkie'] = False
    if 'count' in rule:
        for _ in range(min(rule['count'], len(cand))):
            e = cand.pop(g.below(len(cand)))
            e['talkie'] = True
    else:
        for e in cand:
            e['talkie'] = g.chance(rule['pct'], 100)
    for e in entries:
        if e['talkie'] and e['speech_line'] is None:
            e['speech_line'] = d.role_cfg['speech_line'][e['size']]


def fame_gate(st, e):
    g = e['fame_gate']
    if e['size'] == 'big' and film.low_budget(st):
        g += cfg(st.d)['lowbudget_big_gate_add']
    return g


def eligible(st, e):
    """Whether the role can be signed: fame high enough, morals clause, long contract allows only house roles. Returns None or the reason."""
    if st.attr['fame'] < fame_gate(st, e):
        return 'out_of_reach'
    if e['size'] == 'big' and st.val('crime') >= cfg(st.d)['morals_crime']:
        return 'morals'
    if st.status['long_contract'] and not e['house']:
        return 'not a house role'
    return None


def make(st):
    """Builds a board: roles, style, opponents, talkie, house, intel. The result is stored in st.story['board']."""
    d = st.d
    c = cfg(d)
    g = st.rng.logic
    entries = compose(st)
    for e in entries:
        if e['road'] is None:
            e['road'] = d.roads[main_of(e['base_style'])]
        key = 'remembered.' + e['id']
        if st.flags.get(key):           # Remembered by the director: the player's main color +10 when it appears this time (7.4)
            e['style_probs'] = audition.remembered_probs(e['style_probs'], audition.player_main(st),
                                                    d.t['habits']['audition']['result']['remembered']['main_style_add_pts'])
            st.flags[key] = 0
            e['intel']['remembered'] = True
    assign_talkie(st, entries)
    for e in entries:
        make_rivals(st, e)
    if st.status['long_contract']:
        k = d.contract['long_contract']
        cand = [e for e in entries if st.attr['fame'] >= fame_gate(st, e)]
        for _ in range(min(k['house_roles'], len(cand))):
            e = cand.pop(g.below(len(cand)))
            e['house'] = True
            e['style_probs'] = audition.remembered_probs(e['style_probs'], audition.player_main(st), k['house_style_add'])
    # intel
    ic = c['intel']
    for e in entries:
        e['intel']['tags'] = st.val('taste') >= ic['tag_taste']
        e['intel']['habit'] = [st.val('connections') >= ic['habit_connections'] or
                           (rv['id'] is not None and st.cnt('duels.' + rv['id']) >= ic['habit_duels'])
                           for rv in e['opponents']]
        if st.val('connections') >= ic['exclude_color_connections']:
            p = e['style_probs']
            e['intel']['excluded'] = min(range(4), key=lambda x: (p[x], x))
    if st.flags.get('waiter_tip') and entries:
        e = entries[g.below(len(entries))]
        e['intel']['habit'] = [True] * len(e['opponents'])
    while st.story['tipoff'] > 0:
        st.story['tipoff'] -= 1
        cand = [e for e in entries if e['size'] in ('medium', 'big') and not e['intel'].get('style')]
        if cand:
            e = cand[g.below(len(cand))]
            e['intel']['style'] = True
            e['intel']['tags'] = True
    for e in entries:
        e['intel']['eligible'] = eligible(st, e)
    st.story['board'] = {'month': st.ym, 'roles': entries, 'tried': [], 'won': None}
    return st.story['board']


# ---------- auditions ----------
def can_try(st, idx):
    b = board(st)
    if b is None or b['month'] != st.ym:
        return 'no board this month'
    if b['won'] is not None:
        return 'this board already gave a role'
    if len(b['tried']) >= cfg(st.d)['audition_tries']:
        return 'this board was already tried twice'
    if idx in b['tried']:
        return 'this role was already tried'
    e = b['roles'][idx]
    if b['tried'] and RANK[e['size']] >= RANK[b['roles'][b['tried'][-1]]['size']]:
        return 'the second try must be a lower size than the first'
    return eligible(st, e)


def try_role(st, idx, agent):
    """Signs up for the idx-th role on the board and plays the audition. A film contract is created when a role or a supporting part is won. Returns the audition result."""
    why = can_try(st, idx)
    if why:
        raise ValueError(why)
    b = board(st)
    e = b['roles'][idx]
    b['tried'].append(idx)
    res = audition.audition(st, e, agent, e['opponents'], e['style_probs'])
    support = False
    if res['result'] == 'narrow_loss' and agent.accept_support(st, e):
        support = True
    if res['result'] == 'won' or support:
        b['won'] = idx
        pers = (not support) and film.can_go_personally(st, e) and agent.go_personally(st, e)
        res['film'] = film.new_film(st, e, film.board_locks(st, e['size'], support), support, pers)['id']
    res['support'] = support
    st.inc('count.audition')
    if res['result'] == 'won':
        st.inc('count.audition_won')
        st.inc('count.audition_won.' + e['size'])
    st.inc('count.audition.' + e['size'])
    return res


def run(st, agent):
    """After the board is built, lets the player sign up one by one until giving up, winning a role, or having tried twice."""
    out = []
    while True:
        b = board(st)
        ok = [i for i in range(len(b['roles'])) if can_try(st, i) is None]
        if not ok:
            break
        i = agent.pick_role(st, b, ok)
        if i is None:
            break
        out.append(try_role(st, i, agent))
    return out


# ---------- auditions outside the board (11.1) ----------
def one_match(st, agent, role, rival):
    """A single match (swap role, steal role). Returns True when the player wins."""
    ctx = {'roles': role, 'rounds': 0, 'opponents': rival, 'levels': audition.player_levels(st)}
    colors = agent.deck(st, ctx)
    m = audition.match(st, audition.build_deck(ctx['levels'], colors), rival, role['style_probs'], agent)
    if rival['id']:
        st.inc('duels.' + rival['id'])
    return m['score_line'][0] >= audition.cfg(st.d)['rounds_to_win']


def swap_role(st, i, agent):
    """Swap role: play a medium audition; a win takes the next period for shooting. Does not fire when the next period is taken (the caller checks first)."""
    d = st.d
    c = d.role_cfg['shoot']['swap_role']
    e = draw(st, c['size'], set())
    if e['source'] == 'pool':
        st.story['boarded'][e['id']] = st.story['boarded'].get(e['id'], 0) + 1
    e['road'] = d.roads[main_of(e['base_style'])]
    e['talkie'] = bool(e['talkie']) and st.date >= d.role_cfg['talkie']['start']
    if e['talkie'] and e['speech_line'] is None:
        e['speech_line'] = d.role_cfg['speech_line'][e['size']]
    rv = audition.unnamed_rival(st, e['size'], None, e['style_probs'])
    win = one_match(st, agent, e, rv)
    if win:
        nxt = film.next_period(st, i)
        pers = film.can_go_personally(st, e) and agent.go_personally(st, e)
        film.new_film(st, e, [nxt][:c['period_count']], False, pers)
    return win


def steal_role(st, agent):
    """Steal role: an unnamed rival comes for a role not yet shot; on a loss the film contract is void."""
    f = next(x for x in film.films(st) if x['status'] == 'to_shoot')
    role = f['roles']
    rv = audition.unnamed_rival(st, role['size'], None, role['style_probs'])
    win = one_match(st, agent, role, rv)
    if not win:
        f['status'] = 'stolen'
        film.update_status(st)
    return win


# ---------- scripts (6.5) ----------
def script_ok(st, kind):
    d = st.d
    c = d.role_cfg['script']
    sv = st.story['script']
    y = int(st.date[:4])
    if not rules.cond(st, c[kind]['cond']):
        return False
    if kind == 'co_written':
        return not sv['co_written'] and sv['self_written'] != y and sv['duv_written'] != y
    return sv[kind] != y


def write_script(st, kind, color=None):
    """Start-of-month action: self_written / duv_written / co_written. The next board gets one more role. color: the color the player picks for self_written and co_written (0-3)."""
    d = st.d
    c = d.role_cfg['script']
    if not script_ok(st, kind):
        raise ValueError(f'cannot {kind} now')
    sv = st.story['script']
    y = int(st.date[:4])
    tier = c[kind]['size']
    st.story['seq'] += 1
    if kind == 'duv_written':
        main = audition.player_main(st)
        b = st.bonus()
        names = ['stamina', 'education', 'loyalty', 'looks', 'discipline', 'crime']
        top = sorted(names, key=lambda n: (-st.val(n, b), names.index(n)))[:2]
        want = [{'stat': n, 'target': max(1, st.val(n, b) * c['duv_written']['wants_pct'] // 100)} for n in top]
        rules.apply_effect(st, c['duv_written']['favor'], source='event')
        sv['duv_written'] = y
    else:
        if color is None or not 0 <= color < 4:
            raise ValueError('a color must be given')
        main = color
        want = [{'stat': d.road_skills[d.roads[main]][0], 'target': d.role_cfg['placeholder_gen']['wants_target'][tier]}]
        if kind == 'co_written':
            sv['co_written'] = 1
            sv['self_written'] = sv['duv_written'] = y
        else:
            sv['self_written'] = y
    opp = [{'unnamed': True}] + ([{'named_placeholder': True}] if tier == 'big' else [])
    r = {'id': f"script{st.story['seq']}", 'name': f'script role ({kind})', 'size': tier, 'fame_gate': None,
         'style_probs': split_probs(main, c['main_style']), 'wants': want, 'tags': [], 'bonus_skill': None,
         'talkie': None, 'speech_line': None, 'fee': None, 'opponents': opp}
    st.story['pending_board'].append(snapshot(st, r, 'script'))
