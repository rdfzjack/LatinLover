extends VBoxContainer
## Items and gear: equip, unequip, use. Selling is done at the pawn shop (shop_view.gd). Every action goes through core/street.gd;
## on_change is called after each action so that the host screen can redraw.

const Street = preload("res://core/street.gd")


func build(m, on_change := Callable()) -> void:
	var d = m.d
	var st = m.st
	m.heading(tr("ui.inventory.build.1"), self)
	m.label(tr("ui.inventory.build.2") % [m.nm(st.equip["outfit"]) if st.equip["outfit"] != null else tr("ui.inventory.build.3"), st.equip["accessory"].size(), int(d.item_rules["accessory_slots"])], self)
	var seen := {}
	for iid in st.items:
		if seen.has(iid):
			continue
		seen[iid] = true
		var it: Dictionary = d.items[iid]
		var hb := HBoxContainer.new()
		add_child(hb)
		var eq: bool = st.equip["outfit"] == iid or st.equip["accessory"].has(iid)
		m.label(tr("ui.inventory.build.4") % [m.nm(iid), st.items.count(iid), tr("ui.inventory.build.5") if eq else "", m.pretty(it["effect"])], hb)
		var ii: String = iid
		if it.get("slot") == "outfit" or it.get("slot") == "accessory":
			if eq:
				m.button(tr("ui.inventory.build.6"), func(): _do(m, on_change, Street.unequip(st, ii), tr("ui.inventory.build.7") + m.nm(ii)), hb)
			else:
				m.button(tr("ui.inventory.build.8"), func(): _do(m, on_change, Street.equip(st, ii), tr("ui.inventory.build.9") + m.nm(ii)), hb)
		if it["class"] == "consumable":
			m.button(tr("ui.inventory.build.10"), func(): _do(m, on_change, Street.use(st, ii), tr("ui.inventory.build.11") + m.nm(ii)), hb)
	for bid in st.books:
		m.label(tr("ui.inventory.build.16") % [m.nm(bid), int(st.books[bid]), m.book_text(bid)], self)
	for bid in st.read_books:
		m.label(tr("ui.inventory.build.15") % m.nm(bid), self)


func _do(m, on_change: Callable, result: String, ok_text: String) -> void:
	m.report(result, ok_text)
	if on_change.is_valid():
		on_change.call()
	m.refresh_status()
