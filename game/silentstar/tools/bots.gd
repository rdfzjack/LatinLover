extends RefCounted
## Strategy bots (PLAN step 7, ported to Godot in step 12b): they plug into Story.Agent and play whole games in bulk.
## Port of sim/bots.py; class, method and field names are the same. Rules and strategies are NOT changed here; a Python bug stays a bug.
##
##   var rec = Bots.play(Bots.BOTS["only_lover"], 1, d)      # plays one game and returns a record (report.gd aggregates them)
##
## Eight bots (names in BOTS): only_tough / only_lover / only_culture / only_savvy, two_roads, random_pick, crime_line, books_culture.
##
## Porting notes (the reconciliation, tools/trace.gd against tools/trace.py, checks all of this):
## - The bot's own random numbers are BotRng (PCG32, sequence 3, seed * 1000003 + 17), the same on both sides.
## - Python 3.12+ sum() of floats is a compensated (Neumaier) sum; H.fsum copies it, so every float sum uses it.
## - Python's sorted() is stable; H.stable_order sorts with the index as the tie-breaker.
## - "first of the largest" in Python max() = the first one with a strictly larger value here.
## - Dictionaries are walked in table order (the tables are read in file order on both sides).
## - Python's `//` is Rules.fdiv, `/` on ints is a float division (written with float()).

const Rules = preload("res://core/rules.gd")
const Rng = preload("res://core/rng.gd")
const Schedule = preload("res://core/schedule.gd")
const Street = preload("res://core/street.gd")
const Film = preload("res://core/film.gd")
const Audition = preload("res://core/audition.gd")
const Story = preload("res://core/story.gd")

const Events = preload("res://core/events.gd")

const OLD_CRIME_JOBS := ["job_bootleg", "job_escort", "job_bar"]    # before step 12c; now every job with crime_tier counts (H.is_crime)
const THRESH := {"big": 0.12, "medium": 0.2, "small": 0.0}      # Choosing a role: do not go if the win-rate estimate is below this line
const ROAD_PLACE := {"tough": "place_dock", "lover": "place_downtown", "culture": "place_downtown", "savvy": "place_studio"}
const ROAD_JOBS := {"culture": ["job_news", "job_model_art"]}   # When short of money, first take jobs of the own road


## Small helpers that Python gets from its standard library.
class H:
	extends RefCounted

	## Python 3.12+ sum() of floats (Neumaier compensated sum). The first item is added to the int 0, which is exact.
	static func fsum(xs: Array) -> float:
		if xs.is_empty():
			return 0.0
		var f_result: float = float(xs[0])
		var c := 0.0
		for i in range(1, xs.size()):
			var x: float = float(xs[i])
			var t: float = f_result + x
			if absf(f_result) >= absf(x):
				c += (f_result - t) + x
			else:
				c += (x - t) + f_result
			f_result = t
		if c != 0.0 and is_finite(c):
			f_result += c
		return f_result

	## The indexes of keys sorted ascending, ties keep their original order (Python's stable sorted()).
	static func stable_order(keys: Array) -> Array:
		var idx := []
		for i in keys.size():
			idx.append(i)
		idx.sort_custom(func(a, b): return keys[a] < keys[b] if keys[a] != keys[b] else a < b)
		return idx

	## itertools.combinations(arr, k) as a list, in the same order.
	static func combinations(arr: Array, k: int) -> Array:
		var out := []
		_comb(arr, k, 0, [], out)
		return out

	static func _comb(arr: Array, k: int, start: int, cur: Array, out: Array) -> void:
		if cur.size() == k:
			out.append(cur.duplicate())
			return
		for i in range(start, arr.size()):
			cur.append(arr[i])
			_comb(arr, k, i + 1, cur, out)
			cur.pop_back()

	## itertools.permutations(range(n)), in the same order.
	static func permutations(n: int) -> Array:
		var out := []
		_perm(n, [], out)
		return out

	static func _perm(n: int, cur: Array, out: Array) -> void:
		if cur.size() == n:
			out.append(cur.duplicate())
			return
		for i in n:
			if cur.has(i):
				continue
			cur.append(i)
			_perm(n, cur, out)
			cur.pop_back()

	## audition.candidate_decks(levels): mono, then main color 4 cards + one other color, then 3 + 2. Returns the color lists in that order.
	static func candidate_decks(levels: Array) -> Array:
		var main := 0
		for c in range(1, 4):
			if levels[c] > levels[main]:
				main = c
		var out := [[main, main, main, main, main]]
		for k in [4, 3]:
			for s in 4:
				if s != main:
					var cols := []
					for i in k:
						cols.append(main)
					for i in 5 - k:
						cols.append(s)
					out.append(cols)
		return out


	# ---------- scheduling helpers ----------

	## Step 12c: a crime job is a job with crime_tier in jobs.json (or one of the jobs that were crime jobs before).
	static func is_crime(d, jid: String) -> bool:
		return d.jobs[jid].has("crime_tier") or OLD_CRIME_JOBS.has(jid)

	## The crime jobs of a road, tier 2 first: [job id, ...].
	static func road_crime_jobs(d, road: String) -> Array:
		var out := []
		for t in [2, 1]:
			for jid in d.jobs:
				var j: Dictionary = d.jobs[jid]
				if j.get("crime_tier") == t and j.get("road") == road:
					out.append(jid)
		return out

	static func resort_cost(st, i: int) -> int:
		return Schedule.place_cost(st, "place_resort") * alldays(st, i)

	## Probability that a check passes (GDD 11.0): a gate is 0 or 1; a dice check is displayed + r0(20) >= line.
	static func check_p(st, c) -> float:
		if c == null:
			return 1.0
		if typeof(c) == TYPE_DICTIONARY:
			var need: int = int(c["line"]) - st.val(c["check"])
			return clampf(float(21 - maxi(0, need)) / 21.0, 0.0, 1.0)
		return 1.0 if Rules.test(st, c) else 0.0

	static func est_of(d) -> Est:
		if d.has_meta("bots_est"):
			return d.get_meta("bots_est")
		var e := Est.new(d)
		d.set_meta("bots_est", e)
		return e


	static func workdays(st, i: int) -> int:
		var n := 0
		for x in Schedule.days_of(st, i):
			if not x[1]:
				n += 1
		return n


	static func alldays(st, i: int) -> int:
		return Schedule.days_of(st, i).size()


	static func job_fat(j: Dictionary) -> int:
		var s := 0
		for e in j["daily_effect"]:
			if e["stat"] == "fatigue":
				s += int(e["add"][0])
		return s


	## Available, and the displayed value is at least margin above the success line (fatigue will take some).
	static func can_do_job(st, jid: String, margin := 10) -> bool:
		if Schedule.validate(st, jid) != "":
			return false
		var j: Dictionary = st.d.jobs[jid]
		for kv in Schedule.job_lines(st, j):
			if not (st.val(kv[0]) - margin >= kv[1]):
				return false
		return true


	## Swaps the held outfits and accessories for the set that gives `road` the highest reputation; returns the reputation after the swap.
	static func best_equip(st, road: String) -> int:
		var d = st.d
		var outfits := []
		var ac := []
		for i in st.items:
			var slot = d.items[i]["slot"]
			if slot == "outfit" and not outfits.has(i):
				outfits.append(i)
			elif slot == "accessory" and not ac.has(i):
				ac.append(i)
		outfits.sort_custom(func(a, b): return d.item_order[a] < d.item_order[b])
		ac.sort_custom(func(a, b): return d.item_order[a] < d.item_order[b])
		var cl := [null]
		cl.append_array(outfits)
		var n: int = d.t["items"]["rules"]["accessory_slots"]
		var best = null
		for c in cl:
			for k in range(mini(n, ac.size()), -1, -1):
				for a in H.combinations(ac, k):
					st.equip = {"outfit": c, "accessory": a.duplicate()}
					var r: int = st.rep(road)
					if best == null or r > best[0]:
						best = [r, c, a.duplicate()]
		st.equip = {"outfit": best[1], "accessory": best[2]}
		return best[0]


## The bot's own stream: PCG32 with sequence number 3 (the game uses 1 and 2), seeded with seed * 1000003 + 17.
## Everything is built on below(n); there is no float random. Every call consumes exactly one number.
class BotRng:
	extends RefCounted
	var g

	func _init(sd: int) -> void:
		g = Rng.PCG32.new(sd * 1000003 + 17, 3)

	## 0..n-1 (n >= 1).
	func below(n: int) -> int:
		return g.below(n)

	## One item of a non-empty list: seq[below(len(seq))].
	func choice(seq: Array):
		return seq[g.below(seq.size())]

	## True with probability p / q: below(q) < p.
	func chance(p: int, q: int) -> bool:
		return g.below(q) < p


# ---------- fast audition estimate ----------

## Win-rate estimator, cached per Data (kept on the Data object).
class Est:
	extends RefCounted
	var d_ref: WeakRef          # weak, because the Data object keeps this estimator in its metadata (no reference cycle)
	var bt: Array
	var fp: int
	var win_pct: int
	var lose_pct: int
	var need: int
	var cache := {}
	var perms: Array

	func _init(data) -> void:
		var c: Dictionary = Audition.cfg(data)
		d_ref = weakref(data)
		bt = Audition.beats(data)
		fp = c["style_pct"]
		win_pct = c["counter_pct"]
		lose_pct = c["countered_pct"]
		need = c["rounds_to_win"]
		perms = H.permutations(5)

	func beat(a: Array, b: Array, field: int, fame_hi: bool) -> bool:
		var ca: int = a[0]
		var cb: int = b[0]
		var va: int = int(a[1]) * 100
		var vb: int = int(b[1]) * 100
		if ca == field:
			va = Rules.fdiv(va * fp, 100)
		if cb == field:
			vb = Rules.fdiv(vb * fp, 100)
		if bt[ca] == cb and cb != field:
			var na := Rules.fdiv(va * win_pct, 100)
			var nb := Rules.fdiv(vb * lose_pct, 100)
			va = na
			vb = nb
		elif bt[cb] == ca and ca != field:
			var nb2 := Rules.fdiv(vb * win_pct, 100)
			var na2 := Rules.fdiv(va * lose_pct, 100)
			vb = nb2
			va = na2
		if va != vb:
			return va > vb
		return fame_hi

	## Probability that I win the needed rounds first when both sides play at random (enumerates the 120 orderings of the rival's plays).
	func p_field(mine: Array, theirs: Array, field: int, fame_hi: bool) -> float:
		var m := []
		for a in mine:
			var row := []
			for b in theirs:
				row.append(beat(a, b, field, fame_hi))
			m.append(row)
		var n := 0
		for p in perms:
			var w := 0
			for i in 5:
				if m[i][p[i]]:
					w += 1
					if w >= need:
						n += 1
						break
				elif i - w + 1 >= need:
					break
		return float(n) / 120.0

	## Best deck against a rival: [win rate, color list]. Candidates = mono, or main color 4/3 cards plus one second color.
	func best(levels: Array, rival: Dictionary, probs: Array, fame_me: int) -> Array:
		var fame_hi: bool = fame_me > rival["fame"]
		var key := "%s|%s|%d|%s|%s" % [str(levels), str(rival["levels"]), rival["k"], str(probs), str(fame_hi)]
		var r = cache.get(key)
		if r == null:
			var theirs: Array = Audition.opponent_deck(d_ref.get_ref(), rival, probs)
			r = [-1, null]
			for cols in H.candidate_decks(levels):
				var mine: Array = Audition.build_deck(levels, cols)
				var terms := []
				for f in 4:
					if probs[f] != 0:
						terms.append(probs[f] * p_field(mine, theirs, f, fame_hi))
				var p: float = H.fsum(terms) / 100.0
				if p > r[0]:
					r = [p, cols]
			if cache.size() > 20000:
				cache.clear()
			cache[key] = r
		return r


class Bot:
	extends Story.SimpleAgent
	var name := "?"
	var origin := [0, 0, 3]       # Opening questions; question 3 picks "ring": it only gives a flag and changes no numbers
	var smart_play := true
	var crime := false
	var buy := true               # Buy gear of the own road at the start of the month (--no-buy of the report turns it off)
	var gear_road = null          # Which road's gear to buy; null = buy nothing
	var place := "place_downtown"
	var road = null               # RoadBot and its subclasses
	var second = null
	var roads := []               # Two
	var rnd                       # The bot's own random stream, not the game's
	var seed := 1
	var strategy := ""            # step 12c: "disciplined" / "bad_boy" / "addict" for the new bots, "" for the old ones
	## Step 12c: weights for picking event options (BALANCE_WORKFLOW.md). "main" = a skill or rep_bonus of the bot's road.
	var pref := {"main": 1.0, "skill": 0.3, "attr": 0.1, "discipline": 0.1, "crime": -0.3, "fatigue": -0.2, "money": 0.02,
		"fame": 0.2, "favor": 0.05, "flag.drug_access": -100.0, "status.in_love": -3.0, "bad_event": -20.0}
	var random_options := false   # pick options at random (worst case; report --random-options)

	func _init(sd := 1) -> void:
		rnd = BotRng.new(sd)
		seed = sd

	# ---------- auditions ----------
	func deck(st, ctx) -> Array:
		var rv: Dictionary = ctx["opponents"]
		var role: Dictionary = ctx["roles"]
		var cols: Array = H.est_of(st.d).best(ctx["levels"], rv, role["style_probs"], st.attr["fame"])[1]
		return cols.duplicate()

	func play(st, ctx) -> int:
		var hand: Array = ctx["hand"]
		if not smart_play:
			return st.rng.logic.below(hand.size())
		var d = st.d
		var field: int = ctx["style"]
		var fame_me: int = st.attr["fame"]
		var fame_them: int = ctx["opponents"]["fame"]
		var best_w := -1
		var best_n := 0
		var bi := 0
		var have := false
		for i in hand.size():
			var a: Array = hand[i]
			var w := 0
			for b in ctx["rival_hand"]:
				if Audition.round_winner(d, a, b, field, fame_me, fame_them):
					w += 1
			var kn: int = -int(a[1])        # Prefer the card that beats more; on ties play the smaller card first
			if not have or w > best_w or (w == best_w and kn > best_n):
				have = true
				best_w = w
				best_n = kn
				bi = i
		return bi

	## Win-rate estimate for signing up for this role: the product over the matches.
	func role_p(st, e: Dictionary) -> float:
		var est := H.est_of(st.d)
		var lv: Array = Audition.player_levels(st)
		var p := 1.0
		for rv in e["opponents"]:
			p *= est.best(lv, rv, e["style_probs"], st.attr["fame"])[0]
		return p

	## From the biggest size down: go for the best role if its win rate clears the line, otherwise drop one size.
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
			var bp := 0.0
			var bni := 0
			var have := false
			for i in by[t]:
				var p := role_p(st, b["roles"][i])
				var ni: int = -int(i)
				if not have or p > bp or (p == bp and ni > bni):
					have = true
					bp = p
					bni = ni
			if bp >= THRESH[t]:
				return -bni
		return null

	# ---------- event options (step 12c) ----------
	## Value of one effect line for this bot: the sum of term x weight; a trigger of a "bad" tier event costs bad_event.
	func effect_value(st, text) -> float:
		var d = st.d
		var v := 0.0
		for e in Rules.parse_effect(text):
			var n: String = e[0]
			if n == "trigger":
				if d.events.has(e[1]) and d.events[e[1]].get("tier") == "bad":
					v += pref["bad_event"]
				continue
			var amt := float(e[2]) * (-1.0 if e[1] == "-" else 1.0)
			if e[1] == "=":
				if pref.has(n):
					v += pref[n] * (1.0 if e[2] != 0 else -1.0)
				continue
			if e[3] != "":
				amt = amt * float(Rules.get_var(st, n) if st.attr.has(n) else 0) / 100.0
			var w := 0.0
			if pref.has(n):
				w = pref[n]
			elif st.skill.has(n):
				w = pref["main"] if road != null and d.skill_road[n] == road else pref["skill"]
			elif n.begins_with("rep_bonus."):
				w = pref["main"] * 1.5 if road != null and n.substr(10) == road else pref["skill"]
			elif n.begins_with("favor."):
				w = pref["favor"]
			elif st.attr.has(n):
				w = pref["attr"]
			v += w * amt
		return v

	## Picks the option with the best expected value (checks weighted by their chance); ties go to the first.
	func option(st, ev: Dictionary, avail: Array) -> int:
		if random_options:
			return rnd.choice(avail)
		var best := -1
		var bv := 0.0
		for k in avail:
			var o: Dictionary = ev["options"][k]
			var ck = o.get("check") if Schedule.truthy(o.get("check")) else null
			var p := H.check_p(st, ck)
			var v: float = p * effect_value(st, o.get("success_effect", "")) + (1.0 - p) * effect_value(st, o.get("fail_effect", ""))
			if best < 0 or v > bv:
				best = k
				bv = v
		return best

	# ---------- buying gear ----------
	## Buy gear of the own road at the start of the month: each time pick the item that adds the most reputation per coin,
	## keeping two months of living costs plus 200.
	func month_start(_story, st) -> void:
		var rd = gear_road
		if not buy or rd == null:
			return
		var reserve: int = 2 * living(st) + 200
		for _n in 4:
			var base: int = st.rep(rd)
			var best = null
			for entry in ["clothing_store", "general_store"]:
				for iid in Street.shelf(st, entry):
					var it: Dictionary = st.d.items[iid]
					if it["class"] == "consumable" or st.items.has(iid):
						continue
					var p: int = Street.price(st, entry, it["price"])
					if st.money - p < reserve:
						continue
					var old := {"outfit": st.equip["outfit"], "accessory": st.equip["accessory"].duplicate()}
					st.items.append(iid)
					var gain: int = H.best_equip(st, rd) - base
					st.items.remove_at(st.items.rfind(iid))     # Python list.remove: iid was not held before, so this is the last one
					st.equip = old
					if gain > 0 and (best == null or float(gain) / float(p) > best[0]):
						best = [float(gain) / float(p), entry, iid]
			if best == null:
				break
			Street.buy(st, best[1], best[2])
			st.inc("count.gear_spend", Street.price(st, best[1], st.d.items[best[2]]["price"]))
		H.best_equip(st, rd)

	# ---------- schedule ----------
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
			var e: String = pick(g, P, i)
			apply(g, P, i, e)
			out.append(e)
		return out

	func living(st) -> int:
		return st.d.lifestyles[st.lifestyle]["monthly_cost"][st.fame_tier()]

	## Estimates [fatigue change, money change] of this period.
	func delta(g, P: Dictionary, i: int, e: String) -> Array:
		var st = g.st
		var d = g.d
		var pe: Array = Schedule.parse_entry(e)
		var kind: String = pe[0]
		var iid: String = pe[1]
		var plc = pe[2]
		var w := H.workdays(st, i)
		var n := H.alldays(st, i)
		if kind == "class":
			var k: int = st.cnt("class_periods." + iid) + P["cls"].get(iid, 0) + 1
			var L := 1
			for s in d.class_steps:
				if k > s:
					L += 1
			return [w * int(d.classes[iid].get("fatigue_per_day", 1)), -int(d.classes[iid]["fee"][L - 1]) * w]
		if kind == "book":
			return [w * int(d.books[iid].get("fatigue_per_day", 1)), 0]
		if kind == "job":
			return [w * H.job_fat(d.jobs[iid]), int(Schedule.wage_of(st, iid) * w * 0.7)]
		if iid == "rest_outing":
			return [int(d.places[plc]["fatigue_per_day"]) * n, -Schedule.place_cost(st, plc) * n]
		if iid == "rest_sanatorium":
			return [-11 * n, -8 * n]
		return [-5 * n, 0]

	func apply(g, P: Dictionary, i: int, e: String) -> void:
		var dd := delta(g, P, i, e)
		P["fat"] = maxi(0, P["fat"] + dd[0])
		P["money"] += dd[1]
		var pe: Array = Schedule.parse_entry(e)
		if pe[0] == "class":
			P["cls"][pe[1]] = P["cls"].get(pe[1], 0) + 1

	func rest_entry(g, P: Dictionary, _i: int) -> String:
		var st = g.st
		if Schedule.truthy(st.status["sick"]) or P["money"] < 60 + Schedule.place_cost(st, place) * 10:
			return "rest_home"
		return "rest_outing@" + place

	func pick(g, P: Dictionary, i: int) -> String:
		var st = g.st
		var want_e = want(g, P, i)
		if want_e == null:
			want_e = money_job(g, P)
		if want_e == null:
			return rest_entry(g, P, i)
		var kind: String = Schedule.parse_entry(want_e)[0]
		# Not enough money for classes or books: take a job
		var dd := delta(g, P, i, want_e)
		var df: int = dd[0]
		var dm: int = dd[1]
		var reserve: int = living(st) if i == 2 else 0
		if kind == "class" and P["money"] + dm < reserve:
			want_e = money_job(g, P)
			if want_e == null:
				return rest_entry(g, P, i)
			dd = delta(g, P, i, want_e)
			df = dd[0]
			dm = dd[1]
			kind = "job"
		# Rest when fatigue is high (>= 45, or this period would cross the discipline line)
		var fat: int = P["fat"]
		var sta: int = st.val("stamina")
		var disc: int = st.val("discipline")
		if fat >= 45 or (fat >= 20 and (fat + df >= 10 + disc or fat + df >= sta + 5)):
			return rest_entry(g, P, i)
		# Go to church volunteering when discipline is low
		if kind == "job" and not crime and disc < 35 and H.can_do_job(st, "job_church", 0):
			return "job_church"
		return want_e

	# ---------- finding work ----------
	func want(_g, _P: Dictionary, _i: int):
		push_error("want() is not implemented")
		return null

	## The job that adds the most per day to the skills in `need` that are not yet full (minus the cost of fatigue, crime and discipline).
	func job_for(g, _P: Dictionary, need: Array, crime_ok := false):
		var st = g.st
		var d = g.d
		var best = null
		for jid in d.jobs:
			var j: Dictionary = d.jobs[jid]
			if not H.can_do_job(st, jid):
				continue
			if not crime_ok and H.is_crime(d, jid) and jid != "job_bar":
				continue
			var parts := []
			for e in j["daily_effect"]:
				if need.has(e["stat"]) and st.skill.get(e["stat"], 100) < 100:
					parts.append((e["add"][0] + e["add"][1]) / 2.0)
			var gain: float = H.fsum(parts)
			if gain <= 0:
				continue
			var pen: float = 0.05 * H.job_fat(j)
			for e in j["daily_effect"]:
				if e["stat"] == "crime" and e["add"][0] > 0 and not crime_ok:
					pen += 0.15 * e["add"][0]
				if e["stat"] == "discipline" and e["add"][1] < 0:
					pen += 0.1 * -e["add"][1]
			var score: float = gain - pen + 0.01 * Schedule.wage_of(st, jid)
			if best == null or score > best[0]:
				best = [score, jid]
		return best[1] if best != null else null

	## Earning money: daily wage minus 1.5 x daily fatigue, crime jobs excluded. If the road has a matching job (ROAD_JOBS), do that first.
	func money_job(g, _P: Dictionary):
		var st = g.st
		var d = g.d
		if road != null:
			for jid in ROAD_JOBS.get(road, []):
				if H.can_do_job(st, jid):
					return jid
		var best = null
		for jid in d.jobs:
			if H.is_crime(d, jid) and not crime:
				continue
			if not H.can_do_job(st, jid):
				continue
			var score: float = Schedule.wage_of(st, jid) - 1.5 * H.job_fat(d.jobs[jid])
			if best == null or score > best[0]:
				best = [score, jid]
		return best[1] if best != null else null

	## The next book worth reading for this skill: [tier, book id] or null. When education is too low returns ["education", gate].
	func book_for(st, skill: String) -> Variant:
		var d = st.d
		var caps := {1: 40, 2: 70, 3: 100}
		for t in [1, 2, 3]:
			if st.skill[skill] >= caps[t]:
				continue
			var b = null
			for x in d.books.values():
				if x["skills"] == skill and x["tier"] == t:
					b = x
					break
			if b == null:
				return null
			if st.read_books.has(b["id"]):
				continue
			if not Street.shelf(st, "bookstore").has(b["id"]) and not st.books.has(b["id"]):
				return null
			if st.val("education") < b["education_gate"]:
				return ["education", b["education_gate"]]
			return [t, b["id"]]
		return null

	## The schedule entry for the book to read (buy it first if missing); null when the book cannot be read or cannot be afforded.
	func book_entry(g, P: Dictionary, skill: String):
		var st = g.st
		var d = g.d
		var r: Variant = book_for(st, skill)
		if r == null or r[0] is String:
			return null
		var bid: String = r[1]
		if not st.books.has(bid):
			var price: int = Street.price(st, "bookstore", d.books[bid]["price"])
			if P["money"] - price < living(st):
				return null
			Street.buy(st, "bookstore", bid)
			P["money"] -= price
		return bid

	func want_road(g, P: Dictionary, rd):
		var st = g.st
		var sk: Dictionary = st.skill
		var ed: int = st.val("education")
		if rd == "lover":
			for sc in [["acting", "class_acting"], ["grooming", "class_etiquette"], ["physique", "class_dance"]]:
				if sk[sc[0]] < 100:
					return sc[1]
		elif rd == "tough":
			for sc in [["fight", "class_boxing"], ["riding", "class_riding"]]:
				if sk[sc[0]] < 100:
					return sc[1]
			if sk["nerve"] < 100:
				return job_for(g, P, ["nerve"])
		elif rd == "culture":
			if sk["writing"] < 100 or ed < 300:
				return "class_tutor"
			for s in ["taste", "speech"]:
				var e = book_entry(g, P, s)
				if e != null and e != "":
					return e
		elif rd == "savvy":
			if ed < 200 and (sk["negotiation"] < 70 or sk["business"] < 70):
				return "class_tutor"
			for s in ["negotiation", "business"]:
				var e2 = book_entry(g, P, s)
				if e2 != null and e2 != "":
					return e2
			var need := []
			for s in g.d.road_skills["savvy"]:
				if sk[s] < 100:
					need.append(s)
			if not need.is_empty():
				return job_for(g, P, need)
		return null


## Trains one road, then the second road once the first is full.
## Step 12c c3 (round 4): the pure bots (only_*) rest like the disciplined line (disc_rest); before that they rested only at
## fatigue >= 45 and could not keep training once fatigue started to bite.
class RoadBot:
	extends Bot

	var disc_rest := false

	func want(g, P: Dictionary, _i: int):
		var w = want_road(g, P, road)
		if w != null and w != "":
			return w
		return want_road(g, P, second)

	func pick(g, P: Dictionary, i: int) -> String:
		if disc_rest:
			return disc_pick(g, P, i, false)
		return super(g, P, i)

	## The work of this period (training first, a job when short of money, like Bot.pick); null = nothing to do.
	func work(g, P: Dictionary, i: int):
		var st = g.st
		var e = want(g, P, i)
		if e == null:
			e = money_job(g, P)
		if e == null:
			return null
		if Schedule.parse_entry(e)[0] == "class":
			var reserve: int = living(st) if i == 2 else 0
			if P["money"] + delta(g, P, i, e)[1] < reserve:
				e = money_job(g, P)
		return e

	## Would this period make him sick (sick_index >= 10 is the sick status)?
	func sick_after(g, P: Dictionary, i: int, e: String) -> bool:
		return P["fat"] + delta(g, P, i, e)[0] - g.st.val("stamina") >= 0

	## Step 12c c3: the tough road rests at the dock until it has gone out there 3 times (the expedition opportunity needs it,
	## like only_tough); otherwise `other`. go_personally is already always yes (SimpleAgent).
	func rest_or_dock(g, P: Dictionary, i: int, other: String) -> String:
		var st = g.st
		if road == "tough" and st.cnt("count.outing.place_dock") < DOCK_OUTINGS and not Schedule.truthy(st.status["sick"]) \
				and P["money"] - Schedule.place_cost(st, "place_dock") * H.alldays(st, i) >= living(st):
			return "rest_outing@place_dock"
		return other

	## The disciplined rest rule: reckless_index >= 10 (after this period) or sick -> church volunteering, or rest at home when
	## fatigue is high or the church is not possible (or no_church).
	func disc_pick(g, P: Dictionary, i: int, no_church: bool) -> String:
		var st = g.st
		var e = work(g, P, i)
		if e == null:
			return "rest_home"
		var after: int = P["fat"] + delta(g, P, i, e)[0]
		if after - st.val("discipline") >= 10 or sick_after(g, P, i, e):
			if no_church or P["fat"] >= 40 or P["fat"] - st.val("stamina") >= -20 or not H.can_do_job(st, "job_church", 0):
				return rest_or_dock(g, P, i, "rest_home")
			return "job_church"
		return e


class Hard:
	extends RoadBot

	func _init(sd := 1) -> void:
		super(sd)
		name = "only_tough"
		disc_rest = true
		road = "tough"
		second = "lover"
		origin = [0, 0, 3]
		place = ROAD_PLACE[road]
		gear_road = road


class Lover:
	extends RoadBot

	func _init(sd := 1) -> void:
		super(sd)
		name = "only_lover"
		disc_rest = true
		road = "lover"
		second = "tough"
		origin = [3, 2, 3]
		place = ROAD_PLACE[road]
		gear_road = road


class Culture:
	extends RoadBot

	func _init(sd := 1) -> void:
		super(sd)
		name = "only_culture"
		disc_rest = true
		road = "culture"
		second = "lover"
		origin = [4, 1, 3]
		place = ROAD_PLACE[road]
		gear_road = road


class Wrist:
	extends RoadBot

	func _init(sd := 1) -> void:
		super(sd)
		name = "only_savvy"
		disc_rest = true
		road = "savvy"
		second = "lover"
		origin = [1, 1, 3]
		place = ROAD_PLACE[road]
		gear_road = road


## Of the two roads, train the one with the lower training value first.
class Two:
	extends Bot

	func _init(sd := 1) -> void:
		super(sd)
		name = "two_roads"
		origin = [0, 2, 3]
		roads = ["tough", "lover"]
		gear_road = "tough"
		place = "place_studio"

	func want(g, P: Dictionary, _i: int):
		var st = g.st
		var keys := []
		for r in roads:
			var tr := 0
			for s in g.d.road_skills[r]:
				tr += st.skill[s]
			keys.append(tr)
		for oi in H.stable_order(keys):
			var w = want_road(g, P, roads[oi])
			if w != null and w != "":
				return w
		return null


## Only crime jobs: bootlegging, bar bouncer, dock.
class Crime:
	extends Bot

	func _init(sd := 1) -> void:
		super(sd)
		name = "crime_line"
		origin = [1, 0, 3]
		crime = true
		place = "place_dock"

	func want(g, _P: Dictionary, i: int):
		var st = g.st
		# In the first period of each month go to the boxing gym (the gang boss and the thug boss endings need tough 210), the rest of the time do crime jobs
		if i == 0 and st.skill["fight"] < 100 and st.cnt("job_periods.job_bar") >= 3:
			return "class_boxing"
		for jid in ["job_bootleg", "job_bar", "job_dock"]:
			if H.can_do_job(st, jid):
				return jid
		return null


## No classes, only reading; takes tutoring only when education is too low for the next book.
class BookCulture:
	extends Bot

	func _init(sd := 1) -> void:
		super(sd)
		name = "books_culture"
		origin = [4, 1, 3]
		place = "place_downtown"
		gear_road = "culture"

	func want(g, P: Dictionary, _i: int):
		var st = g.st
		var sk: Dictionary = st.skill
		var blocked := false
		var names := ["writing", "taste", "speech"]
		var keys := []
		for s in names:
			keys.append(sk[s])
		for oi in H.stable_order(keys):
			var skn: String = names[oi]
			var r: Variant = book_for(st, skn)
			if r == null:
				continue
			if r[0] is String:
				blocked = true
				continue
			var e = book_entry(g, P, skn)
			if e != null and e != "":
				return e
		return "class_tutor" if blocked else null


## Schedule, auditions and event options all random (uses its own random stream, not the game's).
class Random:
	extends Bot

	func _init(sd := 1) -> void:
		super(sd)
		name = "random_pick"
		origin = [rnd.below(5), rnd.below(4), rnd.below(6)]
		smart_play = false

	func plan(g) -> Array:
		var st = g.st
		var ops: Array = Schedule.options(st)
		return [rnd.choice(ops), rnd.choice(ops), rnd.choice(ops)]

	func deck(_st, _ctx) -> Array:
		return [rnd.below(4), rnd.below(4), rnd.below(4), rnd.below(4), rnd.below(4)]

	func play(_st, ctx) -> int:
		return rnd.below(ctx["hand"].size())

	func pick_role(_st, _b: Dictionary, ok: Array):
		if rnd.chance(3, 5):
			return rnd.choice(ok)
		return null

	func accept_support(_st, _role: Dictionary) -> bool:
		return rnd.chance(1, 2)

	func go_personally(_st, _role: Dictionary) -> bool:
		return rnd.chance(1, 2)

	func option(_st, _ev: Dictionary, avail: Array) -> int:
		return rnd.choice(avail)

	func annual(_st, opts: Array):
		var ids := [null]
		for x in opts:
			ids.append(x["id"])
		return rnd.choice(ids)

	func suppress(_st, _kind: String) -> bool:
		return rnd.chance(1, 2)


# ---------- step 12c: three strategies, each on the four roads ----------

const DOCK_OUTINGS := 3        # step 12c c3: dock outings the tough strategy bots make (opp_expedition)
const BAD_CRIME_PERIODS := 1  # step 12c c3: once his tier-2 crime job is open, the bad boy works it in the first N periods of every
                               # month (a steady side income, not a savings line: his cash is then a result, not a setting)

const TUITION_DAYS := 26      # round 4: three periods of class days, for the addict bots' tuition reserve
const ROAD_CLASSES := {"tough": ["class_boxing", "class_riding"], "lover": ["class_acting", "class_etiquette", "class_dance"],
	"culture": ["class_tutor"], "savvy": ["class_tutor"]}

## Road setup of the pure bots: [second road, origin].
const ROAD_SETUP := {"tough": ["lover", [0, 0, 3]], "lover": ["tough", [3, 2, 3]], "culture": ["lover", [4, 1, 3]],
	"savvy": ["lover", [1, 1, 3]]}


## Trains one road (like the pure bots); the three strategies differ in how they deal with fatigue.
class StratBot:
	extends RoadBot

	func setup(rd: String) -> void:
		road = rd
		second = ROAD_SETUP[rd][0]
		origin = ROAD_SETUP[rd][1].duplicate()
		place = ROAD_PLACE[rd]
		gear_road = rd
		name = "%s_%s" % [strategy, rd]


## Disciplined: carries fatigue on discipline. reckless_index >= 10 (after this period) -> church volunteering, or rest at home
## when fatigue is high or the church is not possible. Never boosts, never takes crime jobs.
class Disc:
	extends StratBot

	var no_church := false     # the addict bots rest at home instead (discipline >= refuse_discipline would turn the dealer away)

	func _init(sd := 1) -> void:
		super(sd)
		strategy = "disciplined"
		pref["discipline"] = 0.3
		pref["crime"] = -1.0

	func pick(g, P: Dictionary, i: int) -> String:
		return disc_pick(g, P, i, no_church)


## Bad boy: earns with his road's crime jobs and buys the fatigue off at the resort. Never boosts.
## The reckless_index that counts is the one at month end, so: the first two periods work (his road's crime job in the first
## BAD_CRIME_PERIODS periods once tier 2 is open, and whenever he is short of money, i.e. has less than a resort period plus a month
## of living costs; otherwise training); the last period is the resort (home when the
## money is not there) whenever working it would end the month with reckless_index >= 10. Crime jobs take his discipline to 0,
## so that is most months. Also rests when a period would make him sick. Culture has no crime jobs yet, so there is no
## bad_boy_culture (BOTS).
class Bad:
	extends StratBot

	var crime_periods := 1      # tier-2 crime job in the first N periods of every month
	var cap60 := true           # keep the month-end reckless_index below 60

	func _init(sd := 1) -> void:
		super(sd)
		strategy = "bad_boy"
		crime = true
		crime_periods = BAD_CRIME_PERIODS
		pref["crime"] = 0.0
		pref["money"] = 0.05
		pref["discipline"] = 0.0

	func crime_job(g):
		for jid in H.road_crime_jobs(g.d, road):
			if H.can_do_job(g.st, jid):
				return jid
		return null

	## His road's crime jobs; an ordinary job only while none of them can be done (before it unlocks, or its line is out of reach).
	func money_job(g, P: Dictionary):
		var j = crime_job(g)
		if j != null:
			return j
		crime = false
		j = super(g, P)
		crime = true
		return j

	func rest_choice(g, P: Dictionary, i: int) -> String:
		var st = g.st
		var dock := rest_or_dock(g, P, i, "")
		if dock != "":
			return dock
		if not Schedule.truthy(st.status["sick"]) and P["money"] - H.resort_cost(st, i) >= living(st):
			return "rest_outing@place_resort"
		return "rest_home"

	func pick(g, P: Dictionary, i: int) -> String:
		var st = g.st
		var e = null
		var cj = crime_job(g)
		var steady: bool = cj != null and g.d.jobs[cj]["crime_tier"] == 2 and i < crime_periods
		if steady or P["money"] < H.resort_cost(st, i) + living(st):
			e = cj
		if e == null:
			e = work(g, P, i)
		if e == null:
			e = crime_job(g)
		if e == null or sick_after(g, P, i, e):
			return rest_choice(g, P, i)
		var after: int = P["fat"] + delta(g, P, i, e)[0] - st.val("discipline")
		if i == 2 and after >= 10:
			return rest_choice(g, P, i)
		# step 12c c3: keep the month-end reckless_index below 60 (refused jobs; at 100 he is arrested), as BALANCE_LOG describes:
		# before the last period, work only if the rest he can afford in the last period brings it back under 60
		if cap60 and i < 2:
			var rc := rest_choice(g, P, 2)
			if after + delta(g, P, 2, rc)[0] >= 60:
				return rest_choice(g, P, i)
		return e


## Bold (step 12c c3 round 4): the bad boy who takes risks. He does not keep the month-end reckless_index below 60 and works his
## tier-2 crime job in the first two periods of every month, so his downside (refused jobs, arrests, scandals) shows in the report.
class Bold:
	extends Bad

	func _init(sd := 1) -> void:
		super(sd)
		strategy = "bold"
		crime_periods = 2
		cap60 = false


## Addict (step 12c c3 round 3): plays like the disciplined bot (rests at home, not at the church) and buys from the dealer
## whenever he is around; takes a dose when tired. No crime jobs. Four ways to play it (policy):
##   always - buys what the dealer has (keeping a month of living costs); sends himself to detox when deep (stage 3)
##   quit   - the same until the first attack tells him he is addicted; then stops buying and goes to detox, and never buys again
##   shoot  - buys, but takes a dose only before a shooting period (for the divine roll) until he is addicted
##   allin  - like always, never goes to detox by himself
class Addict:
	extends Disc

	var policy := "always"

	func _init(sd := 1) -> void:
		super(sd)
		strategy = "addict"
		no_church = false
		pref["flag.drug_stock"] = 100.0
		pref["discipline"] = 0.0

	func stock(st) -> int:
		return int(st.flags.get("drug_stock", 0))

	func known(st) -> bool:
		return int(st.flags.get("drug_known", 0)) > 0

	func month_start(story, st) -> void:
		super(story, st)
		if policy == "quit" and (known(st) or st.cnt("count.detox") > 0 or st.cnt("count.clean") > 0):
			if st.drug >= 1 and known(st):
				story.send_detox(st)
			return
		if policy == "always" and st.drug >= 3:
			story.send_detox(st)
		var n: int = int(st.flags.get("dealer_stock", 0))
		var price: int = int(st.flags.get("dealer_price", 0))
		var reserve: int = living(st) + tuition(st)
		while n > 0 and st.money - price * n < reserve:
			n -= 1
		if n > 0:
			story.buy_drug(st, n)

	## Round 4: the tuition of the class he would take this month (three periods of his road's first class that is not full, at
	## its current fee level); 0 when his road has no class left. Kept on top of a month of living costs before buying.
	func tuition(st) -> int:
		var d = st.d
		for cid in ROAD_CLASSES.get(road, []):
			var c: Dictionary = d.classes[cid]
			var full := true
			for gn in c["gain"]:
				if gn.get("cond") == null and st.skill.has(gn["stat"]) and st.skill[gn["stat"]] < 100:
					full = false
			if cid == "class_tutor" and st.val("education") < 300:
				full = false
			if full:
				continue
			var k: int = st.cnt("class_periods." + cid) + 1
			var L := 1
			for s in d.class_steps:
				if k > s:
					L += 1
			return int(c["fee"][mini(L, c["fee"].size()) - 1]) * TUITION_DAYS
		return 0

	## Shooting periods of this month after period i (round 4: the doses in hand are kept for them).
	func shoots_after(hooks, st, i: int) -> int:
		var n := 0
		for j in range(i + 1, 3):
			if hooks.locked(st, j) != null:
				n += 1
		return n

	func wants_dose(story, st, i: int) -> bool:
		if story.locked(st, i) != null:
			return true
		if policy == "shoot":
			return false
		return st.val("fatigue") >= 40 and stock(st) > shoots_after(story, st, i)

	func before_period(story, st, i: int) -> void:
		if stock(st) > 0 and wants_dose(story, st, i) and Events.boost_reason(st, i) == "":
			story.boost(st, i)

	func pick(g, P: Dictionary, i: int) -> String:
		var st = g.st
		var have: int = stock(st) - P.get("dose", 0) - shoots_after(g.hooks, st, i)
		if have > 0 and (st.drug_points > 0 or (policy != "shoot" and P["fat"] >= 40)):
			P["fat"] = maxi(0, P["fat"] - 40)
			P["dose"] = P.get("dose", 0) + 1
		return super(g, P, i)


class Quit:
	extends Addict
	func _init(sd := 1) -> void:
		super(sd)
		strategy = "quit"
		policy = "quit"


class Shoot:
	extends Addict
	func _init(sd := 1) -> void:
		super(sd)
		strategy = "shoot"
		policy = "shoot"


class Allin:
	extends Addict
	func _init(sd := 1) -> void:
		super(sd)
		strategy = "allin"
		policy = "allin"


## Wild (step 12c c3 round 3): the bad boy who also buys from the dealer whenever he is around (he has the money and, with his
## crime, meets the dealer more often). Takes a dose when tired. Round 4: at the deepest stage (stage 3) he goes to detox and buys
## nothing that month.
class Wild:
	extends Bad

	func _init(sd := 1) -> void:
		super(sd)
		strategy = "wild"
		pref["flag.drug_stock"] = 100.0

	func stock(st) -> int:
		return int(st.flags.get("drug_stock", 0))

	func month_start(story, st) -> void:
		super(story, st)
		if st.drug >= 3:            # round 4: at the deepest stage he goes to detox and buys nothing that month
			story.send_detox(st)
			return
		var n: int = int(st.flags.get("dealer_stock", 0))
		var price: int = int(st.flags.get("dealer_price", 0))
		while n > 0 and st.money - price * n < living(st):
			n -= 1
		if n > 0:
			story.buy_drug(st, n)

	func before_period(story, st, i: int) -> void:
		if stock(st) > 0 and st.val("fatigue") >= 40 and Events.boost_reason(st, i) == "":
			story.boost(st, i)

	func pick(g, P: Dictionary, i: int) -> String:
		var st = g.st
		var have: int = stock(st) - P.get("dose", 0)
		if have > 0 and (st.drug_points > 0 or P["fat"] >= 40):
			P["fat"] = maxi(0, P["fat"] - 40)
			P["dose"] = P.get("dose", 0) + 1
		return super(g, P, i)


const BOTS := {
	"only_tough": Hard,
	"only_lover": Lover,
	"only_culture": Culture,
	"only_savvy": Wrist,
	"two_roads": Two,
	"crime_line": Crime,
	"books_culture": BookCulture,
	"random_pick": Random,
	"disciplined_tough": [Disc, "tough"],
	"disciplined_lover": [Disc, "lover"],
	"disciplined_culture": [Disc, "culture"],
	"disciplined_savvy": [Disc, "savvy"],
	"bad_boy_tough": [Bad, "tough"],
	"bad_boy_lover": [Bad, "lover"],
	"bad_boy_savvy": [Bad, "savvy"],
	"bold_tough": [Bold, "tough"],
	"bold_lover": [Bold, "lover"],
	"bold_savvy": [Bold, "savvy"],
	"wild_tough": [Wild, "tough"],
	"wild_lover": [Wild, "lover"],
	"wild_savvy": [Wild, "savvy"],
	"addict_tough": [Addict, "tough"],
	"addict_lover": [Addict, "lover"],
	"addict_culture": [Addict, "culture"],
	"addict_savvy": [Addict, "savvy"],
	"quit_tough": [Quit, "tough"],
	"quit_lover": [Quit, "lover"],
	"quit_culture": [Quit, "culture"],
	"quit_savvy": [Quit, "savvy"],
	"shoot_tough": [Shoot, "tough"],
	"shoot_lover": [Shoot, "lover"],
	"shoot_culture": [Shoot, "culture"],
	"shoot_savvy": [Shoot, "savvy"],
	"allin_tough": [Allin, "tough"],
	"allin_lover": [Allin, "lover"],
	"allin_culture": [Allin, "culture"],
	"allin_savvy": [Allin, "savvy"],
}
const PURE := ["only_tough", "only_lover", "only_culture", "only_savvy"]
const STRATEGIES := ["disciplined", "bad_boy", "bold", "wild", "addict", "quit", "shoot", "allin"]


## A bot from a BOTS value: a class, or [class, road] for the step-12c bots.
static func make_bot(spec, sd: int):
	if spec is Array:
		var b = spec[0].new(sd)
		b.setup(spec[1])
		return b
	return spec.new(sd)


# ---------- playing one game ----------

## Plays one game and returns a record. Array indexes in the record = month index (the value after month end).
## on_month(g, date), if valid, is called after each month with the date the month started (reconciliation uses it).
## smart_play / buy: null = the bot's own setting.
static func play(cls, sd: int, data, smart_play = null, buy_gear = null, on_month := Callable(), random_options := false) -> Dictionary:
	var bot = make_bot(cls, sd)
	bot.random_options = random_options
	if smart_play != null:
		bot.smart_play = smart_play
	if buy_gear != null:
		bot.buy = buy_gear
	var g = Story.new_game(data, sd, bot.origin, bot)
	var st = g.st
	var d = g.d
	var rec := {"bot": bot.name, "seed": sd, "origin": bot.origin.duplicate(),
		"train": [], "rep": [], "money": [], "fame": [], "debt": 0}
	while not st.finished:
		var date: String = st.date()
		g.start_month()
		g.run_month(Story.fit_plan(g, bot.plan(g)))
		var tr := []
		for r in d.roads:
			var s := 0
			for k in d.road_skills[r]:
				s += st.skill[k]
			tr.append(s)
		rec["train"].append(tr)
		var b: Dictionary = st.bonus()
		var rp := []
		for r in d.roads:
			rp.append(st.rep(r, b))
		rec["rep"].append(rp)
		rec["money"].append(st.money)
		rec["fame"].append(st.attr["fame"])
		if st.money < 0:
			rec["debt"] += 1
		if on_month.is_valid():
			on_month.call(g, date)
	rec.merge(summarize(g))
	rec["strategy"] = bot.strategy
	rec["road"] = bot.road
	var ev := {}
	var op := {}
	for x in g.hooks.event_log:
		ev[x["id"]] = ev.get(x["id"], 0) + 1
		if x.has("options") and x["options"] != null:
			var k: String = "%s#%d" % [x["id"], x["options"]]
			op[k] = op.get(k, 0) + 1
	rec["events"] = ev
	rec["options"] = op
	return rec


static func summarize(g) -> Dictionary:
	var st = g.st
	var d = g.d
	var res: Dictionary = st.story["ending"]
	var c: Dictionary = st.count
	var rec := {"ending": res["ending"], "category": res.get("category"), "grade": res.get("grade"), "total": res.get("total"),
		"months_played": st.ym if g.hooks.boards.size() > 0 else 0,
		"fame_end": st.attr["fame"], "fame_tier": st.fame_tier(),
		"max_rep": Rules.get_var(st, "max_rep")}
	for k in ["count.audition", "count.audition_won", "count.audition.big", "count.audition.medium", "count.audition.small",
			"count.audition_won.big", "count.audition_won.medium", "count.audition_won.small", "count.release", "count.hit",
			"count.flop", "count.support", "count.breach", "count.lead.big", "count.lead.medium", "count.lead.small",
			"count.arrest", "count.scandal", "count.opportunity"]:
		rec[k] = c.get(k, 0)
	# The reputation bonus from annual events is subtracted when computing "full training plus plain releases"
	var ann := {}
	for r in d.roads:
		ann[r] = 0
	var rw := {}
	for x in d.t["annual"]["ranking"]["rewards"]:
		rw[x["rank"]] = x["rep_bonus"]
	var occ := {}
	for x in d.t["annual"]["occasions"]:
		occ[x["id"]] = x["road"]
	for a in g.hooks.annuals:
		if Schedule.truthy(a.get("occasions")) and rw.has(a.get("rank")):
			ann[occ[a["occasions"]]] += rw[a["rank"]]
	var b: Dictionary = st.bonus()
	var no_annual := 0
	var first := true
	for r in d.roads:
		var v: int = st.rep(r, b) - ann[r]
		if first or v > no_annual:
			no_annual = v
			first = false
	rec["no_annual_rep"] = no_annual
	var annual_bonus := 0
	for r in d.roads:
		annual_bonus += ann[r]
	rec["annual_bonus"] = annual_bonus
	# Breakdown of the main road's (the road with the highest final reputation) reputation: training value / gear and stamina bonus / releases / annual / the rest
	var top: String = d.roads[0]
	var top_v: int = st.rep(top, b)
	for r in d.roads:
		var v2: int = st.rep(r, b)
		if v2 > top_v:
			top = r
			top_v = v2
	var tr := 0
	var shown := 0
	for s in d.road_skills[top]:
		tr += st.skill[s]
		shown += st.val(s, b)
	var rel := 0
	for f in st.story["films"]:
		if Schedule.truthy(f.get("result")) and f["roles"]["road"] == top:
			rel += f["result"]["rep_bonus"]
	rec["breakdown"] = {"training": tr, "gear": shown - tr, "release": rel,
		"annual": ann[top], "opportunity": st.corr[top] - rel - ann[top]}
	rec["plain_rep"] = tr + rec["breakdown"]["gear"] + rel      # "Full training plus plain releases" (gear included)
	rec["gear_buy"] = c.get("count.gear_spend", 0)
	var fee := 0
	for f in st.story["films"]:
		if Schedule.truthy(f.get("result")):
			fee += f.get("fee", 0)
	rec["fee"] = fee
	var ranks := []
	for a in g.hooks.annuals:
		ranks.append(a.get("rank"))
	rec["annual_rank"] = ranks
	# step 12c: fatigue strategies
	for k in ["count.detox", "count.sanatorium", "count.boost", "count.raid", "count.dealer", "count.hooked", "count.attack_months",
			"count.divine", "count.divine_hit", "count.drug_side", "count.clean", "count.void.detained", "count.void.detox",
			"count.void.missing", "count.void.sanatorium", "count.period.rest_home", "count.period.rest_outing", "count.period.job_church",
			"count.outing.place_resort"]:
		rec[k] = c.get(k, 0)
	var crime_p := 0
	for jid in d.jobs:
		if d.jobs[jid].has("crime_tier"):
			crime_p += c.get("count.period." + jid, 0)
	rec["crime_job_periods"] = crime_p
	rec["drug_stage_end"] = st.drug
	# effects by source: events (main-road reputation = its skills + rep_bonus; money; fatigue), all money gained
	var evs: Dictionary = st.src.get("event", {})
	var main_rep := 0
	for s in d.road_skills[top]:
		main_rep += evs.get(s, 0)
	main_rep += evs.get("rep_bonus." + top, 0)
	rec["src_event_rep"] = main_rep
	rec["src_event_money"] = evs.get("money", 0)
	rec["src_event_fatigue"] = evs.get("fatigue", 0)
	rec["src_opp_rep"] = st.src.get("opportunity", {}).get("rep_bonus." + top, 0)
	rec["income"] = st.src.get("income", 0)
	return rec
