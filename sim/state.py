"""The whole state of one game, plus the derived values: displayed values, reputation, fame tier.

A save is the JSON of to_dict(): both random streams, all counters, flags, the table of fired events, the points left in each book (GDD 16).
"""
import json

from .rng import Rng
from . import rules


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


STATUS_KEYS = ['sick', 'very_sick', 'reckless', 'in_love', 'long_contract', 'shooting_period', 'shoot_this_month', 'has_pending_role']


def new_story():
    """The state of step 6, all directly storable in JSON.
        board: the current board (board.py); films: all film contracts (film.py); boarded: role id -> times on a board;
        pending_board: roles added to the next board; tipoff: number of roles whose style the next board reveals; last_fired: event id -> month index of the last firing;
        script: last year of self_written / duv_written, whether co_written was used; contract_refused: month index of the last refusal;
        transition: remaining boards and the tag family; seq: running number for generated roles and film contracts; ending: result of the ending resolution."""
    return {'board': None, 'films': [], 'boarded': {}, 'pending_board': [], 'tipoff': 0, 'last_fired': {},
            'script': {'self_written': 0, 'duv_written': 0, 'co_written': 0}, 'contract_refused': -99, 'transition': [0, None],
            'scandal_cover_year': 0, 'leak_year': 0, 'seq': 0, 'ending': None}


class State:
    def __init__(self, data):
        self.d = data
        self.rng = Rng(0)
        self.ym = 0                       # month index, 0 = 1926-01
        self.attr = dict(data.attr_init)  # base attributes (base values, gear not included)
        self.skill = dict(data.skill_init)  # skill training values
        self.money = data.money_init
        self.corr = {r: 0 for r in data.roads}      # reputation bonus values
        self.favor = {n: v['favor_init'] for n, v in data.npcs.items()}
        self.known = sorted(n for n, v in data.npcs.items() if v.get('known_at_start'))
        self.flags = {}                   # flags: name -> integer (mostly 0/1; accent_period style ones count down)
        self.count = {}                   # counters: class_periods.<class> job_periods.<job> road_periods.<road> count.<name> ...
        self.tags = {}                    # film tag counts
        self.weights = {}                 # board weights (weight.<tag>, used in step 6)
        self.books = {}                   # books held and not finished: id -> points left
        self.read_books = []              # books already read (can be sold at half price)
        self.items = []                   # ids of held items (may repeat)
        self.equip = {'outfit': None, 'accessory': []}
        self.lifestyle = 'life_normal'
        self.idx = {'sick_index': 0, 'reckless_index': 0}   # computed at month end, kept for the whole month
        self.status = {k: 0 for k in STATUS_KEYS}
        self.romance_months = 0
        self.debt_months = 0
        self.drug = 0
        self.collapse_months = 0          # months in a row with sick_index = 100
        self.forced_rest = 0              # 1 = the sanatorium is forced next month (very sick)
        self.void_next = 0                # 1 = next month's schedule is void (missing, set by a step-6 event)
        self.exposed = 0                  # whether there was exposure this month
        self.month_used = {}              # limited services already used this month
        self.fired = {}                   # fired events: id -> times (used in step 6)
        self.ended = None                 # ending id; a forced mid-game ending is written here too
        self.finished = 0                 # 1 after the 1929-12 month settlement
        self.story = new_story()          # step 6: board, film contracts, event records, ending (see new_story)
        self.log = []                     # for debugging, not saved

    # ---------- origin ----------
    @classmethod
    def new(cls, data, seed, origin=(0, 0, 0)):
        """origin: which option was picked for each opening question (counting from 0)."""
        st = cls(data)
        st.rng = Rng(seed)
        for q, i in zip(data.origins, origin):
            o = q['options'][i]
            if o['effect']:
                rules.apply_effect(st, o['effect'], source='origin')
            for t, n in o['tag_counts'].items():
                st.tags[t] = st.tags.get(t, 0) + n
            for f in o['flags']:
                st.flags[f] = 1
            for it in o['items']:
                st.items.append(it)
        st.update_indices()
        return st

    # ---------- calendar ----------
    @property
    def month(self):
        return self.d.months[self.ym]

    @property
    def date(self):
        return self.d.months[min(self.ym, len(self.d.months) - 1)]['month']

    # ---------- counters ----------
    def cnt(self, k):
        return self.count.get(k, 0)

    def inc(self, k, n=1):
        self.count[k] = self.count.get(k, 0) + n

    # ---------- gear bonus ----------
    def _held(self):
        """Held items that take effect by being held: within one exclusive group only the highest price counts; several copies of one item count once."""
        best, out = {}, []
        for iid in sorted(set(self.items), key=self.d.item_order.get):          # table order
            it = self.d.items[iid]
            if it['class'] != 'held':
                continue
            g = it.get('exclusive_group')
            if g is None:
                out.append(iid)
            elif g not in best or it['price'] > self.d.items[best[g]]['price']:
                best[g] = iid
        return out + list(best.values())

    def bonus(self):
        """Bonus from gear and held items: {attribute or skill: value}.
                Outfits follow GDD 14.1: outfit value x (50 + grooming)/100, truncated toward zero; grooming here is the training value plus the non-outfit bonus."""
        b = {}
        plain = self._held() + list(self.equip['accessory'])
        for iid in plain:
            for n, op, v, pct in rules.parse_effect(self.d.items[iid]['effect']):
                if op in '+-' and not pct:
                    b[n] = b.get(n, 0) + (v if op == '+' else -v)
        cl = self.equip['outfit']
        if cl:
            dress = self.skill['grooming'] + b.get('grooming', 0)
            f = 50 + dress
            for n, op, v, pct in rules.parse_effect(self.d.items[cl]['effect']):
                if op in '+-' and not pct:
                    b[n] = b.get(n, 0) + rules.tdiv((v if op == '+' else -v) * f, 100)
        return b

    # ---------- displayed values ----------
    def val(self, name, b=None):
        """Displayed value of an attribute or skill. Conditions, success lines and checks all use it."""
        if b is None:
            b = self.bonus()
        if name in self.attr:
            lo, hi = self.d.attr_range[name]
            return clamp(self.attr[name] + b.get(name, 0), lo, hi)
        if name in self.skill:
            v = self.skill[name] + b.get(name, 0)
            sb = self.d.skill_bonus.get(name)
            if sb:
                v += min(self.val(sb['attr'], b) // sb['div'], sb['max'])
            return max(0, v)
        raise KeyError(name)

    def rep(self, road, b=None):
        if b is None:
            b = self.bonus()
        v = sum(self.val(s, b) for s in self.d.road_skills[road]) + self.corr[road]
        return clamp(v, *self.d.rep_range)

    def level(self, road):
        r, L = self.rep(road), 0
        for i, g in enumerate(self.d.level_gate):
            if r >= g:
                L = i
        return L

    def fame_tier(self):
        f = self.attr['fame']
        for i, (lo, hi) in enumerate(self.d.fame_tiers):
            if lo <= f <= hi:
                return i
        return len(self.d.fame_tiers) - 1

    def highest_base(self):
        """Highest base attribute (GDD 10): the highest of stamina, education, loyalty, looks, discipline and crime; ties go to the earlier one."""
        b = self.bonus()
        names = ['stamina', 'education', 'loyalty', 'looks', 'discipline', 'crime']
        return max(names, key=lambda n: (self.val(n, b), -names.index(n)))

    # ---------- indices ----------
    def calc_indices(self):
        b = self.bonus()
        tired = self.val('fatigue', b)
        sick = clamp(tired - self.val('stamina', b), 0, 100)
        wild = clamp(tired - self.val('discipline', b), 0, 100)
        return sick, wild

    def update_indices(self):
        """Computes the two indices at month end and updates the status (GDD 10). The result is kept for the whole month."""
        sick, wild = self.calc_indices()
        r = self.d.idx_rule
        self.idx['sick_index'], self.idx['reckless_index'] = sick, wild
        self.status['sick'] = int(sick >= r['sick_index']['status_line'])
        self.status['very_sick'] = int(sick >= r['sick_index']['very_sick_line'])
        self.status['reckless'] = int(wild >= r['reckless_index']['status_line'])

    # ---------- money ----------
    def add_money(self, n):
        self.money = min(self.money + n, self.d.money_cap)

    # ---------- save ----------
    SAVE_VERSION = 2          # 2: English ids and keys (step 9c-1); older saves are not readable
    SAVE_KEYS = ['ym', 'attr', 'skill', 'money', 'corr', 'favor', 'known', 'flags', 'count', 'tags', 'weights',
                 'books', 'read_books', 'items', 'equip', 'lifestyle', 'idx', 'status', 'romance_months',
                 'debt_months', 'drug', 'collapse_months', 'forced_rest', 'void_next', 'exposed',
                 'month_used', 'fired', 'ended', 'finished', 'story']

    def to_dict(self):
        out = {'version': self.SAVE_VERSION, 'rng': self.rng.dump()}
        for k in self.SAVE_KEYS:
            out[k] = getattr(self, k)
        return json.loads(json.dumps(out, ensure_ascii=False, sort_keys=True))

    def dumps(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(',', ':'))

    @classmethod
    def from_dict(cls, data, d):
        if d.get('version') != cls.SAVE_VERSION:
            raise ValueError(f"unsupported save version {d.get('version')}, expected {cls.SAVE_VERSION}")
        st = cls(data)
        st.rng = Rng.load(d['rng'])
        for k in cls.SAVE_KEYS:
            setattr(st, k, json.loads(json.dumps(d[k] if k in d else getattr(st, k))))
        return st

    @classmethod
    def loads(cls, data, s):
        return cls.from_dict(data, json.loads(s))
