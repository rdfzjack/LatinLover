extends RefCounted
## Street, conversations, items and gear (GDD 5.8, 14.1). Port of sim/street.py.
## All are free actions at the start of the month and take no schedule slot.
##
## Python raises StreetError on failure; here every action returns "" on success or the reason it failed,
## and the state is unchanged on failure. Prices are computed with price() before buying.
## All functions are static; st is an instance of core/state.gd.

const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")

const IF_BROKE := "if_broke"


## Every full 20 of rapport displayed value gives 5% off, at most 25%.
static func discount_pct(st) -> int:
	var r: Dictionary = st.d.discount
	return mini(Rules.fdiv(st.val("rapport"), r["rapport_per"]) * r["cut_pct_per_step"], r["cap_pct"])


## Discounted price, rounded up; only entries in discount.applies get the discount.
static func price(st, entry: String, base: int) -> int:
	if not st.d.discount["applies"].has(entry):
		return base
	var pct: int = 100 - discount_pct(st)
	return -Rules.fdiv(-base * pct, 100)


static func _used(st, key: String, n: int) -> bool:
	return st.month_used.get(key, 0) >= n


static func _use(st, key: String) -> void:
	st.month_used[key] = st.month_used.get(key, 0) + 1


# ---------- buying and selling ----------

## What is on the shelf of that entry this month. The bookstore filters books by their on_shelf date.
static func shelf(st, entry: String) -> Array:
	var e: Dictionary = st.d.street[entry]
	if entry != "bookstore":
		return e["shelf"].duplicate()
	var out := []
	for b in e["shelf"]:
		if Schedule.book_on_shelf(st, b):
			out.append(b)
	return out


static func buy(st, entry: String, iid: String) -> String:
	if not shelf(st, entry).has(iid):
		return "%s does not sell %s" % [entry, iid]
	var d = st.d
	if d.books.has(iid):
		if st.books.has(iid) or st.read_books.has(iid):
			return "already own this book"
		var bp := price(st, entry, d.books[iid]["price"])
		if st.money < bp:
			return IF_BROKE
		st.money -= bp
		st.books[iid] = d.books[iid]["points"]
		return ""
	if st.items.size() >= d.item_rules["hold_cap"]:
		return "carrying too many items"
	var p := price(st, entry, d.items[iid]["price"])
	if st.money < p:
		return IF_BROKE
	st.money -= p
	st.items.append(iid)
	return ""


static func _equipped_count(st, iid: String) -> int:
	return (1 if st.equip["outfit"] == iid else 0) + st.equip["accessory"].count(iid)


## Any item sells at half price (rounded down); equipped ones cannot be sold. Books already read go through here too.
static func sell(st, iid: String) -> String:
	var d = st.d
	if st.read_books.has(iid):
		st.read_books.erase(iid)
		st.add_money(Rules.fdiv(d.books[iid]["price"], 2))
		return ""
	if not st.items.has(iid):
		return "no such item"
	var it: Dictionary = d.items[iid]
	if not it["sellable"]:
		return "this item cannot be sold"
	if st.items.count(iid) <= _equipped_count(st, iid):
		return "equipped items cannot be sold"
	st.items.erase(iid)
	st.add_money(Rules.fdiv(it["price"], 2))
	return ""


static func equip(st, iid: String) -> String:
	if not st.items.has(iid) or not st.d.items.has(iid):
		return "no such item"
	if st.items.count(iid) <= _equipped_count(st, iid):
		return "already equipped"
	var slot = st.d.items[iid]["slot"]
	if slot == "outfit":
		st.equip["outfit"] = iid
	elif slot == "accessory":
		if st.equip["accessory"].size() >= st.d.item_rules["accessory_slots"]:
			return "accessory slots are full"
		st.equip["accessory"].append(iid)
	else:
		return "this item cannot be equipped"
	return ""


static func unequip(st, iid: String) -> String:
	if st.equip["outfit"] == iid:
		st.equip["outfit"] = null
	elif st.equip["accessory"].has(iid):
		st.equip["accessory"].erase(iid)
	else:
		return "this item is not equipped"
	return ""


## Uses up one consumable. The trigger ids its effect returns are not fired (no consumable has one).
static func use(st, iid: String) -> String:
	if not st.items.has(iid) or not st.d.items.has(iid) or st.d.items[iid]["class"] != "consumable":
		return "not a held consumable"
	st.items.erase(iid)
	Rules.apply_effect(st, st.d.items[iid]["effect"], "event")
	return ""


# ---------- services ----------

## The service row, or {} when the entry has no such service.
static func _service(st, entry: String, sid: String) -> Dictionary:
	for s in st.d.street[entry]["services"]:
		if s["id"] == sid:
			return s
	return {}


## Once a month, pick one of three. When sick the money is still charged and there is no effect (GDD 5.8).
static func restaurant(st, sid: String) -> String:
	var e: Dictionary = st.d.street["restaurant"]
	var s := _service(st, "restaurant", sid)
	if s.is_empty():
		return "restaurant has no %s" % sid
	if _used(st, "restaurant", e["limit"]["times"]):
		return "already used this month"
	var p := price(st, "restaurant", s["price"])
	if st.money < p:
		return IF_BROKE
	st.money -= p
	_use(st, "restaurant")
	if not st.status["sick"]:
		Rules.apply_effect(st, s["effect"], "schedule")
	return ""


static func church(st) -> String:
	var s := _service(st, "church", "donation")
	if _used(st, "church.donation", s["limit"]["times"]):
		return "already used this month"
	if st.money < s["price"]:
		return IF_BROKE
	st.money -= s["price"]
	_use(st, "church.donation")
	Rules.apply_effect(st, s["effect"], "schedule")
	return ""


## "" when the hospital can be used now (sick), otherwise the reason. Does not change anything.
static func hospital_check(st) -> String:
	if not Rules.cond(st, st.d.street["hospital"]["cond"]):
		return "not sick"
	return ""


## Only usable when sick. Cost sick_index x 2 (discounted), fatigue -(sick_index+1).
static func hospital(st) -> String:
	if not Rules.cond(st, st.d.street["hospital"]["cond"]):
		return "not sick"
	var i: int = st.idx["sick_index"]
	var p := price(st, "hospital", i * 2)
	if st.money < p:
		return IF_BROKE
	st.money -= p
	st.attr["fatigue"] = maxi(0, st.attr["fatigue"] - (i + 1))
	return ""


## When reckless, let Sil persuade: fatigue -(Sil favor/2), Sil favor +2, once a month.
static func sil_persuade(st) -> String:
	var s := _service(st, "sil_talk", "persuade")
	if not Rules.cond(st, s["cond"]):
		return "not in a reckless state"
	if _used(st, "sil.persuade", s["limit"]["times"]):
		return "already used this month"
	_use(st, "sil.persuade")
	st.attr["fatigue"] = maxi(0, st.attr["fatigue"] - Rules.fdiv(st.favor.get("sil", 0), 2))
	st.favor["sil"] = Rules.favor_clamp(st, st.favor.get("sil", 0) + 2)
	return ""


## Status hint: picks one in the order sick, reckless, favor, fatigue, top attribute and returns [kind, detail].
## The favor and fatigue lines are not set in the GDD; for now favor >= 60 on a romance line and fatigue >= 50 (placeholder).
static func sil_hint(st) -> Array:
	if st.status["sick"]:
		return ["sick", "seriously ill" if st.idx["sick_index"] >= 60 else "do not overdo it"]
	if st.status["reckless"]:
		return ["reckless", st.idx["reckless_index"]]
	var top = null
	var tv := -1
	for n in st.d.romance_lines:          # ties: earlier line first
		var v: int = st.favor.get(n, 0)
		if v > tv:
			tv = v
			top = n
	if tv >= 60:
		return ["favor", top]
	if st.val("fatigue") >= 50:
		return ["fatigue", st.val("fatigue")]
	return ["top attribute", st.highest_base()]
