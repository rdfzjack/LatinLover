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
	return "%s %d点%s" % [m.nm(d.roads[card[0]]), card[1], text_extra]


# ---------------- phase 1: the deck ----------------

func show_deck(main, ctx: Dictionary) -> void:
	m = main
	d = m.d
	st = m.st
	var role: Dictionary = ctx["roles"]
	m.heading("试镜：%s" % role["name"], self)
	var rv: Dictionary = ctx["opponents"]
	var n: int = int(ctx["rounds"])
	var info := "对手：%s（第 %d 场）" % [m.rival_name(rv), n + 1]
	var habit_known := false
	if role["intel"].has("habit") and n < role["intel"]["habit"].size() and role["intel"]["habit"][n]:
		habit_known = true
		info += "　出牌习惯：" + m.nm(rv["habit"])
	m.label(info, self)
	if not habit_known:
		m.label("（对手的出牌习惯还不知道：人脉高、或和他交过手多次、或探听到，才看得到。）", self, Color(0.7, 0.7, 0.7))
	var lv: Array = ctx["levels"]
	var t := PackedStringArray()
	for c in 4:
		t.append("%s Lv%d" % [m.nm(d.roads[c]), lv[c]])
	m.label("你的等级：" + "　".join(t), self)
	if role["style_probs"] != null:
		var sp := PackedStringArray()
		for c in 4:
			sp.append("%s %d%%" % [m.nm(d.roads[c]), int(role["style_probs"][c])])
		m.label("本场场风概率（开场时抽一个）：" + "　".join(sp), self)
	m.label(m.rules_text(), self)
	m.label("选 5 张牌。同色第 k 张的点数 = 等级 − k，所以一种颜色放得越多，后面的牌越弱。", self, Color(1, 0.85, 0.4))

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
	m.button("确定牌组，开始比", func():
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
	m.heading("试镜：第 %d 轮　比分 %d : %d（先到 %d 分的赢）" % [int(ctx["round"]) + 1, sl[0], sl[1], int(m.ac()["rounds_to_win"])], self)
	var fl = m.label("本场场风：%s　（%s色的牌 ×%d%%，且不受克制）" % [m.nm(d.roads[field]), m.nm(d.roads[field]), int(m.ac()["style_pct"])], self)
	fl.modulate = COLORS[field]
	m.label(m.rules_text(), self)
	# the history of this audition
	var n := 1
	for h in ctx["history"]:
		var v: Array = Audition.effective(d, h[0], h[1], field)
		m.label("第 %d 轮：你 %s　对手 %s　→ %d : %d　%s" % [n, _card_btn(h[0]), _card_btn(h[1]), v[0], v[1], "你赢" if h[2] else "你输"], self, Color(0.75, 0.75, 0.75))
		n += 1
	var rr: int = ctx["rival_hand"].size()
	m.label("对手手里还有 %d 张牌（扣着）：%s" % [rr, "  ".join(PackedStringArray(Array(range(rr)).map(func(_x): return "▮")))], self)
	m.label("你的手牌，点一张打出去：", self)
	var hand: Array = ctx["hand"]
	var row := HBoxContainer.new()
	add_child(row)
	var btns: Array = []
	for i in hand.size():
		var c: Array = hand[i]
		var b := Button.new()
		b.text = "%s\n%d 点" % [m.nm(d.roads[c[0]]), c[1]]
		b.custom_minimum_size = Vector2(130, 90)
		b.modulate = COLORS[c[0]]
		var ii: int = i
		b.pressed.connect(func():
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
	m.heading("亮牌", self)
	var row := HBoxContainer.new()
	add_child(row)
	var l1 = m.label("你：\n%s\n%s" % [_card_btn(mine), m.card_text(mine, theirs, field)], row)
	l1.modulate = COLORS[mine[0]]
	var l2 = m.label("对手：\n%s\n%s" % [_card_btn(theirs), m.card_text(theirs, mine, field)], row)
	l2.modulate = COLORS[theirs[0]]
	var win: bool
	var how := ""
	if v[0] != v[1]:
		win = v[0] > v[1]
		how = "%d %s %d" % [v[0], ">" if win else "<", v[1]]
	else:
		win = fame_me > fame_them
		how = "%d = %d，平局比名气：%s" % [v[0], v[1], "你的名气更高，你赢" if win else "对手名气不低于你，对手赢"]
	var sl: Array = ctx["score_line"]
	var me: int = sl[0] + (1 if win else 0)
	var them: int = sl[1] + (0 if win else 1)
	var need: int = int(m.ac()["rounds_to_win"])
	var res = m.label("比较：%s\n这一轮：%s　　比分 %d : %d" % [how, "你赢了" if win else "你输了", me, them], self, Color(0.6, 1, 0.6) if win else Color(1, 0.6, 0.6))
	res.add_theme_font_size_override("font_size", 22)
	if me >= need or them >= need:
		m.label("这一场结束：" + ("你赢了这场！" if me >= need else "你输了这场。"), self, Color(1, 0.85, 0.4))
	m.button("下一步", func(): play_done.emit(mi), self)
