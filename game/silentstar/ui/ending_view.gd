extends VBoxContainer
## The ending page: picture slot, name, grade and score, the parts of the result, the text of the ending.

signal again
signal quit_to_title

const CgScene = preload("res://ui/cg_view.tscn")


func build(m) -> void:
	var d = m.d
	var st = m.st
	var e: Dictionary = st.story["ending"]
	var title: String = m.nm(e["ending"])
	if e.get("top_job") != null:
		title = title.replace("{top_job}", m.nm(e["top_job"]))
	var cg = CgScene.instantiate()
	add_child(cg)
	cg.show_cg("cg", ["ending/" + str(e["ending"]), "ending_category/" + str(e.get("category"))], title)
	m.heading(tr("ui.ending.build.1") + title, self)
	m.label(tr("ui.ending.build.2") % [str(e.get("grade")), str(e.get("total", "-"))], self)
	m.label(tr("ui.ending.build.3") + m.nm(e.get("category")), self)
	if e.has("character"):
		m.label(tr("ui.ending.build.4") + str(e["character"]), self)
	for x in e.get("rumors", []):
		m.label(str(x), self)
	for x in d.t["endings"].get("endings", []):
		if x["id"] == e["ending"] and x.get("content") != null:
			m.label(str(x["content"]), self)
	var hb := HBoxContainer.new()
	add_child(hb)
	m.button(tr("ui.ending.build.9"), func(): again.emit(), hb)
	m.button(tr("ui.ending.build.10"), func(): quit_to_title.emit(), hb)
