"""Reconciliation: prints the random-number sequences, save round trips, the results of conditions and effects (step 9), the
fixed-schedule months (step 10), the auditions (step 11) and the bot games (step 12), following tools/trace_cases.json.

The Godot side is game/silentstar/tools/trace.gd; the two outputs must be byte-identical; compare them with tools/compare_trace.py.
The `games` cases are recorded here into work/games/ (tools/record_game.py), so run this before the Godot trace.

    python3 tools/trace.py --out work/trace_py.txt
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from sim import audition as A, data as D, rules, schedule  # noqa: E402
from sim.month import Game, trace_line  # noqa: E402
from sim.rng import PCG32, Rng  # noqa: E402
from sim.state import State  # noqa: E402
import record_game  # noqa: E402


def js(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def run(cases, games_dir=None):
    out = []
    w = out.append
    d = D.load()

    c = cases['rng']
    for s in c['seed']:
        g = Rng(s)
        w(f'# rng seed={s}')
        w('logic ' + ' '.join(str(g.logic.next_u32()) for _ in range(c['count'])))
        w('show ' + ' '.join(str(g.show.next_u32()) for _ in range(c['count'])))
        w('dump ' + js(g.dump()))

    c = cases['mixed']
    g = Rng(c['seed'])
    w(f'# mixed seed={c["seed"]}')
    for step in c['steps']:
        op, args = step[0], step[1:]
        w(f'{op} {js(args)} -> {js(getattr(g.logic, op)(*args))}')
    w('dump ' + js(g.dump()))
    g2 = Rng.load(json.loads(js(g.dump())))
    w('cont ' + ' '.join(str(g.logic.next_u32()) for _ in range(4)))
    w('reload ' + ' '.join(str(g2.logic.next_u32()) for _ in range(4)))
    p = PCG32.load(g.show.dump())
    w('show reload ' + str(p.next_u32()) + ' ' + str(g.show.next_u32()))

    for c in cases['origin']:
        st = State.new(d, c['seed'], tuple(c['origin']))
        s1 = st.dumps()
        w(f'# origin seed={c["seed"]} origin={js(c["origin"])}')
        w('save ' + s1)
        s2 = State.loads(d, s1).dumps()
        w('roundtrip ' + ('identical' if s1 == s2 else 'differs ' + s2))

    c = cases['effect']
    st = State.new(d, c['seed'], tuple(c['origin']))
    w(f'# effect seed={c["seed"]} origin={js(c["origin"])}')
    for step in c['steps']:
        if isinstance(step, dict):
            if 'equip' in step:
                st.equip = json.loads(js(step['equip']))
                w('equip ' + js(st.equip) + ' gear ' + js(st.bonus()))
            if step.get('update_indices'):
                st.update_indices()
                w('update_indices ' + js(st.idx) + ' ' + js(st.status))
            continue
        text = step[0]
        source = step[1] if len(step) > 1 else 'event'
        trig = rules.apply_effect(st, text, source=source)
        w(f'effect {text} [{source}] -> {js(trig)} money={st.money} favor={js(st.favor)} items={js(st.items)}'
          f' equip={js(st.equip)} bonus={js(st.bonus())}')
    w('levels ' + js({r: st.level(r) for r in d.roads}) + ' fame_tiers ' + str(st.fame_tier()))
    for name in cases['var']:
        w(f'var {name} = {js(rules.get_var(st, name))}')
    for cd in cases['cond']:
        w(f'cond {js(cd)} = {js(rules.cond(st, cd))}')
    for ck in cases['check']:
        w(f'check {js(ck)} = {js(rules.check(st, ck))}')
    for pr in cases['prob']:
        w(f'prob {js(pr)} = {js(rules.prob(st, pr))}')
    s1 = st.dumps()
    w('save ' + s1)
    s2 = State.loads(d, s1).dumps()
    w('roundtrip ' + ('identical' if s1 == s2 else 'differs ' + s2))

    for c in cases.get('month', []):
        run_month_case(d, c, w)
    if 'audition' in cases:
        run_audition_cases(d, cases['audition'], w)
    for c in cases.get('games', []):
        run_game_case(d, c, games_dir, w)
    return '\n'.join(out) + '\n'


class _TracePlayer(A.Player):
    """Step 11: main color of the player + a second color drawn from the show stream, random play from the logic stream."""

    def __init__(self, colors):
        self.colors = colors

    def deck(self, st, ctx):
        return list(self.colors)

    def play(self, st, ctx):
        return st.rng.logic.below(len(ctx['hand']))


def run_audition_cases(d, c, w):
    """Step 11: c['count'] auditions. The scenario of each one (month, fame, reputation, role style, rivals, deck) is drawn from the show
    stream; the audition itself uses the logic stream. One line per audition with every round, so the first difference shows."""
    st = State.new(d, c['seed'], tuple(c['origin']))
    sh = st.rng.show
    w(f'# audition seed={c["seed"]} origin={js(c["origin"])} count={c["count"]}')
    named = [x['id'] for x in d.t['rivals']['named']]
    tiers = ['small', 'medium', 'big']
    pools = [[15, 60, 10, 15], [25, 25, 25, 25], [70, 10, 10, 10], [10, 10, 10, 70], [0, 0, 100, 0], [40, 0, 0, 60]]
    for i in range(c['count']):
        st.ym = sh.below(48)
        st.attr['fame'] = sh.r(0, 400)
        for r in d.roads:
            st.corr[r] = sh.r(-50, 300)
        probs = list(pools[sh.below(len(pools))])
        size = tiers[sh.below(3)]
        rivals = []
        for k in range(2 if size == 'big' else 1):
            nid = named[sh.below(len(named))]
            if sh.below(2) and A.rival_present(st, nid):
                rivals.append(A.named_rival(st, nid))
            else:
                rivals.append(A.unnamed_rival(st, size))
        main = A.player_main(st)
        sub = (main + 1 + sh.below(3)) % 4
        k = 3 + sh.below(3)
        pl = _TracePlayer([main] * k + [sub] * (5 - k))
        if sh.below(4) == 0:
            probs = A.remembered_probs(probs, main, 10)
        role = {'id': f'role{i}', 'style_probs': probs}
        out = A.audition(st, role, pl, rivals)
        w(f'{i} {st.date} fame={st.attr["fame"]} lv={js(A.player_levels(st))} probs={js(probs)} rivals={js(rivals)} -> {js(out)}')
    w('state ' + js(st.rng.dump()) + ' ' + js(st.count) + ' ' + js(st.favor))
    w('save ' + st.dumps())


def game_name(c):
    return f"{c['bot']}_{c['seed']}{'_x' if c.get('extras') else ''}"


def run_game_case(d, c, games_dir, w):
    """Step 12: records one bot game into games_dir and prints its replay: one line per month (reconciliation line and md5 of the
    save), then the ending, the fired events, the annual events, the auditions of each board and the final save."""
    name = game_name(c)
    rec, lines, _ = record_game.record(c['bot'], c['seed'], c.get('extras', False), d)
    text = record_game.js(rec)
    os.makedirs(games_dir, exist_ok=True)
    with open(os.path.join(games_dir, name + '.json'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    again = record_game.replay(json.loads(text), d)
    w(f'# game {name} answers={len(rec["answers"])}')
    if again != lines:
        w('the replay differs from the recorded game')
    for line in again:
        w(line)


def run_month_case(d, c, w):
    """Step 10: a fixed schedule for 48 months (default hooks). The plans are used in turn, month by month; an entry that cannot be
    scheduled is replaced by rest_home. Optional: effect (applied once at the start), month_effect (applied after every month start), books, lifestyles (in turn),
    restore_at (month index: save, load and carry on with the loaded game)."""
    g = Game(d, seed=c['seed'], origin=tuple(c['origin']))
    w(f'# month {c["name"]} seed={c["seed"]} origin={js(c["origin"])}')
    if c.get('effect'):
        rules.apply_effect(g.st, c['effect'], source='origin')
        g.st.update_indices()
    for bid, pts in c.get('books', {}).items():
        g.st.books[bid] = pts
    n = 0
    while not g.st.finished:
        if n == c.get('restore_at', -1):
            s = g.save()
            g = Game.restore(s, d)
            w('restore ' + str(len(s)))
        date = g.st.date
        if c.get('lifestyles'):
            g.set_lifestyle(c['lifestyles'][n % len(c['lifestyles'])])
        g.start_month()
        if c.get('month_effect') and n < c.get('month_effect_months', 48):
            rules.apply_effect(g.st, c['month_effect'], source='origin')
        plan = [e if not schedule.validate(g.st, e) else 'rest_home' for e in c['plans'][n % len(c['plans'])]]
        g.run_month(plan)
        w('plan ' + js(plan) + ' ' + js(g.last))
        w(trace_line(g.st, date))
        n += 1
    w(f'end finished={g.st.finished} ended={js(g.st.ended)} debt={g.st.debt_months} collapse={g.st.collapse_months}')
    w('save ' + g.st.dumps())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', default=os.path.join(ROOT, 'tools', 'trace_cases.json'))
    ap.add_argument('--out', default=None)
    ap.add_argument('--games', default=os.path.join(ROOT, 'work', 'games'), help='where the game recordings are written')
    a = ap.parse_args()
    with open(a.cases, encoding='utf-8') as fh:
        text = run(json.load(fh), a.games)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(f'wrote {a.out}, {text.count(chr(10))} lines')
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
