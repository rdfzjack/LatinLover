"""Street, conversations, items and gear (GDD 5.8, 14.1). All are free actions at the start of the month and take no schedule slot.

A StreetError is raised on failure and the state is unchanged.
"""
from . import rules


class StreetError(Exception):
    pass


def discount_pct(st):
    """Every full 20 of connections displayed value gives 5% off, at most 25%."""
    r = st.d.discount
    return min(st.val('connections') // r['connections_per'] * r['cut_pct_per_step'], r['cap_pct'])


def price(st, entry, base):
    """Discounted price, rounded up; only entries in discount.applies get the discount."""
    if entry not in st.d.discount['applies']:
        return base
    pct = 100 - discount_pct(st)
    return -(-base * pct // 100)


def _pay(st, n):
    if st.money < n:
        raise StreetError('if_broke')
    st.money -= n


def _limit(st, key, n):
    if st.month_used.get(key, 0) >= n:
        raise StreetError('already used this month')


def _use(st, key):
    st.month_used[key] = st.month_used.get(key, 0) + 1


# ---------- buying and selling ----------
def shelf(st, entry):
    """What is on the shelf of that entry this month. The bookstore filters books by their on_shelf date."""
    from .schedule import book_on_shelf
    e = st.d.street[entry]
    if entry == 'bookstore':
        return [b for b in e['shelf'] if book_on_shelf(st, b)]
    return list(e['shelf'])


def buy(st, entry, iid):
    if iid not in shelf(st, entry):
        raise StreetError(f'{entry} does not sell {iid}')
    d = st.d
    if iid in d.books:
        if iid in st.books or iid in st.read_books:
            raise StreetError('already own this book')
        p = price(st, entry, d.books[iid]['price'])
        _pay(st, p)
        st.books[iid] = d.books[iid]['points']
        return p
    if len(st.items) >= d.item_rules['hold_cap']:
        raise StreetError('carrying too many items')
    p = price(st, entry, d.items[iid]['price'])
    _pay(st, p)
    st.items.append(iid)
    return p


def _equipped_count(st, iid):
    return (st.equip['outfit'] == iid) + st.equip['accessory'].count(iid)


def sell(st, iid):
    """Any item sells at half price (rounded down); equipped ones cannot be sold. Books already read go through here too."""
    d = st.d
    if iid in st.read_books:
        st.read_books.remove(iid)
        p = d.books[iid]['price'] // 2
        st.add_money(p)
        return p
    if iid not in st.items:
        raise StreetError('no such item')
    it = d.items[iid]
    if not it['sellable']:
        raise StreetError('this item cannot be sold')
    if st.items.count(iid) <= _equipped_count(st, iid):
        raise StreetError('equipped items cannot be sold')
    st.items.remove(iid)
    p = it['price'] // 2
    st.add_money(p)
    return p


def equip(st, iid):
    it = st.d.items.get(iid)
    if iid not in st.items or it is None:
        raise StreetError('no such item')
    if st.items.count(iid) <= _equipped_count(st, iid):
        raise StreetError('already equipped')
    slot = it['slot']
    if slot == 'outfit':
        st.equip['outfit'] = iid
    elif slot == 'accessory':
        if len(st.equip['accessory']) >= st.d.t['items']['rules']['accessory_slots']:
            raise StreetError('accessory slots are full')
        st.equip['accessory'].append(iid)
    else:
        raise StreetError('this item cannot be equipped')


def unequip(st, iid):
    if st.equip['outfit'] == iid:
        st.equip['outfit'] = None
    elif iid in st.equip['accessory']:
        st.equip['accessory'].remove(iid)
    else:
        raise StreetError('this item is not equipped')


def use(st, iid):
    """Uses up one consumable."""
    it = st.d.items.get(iid)
    if iid not in st.items or it is None or it['class'] != 'consumable':
        raise StreetError('not a held consumable')
    st.items.remove(iid)
    return rules.apply_effect(st, it['effect'], source='event')


# ---------- services ----------
def _service(st, entry, name):
    for s in st.d.street[entry]['services']:
        if s['id'] == name:
            return s
    raise StreetError(f'{entry} has no {name}')


def restaurant(st, name):
    """Once a month, pick one of three. When sick the money is still charged and there is no effect (GDD 5.8)."""
    e = st.d.street['restaurant']
    s = _service(st, 'restaurant', name)
    _limit(st, 'restaurant', e['limit']['times'])
    p = price(st, 'restaurant', s['price'])
    _pay(st, p)
    _use(st, 'restaurant')
    if not st.status['sick']:
        rules.apply_effect(st, s['effect'], source='schedule')
    return p


def church(st):
    s = _service(st, 'church', 'donation')
    _limit(st, 'church.donation', s['limit']['times'])
    _pay(st, s['price'])
    _use(st, 'church.donation')
    rules.apply_effect(st, s['effect'], source='schedule')
    return s['price']


def hospital(st):
    """Only usable when sick. Cost sick_index x 2 (discounted), fatigue -(sick_index+1)."""
    e = st.d.street['hospital']
    if not rules.cond(st, e['cond']):
        raise StreetError('not sick')
    idx = st.idx['sick_index']
    p = price(st, 'hospital', idx * 2)
    _pay(st, p)
    st.attr['fatigue'] = max(0, st.attr['fatigue'] - (idx + 1))
    return p


def sil_persuade(st):
    """When reckless, let Sil persuade: fatigue -(Sil favor/2), Sil favor +2, once a month."""
    s = _service(st, 'sil_talk', 'persuade')
    if not rules.cond(st, s['cond']):
        raise StreetError('not in a reckless state')
    _limit(st, 'sil.persuade', s['limit']['times'])
    _use(st, 'sil.persuade')
    st.attr['fatigue'] = max(0, st.attr['fatigue'] - st.favor.get('sil', 0) // 2)
    st.favor['sil'] = min(100, st.favor.get('sil', 0) + 2)


def sil_hint(st):
    """Status hint: picks one in the order sick, reckless, favor, fatigue, top attribute and returns (kind, detail).
        The favor and fatigue lines are not set in the GDD; for now favor >= 60 on a romance line and fatigue >= 50 (placeholder)."""
    if st.status['sick']:
        i = st.idx['sick_index']
        return ('sick', 'seriously ill' if i >= 60 else 'do not overdo it')
    if st.status['reckless']:
        return ('reckless', st.idx['reckless_index'])
    lines = [(st.favor.get(n, 0), -i, n) for i, n in enumerate(st.d.romance_lines)]    # ties: earlier line first
    top = max(lines)
    if top[0] >= 60:
        return ('favor', top[2])
    if st.val('fatigue') >= 50:
        return ('fatigue', st.val('fatigue'))
    return ('top attribute', st.highest_base())
