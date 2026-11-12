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
	m.heading("选片板（%s）" % st.date(), self)
	m.label("本月最多试两次，第二次要比第一次小一档。赢了的片约会锁定下个月的旬。名气门槛：你现在是「%s」。" % d.t["stats"]["fame_tiers"][st.fame_tier()]["name"], self)
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
		var title := "%s　[%s]%s" % [r["name"], m.SIZE_NAME.get(r["size"], r["size"]), "　【厂约】" if r["house"] else ""]
		m.heading(title, box)
		var line := "名气要求 %d　酬金 $%s" % [int(r["fame_gate"]), str(r["fee"])]
		if r.get("talkie") != null and r["talkie"]:
			line += "　有声片"
		m.label(line, box)
		var w := PackedStringArray()
		for x in r["wants"]:
			var have: int = st.val(x["stat"])
			w.append("%s %d（你 %d）" % [m.nm(x["stat"]), int(x["target"]), have])
		m.label("角色要求：" + "　".join(w), box)
		if r["intel"].get("tags", false) and not r["tags"].is_empty():
			var tg := PackedStringArray()
			for x in r["tags"]:
				tg.append(m.nm(x))
			m.label("内容：" + " ".join(tg), box)
		if r["style_probs"] != null:
			var sp := PackedStringArray()
			for c in 4:
				sp.append("%s %d%%" % [m.nm(d.roads[c]), int(r["style_probs"][c])])
			var t := "场风概率：" + "　".join(sp)
			if r["intel"].has("excluded"):
				t += "（探听到：不会出 %s）" % m.nm(d.roads[r["intel"]["excluded"]])
			m.label(t, box)
		if r["opponents"].size() > 0:
			var on := PackedStringArray()
			for k in r["opponents"].size():
				var o: Dictionary = r["opponents"][k]
				var s: String = m.rival_name(o)
				if r["intel"].has("habit") and k < r["intel"]["habit"].size() and r["intel"]["habit"][k]:
					s += "（习惯：" + m.nm(o["habit"]) + "）"
				on.append(s)
			m.label("对手：" + "、".join(on), box)
		if ok.has(i):
			var ii: int = i
			m.button("报名这个角色", func(): picked.emit(ii), box)
		else:
			m.label("不能报名：" + m.why(Board.can_try(st, i)), box, Color(1, 0.7, 0.7))
	m.button("不试了", func(): picked.emit(null), self)
