"""Runs bots in bulk and prints a report (PLAN steps 7, 8).

    python3 -m sim.report                 # 200 games per bot
    python3 -m sim.report --n 50 --bots only_lover,random_pick
    python3 -m sim.report --random-play   # bots play random cards
    python3 -m sim.report --no-buy        # bots do not buy gear

At most 60 lines of output. The brackets hold the targets of PLAN step 8.
Full training = the target road's three training values sum to >= 300 (random_pick, crime_line and books_culture take whichever of the four roads is full first).
Main road = the road with the highest final reputation. "Full training plus plain releases" = main road training value + the bonus from releases (no gear, stamina bonus, annual events or opportunities).
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from .bots import BOTS, PURE, play



def _job(args):
    name, seed, smart, buy = args
    return play(BOTS[name], seed, smart_play=smart, buy=buy)


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float('nan')
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def med(xs):
    return pct(xs, 0.5)


def first_month(rec, fn):
    """Month index + 1 (counted from 1) of the first month satisfying fn(month-end record); None if there is none."""
    for m in range(len(rec['train'])):
        if fn(m):
            return m + 1
    return None


def full_month(rec):
    return first_month(rec, lambda m: max(rec['train'][m]) >= 300)


def rep_month(rec, line):
    return first_month(rec, lambda m: max(rec['rep'][m]) >= line)


def fmt_q(xs, n):
    """Median (p10-p90); None counts as not reached; flags it when the share reaching it is too low."""
    got = [x for x in xs if x is not None]
    if not got:
        return '—'
    s = f'{med(got):.0f}({pct(got, .1):.0f}–{pct(got, .9):.0f})'
    if len(got) < n * 0.9:
        s += f'[{len(got) * 100 // n}%]'
    return s


def ratio(a, b):
    return 100 * a / b if b else float('nan')


def run(n, names, smart, workers, buy=None):
    jobs = [(nm, s, smart, buy) for nm in names for s in range(1, n + 1)]
    with ProcessPoolExecutor(workers) as ex:
        recs = list(ex.map(_job, jobs, chunksize=8))
    out = {nm: [] for nm in names}
    for r in recs:
        out[r['bot']].append(r)
    return out


def report(res, n, smart, nobuy=None):
    L = []
    L.append(f"== each bot {n} games (seeds 1-{n}), cards played {'greedy' if smart else 'random'}; targets: PLAN step 8 ==")
    L.append('-- full-training month median (10%-90%) [target 16-21] | months with rep >= 210 | main-road rep median at months 12/24/36/48')
    for nm, rs in res.items():
        k = len(rs)
        mm = [med([max(r['rep'][min(m, len(r['rep']) - 1)]) for r in rs]) for m in (11, 23, 35, 47)]
        L.append(f"{nm:<8} full {fmt_q([full_month(r) for r in rs], k):<14} 210:{fmt_q([rep_month(r, 210) for r in rs], k):<12} {'/'.join(f'{x:.0f}' for x in mm)}")
    L.append('-- final main-road rep breakdown (mean): training+gear and stamina+releases+annual+opportunities | full training plus plain releases (no gear) median [311-340], over 311 [90%] | grade S/A/B/C/D %')
    for nm, rs in res.items():
        k = len(rs)
        av = lambda key: sum(r['breakdown'][key] for r in rs) / k
        plain = [r['breakdown']['training'] + r['breakdown']['release'] for r in rs]
        t = Counter(r['grade'] for r in rs)
        L.append(f"{nm:<8} {av('training'):3.0f}+{av('gear'):2.0f}+{av('release'):2.0f}+{av('annual'):2.0f}+{av('opportunity'):2.0f} = {med([r['max_rep'] for r in rs]):3.0f}"
                 f" | {med(plain):.0f} over 311 {ratio(sum(x >= 311 for x in plain), k):3.0f}%"
                 f" | {'/'.join(str(t.get(x, 0) * 100 // k) for x in 'SABCD')}")
    L.append('-- cash at each year end, median (years 1-4) [first two years <1000] | final p90 [<10k] | final >10k | debt months | film fees total, gear spend (mean)')
    for nm, rs in res.items():
        k = len(rs)
        y = [med([r['money'][min(m, len(r['money']) - 1)] for r in rs]) for m in (11, 23, 35, 47)]
        end = [r['money'][-1] for r in rs]
        L.append(f"{nm:<8} {' / '.join(f'{v:,.0f}' for v in y):<32} p90 {pct(end, .9):>7,.0f}  >10k {ratio(sum(e > 10000 for e in end), k):3.0f}%"
                 f"  debt {sum(r['debt'] for r in rs) / k:4.1f} | {sum(r['fee'] for r in rs) / k:6,.0f} {sum(r['gear_buy'] for r in rs) / k:5,.0f}")
    L.append('-- auditions per game, won% small/medium/big [big 10-35%] | releases per game, hit% [10%] flop% | leads small/medium/big | supports, breaches')
    for nm, rs in res.items():
        s = lambda key: sum(r[key] for r in rs)
        k = len(rs)
        w = lambda t: f"{ratio(s('count.audition_won.' + t), s('count.audition.' + t)):.0f}"
        L.append(f"{nm:<8} {s('count.audition') / k:4.1f} games {w('small')}/{w('medium')}/{w('big')}% (big {s('count.audition.big') / k:.1f} games)"
                 f" | release {s('count.release') / k:4.1f} hit {ratio(s('count.hit'), s('count.release')):3.0f}% flop {ratio(s('count.flop'), s('count.release')):3.0f}%"
                 f" | {s('count.lead.small') / k:.1f}/{s('count.lead.medium') / k:.1f}/{s('count.lead.big') / k:.1f} | {s('count.support') / k:.1f} {s('count.breach') / k:.1f}")
    L.append('-- median fame at each year end | final fame tier unknown/familiar/famous/hot/superstar % | mean annual rank (years 1-4) | collapse% | endings (kinds [>=3]; top four)')
    for nm, rs in res.items():
        k = len(rs)
        c = Counter(r['fame_tier'] for r in rs)
        e = Counter(r['ending'] for r in rs)
        fy = [med([r['fame'][min(m, len(r['fame']) - 1)] for r in rs]) for m in (11, 23, 35, 47)]
        rk = []
        for i in range(4):
            xs = [r['annual_rank'][i] for r in rs if len(r['annual_rank']) > i and r['annual_rank'][i]]
            rk.append(f'{sum(xs) / len(xs):.1f}' if xs else '-')
        top = ' '.join(f'{x.replace("end_", "")}{v * 100 // k}%' for x, v in e.most_common(4))
        L.append(f"{nm:<8} {'/'.join(f'{x:.0f}' for x in fy):<16} {'/'.join(str(c.get(i, 0) * 100 // k) for i in range(5)):<14}"
                 f" rank {'/'.join(rk)}  collapse {ratio(e.get('end_collapse', 0), k):.0f}%  endings {len(e)} kinds: {top}")
    if nobuy:
        L.append('-- without buying gear: final cash median / p90 | final main-road rep median | grade S/A/B/C/D %')
        for nm, rs in nobuy.items():
            k = len(rs)
            end = [r['money'][-1] for r in rs]
            t = Counter(r['grade'] for r in rs)
            L.append(f"{nm:<8} {med(end):>7,.0f} / {pct(end, .9):>7,.0f} | {med([r['max_rep'] for r in rs]):.0f} | {'/'.join(str(t.get(x, 0) * 100 // k) for x in 'SABCD')}")
    return L


def main():
    ap = argparse.ArgumentParser(description='run the bots in bulk and print a report')
    ap.add_argument('--n', type=int, default=200, help='games per bot')
    ap.add_argument('--bots', default=','.join(BOTS), help='comma-separated bot names')
    ap.add_argument('--random-play', action='store_true', help='bots play random cards (random_pick is unaffected)')
    ap.add_argument('--no-buy', action='store_true', help='bots do not buy gear')
    ap.add_argument('--workers', type=int, default=None)
    a = ap.parse_args()
    names = a.bots.split(',')
    smart = False if a.random_play else None
    res = run(a.n, names, smart, a.workers, False if a.no_buy else None)
    pure = [x for x in names if x in PURE]
    nobuy = run(a.n, pure, smart, a.workers, False) if pure and not a.no_buy else None
    for line in report(res, a.n, not a.random_play, nobuy):
        print(line)


if __name__ == '__main__':
    main()
