"""校验 data/new/*.json。用法：python3 tools/check_data.py
检查：字段齐全、没有小数、引用的属性/技能/课/书/工/NPC存在、条件和效果能解析、开局预算、日历。
事件、物品、NPC 表（第 3 步）存在时才校验对应引用，否则只统计。"""
import json, os, re, sys, datetime, calendar as cal
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'new')
errs, notes = [], []
def err(f, m): errs.append(f'{f}: {m}')
def load(n):
    p = os.path.join(D, n)
    if not os.path.exists(p): return None
    with open(p, encoding='utf-8') as fh: return json.load(fh)
def no_float(o, f, path=''):
    if isinstance(o, float): err(f, f'小数 {path}={o}')
    elif isinstance(o, dict):
        for k, v in o.items(): no_float(v, f, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o): no_float(v, f, f'{path}[{i}]')
def need(f, d, keys, where=''):
    for k in keys:
        if k not in d: err(f, f'{where} 缺字段 {k}')

FILES = ['stats','skills','classes','books','jobs','rest','places','lifestyle','street','origins','calendar']
T = {}
for n in FILES:
    T[n] = load(n + '.json')
    if T[n] is None: err(n + '.json', '文件不存在'); continue
    no_float(T[n], n + '.json')
if errs:
    print('\n'.join(errs)); sys.exit(1)

stats, skills, classes, books, jobs, rest, places, life, street, origins, cal_ = (T[n] for n in FILES)
ATTRS = [a['名字'] for a in stats['基础属性']]
SK = [s['名字'] for s in skills['技能']]
ROADS = [r['名字'] for r in stats['声望']]
CLASS_IDS = [c['id'] for c in classes['课']]
JOB_IDS = [j['id'] for j in jobs['工']]
BOOK_IDS = [b['id'] for b in books['书']]
CAL_MONTHS = [m['月'] for m in cal_['月']]
TAGS = ['西部','动作冒险','战争','古装','浪漫','异国情人','歌舞','喜剧','悲情','文艺','宗教','贵族','反派','犯罪','恐怖','地下片','低成本制作']

# NPC 登记：有 romance.json 用它，否则用基础名单
romance = load('romance.json')
NPC = {'Sil','Duv','女明星','同乡工头','神父','画家','酒吧老板','片厂老板','编辑','富婆','动作片导演','第四人'}
if romance is not None:
    names = romance.get('npc') or romance.get('NPC') or romance.get('功能NPC')
    if names: NPC = {n if isinstance(n, str) else n.get('名字') for n in names}
items_t = load('items.json'); events_t = load('events.json')
ITEM_NAMES = None
if items_t is not None:
    lst = items_t.get('物品', items_t) if isinstance(items_t, dict) else items_t
    ITEM_NAMES = {i.get('名字') or i.get('id') for i in lst} | {i.get('id') for i in lst}
EVENT_IDS = None
if events_t is not None:
    lst = events_t.get('事件', events_t) if isinstance(events_t, dict) else events_t
    EVENT_IDS = {e.get('id') for e in lst}
pending_items, pending_events = set(), set()
def ref_item(f, n):
    if ITEM_NAMES is None: pending_items.add(n)
    elif n not in ITEM_NAMES: err(f, f'物品不存在 {n}')
def ref_event(f, e):
    if e is None: return
    if EVENT_IDS is None: pending_events.add(e)
    elif e not in EVENT_IDS: err(f, f'事件不存在 {e}')

def var_ok(v):
    if v in ATTRS or v in SK or v in ('金钱','生病指数','失控指数','日期'): return True
    if v.startswith('好感.'): return v[3:] in NPC
    if v.startswith('成功期数.'): return v[5:] in JOB_IDS
    if v.startswith('旬数.'): return v[3:] in CLASS_IDS
    if v.startswith('旗标.'): return len(v) > 3
    return False
def check_cond(f, c, where=''):
    if not isinstance(c, list): err(f, f'{where} 条件不是列表'); return
    for g in c:
        if not isinstance(g, list): err(f, f'{where} 条件组不是列表'); continue
        for t in g:
            if not (isinstance(t, list) and len(t) == 3): err(f, f'{where} 条件项格式 {t}'); continue
            if not var_ok(t[0]): err(f, f'{where} 条件变量不存在 {t[0]}')
            if t[1] not in ('>=','<=','>','<','==','!='): err(f, f'{where} 比较符 {t[1]}')
            if not isinstance(t[2], (int, str)): err(f, f'{where} 条件值 {t[2]}')
TOK = re.compile(r'^(.+?)([+-])(\d+)$')
def parse_effect(f, s, where=''):
    out = {}
    for tok in s.split():
        m = TOK.match(tok)
        if not m: err(f, f'{where} 效果项格式 {tok}'); continue
        n, sg, v = m.group(1), m.group(2), int(m.group(3))
        if not var_ok(n) or n in ('生病指数','失控指数','日期') or n.startswith(('成功期数','旬数','旗标')):
            err(f, f'{where} 效果名字不存在 {n}')
        out[n] = out.get(n, 0) + (v if sg == '+' else -v)
    return out
def is_range(r): return isinstance(r, list) and len(r) == 2 and all(isinstance(x, int) for x in r) and r[0] <= r[1]

# stats
f = 'stats.json'
for a in stats['基础属性']: need(f, a, ['id','名字','范围','初值'], a.get('名字'))
if len(ATTRS) != 8: err(f, '基础属性应为 8 项')
if len(stats['名气档']) != 5: err(f, '名气档应为 5 档')
if stats['等级']['门槛'] != [5*l*(l+1) for l in range(10)]: err(f, '等级门槛与 5L(L+1) 不符')
# skills
f = 'skills.json'
if len(SK) != 12 or len(set(SK)) != 12: err(f, '技能应为 12 项且不重名')
for s in skills['技能']:
    need(f, s, ['名字','路','训练范围','初值','固定用途'], s.get('名字'))
    if s['路'] not in ROADS: err(f, f"{s['名字']} 路不存在 {s['路']}")
for r in stats['声望']:
    if [s['名字'] for s in skills['技能'] if s['路'] == r['名字']] != r['技能']: err('stats.json', f"声望 {r['名字']} 的技能与 skills.json 不一致")
init = {s['名字']: s['初值'] for s in skills['技能']}
for r, want in (('情人',50),('硬汉',25),('手腕',20),('文化',10)):
    got = sum(init[s] for s in next(x for x in stats['声望'] if x['名字']==r)['技能'])
    if got != want: err('stats.json', f'开局声望 {r} = {got}，GDD 3.1 是 {want}')
# classes
f = 'classes.json'
for c in classes['课']:
    need(f, c, ['id','名字','学费','收益'], c.get('id'))
    if len(c['学费']) != 4: err(f, f"{c['id']} 学费应 4 档")
    for e in c['收益']:
        if e['项'] not in SK and e['项'] not in ATTRS: err(f, f"{c['id']} 收益项不存在 {e['项']}")
        if len(e['各级']) != 4 or not all(is_range(r) for r in e['各级']): err(f, f"{c['id']} {e['项']} 各级格式")
        if '条件' in e: check_cond(f, e['条件'], c['id'])
    if '每旬效果' in c: parse_effect(f, c['每旬效果'], c['id'])
    if 'Duv' in c.get('剧情链', {}).values() and 'Duv' not in NPC: err(f, 'Duv 不在 NPC 表')
# books
f = 'books.json'
tiers = {t['档']: t for t in books['档']}
for b in books['书']:
    need(f, b, ['id','名字','技能','档','教育门槛','技能上限','点数','收益','价格','读完事件'], b.get('id'))
    if b['技能'] not in SK: err(f, f"{b['id']} 技能不存在")
    t = tiers.get(b['档'])
    if not t: err(f, f"{b['id']} 档不存在"); continue
    for k in ('教育门槛','技能上限','点数','收益','价格'):
        if b[k] != t[k]: err(f, f"{b['id']} {k} 与档表不符")
    ref_event(f, b['读完事件'])
if len(set(BOOK_IDS)) != len(BOOK_IDS): err(f, 'id 重复')
if len(BOOK_IDS) != 15: err(f, f'书应为 15 本，现 {len(BOOK_IDS)}')
for s in ('打斗','骑马驾驶','胆识','体态','人脉'):
    if any(b['技能'] == s for b in books['书']): err(f, f'{s} 不应有书')
# jobs
f = 'jobs.json'
if len(JOB_IDS) != 15 or len(set(JOB_IDS)) != 15: err(f, '工应为 15 种且 id 不重复')
ev_ids = []
for j in jobs['工']:
    w = j['id']
    need(f, j, ['id','名字','最早时间','前置','日薪','成功线','每天效果','曝光','npc','每期效果','每期随机','里程碑'], w)
    if j['最早时间'] not in CAL_MONTHS: err(f, f'{w} 最早时间不在日历内')
    if not isinstance(j['日薪'], int): err(f, f'{w} 日薪不是整数')
    check_cond(f, j['前置'], w + ' 前置')
    for c in j['成功线']:
        if c['项'] not in ATTRS and c['项'] not in SK: err(f, f"{w} 成功线项不存在 {c['项']}")
    for e in j['每天效果']:
        if e['项'] not in ATTRS and e['项'] not in SK: err(f, f"{w} 每天效果项不存在 {e['项']}")
        if not is_range(e['加']): err(f, f'{w} 每天效果范围')
    if j['npc'] and j['npc'] not in NPC: err(f, f"{w} NPC 不存在 {j['npc']}")
    if j['每期效果']: parse_effect(f, j['每期效果'], w)
    for r in j['每期随机']:
        if not (is_range(r['概率']) and r['概率'][0] >= 1): err(f, f'{w} 概率格式')
        ev_ids.append(r['事件']); ref_event(f, r['事件'])
    for m in j['里程碑']:
        check_cond(f, m['条件'], w + ' 里程碑'); ev_ids.append(m['事件']); ref_event(f, m['事件'])
if len(set(ev_ids)) != len(ev_ids): err(f, '事件 id 重复')
# 日历里的解锁与 jobs 一致
for m in cal_['月']:
    want = sorted(j['id'] for j in jobs['工'] if j['最早时间'] == m['月'])
    if sorted(m['打工解锁']) != want: err('calendar.json', f"{m['月']} 打工解锁与 jobs.json 不一致")
if sum(1 for j in jobs['工'] if j['最早时间'] == '1926-01') != 6: err(f, '开局应有 6 种工')
# rest / places / lifestyle
f = 'rest.json'
rest_ids = [r['id'] for r in rest['休息']]
if len(rest_ids) != 5: err(f, '休息应 5 项')
for fo in rest['强制']:
    check_cond(f, fo['条件'], '强制')
    for k in ('日程','钱不够改'):
        if fo[k] not in rest_ids: err(f, f'强制 {k} 引用不存在 {fo[k]}')
for r in rest['休息']:
    if r['id'] == 'rest_escort': parse_effect(f, r['每天效果'] + ' ' + r['每旬效果'], r['id'])
f = 'places.json'
for p in places['地点']:
    need(f, p, ['id','名字','花费','常在的人','随机表'], p.get('id'))
    for n in p['常在的人']:
        if n not in NPC: err(f, f"{p['id']} NPC 不存在 {n}")
    for e in p['随机表']: ref_event(f, e)
f = 'lifestyle.json'
for l in life['生活方式']:
    if len(l['月费']) != 5 or not all(isinstance(x, int) for x in l['月费']): err(f, f"{l['id']} 月费")
    if l['月结效果']: parse_effect(f, l['月结效果'], l['id'])
if len(life['生活方式']) != 4: err(f, '生活方式应 4 种')
# street
f = 'street.json'
for e in street['入口']:
    need(f, e, ['名字','货架','服务'], e.get('名字'))
    for it in e['货架']:
        if it in BOOK_IDS: continue
        if e['名字'] == '书店': err(f, f'书店货架书不存在 {it}')
        else: ref_item(f, it)
    for s in e['服务']:
        if 'price' in s: err(f, 'price')
        if '效果' in s: parse_effect(f, s['效果'], s['名字'])
        if '条件' in s: check_cond(f, s['条件'], s['名字'])
    if '条件' in e: check_cond(f, e['条件'], e['名字'])
# origins
f = 'origins.json'
ATTR_SET = set(ATTRS)
if [len(q['选项']) for q in origins['问']] != [5,4,6]: err(f, '三问的选项数应为 5/4/6')
for qi, q in enumerate(origins['问']):
    for o in q['选项']:
        eff = parse_effect(f, o['效果'], o['文字'])
        for t, n in o['标签计数'].items():
            if t not in TAGS: err(f, f'{o["文字"]} 标签不存在 {t}')
        for it in o['物品']: ref_item(f, it)
        base = sum((-v if k == '犯罪' else v) for k, v in eff.items() if k in ATTR_SET and k not in ('名气','疲劳'))
        skl = sum(v for k, v in eff.items() if k in SK)
        if qi == 0:
            if abs(base) > 40: err(f, f'{o["文字"]} 第一问基础属性合计 {base} 超出 ±40（犯罪按代价算）')
            if skl > 20: err(f, f'{o["文字"]} 第一问技能合计 {skl} 超过 +20')
        if qi == 1:
            if skl > 30: err(f, f'{o["文字"]} 第二问技能合计 {skl} 超过 +30')
            if sum(o['标签计数'].values()) > 2 or any(v > 1 for v in o['标签计数'].values()): err(f, f'{o["文字"]} 标签计数超预算')
            if abs(eff.get('名气', 0)) > 30: err(f, f'{o["文字"]} 名气超 ±30')
# calendar
f = 'calendar.json'
ms = cal_['月']
if len(ms) != 48: err(f, f'应 48 个月，现 {len(ms)}')
for m in ms:
    y, mo = map(int, m['月'].split('-'))
    nd = cal.monthrange(y, mo)[1]
    if m['天数'] != nd: err(f, f"{m['月']} 天数")
    if m['周日'] != [d for d in range(1, nd+1) if datetime.date(y, mo, d).weekday() == 6]: err(f, f"{m['月']} 周日")
    if m['旬'] != [[1,10],[11,20],[21,nd]]: err(f, f"{m['月']} 旬")
    for e in m['时代事件']: ref_event(f, e)
if sum(1 for m in ms if m['选片板']) != 16: err(f, '选片板应 16 次')
if sum(1 for m in ms if m['年度大事']) != 4: err(f, '年度大事应 4 次')
if sum(1 for m in ms if m['时代事件']) != 8: err(f, '时代节点应 8 个')

if pending_items: notes.append(f'待第 3 步校验的物品引用 {len(pending_items)} 个：{sorted(pending_items)}')
if pending_events: notes.append(f'待第 3 步校验的事件引用 {len(pending_events)} 个')
for n in notes: print('注：' + n)
if errs:
    print('\n'.join(errs)); print(f'失败：{len(errs)} 处'); sys.exit(1)
print(f'通过：{len(FILES)} 个表，{len(JOB_IDS)} 种工、{len(CLASS_IDS)} 门课、{len(BOOK_IDS)} 本书、{len(ms)} 个月')
