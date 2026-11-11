"""Step 9 reconciliation: prints the random-number sequences, save round trips, and the results of conditions and effects, following tools/trace_cases.json.

The Godot side is game/silentstar/tools/trace.gd; the two outputs must be byte-identical; compare them with tools/compare_trace.py.

    python3 tools/trace.py --out work/trace_py.txt
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sim import data as D, rules, schedule  # noqa: E402
from sim.month import Game, trace_line  # noqa: E402
from sim.rng import PCG32, Rng  # noqa: E402
from sim.state import State  # noqa: E402


def js(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def run(cases):
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
    return '\n'.join(out) + '\n'


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
    a = ap.parse_args()
    with open(a.cases, encoding='utf-8') as fh:
        text = run(json.load(fh))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(f'wrote {a.out}, {text.count(chr(10))} lines')
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
