extends RefCounted
## The co-star mini game (user, 2026-11, TODO C5): once per film, in the first shooting period, when the film has a named heroine
## (medium and big films). Same cards and screen as an audition. She has a hand of 5 cards, face up; the player builds 5 cards the
## usual way. Three rounds: she plays one of her cards (turned over at random), the player answers with one of his. Score of a round:
## same color 1, same number 1, both the same x2 (so 0, 1, 2 or 4); the sum is 0-12.
## The score gives P + score x per_point (max about +0.18, after the clamp of 500-1200) and her favor + score x favor_per_point.
## Numbers are in roles.json defaults.costar. The player is the agent (costar_deck, costar_play).

const Audition = preload("res://core/audition.gd")
const Rules = preload("res://core/rules.gd")
const Film = preload("res://core/film.gd")


static func cfg(d) -> Dictionary:
	return d.role_cfg["costar"]


## Her hand: 3 cards of her main road + 2 of the second road, levels from the expected level of the year (audition_curve).
static func her_hand(st, nid: String) -> Array:
	var d = st.d
	var n: Dictionary = d.npcs[nid]
	var c: Dictionary = cfg(d)
	var main: int = d.roads.find(n.get("road", ""))
	if main < 0:
		main = 0
	var sub: int = d.roads.find(n.get("road2", ""))
	if sub < 0 or sub == main:
		sub = Audition.guard_color(d, main)
	var lvl: int = Audition.curve_level(st) if Audition.curve_on(d) else 6
	var lv := [1, 1, 1, 1]
	lv[main] = lvl
	lv[sub] = maxi(1, lvl - int(c["second_gap"]))
	return Audition.deck_of(lv, main, int(c["main_cards"]), sub)


## Score of one round: [her card, his card].
static func round_score(a: Array, b: Array) -> int:
	var s := (1 if a[0] == b[0] else 0) + (1 if a[1] == b[1] else 0)
	return s * 2 if s == 2 else s


## Plays the mini game for film f once. Returns {score, bonus, rounds} or {} when the film has no named heroine or it was played already.
static func play(st, f: Dictionary, agent) -> Dictionary:
	var role: Dictionary = f["roles"]
	var hid: String = Film.partner(f)
	if hid == "" or f.has("costar") or not st.d.npcs.has(hid):
		return {}
	var d = st.d
	var c := cfg(d)
	var her := her_hand(st, hid)
	var levels: Array = Audition.player_levels(st)
	var ctx := {"costar": true, "roles": role, "heroine": hid, "you_lead": not f["support"], "rounds": 0, "levels": levels, "her_hand": her.duplicate(true)}
	var cols: Array = agent.costar_deck(st, ctx)
	var bad: bool = cols.size() != 5
	for x in cols:
		if x < 0 or x >= 4:
			bad = true
	if bad:
		cols = []
		for k in her:
			cols.append(k[0])
	var mine: Array = Audition.build_deck(levels, cols)
	var left: Array = her.duplicate(true)
	var hist := []
	var score := 0
	for r in int(c["rounds"]):
		var hc: Array = left.pop_at(st.rng.logic.below(left.size()))
		var ctx2 := {"costar": true, "roles": role, "heroine": hid, "you_lead": not f["support"], "round": r, "hand": mine.duplicate(true), "her_card": hc,
			"her_hand": left.duplicate(true), "history": hist.duplicate(true), "score": score, "total_rounds": int(c["rounds"]),
			"per_point": int(c["per_point"])}
		var mi: int = agent.costar_play(st, ctx2)
		mi = clampi(mi, 0, mine.size() - 1)
		var mc: Array = mine.pop_at(mi)
		var s := round_score(hc, mc)
		score += s
		hist.append([hc, mc, s])
	var bonus: int = score * int(c["per_point"])
	f["costar"] = {"score": score, "bonus": bonus, "rounds": hist}
	Rules.apply_effect(st, "favor.%s+%d" % [hid, score * int(c["favor_per_point"])], "personality")
	return f["costar"]
