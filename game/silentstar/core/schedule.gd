extends RefCounted
## Schedule: classes, books, jobs, rest (GDD 5.1-5.5). One entry per period, settled day by day. Port of sim/schedule.py.
##
## Schedule entries are strings: class "class_boxing", book "book_...", job "job_dock", rest "rest_home";
## an outing carries its place: "rest_outing@place_dock". All functions are static; st is an instance of core/state.gd.
## hooks is any object with the methods of month.gd's Hooks (class_chain, book_done, job_period, outing, day).
##
## Random-number order (copied from the Python side, the reconciliation checks it):
## - Class, book: fatigue per day from the table (fatigue_per_day, step 12c). Each class day first r0(fatigue), then r0(stamina/2); in_love rolls one more 20%; on a successful day the gains are rolled in table order.
## - Job: each work day first rolls the daily effects in table order (fatigue included), then r0(fatigue) once per success line in order,
##   then in_love 20% and reckless slacking 40%/80% (each only rolled in that state).

const Rules = preload("res://core/rules.gd")


## Python truthiness for values read from the tables: null, "", 0, [] and {} are false.
static func truthy(v) -> bool:
	if v == null:
		return false
	match typeof(v):
		TYPE_STRING:
			return v != ""
		TYPE_INT, TYPE_FLOAT:
			return v != 0
		TYPE_ARRAY, TYPE_DICTIONARY:
			return v.size() > 0
		TYPE_BOOL:
			return v
	return true


## "rest_outing@place_dock" -> ["rest", "rest_outing", "place_dock"]; returns [] for an unknown entry.
static func parse_entry(e: String) -> Array:
	var base := e
	var place := ""
	var i := e.find("@")
	if i >= 0:
		base = e.substr(0, i)
		place = e.substr(i + 1)
	var kind := base.split("_")[0]
	if not (kind in ["class", "book", "job", "rest"]):
		return []
	return [kind, base, place if place != "" else null]


## Adds v to an attribute or skill training value, clamped to the range.
static func add_stat(st, name: String, v: int) -> void:
	var d = st.d
	if st.attr.has(name):
		var rg: Array = d.attr_range[name]
		st.attr[name] = clampi(st.attr[name] + v, rg[0], rg[1])
	elif st.skill.has(name):
		var rg: Array = d.skill_range[name]
		st.skill[name] = clampi(st.skill[name] + v, rg[0], rg[1])
	else:
		push_error("not an attribute or a skill: %s" % name)


## Days of period i (0 early, 1 mid, 2 late): [[day, is_sunday], ...].
static func days_of(st, i: int) -> Array:
	var m: Dictionary = st.month()
	var ab: Array = m["periods"][i]
	var out := []
	for x in range(ab[0], ab[1] + 1):
		out.append([x, m["sundays"].has(x)])
	return out


## The class level 1-4 of this period: periods taken so far (including this one) <=3 is level 1, <=6 level 2, <=9 level 3 (GDD 5.2).
static func class_level(st, cid: String) -> int:
	var n: int = st.cnt("class_periods." + cid) + 1
	var lv := 1
	for step in st.d.class_steps:
		if n > step:
			lv += 1
	return lv


# ---------- can it be picked ----------

static func job_unlocked(st, jid: String) -> bool:
	var j: Dictionary = st.d.jobs[jid]
	return st.ym >= st.d.month_index[j["earliest"]] and Rules.cond(st, j["prereq"])


static func job_refused(st, jid: String) -> bool:
	var r: Dictionary = st.d.job_rules["refuse"]
	return not r["except"].has(jid) and Rules.cond(st, r["cond"])


static func book_on_shelf(st, bid: String) -> bool:
	var b: Dictionary = st.d.books[bid]
	var s = b.get("on_shelf")
	return s == null or st.ym >= st.d.month_index[s]


## Returns "" (can be picked) or the reason it cannot. Not having the money for a class is not a reason: on a day without money you skip it (GDD 5.3).
static func validate(st, e: String) -> String:
	var pe := parse_entry(e)
	if pe.is_empty():
		return "unknown schedule entry: %s" % e
	var kind: String = pe[0]
	var iid: String = pe[1]
	var place = pe[2]
	var d = st.d
	if kind == "class":
		return "" if d.classes.has(iid) else "no such class %s" % iid
	if kind == "book":
		if not d.books.has(iid):
			return "no such book %s" % iid
		if not st.books.has(iid):
			return "no such book, or already finished"
		if st.val("education") < d.books[iid]["education_gate"]:
			return "education below the gate"
		return ""
	if kind == "job":
		if not d.jobs.has(iid):
			return "no such job %s" % iid
		if not job_unlocked(st, iid):
			return "not unlocked yet"
		if job_refused(st, iid):
			return "reckless_index >= 60, the employer refuses"
		return ""
	if not d.rests.has(iid):
		return "no such rest %s" % iid
	var r: Dictionary = d.rests[iid]
	if not r.get("player_choice", true):
		return "forced only when very sick"
	if st.status["sick"] and not r["sick_allowed"]:
		return "when sick you can only rest at home"
	if iid == "rest_outing":
		if place == null or not d.places.has(place):
			return "an outing needs a place"
	elif place != null:
		return "only an outing takes a place"
	return ""


## The schedule entries available this month (for the UI and bots), in the same order as the Python side.
static func options(st) -> Array:
	var d = st.d
	var out := []
	for c in d.classes:
		out.append(c)
	for b in st.books:
		if validate(st, b) == "":
			out.append(b)
	for j in d.jobs:
		if validate(st, j) == "":
			out.append(j)
	for r in d.rests:
		if r == "rest_outing":
			for p in d.places:
				var e: String = "%s@%s" % [r, p]
				if validate(st, e) == "":
					out.append(e)
		elif validate(st, r) == "":
			out.append(r)
	return out


## Cost of one outing day: the place's cost, or cost_by_fame_tier (resort).
static func place_cost(st, place: String) -> int:
	var p: Dictionary = st.d.places[place]
	if p.has("cost_by_fame_tier"):
		return p["cost_by_fame_tier"][st.fame_tier()]
	return p["cost"]


# ---------- checks ----------

## in_love 20% (classes, books, jobs and shooting all have it); reckless slacking only for jobs and shooting (GDD 5.1),
## and not for crime jobs whose tier has reckless_slack false (step 12c c3). Returns true when the day fails.
static func extra_fail(st, job: bool, slack := true) -> bool:
	var g = st.rng.logic
	var fail := false
	if st.status["in_love"] and g.chance(20, 100):
		fail = true
	if job and slack:
		var w: int = st.idx["reckless_index"]
		if w >= 30:
			var c: bool = g.chance(80, 100)     # always rolled, like the Python "x or fail"
			fail = c or fail
		elif w >= 10:
			var c: bool = g.chance(40, 100)
			fail = c or fail
	return fail


## The dose of this period (step 12c c3, GDD 5.8.1): 1 = this day succeeds whatever the dice say (high), -1 = it fails
## (the side effect of the last dose or an attack, by status.drug_fail_pct), 0 = no change.
static func drug_day(st) -> int:
	if int(st.status.get("drug_high", 0)) > 0:
		return 1
	var p: int = int(st.status.get("drug_fail_pct", 0))
	if p > 0 and st.rng.logic.chance(p, 100):
		return -1
	return 0


## Gains of practice are multiplied on a divine dose (stats.drug.divine_gain_mult).
static func drug_gain(st, v: int) -> int:
	if int(st.status.get("drug_high", 0)) == 2:
		return v * int(st.d.t["stats"]["drug"]["divine_gain_mult"])
	return v


## stamina/2 + r0(stamina/2) >= r0(fatigue) (GDD 5.1).
static func practice_ok(st) -> bool:
	var dg := drug_day(st)
	if dg != 0:
		return dg > 0
	var g = st.rng.logic
	var b: Dictionary = st.bonus()
	var line: int = g.r0(st.val("fatigue", b))
	var hp: int = st.val("stamina", b)
	var half := Rules.fdiv(hp, 2)
	var ok: bool = half + g.r0(half) >= line
	return (not extra_fail(st, false)) and ok


## The success lines including `success_line_mods` (e.g. flag diploma lowers the education line of the newspaper and studio office jobs by 20).
static func job_lines(st, j: Dictionary) -> Array:
	var lines := []
	for c in j["success_lines"]:
		lines.append([c["stat"], c["value"]])
	for m in j.get("success_line_mods", []):
		if Rules.cond(st, m["cond"]):
			for x in lines:
				if x[0] == m["stat"]:
					x[1] += m["value"]
	return lines


static func job_day_ok(st, lines: Array, slack := true) -> bool:
	var dg := drug_day(st)
	if dg != 0:
		return dg > 0
	var g = st.rng.logic
	var b: Dictionary = st.bonus()
	var tired: int = st.val("fatigue", b)
	var ok := true
	for kv in lines:
		if st.val(kv[0], b) - g.r0(tired) < kv[1]:
			ok = false
	return (not extra_fail(st, true, slack)) and ok


## Whether reckless slacking applies on this job: false for a crime job whose tier says reckless_slack false (step 12c c3).
static func job_slacks(st, j: Dictionary) -> bool:
	if not j.has("crime_tier"):
		return true
	return st.d.job_rules["crime_tiers"][str(j["crime_tier"])].get("reckless_slack", true)


## Daily wage = base x raise tier, rounded down; the raise tier is by the periods that succeeded before this one (GDD 5.4).
static func wage_of(st, jid: String) -> int:
	var j: Dictionary = st.d.jobs[jid]
	var n: int = st.cnt("job_periods." + jid)
	for t in st.d.job_rules["raise_tiers"]:
		if n < t["periods_below"]:
			return Rules.fdiv(j["daily_wage"] * (100 + t["bonus_pct"]), 100)
	return j["daily_wage"]


static func accent_on(st) -> bool:
	return st.flags.get("accent_period", 0) > 0


# ---------- execution ----------

static func run_class(st, cid: String, days: Array, hooks) -> Dictionary:
	var c: Dictionary = st.d.classes[cid]
	var lv := class_level(st, cid)
	var fee: int = c["fee"][lv - 1]
	var g = st.rng.logic
	var talk := false
	for e in c["gain"]:
		if e["stat"] == "speech":
			talk = true
	var went := 0
	var ok_days := 0
	for dd in days:
		if dd[1]:
			continue
		if st.money < fee:
			st.inc("count.broke_class_days")
			continue
		went += 1
		if practice_ok(st):
			ok_days += 1
			for e in c["gain"]:
				if e.has("cond") and not Rules.cond(st, e["cond"]):
					continue
				var pl: Array = e["per_level"][lv - 1]
				add_stat(st, e["stat"], drug_gain(st, g.r(pl[0], pl[1])))
			if talk and accent_on(st):
				add_stat(st, "speech", 1)
		add_stat(st, "fatigue", c.get("fatigue_per_day", 1))
		st.money -= fee
	if went > 0:
		st.inc("class_periods." + cid)
		var road = st.d.class_road(cid)
		if road != null:
			st.inc("road_periods." + road)
		if truthy(c.get("period_effect")):
			Rules.apply_effect(st, c["period_effect"], "schedule")
		var ch = c.get("story_chain")
		var n: int = st.cnt("class_periods." + cid)
		if ch != null and ch["trigger_periods"].has(n):
			hooks.class_chain(st, ch["chain"], n)
	return {"class_days": went, "ok_days": ok_days, "levels": lv}


static func run_book(st, bid: String, days: Array, hooks) -> Dictionary:
	var b: Dictionary = st.d.books[bid]
	var sk: String = b["skills"]
	var g = st.rng.logic
	var ok_days := 0
	for dd in days:
		if dd[1]:
			continue
		if practice_ok(st):
			ok_days += 1
			var left: int = st.books.get(bid, 0)
			var room: int = b["skill_cap"] - st.skill[sk]
			if left > 0 and room > 0:
				var v: int = mini(mini(drug_gain(st, g.r(b["gain"][0], b["gain"][1])), left), room)
				add_stat(st, sk, v)
				st.books[bid] = left - v
			if sk == "speech" and accent_on(st):
				add_stat(st, "speech", 1)
		add_stat(st, "fatigue", b.get("fatigue_per_day", 1))
	st.inc("count.book_periods")
	st.inc("road_periods." + st.d.skill_road[sk])
	if st.books.get(bid, 1) <= 0:
		st.books.erase(bid)
		st.read_books.append(bid)
		hooks.book_done(st, bid)
	return {"ok_days": ok_days}


static func run_job(st, jid: String, days: Array, hooks) -> Dictionary:
	var j: Dictionary = st.d.jobs[jid]
	var g = st.rng.logic
	var lines := job_lines(st, j)
	var wage := wage_of(st, jid)
	var slack := job_slacks(st, j)
	var work := 0
	var ok_days := 0
	for dd in days:
		if dd[1]:
			continue
		work += 1
		for e in j["daily_effect"]:
			add_stat(st, e["stat"], g.r(e["add"][0], e["add"][1]))
		if job_day_ok(st, lines, slack):
			ok_days += 1
	var pay := wage * ok_days
	if work > 0 and ok_days == work:
		pay = Rules.fdiv(pay * (100 + st.d.job_rules["full_attendance_bonus_pct"]), 100)
	st.add_money(pay)
	var good := ok_days > 0    # Original: one successful day makes the period successful
	if good:
		st.inc("job_periods." + jid)
		for r in st.d.job_roads(jid):
			st.inc("road_periods." + r)
		if truthy(j["exposure"]):
			st.exposed = 1
		if truthy(j["job_period_effect"]):
			Rules.apply_effect(st, j["job_period_effect"], "schedule")
	hooks.job_period(st, jid, good)
	return {"work_days": work, "ok_days": ok_days, "pay": pay}


static func run_rest(st, rid: String, place, days: Array, hooks) -> Dictionary:
	var d = st.d
	var r: Dictionary = d.rests[rid]
	var spent := 0
	var mid := days.size() / 2
	for k in days.size():
		if rid == "rest_outing":
			var cost := place_cost(st, place)
			if st.money >= cost:
				st.money -= cost
				spent += cost
				add_stat(st, "fatigue", d.places[place]["fatigue_per_day"])
			else:
				add_stat(st, "fatigue", d.rests["rest_home"]["fatigue_per_day"])
			if k == mid - 1:
				st.inc("count.outing." + place)
				hooks.outing(st, place)
		elif rid == "rest_sanatorium":
			if st.money >= r["cost"]:
				st.money -= r["cost"]
				spent += r["cost"]
				add_stat(st, "fatigue", r["fatigue_per_day"])
		else:
			add_stat(st, "fatigue", r["fatigue_per_day"])
			if truthy(r.get("daily_effect")):
				Rules.apply_effect(st, r["daily_effect"], "schedule")
	if truthy(r.get("period_effect")):
		Rules.apply_effect(st, r["period_effect"], "schedule")
	return {"cost": spent}


## Runs schedule entry e of period i. Returns a summary (for the log and the report).
static func run_period(st, i: int, e: String, hooks) -> Dictionary:
	var days := days_of(st, i)
	var pe := parse_entry(e)
	if pe.is_empty():
		push_error("unknown schedule entry: %s" % e)
		return {}
	var kind: String = pe[0]
	var iid: String = pe[1]
	var place = pe[2]
	st.inc("count.period." + iid)
	var out: Dictionary
	if kind == "class":
		out = run_class(st, iid, days, hooks)
	elif kind == "book":
		out = run_book(st, iid, days, hooks)
	elif kind == "job":
		out = run_job(st, iid, days, hooks)
	else:
		out = run_rest(st, iid, place, days, hooks)
	for dd in days:      # Per-day events such as birthdays: checked in order after this period is settled
		hooks.day(st, dd[0])
	out["schedule"] = e
	return out
