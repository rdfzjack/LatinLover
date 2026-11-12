extends RefCounted
## Casting board (GDD 3.3, 6.1-6.5, 11.1 swap role and steal role, 11.3 the extra role after Valen's death). Port of sim/board.py.
## Numbers are in roles.json defaults.
##
## One board entry (a role snapshot, in st.story["board"]["roles"]):
##   {id, name, size, fame_gate, style_probs (the ones actually used), base_style, road, wants, tags, bonus_skill,
##    talkie, speech_line, fee, lead, rival_spec, opponents: [rival ...], house, source, intel: {...}}
## road is the road with the highest base style (used for the reputation bonus at release). intel is only for the UI:
## whether tags / style / habit are shown, the excluded color, and why the role cannot be signed (null = it can).
##
## Random-number order when building a board (copied from the Python side):
##   1. Draw roles in the order big, medium, small: the base counts, plus the extra medium/big roles from connections; the second
##      small slot of the first board holds the tutorial role. Drawing from the pool: index below(sum of weights); if no suitable role is
##      in the pool, a placeholder role is generated: main color below(4), wanted skill below(3), tag below(n).
##   2. The extra roles are, in order: pending_board (script), the widow-invested medium film, the transition medium film,
##      the small film after Valen's death.
##   3. Talkies: the 1927-10 board picks 1 with below(candidate count); later each candidate gets chance(percent).
##   4. Opponents: for each role by its rival_spec (unnamed rivals: see Audition.unnamed_rival; Valen's replacement below(2);
##      the named rival of a placeholder big film is drawn by weight with below(10)).
##   5. Long contract: below picks 3 of the roles that can be signed and marks them house.
##   6. Waiter intel: below(role count) picks one; tip-off: below picks among the medium and big films.
## All functions are static; st is an instance of core/state.gd.

const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")
const Audition = preload("res://core/audition.gd")
const Film = preload("res://core/film.gd")

const TIERS := ["small", "medium", "big"]
const RANK := {"small": 0, "medium": 1, "big": 2}


static func cfg(d) -> Dictionary:
	return d.role_cfg["board"]


static func board(st):
	return st.story["board"]


static func _year(st) -> int:
	return st.date().substr(0, 4).to_int()


# ---------- roles ----------

static func snapshot(st, r: Dictionary, src := "pool") -> Dictionary:
	var df: Dictionary = st.d.role_cfg
	var t: String = r["size"]
	var probs = r["style_probs"]
	var has_probs := Schedule.truthy(probs)
	var wants := []
	for k in r["wants"]:
		wants.append(k.duplicate())
	var spec := []
	for o in r["opponents"]:
		spec.append(o.duplicate())
	return {"id": r["id"], "name": r["name"], "size": t,
		"fame_gate": r["fame_gate"] if r.get("fame_gate") != null else df["fame_gate"][t],
		"style_probs": probs.duplicate() if has_probs else null, "base_style": probs.duplicate() if has_probs else null,
		"road": null, "wants": wants, "tags": r["tags"].duplicate(),
		"bonus_skill": r["bonus_skill"] if Schedule.truthy(r.get("bonus_skill")) else df["bonus_skill"],
		"talkie": r.get("talkie"), "speech_line": r.get("speech_line"),
		"fee": r["fee"] if Schedule.truthy(r.get("fee")) else df["fee"][t], "lead": r.get("lead"),
		"rival_spec": spec, "opponents": [], "house": false, "source": src, "intel": {}}


static func set_probs(e: Dictionary, probs: Array) -> void:
	e["style_probs"] = probs.duplicate()
	e["base_style"] = probs.duplicate()
	e["road"] = null


## The color with the highest probability; ties go to the earlier color.
static func main_of(probs: Array) -> int:
	var best := 0
	for c in 4:
		if probs[c] > probs[best]:
			best = c
	return best


## The main color gets top%, the other three colors share the rest equally, and any remainder goes to the earlier colors.
static func split_probs(main: int, top: int) -> Array:
	var rest := 100 - top
	var each := Rules.fdiv(rest, 3)
	var p := [each, each, each, each]
	p[main] = top
	var left := rest - each * 3
	for c in 4:
		if c != main and left:
			p[c] += 1
			left -= 1
	return p


## Generates a placeholder role when the pool has no suitable role (roles.json defaults.placeholder_gen).
## tags: the tag pool to draw from, or null for the main color's set.
static func placeholder(st, tier: String, tags = null) -> Dictionary:
	var d = st.d
	var g = st.rng.logic
	var c: Dictionary = d.role_cfg["placeholder_gen"]
	var main: int = g.below(4)
	var road: String = d.roads[main]
	var sk: Array = d.road_skills[road]
	var skill: String = sk[g.below(sk.size())]
	var pool: Array = tags if Schedule.truthy(tags) else c["tags_by_color"][road]
	var tag: String = pool[g.below(pool.size())]
	var probs := [c["other_style"], c["other_style"], c["other_style"], c["other_style"]]
	probs[main] = c["main_style"]
	st.story["seq"] += 1
	var opp := [{"unnamed": true}]
	if tier == "big":
		opp.append({"named_placeholder": true})
	var r := {"id": "gen%d" % st.story["seq"], "name": "placeholder role (%s)" % tier, "size": tier, "fame_gate": null,
		"style_probs": probs, "wants": [{"stat": skill, "target": c["wants_target"][tier]}], "tags": [tag],
		"bonus_skill": null, "talkie": null, "speech_line": null, "fee": null, "opponents": opp}
	return snapshot(st, r, "placeholder")


static func in_years(st, r: Dictionary) -> bool:
	var y := _year(st)
	return r["years_active"][0] <= y and y <= r["years_active"][1]


static func role_weight(st, r: Dictionary) -> int:
	var w := 0
	for t in r["tags"]:
		w += st.weights.get(t, 0)
	return 1 + mini(w, cfg(st.d)["weight_cap"])


static func _shares_tag(a: Array, b: Array) -> bool:
	for t in a:
		if b.has(t):
			return true
	return false


## Draws one role of the given size from the pool; if none, generates a placeholder. Small roles are drawn by board weight (6.1),
## the rest with equal probability. taken: a set (Dictionary) of role ids already on this board; tags: null or the tags to match.
static func draw(st, tier: String, taken: Dictionary, tags = null) -> Dictionary:
	var d = st.d
	var lim: int = cfg(d)["same_role_cap"][tier]
	var seen: Dictionary = st.story["boarded"]
	var cands := []
	for r in d.roles.values():
		if (r["size"] == tier and not r.get("tutorial", false) and in_years(st, r) and not taken.has(r["id"])
				and seen.get(r["id"], 0) < lim and (tags == null or _shares_tag(r["tags"], tags))):
			cands.append(r)
	if cands.is_empty():
		return placeholder(st, tier, tags)
	var ws := []
	var tot := 0
	for r in cands:
		var w: int = role_weight(st, r) if tier == "small" else 1
		ws.append(w)
		tot += w
	var v: int = st.rng.logic.below(tot)
	for k in cands.size():
		if v < ws[k]:
			return snapshot(st, cands[k])
		v -= ws[k]
	push_error("draw: weights out of range")
	return {}


static func tutorial(st) -> Dictionary:
	var d = st.d
	var r: Dictionary = {}
	for x in d.roles.values():
		if x.get("tutorial", false):
			r = x
			break
	var e := snapshot(st, r, "tutorial")
	set_probs(e, split_probs(Audition.player_main(st), 60))
	e["rival_spec"] = [{"unnamed": true, "main_level": d.t["rivals"]["tutorial"]["main_level"]}]
	return e


# ---------- rivals ----------

## The second match of a placeholder big film: of the 3 named rivals present that year (easter egg excluded) with the highest
## main-color level for the role, drawn 5:3:2.
static func named_for_placeholder(st, probs: Array) -> String:
	var d = st.d
	var c: Dictionary = d.role_cfg["placeholder_gen"]["big_named_rivals"]
	var main := main_of(probs)
	var ids := []
	for rid in d.rivals_named:
		if not d.rivals_named[rid].get("easter_egg", false) and Audition.rival_present(st, rid):
			ids.append(rid)
	var lv := {}
	for rid in ids:
		for s in d.rivals_named[rid]["stages"]:
			if st.date() >= s["from"]:
				lv[rid] = s["levels"][main]
	var top := ids.duplicate()
	top.sort_custom(func(a, b):
		if lv[a] != lv[b]:
			return lv[a] > lv[b]
		return ids.find(a) < ids.find(b))
	top = top.slice(0, c["take_top"])
	var w: Array = c["weight"].slice(0, top.size())
	var tot := 0
	for x in w:
		tot += x
	var v: int = st.rng.logic.below(tot)
	for k in top.size():
		if v < w[k]:
			return top[k]
		v -= w[k]
	push_error("named_for_placeholder: weights out of range")
	return ""


static func make_rivals(st, e: Dictionary) -> void:
	var out := []
	var probs: Array = e["style_probs"] if e["style_probs"] != null else []
	for o in e["rival_spec"]:
		if o.get("unnamed", false):
			out.append(Audition.unnamed_rival(st, e["size"], o.get("main_level"), probs))
		elif Schedule.truthy(o.get("named")):
			out.append(Audition.named_rival(st, o["named"]))
		else:
			out.append(Audition.named_rival(st, named_for_placeholder(st, e["style_probs"])))
	e["opponents"] = out


# ---------- building the board ----------

## List of this board's role snapshots (no opponents, talkie, house or intel yet).
static func compose(st) -> Array:
	var d = st.d
	var c := cfg(d)
	var sv: Dictionary = st.story
	var n: Dictionary = c["per_board"].duplicate()
	if st.val("connections") >= c["connections_extra_medium"]:
		n["medium"] += 1
	if st.val("connections") >= c["connections_extra_big"]:
		n["big"] += 1
	var out := []
	var taken := {}
	var tut: bool = int(st.flags.get("tutorial_board", 0)) == 0     # the first board of the game (six-year swap: 1924-03)
	st.flags["tutorial_board"] = 1
	for t in ["big", "medium", "small"]:
		for k in int(n[t]):
			var e: Dictionary
			if tut and t == "small" and k == n[t] - 1:
				e = tutorial(st)
			else:
				e = draw(st, t, taken)
			taken[e["id"]] = true
			out.append(e)
	# extra roles
	for r in sv["pending_board"]:
		out.append(r)
	sv["pending_board"] = []
	if st.flags.get("widow_invest", 0) == 1:
		st.flags["widow_invest"] = 2
		var e := draw(st, "medium", taken)
		if e["source"] == "pool":
			e["source"] = "widow_invest"
		taken[e["id"]] = true
		out.append(e)
	var left: int = sv["transition"][0]
	if left > 0:
		var e := draw(st, "medium", taken, d.tag_families[sv["transition"][1]])
		taken[e["id"]] = true
		out.append(e)
		sv["transition"][0] -= 1
	var v: Dictionary = c["after_valen_extra"]
	if Schedule.truthy(st.flags.get("valen_dead")) and st.date() <= v["until"]:
		var e := draw(st, v["size"], taken, v["tags"])
		taken[e["id"]] = true
		out.append(e)
	for e in out:
		if e["source"] == "pool" or e["source"] == "widow_invest":
			sv["boarded"][e["id"]] = sv["boarded"].get(e["id"], 0) + 1
	return out


static func assign_talkie(st, entries: Array) -> void:
	var d = st.d
	var c: Dictionary = d.role_cfg["talkie"]
	var g = st.rng.logic
	if st.date() < c["start"]:
		for e in entries:
			e["talkie"] = false
		return
	var rule: Dictionary = {}
	for x in c["ratio"]:
		if st.date() >= x["from"]:
			rule = x
	var cand := []
	for e in entries:
		if e["talkie"] == null:
			cand.append(e)
	for e in entries:
		if e["talkie"] == null:
			e["talkie"] = false
	if rule.has("count"):
		for _k in mini(rule["count"], cand.size()):
			var e: Dictionary = cand.pop_at(g.below(cand.size()))
			e["talkie"] = true
	else:
		for e in cand:
			e["talkie"] = g.chance(rule["pct"], 100)
	for e in entries:
		if e["talkie"] and e["speech_line"] == null:
			e["speech_line"] = d.role_cfg["speech_line"][e["size"]]


static func fame_gate(st, e: Dictionary) -> int:
	var g: int = e["fame_gate"]
	if e["size"] == "big" and Film.low_budget(st):
		g += cfg(st.d)["lowbudget_big_gate_add"]
	return g


## Whether the role can be signed: fame high enough, morals clause (step 12c: no big film for morals_months after an arrest or an
## unsuppressed scandal, flag morals_until = last blocked month index), long contract allows only house roles.
## Returns "" or the reason.
static func eligible(st, e: Dictionary) -> String:
	if st.attr["fame"] < fame_gate(st, e):
		return "out_of_reach"
	if e["size"] == "big" and st.flags.has("morals_until") and st.ym <= st.flags["morals_until"]:
		return "morals"
	if st.status["long_contract"] and not e["house"]:
		return "not a house role"
	return ""


## Builds a board: roles, style, opponents, talkie, house, intel. The result is stored in st.story["board"].
static func make(st) -> Dictionary:
	var d = st.d
	var c := cfg(d)
	var g = st.rng.logic
	var entries := compose(st)
	for e in entries:
		if e["road"] == null:
			e["road"] = d.roads[main_of(e["base_style"])]
		var key: String = "remembered." + e["id"]
		if Schedule.truthy(st.flags.get(key)):    # Remembered by the director: the player's main color +10 when it appears this time (7.4)
			e["style_probs"] = Audition.remembered_probs(e["style_probs"], Audition.player_main(st),
				d.t["habits"]["audition"]["result"]["remembered"]["main_style_add_pts"])
			st.flags[key] = 0
			e["intel"]["remembered"] = true
	assign_talkie(st, entries)
	for e in entries:
		make_rivals(st, e)
	if st.status["long_contract"]:
		var k: Dictionary = d.contract["long_contract"]
		var cand := []
		for e in entries:
			if st.attr["fame"] >= fame_gate(st, e):
				cand.append(e)
		for _i in mini(k["house_roles"], cand.size()):
			var e: Dictionary = cand.pop_at(g.below(cand.size()))
			e["house"] = true
			e["style_probs"] = Audition.remembered_probs(e["style_probs"], Audition.player_main(st), k["house_style_add"])
	# intel
	var ic: Dictionary = c["intel"]
	for e in entries:
		e["intel"]["tags"] = st.val("taste") >= ic["tag_taste"]
		var hb := []
		for rv in e["opponents"]:
			hb.append(st.val("connections") >= ic["habit_connections"] or
				(rv["id"] != null and st.cnt("duels." + rv["id"]) >= ic["habit_duels"]))
		e["intel"]["habit"] = hb
		if st.val("connections") >= ic["exclude_color_connections"]:
			var p: Array = e["style_probs"]
			var lo := 0
			for x in 4:
				if p[x] < p[lo]:
					lo = x
			e["intel"]["excluded"] = lo
	if Schedule.truthy(st.flags.get("waiter_tip")) and not entries.is_empty():
		var e: Dictionary = entries[g.below(entries.size())]
		var all := []
		for _rv in e["opponents"]:
			all.append(true)
		e["intel"]["habit"] = all
	while st.story["tipoff"] > 0:
		st.story["tipoff"] -= 1
		var cand := []
		for e in entries:
			if (e["size"] == "medium" or e["size"] == "big") and not e["intel"].get("style", false):
				cand.append(e)
		if not cand.is_empty():
			var e: Dictionary = cand[g.below(cand.size())]
			e["intel"]["style"] = true
			e["intel"]["tags"] = true
	for e in entries:
		var why := eligible(st, e)
		e["intel"]["eligible"] = why if why != "" else null
	st.story["board"] = {"month": st.ym, "roles": entries, "tried": [], "won": null}
	return st.story["board"]


# ---------- auditions ----------

## Returns "" when the idx-th role of this month's board can be signed up for, otherwise the reason.
static func can_try(st, idx: int) -> String:
	var b = board(st)
	if b == null or b["month"] != st.ym:
		return "no board this month"
	if b["won"] != null:
		return "this board already gave a role"
	if b["tried"].size() >= cfg(st.d)["audition_tries"]:
		return "this board was already tried twice"
	if b["tried"].has(idx):
		return "this role was already tried"
	var e: Dictionary = b["roles"][idx]
	if not b["tried"].is_empty() and RANK[e["size"]] >= RANK[b["roles"][b["tried"][-1]]["size"]]:
		return "the second try must be a lower size than the first"
	return eligible(st, e)


## Signs up for the idx-th role on the board and plays the audition. A film contract is created when a role or a supporting
## part is won. Returns the audition result ({} and an error when the role cannot be tried).
static func try_role(st, idx: int, agent) -> Dictionary:
	var why := can_try(st, idx)
	if why != "":
		push_error(why)
		return {}
	var b: Dictionary = board(st)
	var e: Dictionary = b["roles"][idx]
	b["tried"].append(idx)
	var res := Audition.audition(st, e, agent, e["opponents"], e["style_probs"])
	var support := false
	if res["result"] == "narrow_loss" and agent.accept_support(st, e):
		support = true
	if res["result"] == "won" or support:
		b["won"] = idx
		var pers: bool = (not support) and Film.can_go_personally(st, e) and agent.go_personally(st, e)
		res["film"] = Film.new_film(st, e, Film.board_locks(st, e["size"], support), support, pers)["id"]
	res["support"] = support
	st.inc("count.audition")
	if res["result"] == "won":
		st.inc("count.audition_won")
		st.inc("count.audition_won." + e["size"])
	st.inc("count.audition." + e["size"])
	return res


## After the board is built, lets the player sign up one by one until giving up, winning a role, or having tried twice.
static func run(st, agent) -> Array:
	var out := []
	while true:
		var b: Dictionary = board(st)
		var ok := []
		for i in b["roles"].size():
			if can_try(st, i) == "":
				ok.append(i)
		if ok.is_empty():
			break
		var i = agent.pick_role(st, b, ok)
		if i == null:
			break
		out.append(try_role(st, i, agent))
	return out


# ---------- auditions outside the board (11.1) ----------

## A single match (swap role, steal role). Returns true when the player wins.
static func one_match(st, agent, role: Dictionary, rival: Dictionary) -> bool:
	var ctx := {"roles": role, "rounds": 0, "opponents": rival, "levels": Audition.player_levels(st)}
	var colors: Array = agent.deck(st, ctx)
	var m := Audition.play_match(st, Audition.build_deck(ctx["levels"], colors), rival, role["style_probs"], agent)
	if rival["id"] != null:
		st.inc("duels." + rival["id"])
	return m["score_line"][0] >= Audition.cfg(st.d)["rounds_to_win"]


## Swap role: play a medium audition; a win takes the next period for shooting. Does not fire when the next period is taken
## (the caller checks first).
static func swap_role(st, i: int, agent) -> bool:
	var d = st.d
	var c: Dictionary = d.role_cfg["shoot"]["swap_role"]
	var e := draw(st, c["size"], {})
	if e["source"] == "pool":
		st.story["boarded"][e["id"]] = st.story["boarded"].get(e["id"], 0) + 1
	e["road"] = d.roads[main_of(e["base_style"])]
	e["talkie"] = Schedule.truthy(e["talkie"]) and st.date() >= d.role_cfg["talkie"]["start"]
	if e["talkie"] and e["speech_line"] == null:
		e["speech_line"] = d.role_cfg["speech_line"][e["size"]]
	var rv := Audition.unnamed_rival(st, e["size"], null, e["style_probs"])
	var win := one_match(st, agent, e, rv)
	if win:
		var nxt := Film.next_period(st, i)
		var pers: bool = Film.can_go_personally(st, e) and agent.go_personally(st, e)
		Film.new_film(st, e, [nxt].slice(0, c["period_count"]), false, pers)
	return win


## Steal role: an unnamed rival comes for a role not yet shot; on a loss the film contract is void.
static func steal_role(st, agent) -> bool:
	var f: Dictionary = {}
	for x in Film.films(st):
		if x["status"] == "to_shoot":
			f = x
			break
	var role: Dictionary = f["roles"]
	var rv := Audition.unnamed_rival(st, role["size"], null, role["style_probs"])
	var win := one_match(st, agent, role, rv)
	if not win:
		f["status"] = "stolen"
		Film.update_status(st)
	return win


# ---------- scripts (6.5) ----------

static func script_ok(st, kind: String) -> bool:
	var c: Dictionary = st.d.role_cfg["script"]
	var sv: Dictionary = st.story["script"]
	var y := _year(st)
	if not Rules.cond(st, c[kind]["cond"]):
		return false
	if kind == "co_written":
		return not sv["co_written"] and sv["self_written"] != y and sv["duv_written"] != y
	return sv[kind] != y


## Start-of-month action: self_written / duv_written / co_written. The next board gets one more role.
## color: the color the player picks for self_written and co_written (0-3; ignored for duv_written). Returns "" or the reason.
static func write_script(st, kind: String, color := -1) -> String:
	var d = st.d
	var c: Dictionary = d.role_cfg["script"]
	if not c.has(kind) or not script_ok(st, kind):
		return "cannot %s now" % kind
	if kind != "duv_written" and (color < 0 or color >= 4):
		return "a color must be given"
	var sv: Dictionary = st.story["script"]
	var y := _year(st)
	var tier: String = c[kind]["size"]
	st.story["seq"] += 1
	var main: int
	var want := []
	if kind == "duv_written":
		main = Audition.player_main(st)
		var b: Dictionary = st.bonus()
		var names := ["stamina", "education", "loyalty", "looks", "discipline", "crime"]
		var top := names.duplicate()
		top.sort_custom(func(x, z):
			var vx: int = st.val(x, b)
			var vz: int = st.val(z, b)
			if vx != vz:
				return vx > vz
			return names.find(x) < names.find(z))
		for n in top.slice(0, 2):
			want.append({"stat": n, "target": maxi(1, Rules.fdiv(st.val(n, b) * c["duv_written"]["wants_pct"], 100))})
		Rules.apply_effect(st, c["duv_written"]["favor"], "event")
		sv["duv_written"] = y
	else:
		main = color
		want = [{"stat": d.road_skills[d.roads[main]][0], "target": d.role_cfg["placeholder_gen"]["wants_target"][tier]}]
		if kind == "co_written":
			sv["co_written"] = 1
			sv["self_written"] = y
			sv["duv_written"] = y
		else:
			sv["self_written"] = y
	var opp := [{"unnamed": true}]
	if tier == "big":
		opp.append({"named_placeholder": true})
	var r := {"id": "script%d" % st.story["seq"], "name": "script role (%s)" % kind, "size": tier, "fame_gate": null,
		"style_probs": split_probs(main, c["main_style"]), "wants": want, "tags": [], "bonus_skill": null,
		"talkie": null, "speech_line": null, "fee": null, "opponents": opp}
	st.story["pending_board"].append(snapshot(st, r, "script"))
	return ""
