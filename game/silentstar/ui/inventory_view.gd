extends VBoxContainer
## Items and gear: equip, unequip, use, sell. Every action goes through core/street.gd and reports through the main screen.

const Street = preload("res://core/street.gd")


func build(m) -> void:
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
				m.button(tr("ui.inventory.build.6"), func(): m.act(Street.unequip(st, ii), tr("ui.inventory.build.7") + m.nm(ii)), hb)
			else:
				m.button(tr("ui.inventory.build.8"), func(): m.act(Street.equip(st, ii), tr("ui.inventory.build.9") + m.nm(ii)), hb)
		if it["class"] == "consumable":
			m.button(tr("ui.inventory.build.10"), func(): m.act(Street.use(st, ii), tr("ui.inventory.build.11") + m.nm(ii)), hb)
		m.button(tr("ui.inventory.build.12") % (int(it["price"]) / 2), func(): m.act(Street.sell(st, ii), tr("ui.inventory.build.13") + m.nm(ii)), hb)
	for bid in st.books:
		m.label(tr("ui.inventory.build.14") % [m.nm(bid), int(st.books[bid])], self)
	for bid in st.read_books:
		var hb := HBoxContainer.new()
		add_child(hb)
		m.label(tr("ui.inventory.build.15") % m.nm(bid), hb)
		var bb: String = bid
		m.button(tr("ui.inventory.build.12") % (int(d.books[bid]["price"]) / 2), func(): m.act(Street.sell(st, bb), tr("ui.inventory.build.13") + m.nm(bb)), hb)
