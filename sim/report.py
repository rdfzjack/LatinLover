"""批量跑机器人并出报告（PLAN 第 7、8 步）。

    python3 -m sim.report                 # 每种机器人 200 局
    python3 -m sim.report --n 50 --bots 专练情人,乱选
    python3 -m sim.report --random-play   # 机器人随机出牌
    python3 -m sim.report --no-buy        # 机器人不买装备

输出不超过 60 行。方括号里是 PLAN 第 8 步的目标。
练满 = 目标路三项训练值之和 ≥ 300（乱选、犯罪线、只读书文化取四路里最早练满的）。
主路 = 期末声望最高的路。“练满加普通上映” = 主路训练值 + 上映给的修正（不含装备、体力加成、年度、机遇）。
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
    L.append(f"== 每种机器人 {n} 局（种子 1–{n}），出牌{'贪心' if smart else '随机'}；目标见 PLAN 第 8 步 ==")
    L.append('-- 练满月 中位(10%–90%) [目标 16–21] | 声望过 210 的月 | 主路声望中位 第12/24/36/48月')
    for nm, rs in res.items():
        k = len(rs)
        mm = [med([max(r['rep'][min(m, len(r['rep']) - 1)]) for r in rs]) for m in (11, 23, 35, 47)]
        L.append(f"{nm:<8} 满 {fmt_q([full_month(r) for r in rs], k):<14} 210:{fmt_q([rep_month(r, 210) for r in rs], k):<12} {'/'.join(f'{x:.0f}' for x in mm)}")
    L.append('-- 期末主路声望拆开（均值）：训练+装备和体力+上映+年度+机遇 | 练满加普通上映(不含装备) 中位 [311–340]，过311 [九成] | 档次 S/A/B/C/D %')
    for nm, rs in res.items():
        k = len(rs)
        av = lambda key: sum(r['拆'][key] for r in rs) / k
        plain = [r['拆']['训练'] + r['拆']['上映'] for r in rs]
        t = Counter(r['档次'] for r in rs)
        L.append(f"{nm:<8} {av('训练'):3.0f}+{av('加成'):2.0f}+{av('上映'):2.0f}+{av('年度'):2.0f}+{av('机遇'):2.0f} = {med([r['最高声望'] for r in rs]):3.0f}"
                 f" | {med(plain):.0f} 过311 {ratio(sum(x >= 311 for x in plain), k):3.0f}%"
                 f" | {'/'.join(str(t.get(x, 0) * 100 // k) for x in 'SABCD')}")
    L.append('-- 每年末现金中位（第 1–4 年）[前两年 <1000] | 期末 p90 [<1万] | 期末>1万 | 负债月 | 片酬合计 买装备（均值）')
    for nm, rs in res.items():
        k = len(rs)
        y = [med([r['money'][min(m, len(r['money']) - 1)] for r in rs]) for m in (11, 23, 35, 47)]
        end = [r['money'][-1] for r in rs]
        L.append(f"{nm:<8} {' / '.join(f'{v:,.0f}' for v in y):<32} p90 {pct(end, .9):>7,.0f}  >1万 {ratio(sum(e > 10000 for e in end), k):3.0f}%"
                 f"  负债 {sum(r['debt'] for r in rs) / k:4.1f} | {sum(r['片酬'] for r in rs) / k:6,.0f} {sum(r['买装备'] for r in rs) / k:5,.0f}")
    L.append('-- 试镜 局均场数，拿到% 小/中/大 [大 10–35%] | 上映局均 大卖% [一成] 扑街% | 主演 小/中/大 | 配角 违约')
    for nm, rs in res.items():
        s = lambda key: sum(r[key] for r in rs)
        k = len(rs)
        w = lambda t: f"{ratio(s('计数.试镜拿到.' + t), s('计数.试镜.' + t)):.0f}"
        L.append(f"{nm:<8} {s('计数.试镜') / k:4.1f}场 {w('小')}/{w('中')}/{w('大')}%（大片 {s('计数.试镜.大') / k:.1f} 场）"
                 f" | 上映 {s('计数.上映') / k:4.1f} 大卖 {ratio(s('计数.大卖'), s('计数.上映')):3.0f}% 扑街 {ratio(s('计数.扑街'), s('计数.上映')):3.0f}%"
                 f" | {s('计数.主演.小') / k:.1f}/{s('计数.主演.中') / k:.1f}/{s('计数.主演.大') / k:.1f} | {s('计数.配角') / k:.1f} {s('计数.违约') / k:.1f}")
    L.append('-- 各年末名气中位 | 期末名气档 无名/眼熟/有名/当红/巨星 % | 年度名次均值(1–4年) | 倒下% | 结局（种类数 [≥3]；最多的四个）')
    for nm, rs in res.items():
        k = len(rs)
        c = Counter(r['名气档'] for r in rs)
        e = Counter(r['结局'] for r in rs)
        fy = [med([r['fame'][min(m, len(r['fame']) - 1)] for r in rs]) for m in (11, 23, 35, 47)]
        rk = []
        for i in range(4):
            xs = [r['年度名次'][i] for r in rs if len(r['年度名次']) > i and r['年度名次'][i]]
            rk.append(f'{sum(xs) / len(xs):.1f}' if xs else '-')
        top = ' '.join(f'{x.replace("end_", "")}{v * 100 // k}%' for x, v in e.most_common(4))
        L.append(f"{nm:<8} {'/'.join(f'{x:.0f}' for x in fy):<16} {'/'.join(str(c.get(i, 0) * 100 // k) for i in range(5)):<14}"
                 f" 名次 {'/'.join(rk)}  倒下 {ratio(e.get('end_collapse', 0), k):.0f}%  结局 {len(e)} 种：{top}")
    if nobuy:
        L.append('-- 不买装备时：期末现金 中位 / p90 | 期末主路声望中位 | 档次 S/A/B/C/D %')
        for nm, rs in nobuy.items():
            k = len(rs)
            end = [r['money'][-1] for r in rs]
            t = Counter(r['档次'] for r in rs)
            L.append(f"{nm:<8} {med(end):>7,.0f} / {pct(end, .9):>7,.0f} | {med([r['最高声望'] for r in rs]):.0f} | {'/'.join(str(t.get(x, 0) * 100 // k) for x in 'SABCD')}")
    return L


def main():
    ap = argparse.ArgumentParser(description='批量跑机器人出报告')
    ap.add_argument('--n', type=int, default=200, help='每种机器人跑几局')
    ap.add_argument('--bots', default=','.join(BOTS), help='逗号分隔的机器人名')
    ap.add_argument('--random-play', action='store_true', help='机器人随机出牌（乱选不受影响）')
    ap.add_argument('--no-buy', action='store_true', help='机器人不买装备')
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
