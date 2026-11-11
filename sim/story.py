"""Connects the step-6 modules to the month flow: Story implements month.Hooks, Agent is the questions the player (UI or bot) must answer.

Usage:
    from sim.story import Story, SimpleAgent, new_game
    g = new_game(seed=1, origin=(0, 1, 2), agent=SimpleAgent())
    while not g.st.finished:
        g.start_month()                  # living costs, board (agent signs up, plays), agent.month_start
        g.run_month(plan)                # the three periods; periods locked by shooting ignore the plan
    g.st.story['ending']

Command line: python3 -m sim.story --seed 1 --origin 0,1,2 --plan class_acting,job_dock,rest_home
One reconciliation line per month (same as sim.month), the last line is the ending.
"""
import argparse

from . import audition, board, ending, events, film, rules, schedule
from .data import load
from .month import Game, Hooks, trace_line


class Agent(audition.Player):
    """The decisions the player has to make. The UI and the step-7 bots implement these methods; see SimpleAgent for the default implementation."""

    def pick_role(self, st, b, ok):
        """Board: pick one of the signable indexes ok to audition for; None means stop trying. b = st.story['board']."""
        raise NotImplementedError

    def accept_support(self, st, role):
        """On a narrow loss: whether to take a supporting part in the same film."""
        raise NotImplementedError

    def go_personally(self, st, role):
        """When a role that allows stunt_self is won: whether to do it yourself."""
        raise NotImplementedError

    def option(self, st, ev, avail):
        """Event option: avail is the list of pickable option indexes; returns one of them."""
        raise NotImplementedError

    def annual(self, st, opts):
        """Annual event: returns the occasion id; None means rest."""
        raise NotImplementedError

    def family(self, st):
        """Studio boss backs transition: returns a tag family name (tag_families of endings.json)."""
        raise NotImplementedError

    def suppress(self, st, kind):
        """Whether to suppress a scandal: kind is 'free' or 'paid' (200)."""
        raise NotImplementedError

    def month_start(self, story, st):
        """Free actions at the start of the month: story.write_script / send_detox / leak_news, the street etc. (they take no schedule slot)."""


class SimpleAgent(Agent):
    """The simplest player, for tests and reconciliation:
        deck: main color (highest level) 3 cards + the color with the second-highest level 2 cards; plays at random with the logic stream;
        signs up for the first role of the highest signable size; takes supporting parts; does the stunt when possible; picks the first pickable event option;
        annual event: attends the road with the highest reputation; transition picks the first family; suppresses a scandal when possible; does nothing else at month start."""

    def deck(self, st, ctx):
        lv = ctx['levels']
        order = sorted(range(4), key=lambda c: (-lv[c], c))
        return [order[0]] * 3 + [order[1]] * 2

    def play(self, st, ctx):
        return st.rng.logic.below(len(ctx['hand']))

    def pick_role(self, st, b, ok):
        return max(ok, key=lambda i: (board.RANK[b['roles'][i]['size']], -i))

    def accept_support(self, st, role):
        return True

    def go_personally(self, st, role):
        return True

    def option(self, st, ev, avail):
        return avail[0]

    def annual(self, st, opts):
        b = st.bonus()
        best = max(opts, key=lambda x: (st.rep(x['road'], b), -opts.index(x)))
        return best['id']

    def family(self, st):
        return next(iter(st.d.tag_families))

    def suppress(self, st, kind):
        return True


class Story(Hooks):
    def __init__(self, agent=None):
        self.agent = agent or SimpleAgent()
        self.cur_period = 0
        self.log = []          # events fired in this game (not saved)
        self.boards = []       # audition results of each board (not saved)
        self.annuals = []

    # ---------- month start ----------
    def board(self, st):
        board.make(st)
        self.boards.append({'month': st.date, 'audition': board.run(st, self.agent)})

    def month_start(self, st):
        self.agent.month_start(self, st)

    # month-start actions (called by the player)
    def write_script(self, st, kind, color=None):
        board.write_script(st, kind, color)

    def send_detox(self, st):
        """Send to detox: allowed at drug_stage >= 2; the withdrawal event fires at the end of that month."""
        if st.drug < 2:
            raise ValueError('drug_stage below 2')
        st.flags['detox_sent'] = 1

    def leak_news(self, st):
        """Newspaper line favor 80: one news leak per year, fame +10%, counts as exposure."""
        y = st.ym // 12 + 1
        if not st.flags.get('leak_news') or st.story['leak_year'] == y:
            raise ValueError('cannot leak news now')
        st.story['leak_year'] = y
        events.fame_pct(st, 10)
        st.exposed = 1

    # ---------- the three periods ----------
    def locked(self, st, i):
        return film.locked(st, i)

    def film_period(self, st, i, f, days):
        film.shoot(st, i, f, days)

    def film_breach(self, st):
        film.breach_month(st, st.ym + 1)

    def period_start(self, st, i, entry):
        self.cur_period = i
        events.period_start(self, st, i, entry)

    def period_end(self, st, i, entry, out):
        events.period_end(self, st, i, entry, out)

    def day(self, st, day):
        events.day(self, st, day)

    def outing(self, st, place):
        events.outing(self, st, place)

    def class_chain(self, st, chain, n):
        events.class_chain(self, st, chain, n)

    def book_done(self, st, bid):
        events.book_done(self, st, bid)

    def job_period(self, st, jid, good):
        events.job_period(self, st, jid, good)

    # ---------- month end, settlement ----------
    def month_events(self, st):
        events.month_end(self, st)

    def release(self, st):
        film.release(st)

    def rival_growth(self, st):
        """Named rivals switch stage by the `from` date of rivals.json, unnamed rivals by the half-year count; nothing extra is needed in October."""

    def annual(self, st):
        events.annual(self, st)

    def era(self, st, ids):
        events.era(self, st, ids)

    def ending(self, st):
        ending.judge(st)


def new_game(seed=1, origin=(0, 0, 0), agent=None, data=None):
    return Game(data or load(), seed=seed, origin=origin, hooks=Story(agent))


def fit_plan(g, plan):
    """Replaces the entries of a fixed schedule that cannot be scheduled this month with resting at home (sick cannot go out, book finished, job not unlocked ...)."""
    st = g.st
    out = []
    for i, e in enumerate(plan):
        if g.hooks.locked(st, i) or schedule.validate(st, e) is None:
            out.append(e)
        else:
            out.append('rest_home')
    return out


def run(seed, origin, plan, agent=None, data=None):
    """Runs one game with a fixed schedule (entries that cannot be scheduled become resting at home). Returns (reconciliation lines per month, Game)."""
    g = new_game(seed, origin, agent, data)
    lines = []
    while not g.st.finished:
        date = g.st.date
        g.start_month()
        p = plan(g) if callable(plan) else plan
        g.run_month(fit_plan(g, p))
        lines.append(trace_line(g.st, date))
    return lines, g


def main():
    ap = argparse.ArgumentParser(description='run one game with a fixed schedule and SimpleAgent, one status line per month, print the ending at the end')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--origin', default='0,0,0', help='option index of each opening question, counting from 0')
    ap.add_argument('--plan', default='class_acting,job_dock,rest_home', help='the three period entries of each month')
    a = ap.parse_args()
    origin = tuple(int(x) for x in a.origin.split(','))
    lines, g = run(a.seed, origin, a.plan.split(','))
    for line in lines:
        print(line)
    st = g.st
    fs = film.films(st)
    print(f"films {len(fs)}: " + ' '.join(f"{f['size']}{'(support)' if f['support'] else ''}:{f['status']}" for f in fs))
    print(f"ending {st.story['ending']}")


if __name__ == '__main__':
    main()
