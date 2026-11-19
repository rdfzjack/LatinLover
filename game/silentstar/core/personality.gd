extends RefCounted
## Personality types (user, 2026-11): the same event moves different people's favor by different amounts.
## One step is 5 favor ("+" 5, "++" 10); the table is romance.json rules.personality. Which person has which type is the
## `personality` field of the npc row (actors only). Favor is changed directly, with no loyalty bonus, so the numbers stay exact.

const Rules = preload("res://core/rules.gd")


static func cfg(d) -> Dictionary:
	return d.t["romance"]["rules"]["personality"]


## Favor steps of one npc for an event key (see the table), 0 when he or she has no type.
static func steps(d, npc: String, key: String) -> int:
	var p: String = str(d.npcs.get(npc, {}).get("personality", ""))
	if p == "":
		return 0
	for t in cfg(d)["types"]:
		if t["id"] == p:
			return int(t[key])
	return 0


static func shift(st, npc: String, key: String) -> void:
	var n := steps(st.d, npc, key)
	if n != 0:
		Rules.apply_effect(st, "favor.%s%+d" % [npc, n * int(cfg(st.d)["step"])], "personality")


## An audition match against a named star: score = [player rounds, star rounds].
static func after_match(st, npc: String, score: Array) -> void:
	if npc == "":
		return
	if score[0] > score[1]:
		shift(st, npc, "win_clean" if score[1] == 0 else ("win_mid" if score[1] == 1 else "win_close"))
	else:
		shift(st, npc, "lose_zero" if score[0] == 0 else "lose")


## The heroine after a released film. serious: success days >= serious_pct% of the shooting days, and no side effect.
static func after_film(st, f: Dictionary, npc: String) -> void:
	var days: int = int(f["shoot_days"])
	var serious: bool = days > 0 and int(f["ok_days"]) * 100 >= int(cfg(st.d)["serious_pct"]) * days and not int(f.get("side", 0))
	shift(st, npc, "coop_serious" if serious else "coop_sloppy")


## The co-star of a hit (user 2026-11): +coop_hit favor, whatever the type. A normal, poor or flopped film changes nothing.
static func after_hit(st, npc: String) -> void:
	var n: int = int(cfg(st.d).get("coop_hit", 0))
	if n != 0:
		Rules.apply_effect(st, "favor.%s%+d" % [npc, n], "personality")


## Everyone with a type reacts to a hit or a flop of the player's film, scaled by the film's size (user 2026-11:
## release_pct small 0, medium 50, big 100; half a step rounds away from zero, so "+" is 3 and "++" is 5 on a medium film).
static func after_release(st, band: String, size := "big") -> void:
	if band != "hit" and band != "flop":
		return
	var pct: int = int(cfg(st.d).get("release_pct", {}).get(size, 100))
	if pct <= 0:
		return
	for n in st.d.npcs:
		var k := steps(st.d, n, band) * int(cfg(st.d)["step"])
		if k == 0:
			continue
		var v: int = Rules.fdiv(absi(k) * pct + 99, 100)
		Rules.apply_effect(st, "favor.%s%+d" % [n, v if k > 0 else -v], "personality")
