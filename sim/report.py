"""批量跑机器人并出报告（PLAN 第 7 步）。

    python3 -m sim.report                 # 每种机器人 200 局
    python3 -m sim.report --n 50 --bots 专练情人,乱选
    python3 -m sim.report --random-play   # 机器人随机出牌（对照 N60 的随机配对）

输出不超过 60 行：各路声望的月度分位数和练满月份、每年末金钱和负债月数、试镜场数和胜率、
大片通过率、大卖率、主演部数、名气档分布、结局分布，最后和 N60 的粗算表并排。
练满 = 目标路三项训练值之和 ≥ 300（乱选、犯罪线、只读书文化取四路里最早练满的）。
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from .bots import BOTS, PURE, play

# N60（design/DESIGN_NOTES.md）：每条路 400 局粗算，不买装备。
N60 = {
    '专练硬汉': dict(满=18, 现金=(806, 967, 1222, 5483), p90=7720, 过311=80, 试镜=75, 大片=33, 大卖=7),
    '专练情人': dict(满=21, 现金=(300, 701, 620, 2091), p90=4683, 过311=90, 试镜=70, 大片=26, 大卖=13),
    '专练文化': dict(满=21, 现金=(828, 1538, 1832, 5446), p90=8222, 过311=93, 试镜=74, 大片=35, 大卖=14),
    '专练手腕': dict(满=19, 现金=(1646, 3862, 7639, 13191), p90=16656, 过311=92, 试镜=72, 大片=44, 大卖=12),
}
TIER_NAMES = ['新人', '小有名气', '当红', '巨星', '传奇']


def _job(args):
    name, seed, smart = args
    return play(BOTS[name], seed, smart_play=smart)


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return float('nan')
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def med(xs):
    return pct(xs, 0.5)


def first_month(rec, fn):
    """第一个满足 fn(月末记录) 的月序 + 1（1 起数），没有为 None。"""
    for m in range(len(rec['train'])):
        if fn(m):
            return m + 1
    return None


def full_month(rec):
    return first_month(rec, lambda m: max(rec['train'][m]) >= 300)


def rep_month(rec, line):
    return first_month(rec, lambda m: max(rec['rep'][m]) >= line)


def fmt_q(xs, n):
    """中位 (p10–p90)，None 算没达到；达到的比例太低时标出。"""
    got = [x for x in xs if x is not None]
    if not got:
        return '—'
    s = f'{med(got):.0f}({pct(got, .1):.0f}–{pct(got, .9):.0f})'
    if len(got) < n * 0.9:
        s += f'[{len(got) * 100 // n}%]'
    return s


def ratio(a, b):
    return 100 * a / b if b else float('nan')


def run(n, names, smart, workers):
    jobs = [(nm, s, smart) for nm in names for s in range(1, n + 1)]
    with ProcessPoolExecutor(workers) as ex:
        recs = list(ex.map(_job, jobs, chunksize=8))
    out = {nm: [] for nm in names}
    for r in recs:
        out[r['bot']].append(r)
    return out


def report(res, n, smart):
    L = []
    L.append(f"== 每种机器人 {n} 局（种子 1–{n}），出牌{'贪心' if smart else '随机'} ==")
    L.append('-- 练满月（中位(10%–90%)）| 声望过 150 / 210 的月 | 声望中位 第12/24/36/48月 | 末声望含/不含年度 过311')
    for nm, rs in res.items():
        k = len(rs)
        mm = [med([max(r['rep'][min(m, len(r['rep']) - 1)]) for r in rs]) for m in (11, 23, 35, 47)]
        p311 = ratio(sum(r['无年度声望'] >= 311 for r in rs), k)
        L.append(f"{nm:<8} 满 {fmt_q([full_month(r) for r in rs], k):<14} 150:{fmt_q([rep_month(r, 150) for r in rs], k):<12}"
                 f" 210:{fmt_q([rep_month(r, 210) for r in rs], k):<12} {'/'.join(f'{x:.0f}' for x in mm)}"
                 f" | {med([r['最高声望'] for r in rs]):.0f}/{med([r['无年度声望'] for r in rs]):.0f} 过311 {p311:.0f}%")
    L.append('-- 每年末现金中位（第 1–4 年）| 期末 p90 | 期末>1万的局 | 负债月数均值')
    for nm, rs in res.items():
        y = [med([r['money'][min(m, len(r['money']) - 1)] for r in rs]) for m in (11, 23, 35, 47)]
        end = [r['money'][-1] for r in rs]
        L.append(f"{nm:<8} {' / '.join(f'{v:,.0f}' for v in y):<36} p90 {pct(end, .9):>7,.0f}  >1万 {ratio(sum(e > 10000 for e in end), len(end)):.0f}%"
                 f"  负债 {sum(r['debt'] for r in rs) / len(rs):.1f}")
    L.append('-- 试镜（局均场数 | 拿到% | 大片场数 通过%）| 上映局均 大卖% 扑街% | 主演 小/中/大 | 配角 违约')
    for nm, rs in res.items():
        s = lambda k: sum(r[k] for r in rs)
        k = len(rs)
        L.append(f"{nm:<8} {s('计数.试镜') / k:4.1f}场 {ratio(s('计数.试镜拿到'), s('计数.试镜')):3.0f}%  大片 {s('计数.试镜.大') / k:3.1f}场 {ratio(s('计数.试镜拿到.大'), s('计数.试镜.大')):3.0f}%"
                 f" | 上映 {s('计数.上映') / k:4.1f} 大卖 {ratio(s('计数.大卖'), s('计数.上映')):3.0f}% 扑街 {ratio(s('计数.扑街'), s('计数.上映')):3.0f}%"
                 f" | {s('计数.主演.小') / k:.1f}/{s('计数.主演.中') / k:.1f}/{s('计数.主演.大') / k:.1f} | {s('计数.配角') / k:.1f} {s('计数.违约') / k:.1f}")
    L.append('-- 期末名气档（新人/小有名气/当红/巨星/传奇 %）| 倒下% | 结局（种类数；最多的三个）')
    for nm, rs in res.items():
        k = len(rs)
        c = Counter(r['名气档'] for r in rs)
        e = Counter(r['结局'] for r in rs)
        top = ' '.join(f'{x.replace("end_", "")}{v * 100 // k}%' for x, v in e.most_common(3))
        L.append(f"{nm:<8} {'/'.join(str(c.get(i, 0) * 100 // k) for i in range(5)):<16} 倒下 {ratio(e.get('end_collapse', 0), k):.0f}%  结局 {len(e)} 种：{top}")
    L.append('-- 对 N60（粗算；左本次，右 N60）：练满月 | 年末现金中位 | 期末p90 | 过311% | 试镜胜率% | 大片% | 大卖%')
    for nm in PURE:
        if nm not in res:
            continue
        rs, o, k = res[nm], N60[nm], len(res[nm])
        s = lambda key: sum(r[key] for r in rs)
        y = [med([r['money'][min(m, len(r['money']) - 1)] for r in rs]) for m in (11, 23, 35, 47)]
        L.append(f"{nm:<8} {med([x for x in (full_month(r) for r in rs) if x]):.0f}|{o['满']}  "
                 f"{'/'.join(f'{v:.0f}' for v in y)} | {'/'.join(map(str, o['现金']))}  "
                 f"{pct([r['money'][-1] for r in rs], .9):.0f}|{o['p90']}  {ratio(sum(r['无年度声望'] >= 311 for r in rs), k):.0f}|{o['过311']}  "
                 f"{ratio(s('计数.试镜拿到'), s('计数.试镜')):.0f}|{o['试镜']}  {ratio(s('计数.试镜拿到.大'), s('计数.试镜.大')):.0f}|{o['大片']}  "
                 f"{ratio(s('计数.大卖'), s('计数.上映')):.0f}|{o['大卖']}")
    return L


def main():
    ap = argparse.ArgumentParser(description='批量跑机器人出报告')
    ap.add_argument('--n', type=int, default=200, help='每种机器人跑几局')
    ap.add_argument('--bots', default=','.join(BOTS), help='逗号分隔的机器人名')
    ap.add_argument('--random-play', action='store_true', help='机器人随机出牌（乱选不受影响）')
    ap.add_argument('--workers', type=int, default=None)
    a = ap.parse_args()
    names = a.bots.split(',')
    smart = False if a.random_play else None
    res = run(a.n, names, smart, a.workers)
    for line in report(res, a.n, not a.random_play):
        print(line)


if __name__ == '__main__':
    main()
