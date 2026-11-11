"""Loads data/new/*.json and builds id lookup indexes. Read-only: never modifies the tables."""
import json
import os

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'new')
TABLES = ['stats', 'skills', 'classes', 'books', 'jobs', 'rest', 'places', 'lifestyle', 'street',
          'origins', 'calendar', 'habits', 'rivals', 'roles', 'items', 'events', 'outing', 'romance',
          'npc_schedule', 'npc_chains', 'annual', 'opportunities', 'endings']


class Data:
    def __init__(self, path=DEFAULT_DIR):
        self.t = {}
        for n in TABLES:
            with open(os.path.join(path, n + '.json'), encoding='utf-8') as fh:
                self.t[n] = json.load(fh)
        t = self.t
        st = t['stats']
        # Table order is the canonical order wherever a tie or an iteration order matters.
        self.attrs = [a['id'] for a in st['attrs']]
        self.attr_init = {a['id']: a['init'] for a in st['attrs']}
        self.attr_range = {a['id']: tuple(a['range']) for a in st['attrs']}
        self.money_init = st['money']['init']
        self.money_cap = st['money']['max']
        self.roads = [r['id'] for r in st['roads']]
        self.road_skills = {r['id']: r['skills'] for r in st['roads']}
        self.rep_range = tuple(st['rep_rules']['range'])
        self.level_gate = st['levels']['gate']
        self.fame_tiers = [(x['min'], x['max']) for x in st['fame_tiers']]
        self.idx_rule = st['indices']
        self.contract = st['contract']

        self.skills = [s['id'] for s in t['skills']['skills']]
        self.skill_init = {s['id']: s['init'] for s in t['skills']['skills']}
        self.skill_range = {s['id']: tuple(s['train_range']) for s in t['skills']['skills']}
        self.skill_road = {s['id']: s['road'] for s in t['skills']['skills']}
        self.skill_bonus = {s['id']: s['display_bonus'] for s in t['skills']['skills'] if 'display_bonus' in s}

        self.classes = {c['id']: c for c in t['classes']['classes']}
        self.class_steps = t['classes']['class_steps']
        self.books = {b['id']: b for b in t['books']['books']}
        self.jobs = {j['id']: j for j in t['jobs']['jobs']}
        self.job_rules = t['jobs']
        self.rests = {r['id']: r for r in t['rest']['rests']}
        self.rest_forced = t['rest']['forced']
        self.places = {p['id']: p for p in t['places']['places']}
        self.lifestyles = {x['id']: x for x in t['lifestyle']['lifestyles']}
        self.street = {e['id']: e for e in t['street']['entries']}
        self.discount = t['street']['discount']
        self.items = {i['id']: i for i in t['items']['items']}
        self.item_order = {iid: n for n, iid in enumerate(self.items)}      # table order, for stable iteration
        self.item_rules = t['items']['rules']
        self.months = t['calendar']['months']
        self.month_index = {m['month']: i for i, m in enumerate(self.months)}
        self.npcs = {n['id']: n for n in t['romance']['npcs']}
        self.npc_order = {n: i for i, n in enumerate(self.npcs)}      # table order, for stable sorting
        self.romance_lines = [n['id'] for n in t['romance']['npcs'] if n['class'] == 'romance']
        self.origins = t['origins']['questions']
        self.endings_forced = {e['id']: e for e in t['endings']['forced']}

        # step 6: board, shooting, release, events, endings
        self.roles = {r['id']: r for r in t['roles']['roles']}
        self.role_cfg = t['roles']['defaults']
        self.tag_families = t['endings']['tag_families']
        self.content_tags = [x for v in self.tag_families.values() for x in v]   # the 16 content tags
        self.rivals_named = {r['id']: r for r in t['rivals']['named']}
        self.events = {e['id']: e for e in t['events']['events']}
        self.events.update({e['id']: e for e in t['outing']['events']})
        self.opps = t['opportunities']['opportunities']
        self.chains = t['npc_chains']['chains']
        self.schedule_npc = t['npc_schedule']['schedule']

    def class_road(self, cid):
        """The road a class counts for in road_periods: the road of the first skill in its gain list
        (tutoring's first skill is writing, which counts for culture)."""
        for e in self.classes[cid]['gain']:
            if e['stat'] in self.skill_road:
                return self.skill_road[e['stat']]
        return None

    def job_roads(self, jid):
        """The roads a job counts for in road_periods: roads of the skills in its daily_effect, deduplicated,
        in road order."""
        rs = {self.skill_road[e['stat']] for e in self.jobs[jid]['daily_effect'] if e['stat'] in self.skill_road}
        return [r for r in self.roads if r in rs]


_cached = None


def load(path=None):
    global _cached
    if path:
        return Data(path)
    if _cached is None:
        _cached = Data()
    return _cached
