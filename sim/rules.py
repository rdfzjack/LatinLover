"""条件、效果、判定、概率的解释器。语法见 data/new/README.md，GDD 11.0、16。"""
import re

EFF = re.compile(r'^([^+\-=]+)([+\-=])(\d+)(%?)$')
_cache = {}


def tdiv(a, b):
    """向零截断的整数除法（GDD 0）。"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


# ---------- 效果 ----------
def parse_effect(text):
    """'体力+20 自律-15 触发.evt_x' -> [(名字, 符号, 数, 是否百分比)]；触发写成 ('触发', 'evt_x', 0, '')。"""
    if text in _cache:
        return _cache[text]
    out = []
    for tok in (text or '').split():
        if tok.startswith('触发.'):
            out.append(('触发', tok[3:], 0, ''))
            continue
        m = EFF.match(tok)
        if not m:
            raise ValueError(f'效果项格式错误：{tok}')
        out.append((m.group(1), m.group(2), int(m.group(3)), m.group(4)))
    _cache[text] = out
    return out


def _delta(cur, op, n, pct):
    """返回新值。百分比按当前值算，向零截断。"""
    if op == '=':
        return n
    v = tdiv(cur * n, 100) if pct else n
    return cur + v if op == '+' else cur - v


def apply_effect(st, text, source='event'):
    """执行一行效果，返回要接着触发的事件 id 列表。
    source：'event'（事件、机遇、物品使用等）时，好感正增量在义气 ≥200 时多 1（GDD 10.1）；
    'schedule'（日程里每旬、每期固定的好感）和 'origin' 不加。"""
    trig = []
    d = st.d
    for n, op, v, pct in parse_effect(text):
        if n == '触发':
            trig.append(op)
        elif n in st.attr:
            lo, hi = d.attr_range[n]
            st.attr[n] = max(lo, min(hi, _delta(st.attr[n], op, v, pct)))
        elif n in st.skill:
            lo, hi = d.skill_range[n]
            st.skill[n] = max(lo, min(hi, _delta(st.skill[n], op, v, pct)))
        elif n == '金钱':
            st.money = min(_delta(st.money, op, v, pct), d.money_cap)
        elif n == '药瘾阶段':
            st.drug = max(0, min(3, _delta(st.drug, op, v, pct)))
        elif n == '负债月数':
            st.debt_months = max(0, _delta(st.debt_months, op, v, pct))
        elif n == '股票':
            st.stock = max(0, _delta(st.stock, op, v, pct))
        elif n.startswith('好感.'):
            k = n[3:]
            cur = st.favor.get(k, 0)
            new = _delta(cur, op, v, pct)
            if source == 'event' and new > cur and st.val('义气') >= 200:
                new += 1
            st.favor[k] = max(0, min(100, new))
        elif n.startswith('修正.'):
            k = n[3:]
            st.corr[k] = _delta(st.corr[k], op, v, pct)
        elif n.startswith('权重.'):
            k = n[3:]
            st.weights[k] = _delta(st.weights.get(k, 0), op, v, pct)
        elif n.startswith('物品.'):
            k = n[3:]
            if op == '=' and v == 0:
                remove_item(st, k)
            else:
                st.items.append(k)
        elif n.startswith('状态.'):
            k = n[3:]
            new = _delta(st.status.get(k, 0), op, v, pct)
            if k == '恋爱' and new and not st.status.get('恋爱'):
                st.romance_months = 0
            st.status[k] = new
        elif n.startswith('旗标.'):
            k = n[3:]
            st.flags[k] = _delta(st.flags.get(k, 0), op, v, pct)
        else:
            raise KeyError(f'效果名字未知：{n}')
    return trig


def remove_item(st, iid):
    if iid not in st.items:
        return False
    st.items.remove(iid)
    if iid not in st.items:
        if st.equip['服装'] == iid:
            st.equip['服装'] = None
        if iid in st.equip['配饰']:
            st.equip['配饰'].remove(iid)
    return True


# ---------- 变量 ----------
EXTRA_VARS = {}   # 第 6 步登记结局用的派生值（档次、最大标签族…）：名字 -> fn(st)


def get_var(st, name):
    d = st.d
    if name in st.attr or name in st.skill:
        return st.val(name)
    if name in st.corr:
        return st.rep(name)
    if name == '金钱':
        return st.money
    if name in st.idx:
        return st.idx[name]
    if name == '日期':
        return st.date
    if name == '月份':
        return int(st.date[5:])
    if name == '年份':
        return int(st.date[:4])
    if name == '最高声望':
        b = st.bonus()
        return max(st.rep(r, b) for r in d.roads)
    if name == '最高声望所在路':
        b = st.bonus()
        return max(d.roads, key=lambda r: (st.rep(r, b), -d.roads.index(r)))
    if name == '四路声望极差':
        b = st.bonus()
        v = [st.rep(r, b) for r in d.roads]
        return max(v) - min(v)
    if name == '药瘾阶段':
        return st.drug
    if name == '负债月数':
        return st.debt_months
    if name == '股票':
        return st.stock
    if name == '最高基础属性':
        return st.highest_base()
    if name == '手腕最高技能':
        b = st.bonus()
        sk = d.road_skills['手腕']
        return max(sk, key=lambda s: (st.val(s, b), -sk.index(s)))
    if name == '最大工期数':
        return max([st.cnt('成功期数.' + j) for j in d.jobs] or [0])
    if name == '有声片部数':
        return st.cnt('计数.有声片部数')
    if name.startswith('好感.'):
        return st.favor.get(name[3:], 0)
    if name.startswith('旗标.'):
        return st.flags.get(name[3:], 0)
    if name.startswith('状态.'):
        k = name[3:]
        if k == '收尾期':
            return 1 if st.month.get('收尾期') else 0
        return st.status.get(k, 0)
    if name.startswith('标签.'):
        return st.tags.get(name[3:], 0)
    if name.startswith(('成功期数.', '旬数.', '期数.', '计数.', '交手次数.')):
        return st.cnt(name)
    if name in EXTRA_VARS:
        return EXTRA_VARS[name](st)
    raise KeyError(f'条件变量未知或还没实现：{name}')


def _cmp(a, op, b):
    if op == '>=': return a >= b
    if op == '<=': return a <= b
    if op == '>': return a > b
    if op == '<': return a < b
    if op == '==': return a == b
    if op == '!=': return a != b
    if op == 'in': return a in b
    raise ValueError(op)


def test(st, term):
    var, op, val = term
    a = get_var(st, var)
    if isinstance(val, str) and val.startswith('@'):
        val = get_var(st, val[1:])
    return _cmp(a, op, val)


def cond(st, c):
    """[[项,…],…]：外层或、组内与；[] 恒真。"""
    if not c:
        return True
    return any(all(test(st, t) for t in g) for g in c)


# ---------- 判定（GDD 11.0） ----------
def check(st, c):
    """门槛 [变量, 比较符, 值]，或掷骰 {判定: 技能, 线: n}（技能显示值 + r0(20) >= n）。None 为必然成功。"""
    if c is None:
        return True
    if isinstance(c, dict):
        return st.val(c['判定']) + st.rng.logic.r0(20) >= c['线']
    return test(st, c)


# ---------- 概率 ----------
def prob(st, p):
    """null 必然；[分子,分母]；分档 [{条件,值}] 取第一个满足的；{分子:变量,分母:n,上限:[p,q]}。"""
    g = st.rng.logic
    if p is None:
        return True
    if isinstance(p, dict):
        num, den = get_var(st, p['分子']), p['分母']
        cp, cq = p['上限']
        # min(num/den, cp/cq) 化成同分母 den*cq
        return g.chance(min(num * cq, cp * den), den * cq)
    if p and isinstance(p[0], dict):
        for x in p:
            if cond(st, x['条件']):
                return g.chance(*x['值'])
        return False
    return g.chance(p[0], p[1])
