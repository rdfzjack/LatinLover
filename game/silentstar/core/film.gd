extends RefCounted
## Film contracts, shooting, breaches, releases (GDD 5.6, 8, 10 breach when very sick). Port of sim/film.py.
## Numbers are in roles.json defaults.shoot / defaults.release.
##
## One film contract (an entry of st.story["films"]):
##   {id, roles: role snapshot, size, support, stunt_self, locks: [[month index, period], ...], shoot_days, ok_days,
##    perf, fee, status, release, result}
## status: to_shoot -> shooting -> to_release -> released; plus breached (very sick, missing etc.) and stolen (lost a steal role).
##
## Random-number order (copied from the Python side): on each shooting day first r0(fatigue), then in_love and reckless slacking
## per Schedule.extra_fail; with stunt_self the injury 1/40 is rolled last. Releases roll no random numbers.
## All functions are static; st is an instance of core/state.gd.

const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")


static func shoot_cfg(d) -> Dictionary:
	return d.role_cfg["shoot"]


static func rel_cfg(d) -> Dictionary:
	return d.role_cfg["release"]


static func films(st) -> Array:
	return st.story["films"]


# ---------- tags ----------

## Typed content tags (count >= typed_line), in table order.
static func typecast_tags(st) -> Array:
	var line: int = rel_cfg(st.d)["typed_line"]
	var out := []
	for t in st.d.content_tags:
		if st.tags.get(t, 0) >= line:
			out.append(t)
	return out


## Low-budget typed: lowbudget count >= 4 (released when the count drops to 3 or below, so no extra state is kept). Returns 0/1.
static func low_budget(st) -> int:
	return 1 if st.cnt("count.lowbudget") >= rel_cfg(st.d)["lowbudget"]["typed_line"] else 0


## Undefined: at least 6 content tags have a count and none is typed (8.4). Returns 0/1.
static func undefined(st) -> int:
	var have := 0
	for t in st.d.content_tags:
		if st.tags.get(t, 0) > 0:
			have += 1
	return 1 if have >= rel_cfg(st.d)["undefined_kinds"] and typecast_tags(st).is_empty() else 0


# ---------- film contracts ----------

static func new_film(st, role: Dictionary, locks: Array, support := false, personally := false) -> Dictionary:
	st.story["seq"] += 1
	var lk := []
	for x in locks:
		lk.append(x.duplicate())
	var f := {"id": "film%d" % st.story["seq"], "roles": role, "size": role["size"], "support": support,
		"stunt_self": personally, "locks": lk, "shoot_days": 0, "ok_days": 0,
		"perf": null, "fee": null, "status": "to_shoot", "release": null, "result": null}
	films(st).append(f)
	update_status(st)
	return f


## The role won from the board locks the first periods of next month (small 1, medium 2, big 3; support -1, at least 1).
static func board_locks(st, tier: String, support := false) -> Array:
	var n: int = st.d.role_cfg["shoot_periods"][tier]
	if support:
		var x: Dictionary = st.d.t["habits"]["audition"]["result"]["narrow_loss"]
		n = maxi(x["shoot_periods_min"], n - x["shoot_periods_cut"])
	var out := []
	for k in n:
		out.append([st.ym + 1, k])
	return out


static func next_period(st, i: int) -> Array:
	return [st.ym, i + 1] if i < 2 else [st.ym + 1, 0]


static func _active(f: Dictionary) -> bool:
	return f["status"] == "to_shoot" or f["status"] == "shooting"


static func _has_lock(f: Dictionary, ym: int, i: int) -> bool:
	for x in f["locks"]:
		if x[0] == ym and x[1] == i:
			return true
	return false


static func is_locked(st, ym: int, i: int) -> bool:
	for f in films(st):
		if _active(f) and _has_lock(f, ym, i):
			return true
	return false


## The film contract that locks period i of this month, or null.
static func locked(st, i: int):
	for f in films(st):
		if _active(f) and _has_lock(f, st.ym, i):
			return f
	return null


static func update_status(st) -> void:
	var v := 0
	for f in films(st):
		if f["status"] == "to_shoot":
			v = 1
	st.status["has_pending_role"] = v


## stunt_self: the role has any of the western, action_adventure, war tags and nerve >= 60 (50 after 4 periods of stunt double).
static func can_go_personally(st, role: Dictionary) -> bool:
	var c: Dictionary = shoot_cfg(st.d)["stunt_self"]
	var hit := false
	for t in role["tags"]:
		if c["tags"].has(t):
			hit = true
	if not hit:
		return false
	var line: int = c["nerve_line"]
	if Schedule.truthy(st.flags.get(c["nerve_line_flag"]["flags"])):
		line = c["nerve_line_flag"]["line"]
	return st.val("nerve") >= line


# ---------- shooting ----------

## One shooting period. After the last period it pays the fee, computes the performance and fixes the release month.
static func shoot(st, i: int, f: Dictionary, days: Array) -> void:
	var d = st.d
	var c := shoot_cfg(d)
	var g = st.rng.logic
	var t: String = f["size"]
	f["status"] = "shooting"
	update_status(st)
	if int(st.status.get("drug_high", 0)) == 2:     # a divine dose on a shooting period (GDD 5.8.1)
		f["divine"] = 1
	for dd in days:
		if dd[1]:
			continue
		f["shoot_days"] += 1
		st.exposed = 1
		Schedule.add_stat(st, "fatigue", c["fatigue"][t])
		var b: Dictionary = st.bonus()
		var ok: bool = st.val("stamina", b) - g.r0(st.val("fatigue", b)) >= c["success_lines"][t]
		if Schedule.extra_fail(st, true):
			ok = false
		var dg := Schedule.drug_day(st)      # the dose of this period (GDD 5.8.1)
		if dg != 0:
			ok = dg > 0
		if ok:
			f["ok_days"] += 1
		if f["stunt_self"]:
			var p: Array = c["stunt_self"]["injury_prob"]
			if g.chance(p[0], p[1]):
				Rules.apply_effect(st, c["stunt_self"]["injury_effect"], "schedule")
				st.inc("count.injury")
	var last: Array = f["locks"][f["locks"].size() - 1]
	if last[0] == st.ym and last[1] == i:
		finish(st, f)


## P x1000: 500 + ok_days x 500 / shoot_days + bonus skill x 2 (stunt_self +100), clamped to 500-1200; a divine dose adds on top.
static func performance(st, f: Dictionary) -> int:
	var c := shoot_cfg(st.d)
	var days: int = f["shoot_days"]
	var p: int = c["perf_min"] + (Rules.fdiv(f["ok_days"] * 500, days) if days else 500)
	p += Rules.fdiv(st.val(f["roles"]["bonus_skill"]) * 1000, 500)
	if f["stunt_self"]:
		p += c["stunt_self"]["perf_add"]
	p = maxi(c["perf_min"], mini(c["perf_max"], p))
	if f.get("divine", 0):      # a divine dose on a shooting period goes above the usual top (GDD 5.8.1)
		p += int(st.d.t["stats"]["drug"]["divine_perf_add"])
	return p


## Fee = base x (stunt_self 130%) x (support 40%) x (400+negotiation)/400 x contract coefficient, rounded down at each step.
static func fee(st, f: Dictionary) -> int:
	var d = st.d
	var c := shoot_cfg(d)
	var v: int = f["roles"]["fee"]
	if f["stunt_self"]:
		v = Rules.fdiv(v * c["stunt_self"]["fee_pct"], 100)
	if f["support"]:
		v = Rules.fdiv(v * d.t["habits"]["audition"]["result"]["narrow_loss"]["fee_pct"], 100)
	v = Rules.fdiv(v * (c["negotiation_div"] + st.val("negotiation")), c["negotiation_div"])
	var k: Dictionary = d.contract
	if st.val("education") < k["education_below"] and not Rules.cond(st, k["exempt_cond"]):
		v = Rules.fdiv(v * k["fee_coef_pct"], 100)
	return v


static func finish(st, f: Dictionary) -> void:
	f["perf"] = performance(st, f)
	f["fee"] = fee(st, f)
	st.add_money(f["fee"])
	f["status"] = "to_release"
	f["release"] = st.ym + rel_cfg(st.d)["delay_months"]
	if f["stunt_self"]:
		st.inc("count.stunt_self")
	update_status(st)


# ---------- breaches ----------

## All film contracts locked in month ym breach: fee 0, fame -10%, no release (GDD 10 very sick;
## missing, withdrawal and month-taking opportunities are handled the same way). Returns the breached contracts.
static func breach_month(st, ym: int) -> Array:
	var out := []
	var pct: int = -st.d.rest_forced[0]["shoot_breach"]["fame_pct"]
	for f in films(st):
		if not _active(f):
			continue
		var hit := false
		for x in f["locks"]:
			if x[0] == ym:
				hit = true
		if hit:
			f["status"] = "breached"
			st.attr["fame"] = maxi(0, st.attr["fame"] - Rules.fdiv(st.attr["fame"] * pct, 100))
			st.inc("count.breach")
			out.append(f)
	update_status(st)
	return out


## The film contract locking period i of month ym breaches (detention, step 12c). Same penalty as breach_month.
static func breach_period(st, ym: int, i: int) -> Array:
	var out := []
	var pct: int = -st.d.rest_forced[0]["shoot_breach"]["fame_pct"]
	for f in films(st):
		if _active(f) and _has_lock(f, ym, i):
			f["status"] = "breached"
			st.attr["fame"] = maxi(0, st.attr["fame"] - Rules.fdiv(st.attr["fame"] * pct, 100))
			st.inc("count.breach")
			out.append(f)
	update_status(st)
	return out


# ---------- release ----------

## Fit F x1000 = 600 + 400 x average(min(value/target, 1.5)).
static func fit(st, role: Dictionary) -> int:
	var c: Dictionary = rel_cfg(st.d)["fit"]
	var b: Dictionary = st.bonus()
	var tot := 0
	var n := 0
	for k in role["wants"]:
		tot += mini(Rules.fdiv(st.val(k["stat"], b) * 1000, k["target"]), c["item_cap_pct"] * 10)
		n += 1
	var avg: int = Rules.fdiv(tot, n) if n else 1000
	return c["floor"] + Rules.fdiv(c["coef"] * avg, 1000)


## Tag familiarity T x1000 = 1000 + 30 x min(sum of the role's tag counts, 5); small films get the maximum when one of
## the role's tags is typed or lowbudget is typed. Returns [T, whether the untyped x0.9 applies].
static func familiarity(st, role: Dictionary, tier: String) -> Array:
	var c := rel_cfg(st.d)
	var tf: Dictionary = c["tag_familiarity"]
	var full: int = 1000 + tf["per_tag"] * tf["cap_count"]
	var tc := typecast_tags(st)
	var mine := false
	for t in role["tags"]:
		if tc.has(t):
			mine = true
	if mine or (low_budget(st) and tier == "small"):
		return [full, false]
	var n := 0
	for t in role["tags"]:
		n += st.tags.get(t, 0)
	return [1000 + tf["per_tag"] * mini(n, tf["cap_count"]), not tc.is_empty()]


static func talk_line(st, role: Dictionary) -> int:
	var line: int = role["speech_line"]
	if Schedule.truthy(st.flags.get("talkie_speech_line_minus_10")):
		line -= rel_cfg(st.d)["radio_speech_line_cut"]
	return line


static func release_one(st, f: Dictionary) -> Dictionary:
	var d = st.d
	var c := rel_cfg(d)
	var role: Dictionary = f["roles"]
	var t: String = f["size"]
	var B: int = c["box_base"][t]
	var P: int = f["perf"]
	var F := fit(st, role)
	var tf := familiarity(st, role, t)
	var T: int = tf[0]
	var off: bool = tf[1]
	var S: int = Rules.fdiv(B * P * F * T, 1000000)       # S x1000
	if off:
		S = Rules.fdiv(S * c["untyped_pct"], 100)
	var accent := false
	if Schedule.truthy(role.get("talkie")):
		st.inc("count.talkie_count")
		if st.val("speech") < talk_line(st, role):
			S = Rules.fdiv(S * c["talkie_penalty_pct"], 100)
			accent = true
			st.flags["accent_pending"] = 1
	var hit: bool = S >= B * c["hit_pct"] * 10
	var flop: bool = S < B * c["flop_pct"] * 10
	var k: int = d.t["habits"]["audition"]["result"]["narrow_loss"]["release_pct"] if f["support"] else 100
	var fame: int = Rules.fdiv(S * c["fame_pct"], 100000)
	if flop:
		fame = Rules.fdiv(fame, 2)
	fame = Rules.fdiv(fame * k, 100)
	var money: int = Rules.fdiv(Rules.fdiv(S * c["dividend_mult"], 1000) * k, 100)
	Schedule.add_stat(st, "fame", fame)
	st.add_money(money)
	var corr := 0
	if not flop:
		corr = Rules.fdiv(c["rep_bonus"][t] * (int(c["hit_mult"]) if hit else 1) * k, 100)
		st.corr[role["road"]] += corr
	for tag in role["tags"]:
		st.tags[tag] = st.tags.get(tag, 0) + 1
	if not f["support"]:
		st.count["count.lowbudget"] = maxi(0, st.cnt("count.lowbudget") + c["lowbudget"]["delta"][t])
		st.inc("count.lead." + t)
		if Schedule.truthy(role.get("lead")):
			Rules.apply_effect(st, "favor.%s+%d" % [role["lead"], c["lead_favor"]], "event")
	else:
		st.inc("count.support")
	st.inc("count.release")
	if hit:
		st.inc("count.hit")
		if f.get("divine", 0) and not f["support"]:      # the "divine" achievement: a lead shot on a divine dose is a hit
			st.inc("count.divine_hit")
			st.flags["divine_star"] = 1
		if role["tags"].has("romance") or role["tags"].has("exotic_lover"):
			st.inc("count.romance_hits")
	if flop:
		st.inc("count.flop")
	st.exposed = 1
	f["status"] = "released"
	f["result"] = {"S": S, "B": B, "P": P, "F": F, "T": T, "untyped": off, "accent": accent, "hit": hit,
		"flop": flop, "fame": fame, "dividend": money, "rep_bonus": corr, "month": st.ym}
	return f["result"]


## Month-end step 2: the films to release this month. Also updates the "big-film hits in the last 12 months" count (for the 1929-05 awards).
static func release(st) -> Array:
	var out := []
	for f in films(st):
		if f["status"] == "to_release" and f["release"] == st.ym:
			out.append(release_one(st, f))
	var n := 0
	for f in films(st):
		if f["status"] == "released" and f["size"] == "big" and f["result"]["hit"] and f["result"]["month"] > st.ym - 12:
			n += 1
	st.count["count.big_hits_12m"] = n
	return out
