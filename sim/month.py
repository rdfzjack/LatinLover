"""月流程（GDD 4）：月初、三旬、月末事件、月结。

第 6 步要接的东西（选片板、旬初检查、拍摄、事件、上映、对手、年度大事、时代事件、结局）
都是 Hooks 的方法，这里默认什么都不做。

用法：
    g = Game(load(), seed=1, origin=(0, 1, 2))
    while not g.st.finished:
        g.start_month()          # 扣生活费、出选片板
        street.buy(g.st, '书店', 'book_tantu_1')   # 月初的自由操作
        g.run_month(['class_acting', 'job_dock', 'rest_home'])

命令行：python3 -m sim.month --seed 1 --origin 0,1,2 --plan class_acting,job_dock,rest_home
每月输出一行状态，供和 Godot 对账（PLAN 第 10 步）。
"""
import argparse

from . import rules, schedule
from .data import load
from .state import State


class Hooks:
    """第 5、6 步实现的部分。每个方法拿到 State，可以改它。"""

    def board(self, st): pass                       # 1、4、7、10 月月初的选片板
    def month_start(self, st): pass                 # 月初的自由操作之前（写剧本、送去戒…）
    def locked(self, st, i): return None            # 第 i 旬被拍摄锁定时返回片约
    def film_period(self, st, i, film, days): pass  # 拍摄旬
    def film_breach(self, st): pass                 # 重病：下月已锁定的拍摄违约
    def period_start(self, st, i, entry): pass      # 旬初检查：临时换角、抢角（11.1）
    def period_end(self, st, i, entry, out): pass   # 一旬日程做完（家教旬的 Duv 告密等）
    def day(self, st, day): pass                    # 生日等按日的事件
    def outing(self, st, place): pass               # 外出事件（5.5.2）
    def class_chain(self, st, chain, n): pass       # 家教的 Duv 剧情（第 n 旬）
    def book_done(self, st, bid): pass              # 读完事件
    def job_period(self, st, jid, good): pass       # 打工接口：每期随机、里程碑
    def month_events(self, st): pass                # 月末事件（11.2）
    def release(self, st): pass                     # 上映结算（8）
    def rival_growth(self, st): pass                # 10 月对手换表
    def annual(self, st): pass                      # 12 月年度大事
    def era(self, st, ids): pass                    # 时代事件
    def ending(self, st): pass                      # 1929-12 结局判定


class Game:
    def __init__(self, data=None, seed=0, origin=(0, 0, 0), hooks=None, state=None):
        self.d = data or load()
        self.st = state or State.new(self.d, seed, origin)
        self.hooks = hooks or Hooks()
        self.started = False
        self.last = []          # 本月每旬的小结

    # ---------- 1. 月初 ----------
    def start_month(self):
        st, d = self.st, self.d
        if st.finished:
            raise RuntimeError('这一局已经结束')
        if self.started:
            raise RuntimeError('本月已经开始')
        self.started = True
        st.month_used = {}
        st.exposed = 0
        st.status['当月有拍摄'] = 0
        # 体力 <15 且不是讲究：强制改回讲究（GDD 5.7）
        if st.val('体力') < 15 and st.lifestyle != 'life_fine':
            st.lifestyle = 'life_fine'
        life = d.lifestyles[st.lifestyle]
        st.money -= life['月费'][st.fame_tier()]     # 可以扣成负数
        if st.month['选片板']:
            self.hooks.board(st)
        self.hooks.month_start(st)

    def set_lifestyle(self, lid):
        """月初排日程前改生活方式；下个月初扣费时生效。"""
        if lid not in self.d.lifestyles:
            raise ValueError(lid)
        self.st.lifestyle = lid

    # ---------- 2. 三旬 ----------
    def plan_errors(self, plan):
        """检查本月日程，返回 [(旬, 原因)]。拍摄锁定、强制疗养、作废的月份不检查。"""
        st = self.st
        if st.forced_rest or st.void_next:
            return []
        if len(plan) != 3:
            return [(None, '要排 3 旬')]
        out = []
        for i, e in enumerate(plan):
            if self.hooks.locked(st, i):
                continue
            r = schedule.validate(st, e)
            if r:
                out.append((i, r))
        return out

    def run_month(self, plan):
        st, d, h = self.st, self.d, self.hooks
        if not self.started:
            self.start_month()
        errs = self.plan_errors(plan)
        if errs:
            raise schedule.ScheduleError(f'{st.date} 日程不能这样排：{errs}')
        forced, void = st.forced_rest, st.void_next
        st.forced_rest = st.void_next = 0
        self.last = []
        for i in range(3):
            days = schedule.days_of(st, i)
            if void:
                self.last.append({'日程': '作废'})
                continue
            film = h.locked(st, i)
            if film:
                st.status['拍摄旬'] = 1
                st.status['当月有拍摄'] = 1
                h.film_period(st, i, film, days)
                st.status['拍摄旬'] = 0
                self.last.append({'日程': '拍摄'})
                continue
            e = plan[i] if not forced else self._forced_entry(i)
            h.period_start(st, i, e)
            out = schedule.run_period(st, i, e, h)
            h.period_end(st, i, e, out)
            self.last.append(out)
        if st.flags.get('口音期', 0) > 0:      # 口音事件后的 4 个月加成，每过一个月减一
            st.flags['口音期'] -= 1
        h.month_events(st)
        self.end_month()

    def _forced_entry(self, i):
        """重病的下一个月：疗养院；那一旬的钱不够付每天 8 时改在家休息（GDD 10）。"""
        st, d = self.st, self.d
        f = d.rest_forced[0]
        need = d.rests[f['日程']]['花费'] * len(schedule.days_of(st, i))
        return f['日程'] if st.money >= need else f['钱不够改']

    # ---------- 4. 月结 ----------
    def end_month(self):
        st, d, h = self.st, self.d, self.hooks
        m = st.month
        # 1 生活方式
        eff = d.lifestyles[st.lifestyle]['月结效果']
        if eff:
            rules.apply_effect(st, eff, source='schedule')
        # 2 上映
        h.release(st)
        # 3 名气衰减
        if not st.exposed:
            fr = d.t['stats']['名气规则']
            f = st.attr['名气']
            st.attr['名气'] = max(0, f - max(fr['月衰减最少'], f * fr['月衰减百分比'] // 100))
        # 4 指数和状态
        st.update_indices()
        # 5 重病、倒下
        if st.status['重病']:
            st.forced_rest = 1
            h.film_breach(st)
        st.collapse_months = st.collapse_months + 1 if st.idx['生病指数'] >= 100 else 0
        if st.collapse_months >= 2:
            st.ended = 'end_collapse'
            st.finished = 1
            h.ending(st)
            self.started = False
            return
        # 6 恋爱计时
        rr = d.t['romance']['规则']['恋爱状态']
        if st.status['恋爱']:
            st.romance_months += 1
            for n in rr['作用线']:
                st.favor[n] = max(0, st.favor.get(n, 0) + rr['每月好感'])
            if st.romance_months >= rr['持续月数'] and st.highest_base() != '相貌':
                st.status['恋爱'] = 0
                st.romance_months = 0
        # 7 负债
        st.debt_months = st.debt_months + 1 if st.money < 0 else 0
        # 8–11
        if m['对手成长']:
            h.rival_growth(st)
        if m['年度大事']:
            h.annual(st)
        if m['时代事件']:
            h.era(st, m['时代事件'])
        if m['结局判定']:
            h.ending(st)
            st.finished = 1
        self.started = False
        if not st.finished:
            st.ym += 1
            if st.ym >= len(d.months):
                st.finished = 1

    # ---------- 存读档 ----------
    def save(self):
        if self.started:
            raise RuntimeError('只能在两个月之间存档')
        return self.st.dumps()

    @classmethod
    def restore(cls, s, data=None, hooks=None):
        data = data or load()
        return cls(data, hooks=hooks, state=State.loads(data, s))


# ---------- 对账输出 ----------
def trace_line(st, date=None):
    """一个月一行：日期、金钱、8 项属性、12 项训练值、4 路声望、两个指数、逻辑流状态。
    月结后 st.date 已经是下个月，所以日期由调用方传入。"""
    d = st.d
    a = ' '.join(str(st.attr[k]) for k in d.attrs)
    s = ' '.join(str(st.skill[k]) for k in d.skills)
    b = st.bonus()
    r = ' '.join(str(st.rep(k, b)) for k in d.roads)
    return (f"{date or st.date} ${st.money} | {a} | {s} | {r} | {st.idx['生病指数']} {st.idx['失控指数']} "
            f"| {st.rng.logic.dump()[0]}")


def run_fixed(seed, origin, plan, data=None):
    """固定日程跑满 48 个月，返回每月一行（月结后的状态）。"""
    g = Game(data, seed=seed, origin=origin)
    lines = []
    while not g.st.finished:
        date = g.st.date
        g.start_month()
        g.run_month(plan if not callable(plan) else plan(g.st))
        lines.append(trace_line(g.st, date))
    return lines


def main():
    ap = argparse.ArgumentParser(description='固定日程跑一局，每月输出一行状态')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--origin', default='0,0,0', help='开局三问的选项序号，从 0 数')
    ap.add_argument('--plan', default='class_acting,job_dock,rest_home', help='每月三旬的日程')
    a = ap.parse_args()
    origin = tuple(int(x) for x in a.origin.split(','))
    for line in run_fixed(a.seed, origin, a.plan.split(',')):
        print(line)


if __name__ == '__main__':
    main()
