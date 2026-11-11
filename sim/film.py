"""片约、拍摄、违约、上映（GDD 5.6、8、10 重病违约）。数字在 roles.json 的 默认.拍摄 / 默认.上映。

一部片约（st.story['片'] 里的一项）：
    {'id', '角色': 角色快照, '档次', '配角', '亲自上', '锁': [[月序, 旬], …], '拍摄日', '成功日',
     '表现', '片酬', '状态', '上映', '结果'}
状态：待拍 → 拍摄 → 待映 → 已映；另有 违约（重病、失踪等）和 被抢（抢角输了）。

随机数的消耗顺序（Godot 照抄）：每个拍摄日先 r0(疲劳)，再按 schedule._extra_fail 掷恋爱、失控偷懒，
亲自上时最后掷受伤 1/40。上映不掷随机数。
"""
from . import rules
from .schedule import add_stat, _extra_fail

TIERS = ('小', '中', '大')


def shoot_cfg(d):
    return d.role_cfg['拍摄']


def rel_cfg(d):
    return d.role_cfg['上映']


def films(st):
    return st.story['片']


# ---------- 标签 ----------
def typecast_tags(st):
    """定型的内容标签（计数 ≥ 定型线）。"""
    line = rel_cfg(st.d)['定型线']
    return [t for t in st.d.content_tags if st.tags.get(t, 0) >= line]


def low_budget(st):
    """低成本定型：低成本计数 ≥ 4（计数降到 3 及以下即解除，所以不用另记状态）。"""
    return int(st.cnt('计数.低成本') >= rel_cfg(st.d)['低成本']['定型线'])


def undefined(st):
    """无法定义：有计数的内容标签 ≥6 种，且没有一个 ≥3（8.4）。"""
    c = rel_cfg(st.d)
    have = [t for t in st.d.content_tags if st.tags.get(t, 0) > 0]
    return int(len(have) >= c['无法定义种类'] and not typecast_tags(st))


# ---------- 片约 ----------
def new_film(st, role, locks, support=False, personally=False):
    st.story['序号'] += 1
    f = {'id': f"film{st.story['序号']}", '角色': role, '档次': role['档次'], '配角': bool(support),
         '亲自上': bool(personally), '锁': [list(x) for x in locks], '拍摄日': 0, '成功日': 0,
         '表现': None, '片酬': None, '状态': '待拍', '上映': None, '结果': None}
    films(st).append(f)
    update_status(st)
    return f


def board_locks(st, tier, support=False):
    """选片板拿到的角色：锁定次月开头的若干旬（小 1、中 2、大 3；配角 −1，最少 1）。"""
    n = st.d.role_cfg['拍摄旬数'][tier]
    if support:
        x = st.d.t['habits']['试镜']['结果']['惜败']
        n = max(x['拍摄旬数最少'], n - x['拍摄旬数减'])
    return [[st.ym + 1, k] for k in range(n)]


def next_period(st, i):
    return [st.ym, i + 1] if i < 2 else [st.ym + 1, 0]


def is_locked(st, ym, i):
    return any([ym, i] in f['锁'] for f in films(st) if f['状态'] in ('待拍', '拍摄'))


def locked(st, i):
    for f in films(st):
        if f['状态'] in ('待拍', '拍摄') and [st.ym, i] in f['锁']:
            return f
    return None


def update_status(st):
    st.status['有未开拍角色'] = int(any(f['状态'] == '待拍' for f in films(st)))


def can_go_personally(st, role):
    """亲自上：角色带西部、动作冒险、战争任一标签，且胆识 ≥60（做过替身 4 期后 50）。"""
    c = shoot_cfg(st.d)['亲自上']
    if not set(role['标签']) & set(c['标签']):
        return False
    line = c['胆识线']
    if st.flags.get(c['胆识线_旗标']['旗标']):
        line = c['胆识线_旗标']['线']
    return st.val('胆识') >= line


# ---------- 拍摄 ----------
def shoot(st, i, f, days):
    """一个拍摄旬。最后一旬拍完时发片酬、算表现、定上映月。"""
    d = st.d
    c = shoot_cfg(d)
    g = st.rng.logic
    t = f['档次']
    f['状态'] = '拍摄'
    update_status(st)
    for day, sun in days:
        if sun:
            continue
        f['拍摄日'] += 1
        st.exposed = 1
        add_stat(st, '疲劳', c['疲劳'][t])
        b = st.bonus()
        ok = st.val('体力', b) - g.r0(st.val('疲劳', b)) >= c['成功线'][t]
        if _extra_fail(st, True):
            ok = False
        if ok:
            f['成功日'] += 1
        if f['亲自上'] and g.chance(*c['亲自上']['受伤概率']):
            rules.apply_effect(st, c['亲自上']['受伤效果'], source='schedule')
            st.inc('计数.受伤')
    if [st.ym, i] == f['锁'][-1]:
        finish(st, f)


def performance(st, f):
    """P ×1000：500 + 成功日×500/拍摄日 + 加分技能×2（亲自上 +100），夹在 500–1200。"""
    c = shoot_cfg(st.d)
    days = f['拍摄日']
    p = c['表现下限'] + (f['成功日'] * 500 // days if days else 500)
    p += st.val(f['角色']['加分技能']) * 1000 // 500
    if f['亲自上']:
        p += c['亲自上']['表现加']
    return max(c['表现下限'], min(c['表现上限'], p))


def fee(st, f):
    """片酬 = 基础 ×(亲自上 130%)×(配角 40%)×(400+谈判)/400 × 合同系数，每步向下取整。"""
    d = st.d
    c = shoot_cfg(d)
    v = f['角色']['片酬']
    if f['亲自上']:
        v = v * c['亲自上']['片酬百分比'] // 100
    if f['配角']:
        v = v * d.t['habits']['试镜']['结果']['惜败']['片酬百分比'] // 100
    v = v * (c['谈判除数'] + st.val('谈判')) // c['谈判除数']
    k = d.contract
    if st.val('教育') < k['教育低于'] and not rules.cond(st, k['免除条件']):
        v = v * k['片酬系数百分比'] // 100
    return v


def finish(st, f):
    f['表现'] = performance(st, f)
    f['片酬'] = fee(st, f)
    st.add_money(f['片酬'])
    f['状态'] = '待映'
    f['上映'] = st.ym + rel_cfg(st.d)['隔月']
    if f['亲自上']:
        st.inc('计数.亲自上')
    update_status(st)


# ---------- 违约 ----------
def breach_month(st, ym):
    """ym 月里锁定的片约全部违约：片酬为 0，名气 −10%，不上映（GDD 10 重病；失踪、戒断、占月的机遇同样处理）。"""
    out = []
    pct = -st.d.rest_forced[0]['拍摄违约']['名气百分比']
    for f in films(st):
        if f['状态'] in ('待拍', '拍摄') and any(x[0] == ym for x in f['锁']):
            f['状态'] = '违约'
            st.attr['名气'] = max(0, st.attr['名气'] - st.attr['名气'] * pct // 100)
            st.inc('计数.违约')
            out.append(f)
    update_status(st)
    return out


# ---------- 上映 ----------
def fit(st, role):
    """契合 F ×1000 = 600 + 400 × 平均(min(值/目标, 1.5))。"""
    c = rel_cfg(st.d)['契合']
    b = st.bonus()
    rs = [min(st.val(k['项'], b) * 1000 // k['目标'], c['单项上限百分比'] * 10) for k in role['看重']]
    avg = sum(rs) // len(rs) if rs else 1000
    return c['底'] + c['系数'] * avg // 1000


def familiarity(st, role, tier):
    """标签熟悉 T ×1000 = 1000 + 30 × min(该角色各标签计数之和, 5)；定型标签、低成本定型下的小片取满。
    返回 (T, 是否吃非定型的 ×0.9)。"""
    c = rel_cfg(st.d)
    full = 1000 + c['标签熟悉']['每个'] * c['标签熟悉']['上限个数']
    tc = typecast_tags(st)
    mine = [t for t in role['标签'] if t in tc]
    if mine or (low_budget(st) and tier == '小'):
        return full, False
    n = sum(st.tags.get(t, 0) for t in role['标签'])
    T = 1000 + c['标签熟悉']['每个'] * min(n, c['标签熟悉']['上限个数'])
    return T, bool(tc)


def talk_line(st, role):
    line = role['谈吐线']
    if st.flags.get('有声谈吐线减10'):
        line -= rel_cfg(st.d)['电台谈吐线减']
    return line


def release_one(st, f):
    d = st.d
    c = rel_cfg(d)
    role, t = f['角色'], f['档次']
    B = c['基数'][t]
    P = f['表现']
    F = fit(st, role)
    T, off = familiarity(st, role, t)
    S = B * P * F * T // 1000000            # S ×1000
    if off:
        S = S * c['非定型百分比'] // 100
    accent = False
    if role.get('有声'):
        st.inc('计数.有声片部数')
        if st.val('谈吐') < talk_line(st, role):
            S = S * c['有声罚百分比'] // 100
            accent = True
            st.flags['口音待触发'] = 1
    hit = S >= B * c['大卖百分比'] * 10
    flop = S < B * c['扑街百分比'] * 10
    k = d.t['habits']['试镜']['结果']['惜败']['上映百分比'] if f['配角'] else 100
    fame = S * c['名气百分比'] // 100000
    if flop:
        fame //= 2
    fame = fame * k // 100
    money = S * c['分红倍数'] // 1000 * k // 100
    add_stat(st, '名气', fame)
    st.add_money(money)
    corr = 0
    if not flop:
        corr = c['修正'][t] * (2 if hit else 1) * k // 100
        st.corr[role['路']] += corr
    for tag in role['标签']:
        st.tags[tag] = st.tags.get(tag, 0) + 1
    if not f['配角']:
        n = st.cnt('计数.低成本') + c['低成本']['增减'][t]
        st.count['计数.低成本'] = max(0, n)
        st.inc('计数.主演.' + t)
        if role.get('女主'):
            rules.apply_effect(st, f"好感.{role['女主']}+{c['女主好感']}", source='event')
    else:
        st.inc('计数.配角')
    st.inc('计数.上映')
    if hit:
        st.inc('计数.大卖')
        if set(role['标签']) & {'浪漫', '异国情人'}:
            st.inc('计数.浪漫系大卖')
    if flop:
        st.inc('计数.扑街')
    st.exposed = 1
    f['状态'] = '已映'
    f['结果'] = {'S': S, 'B': B, 'P': P, 'F': F, 'T': T, '非定型': off, '口音': accent, '大卖': hit,
                 '扑街': flop, '名气': fame, '分红': money, '修正': corr, '月': st.ym}
    return f['结果']


def release(st):
    """月结第 2 步：本月该上映的片。顺带更新“近 12 个月大片大卖”计数（1929-05 颁奖礼用）。"""
    out = [release_one(st, f) for f in films(st) if f['状态'] == '待映' and f['上映'] == st.ym]
    st.count['计数.近12月大片大卖'] = sum(
        1 for f in films(st) if f['状态'] == '已映' and f['档次'] == '大' and f['结果']['大卖']
        and f['结果']['月'] > st.ym - 12)
    return out
