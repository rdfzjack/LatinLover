"""Events (GDD 5.4 hooks, 5.5.2 outings, 6.5 Duv, 11, 12).

Event data is in events.json and outing.json; an event can have:
    effect (applied directly) -> check (event level, success/fail effect) -> branches (the first whose cond holds) -> options (ask the player) -> code (events with `code: true` are written in CODE following `note`)
`trigger.<id>` in an effect fires last, in order.

freq: once_per_game / once_per_year / once_per_quarter / null; `once: true` of an outing event equals once_per_game.

Random-number order (Godot copies this):
- Month end: by `order`, one by one; the probability is rolled only when the cond holds and freq allows; opportunities come after senior approval (order 9), in table order. Stop after 2 fired.
- Period start: swap role, steal role, same.
- Outing: nothing is rolled when someone is present and has a chain event; resident events and the random table use below(sum of weights) by weight.
- Jobs: each period_random is rolled once in table order, then milestones are checked (no roll).
- Tutoring period: with Duv favor >= 30 roll 1/10 for the tip-off.
- Annual: first r0(50) for my score, then r0(50) for each rival in sorted order.
"""
from . import board, film, rules
from .schedule import add_stat

SCANDAL_PAY = 200          # Newspaper line: pay 200 to suppress a scandal (5.4)
ARREST_FINE = 500          # Cap on the arrest fine (11.2)
HELP_YIQI = 150            # loyalty >= 150: someone helps (10.1)
HELP_COST = 30
SCANDAL_YIQI = 200
SLOTS = ('early', 'mid', 'late')


# ---------- freq ----------
def can_fire(st, e):
    n = st.fired.get(e['id'], 0)
    if e.get('once') and n:
        return False
    f = e.get('freq')
    if not f or not n:
        return True
    last = st.story['last_fired'].get(e['id'], -99)
    if f == 'once_per_game':
        return False
    if f == 'once_per_year':
        return last // 12 != st.ym // 12
    if f == 'once_per_quarter':
        return last // 3 != st.ym // 3
    raise ValueError(f)


def ready(st, e):
    return can_fire(st, e) and rules.cond(st, e.get('cond'))


# ---------- trigger ----------
def fire(story, st, eid, depth=0):
    """Fires one event and settles it. Returns {'id', 'options', 'check'}."""
    if depth > 8:
        raise RuntimeError(f'event trigger chain too deep: {eid}')
    d = st.d
    e = d.events[eid]
    st.fired[eid] = st.fired.get(eid, 0) + 1
    st.story['last_fired'][eid] = st.ym
    rec = {'id': eid, 'month': st.date}
    trig = []
    if e.get('effect'):
        trig += rules.apply_effect(st, e['effect'], source='event')
    if e.get('check'):
        ok = rules.check(st, e['check'])
        rec['check'] = ok
        trig += rules.apply_effect(st, e['success_effect' if ok else 'fail_effect'], source='event')
    for br in e.get('branches') or []:
        if rules.cond(st, br['cond']):
            trig += rules.apply_effect(st, br['effect'], source='event')
            break
    choice = None
    opts = e.get('options') or []
    if opts:
        avail = [k for k, o in enumerate(opts) if rules.cond(st, o.get('cond'))]
        if avail:
            choice = story.agent.option(st, e, avail)
            if choice not in avail:
                raise ValueError(f'{eid} picked an option that cannot be picked {choice}')
            o = opts[choice]
            ok = rules.check(st, o.get('check') or None)
            rec['check'] = ok
            trig += rules.apply_effect(st, o['success_effect' if ok else 'fail_effect'], source='event')
        rec['options'] = choice
    h = CODE.get(eid)
    if h:
        trig += h(story, st, e, choice) or []
    story.log.append(rec)
    for t in trig:
        fire(story, st, t, depth + 1)
    return rec


# ---------- code events ----------
def fame_pct(st, pct):
    st.attr['fame'] = max(0, st.attr['fame'] + st.attr['fame'] * pct // 100)


def h_missing(story, st, e, ch):
    """Missing: next month's schedule is void, and the four rep_bonus values each lose 10% of the current reputation."""
    st.void_next = 1
    b = st.bonus()
    for r in st.d.roads:
        st.corr[r] -= st.rep(r, b) * 10 // 100
    film.breach_month(st, st.ym + 1)


def h_arrest(story, st, e, ch):
    """Arrest: fine min(money, 500), crime +20, exposure. With loyalty >= 150 someone bails him out (fine halved, no exposure, loyalty -30);
        the bar owner's milestone also halves the fine (the two do not stack). A sick player is not arrested (GDD 10)."""
    if st.status['sick']:
        return
    fine = max(0, min(st.money, ARREST_FINE))
    bail = st.val('loyalty') >= HELP_YIQI
    if bail or st.flags.get('bail_half'):
        fine //= 2
    st.money -= fine
    add_stat(st, 'crime', 20)
    if bail:
        add_stat(st, 'loyalty', -HELP_COST)
    else:
        st.exposed = 1
    st.inc('count.arrest')


def h_scandal(story, st, e, ch):
    """Scandal exposure: the newspaper line can suppress it (free once a year / pay 200); villain + crime >= 3: fame +10%, otherwise -15%
        (doubled after an official warning, halved with loyalty >= 200)."""
    y = st.ym // 12
    sv = st.story
    if st.flags.get('free_scandal_cover') and sv['scandal_cover_year'] != y + 1 and story.agent.suppress(st, 'free'):
        sv['scandal_cover_year'] = y + 1
        st.inc('count.scandal_covered')
        return
    if st.flags.get('scandal_foresight') and st.money >= SCANDAL_PAY and story.agent.suppress(st, 'paid'):
        st.money -= SCANDAL_PAY
        st.inc('count.scandal_covered')
        return
    st.exposed = 1
    st.inc('count.scandal')
    if st.tags.get('villain', 0) + st.tags.get('crime', 0) >= 3:
        fame_pct(st, 10)
        return
    pct = 15
    if st.flags.get('warning'):
        pct *= 2
        st.flags['warning'] = 0
    if st.val('loyalty') >= SCANDAL_YIQI:
        pct //= 2
    fame_pct(st, -pct)


def h_contract(story, st, e, ch):
    if ch == 1:
        st.story['contract_refused'] = st.ym


def h_creditor(story, st, e, ch):
    """Creditor: the dock countryman blocks once -> loyalty >= 150 a friend covers it -> fight >= 50 drives him off -> the most expensive item is taken -> fame -10% and exposure."""
    if st.flags.get('fellow_debt_shield') == 1:
        st.flags['fellow_debt_shield'] = 2
        st.money = max(st.money, 0)
        st.debt_months = 0
        return
    if st.val('loyalty') >= HELP_YIQI:
        add_stat(st, 'loyalty', -HELP_COST)
        st.money = max(st.money, 0)
        st.debt_months = 0
        return
    st.debt_months = 0
    if st.val('fight') >= 50:
        add_stat(st, 'crime', 10)
        return
    its = [i for i in st.items if st.d.items[i]['price'] > 0]
    if its:
        top = max(its, key=lambda i: (st.d.items[i]['price'], -its.index(i)))
        rules.remove_item(st, top)
        st.money = min(0, st.money + st.d.items[top]['price'])
        return
    fame_pct(st, -10)
    st.exposed = 1


def h_drug_deeper(story, st, e, ch):
    if st.drug >= 3:
        add_stat(st, 'stamina', -30)
        add_stat(st, 'crime', 20)


def h_detox(story, st, e, ch):
    """Withdrawal: takes the whole next month. With Sil favor >= 60 (he is present) Sil +10."""
    if st.favor.get('sil', 0) >= 60:
        rules.apply_effect(st, 'favor.sil+10', source='event')
    st.void_next = 1
    film.breach_month(st, st.ym + 1)


def h_tip(story, st, e, ch):
    """Duv's tip-off: a random medium or big role on the next board shows its full style and tags."""
    if st.flags.get('tipoff'):
        st.flags['tipoff'] = 0
        st.story['tipoff'] += 1


def h_transform(story, st, e, ch):
    """Studio boss "backs transition": the next 3 boards each get an extra medium role of the tag family the player picks."""
    fam = story.agent.family(st)
    if fam not in st.d.tag_families:
        raise ValueError(fam)
    st.story['transition'] = [board.cfg(st.d)['transition_boards'], fam]


def h_birthday(story, st, e, ch):
    rules.apply_effect(st, 'favor.actress+3', source='event')


CODE = {
    'evt_missing': h_missing, 'evt_arrest': h_arrest, 'evt_scandal': h_scandal, 'evt_contract': h_contract,
    'evt_creditor': h_creditor, 'evt_drug_deeper': h_drug_deeper, 'evt_detox': h_detox,
    'outing_duv_tip': h_tip, 'job_studio_m2': h_transform, 'evt_birthday': h_birthday,
}
# The other `code: true` events only need the effects and flags in the data, read by other modules through the flags:
#   evt_swap_role / evt_steal_role (period_start), evt_accent (flag), era_valen_death (board reads the flag),
#   era_talkie (the date is already in the table), job_studio_m1 (the long-contract probability is already tiered by favor in evt_contract).


# ---------- month end (11.2, 12.2) ----------
def month_end_list(d):
    evs = sorted((e for e in d.events.values() if e.get('class') == 'month_end' and e.get('timing') == 'month_end'),
                 key=lambda e: e['order'])
    out = []
    for e in evs:
        out.append(('event', e))
    k = max(i for i, (_, e) in enumerate(out) if e['order'] <= 9)
    return out[:k + 1] + [('opportunity', o) for o in d.opps] + out[k + 1:]


def month_end(story, st):
    d = st.d
    if st.status['long_contract']:
        st.add_money(d.contract['long_contract']['monthly_pay'])
    lim = d.t['events']['month_end_cap']
    n = 0
    for kind, e in month_end_list(d):
        if n >= lim:
            break
        if kind == 'opportunity':
            if st.fired.get(e['story']) or not rules.cond(st, e['cond']):
                continue
            if not rules.prob(st, e['monthly_prob']):
                continue
            fire(story, st, e['story'])
            rules.apply_effect(st, e['effect'], source='event')   # The opportunities' effects are written in opportunities.json; the story event only handles the story
            st.inc('count.opportunity')
            if e['takes_month']:
                st.void_next = 1
                film.breach_month(st, st.ym + 1)
            n += 1
            continue
        if not ready(st, e):
            continue
        if e['id'] == 'evt_contract' and st.ym - st.story['contract_refused'] < d.contract['long_contract']['refuse_months']:
            continue
        if not rules.prob(st, e['prob']):
            continue
        fire(story, st, e['id'])
        n += 1


# ---------- period start (11.1) ----------
def period_start(story, st, i, entry):
    if entry.startswith('rest_'):
        return
    d = st.d
    e = d.events['evt_swap_role']
    nxt = film.next_period(st, i)
    if (ready(st, e) and not film.is_locked(st, *nxt) and nxt[0] < len(d.months)
            and rules.prob(st, e['prob'])):
        fire(story, st, e['id'])
        board.swap_role(st, i, story.agent)
    e = d.events['evt_steal_role']
    if ready(st, e) and rules.prob(st, e['prob']):
        fire(story, st, e['id'])
        board.steal_role(st, story.agent)


def period_end(story, st, i, entry, out):
    d = st.d
    if entry == 'class_tutor' and out.get('class_days'):
        e = d.events['outing_duv_script']
        if ready(st, e):
            fire(story, st, e['id'])
        if st.favor.get('duv', 0) >= 30 and st.rng.logic.chance(1, 10):
            fire(story, st, 'outing_duv_tip')
    duv = d.npcs['duv'].get('education_milestones')
    if duv and 'duv' in st.known:
        for line in duv['line']:
            k = f'duv_education_{line}'
            if not st.flags.get(k) and st.val('education') >= line:
                st.flags[k] = 1
                rules.apply_effect(st, duv['effect'], source='event')


# ---------- outings (5.5.2) ----------
def meet(st, npc):
    if npc not in st.known:
        st.known.append(npc)
        st.known.sort(key=st.d.npc_order.get)      # table order
    st.inc('count.met.' + npc)


def present(st, place, i):
    m = int(st.date[5:])
    y = int(st.date[:4])
    out = []
    for s in st.d.schedule_npc:
        if (s['place'] == place and s['years'][0] <= y <= s['years'][1] and m in s['months']
                and SLOTS[i] in s['periods'] and rules.cond(st, s['cond']) and s['npc'] not in out):
            out.append(s['npc'])
    return out


def weighted(st, pairs):
    """pairs: [(weight, value)], draws one by weight; an empty table returns None."""
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
    """The next chain event of a present NPC (not seen yet, cond holds); None if there is none."""
    d = st.d
    for ch in d.chains:
        if ch['npc'] == npc and ch['trigger'] == 'outing':
            for eid in ch['chain']:
                if ready(st, d.events[eid]):
                    return eid
    return None


def npc_resident(st, npc):
    d = st.d
    pairs = []
    for ch in d.chains:
        if ch['npc'] == npc and ch['trigger'] == 'outing':
            pairs += [(c['weight'], c['event']) for c in ch['resident'] if ready(st, d.events[c['event']])]
    return pairs


def outing(story, st, place):
    """Fires exactly one event in the middle of an outing period. If someone is present and has a chain or resident event, theirs fires, otherwise one is drawn from the place's random table."""
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
        pairs = [(x['weight'], x['event']) for x in d.places[place]['random_table'] if ready(st, d.events[x['event']])]
        eid = weighted(st, pairs)
    if eid:
        fire(story, st, eid)
    return eid


def class_chain(story, st, chain, n):
    """Tutoring periods 1, 4, 7, 10: Duv's tutoring chain, the next unseen event in order."""
    d = st.d
    ch = next(c for c in d.chains if c['id'] == chain)
    meet(st, ch['npc'])
    for eid in ch['chain']:
        if ready(st, d.events[eid]):
            fire(story, st, eid)
            return eid
    return None


def book_done(story, st, bid):
    eid = st.d.books[bid].get('finish_event')
    if eid and ready(st, st.d.events[eid]):
        fire(story, st, eid)


# ---------- job hooks (5.4) ----------
def job_period(story, st, jid, good):
    d = st.d
    j = d.jobs[jid]
    if good and j['npc']:
        meet(st, j['npc'])
    for r in j['period_random']:
        if st.rng.logic.chance(*r['prob']):
            fire(story, st, r['event'])
    for m in j['milestones']:
        e = d.events[m['event']]
        if not st.fired.get(e['id']) and rules.cond(st, m['cond']):
            fire(story, st, e['id'])


# ---------- birthday ----------
def day(story, st, dd):
    e = st.d.events['evt_birthday']
    bd = e.get('date')
    if bd and st.date[5:] == bd[:2] and dd == int(bd[3:]):
        fire(story, st, e['id'])


# ---------- era, annual (11.3, 12.1) ----------
def era(story, st, ids):
    for eid in ids:
        fire(story, st, eid)


def annual_rivals(st, road):
    """Of the named rivals present that year (easter egg excluded), the 5 with the highest level on the road: [(id, level)]."""
    d = st.d
    k = d.roads.index(road)
    out = []
    for rid, r in d.rivals_named.items():
        if r.get('easter_egg') or not (r['present'][0] <= st.date <= r['present'][1]):
            continue
        lv = None
        for s in r['stages']:
            if st.date >= s['from']:
                lv = s['levels'][k]
        out.append((rid, lv))
    out.sort(key=lambda x: -x[1])
    return out[:5]


def annual(story, st):
    """December: pick one of the four occasions to attend, or rest (fatigue reset). Ranking: my score = road reputation + r0(50);
        rival score = 5L(L+1) + r0(50); a rival score >= my score ranks ahead of me."""
    d = st.d
    a = d.t['annual']
    opts = [x for x in a['occasions'] if rules.cond(st, x['cond'])]
    pick = story.agent.annual(st, opts)
    rec = {'month': st.date, 'occasions': pick}
    if pick is None:
        st.attr['fatigue'] = 0
        story.annuals.append(rec)
        return rec
    occ = next(x for x in opts if x['id'] == pick)
    g = st.rng.logic
    me = st.rep(occ['road']) + g.r0(50)
    rank = 1
    for rid, L in annual_rivals(st, occ['road']):
        if 5 * L * (L + 1) + g.r0(50) >= me:
            rank += 1
    rec['rank'] = rank
    for rw in a['ranking']['rewards']:
        if rw['rank'] == rank:
            st.corr[occ['road']] += rw['rep_bonus']
            st.add_money(rw['prize'])
    st.inc(f'count.annual_rank.{rank}')
    story.annuals.append(rec)
    return rec
