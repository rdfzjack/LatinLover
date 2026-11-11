"""一局的全部状态，以及显示值、声望、名气档这些派生值。

存档就是 to_dict() 的 JSON：两个随机流、所有计数器、旗标、已触发事件表、每本书的剩余点数（GDD 16）。
"""
import json

from .rng import Rng
from . import rules


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


STATUS_KEYS = ['生病', '重病', '失控', '恋爱', '长约', '拍摄旬', '当月有拍摄', '有未开拍角色']


class State:
    def __init__(self, data):
        self.d = data
        self.rng = Rng(0)
        self.ym = 0                       # 月序，0 = 1926-01
        self.attr = dict(data.attr_init)  # 基础属性（底值，不含装备）
        self.skill = dict(data.skill_init)  # 技能训练值
        self.money = data.money_init
        self.corr = {r: 0 for r in data.roads}      # 声望修正值
        self.favor = {n: v['好感初值'] for n, v in data.npcs.items()}
        self.known = sorted(n for n, v in data.npcs.items() if v.get('开局认识'))
        self.flags = {}                   # 旗标：名字 -> 整数（多数是 0/1，口音期这类是倒数）
        self.count = {}                   # 计数器：旬数.<课> 成功期数.<工> 期数.<路> 计数.<名> …
        self.tags = {}                    # 戏路标签计数
        self.weights = {}                 # 上板权重（权重.<标签>，第 6 步用）
        self.books = {}                   # 持有、未读完的书：id -> 剩余点数
        self.read_books = []              # 读过的书（可半价卖）
        self.items = []                   # 持有的物品 id（可重复）
        self.equip = {'服装': None, '配饰': []}
        self.lifestyle = 'life_normal'
        self.idx = {'生病指数': 0, '失控指数': 0}   # 月结时算，整月沿用
        self.status = {k: 0 for k in STATUS_KEYS}
        self.romance_months = 0
        self.debt_months = 0
        self.drug = 0
        self.stock = 0
        self.collapse_months = 0          # 生病指数 = 100 连续的月数
        self.forced_rest = 0              # 1 = 下月日程强制疗养院（重病）
        self.void_next = 0                # 1 = 下月日程作废（失踪，第 6 步的事件设）
        self.exposed = 0                  # 本月有没有曝光
        self.month_used = {}              # 本月已用的限次服务
        self.fired = {}                   # 已触发事件：id -> 次数（第 6 步用）
        self.ended = None                 # 结局 id；中途强制结局也写这里
        self.finished = 0                 # 1929-12 月结之后为 1
        self.log = []                     # 调试用，不进存档

    # ---------- 开局 ----------
    @classmethod
    def new(cls, data, seed, origin=(0, 0, 0)):
        """origin：开局三问各选第几项（从 0 数）。"""
        st = cls(data)
        st.rng = Rng(seed)
        for q, i in zip(data.origins, origin):
            o = q['选项'][i]
            if o['效果']:
                rules.apply_effect(st, o['效果'], source='origin')
            for t, n in o['标签计数'].items():
                st.tags[t] = st.tags.get(t, 0) + n
            for f in o['旗标']:
                st.flags[f] = 1
            for it in o['物品']:
                st.items.append(it)
        st.update_indices()
        return st

    # ---------- 日历 ----------
    @property
    def month(self):
        return self.d.months[self.ym]

    @property
    def date(self):
        return self.d.months[min(self.ym, len(self.d.months) - 1)]['月']

    # ---------- 计数器 ----------
    def cnt(self, k):
        return self.count.get(k, 0)

    def inc(self, k, n=1):
        self.count[k] = self.count.get(k, 0) + n

    # ---------- 装备加成 ----------
    def _held(self):
        """持有即生效的物品：同一互斥组只取价格最高的一件；同一件持有多个只算一次。"""
        best, out = {}, []
        for iid in sorted(set(self.items)):
            it = self.d.items[iid]
            if it['类'] != '持有':
                continue
            g = it.get('互斥组')
            if g is None:
                out.append(iid)
            elif g not in best or it['价格'] > self.d.items[best[g]]['价格']:
                best[g] = iid
        return out + [best[g] for g in sorted(best)]

    def bonus(self):
        """装备、持有物给的加成：{属性或技能: 值}。
        服装按 GDD 14.1：服装值 × (50 + 打扮)/100，向零截断；这里的打扮是训练值加非服装加成。"""
        b = {}
        plain = self._held() + list(self.equip['配饰'])
        for iid in plain:
            for n, op, v, pct in rules.parse_effect(self.d.items[iid]['效果']):
                if op in '+-' and not pct:
                    b[n] = b.get(n, 0) + (v if op == '+' else -v)
        cl = self.equip['服装']
        if cl:
            dress = self.skill['打扮'] + b.get('打扮', 0)
            f = 50 + dress
            for n, op, v, pct in rules.parse_effect(self.d.items[cl]['效果']):
                if op in '+-' and not pct:
                    b[n] = b.get(n, 0) + rules.tdiv((v if op == '+' else -v) * f, 100)
        return b

    # ---------- 显示值 ----------
    def val(self, name, b=None):
        """属性或技能的显示值。条件、成功线、判定都用它。"""
        if b is None:
            b = self.bonus()
        if name in self.attr:
            lo, hi = self.d.attr_range[name]
            return clamp(self.attr[name] + b.get(name, 0), lo, hi)
        if name in self.skill:
            v = self.skill[name] + b.get(name, 0)
            sb = self.d.skill_bonus.get(name)
            if sb:
                v += min(self.val(sb['属性'], b) // sb['除'], sb['上限'])
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
        f = self.attr['名气']
        for i, (lo, hi) in enumerate(self.d.fame_tiers):
            if lo <= f <= hi:
                return i
        return len(self.d.fame_tiers) - 1

    def highest_base(self):
        """最高基础属性（GDD 10）：体力、教育、义气、相貌、自律、犯罪里最高的；并列取靠前的。"""
        b = self.bonus()
        names = ['体力', '教育', '义气', '相貌', '自律', '犯罪']
        return max(names, key=lambda n: (self.val(n, b), -names.index(n)))

    # ---------- 指数 ----------
    def calc_indices(self):
        b = self.bonus()
        tired = self.val('疲劳', b)
        sick = clamp(tired - self.val('体力', b), 0, 100)
        wild = clamp(tired - self.val('自律', b), 0, 100)
        return sick, wild

    def update_indices(self):
        """月结时算两个指数并更新状态（GDD 10）。整月沿用这次的结果。"""
        sick, wild = self.calc_indices()
        r = self.d.idx_rule
        self.idx['生病指数'], self.idx['失控指数'] = sick, wild
        self.status['生病'] = int(sick >= r['生病指数']['状态线'])
        self.status['重病'] = int(sick >= r['生病指数']['重病线'])
        self.status['失控'] = int(wild >= r['失控指数']['状态线'])

    # ---------- 金钱 ----------
    def add_money(self, n):
        self.money = min(self.money + n, self.d.money_cap)

    # ---------- 存档 ----------
    SAVE_KEYS = ['ym', 'attr', 'skill', 'money', 'corr', 'favor', 'known', 'flags', 'count', 'tags', 'weights',
                 'books', 'read_books', 'items', 'equip', 'lifestyle', 'idx', 'status', 'romance_months',
                 'debt_months', 'drug', 'stock', 'collapse_months', 'forced_rest', 'void_next', 'exposed',
                 'month_used', 'fired', 'ended', 'finished']

    def to_dict(self):
        out = {'版本': 1, 'rng': self.rng.dump()}
        for k in self.SAVE_KEYS:
            out[k] = getattr(self, k)
        return json.loads(json.dumps(out, ensure_ascii=False, sort_keys=True))

    def dumps(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(',', ':'))

    @classmethod
    def from_dict(cls, data, d):
        st = cls(data)
        st.rng = Rng.load(d['rng'])
        for k in cls.SAVE_KEYS:
            setattr(st, k, json.loads(json.dumps(d[k])))
        return st

    @classmethod
    def loads(cls, data, s):
        return cls.from_dict(data, json.loads(s))
