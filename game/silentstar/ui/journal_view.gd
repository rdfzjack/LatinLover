extends VBoxContainer
## The diary: the schedule book of the people he met (GDD 5.5.2) and the events that happened so far.

const Events = preload("res://core/events.gd")
const PERIOD_KEYS := {"early": "ui.period.early", "mid": "ui.period.mid", "late": "ui.period.late"}


func build(m) -> void:
	var d = m.d
	var st = m.st
	m.heading(tr("ui.journal.build.1"), self)
	var full: bool = st.val("rapport") >= int(d.t["npc_schedule"]["schedule_full_view_line"])
	m.label(tr("ui.journal.build.2") % [
		int(d.t["npc_schedule"]["schedule_full_view_line"]), st.val("rapport")], self)
	var shown := 0
	for s in d.schedule_npc:
		var npc: String = s["npc"]
		var met: bool = st.cnt("count.met." + npc) > 0
		if not (met or (full and st.known.has(npc))):
			continue
		shown += 1
		var ms := PackedStringArray()
		for x in s["months"]:
			ms.append(str(x))
		var ps := PackedStringArray()
		for x in s["periods"]:
			ps.append(tr(PERIOD_KEYS.get(x, x)))
		m.label(tr("ui.journal.build.3") % [m.nm(npc), m.nm(s["place"]), ",".join(ms), tr("ui.board.show_board.15").join(ps), s["years"][0], s["years"][1]], self)
	if shown == 0:
		m.label(tr("ui.journal.build.4"), self)
	m.heading(tr("ui.journal.build.5"), self)
	var last: Dictionary = st.story["last_fired"]
	var ids := last.keys()
	ids.sort_custom(func(a, b): return last[a] > last[b] if last[a] != last[b] else str(a) < str(b))
	if ids.is_empty():
		m.label(tr("ui.journal.build.6"), self)
	for id in ids:
		var times: int = st.fired.get(id, 1)
		m.label(tr("ui.journal.build.7") % [d.months[last[id]]["month"], m.nm(id), tr("ui.journal.build.8") % times if times > 1 else ""], self)
