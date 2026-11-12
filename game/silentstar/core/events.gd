extends RefCounted
## Events (GDD 5.4 hooks, 5.5.2 outings, 6.5 Duv, 11, 12). Port of sim/events.py.
##
## Event data is in events.json and outing.json; an event can have:
##   effect (applied directly) -> check (event level, success/fail effect) -> branches (the first whose cond holds)
##   -> options (ask the player) -> code (events with `code: true` are written in _code following their `note`).
## `trigger.<id>` in an effect fires last, in order.
## freq: once_per_game / once_per_year / once_per_quarter / null; `once: true` of an outing event equals once_per_game.
##
## Random-number order (copied from the Python side):
## - Month end: by `order`, one by one; the probability is rolled only when the cond holds and freq allows; opportunities come
##   after senior approval (order 9), in table order. Stop after 2 fired.
## - Period start: swap role, steal role, same.
## - Outing: nothing is rolled when someone is present and has a chain event; resident events and the random table use
##   below(sum of weights) by weight.
## - Jobs: each period_random is rolled once in table order, then milestones are checked (no roll).
## - Tutoring period: with Duv favor >= 30 roll 1/10 for the tip-off.
## - Annual: first r0(50) for my score, then r0(50) for each rival in sorted order.
##
## All functions are static; st is an instance of core/state.gd, story the Story hooks (core/story.gd: agent, event_log, cur_period, annuals).

const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")
const Board = preload("res://core/board.gd")
const Film = preload("res://core/film.gd")

const SCANDAL_PAY := 200       # Newspaper line: pay 200 to suppress a scandal (5.4)
const HELP_LOYALTY := 150      # loyalty >= 150: someone helps (10.1)
const HELP_COST := 30
const SCANDAL_LOYALTY := 200
const SLOTS := ["early", "mid", "late"]
const MAX_DEPTH := 8


# ---------- freq ----------

static func can_fire(st, e: Dictionary) -> bool:
	var n: int = st.fired.get(e["id"], 0)
	if e.get("once", false) and n:
		return false
	var f = e.get("freq")
	if not Schedule.truthy(f) or not n:
		return true
	var last: int = st.story["last_fired"].get(e["id"], -99)
	match f:
		"once_per_game":
			return false
		"once_per_year":
			return Rules.fdiv(last, 12) != Rules.fdiv(st.ym, 12)
		"once_per_quarter":
			return Rules.fdiv(last, 3) != Rules.fdiv(st.ym, 3)
	push_error("unknown freq %s" % f)
	return false


static func ready(st, e: Dictionary) -> bool:
	return can_fire(st, e) and Rules.cond(st, e.get("cond"))


# ---------- trigger ----------

## Fires one event and settles it. Returns the record {id, month, check?, options?} (also appended to story.event_log).
static func fire(story, st, eid: String, depth := 0) -> Dictionary:
	if depth > MAX_DEPTH:
		push_error("event trigger chain too deep: %s" % eid)
		return {}
	var e: Dictionary = st.d.events[eid]
	st.fired[eid] = st.fired.get(eid, 0) + 1
	st.story["last_fired"][eid] = st.ym
	var rec := {"id": eid, "month": st.date()}
	var trig := []
	if Schedule.truthy(e.get("effect")):
		trig += Rules.apply_effect(st, e["effect"], "event")
	if Schedule.truthy(e.get("check")):
		var ok := Rules.check(st, e["check"])
		rec["check"] = ok
		trig += Rules.apply_effect(st, e["success_effect"] if ok else e["fail_effect"], "event")
	var brs = e.get("branches")
	if Schedule.truthy(brs):
		for br in brs:
			if Rules.cond(st, br["cond"]):
				trig += Rules.apply_effect(st, br["effect"], "event")
				break
	var choice = null
	var opts = e.get("options")
	if Schedule.truthy(opts):
		var avail := []
		for k in opts.size():
			if Rules.cond(st, opts[k].get("cond")):
				avail.append(k)
		if not avail.is_empty():
			choice = story.agent.option(st, e, avail)
			if not avail.has(choice):
				push_error("%s picked an option that cannot be picked: %s" % [eid, choice])
				return {}
			var o: Dictionary = opts[choice]
			var ck = o.get("check") if Schedule.truthy(o.get("check")) else null
			var ok := Rules.check(st, ck)
			rec["check"] = ok
			trig += Rules.apply_effect(st, o["success_effect"] if ok else o["fail_effect"], "event")
		rec["options"] = choice
	trig += _code(story, st, eid, choice)
	story.event_log.append(rec)
	for t in trig:
		fire(story, st, t, depth + 1)
	return rec


# ---------- code events ----------

static func fame_pct(st, pct: int) -> void:
	st.attr["fame"] = maxi(0, st.attr["fame"] + Rules.fdiv(st.attr["fame"] * pct, 100))


## The events whose logic is code. Returns the ids to trigger (none of them triggers anything for now).
## The other `code: true` events only need the effects and flags in the data, read by other modules through the flags:
##   evt_swap_role / evt_steal_role (period_start), evt_accent (flag), era_valen_death (board reads the flag),
##   era_talkie (the date is already in the table), job_studio_m1 (the long-contract probability is tiered by favor in evt_contract).
static func _code(story, st, eid: String, choice) -> Array:
	match eid:
		"evt_missing": _missing(st)
		"evt_arrest": _arrest(story, st)
		"evt_scandal": _scandal(story, st)
		"evt_contract":
			if choice == 1:
				st.story["contract_refused"] = st.ym
		"evt_creditor": _creditor(st)
		"evt_detox": _detox(st)
		"outing_duv_tip":     # Duv's tip-off: a random medium or big role on the next board shows its full style and tags
			if Schedule.truthy(st.flags.get("tipoff")):
				st.flags["tipoff"] = 0
				st.story["tipoff"] += 1
		"job_studio_m2": _transform(story, st)
		"evt_birthday":
			Rules.apply_effect(st, "favor.actress+3", "event")
	return []


## Missing: next month's schedule is void, and the four rep_bonus values each lose 10% of the current reputation.
static func _missing(st) -> void:
	st.void_next = 1
	st.inc("count.void.missing", 3)
	var b: Dictionary = st.bonus()
	for r in st.d.roads:
		st.corr[r] -= Rules.fdiv(st.rep(r, b) * 10, 100)
	Film.breach_month(st, st.ym + 1)


## Arrest (step 12c): fine max(fine_min, money x fine_pct%), at most the money held (never below 0); the next detain_periods
## periods are void (detention; a shoot locked there breaches); crime +20, exposure; no big film for morals_months.
## With loyalty >= 150 someone bails him out (fine halved, no exposure, loyalty -30); the bar owner's milestone also halves the
## fine (the two do not stack). A sick player is not arrested (GDD 10). The detention starts after story.cur_period (3 = month end).
static func _arrest(story, st) -> void:
	if st.status["sick"]:
		return
	var a: Dictionary = st.d.t["stats"]["arrest"]
	var fine := mini(maxi(st.money, 0), maxi(a["fine_min"], Rules.fdiv(st.money * a["fine_pct"], 100)))
	var bail: bool = st.val("loyalty") >= HELP_LOYALTY
	if bail or Schedule.truthy(st.flags.get("bail_half")):
		fine = Rules.fdiv(fine, 2)
	st.money -= fine
	Schedule.add_stat(st, "crime", 20)
	if bail:
		Schedule.add_stat(st, "loyalty", -HELP_COST)
	else:
		st.exposed = 1
	st.inc("count.arrest")
	var start: int = st.ym * 3 + story.cur_period + 1
	for k in a["detain_periods"]:
		if not st.void_periods.has(start + k):
			st.void_periods.append(start + k)
	morals(st)


## Morals clause (step 12c): no big film on the next morals_months boards.
static func morals(st) -> void:
	st.flags["morals_until"] = st.ym + Board.cfg(st.d)["morals_months"]


## Scandal exposure: the newspaper line can suppress it (free once a year / pay 200); villain + crime >= 3: fame +10%,
## otherwise -15% (doubled after an official warning, halved with loyalty >= 200).
static func _scandal(story, st) -> void:
	var y: int = Rules.fdiv(st.ym, 12)
	var sv: Dictionary = st.story
	if (Schedule.truthy(st.flags.get("free_scandal_cover")) and sv["scandal_cover_year"] != y + 1
			and story.agent.suppress(st, "free")):
		sv["scandal_cover_year"] = y + 1
		st.inc("count.scandal_covered")
		return
	if Schedule.truthy(st.flags.get("scandal_foresight")) and st.money >= SCANDAL_PAY and story.agent.suppress(st, "paid"):
		st.money -= SCANDAL_PAY
		st.inc("count.scandal_covered")
		return
	st.exposed = 1
	st.inc("count.scandal")
	morals(st)
	if st.tags.get("villain", 0) + st.tags.get("crime", 0) >= 3:
		fame_pct(st, 10)
		return
	var pct := 15
	if Schedule.truthy(st.flags.get("warning")):
		pct *= 2
		st.flags["warning"] = 0
	if st.val("loyalty") >= SCANDAL_LOYALTY:
		pct = Rules.fdiv(pct, 2)
	fame_pct(st, -pct)


## Creditor: the dock countryman blocks once -> loyalty >= 150 a friend covers it -> fight >= 50 drives him off
## -> the most expensive item is taken -> fame -10% and exposure.
static func _creditor(st) -> void:
	if st.flags.get("fellow_debt_shield", 0) == 1:
		st.flags["fellow_debt_shield"] = 2
		st.money = maxi(st.money, 0)
		st.debt_months = 0
		return
	if st.val("loyalty") >= HELP_LOYALTY:
		Schedule.add_stat(st, "loyalty", -HELP_COST)
		st.money = maxi(st.money, 0)
		st.debt_months = 0
		return
	st.debt_months = 0
	if st.val("fight") >= 50:
		Schedule.add_stat(st, "crime", 10)
		return
	var top = null
	for i in st.items:        # the first of the most expensive, like Python's max
		var p: int = st.d.items[i]["price"]
		if p > 0 and (top == null or p > st.d.items[top]["price"]):
			top = i
	if top != null:
		Rules.remove_item(st, top)
		st.money = mini(0, st.money + st.d.items[top]["price"])
		return
	fame_pct(st, -10)
	st.exposed = 1


## Withdrawal: takes the whole next month. With Sil favor >= 60 (he is present) Sil +10.
static func _detox(st) -> void:
	if st.favor.get("sil", 0) >= 60:
		Rules.apply_effect(st, "favor.sil+10", "event")
	st.void_next = 1
	st.inc("count.detox")
	st.inc("count.void.detox", 3)
	Film.breach_month(st, st.ym + 1)


## Studio boss "backs transition": the next 3 boards each get an extra medium role of the tag family the player picks.
static func _transform(story, st) -> void:
	var fam: String = story.agent.family(st)
	if not st.d.tag_families.has(fam):
		push_error("no such tag family: %s" % fam)
		return
	st.story["transition"] = [Board.cfg(st.d)["transition_boards"], fam]


# ---------- month end (11.2, 12.2) ----------

## The month-end list: [[kind, row], ...] with kind "event" or "opportunity"; events by `order` (ties in table order),
## opportunities in table order after the last event of order <= 9.
static func month_end_list(d) -> Array:
	var evs := []
	for e in d.events.values():
		if e.get("class") == "month_end" and e.get("timing") == "month_end":
			evs.append([e["order"], evs.size(), e])
	evs.sort_custom(func(a, b): return a[0] < b[0] if a[0] != b[0] else a[1] < b[1])
	var out := []
	var k := -1
	for x in evs:
		if x[0] <= 9:
			k = out.size()
		out.append(["event", x[2]])
	var res := out.slice(0, k + 1)
	for o in d.opps:
		res.append(["opportunity", o])
	res += out.slice(k + 1)
	return res


static func month_end(story, st) -> void:
	var d = st.d
	if st.status["long_contract"]:
		st.add_money(d.contract["long_contract"]["monthly_pay"])
	var lim: int = d.t["events"]["month_end_cap"]
	var n := 0
	for ke in month_end_list(d):
		if n >= lim:
			break
		var e: Dictionary = ke[1]
		if ke[0] == "opportunity":
			if Schedule.truthy(st.fired.get(e["story"])) or not Rules.cond(st, e["cond"]):
				continue
			if not Rules.prob(st, e["monthly_prob"]):
				continue
			fire(story, st, e["story"])
			Rules.apply_effect(st, e["effect"], "opportunity")    # the opportunities' effects are in opportunities.json; the story event only handles the story
			st.inc("count.opportunity")
			if e["takes_month"]:
				st.void_next = 1
				Film.breach_month(st, st.ym + 1)
			n += 1
			continue
		if not ready(st, e):
			continue
		if e["id"] == "evt_contract" and st.ym - st.story["contract_refused"] < d.contract["long_contract"]["refuse_months"]:
			continue
		if not Rules.prob(st, e.get("prob")):
			continue
		fire(story, st, e["id"])
		n += 1


# ---------- period start (11.1) ----------

static func period_start(story, st, i: int, entry: String) -> void:
	if entry.begins_with("rest_"):
		return
	var d = st.d
	var e: Dictionary = d.events["evt_swap_role"]
	var nxt := Film.next_period(st, i)
	if (ready(st, e) and not Film.is_locked(st, nxt[0], nxt[1]) and nxt[0] < d.months.size()
			and Rules.prob(st, e["prob"])):
		fire(story, st, e["id"])
		Board.swap_role(st, i, story.agent)
	e = d.events["evt_steal_role"]
	if ready(st, e) and Rules.prob(st, e["prob"]):
		fire(story, st, e["id"])
		Board.steal_role(st, story.agent)


static func period_end(story, st, i: int, entry: String, out: Dictionary) -> void:
	var d = st.d
	if entry == "class_tutor" and Schedule.truthy(out.get("class_days")):
		var e: Dictionary = d.events["outing_duv_script"]
		if ready(st, e):
			fire(story, st, e["id"])
		if st.favor.get("duv", 0) >= 30 and st.rng.logic.chance(1, 10):
			fire(story, st, "outing_duv_tip")
	var duv = d.npcs["duv"].get("education_milestones")
	if Schedule.truthy(duv) and st.known.has("duv"):
		for line in duv["line"]:
			var k := "duv_education_%d" % line
			if not Schedule.truthy(st.flags.get(k)) and st.val("education") >= line:
				st.flags[k] = 1
				Rules.apply_effect(st, duv["effect"], "event")


# ---------- outings (5.5.2) ----------

static func meet(st, npc: String) -> void:
	if not st.known.has(npc):
		st.known.append(npc)
		var order: Dictionary = st.d.npc_order
		st.known.sort_custom(func(a, b): return order[a] < order[b])    # table order
	st.inc("count.met." + npc)


static func present(st, place: String, i: int) -> Array:
	var m: int = st.date().substr(5).to_int()
	var y: int = st.date().substr(0, 4).to_int()
	var out := []
	for s in st.d.schedule_npc:
		if (s["place"] == place and s["years"][0] <= y and y <= s["years"][1] and s["months"].has(m)
				and s["periods"].has(SLOTS[i]) and Rules.cond(st, s["cond"]) and not out.has(s["npc"])):
			out.append(s["npc"])
	return out


## pairs: [[weight, value], ...], draws one by weight; an empty table returns null.
static func weighted(st, pairs: Array):
	var tot := 0
	for p in pairs:
		tot += p[0]
	if tot <= 0:
		return null
	var v: int = st.rng.logic.below(tot)
	for p in pairs:
		if v < p[0]:
			return p[1]
		v -= p[0]
	push_error("weighted: out of range")
	return null


## The next chain event of a present NPC (not seen yet, cond holds); null if there is none.
static func npc_event(st, npc: String):
	var d = st.d
	for ch in d.chains:
		if ch["npc"] == npc and ch["trigger"] == "outing":
			for eid in ch["chain"]:
				if ready(st, d.events[eid]):
					return eid
	return null


static func npc_resident(st, npc: String) -> Array:
	var d = st.d
	var pairs := []
	for ch in d.chains:
		if ch["npc"] == npc and ch["trigger"] == "outing":
			for c in ch["resident"]:
				if ready(st, d.events[c["event"]]):
					pairs.append([c["weight"], c["event"]])
	return pairs


## Fires exactly one event in the middle of an outing period. If someone is present and has a chain or resident event,
## theirs fires, otherwise one is drawn from the place's random table. Returns the event id or null.
static func outing(story, st, place: String):
	var d = st.d
	var people := present(st, place, story.cur_period)
	for npc in people:
		meet(st, npc)
	var eid = null
	for npc in people:
		eid = npc_event(st, npc)
		if eid != null:
			break
	if eid == null:
		for npc in people:
			var pairs := npc_resident(st, npc)
			if not pairs.is_empty():
				eid = weighted(st, pairs)
				break
	if eid == null:
		var pairs := []
		for x in d.places[place]["random_table"]:
			if ready(st, d.events[x["event"]]):
				pairs.append([x["weight"], x["event"]])
		eid = weighted(st, pairs)
	if eid != null:
		fire(story, st, eid)
	return eid


## Tutoring periods 1, 4, 7, 10: Duv's tutoring chain, the next unseen event in order.
static func class_chain(story, st, chain: String, _n: int):
	var d = st.d
	var ch: Dictionary = {}
	for c in d.chains:
		if c["id"] == chain:
			ch = c
			break
	meet(st, ch["npc"])
	for eid in ch["chain"]:
		if ready(st, d.events[eid]):
			fire(story, st, eid)
			return eid
	return null


static func book_done(story, st, bid: String) -> void:
	var eid = st.d.books[bid].get("finish_event")
	if Schedule.truthy(eid) and ready(st, st.d.events[eid]):
		fire(story, st, eid)


# ---------- job hooks (5.4) ----------

static func job_period(story, st, jid: String, good: bool) -> void:
	var d = st.d
	var j: Dictionary = d.jobs[jid]
	if good and Schedule.truthy(j["npc"]):
		meet(st, j["npc"])
	for r in j["period_random"]:
		if st.rng.logic.chance(r["prob"][0], r["prob"][1]):
			fire(story, st, r["event"])
	if j.has("raid_prob"):
		raid(story, st, j)
	for m in j["milestones"]:
		var eid: String = m["event"]
		if not Schedule.truthy(st.fired.get(eid)) and Rules.cond(st, m["cond"]):
			fire(story, st, eid)


## Crime-job search (step 12c): once per period, probability raid_prob x (1 + crime / raid_crime_div); then
## r0(raid_skill displayed) + raid_check_add >= raid_line (step 12c c3), failing means arrest (the detention takes the next periods).
static func raid(story, st, j: Dictionary) -> void:
	var div: int = st.d.t["stats"]["arrest"]["raid_crime_div"]
	var p: Array = j["raid_prob"]
	if not st.rng.logic.chance(p[0] * (div + maxi(0, st.val("crime"))), p[1] * div):
		return
	st.inc("count.raid")
	var add: int = st.d.t["stats"]["arrest"]["raid_check_add"]
	if st.rng.logic.r0(st.val(j["raid_skill"])) + add < j["raid_line"]:
		fire(story, st, "evt_arrest")


# ---------- drugs (step 12c c3 round 3) ----------
# The dealer shows up by a roll at month start with a small stock at a rolled price; a dose is used before a period.
# drug_points is the depth of the addiction (0 = not addicted); drug_stage follows it (stats.drug.stage_lines).
# Player-side numbers live in st.flags: drug_stock, dealer_stock, dealer_price, drug_side_next, drug_known.

## Month start: is the dealer on the street this month, with how many doses and at what price each.
static func dealer_month(st) -> void:
	var dr: Dictionary = st.d.t["stats"]["drug"]
	var g = st.rng.logic
	var dl: Dictionary = dr["dealer"]
	var p: int = dl["prob_pct"] + Rules.fdiv(maxi(0, st.val("crime")), dl["crime_step"]) * dl["crime_add_pct"]
	p = mini(p, dl["prob_cap_pct"])
	if st.drug_points > 0:
		p += dl["addicted_add_pct"]
	st.flags["dealer_stock"] = 0
	st.flags["dealer_price"] = 0
	if not g.chance(p, 100):
		return
	st.inc("count.dealer")
	st.flags["dealer_stock"] = dl["stock"]
	var mult: int = mini(100 + dl["price_depth_pct"] * st.drug_points, dl["price_cap_pct"])
	st.flags["dealer_price"] = Rules.fdiv(g.r(dl["price"][0], dl["price"][1]) * mult, 100)


## Buy n doses from the dealer (month start). "" or the reason.
static func buy_drug(st, n: int) -> String:
	var dr: Dictionary = st.d.t["stats"]["drug"]
	if n <= 0 or int(st.flags.get("dealer_stock", 0)) < n:
		return "the dealer does not have that many"
	if st.drug_points == 0 and st.val("discipline") >= dr["refuse_discipline"]:
		return "discipline too high, he will not touch it"
	var cost: int = int(st.flags["dealer_price"]) * n
	if st.money < cost:
		return "if_broke"
	st.money -= cost
	st.track("drug", "money", -cost)
	st.flags["dealer_stock"] -= n
	st.flags["drug_stock"] = int(st.flags.get("drug_stock", 0)) + n
	st.inc("count.drug_bought", n)
	return ""


## Whether a dose can be taken before period i; "" or the reason. At most one per period.
static func boost_reason(st, i: int) -> String:
	if int(st.flags.get("drug_stock", 0)) <= 0:
		return "no dose"
	if st.month_used.has("boost.%d" % i):
		return "already used this period"
	return ""


## Takes a dose: dose_effect, then one of the outcomes by weight (high: every day of this period succeeds; divine: also gains x
## divine_gain_mult and a better shoot; side: side_effect now and side_fail_pct on the next period). Not addicted yet: a hidden roll,
## hook_base + hook_step x doses taken before (cap hook_cap), makes him addicted (depth 1). Addicted: depth +1.
static func boost(st, i: int) -> String:
	var r := boost_reason(st, i)
	if r != "":
		return r
	var dr: Dictionary = st.d.t["stats"]["drug"]
	var g = st.rng.logic
	st.flags["drug_stock"] -= 1
	st.month_used["boost.%d" % i] = 1
	st.month_used["boost"] = st.month_used.get("boost", 0) + 1
	Rules.apply_effect(st, dr["dose_effect"], "drug")
	var w: Dictionary = dr["outcome_weights"]
	var roll: int = g.r0(w["high"] + w["divine"] + w["side"])
	if roll < w["high"]:
		st.status["drug_high"] = 1
	elif roll < w["high"] + w["divine"]:
		st.status["drug_high"] = 2
		st.inc("count.divine")
	else:
		Rules.apply_effect(st, dr["side_effect"], "drug")
		st.flags["drug_side_next"] = 1
		st.inc("count.drug_side")
	var life: int = st.cnt("count.boost")
	st.inc("count.boost")
	if st.drug_points > 0:
		st.drug_points += 1
	elif g.chance(mini(dr["hook_base_pct"] + dr["hook_step_pct"] * life, dr["hook_cap_pct"]), 100):
		st.drug_points = 1
		st.inc("count.hooked")
	st.drug = st.drug_stage_of(st.drug_points)
	return ""


## Before period i, after the player's own free actions: an addict with a dose in hand takes it himself; then this period's
## drug state: status.drug_high (0, 1 high, 2 divine) and status.drug_fail_pct (side effect of the last dose, or an attack:
## addicted and no dose yet this month).
static func drug_period(st, i: int) -> void:
	var dr: Dictionary = st.d.t["stats"]["drug"]
	var side: bool = int(st.flags.get("drug_side_next", 0)) > 0
	st.flags["drug_side_next"] = 0
	if st.drug_points > 0 and not st.month_used.has("boost.%d" % i):
		boost(st, i)
	var fail := 0
	if side:
		fail = dr["side_fail_pct"]
	if st.drug_points > 0 and not st.month_used.has("boost"):
		fail = maxi(fail, attack_pct(st))
		st.inc("count.attack_periods")
	st.status["drug_fail_pct"] = fail


static func attack_pct(st) -> int:
	var at: Dictionary = st.d.t["stats"]["drug"]["attack"]
	return mini(at["fail_base_pct"] + at["fail_step_pct"] * st.drug_points, at["fail_cap_pct"])


## Month end, before the month-end events. Addicted and not one dose this month: the attack (fatigue, and now he knows), and the
## depth drops; at 0 he is clean. Deep (stage 3): the body wears down.
static func drug_month(st) -> void:
	var dr: Dictionary = st.d.t["stats"]["drug"]
	st.status["drug_high"] = 0
	st.status["drug_fail_pct"] = 0
	if st.drug_points > 0 and not st.month_used.has("boost"):
		var at: Dictionary = dr["attack"]
		Schedule.add_stat(st, "fatigue", at["fatigue_base"] + at["fatigue_step"] * st.drug_points)
		st.inc("count.attack_months")
		st.flags["drug_known"] = 1
		st.drug_points = maxi(0, st.drug_points - at["depth_drop"])
		if st.drug_points == 0:
			st.flags["drug_known"] = 0
			st.inc("count.clean")
	st.drug = st.drug_stage_of(st.drug_points)
	if st.drug >= 3:
		Rules.apply_effect(st, dr["deep_monthly_effect"], "drug")


## Discharge from the sanatorium: roll the discharge event of rest.json forced.
static func discharge(story, st) -> void:
	var de = st.d.rest_forced[0].get("discharge_event")
	if Schedule.truthy(de) and Rules.prob(st, de["prob"]):
		fire(story, st, de["event"])


# ---------- birthday ----------

static func day(story, st, dd: int) -> void:
	var e: Dictionary = st.d.events["evt_birthday"]
	var bd = e.get("date")
	if Schedule.truthy(bd) and st.date().substr(5) == bd.substr(0, 2) and dd == bd.substr(3).to_int():
		fire(story, st, e["id"])


# ---------- era, annual (11.3, 12.1) ----------

static func era(story, st, ids: Array) -> void:
	for eid in ids:
		fire(story, st, eid)


## Of the named rivals present that year (easter egg excluded), the 5 with the highest level on the road: [[id, level], ...].
static func annual_rivals(st, road: String) -> Array:
	var d = st.d
	var k: int = d.roads.find(road)
	var out := []
	for rid in d.rivals_named:
		var r: Dictionary = d.rivals_named[rid]
		if r.get("easter_egg", false) or not (r["present"][0] <= st.date() and st.date() <= r["present"][1]):
			continue
		var lv = null
		for s in r["stages"]:
			if st.date() >= s["from"]:
				lv = s["levels"][k]
		out.append([rid, lv, out.size()])
	out.sort_custom(func(a, b): return a[1] > b[1] if a[1] != b[1] else a[2] < b[2])    # stable, like Python's sort
	var res := []
	for x in out.slice(0, 5):
		res.append([x[0], x[1]])
	return res


## December: pick one of the four occasions to attend, or rest (fatigue reset). Ranking: my score = road reputation + r0(50);
## rival score = 5L(L+1) + r0(50); a rival score >= my score ranks ahead of me.
static func annual(story, st) -> Dictionary:
	var a: Dictionary = st.d.t["annual"]
	var opts := []
	for x in a["occasions"]:
		if Rules.cond(st, x["cond"]):
			opts.append(x)
	var pick = story.agent.annual(st, opts)
	var rec := {"month": st.date(), "occasions": pick}
	if pick == null:
		st.attr["fatigue"] = 0
		story.annuals.append(rec)
		return rec
	var occ: Dictionary = {}
	for x in opts:
		if x["id"] == pick:
			occ = x
			break
	if Schedule.truthy(a.get("attend_effect")):          # step 12c: attending is tiring
		Rules.apply_effect(st, a["attend_effect"], "annual")
	var g = st.rng.logic
	var me: int = st.rep(occ["road"]) + g.r0(50)
	var rank := 1
	for x in annual_rivals(st, occ["road"]):
		var L: int = x[1]
		if 5 * L * (L + 1) + g.r0(50) >= me:
			rank += 1
	rec["rank"] = rank
	for rw in a["ranking"]["rewards"]:
		if rw["rank"] == rank:
			st.corr[occ["road"]] += rw["rep_bonus"]
			st.track("annual", "rep_bonus." + occ["road"], rw["rep_bonus"])
			st.add_money(rw["prize"])
	st.inc("count.annual_rank.%d" % rank)
	story.annuals.append(rec)
	return rec
