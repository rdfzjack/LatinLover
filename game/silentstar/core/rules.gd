extends RefCounted
## 条件、效果、判定、概率的解释器。照抄 sim/rules.py。语法见 data/new/README.md，GDD 11.0、16。
## 函数都是静态的，st 是 core/state.gd 的实例。

static var _cache := {}
static var _re: RegEx = null

## 第 6 步登记结局用的派生值（档次、最大标签族…）：名字 -> Callable(st)。第 12 步移植时填。
static var extra_vars := {}


## 向零截断的整数除法（GDD 0）。GDScript 的 int / int 本来就向零截断。
static func tdiv(a: int, b: int) -> int:
	return a / b


## 向下取整的整数除法，同 Python 的 //。
static func fdiv(a: int, b: int) -> int:
	var q := a / b
	if (a % b != 0) and ((a < 0) != (b < 0)):
		q -= 1
	return q


# ---------- 效果 ----------

## '体力+20 自律-15 触发.evt_x' -> [[名字, 符号, 数, 是否百分比]]；触发写成 ['触发', 'evt_x', 0, '']。
static func parse_effect(text) -> Array:
	if text == null:
		text = ""
	if _cache.has(text):
		return _cache[text]
	if _re == null:
		_re = RegEx.new()
		_re.compile("^([^+\\-=]+)([+\\-=])(\\d+)(%?)$")
	var out := []
	var norm: String = text
	for ws in ["\t", "\n", "\r", "　"]:
		norm = norm.replace(ws, " ")
	for tok in norm.split(" ", false):
		if tok.begins_with("触发."):
			out.append(["触发", tok.substr(3), 0, ""])
			continue
		var m := _re.search(tok)
		if m == null:
			push_error("效果项格式错误：%s" % tok)
			continue
		out.append([m.get_string(1), m.get_string(2), m.get_string(3).to_int(), m.get_string(4)])
	_cache[text] = out
	return out


## 返回新值。百分比按当前值算，向零截断。
static func _delta(cur: int, op: String, n: int, pct: String) -> int:
	if op == "=":
		return n
	var v := tdiv(cur * n, 100) if pct != "" else n
	return cur + v if op == "+" else cur - v


static func _clampi(v: int, lo: int, hi: int) -> int:
	return lo if v < lo else (hi if v > hi else v)


## 执行一行效果，返回要接着触发的事件 id 列表。
## source：'event'（事件、机遇、物品使用等）时，好感正增量在义气 ≥200 时多 1（GDD 10.1）；
## 'schedule'（日程里每旬、每期固定的好感）和 'origin' 不加。
static func apply_effect(st, text, source := "event") -> Array:
	var trig := []
	var d = st.d
	for e in parse_effect(text):
		var n: String = e[0]
		var op: String = e[1]
		var v: int = e[2]
		var pct: String = e[3]
		if n == "触发":
			trig.append(op)
		elif st.attr.has(n):
			var rg: Array = d.attr_range[n]
			st.attr[n] = _clampi(_delta(st.attr[n], op, v, pct), rg[0], rg[1])
		elif st.skill.has(n):
			var rg: Array = d.skill_range[n]
			st.skill[n] = _clampi(_delta(st.skill[n], op, v, pct), rg[0], rg[1])
		elif n == "金钱":
			st.money = mini(_delta(st.money, op, v, pct), d.money_cap)
		elif n == "药瘾阶段":
			st.drug = _clampi(_delta(st.drug, op, v, pct), 0, 3)
		elif n == "负债月数":
			st.debt_months = maxi(0, _delta(st.debt_months, op, v, pct))
		elif n.begins_with("好感."):
			var k := n.substr(3)
			var cur: int = st.favor.get(k, 0)
			var nv := _delta(cur, op, v, pct)
			if source == "event" and nv > cur and st.val("义气") >= 200:
				nv += 1
			st.favor[k] = _clampi(nv, 0, 100)
		elif n.begins_with("修正."):
			var k := n.substr(3)
			st.corr[k] = _delta(st.corr[k], op, v, pct)
		elif n.begins_with("权重."):
			var k := n.substr(3)
			st.weights[k] = _delta(st.weights.get(k, 0), op, v, pct)
		elif n.begins_with("物品."):
			var k := n.substr(3)
			if op == "=" and v == 0:
				remove_item(st, k)
			else:
				st.items.append(k)
		elif n.begins_with("状态."):
			var k := n.substr(3)
			var nv := _delta(st.status.get(k, 0), op, v, pct)
			if k == "恋爱" and nv != 0 and not st.status.get("恋爱", 0):
				st.romance_months = 0
			st.status[k] = nv
		elif n.begins_with("旗标."):
			var k := n.substr(3)
			st.flags[k] = _delta(st.flags.get(k, 0), op, v, pct)
		else:
			push_error("效果名字未知：%s" % n)
	return trig


static func remove_item(st, iid: String) -> bool:
	if not st.items.has(iid):
		return false
	st.items.erase(iid)   # 去掉第一个，同 Python list.remove
	if not st.items.has(iid):
		if st.equip["服装"] == iid:
			st.equip["服装"] = null
		if st.equip["配饰"].has(iid):
			st.equip["配饰"].erase(iid)
	return true


# ---------- 变量 ----------

static func get_var(st, name: String):
	var d = st.d
	if st.attr.has(name) or st.skill.has(name):
		return st.val(name)
	if st.corr.has(name):
		return st.rep(name)
	if name == "金钱":
		return st.money
	if st.idx.has(name):
		return st.idx[name]
	if name == "日期":
		return st.date()
	if name == "月份":
		return st.date().substr(5).to_int()
	if name == "年份":
		return st.date().substr(0, 4).to_int()
	if name == "最高声望":
		var b: Dictionary = st.bonus()
		var best = null
		for r in d.roads:
			var x: int = st.rep(r, b)
			if best == null or x > best:
				best = x
		return best
	if name == "最高声望所在路":
		var b: Dictionary = st.bonus()
		var best_r = null
		var best := 0
		for r in d.roads:     # 并列取靠前的
			var x: int = st.rep(r, b)
			if best_r == null or x > best:
				best_r = r
				best = x
		return best_r
	if name == "四路声望极差":
		var b: Dictionary = st.bonus()
		var lo = null
		var hi = null
		for r in d.roads:
			var x: int = st.rep(r, b)
			if lo == null or x < lo:
				lo = x
			if hi == null or x > hi:
				hi = x
		return hi - lo
	if name == "药瘾阶段":
		return st.drug
	if name == "负债月数":
		return st.debt_months
	if name == "最高基础属性":
		return st.highest_base()
	if name == "手腕最高技能":
		var b: Dictionary = st.bonus()
		var best_s = null
		var best := 0
		for s in d.road_skills["手腕"]:
			var x: int = st.val(s, b)
			if best_s == null or x > best:
				best_s = s
				best = x
		return best_s
	if name == "最大工期数":
		var m := 0
		for j in d.jobs:
			m = maxi(m, st.cnt("成功期数." + j))
		return m
	if name == "有声片部数":
		return st.cnt("计数.有声片部数")
	if name.begins_with("好感."):
		return st.favor.get(name.substr(3), 0)
	if name.begins_with("旗标."):
		return st.flags.get(name.substr(3), 0)
	if name.begins_with("状态."):
		var k := name.substr(3)
		if k == "收尾期":
			return 1 if st.month().get("收尾期", false) else 0
		return st.status.get(k, 0)
	if name.begins_with("标签."):
		return st.tags.get(name.substr(3), 0)
	for p in ["成功期数.", "旬数.", "期数.", "计数.", "交手次数."]:
		if name.begins_with(p):
			return st.cnt(name)
	if extra_vars.has(name):
		return extra_vars[name].call(st)
	push_error("条件变量未知或还没实现：%s" % name)
	return null


## Python 里 int 和 str 用 == 比较得 False；GDScript 会报错，所以先比类型。
static func _same_kind(a, b) -> bool:
	var ta := typeof(a)
	var tb := typeof(b)
	var num := [TYPE_INT, TYPE_FLOAT, TYPE_BOOL]
	if ta in num and tb in num:
		return true
	return ta == tb


static func _cmp(a, op: String, b) -> bool:
	match op:
		"==":
			return _same_kind(a, b) and a == b
		"!=":
			return not (_same_kind(a, b) and a == b)
		"in":
			for x in b:
				if _same_kind(a, x) and a == x:
					return true
			return false
	if not _same_kind(a, b):
		push_error("比较的两边类型不同：%s %s %s" % [a, op, b])
		return false
	match op:
		">=":
			return a >= b
		"<=":
			return a <= b
		">":
			return a > b
		"<":
			return a < b
	push_error("比较符未知：%s" % op)
	return false


static func test(st, term: Array) -> bool:
	var var_name: String = term[0]
	var op: String = term[1]
	var val = term[2]
	var a = get_var(st, var_name)
	if typeof(val) == TYPE_STRING and val.begins_with("@"):
		val = get_var(st, val.substr(1))
	return _cmp(a, op, val)


## [[项,…],…]：外层或、组内与；[] 恒真。
static func cond(st, c) -> bool:
	if c == null or c.is_empty():
		return true
	for g in c:
		var all_ok := true
		for t in g:
			if not test(st, t):
				all_ok = false
				break
		if all_ok:
			return true
	return false


# ---------- 判定（GDD 11.0） ----------

## 门槛 [变量, 比较符, 值]，或掷骰 {判定: 技能, 线: n}（技能显示值 + r0(20) >= n）。null 为必然成功。
static func check(st, c) -> bool:
	if c == null:
		return true
	if typeof(c) == TYPE_DICTIONARY:
		return st.val(c["判定"]) + st.rng.logic.r0(20) >= c["线"]
	return test(st, c)


# ---------- 概率 ----------

## null 必然；[分子,分母]；分档 [{条件,值}] 取第一个满足的；{分子:变量,分母:n,上限:[p,q]}。
static func prob(st, p) -> bool:
	var g = st.rng.logic
	if p == null:
		return true
	if typeof(p) == TYPE_DICTIONARY:
		var num: int = get_var(st, p["分子"])
		var den: int = p["分母"]
		var cp: int = p["上限"][0]
		var cq: int = p["上限"][1]
		# min(num/den, cp/cq) 化成同分母 den*cq
		return g.chance(mini(num * cq, cp * den), den * cq)
	if p.size() > 0 and typeof(p[0]) == TYPE_DICTIONARY:
		for x in p:
			if cond(st, x["条件"]):
				return g.chance(x["值"][0], x["值"][1])
		return false
	return g.chance(p[0], p[1])
