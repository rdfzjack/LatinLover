"""Interpreter for conditions, effects, checks and probabilities. Syntax: data/new/README.md, GDD 11.0 and 16."""
import re

EFF = re.compile(r'^([^+\-=]+)([+\-=])(\d+)(%?)$')
_cache = {}


def tdiv(a, b):
    """Integer division truncating toward zero (GDD 0)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def split_name(name):
    """'favor.sil' -> ('favor', 'sil'); a name without a prefix gives ('name', '')."""
    head, _, rest = name.partition('.')
    return head, rest


# ---------- effects ----------
def parse_effect(text):
    """'stamina+20 discipline-15 trigger.evt_x' -> [(name, sign, number, is_percent)];
    a trigger is returned as ('trigger', 'evt_x', 0, '')."""
    if text in _cache:
        return _cache[text]
    out = []
    for tok in (text or '').split():
        head, rest = split_name(tok)
        if head == 'trigger' and rest:
            out.append(('trigger', rest, 0, ''))
            continue
        m = EFF.match(tok)
        if not m:
            raise ValueError(f'bad effect term: {tok}')
        out.append((m.group(1), m.group(2), int(m.group(3)), m.group(4)))
    _cache[text] = out
    return out


def _delta(cur, op, n, pct):
    """Returns the new value. A percentage is taken of the current value, truncating toward zero."""
    if op == '=':
        return n
    v = tdiv(cur * n, 100) if pct else n
    return cur + v if op == '+' else cur - v


def apply_effect(st, text, source='event'):
    """Applies one effect line and returns the ids of the events to trigger next.
    source 'event' (events, opportunities, item use ...): a positive favor gain is +1 more when loyalty >= 200
    (GDD 10.1); 'schedule' (fixed per-period or per-period favor in schedules) and 'origin' do not get the bonus."""
    trig = []
    d = st.d
    for n, op, v, pct in parse_effect(text):
        head, k = split_name(n)
        if n == 'trigger':
            trig.append(op)
        elif n in st.attr:
            lo, hi = d.attr_range[n]
            st.attr[n] = max(lo, min(hi, _delta(st.attr[n], op, v, pct)))
        elif n in st.skill:
            lo, hi = d.skill_range[n]
            st.skill[n] = max(lo, min(hi, _delta(st.skill[n], op, v, pct)))
        elif n == 'money':
            st.money = min(_delta(st.money, op, v, pct), d.money_cap)
        elif n == 'drug_stage':
            st.drug = max(0, min(3, _delta(st.drug, op, v, pct)))
        elif n == 'debt_months':
            st.debt_months = max(0, _delta(st.debt_months, op, v, pct))
        elif head == 'favor':
            cur = st.favor.get(k, 0)
            new = _delta(cur, op, v, pct)
            if source == 'event' and new > cur and st.val('loyalty') >= 200:
                new += 1
            st.favor[k] = max(0, min(100, new))
        elif head == 'rep_bonus':
            st.corr[k] = _delta(st.corr[k], op, v, pct)
        elif head == 'weight':
            st.weights[k] = _delta(st.weights.get(k, 0), op, v, pct)
        elif head == 'item':
            if op == '=' and v == 0:
                remove_item(st, k)
            else:
                st.items.append(k)
        elif head == 'status':
            new = _delta(st.status.get(k, 0), op, v, pct)
            if k == 'in_love' and new and not st.status.get('in_love'):
                st.romance_months = 0
            st.status[k] = new
        elif head == 'flag':
            st.flags[k] = _delta(st.flags.get(k, 0), op, v, pct)
        else:
            raise KeyError(f'unknown effect name: {n}')
    return trig


def remove_item(st, iid):
    if iid not in st.items:
        return False
    st.items.remove(iid)
    if iid not in st.items:
        if st.equip['outfit'] == iid:
            st.equip['outfit'] = None
        if iid in st.equip['accessory']:
            st.equip['accessory'].remove(iid)
    return True


# ---------- variables ----------
EXTRA_VARS = {}   # step 6: derived values for the endings (grade, top tag family ...): name -> fn(st)


def get_var(st, name):
    d = st.d
    if name in st.attr or name in st.skill:
        return st.val(name)
    if name in st.corr:
        return st.rep(name)
    if name == 'money':
        return st.money
    if name in st.idx:
        return st.idx[name]
    if name == 'date':
        return st.date
    if name == 'month':
        return int(st.date[5:])
    if name == 'year':
        return int(st.date[:4])
    if name == 'max_rep':
        b = st.bonus()
        return max(st.rep(r, b) for r in d.roads)
    if name == 'top_road':
        b = st.bonus()
        return max(d.roads, key=lambda r: (st.rep(r, b), -d.roads.index(r)))
    if name == 'rep_spread':
        b = st.bonus()
        v = [st.rep(r, b) for r in d.roads]
        return max(v) - min(v)
    if name == 'drug_stage':
        return st.drug
    if name == 'debt_months':
        return st.debt_months
    if name == 'top_base_attr':
        return st.highest_base()
    if name == 'top_savvy_skill':
        b = st.bonus()
        sk = d.road_skills['savvy']
        return max(sk, key=lambda s: (st.val(s, b), -sk.index(s)))
    if name == 'max_job_periods':
        return max([st.cnt('job_periods.' + j) for j in d.jobs] or [0])
    if name == 'talkie_count':
        return st.cnt('count.talkie_count')
    head, k = split_name(name)
    if head == 'favor':
        return st.favor.get(k, 0)
    if head == 'flag':
        return st.flags.get(k, 0)
    if head == 'status':
        if k == 'wrap_up':
            return 1 if st.month.get('wrap_up') else 0
        return st.status.get(k, 0)
    if head == 'tag':
        return st.tags.get(k, 0)
    if head in ('job_periods', 'class_periods', 'road_periods', 'count', 'duels'):
        return st.cnt(name)
    if name in EXTRA_VARS:
        return EXTRA_VARS[name](st)
    raise KeyError(f'condition variable unknown or not implemented: {name}')


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
    """[[term, ...], ...]: outer list is OR, inner list is AND; [] is always true."""
    if not c:
        return True
    return any(all(test(st, t) for t in g) for g in c)


# ---------- checks (GDD 11.0) ----------
def check(st, c):
    """A gate [variable, comparator, value], or a dice check {check: skill, line: n}
    (displayed skill value + r0(20) >= n). None always succeeds."""
    if c is None:
        return True
    if isinstance(c, dict):
        return st.val(c['check']) + st.rng.logic.r0(20) >= c['line']
    return test(st, c)


# ---------- probabilities ----------
def prob(st, p):
    """null always; [numerator, denominator]; tiered list [{cond, value}] takes the first that holds;
    {numerator: variable, denominator: n, max: [p, q]}."""
    g = st.rng.logic
    if p is None:
        return True
    if isinstance(p, dict):
        num, den = get_var(st, p['numerator']), p['denominator']
        cp, cq = p['max']
        # min(num/den, cp/cq) over the common denominator den*cq
        return g.chance(min(num * cq, cp * den), den * cq)
    if p and isinstance(p[0], dict):
        for x in p:
            if cond(st, x['cond']):
                return g.chance(*x['value'])
        return False
    return g.chance(p[0], p[1])
