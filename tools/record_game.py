"""Step 12 reconciliation: records the decisions of a bot playing one whole game, and replays a recording.

A recording is JSON:
    {"bot", "seed", "origin", "extras",
     "answers": [[method, answer], ...],        every Agent answer in the order it was asked, month_start included
     "months": [{"actions": [...], "plan": [three entries]}, ...]}
`month_start` answers are lists of actions; `months[n].actions` are the actions done while scheduling (the bots buy books then).
An action is a list:
    ["buy", entry, item]  ["equip", outfit, [accessories]]  ["count", key, value]  ["script", kind, color]
    ["detox"]  ["leak"]  ["restaurant", service]  ["church"]  ["hospital"]  ["persuade"]  ["use", item]  ["sell", item]
The Godot replay (game/silentstar/tools/trace.gd) reads the same file; tools/trace.py records the `games` cases of
tools/trace_cases.json into work/games/ and prints the replay, so run the Python trace before the Godot one.

    python3 tools/record_game.py --bot only_lover --seed 3 [--extras] [--out work/games/x.json]
    python3 tools/record_game.py --coverage --seeds 40        events and counters reached by each bot over many seeds

`--extras` adds month-start actions the bots never take (scripts, detox, news leaks, restaurant, church, hospital, Sil,
consumables, selling read books), decided by the recorder's own random stream, so the replay covers those paths too.
"""
import argparse
import copy
import hashlib
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sim import board, bots, schedule, street  # noqa: E402
from sim.data import load  # noqa: E402
from sim.month import trace_line  # noqa: E402
from sim.story import Agent, fit_plan, new_game  # noqa: E402

QUESTIONS = ('deck', 'play', 'pick_role', 'accept_support', 'go_personally', 'option', 'annual', 'family', 'suppress')


def js(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class ReplayError(Exception):
    pass


# ---------- actions ----------
def do_action(story, st, a):
    """Applies one recorded action. Raises ReplayError when it fails (the recording does not fit this game)."""
    k = a[0]
    try:
        if k == 'buy':
            street.buy(st, a[1], a[2])
        elif k == 'equip':
            st.equip = {'outfit': a[1], 'accessory': list(a[2])}
        elif k == 'count':
            st.count[a[1]] = a[2]
        elif k == 'script':
            story.write_script(st, a[1], a[2])
        elif k == 'detox':
            story.send_detox(st)
        elif k == 'leak':
            story.leak_news(st)
        elif k == 'restaurant':
            street.restaurant(st, a[1])
        elif k == 'church':
            street.church(st)
        elif k == 'hospital':
            street.hospital(st)
        elif k == 'persuade':
            street.sil_persuade(st)
        elif k == 'use':
            street.use(st, a[1])
        elif k == 'sell':
            street.sell(st, a[1])
        else:
            raise ReplayError(f'unknown action {a}')
    except (street.StreetError, ValueError) as e:
        raise ReplayError(f'action {a} failed: {e}')


class Extras:
    """Month-start actions the bots never take, and a favourite job worked into the plan, decided by its own random stream
    (not the game's). Only successful actions are recorded."""

    def __init__(self, seed, d):
        self.rnd = random.Random(seed * 7919 + 3)
        self.job = self.rnd.choice(list(d.jobs))

    def mix(self, g, plan):
        """The middle period becomes the favourite job most months, when it can be scheduled."""
        st = g.st
        if self.rnd.random() < 0.7 and not g.hooks.locked(st, 1) and schedule.validate(st, self.job) is None:
            plan = list(plan)
            plan[1] = self.job
        return plan

    def act(self, story, st, out):
        r = self.rnd
        for kind in ('co_written', 'self_written', 'duv_written'):
            if board.script_ok(st, kind) and r.random() < 0.7:
                color = r.randrange(4)
                story.write_script(st, kind, color)
                out.append(['script', kind, color])
        tries = []
        if st.drug >= 2 and not st.flags.get('detox_sent') and r.random() < 0.5:
            tries.append(['detox'])
        tries.append(['leak'])
        if st.val('fatigue') >= 20 and r.random() < 0.5:
            tries.append(['restaurant', r.choice([s['id'] for s in st.d.street['restaurant']['services']])])
        if st.val('crime') >= 20 and r.random() < 0.3:
            tries.append(['church'])
        tries.append(['hospital'])
        tries.append(['persuade'])
        for iid in dict.fromkeys(st.items):
            if st.d.items[iid]['class'] == 'consumable' and r.random() < 0.5:
                tries.append(['use', iid])
        for bid in list(st.read_books):
            if r.random() < 0.3:
                tries.append(['sell', bid])
        for a in tries:
            try:
                do_action(story, st, a)
            except ReplayError:
                continue
            out.append(a)


# ---------- recording ----------
class Recorder(Agent):
    """Wraps a bot: passes every question on and writes down the answer. An answer may not use the game's random numbers."""

    def __init__(self, bot, extras=None):
        self.bot = bot
        self.extras = extras
        self.answers = []
        self.sink = None            # where street.buy calls are written down

    def _ask(self, name, st, *args):
        before = st.rng.dump()
        v = getattr(self.bot, name)(st, *args)
        if st.rng.dump() != before:
            raise ReplayError(f'{type(self.bot).__name__}.{name} used the game random stream; it cannot be recorded')
        self.answers.append([name, list(v) if isinstance(v, tuple) else v])
        return v

    def month_start(self, story, st):
        acts = []
        eq, cnt = copy.deepcopy(st.equip), dict(st.count)
        self.sink = acts
        self.bot.month_start(story, st)
        self.sink = None
        for k in sorted(st.count):
            if st.count[k] != cnt.get(k):
                acts.append(['count', k, st.count[k]])
        if st.equip != eq:
            acts.append(['equip', st.equip['outfit'], list(st.equip['accessory'])])
        if self.extras:
            self.extras.act(story, st, acts)
        self.answers.append(['month_start', acts])


for _q in QUESTIONS:
    setattr(Recorder, _q, (lambda q: lambda self, st, *a: self._ask(q, st, *a))(_q))


def month_line(st, date):
    return trace_line(st, date) + ' | ' + hashlib.md5(st.dumps().encode('utf-8')).hexdigest()


def end_lines(g):
    h = g.hooks
    return ['ending ' + js(g.st.story['ending']),
            'events ' + js([r['id'] for r in h.log]),
            'annuals ' + js(h.annuals),
            'boards ' + js(h.boards),
            'save ' + g.st.dumps()]


def record(name, seed, extras=False, data=None):
    """Plays one game with the bot, writing down every decision. Returns (recording, output lines, Game)."""
    bot = bots.BOTS[name](seed)
    g = new_game(seed, bot.origin, None, data)
    rec = Recorder(bot, Extras(seed, g.d) if extras else None)
    g.hooks.agent = rec
    st = g.st
    months, lines = [], []
    real_buy = street.buy

    def buy(st_, entry, iid):
        p = real_buy(st_, entry, iid)
        if rec.sink is not None:
            rec.sink.append(['buy', entry, iid])
        return p

    street.buy = buy
    try:
        while not st.finished:
            date = st.date
            g.start_month()
            acts = []
            rec.sink = acts
            plan = bot.plan(g)
            if rec.extras:
                plan = rec.extras.mix(g, plan)
            plan = fit_plan(g, plan)
            rec.sink = None
            months.append({'actions': acts, 'plan': plan})
            g.run_month(plan)
            lines.append(month_line(st, date))
    finally:
        street.buy = real_buy
    out = {'bot': name, 'seed': seed, 'origin': list(bot.origin), 'extras': extras, 'answers': rec.answers, 'months': months}
    return out, lines + end_lines(g), g


# ---------- replay ----------
class Replay(Agent):
    """Answers every question from a recording, in order."""

    def __init__(self, answers):
        self.answers = answers
        self.pos = 0

    def take(self, name):
        if self.pos >= len(self.answers):
            raise ReplayError(f'asked {name} after the last recorded answer')
        q, v = self.answers[self.pos]
        if q != name:
            raise ReplayError(f'answer {self.pos}: asked {name}, recorded {q}')
        self.pos += 1
        return v

    def month_start(self, story, st):
        for a in self.take('month_start'):
            do_action(story, st, a)


for _q in QUESTIONS:
    setattr(Replay, _q, (lambda q: lambda self, st, *a: self.take(q))(_q))


def replay(rec, data=None):
    """Replays a recording. Returns the output lines (the same as record's); a failure ends the lines with 'replay error ...'."""
    ag = Replay(rec['answers'])
    g = new_game(rec['seed'], tuple(rec['origin']), ag, data)
    st = g.st
    lines = []
    try:
        for m in rec['months']:
            if st.finished:
                raise ReplayError('the game ended before the recording')
            date = st.date
            g.start_month()
            for a in m['actions']:
                do_action(g.hooks, st, a)
            g.run_month(m['plan'])
            lines.append(month_line(st, date))
        if not st.finished:
            raise ReplayError('the recording ended before the game')
        if ag.pos != len(ag.answers):
            raise ReplayError(f'{len(ag.answers) - ag.pos} recorded answers were not asked')
    except ReplayError as e:
        return lines + [f'replay error: {e}']
    return lines + end_lines(g)


# ---------- coverage ----------
COUNTS = ('count.arrest', 'count.scandal', 'count.scandal_covered', 'count.breach', 'count.opportunity', 'count.support',
          'count.stunt_self', 'count.injury', 'count.hit', 'count.flop', 'count.talkie_count')


def coverage(names, seeds, extras):
    """Prints, per bot, which events fired and which counters moved over many seeds, and the first seed reaching each."""
    d = load()
    for name in names:
        first = {}
        for s in seeds:
            _, _, g = record(name, s, extras, d)
            st = g.st
            keys = {r['id'] for r in g.hooks.log} | {k for k in COUNTS if st.cnt(k)}
            keys.add('ending:' + st.story['ending']['ending'])
            if st.story['films'] and any(f['roles']['source'] != 'pool' for f in st.story['films']):
                keys |= {'film:' + f['roles']['source'] for f in st.story['films']}
            for k in keys:
                first.setdefault(k, s)
        print(f'{name}: ' + ' '.join(f'{k}@{v}' for k, v in sorted(first.items())))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bot', default=None, choices=list(bots.BOTS), help='default only_lover; with --coverage every bot')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--extras', action='store_true')
    ap.add_argument('--out', default=None)
    ap.add_argument('--coverage', action='store_true')
    ap.add_argument('--seeds', type=int, default=30)
    a = ap.parse_args()
    if a.coverage:
        coverage([a.bot] if a.bot else list(bots.BOTS), range(1, a.seeds + 1), a.extras)
        return
    name = a.bot or 'only_lover'
    rec, lines, _ = record(name, a.seed, a.extras)
    again = replay(json.loads(js(rec)))
    print('replay identical' if again == lines else 'replay DIFFERS')
    out = a.out or os.path.join(ROOT, 'work', 'games', f'{name}_{a.seed}{"_x" if a.extras else ""}.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(js(rec))
    print(f'wrote {out}: {len(rec["answers"])} answers, ending {lines[-5]}')


if __name__ == '__main__':
    main()
