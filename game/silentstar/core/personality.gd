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


## Everyone with a type whom the player has met reacts to a hit or a flop of the player's film. People not met yet do not
## (user, 2026-11: everyone is at 20 when first met; a snob's favor had dropped to 0 from flops before the first meeting).
static func after_release(st, band: String) -> void:
	if band != "hit" and band != "flop":
		return
	for n in st.d.npcs:
		if st.known.has(n):
			shift(st, n, band)
