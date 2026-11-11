"""Ending resolution (GDD 15): forced -> special -> category -> grade -> ending table -> character tier -> destiny -> comment and total score. Data is in endings.json.

This module registers the derived variables the ending conditions need (rules.EXTRA_VARS): grade, top_tag_family, undefined, lowbudget_typed.
"""
from . import film, rules


def tier(st):
    lines = st.d.t['endings']['grade_lines']
    v = rules.get_var(st, 'max_rep')
    for k in ('S', 'A', 'B', 'C'):
        if v >= lines[k]:
            return k
    return 'D'


def biggest_family(st):
    """The tag family with the largest sum of counts; ties follow the table order; None when all are 0."""
    best, bv = None, 0
    for name, tags in st.d.tag_families.items():
        v = sum(st.tags.get(t, 0) for t in tags)
        if v > bv:
            best, bv = name, v
    return best


rules.EXTRA_VARS.update({
    'grade': tier,
    'top_tag_family': biggest_family,
    'undefined': film.undefined,
    'lowbudget_typed': film.low_budget,
})


def most_job(st):
    """The job with the most job_periods (ties go to the earlier row of the table); None when no job was ever done."""
    best, bv = None, 0
    for j in st.d.jobs:
        v = st.cnt('job_periods.' + j)
        if v > bv:
            best, bv = j, v
    return best


def most_class(st):
    """The class taken most often (reading counts as one class, recorded as 'book'), by class_periods; ties go to the earlier one."""
    best, bv = None, 0
    for c in st.d.classes:
        v = st.cnt('class_periods.' + c)
        if v > bv:
            best, bv = c, v
    if st.cnt('count.book_periods') > bv:
        best = 'book'
    return best


def career(st):
    """Career ending: returns (ending id, category). The forced ending (collapse) was already written to st.ended mid-game."""
    t = st.d.t['endings']
    for e in t['special']:
        if rules.cond(st, e['cond']):
            return e['id'], 'special'
    for c in t['categories']:
        if rules.cond(st, c['cond']):
            big = c['id']
            break
    lst = sorted((e for e in t['endings'] if e['category'] == big), key=lambda e: e['order'])
    for e in lst:
        if rules.cond(st, e['cond']):
            return e['id'], big
    raise AssertionError(f'{big} has no fallback ending')


def character(st, eid):
    """Character tier 1/2/3 (pine/bamboo/plum). An ending may write character: [{cond, tier}], otherwise the default tier is used."""
    t = st.d.t['endings']
    e = next((x for x in t['endings'] if x['id'] == eid), None)
    for x in (e or {}).get('character', []):
        if rules.cond(st, x['cond']):
            return x['tier']
    return t['scoring']['character_tiers']['default_tier']


def home(st, eid):
    """Destiny: of the four romance lines the one meeting its condition with the highest favor (ties go to the table order); otherwise the three ordinary destiny modes.
        In the Imperial screen idol run the Sil line is broken. Returns {'class': special/ordinary, 'target' or 'mode', 'good'}."""
    d = st.d
    best = None
    for n in d.romance_lines:
        c = d.npcs[n].get('destiny_cond')
        if not c or (n == 'sil' and eid == 'end_idol'):
            continue
        if rules.cond(st, c) and (best is None or st.favor.get(n, 0) > st.favor.get(best, 0)):
            best = n
    if best:
        return {'class': 'special', 'target': best, 'good': True}
    for m in d.t['endings']['destiny']['ordinary']['mode']:
        if rules.cond(st, m['cond']):
            k, v = m['good_destiny_line']
            return {'class': 'ordinary', 'mode': m['mode'], 'good': st.val(k) >= v}
    raise AssertionError


def score(st, rank, ch, hm):
    sc = st.d.t['endings']['scoring']
    b = st.bonus()
    base = sum(st.val(n, b) for n in ('stamina', 'education', 'loyalty', 'looks', 'discipline')) + st.attr['fame']
    s = base // 6 - st.val('crime', b)
    s += sc['ending_score'][rank]
    s += sc['character_tiers']['score'][str(ch)]
    if hm['class'] == 'special':
        s += sc['destiny_score']['special']
    else:
        s += sc['destiny_score']['ordinary_good' if hm['good'] else 'ordinary']
    return s


def judge(st):
    """Ending resolution after the 1929-12 month end. The result is written to st.story['ending'] and st.ended."""
    if st.ended:          # Forced ending mid-game
        res = {'ending': st.ended, 'category': 'forced', 'grade': tier(st)}
        st.story['ending'] = res
        return res
    eid, big = career(st)
    rank = tier(st)
    ch = character(st, eid)
    hm = home(st, eid)
    res = {'ending': eid, 'category': big, 'grade': rank, 'character': ch, 'destiny': hm,
           'top_job': most_job(st), 'top_class': most_class(st), 'total': score(st, rank, ch, hm)}
    st.ended = eid
    st.story['ending'] = res
    return res
