extends RefCounted
## Interpreter for conditions, effects, checks and probabilities. Port of sim/rules.py.
## Syntax: data/new/README.md, GDD 11.0 and 16. All functions are static; st is an instance of core/state.gd.

static var _cache := {}
static var _re: RegEx = null

## Derived values for the endings (grade, top tag family ...): name -> Callable(st). Filled in when step 6 is ported (step 12).
static var extra_vars := {}


## Integer division truncating toward zero (GDD 0). GDScript int / int already truncates.
static func tdiv(a: int, b: int) -> int:
	return a / b


## Integer division rounding down, like Python's //.
static func fdiv(a: int, b: int) -> int:
	var q := a / b
	if (a % b != 0) and ((a < 0) != (b < 0)):
		q -= 1
	return q


## 'favor.sil' -> ["favor", "sil"]; a name without a prefix gives [name, ""]. Always split at the first '.', never slice by length.
static func split_name(name: String) -> Array:
	var i := name.find(".")
	if i < 0:
		return [name, ""]
	return [name.substr(0, i), name.substr(i + 1)]


# ---------- effects ----------

## 'stamina+20 discipline-15 trigger.evt_x' -> [[name, sign, number, is_percent]];
## a trigger is returned as ["trigger", "evt_x", 0, ""].
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
	for ws in ["\t", "\n", "\r", "\u3000"]:
		norm = norm.replace(ws, " ")
	for tok in norm.split(" ", false):
		var hr := split_name(tok)
		if hr[0] == "trigger" and hr[1] != "":
			out.append(["trigger", hr[1], 0, ""])
			continue
		var m := _re.search(tok)
		if m == null:
			push_error("bad effect term: %s" % tok)
			continue
		out.append([m.get_string(1), m.get_string(2), m.get_string(3).to_int(), m.get_string(4)])
	_cache[text] = out
	return out


## Returns the new value. A percentage is taken of the current value, truncating toward zero.
static func _delta(cur: int, op: String, n: int, pct: String) -> int:
	if op == "=":
		return n
	var v := tdiv(cur * n, 100) if pct != "" else n
	return cur + v if op == "+" else cur - v


static func _clampi(v: int, lo: int, hi: int) -> int:
	return lo if v < lo else (hi if v > hi else v)


## Applies one effect line and returns the ids of the events to trigger next.
## source "event" (events, item use ...) and "opportunity": a positive favor gain is +1 more when loyalty >= 200 (GDD 10.1);
## "schedule" (fixed per-period or per-period favor in schedules), "origin" and "annual" do not get the bonus.
## Step 12c: the change of every attribute, skill, money and rep_bonus is added to st.src[source] (report only).
static func apply_effect(st, text, source := "event") -> Array:
	var trig := []
	var d = st.d
	for e in parse_effect(text):
		var n: String = e[0]
		var op: String = e[1]
		var v: int = e[2]
		var pct: String = e[3]
		var hr := split_name(n)
		var head: String = hr[0]
		var k: String = hr[1]
		if n == "trigger":
			trig.append(op)
		elif st.attr.has(n):
			var rg: Array = d.attr_range[n]
			var old: int = st.attr[n]
			st.attr[n] = _clampi(_delta(st.attr[n], op, v, pct), rg[0], rg[1])
			st.track(source, n, st.attr[n] - old)
			if n == "fame":
				if st.note_ctx.is_empty():
					st.fame_note(st.attr[n] - old, "effect_" + source)
				else:
					st.fame_note(st.attr[n] - old, str(st.note_ctx["why"]), str(st.note_ctx["arg"]))
		elif st.skill.has(n):
			var rg: Array = d.skill_range[n]
			var old: int = st.skill[n]
			st.skill[n] = _clampi(_delta(st.skill[n], op, v, pct), rg[0], rg[1])
			st.track(source, n, st.skill[n] - old)
		elif n == "money":
			var old: int = st.money
			st.money = clampi(_delta(st.money, op, v, pct), 0, d.money_cap)    # six-year swap: money never goes below 0
			st.track(source, n, st.money - old)
			if st.money > old:
				st.src["income"] = st.src.get("income", 0) + st.money - old
		elif n == "drug_points":
			st.drug_points = maxi(0, _delta(st.drug_points, op, v, pct))
		elif n == "drug_stage":
			st.drug = _clampi(_delta(st.drug, op, v, pct), 0, 3)
		elif n == "debt_months":
			st.debt_months = maxi(0, _delta(st.debt_months, op, v, pct))
		elif head == "favor":
			var cur: int = st.favor.get(k, 0)
			var nv := _delta(cur, op, v, pct)
			if (source == "event" or source == "opportunity") and nv > cur and st.val("loyalty") >= 200:
				nv += 1
			st.favor[k] = _clampi(nv, 0, 100)
		elif head == "rep_bonus":
			var old: int = st.corr[k]
			st.corr[k] = _delta(st.corr[k], op, v, pct)
			st.track(source, n, st.corr[k] - old)
		elif head == "weight":
			st.weights[k] = _delta(st.weights.get(k, 0), op, v, pct)
		elif head == "item":
			if op == "=" and v == 0:
				remove_item(st, k)
			else:
				st.items.append(k)
		elif head == "status":
			var nv := _delta(st.status.get(k, 0), op, v, pct)
			if k == "in_love" and nv != 0 and not st.status.get("in_love", 0):
				st.romance_months = 0
			st.status[k] = nv
		elif head == "flag":
			st.flags[k] = _delta(st.flags.get(k, 0), op, v, pct)
		else:
			push_error("unknown effect name: %s" % n)
	return trig


static func remove_item(st, iid: String) -> bool:
	if not st.items.has(iid):
		return false
	st.items.erase(iid)   # removes the first one, like Python list.remove
	if not st.items.has(iid):
		if st.equip["outfit"] == iid:
			st.equip["outfit"] = null
		if st.equip["accessory"].has(iid):
			st.equip["accessory"].erase(iid)
	return true


# ---------- variables ----------

static func get_var(st, name: String):
	var d = st.d
	if st.attr.has(name) or st.skill.has(name):
		return st.val(name)
	if st.corr.has(name):
		return st.rep(name)
	if name == "money":
		return st.money
	if st.idx.has(name):
		return st.idx[name]
	if name == "date":
		return st.date()
	if name == "month":
		return st.date().substr(5).to_int()
	if name == "year":
		return st.date().substr(0, 4).to_int()
	if name == "max_rep":
		var b: Dictionary = st.bonus()
		var best = null
		for r in d.roads:
			var x: int = st.rep(r, b)
			if best == null or x > best:
				best = x
		return best
	if name == "top_road":
		var b: Dictionary = st.bonus()
		var best_r = null
		var best := 0
		for r in d.roads:     # a tie goes to the earlier road
			var x: int = st.rep(r, b)
			if best_r == null or x > best:
				best_r = r
				best = x
		return best_r
	if name == "rep_spread":
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
	if name == "drug_stage":
		return st.drug
	if name == "drug_points":
		return st.drug_points
	if name == "debt_months":
		return st.debt_months
	if name == "top_base_attr":
		return st.highest_base()
	if name == "top_savvy_skill":
		var b: Dictionary = st.bonus()
		var best_s = null
		var best := 0
		for s in d.road_skills["savvy"]:
			var x: int = st.val(s, b)
			if best_s == null or x > best:
				best_s = s
				best = x
		return best_s
	if name == "max_job_periods":
		var m := 0
		for j in d.jobs:
			m = maxi(m, st.cnt("job_periods." + j))
		return m
	if name == "talkie_count":
		return st.cnt("count.talkie_count")
	var hr := split_name(name)
	var head: String = hr[0]
	var k: String = hr[1]
	if head == "favor":
		return st.favor.get(k, 0)
	if head == "flag":
		return st.flags.get(k, 0)
	if head == "status":
		if k == "wrap_up":
			return 1 if st.month().get("wrap_up", false) else 0
		return st.status.get(k, 0)
	if head == "tag":
		return st.tags.get(k, 0)
	if head in ["job_periods", "class_periods", "road_periods", "count", "duels"]:
		return st.cnt(name)
	if extra_vars.has(name):
		return extra_vars[name].call(st)
	push_error("condition variable unknown or not implemented: %s" % name)
	return null


## In Python, == between an int and a str is False; GDScript raises an error, so compare the types first.
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
		push_error("the two sides have different types: %s %s %s" % [a, op, b])
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
	push_error("unknown comparator: %s" % op)
	return false


static func test(st, term: Array) -> bool:
	var var_name: String = term[0]
	var op: String = term[1]
	var val = term[2]
	var a = get_var(st, var_name)
	if typeof(val) == TYPE_STRING and val.begins_with("@"):
		val = get_var(st, val.substr(1))
	return _cmp(a, op, val)


## [[term, ...], ...]: the outer list is OR, the inner list is AND; [] is always true.
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


# ---------- checks (GDD 11.0) ----------

## A gate [variable, comparator, value], or a dice check {check: skill, line: n}
## (displayed skill value + r0(20) >= n). null always succeeds.
static func check(st, c) -> bool:
	if c == null:
		return true
	if typeof(c) == TYPE_DICTIONARY:
		return st.val(c["check"]) + st.rng.logic.r0(20) >= c["line"]
	return test(st, c)


# ---------- probabilities ----------

## null always; [numerator, denominator]; a tiered list [{cond, value}] takes the first that holds;
## {numerator: variable, denominator: n, max: [p, q]}.
static func prob(st, p) -> bool:
	var g = st.rng.logic
	if p == null:
		return true
	if typeof(p) == TYPE_DICTIONARY:
		var num: int = get_var(st, p["numerator"])
		var den: int = p["denominator"]
		var cp: int = p["max"][0]
		var cq: int = p["max"][1]
		# min(num/den, cp/cq) over the common denominator den*cq
		return g.chance(mini(num * cq, cp * den), den * cq)
	if p.size() > 0 and typeof(p[0]) == TYPE_DICTIONARY:
		for x in p:
			if cond(st, x["cond"]):
				return g.chance(x["value"][0], x["value"][1])
		return false
	return g.chance(p[0], p[1])
