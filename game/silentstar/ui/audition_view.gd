extends VBoxContainer
## Step 14: one audition on screen. Phase 1 (show_deck): pick the 5 cards. Phase 2 (show_play, once per round): pick a card from the
## hand, both cards are turned over, the numbers are compared and the round is decided. The main screen (main.gd) owns the game
## thread; this view only builds widgets and emits the answer.

signal deck_done(colors)
signal play_done(index)

const Audition = preload("res://core/audition.gd")
const COLORS := [Color(0.95, 0.55, 0.5), Color(0.95, 0.6, 0.85), Color(0.55, 0.8, 0.95), Color(0.95, 0.85, 0.45)]   # tough, lover, culture, savvy

var m            # main.gd (names, helpers, data)
var d
var st


func _card_btn(card: Array, text_extra := "") -> String:
	return tr("ui.audition.card_btn.1") % [m.nm(d.roads[card[0]]), card[1], text_extra]


# ---------------- phase 1: the deck ----------------

func show_deck(main, ctx: Dictionary) -> void:
	m = main
	d = m.d
	st = m.st
	var role: Dictionary = ctx["roles"]
	m.heading(tr("ui.audition.show_deck.1") % role["name"], self)
	var rv: Dictionary = ctx["opponents"]
	var n: int = int(ctx["rounds"])
	var info := tr("ui.audition.show_deck.2") % [m.rival_name(rv), n + 1]
	var habit_known := false
	if role["intel"].has("habit") and n < role["intel"]["habit"].size() and role["intel"]["habit"][n]:
		habit_known = true
		info += tr("ui.audition.show_deck.3") + m.nm(rv["habit"])
	m.label(info, self)
	if not habit_known:
		m.label(tr("ui.audition.show_deck.4"), self, Color(0.7, 0.7, 0.7))
	var lv: Array = ctx["levels"]
	var t := PackedStringArray()
	for c in 4:
		t.append("%s Lv%d" % [m.nm(d.roads[c]), lv[c]])
	m.label(tr("ui.audition.show_deck.5") + tr("ui.common.wide_space").join(t), self)
	if role["style_probs"] != null:
		var sp := PackedStringArray()
		for c in 4:
			sp.append("%s %d%%" % [m.nm(d.roads[c]), int(role["style_probs"][c])])
		m.label(tr("ui.audition.show_deck.7") + tr("ui.common.wide_space").join(sp), self)
	m.label(m.rules_text(), self)
	m.label(tr("ui.audition.show_deck.8"), self, Color(1, 0.85, 0.4))

	var order := [0, 1, 2, 3]
	order.sort_custom(func(a, b): return lv[a] > lv[b] if lv[a] != lv[b] else a < b)
	var def := [order[0], order[0], order[0], order[1], order[1]]
	var row := HBoxContainer.new()
	add_child(row)
	var obs: Array = []
	var cards: Array = []
	for k in 5:
		var col := VBoxContainer.new()
		col.custom_minimum_size = Vector2(150, 0)
		row.add_child(col)
		var ob := OptionButton.new()
		for c in 4:
			ob.add_item(m.nm(d.roads[c]))
		ob.select(def[k])
		col.add_child(ob)
		var face := Label.new()
		face.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		face.add_theme_font_size_override("font_size", 26)
		col.add_child(face)
		obs.append(ob)
		cards.append(face)
	var refresh := func():
		var cols := []
		for ob in obs:
			cols.append(ob.selected)
		var deck: Array = Audition.build_deck(lv, cols)
		for k in 5:
			cards[k].text = "%d" % deck[k][1]
			cards[k].modulate = COLORS[deck[k][0]]
	for ob in obs:
		ob.item_selected.connect(func(_i): refresh.call())
	refresh.call()
	m.button(tr("ui.audition.show_deck.9"), func():
		var cols := []
		for ob in obs:
			cols.append(ob.selected)
		deck_done.emit(cols), self)


# ---------------- phase 2: one round ----------------

func show_play(main, ctx: Dictionary) -> void:
	m = main
	d = m.d
	st = m.st
	var field: int = ctx["style"]
	var sl: Array = ctx["score_line"]
	m.heading(tr("ui.audition.show_play.1") % [int(ctx["round"]) + 1, sl[0], sl[1], int(m.ac()["rounds_to_win"])], self)
	var fl = m.label(tr("ui.audition.show_play.2") % [m.nm(d.roads[field]), m.nm(d.roads[field]), int(m.ac()["style_pct"])], self)
	fl.modulate = COLORS[field]
	m.label(m.rules_text(), self)
	# the history of this audition
	var n := 1
	for h in ctx["history"]:
		var v: Array = Audition.effective(d, h[0], h[1], field)
		m.label(tr("ui.audition.show_play.3") % [n, _card_btn(h[0]), _card_btn(h[1]), v[0], v[1], tr("ui.audition.show_play.4") if h[2] else tr("ui.audition.show_play.5")], self, Color(0.75, 0.75, 0.75))
		n += 1
	# GDD 7.1 step 3: both hands are face up; the rival's remaining cards are shown with color and number
	var rival_hand: Array = ctx["rival_hand"]
	m.label(tr("ui.audition.show_play.6") % rival_hand.size(), self)
	var orow := HBoxContainer.new()
	add_child(orow)
	for oc in rival_hand:
		var ol = m.label(_card_btn(oc), orow)
		ol.custom_minimum_size = Vector2(130, 0)
		ol.modulate = COLORS[oc[0]]
	m.label(tr("ui.audition.show_play.7"), self)
	var hand: Array = ctx["hand"]
	var row := HBoxContainer.new()
	add_child(row)
	var btns: Array = []
	for i in hand.size():
		var c: Array = hand[i]
		var b := Button.new()
		b.text = tr("ui.audition.show_play.8") % [m.nm(d.roads[c[0]]), c[1]]
		b.custom_minimum_size = Vector2(130, 90)
		b.modulate = COLORS[c[0]]
		var ii: int = i
		b.pressed.connect(func():
			m.fx.cue("card_play", {"card": c})
			for x in btns:
				x.disabled = true
			_reveal(ctx, ii))
		row.add_child(b)
		btns.append(b)


func _reveal(ctx: Dictionary, mi: int) -> void:
	var field: int = ctx["style"]
	var mine: Array = ctx["hand"][mi]
	var oi = ctx.get("rival_pick")
	if oi == null:
		play_done.emit(mi)
		return
	var theirs: Array = ctx["rival_hand"][int(oi)]
	var v: Array = Audition.effective(d, mine, theirs, field)
	var fame_me: int = st.attr["fame"]
	var fame_them: int = int(ctx["opponents"]["fame"])
	m.heading(tr("ui.audition.reveal.1"), self)
	m.fx.cue("reveal", {"mine": mine, "theirs": theirs})
	var row := HBoxContainer.new()
	add_child(row)
	var l1 = m.label(tr("ui.audition.reveal.2") % [_card_btn(mine), m.card_text(mine, theirs, field)], row)
	l1.modulate = COLORS[mine[0]]
	var l2 = m.label(tr("ui.audition.reveal.3") % [_card_btn(theirs), m.card_text(theirs, mine, field)], row)
	l2.modulate = COLORS[theirs[0]]
	var win: bool
	var how := ""
	if v[0] != v[1]:
		win = v[0] > v[1]
		how = "%d %s %d" % [v[0], ">" if win else "<", v[1]]
	else:
		win = fame_me > fame_them
		how = tr("ui.audition.reveal.4") % [v[0], v[1], tr("ui.audition.reveal.5") if win else tr("ui.audition.reveal.6")]
	m.fx.cue("round_win" if win else "round_lose", {"mine": mine, "theirs": theirs})
	var sl: Array = ctx["score_line"]
	var me: int = sl[0] + (1 if win else 0)
	var them: int = sl[1] + (0 if win else 1)
	var need: int = int(m.ac()["rounds_to_win"])
	var res = m.label(tr("ui.audition.reveal.7") % [how, tr("ui.audition.reveal.8") if win else tr("ui.audition.reveal.9"), me, them], self, Color(0.6, 1, 0.6) if win else Color(1, 0.6, 0.6))
	res.add_theme_font_size_override("font_size", 22)
	if me >= need or them >= need:
		m.label(tr("ui.audition.reveal.10") + (tr("ui.audition.reveal.11") if me >= need else tr("ui.audition.reveal.12")), self, Color(1, 0.85, 0.4))
	m.button(tr("ui.audition.reveal.13"), func(): play_done.emit(mi), self)


# ---------------- the co-star mini game (core/costar.gd) ----------------

func _her_row(cards: Array, parent: Node) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	for oc in cards:
		var ol = m.label(_card_btn(oc), row)
		ol.custom_minimum_size = Vector2(130, 0)
		ol.modulate = COLORS[oc[0]]


func show_costar_deck(main, ctx: Dictionary) -> void:
	m = main
	d = m.d
	st = m.st
	m.heading(tr("ui.audition.costar_deck.1") % [m.nm(ctx["heroine"]), ctx["roles"]["name"]], self)
	m.label(tr("ui.audition.costar_deck.2"), self, Color(1, 0.85, 0.4))
	m.label(tr("ui.audition.costar_deck.3"), self)
	m.label(tr("ui.audition.costar_deck.4") % m.nm(ctx["heroine"]), self)
	_her_row(ctx["her_hand"], self)
	var lv: Array = ctx["levels"]
	var t := PackedStringArray()
	for c in 4:
		t.append("%s Lv%d" % [m.nm(d.roads[c]), lv[c]])
	m.label(tr("ui.audition.show_deck.5") + tr("ui.common.wide_space").join(t), self)
	var def := []
	for k in ctx["her_hand"]:
		def.append(k[0])
	var row := HBoxContainer.new()
	add_child(row)
	var obs: Array = []
	var cards: Array = []
	for k in 5:
		var col := VBoxContainer.new()
		col.custom_minimum_size = Vector2(150, 0)
		row.add_child(col)
		var ob := OptionButton.new()
		for c in 4:
			ob.add_item(m.nm(d.roads[c]))
		ob.select(def[k])
		col.add_child(ob)
		var face := Label.new()
		face.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		face.add_theme_font_size_override("font_size", 26)
		col.add_child(face)
		obs.append(ob)
		cards.append(face)
	var refresh := func():
		var cols := []
		for ob in obs:
			cols.append(ob.selected)
		var deck: Array = Audition.build_deck(lv, cols)
		for k in 5:
			cards[k].text = "%d" % deck[k][1]
			cards[k].modulate = COLORS[deck[k][0]]
	for ob in obs:
		ob.item_selected.connect(func(_i): refresh.call())
	refresh.call()
	m.button(tr("ui.audition.show_deck.9"), func():
		var cols := []
		for ob in obs:
			cols.append(ob.selected)
		deck_done.emit(cols), self)


func show_costar_play(main, ctx: Dictionary) -> void:
	m = main
	d = m.d
	st = m.st
	var r: int = int(ctx["round"])
	m.heading(tr("ui.audition.costar_play.1") % [m.nm(ctx["heroine"]), r + 1, int(ctx["total_rounds"]), int(ctx["score"])], self)
	m.label(tr("ui.audition.costar_deck.3"), self, Color(1, 0.85, 0.4))
	for h in ctx["history"]:
		m.label(tr("ui.audition.costar_play.2") % [_card_btn(h[0]), _card_btn(h[1]), int(h[2])], self, Color(0.75, 0.75, 0.75))
	m.label(tr("ui.audition.costar_play.3") % m.nm(ctx["heroine"]), self)
	var her: Array = ctx["her_card"]
	var hl = m.label(_card_btn(her), self)
	hl.add_theme_font_size_override("font_size", 26)
	hl.modulate = COLORS[her[0]]
	var left: Array = ctx["her_hand"]
	if not left.is_empty():
		m.label(tr("ui.audition.costar_play.4") % left.size(), self)
		_her_row(left, self)
	m.label(tr("ui.audition.show_play.7"), self)
	var hand: Array = ctx["hand"]
	var row := HBoxContainer.new()
	add_child(row)
	var btns: Array = []
	for i in hand.size():
		var c: Array = hand[i]
		var b := Button.new()
		b.text = tr("ui.audition.show_play.8") % [m.nm(d.roads[c[0]]), c[1]]
		b.custom_minimum_size = Vector2(130, 90)
		b.modulate = COLORS[c[0]]
		var ii: int = i
		b.pressed.connect(func():
			m.fx.cue("card_play", {"card": c})
			for x in btns:
				x.disabled = true
			_costar_reveal(ctx, ii))
		row.add_child(b)
		btns.append(b)


func _costar_reveal(ctx: Dictionary, mi: int) -> void:
	var Costar = preload("res://core/costar.gd")
	var mine: Array = ctx["hand"][mi]
	var her: Array = ctx["her_card"]
	var s: int = Costar.round_score(her, mine)
	m.heading(tr("ui.audition.reveal.1"), self)
	var same_c: bool = mine[0] == her[0]
	var same_p: bool = mine[1] == her[1]
	var txt := tr("ui.audition.costar_play.5") % [_card_btn(mine), _card_btn(her), tr("ui.audition.costar_play.6") if same_c else tr("ui.audition.costar_play.7"), tr("ui.audition.costar_play.8") if same_p else tr("ui.audition.costar_play.9"), s]
	m.label(txt, self, Color(0.6, 1, 0.6) if s > 0 else Color(1, 0.6, 0.6))
	var total: int = int(ctx["score"]) + s
	if int(ctx["round"]) + 1 >= int(ctx["total_rounds"]):
		m.label(tr("ui.audition.costar_play.10") % [total, total * int(ctx["per_point"]), total], self, Color(1, 0.85, 0.4))
	m.button(tr("ui.audition.reveal.13"), func(): play_done.emit(mi), self)
