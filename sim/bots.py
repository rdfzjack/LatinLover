"""Strategy bots (PLAN step 7): they plug into story.Agent and run whole games in bulk.

A bot = the options of the three opening questions + a plan(g) that schedules the three periods each month + the Agent's decisions.
    from sim.bots import BOTS, play
    rec = play(BOTS['only_lover'], seed=1)      # plays one game and returns a record (sim.report aggregates them)

The eight bots (names in BOTS):
    only_tough / only_lover / only_culture / only_savvy   train one road to full, then a second road; remaining periods go to jobs for money; buy gear of the road at the start of the month
    two_roads (tough + lover)                              of the two roads, train the one with the lower training value first
    random_pick                                            schedule, auditions and event options all random (uses its own random stream, not the game's)
    crime_line                                             only crime jobs: bootlegging, bar bouncer, dock
    books_culture                                          no classes, only reading; takes tutoring only when education is too low for the next book

Scheduling: rest when fatigue is high, take a job when there is not enough money for classes, buy books when there is.
All decisions are made at the start of the month (while scheduling); fatigue and money within the month are projected with estimates.

Auditions: deck building and role choice use a fast win-rate estimate (win rate of each main/second color layout when both sides play at random, weighted by style),
cards are played greedily by "how many of the rival's cards can this beat" (random when `smart_play=False`).
"""
import itertools

from . import audition, rules, schedule, street
from .rng import PCG32
from .story import SimpleAgent, fit_plan, new_game
from . import film

# ---------- the bot's own random numbers (PCG32, integers only, so Godot can copy them line by line) ----------
class BotRng:
    """The bot's own stream: PCG32 with sequence number 3 (the game uses 1 and 2), seeded with seed * 1000003 + 17.
    Everything is built on below(n); there is no float random. Every call consumes exactly one number."""

    def __init__(self, seed):
        self.g = PCG32(seed * 1000003 + 17, 3)

    def below(self, n):
        """0..n-1 (n >= 1)."""
        return self.g.below(n)

    def choice(self, seq):
        """One item of a non-empty list: seq[below(len(seq))]."""
        return seq[self.g.below(len(seq))]

    def chance(self, p, q):
        """True with probability p / q: below(q) < p."""
        return self.g.below(q) < p


# ---------- fast audition estimate ----------
_PERMS = list(itertools.permutations(range(5)))


class Est:
    """Win-rate estimator, cached per Data as constants."""

    def __init__(self, d):
        c = audition.cfg(d)
        self.d = d
        self.bt = audition.beats(d)
        self.fp = c['style_pct']
        self.win_pct = c['counter_pct']
        self.lose_pct = c['countered_pct']
        self.need = c['rounds_to_win']
        self.cache = {}

    def beat(self, a, b, field, fame_hi):
        (ca, pa), (cb, pb) = a, b
        va, vb = pa * 100, pb * 100
        if ca == field:
            va = va * self.fp // 100
        if cb == field:
            vb = vb * self.fp // 100
        if self.bt[ca] == cb and cb != field:
            va, vb = va * self.win_pct // 100, vb * self.lose_pct // 100
        elif self.bt[cb] == ca and ca != field:
            vb, va = vb * self.win_pct // 100, va * self.lose_pct // 100
        return va > vb if va != vb else fame_hi

    def p_field(self, mine, theirs, field, fame_hi):
        """Probability that I win the needed rounds first when both sides play at random (enumerates the 120 orderings of the rival's plays)."""
        m = [[self.beat(a, b, field, fame_hi) for b in theirs] for a in mine]
        need, n = self.need, 0
        for p in _PERMS:
            w = 0
            for i in range(5):
                if m[i][p[i]]:
                    w += 1
                    if w >= need:
                        n += 1
                        break
                elif i - w + 1 >= need:
                    break
        return n / 120

    def best(self, levels, rival, probs, fame_me):
        """Best deck against a rival: (win rate, color list). Candidates = mono, or main color 4/3 cards plus one second color."""
        d = self.d
        fame_hi = fame_me > rival['fame']
        key = (tuple(levels), tuple(rival['levels']), rival['k'], tuple(probs), fame_hi)
        r = self.cache.get(key)
        if r is None:
            theirs = audition.opponent_deck(d, rival, probs)
            r = (-1, None)
            for cols in audition.candidate_decks(levels).values():
                mine = audition.build_deck(levels, cols)
                p = sum(probs[f] * self.p_field(mine, theirs, f, fame_hi) for f in range(4) if probs[f]) / 100
                if p > r[0]:
                    r = (p, cols)
            if len(self.cache) > 20000:
                self.cache.clear()
            self.cache[key] = r
        return r


_EST = {}


def est_of(d):
    e = _EST.get(id(d))
    if e is None:
        e = _EST[id(d)] = Est(d)
    return e


# ---------- scheduling helpers ----------
CRIME_JOBS = ('job_bootleg', 'job_escort', 'job_bar')    # jobs excluded first when earning money
THRESH = {'big': 0.12, 'medium': 0.2, 'small': 0.0}                # Choosing a role: do not go if the win-rate estimate is below this line
ROAD_PLACE = {'tough': 'place_dock', 'lover': 'place_downtown', 'culture': 'place_downtown', 'savvy': 'place_studio'}
ROAD_JOBS = {'culture': ('job_news', 'job_model_art')}      # When short of money, first take jobs of the own road (the two culture opportunities need periods in these jobs)


def workdays(st, i):
    return sum(1 for _, sun in schedule.days_of(st, i) if not sun)


def alldays(st, i):
    return len(schedule.days_of(st, i))


def job_fat(j):
    return sum(e['add'][0] for e in j['daily_effect'] if e['stat'] == 'fatigue')


def can_do_job(st, jid, margin=10):
    """Available, and the displayed value is at least margin above the success line (fatigue will take some)."""
    if schedule.validate(st, jid) is not None:
        return False
    j = st.d.jobs[jid]
    return all(st.val(k) - margin >= v for k, v in schedule.job_lines(st, j))


def best_equip(st, road):
    """Swaps the held outfits and accessories for the set that gives `road` the highest reputation; returns the reputation after the swap."""
    d = st.d
    cl = [None] + sorted({i for i in st.items if d.items[i]['slot'] == 'outfit'}, key=d.item_order.get)
    ac = sorted({i for i in st.items if d.items[i]['slot'] == 'accessory'}, key=d.item_order.get)
    n = d.t['items']['rules']['accessory_slots']
    best = None
    for c in cl:
        for k in range(min(n, len(ac)), -1, -1):
            for a in itertools.combinations(ac, k):
                st.equip = {'outfit': c, 'accessory': list(a)}
                r = st.rep(road)
                if best is None or r > best[0]:
                    best = (r, c, list(a))
    st.equip = {'outfit': best[1], 'accessory': best[2]}
    return best[0]


class Bot(SimpleAgent):
    name = '?'
    origin = (0, 0, 3)          # Opening questions; question 3 picks "ring": it only gives a flag and changes no numbers
    smart_play = True
    crime = False
    buy = True                  # Buy gear of the own road at the start of the month (--no-buy of the report turns it off)
    gear_road = None            # Which road's gear to buy; None = buy nothing

    def __init__(self, seed=1):
        self.rnd = BotRng(seed)   # The bot's own random stream (PCG32, sequence 3), not the game's
        self.seed = seed

    # ---------- auditions ----------
    def deck(self, st, ctx):
        rv, role = ctx['opponents'], ctx['roles']
        return est_of(st.d).best(ctx['levels'], rv, role['style_probs'], st.attr['fame'])[1]

    def play(self, st, ctx):
        hand = ctx['hand']
        if not self.smart_play:
            return st.rng.logic.below(len(hand))
        d, field = st.d, ctx['style']
        fame_me, fame_them = st.attr['fame'], ctx['opponents']['fame']
        best, bi = None, 0
        for i, a in enumerate(hand):
            w = sum(audition.round_winner(d, a, b, field, fame_me, fame_them) for b in ctx['rival_hand'])
            k = (w, -a[1])          # Prefer the card that beats more; on ties play the smaller card first
            if best is None or k > best:
                best, bi = k, i
        return bi

    def role_p(self, st, e):
        """Win-rate estimate for signing up for this role: the product over the matches."""
        est = est_of(st.d)
        lv = audition.player_levels(st)
        p = 1.0
        for rv in e['opponents']:
            p *= est.best(lv, rv, e['style_probs'], st.attr['fame'])[0]
        return p

    def pick_role(self, st, b, ok):
        """From the biggest size down: go for the best role if its win rate clears the line, otherwise drop one size."""
        by = {}
        for i in ok:
            by.setdefault(b['roles'][i]['size'], []).append(i)
        for t in ('big', 'medium', 'small'):
            if t not in by:
                continue
            ps = [(self.role_p(st, b['roles'][i]), -i) for i in by[t]]
            p, ni = max(ps)
            if p >= THRESH[t]:
                return -ni
        return None

    # ---------- buying gear ----------
    def month_start(self, story, st):
        """Buy gear of the own road at the start of the month: each time pick the item that adds the most reputation per coin, keeping two months of living costs plus 200."""
        road = self.gear_road
        if not self.buy or road is None:
            return
        reserve = 2 * self.living(st) + 200
        for _ in range(4):
            base, best = st.rep(road), None
            for entry in ('clothing_store', 'general_store'):
                for iid in street.shelf(st, entry):
                    it = st.d.items[iid]
                    if it['class'] == 'consumable' or iid in st.items:
                        continue
                    p = street.price(st, entry, it['price'])
                    if st.money - p < reserve:
                        continue
                    old = dict(st.equip, accessory=list(st.equip['accessory']))
                    st.items.append(iid)
                    gain = best_equip(st, road) - base
                    st.items.remove(iid)
                    st.equip = old
                    if gain > 0 and (best is None or gain / p > best[0]):
                        best = (gain / p, entry, iid)
            if best is None:
                break
            street.buy(st, best[1], best[2])
            st.inc('count.gear_spend', street.price(st, best[1], st.d.items[best[2]]['price']))
        best_equip(st, road)

    # ---------- schedule ----------
    def plan(self, g):
        st = g.st
        if st.forced_rest or st.void_next:
            return ['rest_home'] * 3
        P = {'fat': st.val('fatigue'), 'money': st.money, 'cls': {}}
        out = []
        for i in range(3):
            f = g.hooks.locked(st, i)
            if f:
                P['fat'] += workdays(st, i) * film.shoot_cfg(st.d)['fatigue'][f['size']]
                out.append('rest_home')
                continue
            e = self.pick(g, P, i)
            self.apply(g, P, i, e)
            out.append(e)
        return out

    def living(self, st):
        return st.d.lifestyles[st.lifestyle]['monthly_cost'][st.fame_tier()]

    def delta(self, g, P, i, e):
        """Estimates (fatigue change, money change) of this period."""
        st, d = g.st, g.d
        kind, iid, place = schedule.parse_entry(e)
        w, n = workdays(st, i), alldays(st, i)
        if kind == 'class':
            k = st.cnt('class_periods.' + iid) + P['cls'].get(iid, 0) + 1
            L = 1 + sum(1 for s in d.class_steps if k > s)
            return w, -d.classes[iid]['fee'][L - 1] * w
        if kind == 'book':
            return w, 0
        if kind == 'job':
            return w * job_fat(d.jobs[iid]), int(schedule.wage_of(st, iid) * w * 0.7)
        if iid == 'rest_outing':
            return d.places[place]['fatigue_per_day'] * n, -schedule.place_cost(st, place) * n
        if iid == 'rest_sanatorium':
            return -11 * n, -8 * n
        return -5 * n, 0

    def apply(self, g, P, i, e):
        df, dm = self.delta(g, P, i, e)
        P['fat'] = max(0, P['fat'] + df)
        P['money'] += dm
        kind, iid, _ = schedule.parse_entry(e)
        if kind == 'class':
            P['cls'][iid] = P['cls'].get(iid, 0) + 1

    def rest_entry(self, g, P, i):
        st = g.st
        place = self.place
        if st.status['sick'] or P['money'] < 60 + schedule.place_cost(st, place) * 10:
            return 'rest_home'
        return 'rest_outing@' + place

    place = 'place_downtown'

    def pick(self, g, P, i):
        st, d = g.st, g.d
        want = self.want(g, P, i)
        if want is None:
            want = self.money_job(g, P)
        if want is None:
            return self.rest_entry(g, P, i)
        kind = schedule.parse_entry(want)[0]
        # Not enough money for classes or books: take a job
        df, dm = self.delta(g, P, i, want)
        reserve = self.living(st) if i == 2 else 0
        if kind == 'class' and P['money'] + dm < reserve:
            want = self.money_job(g, P)
            if want is None:
                return self.rest_entry(g, P, i)
            df, dm = self.delta(g, P, i, want)
            kind = 'job'
        # Rest when fatigue is high (>= 45, or this period would cross the discipline line)
        fat = P['fat']
        sta, disc = st.val('stamina'), st.val('discipline')
        if fat >= 45 or (fat >= 20 and (fat + df >= 10 + disc or fat + df >= sta + 5)):
            return self.rest_entry(g, P, i)
        # Go to church volunteering when discipline is low
        if kind == 'job' and not self.crime and disc < 35 and can_do_job(st, 'job_church', 0):
            return 'job_church'
        return want

    # ---------- finding work ----------
    def want(self, g, P, i):
        raise NotImplementedError

    def job_for(self, g, P, need, crime_ok=False):
        """The job that adds the most per day to the skills in `need` that are not yet full (minus the cost of fatigue, crime and discipline)."""
        st, d = g.st, g.d
        best = None
        for jid, j in d.jobs.items():
            if not can_do_job(st, jid):
                continue
            if not crime_ok and jid in CRIME_JOBS and jid != 'job_bar':
                continue
            gain = sum((e['add'][0] + e['add'][1]) / 2 for e in j['daily_effect']
                       if e['stat'] in need and st.skill.get(e['stat'], 100) < 100)
            if gain <= 0:
                continue
            pen = 0.05 * job_fat(j)
            for e in j['daily_effect']:
                if e['stat'] == 'crime' and e['add'][0] > 0 and not crime_ok:
                    pen += 0.15 * e['add'][0]
                if e['stat'] == 'discipline' and e['add'][1] < 0:
                    pen += 0.1 * -e['add'][1]
            score = gain - pen + 0.01 * schedule.wage_of(st, jid)
            if best is None or score > best[0]:
                best = (score, jid)
        return best[1] if best else None

    def money_job(self, g, P, allow=None):
        """Earning money: daily wage minus 1.5 x daily fatigue, crime jobs excluded. If the road has a matching job (ROAD_JOBS), do that first."""
        st, d = g.st, g.d
        for jid in ROAD_JOBS.get(getattr(self, 'road', None), ()):
            if can_do_job(st, jid):
                return jid
        best = None
        for jid, j in d.jobs.items():
            if jid in CRIME_JOBS and not self.crime:
                continue
            if not can_do_job(st, jid):
                continue
            score = schedule.wage_of(st, jid) - 1.5 * job_fat(j)
            if best is None or score > best[0]:
                best = (score, jid)
        return best[1] if best else None

    def book_for(self, st, skill):
        """The next book worth reading for this skill: (tier, book id) or None. When education is too low returns ('education', gate)."""
        d = st.d
        caps = {1: 40, 2: 70, 3: 100}
        for t in (1, 2, 3):
            if st.skill[skill] >= caps[t]:
                continue
            b = next((x for x in d.books.values() if x['skills'] == skill and x['tier'] == t), None)
            if b is None:
                return None
            if b['id'] in st.read_books:
                continue
            if b['id'] not in street.shelf(st, 'bookstore') and b['id'] not in st.books:
                return None
            if st.val('education') < b['education_gate']:
                return ('education', b['education_gate'])
            return (t, b['id'])
        return None

    def book_entry(self, g, P, skill):
        """The schedule entry for the book to read (buy it first if missing); None when the book cannot be read or cannot be afforded."""
        st, d = g.st, g.d
        r = self.book_for(st, skill)
        if r is None or r[0] == 'education':
            return None
        bid = r[1]
        if bid not in st.books:
            price = street.price(st, 'bookstore', d.books[bid]['price'])
            if P['money'] - price < self.living(st):
                return None
            street.buy(st, 'bookstore', bid)
            P['money'] -= price
        return bid

    def want_road(self, g, P, road):
        st = g.st
        sk, ed = st.skill, st.val('education')
        if road == 'lover':
            for s, c in (('acting', 'class_acting'), ('grooming', 'class_etiquette'), ('physique', 'class_dance')):
                if sk[s] < 100:
                    return c
        elif road == 'tough':
            for s, c in (('fight', 'class_boxing'), ('riding', 'class_riding')):
                if sk[s] < 100:
                    return c
            if sk['nerve'] < 100:
                return self.job_for(g, P, ['nerve'])
        elif road == 'culture':
            if sk['writing'] < 100 or ed < 300:
                return 'class_tutor'
            for s in ('taste', 'speech'):
                e = self.book_entry(g, P, s)
                if e:
                    return e
        elif road == 'savvy':
            if ed < 200 and (sk['negotiation'] < 70 or sk['business'] < 70):
                return 'class_tutor'
            for s in ('negotiation', 'business'):
                e = self.book_entry(g, P, s)
                if e:
                    return e
            need = [s for s in g.d.road_skills['savvy'] if sk[s] < 100]
            if need:
                return self.job_for(g, P, need)
        return None


class RoadBot(Bot):
    """Trains one road, then the second road once the first is full."""
    road = second = None

    def want(self, g, P, i):
        return self.want_road(g, P, self.road) or self.want_road(g, P, self.second)

    @property
    def place(self):
        return ROAD_PLACE[self.road]

    @property
    def gear_road(self):
        return self.road


class Hard(RoadBot):
    name, road, second, origin = 'only_tough', 'tough', 'lover', (0, 0, 3)


class Lover(RoadBot):
    name, road, second, origin = 'only_lover', 'lover', 'tough', (3, 2, 3)


class Culture(RoadBot):
    name, road, second, origin = 'only_culture', 'culture', 'lover', (4, 1, 3)


class Wrist(RoadBot):
    name, road, second, origin = 'only_savvy', 'savvy', 'lover', (1, 1, 3)


class Two(Bot):
    name, origin = 'two_roads', (0, 2, 3)
    roads = ('tough', 'lover')
    gear_road = 'tough'
    place = 'place_studio'

    def want(self, g, P, i):
        st = g.st
        tr = lambda r: sum(st.skill[s] for s in g.d.road_skills[r])
        for r in sorted(self.roads, key=tr):
            w = self.want_road(g, P, r)
            if w:
                return w
        return None


class Crime(Bot):
    name, origin, crime = 'crime_line', (1, 0, 3), True
    place = 'place_dock'

    def want(self, g, P, i):
        st = g.st
        # In the first period of each month go to the boxing gym (the gang boss and the thug boss endings need tough 210), the rest of the time do crime jobs
        if i == 0 and st.skill['fight'] < 100 and st.cnt('job_periods.job_bar') >= 3:
            return 'class_boxing'
        for jid in ('job_bootleg', 'job_bar', 'job_dock'):
            if can_do_job(st, jid):
                return jid
        return None


class BookCulture(Bot):
    name, origin = 'books_culture', (4, 1, 3)
    place = 'place_downtown'
    gear_road = 'culture'

    def want(self, g, P, i):
        st = g.st
        sk = st.skill
        blocked = False
        for s in sorted(('writing', 'taste', 'speech'), key=lambda s: sk[s]):
            r = self.book_for(st, s)
            if r is None:
                continue
            if r[0] == 'education':
                blocked = True
                continue
            e = self.book_entry(g, P, s)
            if e:
                return e
        return 'class_tutor' if blocked else None


class Random(Bot):
    name = 'random_pick'

    def __init__(self, seed=1):
        super().__init__(seed)
        self.origin = tuple(self.rnd.below(n) for n in (5, 4, 6))
        self.smart_play = False

    def plan(self, g):
        st = g.st
        ops = schedule.options(st)
        return [self.rnd.choice(ops) for _ in range(3)]

    def deck(self, st, ctx):
        return [self.rnd.below(4) for _ in range(5)]

    def play(self, st, ctx):
        return self.rnd.below(len(ctx['hand']))

    def pick_role(self, st, b, ok):
        return self.rnd.choice(ok) if self.rnd.chance(3, 5) else None

    def accept_support(self, st, role):
        return self.rnd.chance(1, 2)

    def go_personally(self, st, role):
        return self.rnd.chance(1, 2)

    def option(self, st, ev, avail):
        return self.rnd.choice(avail)

    def annual(self, st, opts):
        return self.rnd.choice([None] + [x['id'] for x in opts])

    def suppress(self, st, kind):
        return self.rnd.chance(1, 2)


BOTS = {c.name: c for c in (Hard, Lover, Culture, Wrist, Two, Crime, BookCulture, Random)}
PURE = ('only_tough', 'only_lover', 'only_culture', 'only_savvy')


# ---------- playing one game ----------
def play(cls, seed, data=None, smart_play=None, buy=None, on_month=None):
    """Plays one game and returns a record. Array indexes in the record = month index (the value after month end).
    on_month(g, date), if given, is called after each month with the date the month started (reconciliation uses it)."""
    bot = cls(seed)
    if smart_play is not None:
        bot.smart_play = smart_play
    if buy is not None:
        bot.buy = buy
    g = new_game(seed, bot.origin, bot, data)
    st, d = g.st, g.d
    rec = {'bot': cls.name, 'seed': seed, 'origin': bot.origin,
           'train': [], 'rep': [], 'money': [], 'fame': [], 'debt': 0}
    while not st.finished:
        date = st.date
        g.start_month()
        g.run_month(fit_plan(g, bot.plan(g)))
        rec['train'].append([sum(st.skill[s] for s in d.road_skills[r]) for r in d.roads])
        b = st.bonus()
        rec['rep'].append([st.rep(r, b) for r in d.roads])
        rec['money'].append(st.money)
        rec['fame'].append(st.attr['fame'])
        rec['debt'] += st.money < 0
        if on_month:
            on_month(g, date)
    rec.update(summarize(g))
    return rec


def summarize(g):
    st, d = g.st, g.d
    res = st.story['ending']
    c = st.count
    rec = {'ending': res['ending'], 'category': res.get('category'), 'grade': res.get('grade'), 'total': res.get('total'),
           'months_played': len(g.hooks.boards) and st.ym,
           'fame_end': st.attr['fame'], 'fame_tier': st.fame_tier(),
           'max_rep': rules.get_var(st, 'max_rep')}
    for k in ('count.audition', 'count.audition_won', 'count.audition.big', 'count.audition.medium', 'count.audition.small',
              'count.audition_won.big', 'count.audition_won.medium', 'count.audition_won.small', 'count.release', 'count.hit',
              'count.flop', 'count.support', 'count.breach', 'count.lead.big', 'count.lead.medium', 'count.lead.small',
              'count.arrest', 'count.scandal', 'count.opportunity'):
        rec[k] = c.get(k, 0)
    # The reputation bonus from annual events is subtracted when computing "full training plus plain releases"
    ann = {r: 0 for r in d.roads}
    rw = {x['rank']: x['rep_bonus'] for x in d.t['annual']['ranking']['rewards']}
    occ = {x['id']: x['road'] for x in d.t['annual']['occasions']}
    for a in g.hooks.annuals:
        if a.get('occasions') and a.get('rank') in rw:
            ann[occ[a['occasions']]] += rw[a['rank']]
    b = st.bonus()
    rec['no_annual_rep'] = max(st.rep(r, b) - ann[r] for r in d.roads)
    rec['annual_bonus'] = sum(ann.values())
    # Breakdown of the main road's (the road with the highest final reputation) reputation: training value / gear and stamina bonus / releases / annual / the rest (opportunities, events)
    top = max(d.roads, key=lambda r: st.rep(r, b))
    tr = sum(st.skill[s] for s in d.road_skills[top])
    rel = sum(f['result']['rep_bonus'] for f in st.story['films'] if f.get('result') and f['roles']['road'] == top)
    rec['breakdown'] = {'training': tr, 'gear': sum(st.val(s, b) for s in d.road_skills[top]) - tr, 'release': rel,
                'annual': ann[top], 'opportunity': st.corr[top] - rel - ann[top]}
    rec['plain_rep'] = tr + rec['breakdown']['gear'] + rel       # "Full training plus plain releases" (gear included)
    rec['gear_buy'] = c.get('count.gear_spend', 0)
    rec['fee'] = sum(f.get('fee', 0) for f in st.story['films'] if f.get('result'))
    rec['annual_rank'] = [a.get('rank') for a in g.hooks.annuals]
    return rec
