extends RefCounted
## Auditions (GDD 7, 9): deck building, effective points, play habits, rival decks, result tiers. Port of sim/audition.py.
##
## Colors are 0-3 in the order tough/lover/culture/savvy (habits.json audition.color_order).
## A card is [color, points]. Effective points are integers scaled by x100 (GDD 16).
##
## Random-number order (copied from the Python side):
## - Unnamed rival: r(main_level random), then the habit with below(6).
## - One match: draw the style with below(100) first; then each round the rival plays first (unless the habit is
##   random: first roll 80% whether to follow the habit; if not following, or random, below(remaining cards)),
##   then the player is asked.
## - Botched: roll report_prob.
## How the player builds a deck and plays is not decided here: a Player (UI or bot) is passed in.
## All functions are static; st is an instance of core/state.gd, d is core/data.gd.

const Rules = preload("res://core/rules.gd")

const COLORS := 4


## The UI or a bot implements these two methods.
class Player:
	extends RefCounted
	## Returns 5 colors (0-3). ctx: role, round number, rival (only the intel the player can see), own levels.
	func deck(_st, _ctx) -> Array:
		return []
	## Returns the index of the card to play from own hand. ctx: hand, rival's remaining hand, style, round, score, history.
	func play(_st, _ctx) -> int:
		return 0


## Fixed deck, random play (for tests and rough estimates). Playing uses the logic stream.
class FixedRandomPlayer:
	extends Player
	var colors := []

	func _init(c := []) -> void:
		colors = c

	func deck(_st, _ctx) -> Array:
		return colors.duplicate()

	func play(st, ctx) -> int:
		return st.rng.logic.below(ctx["hand"].size())


static func cfg(d) -> Dictionary:
	return d.t["habits"]["audition"]


## Counter ring: beats[a] = the color that a counters.
static func beats(d) -> Array:
	var c: Dictionary = cfg(d)
	var names: Array = c["color_order"]
	var out := []
	for n in names:
		out.append(names.find(c["counters"][n]))
	return out


# ---------- cards ----------

## The colors the player picks for the 5 cards; the k-th card of one color (k from 0) has points = max(0, road level - k) (7.2).
static func build_deck(levels: Array, colors: Array) -> Array:
	var seen := [0, 0, 0, 0]
	var out := []
	for c in colors:
		out.append([c, maxi(0, levels[c] - seen[c])])
		seen[c] += 1
	return out


## k cards of the main color plus 5-k of the second color.
static func deck_of(levels: Array, main: int, k: int, sub: int, n := 5) -> Array:
	var cols := []
	for i in k:
		cols.append(main)
	for i in n - k:
		cols.append(sub)
	return build_deck(levels, cols)


## Effective points [va, vb] of the two cards in one round, x100 integers (7.3).
static func effective(d, a: Array, b: Array, field: int) -> Array:
	var c: Dictionary = cfg(d)
	var bt := beats(d)
	var ca: int = a[0]
	var cb: int = b[0]
	var va: int = a[1] * 100
	var vb: int = b[1] * 100
	if ca == field:
		va = Rules.fdiv(va * c["style_pct"], 100)
	if cb == field:
		vb = Rules.fdiv(vb * c["style_pct"], 100)
	if bt[ca] == cb and cb != field:
		va = Rules.fdiv(va * c["counter_pct"], 100)
		vb = Rules.fdiv(vb * c["countered_pct"], 100)
	elif bt[cb] == ca and ca != field:
		vb = Rules.fdiv(vb * c["counter_pct"], 100)
		va = Rules.fdiv(va * c["countered_pct"], 100)
	return [va, vb]


## True when the player wins this round. Ties go to fame, and on equal fame the rival wins (7.3).
static func round_winner(d, mine: Array, theirs: Array, field: int, fame_me: int, fame_them: int) -> bool:
	var v := effective(d, mine, theirs, field)
	if v[0] != v[1]:
		return v[0] > v[1]
	return fame_me > fame_them


## Used to rank "big/small": counts the style only, no counters (7.6).
static func solo_value(d, card: Array, field: int) -> int:
	var v: int = card[1] * 100
	if card[0] == field:
		v = Rules.fdiv(v * cfg(d)["style_pct"], 100)
	return v


# ---------- rivals ----------

## Counter of counter: whoever counters the color that counters main (lover -> savvy, tough -> culture).
static func guard_color(d, main: int) -> int:
	var bt := beats(d)
	var beater := bt.find(main)
	return bt.find(beater)


## The rival's [main color, second color] (7.5): the main color maximizes level x (1 + 0.3 x style probability), ties go to the earlier color;
## the second color is the counter of counter, to avoid being countered.
static func opponent_colors(d, levels: Array, probs: Array) -> Array:
	var co: int = cfg(d)["rival_deck"]["style_factor_pct"]
	var main := 0
	var best := -1
	for c in COLORS:
		var key: int = levels[c] * (10000 + co * probs[c])
		if best < 0 or key > best:
			best = key
			main = c
	return [main, guard_color(d, main)]


static func opponent_deck(d, rival: Dictionary, probs: Array) -> Array:
	var cs := opponent_colors(d, rival["levels"], probs)
	return deck_of(rival["levels"], cs[0], rival["k"], cs[1])


static func half_years(st) -> int:
	return st.ym / 6


## Unnamed rival (9.2). Main color = the color with the highest style probability, second color = counter of counter (level main-2), the other two colors level 1.
## tier: "small", "medium" or "big". main_level and probs are optional (null / empty = default).
static func unnamed_rival(st, tier: String, main_level = null, probs: Array = []) -> Dictionary:
	var d = st.d
	var g = st.rng.logic
	var r: Dictionary = d.t["rivals"]["unnamed"]
	var t: Dictionary = {}
	for x in r["tier"]:
		if x["size"] == tier:
			t = x
			break
	var h := half_years(st)
	var lvl: int
	if main_level == null:
		var ml: Dictionary = t["main_level"]
		var ups := 0
		for m in ml["level_up_months"]:
			if st.date() >= m:
				ups += 1
		lvl = ml["base"] + ups + g.r(ml["random"][0], ml["random"][1])
	else:
		lvl = main_level
	lvl = maxi(1, lvl)
	if probs.is_empty():
		probs = [25, 25, 25, 25]
	var main := 0
	for c in COLORS:
		if probs[c] > probs[main]:
			main = c
	var lv := [1, 1, 1, 1]
	lv[main] = lvl
	lv[guard_color(d, main)] = maxi(1, lvl - t["second_gap"])
	var habits: Array = d.t["habits"]["habits"]
	var hb: String = habits[g.below(habits.size())]["id"]
	return {"id": null, "name": "unnamed (%s)" % tier, "levels": lv,
		"fame": t["fame"]["base"] + t["fame"]["per_half_year"] * h, "habit": hb, "k": t["k"]}


## Named rival's data for the current month (9.1). From 1927-09 Valen is replaced by Nova or Jilbo (9.3); one is drawn.
static func named_rival(st, rid_in: String) -> Dictionary:
	var rv: Dictionary = st.d.t["rivals"]
	var date: String = st.date()
	var rid := rid_in
	for x in rv["replace"]:
		if x["old"] == rid and date >= x["from"]:
			rid = x["new"][st.rng.logic.below(x["new"].size())]
	var r: Dictionary = {}
	for x in rv["named"]:
		if x["id"] == rid:
			r = x
			break
	var lv = null
	var fame = null
	for s in r["stages"]:
		if date >= s["from"]:
			lv = s["levels"]
			fame = s.get("fame", fame)
	return {"id": rid, "name": r["name"], "levels": lv.duplicate(), "fame": fame, "habit": r["habit"], "k": r["k"]}


static func rival_present(st, rid: String) -> bool:
	for x in st.d.t["rivals"]["named"]:
		if x["id"] == rid:
			var date: String = st.date()
			return x["present"][0] <= date and date <= x["present"][1]
	return false


# ---------- play habits ----------

## Hand indexes ordered from the smallest to the largest solo value, ties by index.
static func _order(d, hand: Array, field: int) -> Array:
	var idx := []
	for i in hand.size():
		idx.append(i)
	idx.sort_custom(func(a, b):
		var va := solo_value(d, hand[a], field)
		var vb := solo_value(d, hand[b], field)
		if va != vb:
			return va < vb
		return a < b)
	return idx


## Which card (index into hand) the rival plays this round. score = [player round wins, rival round wins].
static func opponent_pick(st, habit: String, hand: Array, field: int, rnd: int, my_last, score: Array) -> int:
	var d = st.d
	var g = st.rng.logic
	var follow := false
	if habit != "habit_random":
		follow = g.chance(d.t["habits"]["follow_prob"], 100)
	if not follow:
		return g.below(hand.size())
	var order := _order(d, hand, field)
	var small: int = order[0]
	var big: int = order[order.size() - 1]
	if habit == "habit_lead":
		return big
	if habit == "habit_finish":
		return small
	if habit == "habit_open":
		return big if rnd == 0 else small
	if habit == "habit_follow":
		if rnd == 0:
			return order[order.size() / 2]
		for i in order:
			var v := effective(d, my_last, hand[i], field)
			if v[1] > v[0]:
				return i
		return small
	if habit == "habit_score":
		return big if score[1] <= score[0] else small
	push_error("unknown habit %s" % habit)
	return small


# ---------- one match ----------

static func roll_field(st, probs: Array) -> int:
	var v: int = st.rng.logic.below(100)
	var acc := 0
	for c in COLORS:
		acc += probs[c]
		if v < acc:
			return c
	return COLORS - 1


## Plays one match. Returns {score_line: [me, rival], style, rounds: [[my card, rival card, I won]], rival_cards, my_cards}.
## field = -1: the style is drawn from probs.
static func play_match(st, my_deck: Array, rival: Dictionary, probs: Array, player, field := -1) -> Dictionary:
	var d = st.d
	var need: int = cfg(d)["rounds_to_win"]
	var their_deck := opponent_deck(d, rival, probs)
	if field < 0:
		field = roll_field(st, probs)
	var mine := my_deck.duplicate(true)
	var theirs := their_deck.duplicate(true)
	var me := 0
	var them := 0
	var hist := []
	var my_last = null
	var fame_me: int = st.attr["fame"]
	var rnd := 0
	while me < need and them < need and not mine.is_empty():
		var oi := opponent_pick(st, rival["habit"], theirs, field, rnd, my_last, [me, them])
		var ctx := {"hand": mine.duplicate(true), "rival_hand": theirs.duplicate(true), "style": field, "round": rnd,
			"score_line": [me, them], "history": hist.duplicate(true), "opponents": rival}
		var mi: int = player.play(st, ctx)
		var a: Array = mine.pop_at(mi)
		var b: Array = theirs.pop_at(oi)
		var win := round_winner(d, a, b, field, fame_me, rival["fame"])
		if win:
			me += 1
		else:
			them += 1
		hist.append([a, b, win])
		my_last = a
		rnd += 1
	return {"score_line": [me, them], "style": field, "rounds": hist, "rival_cards": their_deck, "my_cards": my_deck.duplicate(true)}


# ---------- results ----------

static func player_levels(st) -> Array:
	var b: Dictionary = st.bonus()
	var lv := []
	for r in st.d.roads:
		var rep: int = st.rep(r, b)
		var L := 0
		for i in st.d.level_gate.size():
			if rep >= st.d.level_gate[i]:
				L = i
		lv.append(L)
	return lv


## The player's main color: the road with the highest current reputation, ties go to the earlier one.
static func player_main(st) -> int:
	var b: Dictionary = st.bonus()
	var best := 0
	var bv := -1
	for c in st.d.roads.size():
		var v: int = st.rep(st.d.roads[c], b)
		if v > bv:
			bv = v
			best = c
	return best


## Remembered by the director: the player's main color +pts percentage points, taken from the highest other color (7.4).
static func remembered_probs(probs: Array, main: int, pts: int) -> Array:
	var p := probs.duplicate()
	var top := -1
	for c in COLORS:
		if c != main and (top < 0 or p[c] > p[top]):
			top = c
	var move := mini(pts, p[top])
	p[main] += move
	p[top] -= move
	return p


static func classify(d, score: Array) -> String:
	var need: int = cfg(d)["rounds_to_win"]
	if score[0] >= need:
		return "remembered" if score[1] == 0 else "won"
	var nl: Array = cfg(d)["result"]["narrow_loss"]["score_line"]
	if score[0] == nl[0] and score[1] == nl[1]:
		return "narrow_loss"
	if score[0] == 0:
		return "botched"
	return "lost"


## One audition. rivals: the rival list (1 for small/medium films, 2 for big films; made by the board).
## probs: the style probabilities for this audition (empty = the role's; remembered, tutorial role etc. are computed by the caller first).
## Returns {result: won/narrow_loss/lost/botched, remembered, rounds: [match ...]} and settles 7.4 fame, report and duels.
static func audition(st, role: Dictionary, player, rivals: Array, probs: Array = []) -> Dictionary:
	var d = st.d
	if probs.is_empty():
		probs = role["style_probs"]
	var res: Dictionary = cfg(d)["result"]
	var out := {"roles": role["id"], "rounds": [], "remembered": false}
	var final := ""
	for n in rivals.size():
		var rv: Dictionary = rivals[n]
		var ctx := {"roles": role, "rounds": n, "opponents": rv, "levels": player_levels(st)}
		var colors: Array = player.deck(st, ctx)
		var bad: bool = colors.size() != cfg(d)["cards"]
		for c in colors:
			if c < 0 or c >= COLORS:
				bad = true
		if bad:
			push_error("bad deck: %s" % str(colors))
			return {}
		var m := play_match(st, build_deck(ctx["levels"], colors), rv, probs, player)
		out["rounds"].append(m)
		if rv["id"] != null:
			st.inc("duels." + rv["id"])
		var kind := classify(d, m["score_line"])
		if n == 0:
			final = kind
			out["remembered"] = kind == "remembered"
			if kind != "won" and kind != "remembered":
				break
		else:    # Second match of a big film: you only get the role by winning; a loss always counts as narrow_loss
			if kind != "won" and kind != "remembered":
				final = "narrow_loss"
			out["remembered"] = out["remembered"] and (kind == "won" or kind == "remembered")
	if final == "remembered":
		final = "won"
	if final == "botched":
		var x: Dictionary = res["botched"]
		Rules.apply_effect(st, x["effect"], "schedule")
		Rules.apply_effect(st, x["favor"], "schedule")
		if st.rng.logic.chance(x["report_prob"][0], x["report_prob"][1]):
			st.exposed = 1
			Rules.apply_effect(st, x["report_effect"], "schedule")
			out["reported"] = true
	if out["remembered"]:
		st.flags["remembered." + role["id"]] = 1
	out["result"] = final
	return out
