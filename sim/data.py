"""读 data/new/*.json，建好按 id 查找的索引。只读，不改表。"""
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
        self.attrs = [a['名字'] for a in st['基础属性']]
        self.attr_init = {a['名字']: a['初值'] for a in st['基础属性']}
        self.attr_range = {a['名字']: tuple(a['范围']) for a in st['基础属性']}
        self.money_init = st['金钱']['初值']
        self.money_cap = st['金钱']['上限']
        self.roads = [r['名字'] for r in st['声望']]
        self.road_skills = {r['名字']: r['技能'] for r in st['声望']}
        self.rep_range = tuple(st['声望规则']['范围'])
        self.level_gate = st['等级']['门槛']
        self.fame_tiers = [(x['下限'], x['上限']) for x in st['名气档']]
        self.idx_rule = st['指数']
        self.contract = st['合同']

        self.skills = [s['名字'] for s in t['skills']['技能']]
        self.skill_init = {s['名字']: s['初值'] for s in t['skills']['技能']}
        self.skill_range = {s['名字']: tuple(s['训练范围']) for s in t['skills']['技能']}
        self.skill_road = {s['名字']: s['路'] for s in t['skills']['技能']}
        self.skill_bonus = {s['名字']: s['显示加成'] for s in t['skills']['技能'] if '显示加成' in s}

        self.classes = {c['id']: c for c in t['classes']['课']}
        self.class_steps = t['classes']['等级门槛']
        self.books = {b['id']: b for b in t['books']['书']}
        self.jobs = {j['id']: j for j in t['jobs']['工']}
        self.job_rules = t['jobs']
        self.rests = {r['id']: r for r in t['rest']['休息']}
        self.rest_forced = t['rest']['强制']
        self.places = {p['id']: p for p in t['places']['地点']}
        self.lifestyles = {x['id']: x for x in t['lifestyle']['生活方式']}
        self.street = {e['名字']: e for e in t['street']['入口']}
        self.discount = t['street']['折扣']
        self.items = {i['id']: i for i in t['items']['物品']}
        self.item_rules = t['items']['规则']
        self.months = t['calendar']['月']
        self.month_index = {m['月']: i for i, m in enumerate(self.months)}
        self.npcs = {n['名字']: n for n in t['romance']['npc']}
        self.romance_lines = [n['名字'] for n in t['romance']['npc'] if n['类'] == '感情线']
        self.origins = t['origins']['问']
        self.endings_forced = {e['id']: e for e in t['endings']['强制']}

        # 第 6 步：选片板、拍摄、上映、事件、结局
        self.roles = {r['id']: r for r in t['roles']['角色']}
        self.role_cfg = t['roles']['默认']
        self.tag_families = t['endings']['标签族']
        self.content_tags = [x for v in self.tag_families.values() for x in v]   # 16 个内容标签
        self.rivals_named = {r['id']: r for r in t['rivals']['有名']}
        self.events = {e['id']: e for e in t['events']['事件']}
        self.events.update({e['id']: e for e in t['outing']['事件']})
        self.opps = t['opportunities']['机遇']
        self.chains = t['npc_chains']['链']
        self.schedule_npc = t['npc_schedule']['日程']

    def class_road(self, cid):
        """一门课算哪条路的“期数”：收益里第一个技能所在的路（家教的第一个技能是创作，算文化）。"""
        for e in self.classes[cid]['收益']:
            if e['项'] in self.skill_road:
                return self.skill_road[e['项']]
        return None

    def job_roads(self, jid):
        """一种工算哪几条路的“期数”：每天效果里出现的技能所在的路，去重，按路的顺序。"""
        rs = {self.skill_road[e['项']] for e in self.jobs[jid]['每天效果'] if e['项'] in self.skill_road}
        return [r for r in self.roads if r in rs]


_cached = None


def load(path=None):
    global _cached
    if path:
        return Data(path)
    if _cached is None:
        _cached = Data()
    return _cached
