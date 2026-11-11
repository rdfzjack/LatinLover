"""结局判定（GDD 15）：强制 → 特殊 → 大类 → 档次 → 结局表 → 品性 → 归宿 → 评语和总分。数据在 endings.json。

这里登记结局条件要用的派生变量（rules.EXTRA_VARS）：档次、最大标签族、无法定义、低成本定型。
"""
from . import film, rules


def tier(st):
    lines = st.d.t['endings']['档次线']
    v = rules.get_var(st, '最高声望')
    for k in ('S', 'A', 'B', 'C'):
        if v >= lines[k]:
            return k
    return 'D'


def biggest_family(st):
    """计数之和最大的标签族；并列按表的顺序；全是 0 时为 None。"""
    best, bv = None, 0
    for name, tags in st.d.tag_families.items():
        v = sum(st.tags.get(t, 0) for t in tags)
        if v > bv:
            best, bv = name, v
    return best


rules.EXTRA_VARS.update({
    '档次': tier,
    '最大标签族': biggest_family,
    '无法定义': film.undefined,
    '低成本定型': film.low_budget,
})


def most_job(st):
    """成功期数最多的工（并列取表里靠前的），没有打过工为 None。"""
    best, bv = None, 0
    for j in st.d.jobs:
        v = st.cnt('成功期数.' + j)
        if v > bv:
            best, bv = j, v
    return best


def most_class(st):
    """上得最多的课（看书算一门，记作 'book'），按旬数；并列取靠前的。"""
    best, bv = None, 0
    for c in st.d.classes:
        v = st.cnt('旬数.' + c)
        if v > bv:
            best, bv = c, v
    if st.cnt('计数.看书旬数') > bv:
        best = 'book'
    return best


def career(st):
    """事业结局：返回 (结局 id, 大类)。强制结局（倒下）在游戏中途已经写进 st.ended。"""
    t = st.d.t['endings']
    for e in t['特殊']:
        if rules.cond(st, e['条件']):
            return e['id'], '特殊'
    for c in t['大类']:
        if rules.cond(st, c['条件']):
            big = c['名字']
            break
    lst = sorted((e for e in t['结局'] if e['大类'] == big), key=lambda e: e['顺序'])
    for e in lst:
        if rules.cond(st, e['条件']):
            return e['id'], big
    raise AssertionError(f'{big} 没有兜底结局')


def character(st, eid):
    """品性档 1/2/3（松竹梅）。结局可写 品性:[{条件, 档}]，否则取默认档。"""
    t = st.d.t['endings']
    e = next((x for x in t['结局'] if x['id'] == eid), None)
    for x in (e or {}).get('品性', []):
        if rules.cond(st, x['条件']):
            return x['档']
    return t['评分']['品性档']['默认档']


def home(st, eid):
    """归宿：四条感情线里满足条件的取好感最高（相同按表的顺序）；否则普通归宿三种模式。
    帝国银幕偶像的局 Sil 线断掉。返回 {'类': 特殊/普通, '对象' 或 '模式', '好'}。"""
    d = st.d
    best = None
    for n in d.romance_lines:
        c = d.npcs[n].get('归宿条件')
        if not c or (n == 'Sil' and eid == 'end_idol'):
            continue
        if rules.cond(st, c) and (best is None or st.favor.get(n, 0) > st.favor.get(best, 0)):
            best = n
    if best:
        return {'类': '特殊', '对象': best, '好': True}
    for m in d.t['endings']['归宿']['普通']['模式']:
        if rules.cond(st, m['条件']):
            k, v = m['好归宿线']
            return {'类': '普通', '模式': m['模式'], '好': st.val(k) >= v}
    raise AssertionError


def score(st, rank, ch, hm):
    sc = st.d.t['endings']['评分']
    b = st.bonus()
    base = sum(st.val(n, b) for n in ('体力', '教育', '义气', '相貌', '自律')) + st.attr['名气']
    s = base // 6 - st.val('犯罪', b)
    s += sc['结局分'][rank]
    s += sc['品性档']['分'][str(ch)]
    if hm['类'] == '特殊':
        s += sc['归宿分']['特殊']
    else:
        s += sc['归宿分']['普通好归宿' if hm['好'] else '普通']
    return s


def judge(st):
    """1929-12 月结后的结局判定。结果写进 st.story['结局'] 和 st.ended。"""
    if st.ended:          # 中途的强制结局
        res = {'结局': st.ended, '大类': '强制', '档次': tier(st)}
        st.story['结局'] = res
        return res
    eid, big = career(st)
    rank = tier(st)
    ch = character(st, eid)
    hm = home(st, eid)
    res = {'结局': eid, '大类': big, '档次': rank, '品性': ch, '归宿': hm,
           '最常打的工': most_job(st), '最常上的课': most_class(st), '总分': score(st, rank, ch, hm)}
    st.ended = eid
    st.story['结局'] = res
    return res
