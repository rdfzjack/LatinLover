extends RefCounted
## Status traits (traits.json, GDD 2.7): a trait is on while its cond holds; nothing is stored.
## effects: "no_audition" = cannot sign up for any audition (board.gd eligible, swap_role).

const Rules = preload("res://core/rules.gd")


## The traits on now, in table order.
static func active(st) -> Array:
	var out := []
	for x in st.d.traits:
		if Rules.cond(st, x.get("cond", [])):
			out.append(x)
	return out


## The first active trait with this effect, or {} when none.
static func with_effect(st, eff: String) -> Dictionary:
	for x in active(st):
		if x.get("effects", []).has(eff):
			return x
	return {}
