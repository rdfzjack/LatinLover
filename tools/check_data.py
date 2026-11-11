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

FILES = ['stats','skills','classes','books','jobs','rest','places','lifestyle','street','origins','calendar',
         'habits','rivals','roles','items','events','outing','romance','npc_schedule','npc_chains','annual','opportunities','endings']
T = {}
for n in FILES:
    T[n] = load(n + '.json')
    if T[n] is None: err(n + '.json', '文件不存在'); continue
    no_float(T[n], n + '.json')
if errs:
    print('\n'.join(errs)); sys.exit(1)

stats, skills, classes, books, jobs, rest, places, life, street, origins, cal_ = (T[n] for n in FILES[:11])
habits, rivals, roles, items_t, events_t, outing, romance, npc_sched, chains, annual, opps, endings = (T[n] for n in FILES[11:])
ATTRS = [a['名字'] for a in stats['基础属性']]
SK = [s['名字'] for s in skills['技能']]
ROADS = [r['名字'] for r in stats['声望']]
CLASS_IDS = [c['id'] for c in classes['课']]
JOB_IDS = [j['id'] for j in jobs['工']]
BOOK_IDS = [b['id'] for b in books['书']]
CAL_MONTHS = [m['月'] for m in cal_['月']]
TAGS = ['西部','动作冒险','战争','古装','浪漫','异国情人','歌舞','喜剧','悲情','文艺','宗教','贵族','反派','犯罪','恐怖','地下片','低成本制作']

# 登记表
NPC = {n['名字'] for n in romance['npc']}
ITEM_NAMES = {i['id'] for i in items_t['物品']}
EVENT_IDS = {e['id'] for e in events_t['事件']} | {e['id'] for e in outing['事件']}
HABITS = {h['id'] for h in habits['习惯']}
RIVALS = {r['id'] for r in rivals['有名']}
PLACES = {p['id'] for p in places['地点']}
pending_items, pending_events = set(), set()
def ref_item(f, n):
    if ITEM_NAMES is None: pending_items.add(n)
    elif n not in ITEM_NAMES: err(f, f'物品不存在 {n}')
def ref_event(f, e):
    if e is None: return
    if EVENT_IDS is None: pending_events.add(e)
    elif e not in EVENT_IDS: err(f, f'事件不存在 {e}')

DERIVED = {'最高声望','月份','年份','药瘾阶段','负债月数','档次','最大标签族','无法定义','低成本定型','有声片部数',
           '最高基础属性','手腕最高技能','最大工期数','四路声望极差','最高声望所在路'}
PREFIX = ('状态.','计数.','标签.','期数.','旗标.','交手次数.')
def var_ok(v):
    if v in ATTRS or v in SK or v in ROADS or v in DERIVED or v in ('金钱','生病指数','失控指数','日期'): return True
    if v.startswith('好感.'): return v[3:] in NPC
    if v.startswith('成功期数.'): return v[5:] in JOB_IDS
    if v.startswith('旬数.'): return v[3:] in CLASS_IDS
    if v.startswith('期数.'): return v[3:] in ROADS
    return v.startswith(PREFIX) and len(v) > 3
COMP = ('>=','<=','>','<','==','!=','in')
def check_cond(f, c, where=''):
    if not isinstance(c, list): err(f, f'{where} 条件不是列表'); return
    for g in c:
        if not isinstance(g, list): err(f, f'{where} 条件组不是列表'); continue
        for t in g:
            if not (isinstance(t, list) and len(t) == 3): err(f, f'{where} 条件项格式 {t}'); continue
            if not var_ok(t[0]): err(f, f'{where} 条件变量不存在 {t[0]}')
            if t[1] not in COMP: err(f, f'{where} 比较符 {t[1]}')
            if t[1] == 'in':
                if not isinstance(t[2], list): err(f, f'{where} in 的值要是列表')
            elif isinstance(t[2], str) and t[2].startswith('@'):
                if not var_ok(t[2][1:]): err(f, f'{where} 引用的变量不存在 {t[2]}')
            elif not isinstance(t[2], (int, str)): err(f, f'{where} 条件值 {t[2]}')
EFF = re.compile(r'^(.+?)([+\-=])(\d+)(%?)$')
def eff_name_ok(n):
    if n in ATTRS or n in SK or n in ('金钱','药瘾阶段','负债月数'): return True
    if n.startswith('好感.'): return n[3:] in NPC
    if n.startswith('修正.'): return n[3:] in ROADS
    if n.startswith('权重.'): return n[3:] in TAGS
    if n.startswith('物品.'): return n[3:] in ITEM_NAMES
    return n.startswith(('状态.','旗标.')) and len(n) > 3
def parse_effect(f, s, where=''):
    """返回 {名字: 累计增量}，只含 +/- 的整数项；%、= 和 触发 只检查格式"""
    out = {}
    for tok in s.split():
        if tok.startswith('触发.'):
            ref_event(f, tok[3:]); continue
        m = EFF.match(tok)
        if not m: err(f, f'{where} 效果项格式 {tok}'); continue
        n, op, v, pct = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        if not eff_name_ok(n): err(f, f'{where} 效果名字不存在 {n}'); continue
        if op != '=' and not pct: out[n] = out.get(n, 0) + (v if op == '+' else -v)
    return out
def is_range(r): return isinstance(r, list) and len(r) == 2 and all(isinstance(x, int) for x in r) and r[0] <= r[1]

# stats
f = 'stats.json'
for a in stats['基础属性']: need(f, a, ['id','名字','范围','初值'], a.get('名字'))
if len(ATTRS) != 8: err(f, '基础属性应为 8 项')
if len(stats['名气档']) != 5: err(f, '名气档应为 5 档')
if stats['等级']['门槛'] != [5*l*(l+1) for l in range(10)]: err(f, '等级门槛与 5L(L+1) 不符')
for k in ('月衰减百分比', '月衰减最少'):
    if not isinstance(stats['名气规则'].get(k), int): err(f, f'名气规则缺整数字段 {k}')
# skills
f = 'skills.json'
if len(SK) != 12 or len(set(SK)) != 12: err(f, '技能应为 12 项且不重名')
for s in skills['技能']:
    need(f, s, ['名字','路','训练范围','初值','固定用途'], s.get('名字'))
    if s['路'] not in ROADS: err(f, f"{s['名字']} 路不存在 {s['路']}")
for r in stats['声望']:
    if [s['名字'] for s in skills['技能'] if s['路'] == r['名字']] != r['技能']: err('stats.json', f"声望 {r['名字']} 的技能与 skills.json 不一致")
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
    for c in j.get('成功线修正', []):
        check_cond(f, c['条件'], w + ' 成功线修正')
        if c['项'] not in [x['项'] for x in j['成功线']]: err(f, f"{w} 成功线修正的项不在成功线里 {c['项']}")
        if not isinstance(c['值'], int): err(f, f'{w} 成功线修正的值')
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
if sum(1 for m in ms if m['时代事件']) != 7: err(f, '时代节点应 7 个（GDD 11.3）')


# habits / rivals
f = 'habits.json'
if len(HABITS) != 6: err(f, '习惯应 6 种')
f = 'rivals.json'
for r in rivals['有名']:
    need(f, r, ['id','名字','在场','阶段','习惯','k'], r.get('id'))
    if r['习惯'] not in HABITS: err(f, f"{r['id']} 习惯不存在")
    if r['k'] not in (3,4,5): err(f, f"{r['id']} k")
    for a in r['阶段']:
        if len(a['等级']) != 4: err(f, f"{r['id']} 等级需 4 项")
        if a['自'] not in CAL_MONTHS: err(f, f"{r['id']} 阶段月不在日历内 {a['自']}")
    if r['阶段'][0].get('名气') is None: err(f, f"{r['id']} 首阶段缺名气")
    for m in r['在场']:
        if m not in CAL_MONTHS: err(f, f"{r['id']} 在场月不在日历内")
for x in rivals['替换']:
    if x['原'] not in RIVALS or any(i not in RIVALS for i in x['改为']): err(f, '替换引用不存在')
if len(rivals['有名']) != 9: err(f, '有名对手应 9 个')
# roles
f = 'roles.json'
ROLE_IDS = [r['id'] for r in roles['角色']]
if len(set(ROLE_IDS)) != len(ROLE_IDS): err(f, 'id 重复')
for r in roles['角色']:
    w = r['id']
    need(f, r, ['id','名字','片名','档次','名气门槛','场风概率','看重','标签','对手','加分技能','有声','谈吐线','片酬','出现年份'], w)
    if r['档次'] not in ('小','中','大'): err(f, f'{w} 档次')
    if r['场风概率'] is not None:
        p = r['场风概率']
        if len(p) != 4 or sum(p) != 100 or max(p) > 60 or min(p) < 5: err(f, f'{w} 场风概率 {p}')
    elif not r.get('场风规则'): err(f, f'{w} 无场风概率时要写场风规则')
    if not 1 <= len(r['看重']) <= 3: err(f, f'{w} 看重应 1-3 项')
    for k in r['看重']:
        if k['项'] not in ATTRS and k['项'] not in SK: err(f, f"{w} 看重项不存在 {k['项']}")
    for t in r['标签']:
        if t not in TAGS or t == '低成本制作': err(f, f'{w} 标签 {t}')
    if not 1 <= len(r['标签']) <= 2: err(f, f'{w} 标签应 1-2 个')
    if r['加分技能'] not in SK: err(f, f'{w} 加分技能')
    need_opp = 2 if r['档次'] == '大' and not r.get('教学') else 1
    if len(r['对手']) != need_opp: err(f, f'{w} 对手数应为 {need_opp}')
    for o in r['对手']:
        if '有名' in o and o['有名'] not in RIVALS: err(f, f'{w} 对手不存在 {o}')
    if r['有声'] and r['谈吐线'] is None: err(f, f'{w} 有声角色要有谈吐线')
    if r['有声'] not in (True, False, None): err(f, f'{w} 有声应为 true/false/null')
# roles.json 默认里第 6 步用的规则块
df = roles['默认']
for k in ('选片板', '有声', '拍摄', '上映', '占位生成', '剧本'):
    if k not in df: err(f, f'默认 缺 {k}')
if '占位生成' in df:
    pg = df['占位生成']
    if sorted(pg['标签按主色']) != sorted(ROADS): err(f, '占位生成 标签按主色 要四条路')
    for road, ts in pg['标签按主色'].items():
        for t in ts:
            if t not in TAGS or t == '低成本制作': err(f, f'占位生成 标签 {t}')
    if pg['主色场风'] + 3 * pg['其余场风'] != 100: err(f, '占位生成 场风和不是 100')
if '剧本' in df:
    for k in ('自己写', 'Duv写', '合写'): check_cond(f, df['剧本'][k]['条件'], '剧本 ' + k)
if '拍摄' in df:
    for t in df['拍摄']['亲自上']['标签']:
        if t not in TAGS: err(f, f'亲自上 标签 {t}')
    parse_effect(f, df['拍摄']['亲自上']['受伤效果'], '亲自上')
if '选片板' in df:
    for t in df['选片板']['瓦伦去世后多一个']['标签']:
        if t not in TAGS: err(f, f'瓦伦去世后 标签 {t}')
# items
f = 'items.json'
if len(ITEM_NAMES) != len(items_t['物品']): err(f, '物品 id 重复')
for i in items_t['物品']:
    need(f, i, ['id','名字','类','价格','效果','槽','出售'], i.get('id'))
    if i['类'] not in ('服装','配饰','持有','消耗','书'): err(f, f"{i['id']} 类")
    if i['效果']: parse_effect(f, i['效果'], i['id'])
    if i['类'] in ('服装','配饰') and i['槽'] != i['类']: err(f, f"{i['id']} 槽应等于类")
# events
f = 'events.json'
eids = [e['id'] for e in events_t['事件']]
if len(set(eids)) != len(eids): err(f, '事件 id 重复')
if set(eids) & {e['id'] for e in outing['事件']}: err(f, 'events 与 outing 的 id 重复')
def check_prob(w, p):
    if p is None: return
    if isinstance(p, dict):
        if not (var_ok(p['分子']) and isinstance(p['分母'], int) and is_range(p['上限'])): err(f, f'{w} 概率公式')
    elif isinstance(p, list) and p and isinstance(p[0], dict):
        for x in p:
            check_cond(f, x['条件'], w + ' 概率分档')
            if not is_range(x['值']): err(f, f'{w} 概率值')
        if p[-1]['条件'] != []: err(f, f'{w} 概率分档最后一档应是兜底（条件空）')
    elif not is_range(p): err(f, f'{w} 概率格式 {p}')
def check_check(w, c):
    if c is None: return
    if isinstance(c, dict):
        if c['判定'] not in SK or not isinstance(c['线'], int): err(f, f'{w} 掷骰判定')
    elif isinstance(c, list):
        check_cond(f, [[c]], w + ' 判定')
for e in events_t['事件']:
    w = e['id']
    need(f, e, ['id','名字','类','时机','条件','概率','频次','效果','代码','说明','来源','文本'], w)
    check_cond(f, e['条件'], w); check_prob(w, e['概率'])
    if e['频次'] not in (None,'每局一次','每年一次','每季度一次'): err(f, f'{w} 频次')
    if e['效果']: parse_effect(f, e['效果'], w)
    for o in e.get('选项', []):
        if o.get('条件'): check_cond(f, o['条件'], w)
        for k in ('成功效果','失败效果'):
            if o.get(k): parse_effect(f, o[k], w)
        check_check(w, o.get('判定'))
    for b in e.get('分支', []):
        check_cond(f, b['条件'], w); 
        if b['效果']: parse_effect(f, b['效果'], w)
    if '判定' in e:
        check_check(w, e['判定'])
        for k in ('成功效果','失败效果'):
            if e[k]: parse_effect(f, e[k], w)
    if e['类'] == '时代' and e['时机'] not in CAL_MONTHS: err(f, f'{w} 时代事件月份不在日历内')
ERA = {e['id'] for e in events_t['事件'] if e['类'] == '时代'}
if ERA != {x for m in cal_['月'] for x in m['时代事件']}: err(f, '时代事件与 calendar.json 不一致')
# outing
f = 'outing.json'
for e in outing['事件']:
    w = e['id']
    need(f, e, ['id','名字','地点','权重','条件','一次性','选项','说明','文本'], w)
    if e['地点'].startswith('place_') and e['地点'] not in PLACES: err(f, f'{w} 地点不存在')
    check_cond(f, e['条件'], w)
    for o in e['选项']:
        check_check(w, o['判定'])
        for k in ('成功效果','失败效果'):
            if o[k]: parse_effect(f, o[k], w)
rt_ids = [r['事件'] for p in places['地点'] for r in p['随机表']]
for p in places['地点']:
    for r in p['随机表']:
        if r['事件'] not in {e['id'] for e in outing['事件']}: err('places.json', f"随机表事件不在 outing.json: {r['事件']}")
    if len(p['随机表']) < 1: err('places.json', f"{p['id']} 随机表为空")
if len(rt_ids) != 8: err('places.json', f'随机表事件应共 8 个，现 {len(rt_ids)}')
for i in rest['休息']:
    for e in i.get('事件表', []):
        if e not in EVENT_IDS: err('rest.json', f'度假事件不存在 {e}')
# romance / schedule / chains
f = 'romance.json'
if len(NPC) != len(romance['npc']): err(f, 'NPC 重名')
for n in romance['npc']:
    if n.get('归宿条件'): check_cond(f, n['归宿条件'], n['名字'])
f = 'npc_schedule.json'
for s_ in npc_sched['日程']:
    if s_['npc'] not in NPC: err(f, f"NPC 不存在 {s_['npc']}")
    if s_['地点'] is not None and s_['地点'] not in PLACES: err(f, f"地点不存在 {s_['地点']}")
    for m in s_['月份']:
        if not 1 <= m <= 12: err(f, '月份')
    for x in s_['旬']:
        if x not in ('上','中','下'): err(f, '旬')
    check_cond(f, s_['条件'], s_['npc'])
for p in places['地点']:
    for n in p['常在的人']:
        if not any(x['npc'] == n for x in npc_sched['日程']): notes.append(f"{n} 在 places.json 常在 {p['id']}，但 npc_schedule.json 没有他的日程（GDD 5.5.2 的日程表没写），不会作为在场 NPC 出现")
        elif not any(x['npc'] == n and x['地点'] == p['id'] for x in npc_sched['日程']): err(f, f"{n} 常在 {p['id']} 但日程地点不一致")
f = 'npc_chains.json'
CH = {c['id'] for c in chains['链']}
for c in chains['链']:
    if c['npc'] not in NPC: err(f, f"NPC 不存在 {c['npc']}")
    for e in c['链'] + [x['事件'] for x in c['常驻']]:
        if e not in EVENT_IDS: err(f, f'事件不存在 {e}')
for c in classes['课']:
    ch = c.get('剧情链')
    if ch and ch['链'] not in CH: err('classes.json', f"剧情链不存在 {ch['链']}")
# annual / opportunities
f = 'annual.json'
if len(annual['场合']) != 4 or {x['路'] for x in annual['场合']} != set(ROADS): err(f, '年度大事应四路各一个')
f = 'opportunities.json'
for o in opps['机遇']:
    need(f, o, ['id','名字','路','条件','每月概率','剧情','效果'], o.get('id'))
    if o['路'] not in ROADS: err(f, f"{o['id']} 路")
    check_cond(f, o['条件'], o['id']); parse_effect(f, o['效果'], o['id'])
    if o['剧情'] not in EVENT_IDS: err(f, f"{o['id']} 剧情不存在")
    if o['每月概率'] is not None and not is_range(o['每月概率']): err(f, f"{o['id']} 概率")
# endings
f = 'endings.json'
for e in endings['强制'] + endings['特殊']: check_cond(f, e['条件'], e['id'])
for c in endings['大类']: check_cond(f, c['条件'], c['名字'])
big = [c['名字'] for c in endings['大类']]
by = {}
for e in endings['结局']:
    need(f, e, ['id','名字','大类','顺序','条件','内容','文本'], e.get('id'))
    check_cond(f, e['条件'], e['id'])
    if e['大类'] not in big: err(f, f"{e['id']} 大类不存在")
    by.setdefault(e['大类'], []).append(e)
fam_tags = [t for v in endings['标签族'].values() for t in v]
if sorted(fam_tags) != sorted(t for t in TAGS if t != '低成本制作'): err(f, '标签族没有恰好覆盖 16 个内容标签')
for b in big:
    lst = sorted(by.get(b, []), key=lambda x: x['顺序'])
    if not lst: err(f, f'{b} 没有结局'); continue
    if lst[-1]['条件'] != []: err(f, f'{b} 最后一条应是兜底（条件空）')
    if [x['顺序'] for x in lst] != sorted({x['顺序'] for x in lst}) and len({x['顺序'] for x in lst}) != len(lst): err(f, f'{b} 顺序重复')
if len(endings['结局']) + len(endings['强制']) + len(endings['特殊']) < 36: err(f, '结局应不少于 36 个')
non_actor = sum(1 for e in endings['结局'] if e['大类'] != '演员')
if non_actor * 2 <= len(endings['结局']): err(f, '非演员结局应过半')
if pending_items: notes.append(f'待第 3 步校验的物品引用 {len(pending_items)} 个：{sorted(pending_items)}')
if pending_events: notes.append(f'待第 3 步校验的事件引用 {len(pending_events)} 个')
for n in notes: print('注：' + n)
if errs:
    print('\n'.join(errs)); print(f'失败：{len(errs)} 处'); sys.exit(1)
print(f'通过：{len(FILES)} 个表，{len(JOB_IDS)} 种工、{len(CLASS_IDS)} 门课、{len(BOOK_IDS)} 本书、{len(ms)} 个月')
