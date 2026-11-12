extends Control
## Step 13: the main screen. Ugly on purpose, but every state of the game is reachable and readable.
##
## The game itself runs on a worker thread (core/ is synchronous: auditions, events and the three periods ask the player in the
## middle of run_month). Every question goes through ask(kind, payload): the worker posts the question to the screen and waits on a
## semaphore until the player answers. While the worker waits, the screen may read and change the state (street, items), which is
## exactly the "free actions at the start of the month" of GDD 4.
##
## Run: godot --path game/silentstar          (a window)
##      godot --headless --path game/silentstar -- --auto [--seed=N] [--months=N]     (plays itself with default answers, for testing)

const Data = preload("res://core/data.gd")
const Month = preload("res://core/month.gd")
const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")
const Street = preload("res://core/street.gd")
const Board = preload("res://core/board.gd")
const Events = preload("res://core/events.gd")
const Film = preload("res://core/film.gd")
const Audition = preload("res://core/audition.gd")
const Story = preload("res://core/story.gd")
const State = preload("res://core/state.gd")
const UiStory = preload("res://ui/ui_story.gd")

const SAVE_PATH := "user://autosave.json"
const SIZE_NAME := {"small": "小片", "medium": "中片", "big": "大片"}
const KIND_NAME := {"self_written": "自己写", "duv_written": "Duv 写", "co_written": "合写"}

var d
var g                      # Month
var st
var thread: Thread
var sem := Semaphore.new()
var answer = null
var auto := false
var title_shot := ""
var shot_kind := "plan"
var shot_path := ""         # --shot=file.png: saves a picture of the first screen that waits for the player, then quits
var uitest := false         # --uitest: builds every screen for real, then presses the buttons itself
var auto_months := 9999
var quitting := false
var names := {}

var prev_plan: Array = []
var skip_playback := false
var snap := {}             # state at the start of the month (for the settlement summary)
var last_snap := {}        # state after the previous period (for the playback)
var ev_seen := 0           # how many records of story.event_log were already shown

# widgets
var status_label: Label
var body: VBoxContainer
var log_box: RichTextLabel
var plan_btns: Array = []
var plan_info: Label
var street_box: VBoxContainer
var street_msg: Label
var sel_color := 0


# ================= start-up =================

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var seed_n := 1
	for a in args:
		if a == "--auto":
			auto = true
		elif a.begins_with("--titleshot="):
			title_shot = a.substr(12)
		elif a.begins_with("--shotkind="):
			shot_kind = a.substr(11)
		elif a.begins_with("--shot="):
			shot_path = a.substr(7)
			uitest = true
		elif a == "--uitest":
			uitest = true
		elif a.begins_with("--seed="):
			seed_n = int(a.substr(7))
		elif a.begins_with("--months="):
			auto_months = int(a.substr(9))
	d = Data.new()
	if not d.ok:
		push_error("cannot read the data tables")
		get_tree().quit(1)
		return
	_index_names(d.t)
	_build_frame()
	if title_shot != "":
		_title()
		_roll()
		for _i in 4:
			await get_tree().process_frame
		get_viewport().get_texture().get_image().save_png(title_shot)
		get_tree().quit()
	elif auto or uitest:
		_start_game(seed_n, [0, 0, 0])
	else:
		_title()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		quitting = true
		get_tree().quit()


func _build_frame() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var th := Theme.new()
	th.default_font_size = 18
	theme = th
	var root := VBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(root)
	status_label = Label.new()
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status_label.custom_minimum_size = Vector2(0, 100)
	root.add_child(status_label)
	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(split)
	var sc := ScrollContainer.new()
	sc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	split.add_child(sc)
	body = VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(body)
	log_box = RichTextLabel.new()
	log_box.custom_minimum_size = Vector2(320, 0)
	log_box.scroll_following = true
	log_box.bbcode_enabled = false
	split.add_child(log_box)


# ================= small helpers =================

func _index_names(v) -> void:
	if v is Dictionary:
		if v.has("id") and v.has("name") and v["id"] is String and v["name"] is String and not names.has(v["id"]):
			names[v["id"]] = v["name"]
		for k in v:
			_index_names(v[k])
	elif v is Array:
		for x in v:
			_index_names(x)


func nm(id) -> String:
	if id == null:
		return "-"
	var s := str(id)
	return names.get(s, s)


## "looks+30 speech-5" -> "相貌+30 谈吐-5"
func pretty(s) -> String:
	if s == null or str(s) == "":
		return ""
	var re := RegEx.new()
	re.compile("[a-z_]{3,}")
	var out := str(s)
	for m in re.search_all(str(s)):
		out = out.replace(m.get_string(), nm(m.get_string()))
	return out


func entry_name(e: String) -> String:
	var pe := Schedule.parse_entry(e)
	if pe.is_empty():
		return e
	var kind: String = pe[0]
	var s := nm(pe[1])
	if kind == "class":
		return "上课·" + s
	if kind == "book":
		return "看书·" + s
	if kind == "job":
		return "打工·" + s
	if pe[2] != null:
		return "外出·" + nm(pe[2]) + "（每天 $%d）" % Schedule.place_cost(st, pe[2])
	return s


const REASONS := {"out_of_reach": "名气不够", "morals": "品行条款（出事后一段时间不能接大片）", "not a house role": "长约期间只能接厂里的角色",
	"no board this month": "本月没有选片板", "this board already gave a role": "这块板已经拿到角色",
	"this board was already tried twice": "本月试过两次了", "this role was already tried": "这个角色试过了",
	"the second try must be a lower size than the first": "第二次要比第一次小一档"}


func why(r: String) -> String:
	return REASONS.get(r, r)


func rival_name(o: Dictionary) -> String:
	var n := str(o.get("name", ""))
	return "无名对手" if n == "" or n.begins_with("unnamed") else n


func rng_txt(a: int, b: int) -> String:
	if a == b:
		return "%+d" % a
	return "%+d~%+d" % [a, b]


## What one period of this entry does, in words and numbers (shown in brackets in the schedule menus).
func entry_effect(e: String) -> String:
	var pe := Schedule.parse_entry(e)
	if pe.is_empty():
		return ""
	var kind: String = pe[0]
	var iid: String = pe[1]
	var t := PackedStringArray()
	if kind == "class":
		var c: Dictionary = d.classes[iid]
		var lv := Schedule.class_level(st, iid)
		var gs := PackedStringArray()
		for x in c["gain"]:
			var pl: Array = x["per_level"][lv - 1]
			gs.append(nm(x["stat"]) + rng_txt(pl[0], pl[1]))
		t.append("成功日条件：体力/2+随机(0~体力/2)≥随机(0~疲劳)")
		t.append("成功日：" + " ".join(gs))
		t.append("每天疲劳%+d" % int(c.get("fatigue_per_day", 1)))
		t.append("学费 $%d/天（第 %d 级）" % [int(c["fee"][lv - 1]), lv])
	elif kind == "book":
		var b: Dictionary = d.books[iid]
		t.append("成功日条件：体力/2+随机(0~体力/2)≥随机(0~疲劳)")
		t.append("成功日：%s%s" % [nm(b["skills"]), rng_txt(b["gain"][0], b["gain"][1])])
		t.append("每天疲劳%+d" % int(b.get("fatigue_per_day", 1)))
		if st.books.has(iid):
			t.append("书还剩 %d 点" % int(st.books[iid]))
	elif kind == "job":
		var j: Dictionary = d.jobs[iid]
		t.append("成功的日子日薪 $%d" % Schedule.wage_of(st, iid))
		var gs := PackedStringArray()
		for x in j["daily_effect"]:
			gs.append(nm(x["stat"]) + rng_txt(x["add"][0], x["add"][1]))
		t.append("每天：" + " ".join(gs))
		var ls := PackedStringArray()
		for x in Schedule.job_lines(st, j):
			ls.append("%s−随机(0~疲劳)≥%s" % [nm(x[0]), str(x[1])])
		if not ls.is_empty():
			t.append("成功日条件：" + "，".join(ls))
	else:
		var r: Dictionary = d.rests[iid]
		if pe[2] != null:
			var pl: Dictionary = d.places[pe[2]]
			t.append("每天疲劳%+d，花 $%d/天，旬内发生一件事" % [int(pl["fatigue_per_day"]), Schedule.place_cost(st, pe[2])])
		else:
			t.append("每天疲劳%+d，免费，%s" % [int(r["fatigue_per_day"]), pretty(r.get("period_effect", ""))])
	return "；".join(t)


func clear_body() -> void:
	for c in body.get_children():
		c.queue_free()
	body.add_child(Control.new())   # keeps the container non-empty while the old children are freed
	plan_btns = []


func label(text: String, parent = null, color := Color(1, 1, 1)) -> Label:
	var l := Label.new()
	l.text = text
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	l.modulate = color
	(parent if parent != null else body).add_child(l)
	return l


func button(text: String, cb: Callable, parent = null) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(cb)
	(parent if parent != null else body).add_child(b)
	return b


func heading(text: String, parent = null) -> void:
	var l := label(text, parent, Color(1, 0.85, 0.4))
	l.add_theme_font_size_override("font_size", 22)


func note(text: String) -> void:
	if not is_inside_tree():
		return
	call_deferred("_log", text)


func _log(text: String) -> void:
	log_box.append_text(text + "\n")


func refresh_status() -> void:
	if st == null:
		status_label.text = "无声之星"
		return
	var b: Dictionary = st.bonus()
	var tier: Dictionary = d.t["stats"]["fame_tiers"][st.fame_tier()]
	var rg := RandomNumberGenerator.new()
	rg.seed = st.ym * 7919 + 13
	var mail := int(round(float(st.attr["fame"]) / 5.0 * rg.randf_range(0.8, 1.2)))
	var a := PackedStringArray()
	for k in ["stamina", "education", "loyalty", "looks", "discipline", "crime", "fatigue"]:
		a.append("%s %d" % [nm(k), st.val(k, b)])
	var r := PackedStringArray()
	for k in d.roads:
		var sk := PackedStringArray()
		for x in d.road_skills[k]:
			sk.append("%s %d" % [nm(x), st.val(x, b)])
		r.append("%s %d（%s）" % [nm(k), st.rep(k, b), " ".join(sk)])
	var flags := PackedStringArray()
	if st.status["very_sick"]:
		flags.append("重病")
	elif st.status["sick"]:
		flags.append("生病")
	if st.status["reckless"]:
		flags.append("失控")
	if st.status["in_love"]:
		flags.append("恋爱中")
	if st.status["long_contract"]:
		flags.append("长约")
	if st.drug > 0:
		flags.append("有瘾")
	var stock := int(st.flags.get("drug_stock", 0))
	if stock > 0:
		flags.append("药 %d 份" % stock)
	status_label.text = "%s   金钱 $%d   名气：%s（本月来信约 %d 封）   生活：%s\n%s\n声望（技能）：%s\n生病指数 %d  失控指数 %d   %s" % [
		st.date(), st.money, tier["name"], mail, nm(st.lifestyle), "  ".join(a), "   ".join(r),
		st.idx["sick_index"], st.idx["reckless_index"], " ".join(flags)]


func snapshot() -> Dictionary:
	var b: Dictionary = st.bonus()
	var s := {"money": st.money, "attr": {}, "skill": {}, "rep": {}}
	for k in d.attrs:
		s["attr"][k] = st.val(k, b)
	for k in d.skills:
		s["skill"][k] = st.val(k, b)
	for k in d.roads:
		s["rep"][k] = st.rep(k, b)
	return s


func diff_text(a: Dictionary, b: Dictionary) -> String:
	var out := PackedStringArray()
	if a["money"] != b["money"]:
		out.append("金钱 %+d" % (b["money"] - a["money"]))
	for grp in ["attr", "skill", "rep"]:
		for k in b[grp]:
			if k == "fame":
				continue
			if a[grp][k] != b[grp][k]:
				out.append("%s %+d" % [nm(k), b[grp][k] - a[grp][k]])
	return "，".join(out) if not out.is_empty() else "没有变化"


func new_events() -> PackedStringArray:
	var out := PackedStringArray()
	var lg: Array = g.hooks.event_log
	while ev_seen < lg.size():
		var rec: Dictionary = lg[ev_seen]
		var s: String = nm(rec["id"])
		if rec.has("options") and rec["options"] != null:
			var ev: Dictionary = d.events[rec["id"]]
			s += "（选了：" + str(ev["options"][rec["options"]]["text"]) + "）"
		if rec.has("check") and rec["check"] != null:
			s += "（判定" + ("成功" if rec["check"] else "失败") + "）"
		out.append(s)
		ev_seen += 1
	return out


# ================= title =================

const POOL_ATTRS := ["stamina", "education", "loyalty", "looks", "discipline"]
var alloc := {}            # starting values the player settled on (attributes and skills)
var base_vals := {}        # the same, as the origin answers leave them (the "default")
var alloc_box: VBoxContainer
var alloc_info: Label
var start_btn: Button
var origin_picks: Array = []
var roll_rng := RandomNumberGenerator.new()


## Rule of the starting values: the total of each pool stays what the three origin answers made it (pool 1: the five attributes,
## pool 2: the twelve skills), so a random start and a hand-made start are worth the same as the default; they only differ in shape.
## Each value may go down to half of its default and up to 150% of it (attributes: at least 60; skills: at least +15).
func _limits(id: String) -> Array:
	var v: int = base_vals[id]
	if POOL_ATTRS.has(id):
		return [v / 2, maxi(60, v * 3 / 2)]
	return [0, mini(100, maxi(v + 15, v * 3 / 2))]


func _pool_of(id: String) -> Array:
	return POOL_ATTRS if POOL_ATTRS.has(id) else d.skills


func _read_origin() -> void:
	var o := []
	for p in origin_picks:
		o.append(p.selected)
	var tmp = State.new(d)
	tmp.start(1, o)
	base_vals = {}
	for k in POOL_ATTRS:
		base_vals[k] = tmp.attr[k]
	for k in d.skills:
		base_vals[k] = tmp.skill[k]
	alloc = base_vals.duplicate()


func _roll() -> void:
	roll_rng.randomize()
	alloc = base_vals.duplicate()
	for pool in [POOL_ATTRS, d.skills]:
		var step: int = 10 if pool == POOL_ATTRS else 2
		for _n in 120:
			var a: String = pool[roll_rng.randi() % pool.size()]
			var c: String = pool[roll_rng.randi() % pool.size()]
			if a == c:
				continue
			if alloc[a] - step >= _limits(a)[0] and alloc[c] + step <= _limits(c)[1]:
				alloc[a] -= step
				alloc[c] += step
	_rebuild_alloc()


func _rebuild_alloc() -> void:
	for c in alloc_box.get_children():
		c.queue_free()
	for pool in [POOL_ATTRS, d.skills]:
		var grid := GridContainer.new()
		grid.columns = 6 if pool == POOL_ATTRS else 6
		alloc_box.add_child(grid)
		for id in pool:
			label(nm(id), grid)
			var sb := SpinBox.new()
			var lim := _limits(id)
			sb.min_value = lim[0]
			sb.max_value = lim[1]
			sb.step = 1
			sb.value = alloc[id]
			var ii: String = id
			sb.value_changed.connect(func(v):
				alloc[ii] = int(v)
				_update_alloc_info())
			grid.add_child(sb)
	_update_alloc_info()


func _update_alloc_info() -> void:
	var t := PackedStringArray()
	var okk := true
	for pool in [POOL_ATTRS, d.skills]:
		var sum := 0
		var tot := 0
		for id in pool:
			sum += alloc[id]
			tot += base_vals[id]
		var left: int = tot - sum
		t.append("%s：还剩 %d 点要分%s" % ["属性" if pool == POOL_ATTRS else "技能", left, "" if left != 0 else "（已分完）"])
		if left != 0:
			okk = false
	alloc_info.text = "　".join(t) + "（多出来的要从别处减掉；每项范围见输入框）"
	start_btn.disabled = not okk


func _title() -> void:
	st = null
	refresh_status()
	clear_body()
	heading("无声之星")
	label("三个问题决定出身：")
	origin_picks = []
	for q in d.origins:
		label(q["question"])
		var ob := OptionButton.new()
		for o in q["options"]:
			ob.add_item(o["text"])
		body.add_child(ob)
		origin_picks.append(ob)
		ob.item_selected.connect(func(_i):
			_read_origin()
			_rebuild_alloc())
	heading("起始数值")
	label("总点数由出身决定，可以重新分配：点“随机”掷一个新的，或者自己填。不动就是默认值。")
	var hb0 := HBoxContainer.new()
	body.add_child(hb0)
	button("随机一个", func(): _roll(), hb0)
	button("恢复默认", func():
		alloc = base_vals.duplicate()
		_rebuild_alloc(), hb0)
	alloc_box = VBoxContainer.new()
	body.add_child(alloc_box)
	alloc_info = label("", null, Color(1, 0.85, 0.4))
	_read_origin()
	_rebuild_alloc()
	var hb := HBoxContainer.new()
	body.add_child(hb)
	label("随机种子（留空 = 随机）：", hb)
	var seed_edit := LineEdit.new()
	seed_edit.custom_minimum_size = Vector2(160, 0)
	hb.add_child(seed_edit)
	start_btn = button("新游戏", func():
		var o := []
		for p in origin_picks:
			o.append(p.selected)
		var sd: int = int(seed_edit.text) if seed_edit.text.strip_edges() != "" else randi() % 1000000 + 1
		_start_game(sd, o, alloc))
	if FileAccess.file_exists(SAVE_PATH):
		button("继续上次的存档（每月结算后自动存）", func(): _continue_game())
	_update_alloc_info()


func _start_game(seed_n: int, origin: Array, start_vals := {}) -> void:
	var agent = UiStory.UiAgent.new(self)
	var story = UiStory.new(agent, self)
	g = Month.new(d, seed_n, origin, story)
	st = g.st
	for k in start_vals:
		if POOL_ATTRS.has(k):
			st.attr[k] = start_vals[k]
		else:
			st.skill[k] = start_vals[k]
	st.update_indices()
	prev_plan = []
	_run_thread()


func _continue_game() -> void:
	var s := FileAccess.get_file_as_string(SAVE_PATH)
	var agent = UiStory.UiAgent.new(self)
	var story = UiStory.new(agent, self)
	var m = Month.restore(s, d, story)
	if m == null:
		_log("存档读不了（版本不对）。")
		return
	g = m
	st = g.st
	prev_plan = []
	_run_thread()


func _run_thread() -> void:
	ev_seen = 0
	clear_body()
	note("—— 新的一局 ——")
	thread = Thread.new()
	thread.start(_worker)


# ================= the game thread =================

func _worker() -> void:
	var months := 0
	while not st.finished and not quitting and months < auto_months:
		g.start_month()
		last_snap = snapshot()
		snap = last_snap
		skip_playback = false
		ev_seen = g.hooks.event_log.size()
		var plan: Array = ask("plan", null)
		if quitting:
			return
		var errs: Array = g.run_month(plan)
		if not errs.is_empty():
			note("日程不能用：" + str(errs))
			g.started = true     # start_month already ran; try again after a new plan
			continue
		months += 1
		prev_plan = plan
		if not st.finished:
			var s: String = g.save()
			var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
			if f != null:
				f.store_string(s)
		ask("summary", null)
	if st.finished:
		ask("ending", null)
	if auto or uitest:
		call_deferred("_auto_done")


func _auto_done() -> void:
	thread.wait_to_finish()
	print("auto run finished: %s, %d fired events, ending %s" % [st.date(), st.fired.size(), str(st.ended)])
	get_tree().quit()


## Called on the game thread. Posts the question to the screen and waits for the answer.
func ask(kind: String, payload):
	if quitting:
		return null
	if auto:
		return _auto_answer(kind, payload)
	answer = null
	call_deferred("_show_request", kind, payload)
	sem.wait()
	return answer


func reply(v) -> void:
	answer = v
	sem.post()


## Called by UiStory (game thread) after each period has been settled.
func period_done(_st, i: int, entry: String, out: Dictionary) -> void:
	var now := snapshot()
	var evs := new_events()
	var days := Schedule.days_of(st, i)
	var span := "%d–%d 日" % [days[0][0], days[days.size() - 1][0]]
	var title: String = ["上旬", "中旬", "下旬"][i]
	var what: String = "拍摄：" + str(out.get("film", "")) if entry == "shooting" else entry_name(entry)
	var lines := PackedStringArray()
	lines.append("%s（%s）：%s" % [title, span, what])
	lines.append("　" + diff_text(last_snap, now))
	for e in evs:
		lines.append("　事件：" + e)
	var text := "\n".join(lines)
	last_snap = now
	note(text)
	if skip_playback:
		return
	var r = ask("period", {"text": text, "i": i})
	if r == "skip":
		skip_playback = true


func ac() -> Dictionary:
	return d.t["habits"]["audition"]


func rules_text() -> String:
	var c := ac()
	var order: Array = c["color_order"]
	var ring := []
	for n in order:
		ring.append("%s克%s" % [nm(n), nm(c["counters"][n])])
	return "【算法】每张牌的点数 = 同色第 k 张：等级−k（最低 0）。比较时 v = 点数×100，然后：\n　① 牌色 = 本场场风色：v × %d%%\n　② 我的色克对方的色，且对方的牌不是场风色：我 v × %d%%，对方 v × %d%%（对方克我同理）\n　③ 场风色不受克制。克制环：%s\n　④ v 大的赢这一轮；相等则名气高的赢；再相等对手赢。先赢 %d 轮的赢这场。" % [
		int(c["style_pct"]), int(c["counter_pct"]), int(c["countered_pct"]), "、".join(ring), int(c["rounds_to_win"])]


## One card's value with the reason, e.g. "硬汉 3 → 300 ×130%（场风）= 390"
func card_text(card: Array, other: Array, field: int) -> String:
	var v: Array = Audition.effective(d, card, other, field)
	var base: int = card[1] * 100
	var why := []
	if card[0] == field:
		why.append("场风 ×%d%%" % int(ac()["style_pct"]))
	var bt := Audition.beats(d)
	if card[0] != field and other[0] != field:
		if bt[card[0]] == other[0]:
			why.append("克制对方 ×%d%%" % int(ac()["counter_pct"]))
		elif bt[other[0]] == card[0]:
			why.append("被克制 ×%d%%" % int(ac()["countered_pct"]))
	return "%s %d点 = %d%s → %d" % [nm(d.roads[card[0]]), card[1], base, ("（" + "，".join(why) + "）") if not why.is_empty() else "", v[0]]


func audition_text(role: Dictionary, res: Dictionary) -> String:
	var t := PackedStringArray()
	t.append("试镜《%s》[%s]" % [role["name"], SIZE_NAME.get(role["size"], role["size"])])
	var k := 1
	for m in res["rounds"]:
		t.append("　第 %d 场 %d : %d" % [k, m["score_line"][0], m["score_line"][1]])
		k += 1
	var r: String = res["result"]
	var verdict := ""
	match r:
		"won":
			verdict = "赢了！" + ("全胜，导演记住了你的路数。" if res.get("remembered", false) else "") + "拿下了这个角色，下个月开拍。"
		"narrow_loss":
			if res.get("support", false):
				verdict = "险败（2:3），但你接了同片的配角，下个月开拍（酬金少、拍的旬少）。"
			else:
				verdict = "险败（2:3），没拿到角色。"
		"botched":
			verdict = "惨败，一分没得，名气下降" + ("，还上了小报。" if res.get("reported", false) else "。")
		_:
			verdict = "输了，没拿到角色。"
	t.append(verdict)
	return "\n".join(t)


# ================= automatic answers (test mode) =================

func _auto_answer(kind: String, payload):
	match kind:
		"plan":
			var plan := []
			var opts := Schedule.options(st)
			var rng := RandomNumberGenerator.new()
			rng.seed = st.ym + 1
			for i in 3:
				var e: String = opts[rng.randi() % opts.size()]
				plan.append(e)
			var fixed := Story.fit_plan(g, plan)
			return fixed
		"deck":
			var lv: Array = payload["levels"]
			var order := [0, 1, 2, 3]
			order.sort_custom(func(a, b): return lv[a] > lv[b] if lv[a] != lv[b] else a < b)
			return [order[0], order[0], order[0], order[1], order[1]]
		"play":
			return 0
		"pick_role":
			return payload["ok"][0]
		"support", "stunt", "suppress":
			return true
		"option":
			return payload["avail"][0]
		"annual":
			return payload[0]["id"] if not payload.is_empty() else null
		"family":
			return d.tag_families.keys()[0]
		"boost":
			return st.ym % 2 == 0
		"period":
			return "ok"
	return null


# ================= the questions on screen =================

func _show_request(kind: String, payload) -> void:
	refresh_status()
	match kind:
		"plan": _show_plan()
		"pick_role": _show_board(payload)
		"deck": _show_deck(payload)
		"play": _show_play(payload)
		"support": _yes_no("险败", "你以微小的差距输了。接受同一部片子的配角吗？（酬金少、拍摄旬少）", payload["name"])
		"stunt": _yes_no("替身戏", "这个角色可以亲自上阵（高风险、有加成）。亲自上吗？", payload["name"])
		"suppress": _yes_no("丑闻", "要压下这件丑闻吗？" + ("（本年免费一次）" if payload == "free" else "（花 200）"), "")
		"boost": _yes_no("用药", "这一旬开始前，要吃一份药吗？（剩 %d 份）" % int(st.flags.get("drug_stock", 0)), "")
		"option": _show_option(payload)
		"annual": _show_annual(payload)
		"family": _show_family()
		"period": _show_period(payload)
		"notice":
			_wait_screen("结果")
			label(str(payload))
			button("继续", func(): reply(null))
		"summary": _show_summary()
		"ending": _show_ending()
		_:
			push_error("unknown question %s" % kind)
			reply(null)
	if uitest:
		await get_tree().process_frame
		if shot_path != "" and (kind == shot_kind):
			for _i in 3:
				await get_tree().process_frame
			get_viewport().get_texture().get_image().save_png(shot_path)
			get_tree().quit()
			return
		_uitest_answer(kind, payload)


## --uitest: press every button of the street once, then answer the question as the automatic player would.
func _uitest_answer(kind: String, payload) -> void:
	if kind == "plan" and st.ym < 3:
		var btns: Array = []
		_collect_buttons(street_box, btns)
		for b in btns:
			if is_instance_valid(b) and b.get_parent() != null:
				b.pressed.emit()
		var plan: Array = _current_plan()
		if g.plan_errors(plan).is_empty():
			reply(plan)
			return
	reply(_auto_answer(kind, payload))


func _collect_buttons(n: Node, out: Array) -> void:
	for c in n.get_children():
		if c is Button and not c.is_queued_for_deletion():
			out.append(c)
		_collect_buttons(c, out)


func _wait_screen(title: String) -> void:
	clear_body()
	heading(title)


func _yes_no(title: String, text: String, extra: String) -> void:
	_wait_screen(title)
	if extra != "":
		label(extra)
	label(text)
	var hb := HBoxContainer.new()
	body.add_child(hb)
	button("是", func(): reply(true), hb)
	button("否", func(): reply(false), hb)


func _show_option(p: Dictionary) -> void:
	var ev: Dictionary = p["event"]
	_wait_screen("事件：" + str(ev["name"]))
	if ev.get("body") != null:
		label(str(ev["body"]))
	label("选一个：")
	for k in p["avail"]:
		var o: Dictionary = ev["options"][k]
		var t: String = str(o["text"])
		if Schedule.truthy(o.get("check")):
			t += "（要判定）"
		var kk: int = k
		button(t, func(): reply(kk))


func _show_annual(opts: Array) -> void:
	_wait_screen("年度大事")
	label("十二月，选一场出席（会累，会和同行排名），或者休息（疲劳清零）：")
	for x in opts:
		var id: String = x["id"]
		button("%s（%s路，现有声望 %d）" % [nm(id), nm(x["road"]), st.rep(x["road"])], func(): reply(id))
	button("休息", func(): reply(null))


func _show_family() -> void:
	_wait_screen("转型")
	label("片厂老板要帮你转型，选一个内容方向：")
	for k in d.tag_families:
		var kk: String = k
		button(nm(k), func(): reply(kk))


func _show_period(p: Dictionary) -> void:
	_wait_screen("本月进行中")
	label(str(p["text"]))
	var hb := HBoxContainer.new()
	body.add_child(hb)
	button("继续", func(): reply("ok"), hb)
	button("跳过本月剩下的播放", func(): reply("skip"), hb)


# ---------- the board and auditions ----------

func _show_board(p: Dictionary) -> void:
	var b: Dictionary = p["board"]
	var ok: Array = p["ok"]
	_wait_screen("选片板（%s）" % st.date())
	label("本月最多试两次，第二次要比第一次小一档。赢了的片约会锁定下个月的旬。")
	for i in b["roles"].size():
		var r: Dictionary = b["roles"][i]
		var t := "%s　[%s]　名气要求 %d　酬金 $%s" % [r["name"], SIZE_NAME.get(r["size"], r["size"]), int(r["fame_gate"]), str(r["fee"])]
		var w := PackedStringArray()
		for x in r["wants"]:
			w.append("%s≥%d" % [nm(x["stat"]), int(x["target"])])
		t += "\n　要求：" + " ".join(w)
		if r["intel"].get("tags", false) and not r["tags"].is_empty():
			var tg := PackedStringArray()
			for x in r["tags"]:
				tg.append(nm(x))
			t += "　内容：" + " ".join(tg)
		if r["style_probs"] != null:
			var sp := PackedStringArray()
			for c in 4:
				sp.append("%s %d%%" % [nm(d.roads[c]), int(r["style_probs"][c])])
			t += "\n　戏路：" + " ".join(sp)
			if r["intel"].has("excluded"):
				t += "（探听到：不会出 %s）" % nm(d.roads[r["intel"]["excluded"]])
		if r.get("talkie") != null and r["talkie"]:
			t += "　有声片"
		if r["house"]:
			t += "　【厂约】"
		if r["opponents"].size() > 0:
			var on := PackedStringArray()
			for o in r["opponents"]:
				on.append(rival_name(o))
			t += "\n　对手：" + "、".join(on)
		label(t)
		if ok.has(i):
			var ii: int = i
			button("报名：" + str(r["name"]), func(): reply(ii))
		else:
			label("　（不能报名：" + why(Board.can_try(st, i)) + "）", null, Color(0.6, 0.6, 0.6))
	button("不试了", func(): reply(null))


func _show_deck(ctx: Dictionary) -> void:
	var r: Dictionary = ctx["roles"]
	_wait_screen("试镜：" + str(r["name"]))
	var lv: Array = ctx["levels"]
	var t := PackedStringArray()
	for c in 4:
		t.append("%s Lv%d" % [nm(d.roads[c]), lv[c]])
	label("你的等级：" + "  ".join(t))
	var o = ctx["opponents"]
	label("对手：" + rival_name(o) + "　（第 %d 场）" % (int(ctx["rounds"]) + 1))
	label(rules_text())
	if ctx["roles"]["style_probs"] != null:
		var sp := PackedStringArray()
		for c in 4:
			sp.append("%s %d%%" % [nm(d.roads[c]), int(ctx["roles"]["style_probs"][c])])
		label("本场场风概率：" + "  ".join(sp))
	label("组 5 张牌（同色第 k 张点数 = 等级 − k，后面的牌更弱）：")
	var order := [0, 1, 2, 3]
	order.sort_custom(func(a, b): return lv[a] > lv[b] if lv[a] != lv[b] else a < b)
	var def := [order[0], order[0], order[0], order[1], order[1]]
	var obs: Array = []
	var hb := HBoxContainer.new()
	body.add_child(hb)
	for k in 5:
		var ob := OptionButton.new()
		for c in 4:
			ob.add_item(nm(d.roads[c]))
		ob.select(def[k])
		hb.add_child(ob)
		obs.append(ob)
	button("确定牌组", func():
		var cols := []
		for ob in obs:
			cols.append(ob.selected)
		reply(cols))


func _show_play(ctx: Dictionary) -> void:
	_wait_screen("试镜：第 %d 轮" % (int(ctx["round"]) + 1))
	var sl: Array = ctx["score_line"]
	label("比分 %d : %d　本场风格：%s" % [sl[0], sl[1], nm(d.roads[ctx["style"]])])
	label(rules_text())
	var n := 1
	for h in ctx["history"]:
		var v: Array = Audition.effective(d, h[0], h[1], ctx["style"])
		label("第 %d 轮：你 %s\n　　　对手 %s\n　　　%d %s %d → %s" % [n, card_text(h[0], h[1], ctx["style"]), card_text(h[1], h[0], ctx["style"]),
			v[0], ">" if v[0] > v[1] else ("<" if v[0] < v[1] else "="), v[1], "你赢" if h[2] else "你输"])
		n += 1
	label("对手还剩 %d 张牌（不知道他出哪张）。你的每张牌在不同情况下的有效点数：" % ctx["rival_hand"].size())
	var hand: Array = ctx["hand"]
	for i in hand.size():
		var ii: int = i
		var c: Array = hand[i]
		var plain: int = c[1] * 100
		var inf: int = plain * int(ac()["style_pct"]) / 100 if c[0] == ctx["style"] else plain
		var txt := "%s　点数 %d　基础 %d" % [nm(d.roads[c[0]]), c[1], plain]
		if c[0] == ctx["style"]:
			txt += "　场风 ×%d%% = %d" % [int(ac()["style_pct"]), inf]
		else:
			txt += "　克制对方时 %d，被克制时 %d" % [plain * int(ac()["counter_pct"]) / 100, plain * int(ac()["countered_pct"]) / 100]
		button(txt, func(): reply(ii))


# ================= the month plan =================

func _show_plan() -> void:
	clear_body()
	heading("%s　排本月的日程" % st.date())
	var tabs := TabContainer.new()
	tabs.custom_minimum_size = Vector2(0, 560)
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(tabs)
	var t1 := VBoxContainer.new()
	t1.name = "日程"
	tabs.add_child(t1)
	var t2 := ScrollContainer.new()
	t2.name = "街道和谈话"
	t2.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs.add_child(t2)
	street_box = VBoxContainer.new()
	street_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t2.add_child(street_box)
	var t3 := ScrollContainer.new()
	t3.name = "状态"
	t3.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs.add_child(t3)
	var sbox := VBoxContainer.new()
	sbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t3.add_child(sbox)
	_fill_schedule(t1)
	_fill_street()
	_fill_status(sbox)


func _fill_schedule(box: VBoxContainer) -> void:
	label("上月的安排已经预填。要改的旬点开下拉；不改直接按「开始本月」。括号里是这一旬每天的效果和成功条件（疲劳 + 是变累，− 是恢复；「随机(0~X)」是每天掷一个 0 到 X 的数）。恋爱中每天另有 20% 失败；失控时打工另有偷懒。", box)
	var m: Dictionary = st.month()
	var era := PackedStringArray()
	if Schedule.truthy(m.get("board")):
		era.append("本月有选片板")
	if Schedule.truthy(m.get("annual")):
		era.append("本月有年度大事")
	if not era.is_empty():
		label("　" + "，".join(era), box)
	var opts := Schedule.options(st)
	var good: Array = Story.fit_plan(g, prev_plan) if prev_plan.size() == 3 else ["rest_home", "rest_home", "rest_home"]
	plan_btns = []
	for i in 3:
		var days := Schedule.days_of(st, i)
		var head: String = "%s（%d–%d 日）" % [["上旬", "中旬", "下旬"][i], days[0][0], days[days.size() - 1][0]]
		var f = g.hooks.locked(st, i)
		var ab: int = st.ym * 3 + i
		if st.forced_rest or st.void_next:
			label(head + "　" + ("重病后强制疗养" if st.forced_rest else "本月日程作废"), box)
			plan_btns.append(null)
			continue
		if st.void_periods.has(ab):
			label(head + "　被拘留（作废）", box)
			plan_btns.append(null)
			continue
		if f != null:
			label(head + "　拍摄中：" + str(f["roles"]["name"]), box)
			plan_btns.append(null)
			continue
		var hb := VBoxContainer.new()
		box.add_child(hb)
		label(head, hb)
		var ob := OptionButton.new()
		var sel := 0
		for k in opts.size():
			ob.add_item("%s（%s）" % [entry_name(opts[k]), entry_effect(opts[k])])
			ob.set_item_metadata(k, opts[k])
			if opts[k] == good[i]:
				sel = k
		ob.select(sel)
		ob.clip_text = true
		ob.custom_minimum_size = Vector2(300, 0)
		ob.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hb.add_child(ob)
		var full := label("　" + ob.get_item_text(sel), hb, Color(0.8, 0.9, 1))
		ob.item_selected.connect(func(ix): full.text = "　" + ob.get_item_text(ix))
		plan_btns.append(ob)
	var hb2 := HBoxContainer.new()
	box.add_child(hb2)
	label("生活方式（从下个月起扣）：", hb2)
	var lb := OptionButton.new()
	var li := 0
	var k := 0
	for lid in d.lifestyles:
		lb.add_item("%s（月费 $%d）" % [nm(lid), d.lifestyles[lid]["monthly_cost"][st.fame_tier()]])
		lb.set_item_metadata(k, lid)
		if lid == st.lifestyle:
			li = k
		k += 1
	lb.select(li)
	lb.item_selected.connect(func(idx): g.set_lifestyle(lb.get_item_metadata(idx)))
	hb2.add_child(lb)
	plan_info = label("", box, Color(1, 0.5, 0.5))
	button("开始本月", func(): _submit_plan(), box)


func _current_plan() -> Array:
	var plan := []
	for i in 3:
		var ob = plan_btns[i]
		plan.append(ob.get_item_metadata(ob.selected) if ob != null else "rest_home")
	return plan


func _submit_plan() -> void:
	var plan: Array = _current_plan()
	var errs: Array = g.plan_errors(plan)
	if not errs.is_empty():
		var t := PackedStringArray()
		for e in errs:
			t.append("第 %d 旬：%s" % [int(e[0]) + 1, str(e[1])])
		plan_info.text = "不能这样排：" + "；".join(t)
		return
	reply(plan)


# ---------- street ----------

func smsg(text: String) -> void:
	street_msg.text = text
	note(text)


func _act(result: String, ok_text: String) -> void:
	smsg(ok_text if result == "" else "没成功：" + why(result))
	_fill_street()
	refresh_status()


func _fill_street() -> void:
	for c in street_box.get_children():
		c.queue_free()
	var box := street_box
	street_msg = label("", box, Color(0.6, 1, 0.6))
	label("钱：$%d　（街道上的事不占日程）" % st.money, box)
	# stores
	for entry in ["clothing_store", "general_store", "bookstore"]:
		heading(nm(entry), box)
		for iid in Street.shelf(st, entry):
			var base: int = d.books[iid]["price"] if d.books.has(iid) else d.items[iid]["price"]
			var p := Street.price(st, entry, base)
			var eff: String = ("　" + pretty(d.items[iid]["effect"])) if d.items.has(iid) else ""
			var hb := HBoxContainer.new()
			box.add_child(hb)
			label("%s　$%d%s" % [nm(iid), p, eff], hb)
			var e: String = entry
			var ii: String = iid
			button("买", func(): _act(Street.buy(st, e, ii), "买了 " + nm(ii)), hb)
	# inventory
	heading("你的东西", box)
	var seen := {}
	for iid in st.items:
		if seen.has(iid):
			continue
		seen[iid] = true
		var it: Dictionary = d.items[iid]
		var hb := HBoxContainer.new()
		box.add_child(hb)
		var eq: bool = st.equip["outfit"] == iid or st.equip["accessory"].has(iid)
		label("%s ×%d%s　%s" % [nm(iid), st.items.count(iid), "（装备中）" if eq else "", pretty(it["effect"])], hb)
		var ii: String = iid
		if it.get("slot") == "outfit" or it.get("slot") == "accessory":
			if eq:
				button("卸下", func(): _act(Street.unequip(st, ii), "卸下 " + nm(ii)), hb)
			else:
				button("装备", func(): _act(Street.equip(st, ii), "装备 " + nm(ii)), hb)
		if it["class"] == "consumable":
			button("用", func(): _act(Street.use(st, ii), "用了 " + nm(ii)), hb)
		button("卖（$%d）" % (int(it["price"]) / 2), func(): _act(Street.sell(st, ii), "卖了 " + nm(ii)), hb)
	for bid in st.books:
		label("书：%s（还剩 %d 点）" % [nm(bid), int(st.books[bid])], box)
	for bid in st.read_books:
		var hb := HBoxContainer.new()
		box.add_child(hb)
		label("读过的书：%s" % nm(bid), hb)
		var bb: String = bid
		button("卖（$%d）" % (int(d.books[bid]["price"]) / 2), func(): _act(Street.sell(st, bb), "卖了 " + nm(bb)), hb)
	# services
	heading("餐厅（每月一次）", box)
	var hr := HBoxContainer.new()
	box.add_child(hr)
	for s in d.street["restaurant"]["services"]:
		var sid: String = s["id"]
		button("%s $%d　%s" % [nm(sid) if names.has(sid) else s["name"], Street.price(st, "restaurant", s["price"]), pretty(s["effect"])],
			func(): _act(Street.restaurant(st, sid), "吃了 " + sid), hr)
	heading("教堂 / 医院", box)
	var hc := HBoxContainer.new()
	box.add_child(hc)
	button("捐 100（犯罪 −10，每月一次）", func(): _act(Street.church(st), "捐了款"), hc)
	button("去医院（只有生病时；费用 = 生病指数×2）", func(): _act(Street.hospital(st), "看了病"), hc)
	heading("和 Sil 谈话", box)
	var hint := Street.sil_hint(st)
	label("近况：" + _hint_text(hint), box)
	button("让 Sil 劝一劝（失控时可用，每月一次）", func(): _act(Street.sil_persuade(st), "Sil 劝了你"), box)
	# scripts etc.
	heading("投稿剧本（下一块选片板多一个角色）", box)
	for kind in ["self_written", "duv_written", "co_written"]:
		if not Board.script_ok(st, kind):
			continue
		var hb := HBoxContainer.new()
		box.add_child(hb)
		label(KIND_NAME[kind], hb)
		var cb := OptionButton.new()
		for c in 4:
			cb.add_item("主色：" + nm(d.roads[c]))
		hb.add_child(cb)
		var kk: String = kind
		button("写", func(): _act(g.hooks.write_script(st, kk, cb.selected), "写了剧本"), hb)
	if st.drug >= 1:
		heading("戒毒", box)
		button("送去戒毒（月末发作）", func(): _act(g.hooks.send_detox(st), "送去戒毒"), box)
	if Schedule.truthy(st.flags.get("leak_news")):
		button("向报社放消息（每年一次，名气 +10%）", func(): _act(g.hooks.leak_news(st), "放了消息"), box)
	if int(st.flags.get("dealer_stock", 0)) > 0:
		heading("药贩（这个月在街上）", box)
		label("库存 %d 份，每份 $%d。手里有 %d 份。" % [int(st.flags["dealer_stock"]), int(st.flags["dealer_price"]), int(st.flags.get("drug_stock", 0))], box)
		button("买 1 份", func(): _act(g.hooks.buy_drug(st, 1), "买了 1 份"), box)


func _hint_text(h: Array) -> String:
	match h[0]:
		"sick":
			return str(h[1])
		"reckless":
			return "你最近太冲动了（失控指数 %s）" % str(h[1])
		"favor":
			return "%s 对你很有好感" % nm(h[1])
		"fatigue":
			return "你看起来很累（疲劳 %s）" % str(h[1])
	return "你最强的是 " + nm(h[1])


# ---------- status tab ----------

func _fill_status(box: VBoxContainer) -> void:
	var b: Dictionary = st.bonus()
	heading("技能", box)
	for r in d.roads:
		var t := PackedStringArray()
		for s in d.road_skills[r]:
			t.append("%s %d" % [nm(s), st.val(s, b)])
		label("%s路：声望 %d　（%s）" % [nm(r), st.rep(r, b), "　".join(t)], box)
	heading("人物（好感）", box)
	for n in st.known:
		label("%s　好感 %d" % [nm(n), st.favor.get(n, 0)], box)
	heading("片约", box)
	var any := false
	for f in st.story["films"]:
		if f["status"] == "to_shoot" or f["status"] == "shooting" or f["status"] == "wrapped":
			any = true
			label("%s [%s]　状态：%s　上映：%s" % [f["roles"]["name"], SIZE_NAME.get(f["size"], f["size"]), f["status"], str(f["release"])], box)
	if not any:
		label("没有在拍或待映的片子。", box)
	heading("已上映", box)
	for f in st.story["films"]:
		if f["status"] == "released":
			var r = f["result"]
			label("%s [%s]　%s" % [f["roles"]["name"], SIZE_NAME.get(f["size"], f["size"]), "大卖" if r != null and r.get("hit", false) else "已上映"], box)


# ================= month summary and ending =================

func _show_summary() -> void:
	refresh_status()
	clear_body()
	var now := snapshot()
	heading("%s 月结" % d.months[st.ym - 1]["month"] if st.ym > 0 else "月结")
	label("本月变化：" + diff_text(snap, now))
	var evs := new_events()
	if not evs.is_empty():
		heading("发生的事")
		for e in evs:
			label("　" + e)
	var rel := 0
	for f in st.story["films"]:
		if f["status"] == "released" and f["result"] != null and f["result"].get("month", -1) == st.ym - 1:
			rel += 1
			label("上映：%s（%s）　%s" % [f["roles"]["name"], SIZE_NAME.get(f["size"], f["size"]), "大卖" if f["result"].get("hit", false) else "—"])
	if st.finished:
		button("看结局", func(): reply(null))
	else:
		button("下个月", func(): reply(null))


func _show_ending() -> void:
	refresh_status()
	clear_body()
	var e: Dictionary = st.story["ending"]
	var nmid: String = nm(e["ending"])
	if e.get("top_job") != null:
		nmid = nmid.replace("{top_job}", nm(e["top_job"]))
	heading("结局：" + nmid)
	label("评级 %s　总分 %s" % [str(e.get("grade")), str(e.get("total", "-"))])
	label("类别：" + str(e.get("category")))
	if e.has("character"):
		label("人物档次：" + str(e["character"]))
	if e.has("destiny"):
		label("归宿：" + str(e["destiny"]))
	var content := ""
	for x in d.t["endings"].get("endings", []):
		if x["id"] == e["ending"]:
			content = str(x.get("content", ""))
	if content != "":
		label(content)
	button("再来一局", func():
		if thread != null:
			thread.wait_to_finish()
		_title())
	reply(null)
