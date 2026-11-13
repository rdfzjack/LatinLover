"""Validates data/new/*.json. Usage: python3 tools/check_data.py
Checks: fields complete, no decimals, referenced attributes/skills/classes/books/jobs/NPCs exist, conditions and effects parse, opening-question budgets, calendar.
References to events, items and the NPC table (step 3) are only validated when those tables exist; otherwise they are only counted."""
import json, os, re, sys, datetime, calendar as cal
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'new')
errs, notes = [], []
def err(f, m): errs.append(f'{f}: {m}')
def load(n):
    p = os.path.join(D, n)
    if not os.path.exists(p): return None
    with open(p, encoding='utf-8') as fh: return json.load(fh)
def no_float(o, f, path=''):
    if isinstance(o, float): err(f, f'decimal {path}={o}')
    elif isinstance(o, dict):
        for k, v in o.items(): no_float(v, f, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o): no_float(v, f, f'{path}[{i}]')
def need(f, d, keys, where=''):
    for k in keys:
        if k not in d: err(f, f'{where} missing field {k}')

FILES = ['stats','skills','classes','books','jobs','rest','places','lifestyle','street','origins','calendar',
         'habits','rivals','roles','items','events','outing','romance','npc_schedule','npc_chains','annual','opportunities','endings','map','traits']
T = {}
for n in FILES:
    T[n] = load(n + '.json')
    if T[n] is None: err(n + '.json', 'file does not exist'); continue
    no_float(T[n], n + '.json')
if errs:
    print('\n'.join(errs)); sys.exit(1)

stats, skills, classes, books, jobs, rest, places, life, street, origins, cal_ = (T[n] for n in FILES[:11])
habits, rivals, roles, items_t, events_t, outing, romance, npc_sched, chains, annual, opps, endings, map_t, traits_t = (T[n] for n in FILES[11:])
ATTRS = [a['id'] for a in stats['attrs']]
SK = [s['id'] for s in skills['skills']]
ROADS = [r['id'] for r in stats['roads']]
CLASS_IDS = [c['id'] for c in classes['classes']]
JOB_IDS = [j['id'] for j in jobs['jobs']]
BOOK_IDS = [b['id'] for b in books['books']]
CAL_MONTHS = [m['month'] for m in cal_['months']]
TAGS = [t['id'] for t in roles['tags']]

# registries
NPC = {n['id'] for n in romance['npcs']}
ITEM_NAMES = {i['id'] for i in items_t['items']}
EVENT_IDS = {e['id'] for e in events_t['events']} | {e['id'] for e in outing['events']}
HABITS = {h['id'] for h in habits['habits']}
RIVALS = {r['id'] for r in rivals['named']}
PLACES = {p['id'] for p in places['places']}
pending_items, pending_events = set(), set()
def ref_item(f, n):
    if ITEM_NAMES is None: pending_items.add(n)
    elif n not in ITEM_NAMES: err(f, f'item does not exist {n}')
def ref_event(f, e):
    if e is None: return
    if EVENT_IDS is None: pending_events.add(e)
    elif e not in EVENT_IDS: err(f, f'event does not exist {e}')

DERIVED = {'max_rep','month','year','drug_stage','drug_points','debt_months','grade','top_tag_family','undefined','lowbudget_typed','talkie_count',
           'top_base_attr','top_savvy_skill','max_job_periods','rep_spread','top_road'}
PREFIX = ('status.','count.','tag.','road_periods.','flag.','duels.')
def var_ok(v):
    if v in ATTRS or v in SK or v in ROADS or v in DERIVED or v in ('money','sick_index','reckless_index','date'): return True
    if v.startswith('favor.'): return v.split('.', 1)[1] in NPC
    if v.startswith('job_periods.'): return v.split('.', 1)[1] in JOB_IDS
    if v.startswith('class_periods.'): return v.split('.', 1)[1] in CLASS_IDS
    if v.startswith('road_periods.'): return v.split('.', 1)[1] in ROADS
    return v.startswith(PREFIX) and len(v) > 3
COMP = ('>=','<=','>','<','==','!=','in')
def check_cond(f, c, where=''):
    if not isinstance(c, list): err(f, f'{where} cond is not a list'); return
    for g in c:
        if not isinstance(g, list): err(f, f'{where} cond group is not a list'); continue
        for t in g:
            if not (isinstance(t, list) and len(t) == 3): err(f, f'{where} cond term format {t}'); continue
            if not var_ok(t[0]): err(f, f'{where} cond variable does not exist {t[0]}')
            if t[1] not in COMP: err(f, f'{where} comparator {t[1]}')
            if t[1] == 'in':
                if not isinstance(t[2], list): err(f, f'{where} the value of `in` must be a list')
            elif isinstance(t[2], str) and t[2].startswith('@'):
                if not var_ok(t[2][1:]): err(f, f'{where} referenced variable does not exist {t[2]}')
            elif not isinstance(t[2], (int, str)): err(f, f'{where} cond value {t[2]}')
EFF = re.compile(r'^(.+?)([+\-=])(\d+)(%?)$')
def eff_name_ok(n):
    if n in ATTRS or n in SK or n in ('money','drug_stage','drug_points','debt_months'): return True
    if n.startswith('favor.'): return n.split('.', 1)[1] in NPC
    if n.startswith('rep_bonus.'): return n.split('.', 1)[1] in ROADS
    if n.startswith('weight.'): return n.split('.', 1)[1] in TAGS
    if n.startswith('item.'): return n.split('.', 1)[1] in ITEM_NAMES
    return n.startswith(('status.','flag.')) and len(n) > 3
def parse_effect(f, s, where=''):
    """Returns {name: accumulated delta}, only the +/- integer terms; for %, = and trigger only the format is checked"""
    out = {}
    for tok in s.split():
        if tok.startswith('trigger.'):
            ref_event(f, tok.split('.', 1)[1]); continue
        m = EFF.match(tok)
        if not m: err(f, f'{where} bad effect term: {tok}' + hint(tok)); continue
        n, op, v, pct = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        if not eff_name_ok(n): err(f, f'{where} effect name does not exist {n}'); continue
        if op != '=' and not pct: out[n] = out.get(n, 0) + (v if op == '+' else -v)
    return out
def hint(s):
    """Hints for common typos such as Chinese punctuation and full-width symbols."""
    bad = [c for c in s if c in '＋－＝％，。：；“”‘’　（）']
    return f'(it contains non-ASCII symbols {"".join(bad)}; use ASCII + - = % and plain spaces)' if bad else '(syntax: name+n, name-n, name=n, terms separated by spaces)'
def is_range(r): return isinstance(r, list) and len(r) == 2 and all(isinstance(x, int) for x in r) and r[0] <= r[1]

# stats
f = 'stats.json'
for a in stats['attrs']: need(f, a, ['id','name','range','init'], a.get('id'))
if len(ATTRS) != 8: err(f, 'attrs must have 8 entries')
if len(stats['fame_tiers']) != 5: err(f, 'fame_tiers must have 5 tiers')
if stats['levels']['gate'] != [5*l*(l+1) for l in range(10)]: err(f, 'class_steps does not match 5L(L+1)')
for k in ('monthly_decay_pct', 'monthly_decay_min'):
    if not isinstance(stats['fame_rules'].get(k), int): err(f, f'fame_rules is missing the integer field {k}')
dr = stats.get('drug', {})
for k in ('divine_gain_mult', 'divine_perf_add', 'side_perf_add', 'side_fail_pct', 'hook_base_pct', 'hook_step_pct', 'hook_cap_pct', 'refuse_discipline'):
    if not isinstance(dr.get(k), int): err(f, f'drug is missing the integer field {k}')
for k in ('dose_effect', 'side_effect', 'deep_monthly_effect'):
    if k not in dr: err(f, f'drug is missing {k}')
    else: parse_effect(f, dr[k], 'drug ' + k)
for k in ('prob_pct', 'crime_step', 'crime_add_pct', 'prob_cap_pct', 'addicted_add_pct', 'stock', 'price_depth_pct', 'price_cap_pct'):
    if not isinstance(dr.get('dealer', {}).get(k), int): err(f, f'drug.dealer is missing the integer field {k}')
pr = dr.get('dealer', {}).get('price')
if not (isinstance(pr, list) and len(pr) == 2 and pr[0] <= pr[1]): err(f, 'drug.dealer.price must be [low, high]')
for k in ('fail_base_pct', 'fail_step_pct', 'fail_cap_pct', 'fatigue_base', 'fatigue_step', 'depth_drop'):
    if not isinstance(dr.get('attack', {}).get(k), int): err(f, f'drug.attack is missing the integer field {k}')
ow = dr.get('outcome_weights', {})
if sorted(ow) != ['divine', 'high', 'side'] or not all(isinstance(v, int) and v >= 0 for v in ow.values()):
    err(f, 'drug.outcome_weights must have the integer weights high, divine, side')
if not (isinstance(dr.get('stage_lines'), list) and len(dr['stage_lines']) == 3 and dr['stage_lines'] == sorted(dr['stage_lines'])):
    err(f, 'drug stage_lines must be 3 increasing numbers (stages 1, 2, 3)')
for k in ('fine_min', 'fine_pct', 'detain_periods', 'raid_crime_div'):
    if not isinstance(stats.get('arrest', {}).get(k), int): err(f, f'arrest is missing the integer field {k}')
# skills
f = 'skills.json'
if len(SK) != 12 or len(set(SK)) != 12: err(f, 'skills must have 12 entries with unique ids')
for s in skills['skills']:
    need(f, s, ['id','name','road','train_range','init','fixed_use'], s.get('id'))
    if s['road'] not in ROADS: err(f, f"{s['id']} road does not exist {s['road']}")
for r in stats['roads']:
    if [s['id'] for s in skills['skills'] if s['road'] == r['id']] != r['skills']: err('stats.json', f"road {r['id']} skills differ from skills.json")
# classes
f = 'classes.json'
for c in classes['classes']:
    need(f, c, ['id','name','fee','gain'], c.get('id'))
    if len(c['fee']) != 4: err(f, f"{c['id']} fee must have 4 tiers")
    for e in c['gain']:
        if e['stat'] not in SK and e['stat'] not in ATTRS: err(f, f"{c['id']} gain stat does not exist {e['stat']}")
        if len(e['per_level']) != 4 or not all(is_range(r) for r in e['per_level']): err(f, f"{c['id']} {e['stat']} per_level format")
        if 'cond' in e: check_cond(f, e['cond'], c['id'])
    if 'period_effect' in c: parse_effect(f, c['period_effect'], c['id'])
    if not (isinstance(c.get('fatigue_per_day'), int) and c['fatigue_per_day'] >= 0): err(f, f"{c['id']} fatigue_per_day must be an integer >= 0")
    if 'duv' in c.get('story_chain', {}).values() and 'duv' not in NPC: err(f, 'duv is not in the NPC table')
# books
f = 'books.json'
tiers = {t['tier']: t for t in books['tiers']}
for b in books['books']:
    need(f, b, ['id','name','skills','tier','education_gate','skill_cap','points','gain','price','finish_event'], b.get('id'))
    if b['skills'] not in SK: err(f, f"{b['id']} skill does not exist")
    t = tiers.get(b['tier'])
    if not t: err(f, f"{b['id']} tier does not exist"); continue
    for k in ('education_gate','skill_cap','points','gain','price'):
        if b[k] != t[k]: err(f, f"{b['id']} {k} does not match the tier table")
    ref_event(f, b['finish_event'])
    if not (isinstance(b.get('fatigue_per_day'), int) and b['fatigue_per_day'] >= 0): err(f, f"{b['id']} fatigue_per_day must be an integer >= 0")
if len(set(BOOK_IDS)) != len(BOOK_IDS): err(f, 'duplicate id')
if not BOOK_IDS: err(f, 'need at least one book')
for s in ('fight','riding','nerve','physique','connections'):
    if any(b['skills'] == s for b in books['books']): err(f, f'{s} must not have books')
# jobs
f = 'jobs.json'
if not JOB_IDS or len(set(JOB_IDS)) != len(JOB_IDS): err(f, 'need at least one job and ids must be unique')
ev_ids = []
for j in jobs['jobs']:
    w = j['id']
    need(f, j, ['id','name','earliest','prereq','daily_wage','success_lines','daily_effect','exposure','npc','job_period_effect','period_random','milestones'], w)
    if j['earliest'] not in CAL_MONTHS: err(f, f'{w} earliest is not in the calendar')
    if not isinstance(j['daily_wage'], int): err(f, f'{w} daily_wage is not an integer')
    check_cond(f, j['prereq'], w + ' prereq')
    for c in j['success_lines']:
        if c['stat'] not in ATTRS and c['stat'] not in SK: err(f, f"{w} success line stat does not exist {c['stat']}")
    for c in j.get('success_line_mods', []):
        check_cond(f, c['cond'], w + ' success_line_mods')
        if c['stat'] not in [x['stat'] for x in j['success_lines']]: err(f, f"{w} success_line_mods stat is not in success_lines {c['stat']}")
        if not isinstance(c['value'], int): err(f, f'{w} success_line_mods value')
    for e in j['daily_effect']:
        if e['stat'] not in ATTRS and e['stat'] not in SK: err(f, f"{w} daily_effect stat does not exist {e['stat']}")
        if not is_range(e['add']): err(f, f'{w} daily_effect range')
    if j['npc'] and j['npc'] not in NPC: err(f, f"{w} NPC does not exist {j['npc']}")
    if j['job_period_effect']: parse_effect(f, j['job_period_effect'], w)
    for r in j['period_random']:
        if not (is_range(r['prob']) and r['prob'][0] >= 1): err(f, f'{w} prob format')
        ev_ids.append(r['event']); ref_event(f, r['event'])
    for m in j['milestones']:
        check_cond(f, m['cond'], w + ' milestones'); ev_ids.append(m['event']); ref_event(f, m['event'])
if len(set(ev_ids)) != len(ev_ids): err(f, 'duplicate event id')
# crime jobs (step 12c): every job with crime_tier must have exactly the shape of crime_tiers; only skills, success-line stats and the name may differ
CT = jobs.get('crime_tiers', {})
for j in jobs['jobs']:
    w = j['id']
    if 'crime_tier' not in j:
        if any(k in j for k in ('raid_prob', 'raid_line', 'raid_skill')): err(f, f'{w} has raid_* fields but no crime_tier')
        continue
    t = CT.get(str(j['crime_tier']))
    if t is None: err(f, f"{w} crime_tier must be 1 or 2 (a key of crime_tiers), got {j['crime_tier']}"); continue
    if j['daily_wage'] != t['daily_wage']: err(f, f"{w} crime_tier {j['crime_tier']}: daily_wage must be {t['daily_wage']}, got {j['daily_wage']}")
    eff = {e['stat']: e['add'] for e in j['daily_effect']}
    for k, v in t['daily'].items():
        if eff.get(k) != v: err(f, f"{w} crime_tier {j['crime_tier']}: daily_effect {k} must be {v}, got {eff.get(k)}")
    for k, v in eff.items():
        if k not in t['daily'] and k in ATTRS: err(f, f"{w} crime_tier {j['crime_tier']}: daily_effect may only change skills besides {sorted(t['daily'])}, not the attribute {k}")
    if len(j['success_lines']) != t['success_lines']: err(f, f"{w} crime_tier {j['crime_tier']}: needs {t['success_lines']} success lines")
    if 'skill_line' in t and not any(c['stat'] in SK and c['value'] == t['skill_line'] for c in j['success_lines']):
        err(f, f"{w} crime_tier {j['crime_tier']}: one success line must be a skill at {t['skill_line']}")
    if j.get('raid_prob') != t['raid_prob'] or j.get('raid_line') != t['raid_line']:
        err(f, f"{w} crime_tier {j['crime_tier']}: raid_prob must be {t['raid_prob']} and raid_line {t['raid_line']}")
    if j.get('raid_skill') not in SK: err(f, f"{w} raid_skill must be a skill, got {j.get('raid_skill')}")
    if j.get('road') not in ROADS: err(f, f"{w} road must be one of {ROADS}")
    if 'earliest' in t and j['earliest'] < t['earliest']: err(f, f"{w} crime_tier 2 cannot start before {t['earliest']}")
    if 'latest_earliest' in t and j['earliest'] > t['latest_earliest']: err(f, f"{w} crime_tier 1 must be available by {t['latest_earliest']}")
# the unlocks in the calendar agree with jobs
for m in cal_['months']:
    want = sorted(j['id'] for j in jobs['jobs'] if j['earliest'] == m['month'])
    if sorted(m['job_unlocks']) != want: err('calendar.json', f"{m['month']} job_unlocks does not match jobs.json")
if not any(j['earliest'] == CAL_MONTHS[0] and not j.get('disabled') for j in jobs['jobs']): err(f, f'at least one job must be doable at the start ({CAL_MONTHS[0]})')
for j in jobs['jobs']:
    wt = j.get('wage_tiers')
    if wt is not None and (len(wt) != len(jobs['raise_tiers']) or not all(isinstance(x, int) for x in wt)): err(f, f"{j['id']} wage_tiers must be {len(jobs['raise_tiers'])} integers")
    for e in j['daily_effect']:
        for x in e.get('one_of', []):
            if x not in ATTRS and x not in SK: err(f, f"{j['id']} one_of stat does not exist {x}")
# rest / places / lifestyle
f = 'rest.json'
rest_ids = [r['id'] for r in rest['rests']]
if sorted(r['id'] for r in rest['rests'] if r.get('player_choice', True)) != ['rest_home', 'rest_outing']:
    err(f, 'the rests a player may pick must be exactly rest_home and rest_outing (user decision)')
for fo in rest['forced']:
    check_cond(f, fo['cond'], 'forced')
    for k in ('schedule','if_broke_switch'):
        if fo[k] not in rest_ids: err(f, f'forced {k} refers to a missing {fo[k]}')
    if fo.get('discharge_effect'): parse_effect(f, fo['discharge_effect'], 'forced discharge_effect')
    if fo.get('discharge_event'): ref_event(f, fo['discharge_event']['event'])
for r in rest['rests']:
    for k in ('daily_effect', 'period_effect'):
        if r.get(k): parse_effect(f, r[k], r['id'])
f = 'places.json'
for p in places['places']:
    need(f, p, ['id','name','fatigue_per_day','residents','random_table'], p.get('id'))
    if ('cost' in p) == ('cost_by_fame_tier' in p): err(f, f"{p.get('id')} needs cost or cost_by_fame_tier (only one of them)")
    if 'cost' in p and not (isinstance(p['cost'], int) and p['cost'] >= 0): err(f, f"{p['id']} cost")
    if 'cost_by_fame_tier' in p and (len(p['cost_by_fame_tier']) != 5 or not all(isinstance(x, int) for x in p['cost_by_fame_tier'])):
        err(f, f"{p['id']} cost_by_fame_tier must be 5 integers")
    if not (isinstance(p['fatigue_per_day'], int) and p['fatigue_per_day'] < 0): err(f, f"{p['id']} fatigue_per_day must be a negative integer")
    for n in p['residents']:
        if n not in NPC: err(f, f"{p['id']} NPC does not exist {n}")
f = 'lifestyle.json'
for l in life['lifestyles']:
    if len(l['monthly_cost']) != 5 or not all(isinstance(x, int) for x in l['monthly_cost']): err(f, f"{l['id']} monthly_cost")
    if l['month_end_effect']: parse_effect(f, l['month_end_effect'], l['id'])
if 'life_normal' not in {l['id'] for l in life['lifestyles']}: err(f, 'life_normal (the opening lifestyle) must be kept')
# street
f = 'street.json'
for e in street['entries']:
    need(f, e, ['id','name','shelf','services'], e.get('id'))
    for it in e['shelf']:
        if it in BOOK_IDS: continue
        if e['id'] == 'bookstore': err(f, f'bookstore shelf book does not exist {it}')
        else: ref_item(f, it)
    for s in e['services']:
        if 'effect' in s: parse_effect(f, s['effect'], s['id'])
        if 'cond' in s: check_cond(f, s['cond'], s['id'])
    if 'cond' in e: check_cond(f, e['cond'], e['id'])
# origins
f = 'origins.json'
ATTR_SET = set(ATTRS)
if len(origins['questions']) != 3 or not all(q['options'] for q in origins['questions']): err(f, 'origins must have 3 questions with at least one option each')
for qi, q in enumerate(origins['questions']):
    for o in q['options']:
        eff = parse_effect(f, o['effect'], o['text'])
        for t, n in o['tag_counts'].items():
            if t not in TAGS: err(f, f'{o["text"]} tag does not exist {t}')
        for it in o['items']: ref_item(f, it)
        base = sum((-v if k == 'crime' else v) for k, v in eff.items() if k in ATTR_SET and k not in ('fame','fatigue'))
        skl = sum(v for k, v in eff.items() if k in SK)
        if qi == 0:
            if abs(base) > 40: err(f, f'{o["text"]} question 1 attribute total {base} exceeds ±40 (crime counted as cost)')
            if skl > 20: err(f, f'{o["text"]} question 1 skill total {skl} exceeds +20')
        if qi == 1:
            if skl > 30: err(f, f'{o["text"]} question 2 skill total {skl} exceeds +30')
            if sum(o['tag_counts'].values()) > 2 or any(v > 1 for v in o['tag_counts'].values()): err(f, f'{o["text"]} tag counts over budget')
            if abs(eff.get('fame', 0)) > 30: err(f, f'{o["text"]} fame beyond ±30')
# calendar
f = 'calendar.json'
ms = cal_['months']
if len(ms) != 72: err(f, f'need 72 months (1924-01 to 1929-12), got {len(ms)}')
for m in ms:
    y, mo = map(int, m['month'].split('-'))
    nd = cal.monthrange(y, mo)[1]
    if m['days'] != nd: err(f, f"{m['month']} days")
    if m['sundays'] != [d for d in range(1, nd+1) if datetime.date(y, mo, d).weekday() == 6]: err(f, f"{m['month']} sundays")
    if m['periods'] != [[1,10],[11,20],[21,nd]]: err(f, f"{m['month']} periods")
    for e in m['era_events']: ref_event(f, e)
BS = roles.get('board_schedule', [])
if sorted(m['month'] for m in ms if m['board']) != sorted(x['month'] for x in BS): err(f, 'the board months must be exactly the months of roles.json board_schedule')
if sum(1 for m in ms if m['annual']) != 6: err(f, 'annual must be 6 times')
if sum(1 for m in ms if m['era_events']) != 7: err(f, 'era events must be 7 (GDD 11.3)')


# habits / rivals
f = 'habits.json'
if len(HABITS) != 6: err(f, 'habits must be 6')
f = 'rivals.json'
for r in rivals['named']:
    need(f, r, ['id','name','present','stages','habit','k'], r.get('id'))
    if r['habit'] not in HABITS: err(f, f"{r['id']} habit does not exist")
    if r['k'] not in (3,4,5): err(f, f"{r['id']} k")
    for a in r['stages']:
        if len(a['levels']) != 4: err(f, f"{r['id']} levels need 4 entries")
        if a['from'] not in CAL_MONTHS: err(f, f"{r['id']} stage month is not in the calendar {a['from']}")
    if r['stages'][0].get('fame') is None: err(f, f"{r['id']} first stage lacks fame")
    for m in r['present']:
        if m not in CAL_MONTHS: err(f, f"{r['id']} present month is not in the calendar")
for x in rivals['replace']:
    if x['old'] not in RIVALS or any(i not in RIVALS for i in x['new']): err(f, 'replace refers to a missing rival')
if not rivals['named']: err(f, 'need at least one named rival')
# roles
f = 'roles.json'
for t in roles['tags']: need(f, t, ['id','name'], t.get('id'))
if len(TAGS) != 16 or len(set(TAGS)) != 16: err(f, 'tags must have 16 entries with unique ids')
ROLE_IDS = [r['id'] for r in roles['roles']]
if len(set(ROLE_IDS)) != len(ROLE_IDS): err(f, 'duplicate id')
for r in roles['roles']:
    w = r['id']
    need(f, r, ['id','name','film_title','size','fame_gate','style_probs','wants','tags','opponents','bonus_skill','talkie','speech_line','fee','years_active'], w)
    if r['size'] not in ('small','medium','big'): err(f, f'{w} size')
    if r['style_probs'] is not None:
        p = r['style_probs']
        if len(p) != 4 or sum(p) != 100 or max(p) > 60 or min(p) < 5: err(f, f'{w} style_probs {p}')
    elif not r.get('style_rule'): err(f, f'{w} style_rule is required when style_probs is absent')
    if not 1 <= len(r['wants']) <= 3: err(f, f'{w} wants must have 1-3 entries')
    for k in r['wants']:
        if k['stat'] not in ATTRS and k['stat'] not in SK: err(f, f"{w} wants stat does not exist {k['stat']}")
    for t in r['tags']:
        if t not in TAGS: err(f, f'{w} tags {t}')
    if not 1 <= len(r['tags']) <= 2: err(f, f'{w} tags must have 1-2 entries')
    if r['bonus_skill'] not in SK: err(f, f'{w} bonus_skill')
    need_opp = 2 if r['size'] == 'big' and not r.get('tutorial') else 1
    if len(r['opponents']) != need_opp: err(f, f'{w} opponents must number {need_opp}')
    for o in r['opponents']:
        if 'named' in o and o['named'] not in RIVALS: err(f, f'{w} opponent does not exist {o}')
    if r['talkie'] and r['speech_line'] is None: err(f, f'{w} talkie roles need speech_line')
    if r['talkie'] not in (True, False, None): err(f, f'{w} talkie must be true/false/null')
# the rule blocks of step 6 in roles.json defaults
df = roles['defaults']
for k in ('board', 'talkie', 'shoot', 'release', 'placeholder_gen', 'script'):
    if k not in df: err(f, f'defaults is missing {k}')
if 'placeholder_gen' in df:
    pg = df['placeholder_gen']
    if sorted(pg['tags_by_color']) != sorted(ROADS): err(f, 'placeholder_gen tags_by_color needs four roads')
    for road, ts in pg['tags_by_color'].items():
        for t in ts:
            if t not in TAGS: err(f, f'placeholder_gen tags {t}')
    if pg['main_style'] + 3 * pg['other_style'] != 100: err(f, 'placeholder_gen style does not sum to 100')
if 'script' in df:
    for k in ('self_written', 'duv_written', 'co_written'): check_cond(f, df['script'][k]['cond'], 'script ' + k)
if 'release' in df:
    rl = df['release']
    for band in ('hit', 'normal', 'poor', 'flop'):
        for size in ('small', 'medium', 'big'):
            if not isinstance(rl.get('rep_table', {}).get(band, {}).get(size), int): err(f, f'release rep_table needs an integer {band}.{size}')
    if not (rl.get('flop_pct', 0) <= rl.get('fail_pct', -1) <= rl.get('hit_pct', 0)): err(f, 'release needs flop_pct <= fail_pct <= hit_pct')
if 'shoot' in df:
    for t in df['shoot']['stunt_self']['tags']:
        if t not in TAGS: err(f, f'stunt_self tags {t}')
    parse_effect(f, df['shoot']['stunt_self']['injury_effect'], 'stunt_self')
if 'board' in df:
    if not isinstance(df['board'].get('morals_months'), int): err(f, 'board is missing the integer field morals_months')
    for t in df['board']['after_valen_extra']['tags']:
        if t not in TAGS: err(f, f'tag {t} added after Valen dies')
# items
f = 'items.json'
if len(ITEM_NAMES) != len(items_t['items']): err(f, 'duplicate item id')
for i in items_t['items']:
    need(f, i, ['id','name','class','price','effect','slot','sellable'], i.get('id'))
    if i['class'] not in ('outfit','accessory','held','consumable','book'): err(f, f"{i['id']} class")
    if i['effect']: parse_effect(f, i['effect'], i['id'])
    if i['class'] in ('outfit','accessory') and i['slot'] != i['class']: err(f, f"{i['id']} slot must equal class")
# events
f = 'events.json'
eids = [e['id'] for e in events_t['events']]
if len(set(eids)) != len(eids): err(f, 'duplicate event id')
if set(eids) & {e['id'] for e in outing['events']}: err(f, 'events and outing share an id')
def check_prob(w, p):
    if p is None: return
    if isinstance(p, dict):
        if not (var_ok(p['numerator']) and isinstance(p['denominator'], int) and is_range(p['max'])): err(f, f'{w} prob formula')
    elif isinstance(p, list) and p and isinstance(p[0], dict):
        for x in p:
            check_cond(f, x['cond'], w + ' prob tiers')
            if not is_range(x['value']): err(f, f'{w} prob value')
        if p[-1]['cond'] != []: err(f, f'{w} the last prob tier must be the fallback (empty cond)')
    elif not is_range(p): err(f, f'{w} prob format {p}')
def check_check(w, c):
    if c is None: return
    if isinstance(c, dict):
        if c['check'] not in SK or not isinstance(c['line'], int): err(f, f'{w} dice check')
    elif isinstance(c, list):
        check_cond(f, [[c]], w + ' check')
for e in events_t['events']:
    w = e['id']
    need(f, e, ['id','name','class','timing','cond','prob','freq','effect','code','note','source','body'], w)
    check_cond(f, e['cond'], w); check_prob(w, e['prob'])
    if e['freq'] not in (None,'once_per_game','once_per_year','once_per_quarter'): err(f, f'{w} freq')
    if e['effect']: parse_effect(f, e['effect'], w)
    for o in e.get('options', []):
        if o.get('cond'): check_cond(f, o['cond'], w)
        for k in ('success_effect','fail_effect'):
            if o.get(k): parse_effect(f, o[k], w)
        check_check(w, o.get('check'))
    for b in e.get('branches', []):
        check_cond(f, b['cond'], w); 
        if b['effect']: parse_effect(f, b['effect'], w)
    if 'check' in e:
        check_check(w, e['check'])
        for k in ('success_effect','fail_effect'):
            if e[k]: parse_effect(f, e[k], w)
    if e['class'] == 'era' and e['timing'] not in CAL_MONTHS: err(f, f'{w} era event month is not in the calendar')
ERA = {e['id'] for e in events_t['events'] if e['class'] == 'era'}
if ERA != {x for m in cal_['months'] for x in m['era_events']}: err(f, 'era events do not match calendar.json')
# outing
f = 'outing.json'
for e in outing['events']:
    w = e['id']
    need(f, e, ['id','name','place','weight','cond','once','options','note','body'], w)
    if e['place'].startswith('place_') and e['place'] not in PLACES: err(f, f'{w} place does not exist')
    check_cond(f, e['cond'], w)
    for o in e['options']:
        check_check(w, o['check'])
        for k in ('success_effect','fail_effect'):
            if o[k]: parse_effect(f, o[k], w)
for p in places['places']:
    for r in p['random_table']:
        if r['event'] not in {e['id'] for e in outing['events']}: err('places.json', f"random_table event is not in outing.json: {r['event']}")
    if len(p['random_table']) < 1: err('places.json', f"{p['id']} random_table is empty")
# event budget (design/BALANCE_WORKFLOW.md, step 12c): every event has a tier; each option's effect stays inside the tier's caps
BUDGET = {
    'small':  {'attr': 5, 'skill': 3, 'money': 50, 'fatigue': 10, 'favor': 5, 'fame': 5, 'rep_bonus': 0, 'fame_pct': 0},
    'medium': {'attr': 15, 'skill': 8, 'money': 200, 'fatigue': 20, 'favor': 10, 'fame': 15, 'rep_bonus': 0, 'fame_pct': 0},
    'large':  {'attr': 30, 'skill': 16, 'money': 500, 'fatigue': 40, 'favor': 20, 'fame': 30, 'rep_bonus': 10, 'fame_pct': 10},
}
TIERS = list(BUDGET) + ['bad']
def effect_lines(e):
    """Every effect a player can end up with from one event: [(label, effect text), ...]. The event-level effect is added to each."""
    base = e.get('effect') or ''
    out = []
    if e.get('check'):
        out += [('success', base + ' ' + (e.get('success_effect') or '')), ('fail', base + ' ' + (e.get('fail_effect') or ''))]
    for i, b in enumerate(e.get('branches') or []):
        out.append((f'branch {i + 1}', base + ' ' + (b.get('effect') or '')))
    for i, o in enumerate(e.get('options') or []):
        for k in ('success_effect', 'fail_effect'):
            if o.get(k) is not None:
                out.append((f'option {i + 1} {k.split("_")[0]}', base + ' ' + (o.get(k) or '')))
    if not out:
        out.append(('effect', base))
    return out
def over_budget(tier, text):
    """The terms of one effect line that exceed the tier's caps: [message, ...]."""
    cap = BUDGET[tier]
    bad = []
    for tok in text.split():
        m = EFF.match(tok)
        if not m or tok.startswith('trigger.'): continue
        n, op, v, pct = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        if op == '=': continue
        if pct:
            kind = 'fame_pct' if n == 'fame' else None
        elif n in ('fatigue', 'fame', 'money'): kind = n
        elif n in ATTRS: kind = 'attr'
        elif n in SK: kind = 'skill'
        elif n.startswith('favor.'): kind = 'favor'
        elif n.startswith('rep_bonus.'): kind = 'rep_bonus'
        else: continue
        if kind is None or v > cap[kind]: bad.append(f'{tok} (cap {cap.get(kind, 0)}{"%" if pct else ""})')
    return bad
budget_notes = []
for fname, evs_ in (('events.json', events_t['events']), ('outing.json', outing['events'])):
    for e in evs_:
        t = e.get('tier')
        if t not in TIERS: err(fname, f"{e['id']} tier must be one of {TIERS}, got {t}"); continue
        if e.get('budget_note'): budget_notes.append(f"{e['id']} ({t}): {e['budget_note']}")
        if t == 'bad' or e.get('budget_note'): continue
        for label, text in effect_lines(e):
            b = over_budget(t, text)
            if b: err(fname, f"{e['id']} tier {t} {label} is over budget: {', '.join(b)}. Lower it, pick a bigger tier, or add budget_note with the reason")
for n_ in budget_notes: notes.append('budget_note ' + n_)
# romance / schedule / chains
f = 'romance.json'
if len(NPC) != len(romance['npcs']): err(f, 'duplicate NPC')
for n in romance['npcs']:
    if n.get('destiny_cond'): check_cond(f, n['destiny_cond'], n['id'])
f = 'npc_schedule.json'
for s_ in npc_sched['schedule']:
    if s_['npc'] not in NPC: err(f, f"NPC does not exist {s_['npc']}")
    if s_['place'] is not None and s_['place'] not in PLACES: err(f, f"place does not exist {s_['place']}")
    for m in s_['months']:
        if not 1 <= m <= 12: err(f, 'months')
    for x in s_['periods']:
        if x not in ('early', 'mid', 'late'): err(f, 'periods')
    check_cond(f, s_['cond'], s_['npc'])
for p in places['places']:
    for n in p['residents']:
        if not any(x['npc'] == n for x in npc_sched['schedule']): notes.append(f"{n} is resident at {p['id']} in places.json but npc_schedule.json has no schedule for him (GDD 5.5.2 does not list one), so he will not show up as a present NPC")
        elif not any(x['npc'] == n and x['place'] == p['id'] for x in npc_sched['schedule']): err(f, f"{n} is resident at {p['id']} but the schedule place differs")
f = 'npc_chains.json'
CH = {c['id'] for c in chains['chains']}
for c in chains['chains']:
    if c['npc'] not in NPC: err(f, f"NPC does not exist {c['npc']}")
    for e in c['chain'] + [x['event'] for x in c['resident']]:
        if e not in EVENT_IDS: err(f, f'event does not exist {e}')
for c in classes['classes']:
    ch = c.get('story_chain')
    if ch and ch['chain'] not in CH: err('classes.json', f"story_chain does not exist {ch['chain']}")
# annual / opportunities
f = 'annual.json'
if annual.get('attend_effect'): parse_effect(f, annual['attend_effect'], 'attend_effect')
if len(annual['occasions']) != 4 or {x['road'] for x in annual['occasions']} != set(ROADS): err(f, 'annual needs exactly one occasion per road')
f = 'opportunities.json'
for o in opps['opportunities']:
    need(f, o, ['id','name','road','cond','monthly_prob','story','effect'], o.get('id'))
    if o['road'] not in ROADS: err(f, f"{o['id']} road")
    check_cond(f, o['cond'], o['id']); parse_effect(f, o['effect'], o['id'])
    if o['story'] not in EVENT_IDS: err(f, f"{o['id']} story does not exist")
    if o['monthly_prob'] is not None and not is_range(o['monthly_prob']): err(f, f"{o['id']} prob")
# endings
f = 'endings.json'
for e in endings['forced'] + endings['special']: check_cond(f, e['cond'], e['id'])
for c in endings['categories']: check_cond(f, c['cond'], c['id'])
big = [c['id'] for c in endings['categories']]
by = {}
for e in endings['endings']:
    need(f, e, ['id','name','category','order','cond','content','body'], e.get('id'))
    check_cond(f, e['cond'], e['id'])
    if e['category'] not in big: err(f, f"{e['id']} category does not exist")
    by.setdefault(e['category'], []).append(e)
fam_tags = [t for v in endings['tag_families'].values() for t in v]
if sorted(fam_tags) != sorted(TAGS): err(f, 'tag_families must cover exactly the 16 content tags')
for b in big:
    lst = sorted(by.get(b, []), key=lambda x: x['order'])
    if not lst: err(f, f'{b} has no endings'); continue
    if lst[-1]['cond'] != []: err(f, f'{b} the last ending must be the fallback (empty cond)')
    if [x['order'] for x in lst] != sorted({x['order'] for x in lst}) and len({x['order'] for x in lst}) != len(lst): err(f, f'{b} duplicate order')
if pending_items: notes.append(f'{len(pending_items)} item references wait for the step-3 check: {sorted(pending_items)}')
if pending_events: notes.append(f'{len(pending_events)} event references wait for the step-3 check')
for n in notes: print('note: ' + n)
if errs:
    print('\n'.join(errs)); print(f'failed: {len(errs)} problems'); sys.exit(1)
# status traits
f = 'traits.json'
TR = T['traits']
seen = set()
for x in TR['traits']:
    w = x.get('id')
    need(f, x, ['id', 'name', 'body', 'cond', 'effects'], w)
    if w in seen: err(f, f'duplicate id {w}')
    seen.add(w)
    check_cond(f, x.get('cond', []), w)
    for e in x.get('effects', []):
        if e not in TR['effects_allowed']: err(f, f'{w} effect not allowed: {e} (allowed: {TR["effects_allowed"]})')
# fixed boards (roles.json board_schedule, reserve_pool, gates)
f = 'roles.json'
RD = {r['id']: r for r in roles['roles']}
for x in roles.get('board_schedule', []):
    if x['month'] not in CAL_MONTHS: err(f, f"board_schedule month is not in the calendar {x['month']}")
    for t in ('big', 'medium', 'small', 'small2'):
        if t == 'small2' and t not in x: continue
        r = RD.get(x.get(t))
        if r is None: err(f, f"board_schedule {x['month']} {t} role does not exist {x.get(t)}")
        elif r['size'] != t.rstrip('2'): err(f, f"board_schedule {x['month']} {t} role {r['id']} is size {r['size']}")
for rid in roles.get('reserve_pool', []):
    r = RD.get(rid)
    if r is None: err(f, f'reserve_pool role does not exist {rid}')
    elif r['size'] not in ('small', 'medium'): err(f, f'reserve_pool role {rid} must be small or medium')
for r in roles['roles']:
    if 'gates' in r: check_cond(f, r['gates'], r['id'] + ' gates')
if not isinstance(roles['defaults']['board'].get('connections_extra'), int): err(f, 'defaults.board needs the integer connections_extra')
# map (the places on the map and what each offers)
f = 'map.json'
seen = set()
for L in map_t['locations']:
    w = L.get('id')
    need(f, L, ['id','name','hint','pos','size','entries','shops','activities','extra'], w)
    if w in seen: err(f, f'duplicate id {w}')
    seen.add(w)
    for e in L['entries']:
        base, _, place = e.partition('@')
        if base not in CLASS_IDS and base not in JOB_IDS and base not in rest_ids: err(f, f'{w} entry does not exist {e}')
        if place and place not in [p['id'] for p in places['places']]: err(f, f'{w} outing place does not exist {place}')
    for sh in L['shops']:
        if sh not in [x['id'] for x in street['entries']]: err(f, f'{w} shop does not exist {sh}')
    if L['extra'] not in (None, 'home', 'city', 'studio'): err(f, f'{w} extra must be null, home, city or studio')
on = [j['id'] for j in jobs['jobs'] if not j.get('disabled')] + [c['id'] for c in classes['classes'] if not c.get('disabled')]
placed = {e for L in map_t['locations'] for e in L['entries']}
for x in on:
    if x not in placed: err(f, f'{x} is switched on but on no place of the map')
print(f'passed: {len(FILES)} tables, {len(JOB_IDS)} jobs, {len(CLASS_IDS)} classes, {len(BOOK_IDS)} books, {len(ms)} months')
