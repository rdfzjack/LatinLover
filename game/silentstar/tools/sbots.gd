extends RefCounted
## Strategy bots that look for strong results (PLAN step 2, 2026-11; the list was agreed with the user).
## Built on bots.gd's Bot for auditions and event options; the schedule is a plain goal list:
##   goals = [{stat, to, via: [entries]}, ...] in order; a goal is done when the trained value (skill) or the attribute reaches `to`.
##   Each period takes the first entry of the first unfinished goal that can be done now. A class he cannot pay for sends him to a
##   money job; a goal with nothing doable now is skipped (e.g. grooming before lounge lizard opens).
## Rest: when this period would push the slack-off chance (scale fatigue - scale discipline) to slack_line % or more, or make him
## sick, he rests (home; the resort when he is rich and very tired).
## Run with tools/sreport.gd.

const Bots = preload("res://tools/bots.gd")
const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")
const Street = preload("res://core/street.gd")
const Audition = preload("res://core/audition.gd")
const Events = preload("res://core/events.gd")
const Film = preload("res://core/film.gd")
const Board = preload("res://core/board.gd")
const H = Bots.H

## Main-road training: [skill, entries that train it, best first].
const ROAD_GOALS := {
	"tough": [["fight", ["class_h1"]], ["riding", ["class_h2"]], ["nerve", ["class_h1", "job_collector"]]],
	"lover": [["acting", ["class_l1"]], ["physique", ["class_l3"]], ["grooming", ["job_l_night"]]],
	"culture": [["writing", ["class_c1"]], ["taste", ["class_c1"]], ["speech", ["job_collector", "class_c3"]]],
	"savvy": [["negotiation", ["job_runner"]], ["rapport", ["job_runner"]], ["insight", ["job_runner"]]],
}
## Jobs to earn with, first doable wins (no crime jobs here).
const ROAD_MONEY := {
	"tough": ["job_dock1"], "lover": ["job_l_day", "job_server"], "culture": ["job_c_money", "job_server"],
	"savvy": ["job_server", "job_dock1"],
}
## Opening questions per road (same as bots.gd ROAD_SETUP).
const ROAD_ORIGIN := {"tough": [0, 0, 3], "lover": [3, 2, 3], "culture": [4, 1, 3], "savvy": [1, 1, 3]}
## Tough road (2026-11 round): the dock (looks -1 a day) is his only tuition job; under this looks he leaves it. Waiting tables
## (fight -0/1) is then allowed as his fallback if TOUGH_SERVER.
const TOUGH_FLOOR := 66
const TOUGH_SERVER := true
## Level lines of the staged goal list (GDD 2.4): level 6 = 210, level 7 = 280; 999 = the three skills trained to 100.
const LINES := [210, 280, 999]
## Off-road attribute gates of the boards (GDD 6.1) and how a bot trains each, best first.
const ATTR_VIA := {"looks": ["class_l1", "class_l3"], "education": ["class_c3", "class_yi"],
	"loyalty": ["class_yi", "job_l_day", "job_c_slow"], "stamina": ["job_dock1", "class_l3"]}
const ATTR_RATE := 12          # a period of training adds about this much to one of these attributes (rough, for the prep check)
## Speech for the talkies (a talkie needs speech >= its line to sign up, big 70, GDD 6.4): tutoring (also education and
## discipline), else collecting.
const SPEECH_TALKIE := {"stat": "speech", "to": 70, "via": ["class_c3", "job_collector"]}
## Outfits that lift looks, cheapest first (keep looks >= 60 so he may audition).
const LOOKS_OUTFITS := ["suit_old", "riding_habit", "suit_custom", "evening_gown", "fur_white"]


class SBot:
	extends "res://tools/bots.gd".Bot

	var goal_list := []            # see the file header
	var money_jobs := []           # tried first when he needs money (may include crime jobs on purpose)
	var crime_ok := false          # may the fallback money job be a crime job
	var slack_line := 10           # rest when the slack-off chance after this period would reach this %
	var class_cap := 0             # stop a class after this many periods (0 = no cap)
	var thresh := {"big": 0.12, "medium": 0.2, "small": 0.0}
	var gear_reserve := 200        # money kept on top of two months of living costs when buying gear
	var gear_months := 2
	var stop_when_full := false    # type-1 bots: the report stops the game when the main road is full
	var ignore_looks := false      # fur strongman: no acting class for looks (his outfit set and the diet carry them)
	var looks_floor := 80          # money jobs that cost looks are avoided while displayed looks are under this
	var stamina_floor := 50        # stamina under this: train it back to 80 first (dock, else the dance class); 0 = never
	var stamina_fix := false
	var looks_late := false        # tough road: ignore looks (dock freely, no acting class) until the main road is full, then fix them
	# rules of the new bots (2026-11, closer to a skilled player); the older bots keep new_rules false and play as before
	var new_rules := false
	var stam_to := 300             # stamina target: the fine lifestyle while under it; in the opening year also trained (dock / dance)
	var stam_open_until := 12      # the opening phase: trained stamina only before this month index (1925-01)
	var stam_via := ["job_dock1", "class_l3"]
	var disc_on := true            # keep discipline high enough that the slack-off chance stays at 0 (church with Sil)
	var succ_line := 0.9           # rest when the expected success of this period is under this
	var prep_on := true            # read the next board and train a missing off-road gate of its big / medium role
	var prep_fame_slack := 20      # ... when fame is within this of that role's fame gate
	var prep_periods := 8          # ... and the gap can be closed in this many periods

	func _init(sd := 1) -> void:
		super(sd)

	## The road skills as goals to 100.
	static func road_goals(rd: String, cap := 100) -> Array:
		var out := []
		for x in ROAD_GOALS[rd]:
			out.append({"stat": x[0], "to": cap, "via": x[1]})
		return out

	## Staged goal list: every road in `roads` to level 6 (rep 210), then all to level 7 (280), then all full.
	## `lines` per road may be cut short (e.g. savvy only to 210).
	static func staged(roads: Array, lines := LINES, caps := {}) -> Array:
		var out := []
		for ln in lines:
			for rd in roads:
				if caps.has(rd) and int(caps[rd]) < int(ln):
					continue
				out.append({"road": rd, "rep": ln})
		return out

	## The 56 non-decreasing color lists of five cards.
	static func mixes() -> Array:
		var out := []
		for a in 4:
			for b in range(a, 4):
				for c in range(b, 4):
					for d in range(c, 4):
						for e in range(d, 4):
							out.append([a, b, c, d, e])
		return out

	func setup_road(rd: String, nm: String) -> void:
		road = rd
		name = nm
		origin = ROAD_ORIGIN[rd].duplicate()
		gear_road = rd
		place = Bots.ROAD_PLACE[rd]
		money_jobs = ROAD_MONEY[rd].duplicate()
		if rd == "tough":
			looks_floor = TOUGH_FLOOR
			looks_late = true

	## Goals of this period (subclasses may change them with the date or the state).
	func goals(_g, _P: Dictionary, _i: int) -> Array:
		return goal_list

	func reached(st, gl: Dictionary) -> bool:
		if gl.has("road"):
			var full := true
			for x in ROAD_GOALS[gl["road"]]:
				if st.skill[x[0]] < 100:
					full = false
			return full or (int(gl["rep"]) < 999 and st.rep(gl["road"]) >= int(gl["rep"]))
		var s: String = gl["stat"]
		var v: int = st.skill[s] if st.skill.has(s) else st.attr[s]
		return v >= int(gl["to"])

	# ---------- the month ----------
	func plan(g) -> Array:
		var st = g.st
		if Schedule.truthy(st.forced_rest) or Schedule.truthy(st.void_next):
			return ["rest_home", "rest_home", "rest_home"]
		var P := {"fat": st.val("fatigue"), "money": st.money, "cls": {}}
		var out := []
		for i in 3:
			var f = g.hooks.locked(st, i)
			if f != null:
				P["fat"] += H.workdays(st, i) * Film.shoot_cfg(st.d)["fatigue"][f["size"]]
				out.append("rest_home")
				continue
			var e: String = decide(g, P, i)
			apply(g, P, i, e)
			out.append(e)
		return out

	func decide(g, P: Dictionary, i: int) -> String:
		var e = choose(g, P, i)
		if e == null:
			return rest(g, P, i)
		if needs_rest(g, P, i, e):
			return rest(g, P, i)
		return e

	## The entry of this period before the rest check: the first doable goal, or a money job.
	## Before the bot's own goals: looks under 62 (under 60 he cannot audition), stamina under the floor, the opening stamina target,
	## discipline for a zero slack-off chance, and the off-road gate of the next board's big or medium role.
	func choose(g, P: Dictionary, i: int):
		var st = g.st
		var gs: Array = pre_goals(g, P, i) + goals(g, P, i)
		for gl in gs:
			if reached(st, gl):
				continue
			for e in via_of(st, gl):
				var r := usable(g, P, i, e)
				if r == "ok":
					return e
				if r == "broke":
					return money_job(g, P)
		return money_job(g, P)

	## Entries that train a goal: a road goal trains its lowest unfinished skill first.
	func via_of(st, gl: Dictionary) -> Array:
		if not gl.has("road"):
			return gl["via"]
		var xs: Array = ROAD_GOALS[gl["road"]].duplicate()
		xs.sort_custom(func(a, b): return st.skill[a[0]] < st.skill[b[0]])
		var out := []
		for x in xs:
			if st.skill[x[0]] < 100:
				for e in x[1]:
					if not out.has(e):
						out.append(e)
		return out

	func pre_goals(g, P: Dictionary, i: int) -> Array:
		var st = g.st
		var gs := []
		# stamina: the flagpole, the column and the church take 1 a day, and under 30 even the dock is closed
		if stamina_floor > 0:
			if st.attr["stamina"] < stamina_floor:
				stamina_fix = true
			elif st.attr["stamina"] >= 80:
				stamina_fix = false
			if stamina_fix:
				gs.append({"stat": "stamina", "to": 80, "via": ["job_dock1", "class_l3"]})
		if st.val("looks") < 62 and not skip_looks(st):
			gs.append({"stat": "looks", "to": st.attr["looks"] + 1, "via": ["class_l1"]})
		if not new_rules:
			return gs
		if stam_to > 0 and st.ym < stam_open_until:
			gs.append({"stat": "stamina", "to": stam_to, "via": stam_via})
		if want_disc(st) and st.val("discipline") < disc_to() - 10:
			gs.append({"stat": "discipline", "to": disc_to(), "via": ["job_church_aid"]})
		if prep_on:
			var pg = prep_goal(st, i)
			if pg != null:
				gs.append(pg)
		return gs

	## Discipline that keeps the slack-off chance at 0 up to fatigue = half the stamina target (scale fatigue = scale discipline).
	func disc_to() -> int:
		var s := maxi(stam_to, 160)
		return s * 3 / 16 + 12

	func want_disc(_st) -> bool:
		return disc_on

	## The fame gate of a role at the board of `month` (the next-board page shows it; GDD 6.1, 9.0, 8.4).
	static func gate_at(st, e: Dictionary, month: String) -> int:
		var g: int = int(e["fame_gate"])
		if Audition.curve_on(st.d):
			var tb: Dictionary = Audition.curve_cfg(st.d)["fame_gate"]
			if tb.has(e["size"]):
				var y := month.substr(0, 4)
				for k in tb[e["size"]]:
					if String(k) <= y:
						g = int(tb[e["size"]][k])
		if e["size"] == "big" and Film.low_budget(st):
			g += int(Board.cfg(st.d)["lowbudget_big_gate_add"])
		return g

	## The next board's big (then medium) role: when fame is about there and its off-road gate is short by what a few periods can
	## train before the board, a goal for that attribute.
	func prep_goal(st, i: int):
		var nb: Dictionary = Board.next_board(st)
		if nb.is_empty():
			return null
		var left: int = (int(st.d.month_index[nb["month"]]) - st.ym) * 3 - i
		if left <= 0:
			return null
		for sz in ["big", "medium"]:
			for e in nb["roles"]:
				if e["size"] != sz or not prep_size(sz):
					continue
				if st.attr["fame"] + fame_room(st, left) < gate_at(st, e, nb["month"]):
					continue
				for cl in e["gates"]:
					for c in cl:
						var a: String = c[0]
						var need: int = int(c[2])
						var gap: int = need - st.val(a)
						if gap > 0 and ATTR_VIA.has(a) and gap <= ATTR_RATE * mini(left, prep_periods):
							return {"stat": a, "to": st.attr[a] + gap + 3, "via": attr_via(a)}
		return null

	func prep_size(_sz: String) -> bool:
		return true

	## How much fame the bot expects to add before the board (flagpole bots add more).
	func fame_room(_st, _left: int) -> int:
		return prep_fame_slack

	func attr_via(a: String) -> Array:
		return stam_via if a == "stamina" else ATTR_VIA[a]

	func reserve(st) -> int:
		return living(st) * 2 + 50

	## "ok", "broke" (a class he cannot pay for this period) or "no".
	func usable(g, P: Dictionary, i: int, e: String) -> String:
		var st = g.st
		var d = g.d
		if d.classes.has(e):
			if class_cap > 0 and st.cnt("class_periods." + e) + P["cls"].get(e, 0) >= class_cap:
				return "no"
			if P["money"] + delta(g, P, i, e)[1] < reserve(st):
				return "broke"
			return "ok"
		if d.jobs.has(e):
			if not H.can_do_job(st, e):
				return "no"
			if is_crime(d, e) and not crime_ok and not money_jobs.has(e):
				return "no"
			return "ok"
		return "ok" if Schedule.validate(st, e) == "" else "no"

	static func costs_looks(d, jid: String) -> bool:
		for e in d.jobs[jid]["daily_effect"]:
			if e["stat"] == "looks" and int(e["add"][1]) < 0:
				return true
		return false

	static func is_crime(d, jid: String) -> bool:
		return Schedule.truthy(d.jobs[jid].get("crime_job"))

	## Money: the bot's own list first, else the best wage minus fatigue. With looks under looks_floor jobs that cost looks are avoided
	## (looks under 60 bars auditions).
	func money_job(g, _P: Dictionary):
		var st = g.st
		var d = g.d
		var low: bool = st.val("looks") < looks_floor and not skip_looks(st)
		for jid in money_jobs:
			if H.can_do_job(st, jid) and not (low and costs_looks(d, jid)):
				return jid
		var best = null
		for jid in d.jobs:
			if is_crime(d, jid) and not crime_ok:
				continue
			if not H.can_do_job(st, jid) or (low and costs_looks(d, jid)):
				continue
			if hurts_goals(st, jid) and not (road == "tough" and TOUGH_SERVER):
				continue                  # e.g. waiting tables (fight -0/1) would undo the tough road's classes
			var score: float = Schedule.wage_of(st, jid) - 1.5 * H.job_fat(d.jobs[jid])
			if best == null or score > best[0]:
				best = [score, jid]
		return best[1] if best != null else null

	func skip_looks(st) -> bool:
		if ignore_looks:
			return true
		if not looks_late:
			return false
		for sk in st.d.road_skills[road]:
			if st.skill[sk] < 100:
				return true
		return false

	## Whether the job lowers a skill or attribute that is still an unfinished goal.
	func hurts_goals(st, jid: String) -> bool:
		for e in st.d.jobs[jid]["daily_effect"]:
			if int(e["add"][0]) >= 0 and int(e["add"][1]) >= 0:
				continue
			for gl in goal_list:
				if gl.has("road"):
					for x in ROAD_GOALS[gl["road"]]:
						if x[0] == e["stat"] and st.skill[x[0]] < 100:
							return true
				elif gl["stat"] == e["stat"] and not reached(st, gl):
					return true
		return false

	## Slack-off chance % at fatigue f (GDD 5.1.1).
	func slack_pct(st, f: int) -> int:
		var div: int = int(st.d.t["stats"]["scale"]["div10"]["fatigue"])
		var sf: int = mini(100, Rules.fdiv(maxi(f, 0) * 10, div))
		return clampi(sf - Rules.scale_of(st, "discipline"), 0, int(st.d.t["stats"]["slack"]["cap_pct"]))

	## Rest (2026-11): the slack-off chance at the start of the period >= slack_line %, or the period would bring him near the sick
	## line (fatigue - stamina >= 0; sick at 10), or its expected daily success is under succ_line.
	func needs_rest(g, P: Dictionary, i: int, e: String) -> bool:
		if e.begins_with("rest_"):
			return false
		var st = g.st
		if not new_rules:
			var after: int = maxi(0, P["fat"] + delta(g, P, i, e)[0])
			return slack_pct(st, after) >= slack_line or after - st.val("stamina") >= 10
		var df: int = delta(g, P, i, e)[0]
		if slack_pct(st, P["fat"]) >= slack_line:
			return true
		if P["fat"] + df - st.val("stamina") >= 0:
			return true
		# low expected success: rest when fatigue is the reason (rested, the period would clear the line); a job whose line his
		# stat barely clears is worked anyway (resting would not help)
		var line: float = succ_line if not e.begins_with("job_") else succ_line - 0.2
		if success_p(g, e, P["fat"] + df / 2) >= line:
			return false
		return success_p(g, e, df / 2) >= line

	## Expected chance that a day of this entry succeeds at fatigue f (GDD 5.1; the bot sees its stats and fatigue, not the dice).
	func success_p(g, e: String, f: int) -> float:
		var st = g.st
		var d = g.d
		var pe: Array = Schedule.parse_entry(e)
		f = maxi(f, 0)
		if pe[0] == "class":
			var h: float = maxf(st.val(str(d.classes[pe[1]].get("success_stat", "stamina"))), 0) / 2.0
			if f <= h:
				return 1.0
			var t := 0.0
			for k in 11:
				t += minf(1.0, (h + h * k / 10.0 + 1.0) / (f + 1.0))
			return t / 11.0
		if pe[0] == "job":
			var p := 1.0
			for kv in Schedule.job_lines(st, d.jobs[pe[1]]):
				p *= clampf((st.val(kv[0]) - int(kv[1]) + 1.0) / (f + 1.0), 0.0, 1.0)
			return p
		return 1.0

	func rest(g, P: Dictionary, i: int) -> String:
		var st = g.st
		var cost: int = Schedule.place_cost(st, "place_resort") * H.alldays(st, i)
		if not Schedule.truthy(st.status["sick"]) and P["fat"] >= 100 and P["money"] - cost >= reserve(st) * 2:
			return "rest_outing@place_resort"
		return "rest_home"

	# ---------- month start: gear, looks ----------
	func month_start(_story, st) -> void:
		set_life(st)
		buy_gear(st)
		keep_looks(st)

	## The fine lifestyle (stamina +10 a month for 40 a month) while stamina is under the target and he can afford it.
	func set_life(st) -> void:
		if not new_rules or stam_to <= 0:
			return
		st.lifestyle = "life_fine" if st.val("stamina") < stam_to and st.money >= 200 else "life_normal"

	## Bot.month_start with a configurable reserve.
	func buy_gear(st) -> void:
		var rd = gear_road
		if not buy or rd == null:
			return
		var rsv: int = gear_months * living(st) + gear_reserve
		for _n in 4:
			var base: int = st.rep(rd)
			var best = null
			for entry in ["clothing_store", "general_store"]:
				for iid in Street.shelf(st, entry):
					var it: Dictionary = st.d.items[iid]
					if it["class"] == "consumable" or st.items.has(iid):
						continue
					var p: int = Street.price(st, entry, it["price"])
					if st.money - p < rsv:
						continue
					var old := {"outfit": st.equip["outfit"], "accessory": st.equip["accessory"].duplicate()}
					st.items.append(iid)
					var gain: int = H.best_equip(st, rd) - base
					st.items.remove_at(st.items.rfind(iid))
					st.equip = old
					if gain > 0 and (best == null or float(gain) / float(p) > best[0]):
						best = [float(gain) / float(p), entry, iid]
			if best == null:
				break
			Street.buy(st, best[1], best[2])
			st.inc("count.gear_spend", Street.price(st, best[1], st.d.items[best[2]]["price"]))
		H.best_equip(st, rd)

	## Looks under 60 bars auditions (traits.json): wear, or buy, the cheapest outfit that lifts the displayed looks to 60.
	func keep_looks(st) -> void:
		if st.val("looks") >= 60:
			return
		var old = st.equip["outfit"]
		for iid in LOOKS_OUTFITS:
			var own: bool = st.items.has(iid)
			var p: int = Street.price(st, "clothing_store", st.d.items[iid]["price"])
			if not own and st.money - p < living(st):
				continue
			if not own:
				st.items.append(iid)
			st.equip["outfit"] = iid
			var ok: bool = st.val("looks") >= 60
			if not own:
				st.items.remove_at(st.items.rfind(iid))
			if ok:
				if not own:
					Street.buy(st, "clothing_store", iid)
					st.inc("count.looks_outfit_buy")
				st.equip["outfit"] = iid
				return
		st.equip["outfit"] = old

	# ---------- auditions: every five-card color mix ----------
	func pick_role(st, b: Dictionary, ok: Array):
		if b["tried"].is_empty():
			note_big(st, b, ok)          # report only: what happened to the big role of this board (bots.gd)
		var by := {}
		for i in ok:
			var sz: String = b["roles"][i]["size"]
			if not by.has(sz):
				by[sz] = []
			by[sz].append(i)
		for t in ["big", "medium", "small"]:
			if not by.has(t):
				continue
			var bp := -1.0
			var bi := -1
			for i in by[t]:
				var p := role_p(st, b["roles"][i])
				if p > bp:
					bp = p
					bi = i
			if bp >= float(thresh[t]):
				return bi
		return null

	func role_p(st, e: Dictionary) -> float:
		var lv: Array = Audition.player_levels(st)
		var p := 1.0
		for rv in e["opponents"]:
			p *= best_deck(st, lv, rv, e["style_probs"])[0]
		return p

	func deck(st, ctx) -> Array:
		return best_deck(st, ctx["levels"], ctx["opponents"], ctx["roles"]["style_probs"])[1].duplicate()

	## Best of all 56 color mixes of five cards: [win rate, colors].
	func best_deck(st, levels: Array, rival: Dictionary, probs: Array) -> Array:
		var d = st.d
		var est = H.est_of(d)
		var fame_hi: bool = st.attr["fame"] > rival["fame"]
		var key := "full|%s|%s|%d|%s|%s" % [str(levels), str(rival["levels"]), rival["k"], str(probs), str(fame_hi)]
		if est.cache.has(key):
			return est.cache[key]
		var theirs: Array = Audition.opponent_deck(d, rival, probs)
		var r := [-1.0, [0, 0, 0, 0, 0]]
		for cols in mixes():
			var mine: Array = Audition.build_deck(levels, cols)
			var terms := []
			for f in 4:
				if probs[f] != 0:
					terms.append(probs[f] * est.p_field(mine, theirs, f, fame_hi))
			var p: float = H.fsum(terms) / 100.0
			if p > r[0]:
				r = [p, cols]
		est.cache[key] = r
		return r


# ---------- type 1: main road only, the report stops when it is full ----------

class MainOnly:
	extends SBot

	func setup(rd: String) -> void:
		setup_road(rd, "full_" + rd)
		goal_list = road_goals(rd)
		stop_when_full = true


## Type 1, tough without caring about looks (dock all the way, no acting class): how fast the road itself trains.
class MainOnlyNoLooks:
	extends MainOnly

	func setup(rd: String) -> void:
		super(rd)
		name = "full_tough_nolooks"
		looks_floor = 0
		ignore_looks = true


# ---------- type 2 ----------

## 1. Main road, then savvy (the user's own play). Savvy main: then lover.
class MainSavvy:
	extends SBot

	func setup(rd: String) -> void:
		setup_road(rd, "main_savvy_" + rd)
		goal_list = road_goals(rd) + road_goals("lover" if rd == "savvy" else "savvy")


## 2. Lover: the second road first (savvy matures fast and earns auditions), then lover.
class LoverSideFirst:
	extends SBot

	func setup(_rd: String) -> void:
		setup_road("lover", "lover_side_first")
		goal_list = road_goals("savvy") + road_goals("lover")


## 4. Like 1, but spends all money above one month of living costs on the road's gear.
class GearMax:
	extends MainSavvy

	func setup(rd: String) -> void:
		super(rd)
		name = "gear_max_" + rd
		gear_months = 1
		gear_reserve = 0


## 5. Four colors (the user's play): savvy first, then stamina (or discipline), then lover, tough and culture with each class
## only to level 2 (8 periods); a goal that is stuck is skipped. Every audition uses the best five-card mix.
class FourColor:
	extends SBot

	var variant := "stamina"

	func setup(rd: String) -> void:
		variant = rd
		setup_road("savvy", "four_color_" + rd)
		class_cap = 8
		var base := {"stat": "stamina", "to": 300, "via": ["job_dock1"]} if rd == "stamina" else \
			{"stat": "discipline", "to": 300, "via": ["job_church_aid"]}
		goal_list = road_goals("savvy") + [base] + road_goals("lover") + road_goals("tough") + road_goals("culture")
		money_jobs = ["job_server", "job_dock1"]


## 6. Literate tough guy: tough main, education second (church to discipline 90 so tutoring sticks, then tutoring to 150); collecting for speech and nerve; moneylending from
## 1927 for the money (a crime job on purpose).
class LiterateTough:
	extends SBot

	func setup(_rd: String) -> void:
		setup_road("tough", "literate_tough")
		goal_list = [{"stat": "fight", "to": 100, "via": ["class_h1"]}, {"stat": "discipline", "to": 90, "via": ["job_church_aid"]},
			{"stat": "education", "to": 150, "via": ["class_c3"]},
			{"stat": "riding", "to": 100, "via": ["class_h2"]}, {"stat": "nerve", "to": 100, "via": ["class_h1"]},
			{"stat": "speech", "to": 70, "via": ["job_collector", "class_c3"]}]
		money_jobs = ["job_loan", "job_collector", "job_dock1"]


## 9. Pious moneylender: the literate tough guy who works the church whenever crime reaches 100, so crime stays put and he is
## rarely searched; spends the money on gear.
class PiousLender:
	extends LiterateTough

	func setup(rd: String) -> void:
		super(rd)
		name = "pious_lender"
		gear_months = 1
		gear_reserve = 0

	func choose(g, P: Dictionary, i: int):
		var e = super(g, P, i)
		if e != null and g.d.jobs.has(e) and is_crime(g.d, e) and g.st.val("crime") >= 100 \
				and H.can_do_job(g.st, "job_church_aid", 0):
			return "job_church_aid"
		return e


## 7. Smart gambler: main road + savvy; buys when the dealer is around (a month of living costs kept) and keeps the doses;
## takes one only before a shooting period of a lead medium or big film of his road. Detox at the deepest stage.
class Gambler:
	extends MainSavvy

	func setup(rd: String) -> void:
		super(rd)
		name = "gambler_" + rd

	func stock(st) -> int:
		return int(st.flags.get("drug_stock", 0))

	func buy_doses(story, st, keep: int) -> void:
		var n: int = int(st.flags.get("dealer_stock", 0))
		var price: int = int(st.flags.get("dealer_price", 0))
		while n > 0 and st.money - price * n < keep:
			n -= 1
		if n > 0:
			story.buy_drug(st, n)

	func month_start(story, st) -> void:
		super(story, st)
		if st.drug >= 3:
			story.send_detox(st)
			return
		buy_doses(story, st, living(st))

	func bet_film(story, st, i: int) -> bool:
		var f = story.locked(st, i)
		return f != null and not f["support"] and f["roles"]["road"] == road and (f["size"] == "medium" or f["size"] == "big")

	func before_period(story, st, i: int) -> void:
		if stock(st) > 0 and bet_film(story, st, i) and Events.boost_reason(st, i) == "":
			story.boost(st, i)


## 8. Hoard, then get religion: buys every dose he can while discipline is under the dealer's line, until he holds `hoard`;
## then the church to discipline 300; from then a dose before every shooting period and whenever fatigue reaches 200.
class HoardBaptize:
	extends Gambler

	var hoard := 8

	func setup(rd: String) -> void:
		super(rd)
		name = "hoard_baptize_" + rd

	func refuse_line(st) -> int:
		return int(st.d.t["stats"]["drug"]["refuse_discipline"])

	func hoarding(st) -> bool:
		return stock(st) < hoard and st.cnt("count.boost") == 0 and st.ym < 48

	func month_start(story, st) -> void:
		buy_gear(st)
		keep_looks(st)
		if st.drug >= 3:
			story.send_detox(st)
			return
		if hoarding(st) and st.val("discipline") < refuse_line(st):
			buy_doses(story, st, living(st))

	func goals(g, P: Dictionary, i: int) -> Array:
		if hoarding(g.st):
			return goal_list
		return [{"stat": "discipline", "to": 300, "via": ["job_church_aid"]}] + goal_list

	func needs_rest(g, P: Dictionary, i: int, e: String) -> bool:
		if hoarding(g.st) and e == "job_church_aid":
			return true
		return super(g, P, i, e)

	func before_period(story, st, i: int) -> void:
		if stock(st) <= 0 or hoarding(st) or Events.boost_reason(st, i) != "":
			return
		if story.locked(st, i) != null or st.val("fatigue") >= 200:
			story.boost(st, i)


## 10. Sick beauty: lover main + savvy; diet keeps stamina low; from 1927-10 he works the upstairs rooms only in months that
## start in the sick state (the search at month end reads the sick state of the last month end, and sick players are never
## arrested); in a month that starts healthy he works ordinary jobs without resting so that the month ends sick. The hospital
## at month start (any number of times a month) keeps the month-end sick index under 85 (90 is the sanatorium).
class SickBeauty:
	extends MainSavvy

	const LATE_FROM := 45          # 1927-10

	func setup(rd: String) -> void:
		super(rd)
		name = "sick_beauty"
		crime_ok = true
		stamina_floor = 0

	func month_start(story, st) -> void:
		super(story, st)
		if st.ym >= LATE_FROM - 3:
			st.lifestyle = "life_diet" if st.val("stamina") > 40 else "life_normal"
		if st.ym >= LATE_FROM:
			var guard := 0
			while Schedule.truthy(st.status["sick"]) and st.val("fatigue") + 3 * 96 - st.val("stamina") >= 80 and guard < 10:
				if Street.hospital(st) != "":
					break
				st.inc("count.hospital")
				guard += 1

	func choose(g, P: Dictionary, i: int):
		var st = g.st
		if st.ym >= LATE_FROM and Schedule.truthy(st.status["sick"]) and H.can_do_job(st, "job_l_late", 0):
			return "job_l_late"
		var e = super(g, P, i)
		if e != null and g.d.jobs.has(e) and is_crime(g.d, e):
			return money_job_safe(g)
		return e

	func money_job_safe(g):
		crime_ok = false
		var e = money_job(g, {})
		crime_ok = true
		return e

	## After 1927-10: rest only to keep the month-end sick index under 85; never rest a healthy month (it must end sick).
	func needs_rest(g, P: Dictionary, i: int, e: String) -> bool:
		if g.st.ym < LATE_FROM:
			return super(g, P, i, e)
		if e.begins_with("rest_"):
			return false
		var after: int = P["fat"] + delta(g, P, i, e)[0]
		return after - g.st.val("stamina") >= 85


## 11. Flagpole fame: lover main + savvy; until the end of 1925 the first period of every month on the flagpole while fame is
## under 220 (to clear the medium and big fame gates early).
class Flagpole:
	extends MainSavvy

	func setup(rd: String) -> void:
		super(rd)
		name = "flagpole_" + rd

	func choose(g, P: Dictionary, i: int):
		var st = g.st
		if i == 0 and st.ym < 24 and st.attr["fame"] < 220 and H.can_do_job(st, "job_flagpole"):
			return "job_flagpole"
		return super(g, P, i)


## 12. Fur strongman (the user's recipe): tough main + savvy, the last period of every month at the dock (stamina and money;
## looks fall to 0). He saves for the white fur, the makeup case (grooming +5 lifts the fur's outfit bonus) and the slave
## bracelet (looks +20), wears fur and bracelet whenever looks are under 60, and diets while looks are low and stamina is above 60. No acting
## class for looks; dock work (looks -1 a day) is skipped while displayed looks are under 63, so the diet can lift them.
class FurStrongman:
	extends MainSavvy

	const SET := [["fur_white", "clothing_store"], ["makeup_case", "general_store"], ["slave_bracelet", "clothing_store"]]

	func setup(rd: String) -> void:
		super("tough")
		name = "fur_strongman"
		ignore_looks = true
		looks_floor = 63

	func month_start(_story, st) -> void:
		# diet (looks +3, stamina -20 a month) while looks need it; always dieting starves him (stamina 0 by autumn 1924)
		st.lifestyle = "life_diet" if st.val("looks") < 66 and st.val("stamina") > 60 else "life_normal"
		var all_set := true
		for x in SET:
			if st.items.has(x[0]):
				continue
			var p: int = Street.price(st, x[1], st.d.items[x[0]]["price"])
			if st.money - p >= living(st) and Street.buy(st, x[1], x[0]) == "":
				st.inc("count.fur_set_buy")
			else:
				all_set = false
				break
		if all_set:
			buy_gear(st)
		wear_set(st)

	## Fur as the outfit and the bracelet in an accessory slot whenever looks are under 60 without them.
	func wear_set(st) -> void:
		if st.val("looks") >= 60:
			return
		if st.items.has("fur_white"):
			st.equip["outfit"] = "fur_white"
		if st.items.has("slave_bracelet") and not st.equip["accessory"].has("slave_bracelet"):
			if st.equip["accessory"].size() >= int(st.d.t["items"]["rules"]["accessory_slots"]):
				st.equip["accessory"].pop_back()
			st.equip["accessory"].append("slave_bracelet")

	func choose(g, P: Dictionary, i: int):
		var st = g.st
		if i == 2 and H.can_do_job(st, "job_dock1") and st.val("looks") >= 63:
			return "job_dock1"
		return super(g, P, i)

	## Saves for the fur first: until he owns it, its price is kept on top of the usual reserve before paying tuition.
	func reserve(st) -> int:
		var r: int = super(st)
		if not st.items.has("fur_white"):
			r += Street.price(st, "clothing_store", st.d.items["fur_white"]["price"])
		return r

	## No acting class: the set and the diet carry the looks.
	func goals(g, P: Dictionary, i: int) -> Array:
		return goal_list


## 14. Education-main writer with lover second (the user's play, 2026-11): tutoring to education 150 (church to discipline 90 first
## so tutoring sticks), then the culture road, then the lover road. Earns with the fan-magazine column.
class WriterLover:
	extends SBot

	func setup(_rd: String) -> void:
		setup_road("culture", "writer_lover")
		goal_list = [{"stat": "discipline", "to": 90, "via": ["job_church_aid"]}, {"stat": "education", "to": 150, "via": ["class_c3"]}] \
			+ road_goals("culture") + road_goals("lover")


## 15. Flagpole to big-film fame (the user's play, 2026-11): every period on the flagpole until fame reaches `fame_to`, then
## tough, savvy and lover trained full in that order. Board picks follow the usual thresholds.
class FlagpoleBig:
	extends SBot

	var fame_to := 340
	var fame_done := false

	func setup(rd: String) -> void:
		fame_to = int(rd)
		setup_road("tough", "flagpole_big_" + rd)
		goal_list = road_goals("tough") + road_goals("savvy") + road_goals("lover")

	func choose(g, P: Dictionary, i: int):
		var st = g.st
		if st.attr["fame"] >= fame_to:
			fame_done = true
		if not fame_done and not stamina_fix and st.attr["stamina"] >= stamina_floor and H.can_do_job(st, "job_flagpole"):
			return "job_flagpole"
		return super(g, P, i)


## 16. Crime boss: tough main + savvy, all money from crime jobs (bootlegging, then moneylending; the upstairs rooms when his looks
## allow), never the church. Measures whether the month-end search and the arrest fire.
class CrimeBoss:
	extends MainSavvy

	func setup(rd: String) -> void:
		super("tough")
		name = "crime_boss"
		crime_ok = true
		money_jobs = ["job_loan", "job_l_late", "job_dock2", "job_collector", "job_dock1"]


# ---------- new bots (2026-11): each road with its own engine for stamina and money ----------

## Common to the new bots:
## - fine lifestyle from the first month (stamina +10 a month) as the floor, not the engine;
## - stamina follows a curve min(cap, 100 + 12 x month index): under it (minus 10) the bot trains stamina with its road's engine
##   first (dance for the lover, the dock or collecting for the others, bootlegging for the crime roads). A job that costs stamina
##   (flagpole, column) pushes him under the curve, so the next periods pay it back;
## - discipline kept where the slack-off chance stays 0 up to fatigue = half the stamina cap (church with Sil), unless disc_on is off;
## - rest by expected success (needs_rest with new_rules); the next board read ahead (prep_goal);
## - fame: when the next board's big role is short of fame by 40 or less, the first period of the month on the flagpole.
class NewBot:
	extends SBot

	var stam_cap := 300
	var stam_engine := ["class_l3", "job_dock1"]
	var fame_keep := true
	var looks_guard := 72          # jobs that cost looks are not used as the stamina engine under this
	var banned := []               # entries this road does not use (e.g. the lounge for culture: education -2 a day)

	func usable(g, P: Dictionary, i: int, e: String) -> String:
		if banned.has(e):
			return "no"
		return super(g, P, i, e)

	func _init(sd := 1) -> void:
		super(sd)
		new_rules = true
		looks_floor = 72

	## Looks are always kept >= 60 (under 60 no audition at all), also on the tough road.
	func setup_road(rd: String, nm: String) -> void:
		super(rd, nm)
		looks_late = false

	func stam_target(st) -> int:
		return mini(stam_cap, 100 + 12 * st.ym)

	func disc_to() -> int:
		return stam_cap * 3 / 16 + 12

	func set_life(st) -> void:
		st.lifestyle = "life_fine" if st.money >= 100 and st.val("stamina") < stam_cap + 50 else "life_normal"

	func pre_goals(g, _P: Dictionary, i: int) -> Array:
		var st = g.st
		var gs := []
		if st.val("looks") < 62 and not skip_looks(st):
			gs.append({"stat": "looks", "to": st.attr["looks"] + 1, "via": ["class_l1"]})
		var t := stam_target(st)
		if st.val("stamina") < t - 10:
			gs.append({"stat": "stamina", "to": t, "via": engine(st)})
		# the studio runner takes loyalty 1 a day; under 20 the church with Sil (loyalty line 10) closes
		var disc_low: bool = want_disc(st) and st.val("discipline") < disc_to() - 10
		if disc_low and st.val("loyalty") < 20:
			gs.append({"stat": "loyalty", "to": 25, "via": ["job_l_day", "class_yi", "job_church_help"]})
		if disc_low:
			gs.append({"stat": "discipline", "to": disc_to(), "via": ["job_church_aid"]})
		if prep_on:
			var pg = prep_goal(st, i)
			if pg != null:
				gs.append(pg)
		return gs

	func engine(st) -> Array:
		var out := []
		for e in stam_engine:
			if st.d.jobs.has(e) and costs_looks(st.d, e) and st.val("looks") < looks_guard and not skip_looks(st):
				continue
			out.append(e)
		return out

	func attr_via(a: String) -> Array:
		return stam_engine if a == "stamina" else ATTR_VIA[a]

	## Own money jobs first, but only those that a rested day would pass (a stat barely over the line makes bad days).
	func money_job(g, P: Dictionary):
		var st = g.st
		var low: bool = st.val("looks") < looks_floor and not skip_looks(st)
		for jid in money_jobs:
			if H.can_do_job(st, jid) and not (low and costs_looks(g.d, jid)) and success_p(g, jid, H.job_fat(g.d.jobs[jid]) * 5) >= succ_line:
				return jid
		return super(g, P)

	func choose(g, P: Dictionary, i: int):
		var st = g.st
		if fame_keep and i == 0 and H.can_do_job(st, "job_flagpole"):
			var nb: Dictionary = Board.next_board(st)
			if not nb.is_empty():
				for e in nb["roles"]:
					if e["size"] == "big":
						var gap: int = gate_at(st, e, nb["month"]) - st.attr["fame"]
						if gap > 0 and gap <= 40:
							return "job_flagpole"
		return super(g, P, i)


## N1. Savvy, lover, tough (lover first). Dance is the stamina engine (it also trains physique and looks); money from the escort
## job (physique 25; loyalty +1 a day, which pays back the studio runner's loyalty -1 for the savvy gates), the dock while looks
## are high. Grooming from the lounge from 1927 (its education -2 costs this road nothing).
class NewSLT:
	extends NewBot

	func setup(_rd: String) -> void:
		setup_road("lover", "new_slt")
		goal_list = staged(["savvy"], [280]) + [{"stat": "physique", "to": 35, "via": ["class_l3"]}] \
			+ staged(["lover", "savvy", "tough"], [210, 280]) + [SPEECH_TALKIE] + staged(["lover", "savvy", "tough"], [999])
		money_jobs = ["job_l_day", "job_dock1", "job_server"]
		stam_engine = ["class_l3", "job_dock1"]


## N2. Culture, tough, savvy (not lover: the lounge, the only grooming source, takes education -2 a day, and culture's gates are
## education). Tutoring first to education 90 (the column opens; tutoring and the column both add discipline, so the church is
## rarely needed). Money from the column (counts as exposure: no fame decay); collecting is the stamina engine and trains speech
## and nerve at once (looks -1 a day: not used under looks 72).
class NewCTS:
	extends NewBot

	func setup(_rd: String) -> void:
		setup_road("culture", "new_cts")
		goal_list = [{"stat": "education", "to": 90, "via": ["class_c3"]}] + staged(["culture", "tough", "savvy"])
		money_jobs = ["job_c_money", "job_collector", "job_dock1"]
		stam_engine = ["job_collector", "job_dock1", "class_l3"]


## N3. Tough without crime, looks always >= 60: no job that costs looks (dock, collecting). Stamina from dance (also looks and
## physique); money from the escort job (physique 25 first), else waiting tables. Tough, savvy, lover.
class CleanTough:
	extends NewBot

	func setup(_rd: String) -> void:
		setup_road("tough", "clean_tough")
		looks_late = false
		looks_floor = 999
		looks_guard = 999
		goal_list = staged(["savvy"], [280]) + [{"stat": "physique", "to": 30, "via": ["class_l3"]}] \
			+ staged(["tough", "savvy", "lover"], [210, 280]) + [SPEECH_TALKIE] + staged(["tough", "savvy", "lover"], [999])
		money_jobs = ["job_l_day", "job_server"]
		stam_engine = ["class_l3"]


## N6. Culture, lover, savvy (the user's play): tutoring to education 90, then culture, lover and savvy staged. Lover only by acting
## and physique: the lounge (grooming, education -2 a day) is never used. The first period of every month on the column when
## nothing is locked (a good day counts as exposure: no fame decay that month); stamina taken by the column is paid back by
## dance and the fine lifestyle. Acting is the bonus skill of the films (P), so this road's releases lift fame.
class NewCL:
	extends NewBot

	func setup(_rd: String) -> void:
		setup_road("culture", "new_cl")
		goal_list = [{"stat": "education", "to": 90, "via": ["class_c3"]}] + staged(["culture", "lover", "savvy"])
		money_jobs = ["job_c_money", "job_l_day", "job_dock1"]
		stam_engine = ["class_l3", "job_dock1"]
		banned = ["job_l_night"]

	func choose(g, P: Dictionary, i: int):
		var st = g.st
		if not P.get("col", false) and H.can_do_job(st, "job_c_money") and not stamina_low(st):
			P["col"] = true
			return "job_c_money"
		return super(g, P, i)

	func stamina_low(st) -> bool:
		return st.val("stamina") < stam_target(st) - 30


## N4. Crime boss, new rules: tough and savvy; money from crime (the upstairs rooms when looks allow, bootlegging, collecting,
## the dock); bootlegging (stamina +1 a day, no looks) is also the stamina engine. Never the church. Stamina cap 400 (his jobs
## carry fatigue +5 to +12 a day).
class CrimeBossNew:
	extends NewBot

	func setup(_rd: String) -> void:
		setup_road("tough", "crime_boss_new")
		crime_ok = true
		disc_on = false
		stam_cap = 400
		goal_list = staged(["tough", "savvy"])
		money_jobs = ["job_l_late", "job_dock2", "job_collector", "job_dock1"]
		stam_engine = ["job_dock2", "job_dock1"]


## N5. Literate tough, new: tough to level 6, then tutoring to education 120 (the moneylending gate) while bootlegging pays the
## tuition, then tough and savvy staged; money from moneylending once open (1927-01), else bootlegging, the dock.
class LiterateToughNew:
	extends NewBot

	func setup(_rd: String) -> void:
		setup_road("tough", "literate_tough_new")
		stam_cap = 400
		goal_list = staged(["tough"], [210]) + [{"stat": "education", "to": 120, "via": ["class_c3"]}] + staged(["tough", "savvy"])
		money_jobs = ["job_loan", "job_dock2", "job_dock1"]
		stam_engine = ["job_dock2", "job_dock1"]



## name -> [class, setup argument]. Type 1 first.
const TYPE1 := ["full_tough", "full_tough_nolooks", "full_lover", "full_culture", "full_savvy"]
static func all_bots() -> Dictionary:
	var b := {}
	for rd in ["tough", "lover", "culture", "savvy"]:
		b["full_" + rd] = [MainOnly, rd]
	b["full_tough_nolooks"] = [MainOnlyNoLooks, "tough"]
	for rd in ["tough", "lover", "culture", "savvy"]:
		b["main_savvy_" + rd] = [MainSavvy, rd]
	b["lover_side_first"] = [LoverSideFirst, "lover"]
	for rd in ["tough", "lover", "culture", "savvy"]:
		b["gear_max_" + rd] = [GearMax, rd]
	b["four_color_stamina"] = [FourColor, "stamina"]
	b["four_color_discipline"] = [FourColor, "discipline"]
	b["literate_tough"] = [LiterateTough, "tough"]
	b["gambler_lover"] = [Gambler, "lover"]
	b["hoard_baptize_lover"] = [HoardBaptize, "lover"]
	b["pious_lender"] = [PiousLender, "tough"]
	b["sick_beauty"] = [SickBeauty, "lover"]
	b["flagpole_lover"] = [Flagpole, "lover"]
	b["fur_strongman"] = [FurStrongman, "tough"]
	b["writer_lover"] = [WriterLover, ""]
	b["flagpole_big_300"] = [FlagpoleBig, "300"]
	b["flagpole_big_260"] = [FlagpoleBig, "260"]
	b["crime_boss"] = [CrimeBoss, "tough"]
	b["new_slt"] = [NewSLT, ""]
	b["new_cts"] = [NewCTS, ""]
	b["new_cl"] = [NewCL, ""]
	b["clean_tough"] = [CleanTough, ""]
	b["crime_boss_new"] = [CrimeBossNew, ""]
	b["literate_tough_new"] = [LiterateToughNew, ""]
	return b


static func make(spec, sd: int):
	var bot = spec[0].new(sd)
	bot.setup(spec[1])
	return bot
