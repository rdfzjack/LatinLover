extends PanelContainer
## A picture slot. show_cg(keys, caption): the first existing picture of the keys (see assets.gd), otherwise a coloured placeholder
## with the caption. The slot has a fixed height so that the picture can be swapped in later without moving the layout.

const Assets = preload("res://ui/assets.gd")

@export var slot_height := 240.0


func show_cg(kind: String, keys: Array, caption: String) -> void:
	custom_minimum_size = Vector2(0, slot_height)
	for c in get_children():
		c.queue_free()
	var tex := Assets.find(kind, keys)
	if tex != null:
		var tr_ := TextureRect.new()
		tr_.texture = tex
		tr_.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr_.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		add_child(tr_)
		return
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color.from_hsv(float(hash(caption) % 360) / 360.0, 0.35, 0.35)
	add_theme_stylebox_override("panel", sb)
	var l := Label.new()
	l.text = tr("ui.cg.placeholder") % caption
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", 28)
	add_child(l)
