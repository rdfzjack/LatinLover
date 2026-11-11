"""Month flow (GDD 4): month start, three periods, month-end events, month settlement.

Everything step 6 plugs in (board, period-start checks, shooting, events, releases, rivals, annual events, era events, endings)
is a method of Hooks; by default they do nothing here.

Usage:
    g = Game(load(), seed=1, origin=(0, 1, 2))
    while not g.st.finished:
        g.start_month()          # charge living costs, build the board
        street.buy(g.st, 'bookstore', 'book_tantu_1')   # free actions at the start of the month
        g.run_month(['class_acting', 'job_dock', 'rest_home'])

Command line: python3 -m sim.month --seed 1 --origin 0,1,2 --plan class_acting,job_dock,rest_home
Prints one status line per month, for reconciliation with Godot (PLAN step 10).
"""
import argparse

from . import rules, schedule
from .data import load
from .state import State


class Hooks:
    """The parts implemented in steps 5 and 6. Every method gets the State and may change it."""

    def board(self, st): pass                       # the board in months 1, 4, 7, 10
    def month_start(self, st): pass                 # before the free actions of the month (write script, send to detox ...)
    def locked(self, st, i): return None            # returns the film contract when period i is locked by shooting
    def film_period(self, st, i, film, days): pass  # shooting period
    def film_breach(self, st): pass                 # very sick: the shoots already locked for next month breach
    def period_start(self, st, i, entry): pass      # period-start checks: swap role, steal role (11.1)
    def period_end(self, st, i, entry, out): pass   # after a period's schedule is done (Duv's tip-off in tutoring periods etc.)
    def day(self, st, day): pass                    # per-day events such as birthdays
    def outing(self, st, place): pass               # outing event (5.5.2)
    def class_chain(self, st, chain, n): pass       # Duv's story in tutoring (period n)
    def book_done(self, st, bid): pass              # finish-reading event
    def job_period(self, st, jid, good): pass       # job hook: period_random, milestones
    def month_events(self, st): pass                # month-end events (11.2)
    def release(self, st): pass                     # release settlement (8)
    def rival_growth(self, st): pass                # rival table swap in October
    def annual(self, st): pass                      # annual event in December
    def era(self, st, ids): pass                    # era events
    def ending(self, st): pass                      # ending resolution in 1929-12


class Game:
    def __init__(self, data=None, seed=0, origin=(0, 0, 0), hooks=None, state=None):
        self.d = data or load()
        self.st = state or State.new(self.d, seed, origin)
        self.hooks = hooks or Hooks()
        self.started = False
        self.last = []          # summary of each period of this month

    # ---------- 1. month start ----------
    def start_month(self):
        st, d = self.st, self.d
        if st.finished:
            raise RuntimeError('this game is already over')
        if self.started:
            raise RuntimeError('the month has already started')
        self.started = True
        st.month_used = {}
        st.exposed = 0
        st.status['shoot_this_month'] = 0
        # stamina <15 and the lifestyle is not fine: forced back to fine (GDD 5.7)
        if st.val('stamina') < 15 and st.lifestyle != 'life_fine':
            st.lifestyle = 'life_fine'
        life = d.lifestyles[st.lifestyle]
        st.money -= life['monthly_cost'][st.fame_tier()]     # may go negative
        if st.month['board']:
            self.hooks.board(st)
        self.hooks.month_start(st)

    def set_lifestyle(self, lid):
        """Changes the lifestyle before scheduling at month start; takes effect when it is charged next month."""
        if lid not in self.d.lifestyles:
            raise ValueError(lid)
        self.st.lifestyle = lid

    # ---------- 2. the three periods ----------
    def plan_errors(self, plan):
        """Checks this month's schedule and returns [(period, reason)]. Months with a shoot lock, forced sanatorium or void schedule are not checked."""
        st = self.st
        if st.forced_rest or st.void_next:
            return []
        if len(plan) != 3:
            return [(None, 'need 3 periods')]
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
            raise schedule.ScheduleError(f'{st.date} cannot schedule like this: {errs}')
        forced, void = st.forced_rest, st.void_next
        st.forced_rest = st.void_next = 0
        self.last = []
        for i in range(3):
            days = schedule.days_of(st, i)
            if void:
                self.last.append({'schedule': 'void'})
                continue
            film = h.locked(st, i)
            if film:
                st.status['shooting_period'] = 1
                st.status['shoot_this_month'] = 1
                h.film_period(st, i, film, days)
                st.status['shooting_period'] = 0
                self.last.append({'schedule': 'shooting'})
                continue
            e = plan[i] if not forced else self._forced_entry(i)
            h.period_start(st, i, e)
            out = schedule.run_period(st, i, e, h)
            h.period_end(st, i, e, out)
            self.last.append(out)
        if st.flags.get('accent_period', 0) > 0:      # 4-month bonus after the accent event, one less after each month
            st.flags['accent_period'] -= 1
        h.month_events(st)
        self.end_month()

    def _forced_entry(self, i):
        """The month after very sick: sanatorium; when the money for that period cannot pay 8 a day it falls back to resting at home (GDD 10)."""
        st, d = self.st, self.d
        f = d.rest_forced[0]
        need = d.rests[f['schedule']]['cost'] * len(schedule.days_of(st, i))
        return f['schedule'] if st.money >= need else f['if_broke_switch']

    # ---------- 4. month settlement ----------
    def end_month(self):
        st, d, h = self.st, self.d, self.hooks
        m = st.month
        # 1 lifestyle
        eff = d.lifestyles[st.lifestyle]['month_end_effect']
        if eff:
            rules.apply_effect(st, eff, source='schedule')
        # 2 releases
        h.release(st)
        # 3 fame decay
        if not st.exposed:
            fr = d.t['stats']['fame_rules']
            f = st.attr['fame']
            st.attr['fame'] = max(0, f - max(fr['monthly_decay_min'], f * fr['monthly_decay_pct'] // 100))
        # 4 indices and status
        st.update_indices()
        # 5 very sick, collapse
        if st.status['very_sick']:
            st.forced_rest = 1
            h.film_breach(st)
        st.collapse_months = st.collapse_months + 1 if st.idx['sick_index'] >= 100 else 0
        if st.collapse_months >= 2:
            st.ended = 'end_collapse'
            st.finished = 1
            h.ending(st)
            self.started = False
            return
        # 6 in_love timer
        rr = d.t['romance']['rules']['love_state']
        if st.status['in_love']:
            st.romance_months += 1
            for n in rr['lines']:
                st.favor[n] = max(0, st.favor.get(n, 0) + rr['monthly_favor'])
            if st.romance_months >= rr['duration_months'] and st.highest_base() != 'looks':
                st.status['in_love'] = 0
                st.romance_months = 0
        # 7 debt
        st.debt_months = st.debt_months + 1 if st.money < 0 else 0
        # 8–11
        if m['rival_growth']:
            h.rival_growth(st)
        if m['annual']:
            h.annual(st)
        if m['era_events']:
            h.era(st, m['era_events'])
        if m['ending_check']:
            h.ending(st)
            st.finished = 1
        self.started = False
        if not st.finished:
            st.ym += 1
            if st.ym >= len(d.months):
                st.finished = 1

    # ---------- save / load ----------
    def save(self):
        if self.started:
            raise RuntimeError('saving is only allowed between two months')
        return self.st.dumps()

    @classmethod
    def restore(cls, s, data=None, hooks=None):
        data = data or load()
        return cls(data, hooks=hooks, state=State.loads(data, s))


# ---------- reconciliation output ----------
def trace_line(st, date=None):
    """One line per month: date, money, 8 attributes, 12 training values, 4 road reputations, the two indices, logic stream state.
        st.date is already next month after settlement, so the caller passes the date."""
    d = st.d
    a = ' '.join(str(st.attr[k]) for k in d.attrs)
    s = ' '.join(str(st.skill[k]) for k in d.skills)
    b = st.bonus()
    r = ' '.join(str(st.rep(k, b)) for k in d.roads)
    return (f"{date or st.date} ${st.money} | {a} | {s} | {r} | {st.idx['sick_index']} {st.idx['reckless_index']} "
            f"| {st.rng.logic.dump()[0]}")


def run_fixed(seed, origin, plan, data=None):
    """Runs a fixed schedule for all 48 months and returns one line per month (state after settlement)."""
    g = Game(data, seed=seed, origin=origin)
    lines = []
    while not g.st.finished:
        date = g.st.date
        g.start_month()
        g.run_month(plan if not callable(plan) else plan(g.st))
        lines.append(trace_line(g.st, date))
    return lines


def main():
    ap = argparse.ArgumentParser(description='run one game with a fixed schedule, print one status line per month')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--origin', default='0,0,0', help='option index of each opening question, counting from 0')
    ap.add_argument('--plan', default='class_acting,job_dock,rest_home', help='the three period entries of each month')
    a = ap.parse_args()
    origin = tuple(int(x) for x in a.origin.split(','))
    for line in run_fixed(a.seed, origin, a.plan.split(',')):
        print(line)


if __name__ == '__main__':
    main()
