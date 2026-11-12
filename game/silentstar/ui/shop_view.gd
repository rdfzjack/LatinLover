extends VBoxContainer
## A shop in the city (no schedule slot is used): the three stores (buy), the pawn shop (sell), the restaurant, the church.

const Street = preload("res://core/street.gd")

var m
var entry: String
var back: Callable
var msg: Label
var list_box: VBoxContainer


func show_entry(main, shop_entry: String, back_cb: Callable) -> void:
	m = main
	entry = shop_entry
	back = back_cb
	_build()


func _build() -> void:
	for c in get_children():
		c.queue_free()
	var st = m.st
	var d = m.d
	m.button(tr("ui.shop.build.1"), back, self)
	m.heading(m.shop_title(entry), self)
	m.label(tr("ui.shop.build.2") % st.money, self)
	msg = m.label("", self, Color(0.6, 1, 0.6))
	match entry:
		"pawn":
			_pawn()
		"restaurant":
			_restaurant()
		"church":
			_church()
		_:
			_store()


func _say(result: String, ok_text: String) -> void:
	var text: String = ok_text if result == "" else tr("ui.main.act.1") + m.why(result)
	m.note(text)
	_build()
	msg.text = text
	m.refresh_status()


func _store() -> void:
	var st = m.st
	var d = m.d
	for iid in Street.shelf(st, entry):
		var base: int = d.books[iid]["price"] if d.books.has(iid) else d.items[iid]["price"]
		var p: int = Street.price(st, entry, base)
		var eff: String = (tr("ui.common.wide_space") + m.pretty(d.items[iid]["effect"])) if d.items.has(iid) else ""
		if d.books.has(iid):
			eff = tr("ui.shop.store.1") + m.book_text(iid)
		var hb := HBoxContainer.new()
		add_child(hb)
		m.label(tr("ui.main.fill_street.2") % [m.nm(iid), p, eff], hb)
		var e: String = entry
		var ii: String = iid
		m.button(tr("ui.main.fill_street.3"), func(): _say(Street.buy(st, e, ii), tr("ui.main.fill_street.4") + m.nm(ii)), hb)


func _pawn() -> void:
	var st = m.st
	var d = m.d
	m.label(tr("ui.shop.pawn.1"), self)
	var seen := {}
	for iid in st.items:
		if seen.has(iid):
			continue
		seen[iid] = true
		var it: Dictionary = d.items[iid]
		var hb := HBoxContainer.new()
		add_child(hb)
		m.label(tr("ui.shop.pawn.2") % [m.nm(iid), st.items.count(iid), m.pretty(it["effect"])], hb)
		var ii: String = iid
		m.button(tr("ui.inventory.build.12") % (int(it["price"]) / 2), func(): _say(Street.sell(st, ii), tr("ui.inventory.build.13") + m.nm(ii)), hb)
	for bid in st.read_books:
		var hb := HBoxContainer.new()
		add_child(hb)
		m.label(tr("ui.inventory.build.15") % m.nm(bid), hb)
		var bb: String = bid
		m.button(tr("ui.inventory.build.12") % (int(d.books[bid]["price"]) / 2), func(): _say(Street.sell(st, bb), tr("ui.inventory.build.13") + m.nm(bb)), hb)
	if st.items.is_empty() and st.read_books.is_empty():
		m.label(tr("ui.shop.pawn.3"), self)


func _restaurant() -> void:
	var st = m.st
	var d = m.d
	m.label(tr("ui.shop.restaurant.1"), self)
	for s in d.street["restaurant"]["services"]:
		var sid: String = s["id"]
		m.button(tr("ui.shop.restaurant.2") % [s["name"], Street.price(st, "restaurant", s["price"]), m.pretty(s["effect"])],
			func(): _say(Street.restaurant(st, sid), tr("ui.main.fill_street.7") + str(s["name"])), self)


func _church() -> void:
	var st = m.st
	m.label(tr("ui.shop.church.1"), self)
	m.button(tr("ui.shop.church.2"), func(): _say(Street.church(st), tr("ui.main.fill_street.10")), self)
