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
const H = Bots.H

## Main-road training: [skill, entries that train it, best first].
const ROAD_GOALS := {
	"tough": [["fight", ["class_h1"]], ["riding", ["class_h2"]], ["nerve", ["class_h1", "job_collector"]]],
	"lover": [["acting", ["class_l1"]], ["physique", ["class_l3"]], ["grooming", ["job_l_night"]]],
	"culture": [["writing", ["class_c1"]], ["taste", ["class_c1"]], ["speech", ["job_server", "class_c3", "job_collector"]]],
	"savvy": [["negotiation", ["job_runner"]], ["rapport", ["job_runner"]], ["insight", ["job_runner"]]],
}
## Jobs to earn with, first doable wins (no crime jobs here).
const ROAD_MONEY := {
	"tough": ["job_dock1"], "lover": ["job_l_day", "job_server"], "culture": ["job_c_money", "job_server"],
	"savvy": ["job_server", "job_dock1"],
}
## Opening questions per road (same as bots.gd ROAD_SETUP).
const ROAD_ORIGIN := {"tough": [0, 0, 3], "lover": [3, 2, 3], "culture": [4, 1, 3], "savvy": [1, 1, 3]}
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

	func _init(sd := 1) -> void:
		super(sd)

	## The road skills as goals to 100.
	static func road_goals(rd: String, cap := 100) -> Array:
		var out := []
		for x in ROAD_GOALS[rd]:
			out.append({"stat": x[0], "to": cap, "via": x[1]})
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

	## Goals of this period (subclasses may change them with the date or the state).
	func goals(_g, _P: Dictionary, _i: int) -> Array:
		return goal_list

	func reached(st, gl: Dictionary) -> bool:
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
	## Looks under 62 (after outfits) come first: under 60 he cannot audition, so a real player fixes it with the acting class.
	func choose(g, P: Dictionary, i: int):
		var st = g.st
		var gs: Array = goals(g, P, i)
		if st.val("looks") < 62 and not ignore_looks:
			gs = [{"stat": "looks", "to": st.attr["looks"] + 1, "via": ["class_l1"]}] + gs
		for gl in gs:
			if reached(st, gl):
				continue
			for e in gl["via"]:
				var r := usable(g, P, i, e)
				if r == "ok":
					return e
				if r == "broke":
					return money_job(g, P)
		return money_job(g, P)

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
		var low: bool = st.val("looks") < looks_floor
		for jid in money_jobs:
			if H.can_do_job(st, jid) and not (low and costs_looks(d, jid)):
				return jid
		var best = null
		for jid in d.jobs:
			if is_crime(d, jid) and not crime_ok:
				continue
			if not H.can_do_job(st, jid) or (low and costs_looks(d, jid)):
				continue
			var score: float = Schedule.wage_of(st, jid) - 1.5 * H.job_fat(d.jobs[jid])
			if best == null or score > best[0]:
				best = [score, jid]
		return best[1] if best != null else null

	## Slack-off chance % at fatigue f (GDD 5.1.1).
	func slack_pct(st, f: int) -> int:
		var div: int = int(st.d.t["stats"]["scale"]["div10"]["fatigue"])
		var sf: int = mini(100, Rules.fdiv(maxi(f, 0) * 10, div))
		return clampi(sf - Rules.scale_of(st, "discipline"), 0, int(st.d.t["stats"]["slack"]["cap_pct"]))

	func needs_rest(g, P: Dictionary, i: int, e: String) -> bool:
		if e.begins_with("rest_"):
			return false
		var st = g.st
		var after: int = maxi(0, P["fat"] + delta(g, P, i, e)[0])
		return slack_pct(st, after) >= slack_line or after - st.val("stamina") >= 10

	func rest(g, P: Dictionary, i: int) -> String:
		var st = g.st
		var cost: int = Schedule.place_cost(st, "place_resort") * H.alldays(st, i)
		if not Schedule.truthy(st.status["sick"]) and P["fat"] >= 100 and P["money"] - cost >= reserve(st) * 2:
			return "rest_outing@place_resort"
		return "rest_home"

	# ---------- month start: gear, looks ----------
	func month_start(_story, st) -> void:
		buy_gear(st)
		keep_looks(st)

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


## 3. Like 1, but signs up for a big film only with a good chance.
class BigOnly:
	extends MainSavvy

	func setup(rd: String) -> void:
		super(rd)
		name = "big_only_" + rd
		thresh = {"big": 0.4, "medium": 0.2, "small": 0.0}


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
			{"stat": "riding", "to": 100, "via": ["class_h2"]}, {"stat": "nerve", "to": 100, "via": ["job_collector", "class_h1"]},
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


## name -> [class, setup argument]. Type 1 first.
const TYPE1 := ["full_tough", "full_lover", "full_culture", "full_savvy"]
static func all_bots() -> Dictionary:
	var b := {}
	for rd in ["tough", "lover", "culture", "savvy"]:
		b["full_" + rd] = [MainOnly, rd]
	for rd in ["tough", "lover", "culture", "savvy"]:
		b["main_savvy_" + rd] = [MainSavvy, rd]
	b["lover_side_first"] = [LoverSideFirst, "lover"]
	for rd in ["tough", "lover", "culture", "savvy"]:
		b["big_only_" + rd] = [BigOnly, rd]
	for rd in ["tough", "lover", "culture", "savvy"]:
		b["gear_max_" + rd] = [GearMax, rd]
	b["four_color_stamina"] = [FourColor, "stamina"]
	b["four_color_discipline"] = [FourColor, "discipline"]
	b["literate_tough"] = [LiterateTough, "tough"]
	b["gambler_lover"] = [Gambler, "lover"]
	b["gambler_tough"] = [Gambler, "tough"]
	b["hoard_baptize_lover"] = [HoardBaptize, "lover"]
	b["pious_lender"] = [PiousLender, "tough"]
	b["sick_beauty"] = [SickBeauty, "lover"]
	b["flagpole_lover"] = [Flagpole, "lover"]
	b["fur_strongman"] = [FurStrongman, "tough"]
	return b


static func make(spec, sd: int):
	var bot = spec[0].new(sd)
	bot.setup(spec[1])
	return bot
