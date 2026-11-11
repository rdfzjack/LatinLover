"""街道、谈话、物品和装备（GDD 5.8、14.1）。都是月初的自由操作，不占日程。

出错时抛 StreetError，状态不变。
"""
from . import rules


class StreetError(Exception):
    pass


def discount_pct(st):
    """人脉显示值每满 20 减 5%，最多 25%。"""
    r = st.d.discount
    return min(st.val('人脉') // r['人脉每满'] * r['每档减百分比'], r['上限百分比'])


def price(st, entry, base):
    """折后价，向上取整；只对 折扣.生效 里的入口打折。"""
    if entry not in st.d.discount['生效']:
        return base
    pct = 100 - discount_pct(st)
    return -(-base * pct // 100)


def _pay(st, n):
    if st.money < n:
        raise StreetError('钱不够')
    st.money -= n


def _limit(st, key, n):
    if st.month_used.get(key, 0) >= n:
        raise StreetError('本月已经用过')


def _use(st, key):
    st.month_used[key] = st.month_used.get(key, 0) + 1


# ---------- 买卖 ----------
def shelf(st, entry):
    """该入口本月货架上的东西。书店按书的上架时间过滤。"""
    from .schedule import book_on_shelf
    e = st.d.street[entry]
    if entry == '书店':
        return [b for b in e['货架'] if book_on_shelf(st, b)]
    return list(e['货架'])


def buy(st, entry, iid):
    if iid not in shelf(st, entry):
        raise StreetError(f'{entry} 不卖 {iid}')
    d = st.d
    if iid in d.books:
        if iid in st.books or iid in st.read_books:
            raise StreetError('已经有这本书')
        p = price(st, entry, d.books[iid]['价格'])
        _pay(st, p)
        st.books[iid] = d.books[iid]['点数']
        return p
    if len(st.items) >= d.item_rules['持有上限']:
        raise StreetError('持有物品已满')
    p = price(st, entry, d.items[iid]['价格'])
    _pay(st, p)
    st.items.append(iid)
    return p


def _equipped_count(st, iid):
    return (st.equip['服装'] == iid) + st.equip['配饰'].count(iid)


def sell(st, iid):
    """任何物品半价卖出（向下取整），装备中的不能卖。读过的书也走这里。"""
    d = st.d
    if iid in st.read_books:
        st.read_books.remove(iid)
        p = d.books[iid]['价格'] // 2
        st.add_money(p)
        return p
    if iid not in st.items:
        raise StreetError('没有这件物品')
    it = d.items[iid]
    if not it['出售']:
        raise StreetError('这件不能卖')
    if st.items.count(iid) <= _equipped_count(st, iid):
        raise StreetError('装备中的不能卖')
    st.items.remove(iid)
    p = it['价格'] // 2
    st.add_money(p)
    return p


def equip(st, iid):
    it = st.d.items.get(iid)
    if iid not in st.items or it is None:
        raise StreetError('没有这件物品')
    if st.items.count(iid) <= _equipped_count(st, iid):
        raise StreetError('已经装备上了')
    slot = it['槽']
    if slot == '服装':
        st.equip['服装'] = iid
    elif slot == '配饰':
        if len(st.equip['配饰']) >= st.d.t['items']['规则']['配饰槽']:
            raise StreetError('配饰槽满了')
        st.equip['配饰'].append(iid)
    else:
        raise StreetError('这件不用装备')


def unequip(st, iid):
    if st.equip['服装'] == iid:
        st.equip['服装'] = None
    elif iid in st.equip['配饰']:
        st.equip['配饰'].remove(iid)
    else:
        raise StreetError('没有装备这件')


def use(st, iid):
    """用掉一件消耗品。"""
    it = st.d.items.get(iid)
    if iid not in st.items or it is None or it['类'] != '消耗':
        raise StreetError('不是持有的消耗品')
    st.items.remove(iid)
    return rules.apply_effect(st, it['效果'], source='event')


# ---------- 服务 ----------
def _service(st, entry, name):
    for s in st.d.street[entry]['服务']:
        if s['名字'] == name:
            return s
    raise StreetError(f'{entry} 没有 {name}')


def restaurant(st, name):
    """每月一次，三选一。生病状态下照收钱，没有效果（GDD 5.8）。"""
    e = st.d.street['餐厅']
    s = _service(st, '餐厅', name)
    _limit(st, '餐厅', e['限次']['次数'])
    p = price(st, '餐厅', s['价格'])
    _pay(st, p)
    _use(st, '餐厅')
    if not st.status['生病']:
        rules.apply_effect(st, s['效果'], source='schedule')
    return p


def church(st):
    s = _service(st, '教堂', '捐款')
    _limit(st, '教堂.捐款', s['限次']['次数'])
    _pay(st, s['价格'])
    _use(st, '教堂.捐款')
    rules.apply_effect(st, s['效果'], source='schedule')
    return s['价格']


def hospital(st):
    """只在生病状态可用。费用 生病指数×2（打折），疲劳 -(生病指数+1)。"""
    e = st.d.street['医院']
    if not rules.cond(st, e['条件']):
        raise StreetError('没生病')
    idx = st.idx['生病指数']
    p = price(st, '医院', idx * 2)
    _pay(st, p)
    st.attr['疲劳'] = max(0, st.attr['疲劳'] - (idx + 1))
    return p


def sil_persuade(st):
    """失控状态下让 Sil 劝：疲劳 -(Sil 好感/2)，Sil 好感 +2，每月一次。"""
    s = _service(st, '和 Sil 谈话', '劝说')
    if not rules.cond(st, s['条件']):
        raise StreetError('不在失控状态')
    _limit(st, 'Sil.劝说', s['限次']['次数'])
    _use(st, 'Sil.劝说')
    st.attr['疲劳'] = max(0, st.attr['疲劳'] - st.favor.get('Sil', 0) // 2)
    st.favor['Sil'] = min(100, st.favor.get('Sil', 0) + 2)


def sil_hint(st):
    """近况提示：按生病、失控、好感、疲劳、最高属性的顺序挑一条，返回 (类, 细节)。
    好感、疲劳两条的线 GDD 没定，这里先用感情线好感 ≥60、疲劳 ≥50（占位）。"""
    if st.status['生病']:
        i = st.idx['生病指数']
        return ('生病', '病情很重' if i >= 60 else '不要太勉强')
    if st.status['失控']:
        return ('失控', st.idx['失控指数'])
    lines = [(st.favor.get(n, 0), n) for n in st.d.romance_lines]
    top = max(lines)
    if top[0] >= 60:
        return ('好感', top[1])
    if st.val('疲劳') >= 50:
        return ('疲劳', st.val('疲劳'))
    return ('最高属性', st.highest_base())
