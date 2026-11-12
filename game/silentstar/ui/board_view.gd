extends VBoxContainer
## Step 14: the casting board, one card per role. Emits picked(index) or picked(null) for "no more auditions".

signal picked(index)

const Board = preload("res://core/board.gd")
const SIZE_COLOR := {"small": Color(0.35, 0.45, 0.55), "medium": Color(0.45, 0.4, 0.6), "big": Color(0.6, 0.4, 0.35)}


func show_board(m, p: Dictionary) -> void:
	var d = m.d
	var st = m.st
	var b: Dictionary = p["board"]
	var ok: Array = p["ok"]
	m.heading(tr("ui.board.show_board.1") % st.date(), self)
	m.label(tr("ui.board.show_board.2") % d.t["stats"]["fame_tiers"][st.fame_tier()]["name"], self)
	for i in b["roles"].size():
		var r: Dictionary = b["roles"][i]
		var pc := PanelContainer.new()
		var sb := StyleBoxFlat.new()
		sb.bg_color = SIZE_COLOR.get(r["size"], Color(0.3, 0.3, 0.3))
		sb.content_margin_left = 10
		sb.content_margin_right = 10
		sb.content_margin_top = 6
		sb.content_margin_bottom = 6
		pc.add_theme_stylebox_override("panel", sb)
		add_child(pc)
		var box := VBoxContainer.new()
		pc.add_child(box)
		var title := tr("ui.board.show_board.3") % [r["name"], m.size_name(r["size"]), tr("ui.board.show_board.4") if r["house"] else ""]
		m.heading(title, box)
		var line := tr("ui.board.show_board.5") % [int(r["fame_gate"]), str(r["fee"])]
		if r.get("talkie") != null and r["talkie"]:
			line += tr("ui.board.show_board.6")
		m.label(line, box)
		var w := PackedStringArray()
		for x in r["wants"]:
			var have: int = st.val(x["stat"])
			w.append(tr("ui.board.show_board.7") % [m.nm(x["stat"]), int(x["target"]), have])
		m.label(tr("ui.board.show_board.8") + tr("ui.audition.show_deck.6").join(w), box)
		if r["intel"].get("tags", false) and not r["tags"].is_empty():
			var tg := PackedStringArray()
			for x in r["tags"]:
				tg.append(m.nm(x))
			m.label(tr("ui.board.show_board.9") + " ".join(tg), box)
		if r["style_probs"] != null:
			var sp := PackedStringArray()
			for c in 4:
				sp.append("%s %d%%" % [m.nm(d.roads[c]), int(r["style_probs"][c])])
			var t := tr("ui.board.show_board.10") + tr("ui.audition.show_deck.6").join(sp)
			if r["intel"].has("excluded"):
				t += tr("ui.board.show_board.11") % m.nm(d.roads[r["intel"]["excluded"]])
			m.label(t, box)
		if r["opponents"].size() > 0:
			var on := PackedStringArray()
			for k in r["opponents"].size():
				var o: Dictionary = r["opponents"][k]
				var s: String = m.rival_name(o)
				if r["intel"].has("habit") and k < r["intel"]["habit"].size() and r["intel"]["habit"][k]:
					s += tr("ui.board.show_board.12") + m.nm(o["habit"]) + tr("ui.board.show_board.13")
				on.append(s)
			m.label(tr("ui.board.show_board.14") + tr("ui.board.show_board.15").join(on), box)
		if ok.has(i):
			var ii: int = i
			m.button(tr("ui.board.show_board.16"), func(): picked.emit(ii), box)
		else:
			m.label(tr("ui.board.show_board.17") + m.why(Board.can_try(st, i)), box, Color(1, 0.7, 0.7))
	m.button(tr("ui.board.show_board.18"), func(): picked.emit(null), self)
