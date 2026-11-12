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
const Fx = preload("res://ui/fx.gd")
const Assets = preload("res://ui/assets.gd")
const SaveSlots = preload("res://ui/save_slots.gd")
const Locale = preload("res://core/locale.gd")
const CgScene = preload("res://ui/cg_view.tscn")
const InventoryView = preload("res://ui/inventory_view.gd")
const ShopView = preload("res://ui/shop_view.gd")
const JournalView = preload("res://ui/journal_view.gd")
const EndingScene = preload("res://ui/ending_view.tscn")

## Which cue the effects node gets when a question is put on the screen (see ui/fx.gd and ui/README.md).
const KIND_CUE := {"pick_period": "map_open", "period": "period_report", "event": "event_dialog", "deck": "deck_open", "play": "round_open",
	"month_start": "month_start", "summary": "month_summary", "ending": "ending", "annual_result": "annual_result", "pick_role": "board_open"}

const SIZE_KEY := {"small": "ui.size.small", "medium": "ui.size.medium", "big": "ui.size.big"}
const KIND_KEY := {"self_written": "ui.script_kind.self_written", "duv_written": "ui.script_kind.duv_written", "co_written": "ui.script_kind.co_written"}

var d
var fx                     # fx.gd: sounds and effects, announced by cue()
var g                      # Month
var st
var thread: Thread
var sem := Semaphore.new()
var answer = null
var auto := false
var title_shot := ""
var shot_kind := "pick_period"
var shot_loc := ""
var shot_path := ""         # --shot=file.png: saves a picture of the first screen that waits for the player, then quits
var uitest := false         # --uitest: builds every screen for real, then presses the buttons itself
var auto_months := 9999
var quitting := false
var names := {}

var cur_plan: Array = ["rest_home", "rest_home", "rest_home"]   # filled one period at a time by the map
var month_forced := false
var cur_period_hint := 0
var snap := {}             # state at the start of the month (for the settlement summary)
var last_snap := {}        # state after the previous period (for the playback)
var ev_seen := 0           # how many records of story.event_log were already shown

# widgets
var status_label: Label
var body: VBoxContainer
var log_box: RichTextLabel
var street_box: VBoxContainer
var inv_box: VBoxContainer
var defer_events := false       # true while a period runs: its events are shown after the period report
var held_events: Array = []
var event_snaps: Array = []   # state at the start of each event being settled (events nest)
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
		elif a.begins_with("--shotloc="):
			shot_loc = a.substr(10)
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
	Locale.load_csv()
	Locale.load_csv(Locale.default_path().get_base_dir().path_join("ui.csv"))
	TranslationServer.set_locale("zh_CN")
	d = Data.new()
	if not d.ok:
		push_error("cannot read the data tables")
		get_tree().quit(1)
		return
	_index_names(d.t)
	_build_frame()
	fx = Fx.new()
	fx.host = body
	fx.enabled = shot_path == ""
	add_child(fx)
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


## What a book does, for the shop, the home menu and the inventory.
func book_text(bid: String) -> String:
	var b: Dictionary = d.books[bid]
	return tr("ui.main.book_text.1") % [
		nm(b["skills"]), rng_txt(b["gain"][0], b["gain"][1]), int(b["points"]), nm(b["skills"]), int(b["skill_cap"]),
		int(b["education_gate"]), st.val("education"), int(b.get("fatigue_per_day", 1))]


## Why an entry cannot be picked, in words the player can act on.
func block_reason(e: String, raw: String) -> String:
	var pe := Schedule.parse_entry(e)
	if not pe.is_empty() and pe[0] == "book" and raw == "education below the gate":
		return tr("ui.main.block_reason.1") % [int(d.books[pe[1]]["education_gate"]), st.val("education")]
	return why(raw)


func shop_title(entry: String) -> String:
	return tr("ui.main.shop_title.1") if entry == "pawn" else nm(entry)


func entry_name(e: String) -> String:
	if e == "act_hospital":
		return tr("ui.main.entry_name.6")
	if e == "act_script":
		return tr("ui.main.entry_name.7")
	var pe := Schedule.parse_entry(e)
	if pe.is_empty():
		return e
	var kind: String = pe[0]
	var s := nm(pe[1])
	if kind == "class":
		return tr("ui.main.entry_name.1") + s
	if kind == "book":
		return tr("ui.main.entry_name.2") + s
	if kind == "job":
		return tr("ui.main.entry_name.3") + s
	if pe[2] != null:
		return tr("ui.main.entry_name.4") + nm(pe[2]) + tr("ui.main.entry_name.5") % Schedule.place_cost(st, pe[2])
	return s




func size_name(size: String) -> String:
	return tr(SIZE_KEY.get(size, size))


func why(r: String) -> String:
	var key := "ui.reason." + r.replace(" ", "_")
	var text := tr(key)
	return r if text == key else text


func rival_name(o: Dictionary) -> String:
	var n := str(o.get("name", ""))
	return tr("ui.main.rival_name.1") if n == "" or n.begins_with("unnamed") else n


func rng_txt(a: int, b: int) -> String:
	if a == b:
		return "%+d" % a
	return "%+d~%+d" % [a, b]


## What one period of this entry does, in words and numbers (shown in brackets in the schedule menus).
func entry_effect(e: String) -> String:
	if e.begins_with("act_"):
		return ""
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
		t.append(tr("ui.main.entry_effect.1"))
		t.append(tr("ui.main.entry_effect.2") + " ".join(gs))
		t.append(tr("ui.main.entry_effect.3") % int(c.get("fatigue_per_day", 1)))
		t.append(tr("ui.main.entry_effect.4") % [int(c["fee"][lv - 1]), lv])
	elif kind == "book":
		var b: Dictionary = d.books[iid]
		t.append(tr("ui.main.entry_effect.1"))
		t.append(tr("ui.main.entry_effect.5") % [nm(b["skills"]), rng_txt(b["gain"][0], b["gain"][1])])
		t.append(tr("ui.main.entry_effect.3") % int(b.get("fatigue_per_day", 1)))
		if st.books.has(iid):
			t.append(tr("ui.main.entry_effect.6") % int(st.books[iid]))
	elif kind == "job":
		var j: Dictionary = d.jobs[iid]
		t.append(tr("ui.main.entry_effect.7") % Schedule.wage_of(st, iid))
		var gs := PackedStringArray()
		for x in j["daily_effect"]:
			gs.append(nm(x["stat"]) + rng_txt(x["add"][0], x["add"][1]))
		t.append(tr("ui.main.entry_effect.8") + " ".join(gs))
		var ls := PackedStringArray()
		for x in Schedule.job_lines(st, j):
			ls.append(tr("ui.main.entry_effect.9") % [nm(x[0]), str(x[1])])
		if not ls.is_empty():
			t.append(tr("ui.main.entry_effect.10") + tr("ui.main.entry_effect.11").join(ls))
	else:
		var r: Dictionary = d.rests[iid]
		if pe[2] != null:
			var pl: Dictionary = d.places[pe[2]]
			t.append(tr("ui.main.entry_effect.12") % [int(pl["fatigue_per_day"]), Schedule.place_cost(st, pe[2])])
		else:
			t.append(tr("ui.main.entry_effect.13") % [int(r["fatigue_per_day"]), pretty(r.get("period_effect", ""))])
	return tr("ui.main.entry_effect.14").join(t)


func clear_body() -> void:
	for c in body.get_children():
		c.queue_free()
	body.add_child(Control.new())   # keeps the container non-empty while the old children are freed
	if fx != null:
		fx.fade_in(body, 0.15)


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
		status_label.text = tr("ui.main.refresh_status.1")
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
		r.append(tr("ui.main.refresh_status.2") % [nm(k), st.rep(k, b), " ".join(sk)])
	var flags := PackedStringArray()
	if st.status["very_sick"]:
		flags.append(tr("ui.main.refresh_status.3"))
	elif st.status["sick"]:
		flags.append(tr("ui.main.refresh_status.4"))
	if st.status["reckless"]:
		flags.append(tr("ui.main.refresh_status.5"))
	if st.status["in_love"]:
		flags.append(tr("ui.main.refresh_status.6"))
	if st.status["long_contract"]:
		flags.append(tr("ui.main.refresh_status.7"))
	if st.drug > 0:
		flags.append(tr("ui.main.refresh_status.8"))
	var stock := int(st.flags.get("drug_stock", 0))
	if stock > 0:
		flags.append(tr("ui.main.refresh_status.9") % stock)
	status_label.text = tr("ui.main.refresh_status.10") % [
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
		out.append(tr("ui.main.diff_text.1") % (b["money"] - a["money"]))
	for grp in ["attr", "skill", "rep"]:
		for k in b[grp]:
			if k == "fame":
				continue
			if a[grp][k] != b[grp][k]:
				out.append("%s %+d" % [nm(k), b[grp][k] - a[grp][k]])
	return tr("ui.main.entry_effect.11").join(out) if not out.is_empty() else tr("ui.main.diff_text.2")


func diff_lines(a: Dictionary, b: Dictionary) -> PackedStringArray:
	var out := PackedStringArray()
	if a["money"] != b["money"]:
		out.append(tr("ui.main.diff_lines.1") % [a["money"], b["money"], b["money"] - a["money"]])
	for grp in ["attr", "skill"]:
		for k in b[grp]:
			if k == "fame":
				continue
			if a[grp][k] != b[grp][k]:
				out.append(tr("ui.main.diff_lines.2") % [nm(k), a[grp][k], b[grp][k], b[grp][k] - a[grp][k]])
	for k in b["rep"]:
		if a["rep"][k] != b["rep"][k]:
			out.append(tr("ui.main.diff_lines.3") % [nm(k), a["rep"][k], b["rep"][k], b["rep"][k] - a["rep"][k]])
	return out


func new_events() -> PackedStringArray:
	var out := PackedStringArray()
	var lg: Array = g.hooks.event_log
	while ev_seen < lg.size():
		var rec: Dictionary = lg[ev_seen]
		var s: String = nm(rec["id"])
		if rec.has("options") and rec["options"] != null:
			var ev: Dictionary = d.events[rec["id"]]
			s += tr("ui.main.new_events.1") + str(ev["options"][rec["options"]]["text"]) + tr("ui.board.show_board.13")
		if rec.has("check") and rec["check"] != null:
			s += tr("ui.main.new_events.2") + (tr("ui.main.new_events.3") if rec["check"] else tr("ui.main.new_events.4")) + tr("ui.board.show_board.13")
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
		t.append(tr("ui.main.update_alloc_info.1") % [tr("ui.main.update_alloc_info.2") if pool == POOL_ATTRS else tr("ui.main.update_alloc_info.3"), left, "" if left != 0 else tr("ui.main.update_alloc_info.4")])
		if left != 0:
			okk = false
	alloc_info.text = tr("ui.common.wide_space").join(t) + tr("ui.main.update_alloc_info.5")
	if start_btn != null:
		start_btn.disabled = not okk


func _title() -> void:
	st = null
	refresh_status()
	clear_body()
	heading(tr("ui.main.refresh_status.1"))
	label(tr("ui.main.title.1"))
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
	heading(tr("ui.main.title.2"))
	label(tr("ui.main.title.3"))
	var hb0 := HBoxContainer.new()
	body.add_child(hb0)
	button(tr("ui.main.title.4"), func(): _roll(), hb0)
	button(tr("ui.main.title.5"), func():
		alloc = base_vals.duplicate()
		_rebuild_alloc(), hb0)
	alloc_box = VBoxContainer.new()
	body.add_child(alloc_box)
	alloc_info = label("", null, Color(1, 0.85, 0.4))
	_read_origin()
	_rebuild_alloc()
	var hb := HBoxContainer.new()
	body.add_child(hb)
	label(tr("ui.main.title.6"), hb)
	var seed_edit := LineEdit.new()
	seed_edit.custom_minimum_size = Vector2(160, 0)
	hb.add_child(seed_edit)
	start_btn = button(tr("ui.main.title.7"), func():
		var o := []
		for p in origin_picks:
			o.append(p.selected)
		var sd: int = int(seed_edit.text) if seed_edit.text.strip_edges() != "" else randi() % 1000000 + 1
		_start_game(sd, o, alloc))
	for slot in SaveSlots.SLOTS:
		if SaveSlots.exists(slot):
			var meta: Dictionary = SaveSlots.read(slot).get("meta", {})
			var sl: String = slot
			button(tr("ui.main.title.8") % [slot_name(slot), str(meta.get("date", "?")), str(meta.get("money", "?"))], func(): _continue_game(sl))
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
	_run_thread()


func save_meta() -> Dictionary:
	return {"date": st.date(), "money": st.money}


func slot_name(slot: String) -> String:
	return tr("ui.main.slot_name.1") if slot == "auto" else tr("ui.main.slot_name.2") + slot


func save_slot(slot: String) -> void:
	var text: String = g.save()
	if text != "" and SaveSlots.write(slot, text, save_meta()):
		fx.cue("save", {"slot": slot})
		note(tr("ui.main.save_slot.1") + slot_name(slot))


func _continue_game(slot: String) -> void:
	var rec := SaveSlots.read(slot)
	var agent = UiStory.UiAgent.new(self)
	var story = UiStory.new(agent, self)
	var m = Month.restore(str(rec.get("save", "")), d, story)
	if m == null:
		_log(tr("ui.main.continue_game.1"))
		return
	fx.cue("load", {"slot": slot})
	g = m
	st = g.st
	_run_thread()


func _run_thread() -> void:
	ev_seen = 0
	clear_body()
	note(tr("ui.main.run_thread.1"))
	thread = Thread.new()
	thread.start(_worker)


# ================= the game thread =================

func _worker() -> void:
	var months := 0
	while not st.finished and not quitting and months < auto_months:
		g.start_month()
		last_snap = snapshot()
		snap = last_snap
		ev_seen = g.hooks.event_log.size()
		ask("month_start", null)
		if quitting:
			return
		last_snap = snapshot()      # the street is over: the period reports count from here
		month_forced = st.forced_rest != 0
		cur_plan = ["rest_home", "rest_home", "rest_home"]
		var errs: Array = g.run_month(cur_plan)
		if not errs.is_empty():
			push_error("run_month refused the plan: " + str(errs))
			return
		months += 1
		if not st.finished:
			var s: String = g.save()
			SaveSlots.write("auto", s, save_meta())
		ask("summary", null)
	if st.finished:
		ask("ending", null)
	if auto or uitest:
		call_deferred("_auto_done")


func _auto_done() -> void:
	thread.wait_to_finish()
	print("auto run finished: %s, %d fired events, ending %s, hospital periods %d" % [st.date(), st.fired.size(), str(st.ended), st.cnt("count.period.act_hospital")])
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


## Called by UiStory (game thread) after each period has been settled: CG placeholder, a short report, every stat that changed.
func period_done(_st, i: int, entry: String, out: Dictionary) -> void:
	defer_events = false
	var now := snapshot()
	var evs := new_events()
	var days := Schedule.days_of(st, i)
	var span := tr("ui.main.period_done.1") % [days[0][0], days[days.size() - 1][0]]
	var head: String = tr("ui.main.period_done.2") % [st.date(), [tr("ui.period.early"), tr("ui.period.mid"), tr("ui.period.late")][i], span]
	var what := ""
	var cg := ""
	var cg_keys: Array = Assets.entry_keys(entry, str(out.get("size", "")))
	var rep := PackedStringArray()
	if entry == "shooting":
		what = tr("ui.main.period_done.3") % str(out.get("film", ""))
		cg = tr("ui.main.period_done.4")
		rep.append(tr("ui.main.period_done.5") % [int(out.get("days", 0)), int(out.get("ok", 0))])
	else:
		what = entry_name(entry)
		var pe := Schedule.parse_entry(entry)
		cg = what
		if out.has("class_days"):
			rep.append(tr("ui.main.period_done.6") % [int(out["class_days"]), int(out["ok_days"])])
		elif out.has("work_days"):
			rep.append(tr("ui.main.period_done.7") % [int(out["work_days"]), int(out["ok_days"]), int(out["pay"])])
		elif out.has("ok_days"):
			rep.append(tr("ui.main.period_done.8") % int(out["ok_days"]))
		elif out.get("act") == "act_hospital":
			rep.append(tr("ui.main.period_done.12"))
		elif out.get("act") == "act_script":
			rep.append(tr("ui.main.period_done.13"))
		elif out.has("cost"):
			rep.append(tr("ui.main.period_done.9") % int(out["cost"]))
		elif pe.size() > 0 and pe[0] == "rest":
			rep.append(tr("ui.main.period_done.10"))
	var lines := diff_lines(last_snap, now)
	var evt := PackedStringArray()
	for e in evs:
		evt.append(e)
	last_snap = now
	note(tr("ui.main.period_done.11") % [head, what, diff_text(last_snap, now) if false else tr("ui.main.entry_effect.14").join(rep)])
	ask("period", {"head": head, "what": what, "cg": cg, "cg_keys": cg_keys, "report": "\n".join(rep), "lines": lines, "events": evt})
	var held := held_events
	held_events = []
	for p in held:      # the events of this period, after its report
		ask("event", p)


func ac() -> Dictionary:
	return d.t["habits"]["audition"]


func rules_text() -> String:
	var c := ac()
	var order: Array = c["color_order"]
	var ring := []
	for n in order:
		ring.append(tr("ui.main.rules_text.1") % [nm(n), nm(c["counters"][n])])
	return tr("ui.main.rules_text.2") % [
		int(c["style_pct"]), int(c["counter_pct"]), int(c["countered_pct"]), tr("ui.board.show_board.15").join(ring), int(c["rounds_to_win"])]


## One card's value with the reason, e.g. "硬汉 3 → 300 ×130%（场风）= 390"
func card_text(card: Array, other: Array, field: int) -> String:
	var v: Array = Audition.effective(d, card, other, field)
	var base: int = card[1] * 100
	var why := []
	if card[0] == field:
		why.append(tr("ui.main.card_text.1") % int(ac()["style_pct"]))
	var bt := Audition.beats(d)
	if card[0] != field and other[0] != field:
		if bt[card[0]] == other[0]:
			why.append(tr("ui.main.card_text.2") % int(ac()["counter_pct"]))
		elif bt[other[0]] == card[0]:
			why.append(tr("ui.main.card_text.3") % int(ac()["countered_pct"]))
	return tr("ui.main.card_text.4") % [nm(d.roads[card[0]]), card[1], base, (tr("ui.ending.build.8") + tr("ui.main.entry_effect.11").join(why) + tr("ui.board.show_board.13")) if not why.is_empty() else "", v[0]]


func audition_text(role: Dictionary, res: Dictionary) -> String:
	var t := PackedStringArray()
	t.append(tr("ui.main.audition_text.1") % [role["name"], size_name(role["size"])])
	var k := 1
	for m in res["rounds"]:
		t.append(tr("ui.main.audition_text.2") % [k, m["score_line"][0], m["score_line"][1]])
		k += 1
	var r: String = res["result"]
	var verdict := ""
	match r:
		"won":
			verdict = tr("ui.main.audition_text.3") + (tr("ui.main.audition_text.4") if res.get("remembered", false) else "") + tr("ui.main.audition_text.5")
		"narrow_loss":
			if res.get("support", false):
				verdict = tr("ui.main.audition_text.6")
			else:
				verdict = tr("ui.main.audition_text.7")
		"botched":
			verdict = tr("ui.main.audition_text.8") + (tr("ui.main.audition_text.9") if res.get("reported", false) else tr("ui.main.audition_text.10"))
		_:
			verdict = tr("ui.main.audition_text.11")
	t.append(verdict)
	return "\n".join(t)


# ================= automatic answers (test mode) =================

func _auto_pick() -> String:
	var rng := RandomNumberGenerator.new()
	rng.seed = st.ym * 3 + cur_period_hint + 1
	var ok := []
	for e in Schedule.options(st):
		if Schedule.validate(st, e) == "":
			ok.append(e)
	return ok[rng.randi() % ok.size()]


func _auto_answer(kind: String, payload):
	match kind:
		"month_start":
			return null
		"pick_period":
			return _auto_pick()
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
	fx.cue(KIND_CUE.get(kind, kind), {"kind": kind})
	match kind:
		"month_start": _show_month_start()
		"pick_period": _show_map(int(payload))
		"pick_role": _show_board(payload)
		"deck": _show_deck(payload)
		"play": _show_play(payload)
		"support": _yes_no(tr("ui.main.show_request.1"), tr("ui.main.show_request.2"), payload["name"])
		"stunt": _yes_no(tr("ui.main.show_request.3"), tr("ui.main.show_request.4"), payload["name"])
		"suppress": _yes_no(tr("ui.main.show_request.5"), tr("ui.main.show_request.6") + (tr("ui.main.show_request.7") if payload == "free" else tr("ui.main.show_request.8")), "")
		"boost": _yes_no(tr("ui.main.show_request.9"), tr("ui.main.show_request.10") % int(st.flags.get("drug_stock", 0)), "")
		"option": _show_option(payload)
		"annual": _show_annual(payload)
		"family": _show_family()
		"period": _show_period(payload)
		"notice": _show_notice(payload)
		"event": _show_event(payload)
		"annual_result": _show_annual_result(payload)
		"summary": _show_summary()
		"ending": _show_ending()
		_:
			push_error("unknown question %s" % kind)
			reply(null)
	if uitest:
		await get_tree().process_frame
		if shot_path != "" and (kind == shot_kind):
			if shot_loc == "reveal":
				var bs: Array = []
				_collect_buttons(body, bs)
				bs[0].pressed.emit()
			elif shot_loc != "":
				_show_location(int(payload), shot_loc)
			for _i in 3:
				await get_tree().process_frame
			get_viewport().get_texture().get_image().save_png(shot_path)
			get_tree().quit()
			return
		_uitest_answer(kind, payload)


## --uitest: press every button of the street once, then answer the question as the automatic player would.
func _uitest_answer(kind: String, payload) -> void:
	if kind == "month_start" and st.ym < 3:
		var btns: Array = []
		_collect_buttons(street_box, btns)
		for b in btns:
			if is_instance_valid(b) and b.get_parent() != null:
				b.pressed.emit()
	if kind == "pick_period" and st.ym < 3:
		for loc in ["home", "school", "work", "city", "boat"]:
			_show_location(int(payload), loc)
			await get_tree().process_frame
		for shop in ["clothing_store", "general_store", "bookstore", "pawn", "restaurant", "church"]:
			_show_shop(int(payload), shop)
			await get_tree().process_frame
		_show_inventory(int(payload))
		await get_tree().process_frame
		if st.ym == 2 and int(payload) == 0:      # the hospital visit: make him sick on purpose and press the last button of the city menu
			st.idx["sick_index"] = 30
			st.status["sick"] = 1
			_show_location(int(payload), "city")
			await get_tree().process_frame
			var hb: Array = []
			_collect_buttons(body, hb)
			hb[hb.size() - 1].pressed.emit()
			return
		_show_map(int(payload))
	if kind == "play" or kind == "deck":      # press the real buttons: the first card, then "next" / "confirm the deck"
		var bs: Array = []
		_collect_buttons(body, bs)
		if kind == "play":
			bs[0].pressed.emit()
			await get_tree().process_frame
			bs = []
			_collect_buttons(body, bs)
		bs[bs.size() - 1].pressed.emit()
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
	button(tr("ui.main.yes_no.1"), func(): reply(true), hb)
	button(tr("ui.main.yes_no.2"), func(): reply(false), hb)


func _show_option(p: Dictionary) -> void:
	var ev: Dictionary = p["event"]
	_wait_screen(tr("ui.main.show_option.1") + str(ev["name"]))
	if ev.get("body") != null:
		label(str(ev["body"]))
	label(tr("ui.main.show_option.2"))
	for k in p["avail"]:
		var o: Dictionary = ev["options"][k]
		var t: String = str(o["text"])
		if Schedule.truthy(o.get("check")):
			t += tr("ui.main.show_option.3")
		var kk: int = k
		button(t, func(): reply(kk))


func _show_notice(payload) -> void:
	var text: String = payload["text"] if payload is Dictionary else str(payload)
	if payload is Dictionary and payload.has("cue"):
		fx.cue(payload["cue"], payload)
	_wait_screen(tr("ui.main.show_notice.1"))
	label(text)
	button(tr("ui.main.show_notice.2"), func(): reply(null))


## Called by UiStory (game thread) around every event the core settles.
func event_started(_eid: String) -> void:
	event_snaps.append(snapshot())


func event_ended(rec: Dictionary) -> void:
	var before: Dictionary = event_snaps.pop_back() if not event_snaps.is_empty() else snapshot()
	var ev: Dictionary = d.events[rec["id"]]
	var picked := ""
	if rec.get("options") != null:
		picked = str(ev["options"][rec["options"]]["text"])
	var check := ""
	if rec.get("check") != null:
		check = tr("ui.main.new_events.3") if rec["check"] else tr("ui.main.new_events.4")
	var payload := {"id": rec["id"], "name": str(ev["name"]), "class": str(ev.get("class", "")), "body": ev.get("body"),
		"picked": picked, "check": check, "lines": diff_lines(before, snapshot())}
	if defer_events:
		held_events.append(payload)
	else:
		ask("event", payload)


func _show_event(p: Dictionary) -> void:
	clear_body()
	heading(str(p["name"]))
	add_cg("cg", ["event/" + str(p["id"]), "event_class/" + str(p["class"])], str(p["name"]))
	if p["body"] != null:
		label(str(p["body"]))
	if str(p["picked"]) != "":
		label(tr("ui.main.show_event.1") + str(p["picked"]))
	if str(p["check"]) != "":
		label(tr("ui.main.show_event.2") + str(p["check"]))
	if p["lines"].is_empty():
		label(tr("ui.main.show_event.3"))
	else:
		for x in p["lines"]:
			label(tr("ui.common.wide_space") + x)
	button(tr("ui.main.show_notice.2"), func(): reply(null))


func _show_annual_result(rec: Dictionary) -> void:
	clear_body()
	heading(tr("ui.main.show_annual_result.1"))
	if rec["occasions"] == null:
		label(tr("ui.main.show_annual_result.2"))
	else:
		label(tr("ui.main.show_annual_result.3") + nm(rec["occasions"]))
		label(tr("ui.main.show_annual_result.4") % int(rec["rank"]))
		for rw in d.t["annual"]["ranking"]["rewards"]:
			if rw["rank"] == rec["rank"]:
				label(tr("ui.main.show_annual_result.5") % [int(rw["rep_bonus"]), int(rw["prize"])])
	button(tr("ui.main.show_notice.2"), func(): reply(null))


func _show_annual(opts: Array) -> void:
	_wait_screen(tr("ui.main.show_annual_result.1"))
	label(tr("ui.main.show_annual.1"))
	for x in opts:
		var id: String = x["id"]
		button(tr("ui.main.show_annual.2") % [nm(id), nm(x["road"]), st.rep(x["road"])], func(): reply(id))
	button(tr("ui.main.show_annual.3"), func(): reply(null))


func _show_family() -> void:
	_wait_screen(tr("ui.main.show_family.1"))
	label(tr("ui.main.show_family.2"))
	for k in d.tag_families:
		var kk: String = k
		button(nm(k), func(): reply(kk))


func add_cg(kind: String, keys: Array, caption: String) -> void:
	var cg = CgScene.instantiate()
	body.add_child(cg)
	cg.show_cg(kind, keys, caption)


func _show_period(p: Dictionary) -> void:
	clear_body()
	heading(str(p["head"]) + tr("ui.main.show_period.1") + str(p["what"]))
	add_cg("cg", p["cg_keys"], str(p["cg"]))
	if str(p["report"]) != "":
		label(str(p["report"]))
	if p["lines"].is_empty():
		label(tr("ui.main.show_event.3"))
	else:
		label(tr("ui.main.show_period.2"))
		for x in p["lines"]:
			label(tr("ui.common.wide_space") + x)
	for e in p["events"]:
		label(tr("ui.main.show_option.1") + e, null, Color(1, 0.85, 0.4))
	button(tr("ui.main.show_notice.2"), func(): reply("ok"))


# ---------- the board and auditions ----------

func _show_board(p: Dictionary) -> void:
	clear_body()
	var v = preload("res://ui/board.tscn").instantiate()
	body.add_child(v)
	v.picked.connect(func(i): reply(i))
	v.show_board(self, p)


func _show_deck(ctx: Dictionary) -> void:
	clear_body()
	var v = preload("res://ui/audition.tscn").instantiate()
	body.add_child(v)
	v.deck_done.connect(func(cols): reply(cols))
	v.show_deck(self, ctx)


func _show_play(ctx: Dictionary) -> void:
	clear_body()
	var v = preload("res://ui/audition.tscn").instantiate()
	body.add_child(v)
	v.play_done.connect(func(i): reply(i))
	v.show_play(self, ctx)


# ================= the month: street first, then the map, one period at a time =================

func _show_month_start() -> void:
	clear_body()
	heading(tr("ui.main.show_month_start.1") % st.date())
	var m: Dictionary = st.month()
	var era := PackedStringArray()
	if Schedule.truthy(m.get("board")):
		era.append(tr("ui.main.show_month_start.2"))
	if Schedule.truthy(m.get("annual")):
		era.append(tr("ui.main.show_month_start.3"))
	if st.forced_rest:
		era.append(tr("ui.main.show_month_start.4"))
	if st.void_next:
		era.append(tr("ui.main.show_month_start.5"))
	if not era.is_empty():
		label(tr("ui.common.wide_space") + tr("ui.main.entry_effect.11").join(era))
	label(tr("ui.main.show_month_start.6"))
	var hb2 := HBoxContainer.new()
	body.add_child(hb2)
	label(tr("ui.main.show_month_start.7"), hb2)
	var lb := OptionButton.new()
	var li := 0
	var k := 0
	for lid in d.lifestyles:
		lb.add_item(tr("ui.main.show_month_start.8") % [nm(lid), d.lifestyles[lid]["monthly_cost"][st.fame_tier()]])
		lb.set_item_metadata(k, lid)
		if lid == st.lifestyle:
			li = k
		k += 1
	lb.select(li)
	lb.item_selected.connect(func(idx): g.set_lifestyle(lb.get_item_metadata(idx)))
	hb2.add_child(lb)
	button(tr("ui.main.show_month_start.9"), func(): reply(null))
	var tabs := TabContainer.new()
	tabs.custom_minimum_size = Vector2(0, 520)
	body.add_child(tabs)
	var t2 := ScrollContainer.new()
	t2.name = tr("ui.main.show_month_start.10")
	t2.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs.add_child(t2)
	street_box = VBoxContainer.new()
	street_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t2.add_child(street_box)
	var t_inv := ScrollContainer.new()
	t_inv.name = tr("ui.main.show_month_start.11")
	t_inv.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs.add_child(t_inv)
	inv_box = VBoxContainer.new()
	inv_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t_inv.add_child(inv_box)
	var t_j := ScrollContainer.new()
	t_j.name = tr("ui.journal.build.1")
	t_j.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs.add_child(t_j)
	var jv := JournalView.new()
	jv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t_j.add_child(jv)
	jv.build(self)
	var t3 := ScrollContainer.new()
	t3.name = tr("ui.main.show_month_start.12")
	t3.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	tabs.add_child(t3)
	var sbox := VBoxContainer.new()
	sbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	t3.add_child(sbox)
	_fill_street()
	_fill_status(sbox)


## The places on the map: id -> [name, position, size, hint]. A place groups several schedule entries.
const LOCATIONS := {
	"home": ["ui.loc.home.name", Vector2(40, 40), Vector2(200, 90), "ui.loc.home.hint"],
	"school": ["ui.loc.school.name", Vector2(330, 30), Vector2(240, 90), "ui.loc.school.hint"],
	"work": ["ui.loc.work.name", Vector2(650, 60), Vector2(200, 90), "ui.loc.work.hint"],
	"city": ["ui.loc.city.name", Vector2(90, 220), Vector2(240, 90), "ui.loc.city.hint"],
	"boat": ["ui.loc.boat.name", Vector2(500, 240), Vector2(280, 90), "ui.loc.boat.hint"],
}


func loc_entries(loc: String) -> Array:
	var out := []
	match loc:
		"home":
			out.append("rest_home")
			for b in st.books:
				out.append(b)
			if d.classes.has("class_tutor"):
				out.append("class_tutor")
		"school":
			for c in d.classes:
				if c != "class_tutor":
					out.append(c)
		"work":
			for j in d.jobs:
				out.append(j)
		"city":
			for p in d.places:
				if p != "place_resort":
					out.append("rest_outing@" + p)
		"boat":
			out.append("rest_outing@place_resort")
	return out


func _show_map(i: int) -> void:
	cur_period_hint = i
	clear_body()
	var days := Schedule.days_of(st, i)
	heading(tr("ui.main.show_map.1") % [st.date(), [tr("ui.period.early"), tr("ui.period.mid"), tr("ui.period.late")][i], days[0][0], days[days.size() - 1][0]])
	label(tr("ui.main.show_map.2"))
	var map := Control.new()
	map.custom_minimum_size = Vector2(900, 380)
	body.add_child(map)
	var bg := ColorRect.new()
	bg.color = Color(0.16, 0.26, 0.2)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	map.add_child(bg)
	for loc in LOCATIONS:
		var info: Array = LOCATIONS[loc]
		var b := Button.new()
		b.text = "%s\n%s" % [tr(info[0]), tr(info[3])]
		b.position = info[1]
		b.size = info[2]
		var ll: String = loc
		b.pressed.connect(func(): _show_location(i, ll))
		map.add_child(b)
	button(tr("ui.main.show_map.3"), func(): _show_inventory(i))


func _show_location(i: int, loc: String) -> void:
	fx.cue("location_open", {"location": loc})
	clear_body()
	var info: Array = LOCATIONS[loc]
	heading(tr("ui.main.show_location.1") % [st.date(), [tr("ui.period.early"), tr("ui.period.mid"), tr("ui.period.late")][i], tr(info[0])])
	button(tr("ui.main.show_location.2"), func(): _show_map(i))
	var any := false
	for e in loc_entries(loc):
		var why_not: String = Schedule.validate(st, e)
		var txt := tr("ui.main.show_location.3") % [entry_name(e), entry_effect(e)]
		if why_not == "":
			any = true
			var ee: String = e
			button(tr("ui.main.show_location.4") + entry_name(e), func(): reply(ee))
			label(tr("ui.main.show_location.5") + entry_effect(e), null, Color(0.8, 0.9, 1))
		elif loc != "work" or not why_not.begins_with("not unlocked"):
			label(tr("ui.main.show_location.6") % [entry_name(e), block_reason(e, why_not)], null, Color(1, 0.7, 0.7))
	if loc == "city":
		_city_extras(i)
	elif loc == "home":
		_home_extras()
	elif not any:
		label(tr("ui.main.show_location.7"))


## The things of the city that do not use a period (shops, pawn shop, restaurant, church) and the hospital, which does.
func _city_extras(i: int) -> void:
	heading(tr("ui.main.city_extras.1"))
	for shop in ["clothing_store", "general_store", "bookstore", "pawn", "restaurant", "church"]:
		var sh: String = shop
		button(shop_title(shop), func(): _show_shop(i, sh))
	heading(tr("ui.main.city_extras.2"))
	var can: String = Street.hospital_check(st)
	if can == "":
		var idx: int = st.idx["sick_index"]
		var price: int = Street.price(st, "hospital", idx * 2)
		button(tr("ui.main.city_extras.3") % [price, idx + 1], func():
			var r: String = Street.hospital(st)
			if r == "":
				note(tr("ui.main.city_extras.4"))
				reply("act_hospital")
			else:
				label(tr("ui.main.act.1") + why(r), null, Color(1, 0.7, 0.7)))
	else:
		label(tr("ui.main.city_extras.5") + why(can), null, Color(0.6, 0.6, 0.6))


## Writing a script uses a period at home; it is offered when the script rules allow it.
func _home_extras() -> void:
	heading(tr("ui.main.home_extras.1"))
	label(tr("ui.main.home_extras.2"))
	var any := false
	for kind in ["self_written", "duv_written", "co_written"]:
		if not Board.script_ok(st, kind):
			continue
		any = true
		var hb := HBoxContainer.new()
		body.add_child(hb)
		label(tr(KIND_KEY[kind]), hb)
		var cb := OptionButton.new()
		for c in 4:
			cb.add_item(tr("ui.main.fill_street.18") + nm(d.roads[c]))
		hb.add_child(cb)
		var kk: String = kind
		button(tr("ui.main.home_extras.3"), func():
			var r: String = g.hooks.write_script(st, kk, cb.selected)
			if r == "":
				note(tr("ui.main.home_extras.4"))
				reply("act_script")
			else:
				label(tr("ui.main.act.1") + why(r), null, Color(1, 0.7, 0.7)), hb)
	if not any:
		label(tr("ui.main.home_extras.5"), null, Color(0.6, 0.6, 0.6))


func _show_shop(i: int, entry: String) -> void:
	clear_body()
	var v = ShopView.new()
	body.add_child(v)
	v.show_entry(self, entry, func(): _show_location(i, "city"))


func _show_inventory(i: int) -> void:
	clear_body()
	button(tr("ui.main.show_location.2"), func(): _show_map(i))
	var box := VBoxContainer.new()
	body.add_child(box)
	var rebuild := func(): _show_inventory(i)
	var v := InventoryView.new()
	box.add_child(v)
	v.build(self, rebuild)


# ---------- street ----------

func smsg(text: String) -> void:
	street_msg.text = text
	note(text)


## Tells the player (message line and log) how a free action went; returns true when it worked.
func report(result: String, ok_text: String) -> bool:
	var text: String = ok_text if result == "" else tr("ui.main.act.1") + why(result)
	if street_msg != null and is_instance_valid(street_msg):
		street_msg.text = text
	note(text)
	return result == ""


func act(result: String, ok_text: String) -> void:
	smsg(ok_text if result == "" else tr("ui.main.act.1") + why(result))
	_fill_street()
	refresh_status()


func _fill_inventory() -> void:
	if inv_box == null:
		return
	for c in inv_box.get_children():
		c.queue_free()
	var v := InventoryView.new()
	inv_box.add_child(v)
	v.build(self, Callable(self, "_fill_street"))


func _fill_street() -> void:
	_fill_inventory()
	for c in street_box.get_children():
		c.queue_free()
	var box := street_box
	street_msg = label("", box, Color(0.6, 1, 0.6))
	label(tr("ui.main.fill_street.1") % st.money, box)
	heading(tr("ui.main.fill_street.13"), box)
	var hint := Street.sil_hint(st)
	label(tr("ui.main.fill_street.14") + _hint_text(hint), box)
	button(tr("ui.main.fill_street.15"), func(): act(Street.sil_persuade(st), tr("ui.main.fill_street.16")), box)
	if st.drug >= 1:
		heading(tr("ui.main.fill_street.21"), box)
		button(tr("ui.main.fill_street.22"), func(): act(g.hooks.send_detox(st), tr("ui.main.fill_street.23")), box)
	if Schedule.truthy(st.flags.get("leak_news")):
		button(tr("ui.main.fill_street.24"), func(): act(g.hooks.leak_news(st), tr("ui.main.fill_street.25")), box)
	if int(st.flags.get("dealer_stock", 0)) > 0:
		heading(tr("ui.main.fill_street.26"), box)
		label(tr("ui.main.fill_street.27") % [int(st.flags["dealer_stock"]), int(st.flags["dealer_price"]), int(st.flags.get("drug_stock", 0))], box)
		button(tr("ui.main.fill_street.28"), func(): act(g.hooks.buy_drug(st, 1), tr("ui.main.fill_street.29")), box)


func _hint_text(h: Array) -> String:
	match h[0]:
		"sick":
			return str(h[1])
		"reckless":
			return tr("ui.main.hint_text.1") % str(h[1])
		"favor":
			return tr("ui.main.hint_text.2") % nm(h[1])
		"fatigue":
			return tr("ui.main.hint_text.3") % str(h[1])
	return tr("ui.main.hint_text.4") + nm(h[1])


# ---------- status tab ----------

func _fill_status(box: VBoxContainer) -> void:
	var b: Dictionary = st.bonus()
	heading(tr("ui.main.update_alloc_info.3"), box)
	for r in d.roads:
		var t := PackedStringArray()
		for s in d.road_skills[r]:
			t.append("%s %d" % [nm(s), st.val(s, b)])
		label(tr("ui.main.fill_status.1") % [nm(r), st.rep(r, b), tr("ui.common.wide_space").join(t)], box)
	heading(tr("ui.main.fill_status.2"), box)
	for n in st.known:
		label(tr("ui.main.fill_status.3") % [nm(n), st.favor.get(n, 0)], box)
	heading(tr("ui.main.fill_status.4"), box)
	var any := false
	for f in st.story["films"]:
		if f["status"] == "to_shoot" or f["status"] == "shooting" or f["status"] == "wrapped":
			any = true
			label(tr("ui.main.fill_status.5") % [f["roles"]["name"], size_name(f["size"]), f["status"], str(f["release"])], box)
	if not any:
		label(tr("ui.main.fill_status.6"), box)
	heading(tr("ui.main.fill_status.7"), box)
	for f in st.story["films"]:
		if f["status"] == "released":
			var r = f["result"]
			label(tr("ui.main.fill_status.8") % [f["roles"]["name"], size_name(f["size"]), tr("ui.main.fill_status.9") if r != null and r.get("hit", false) else tr("ui.main.fill_status.7")], box)


# ================= month summary and ending =================

func _show_summary() -> void:
	refresh_status()
	clear_body()
	var now := snapshot()
	heading(tr("ui.main.show_summary.1") % d.months[st.ym - 1]["month"] if st.ym > 0 else tr("ui.main.show_summary.2"))
	label(tr("ui.main.show_summary.3") + diff_text(snap, now))
	var evs := new_events()
	if not evs.is_empty():
		heading(tr("ui.main.show_summary.4"))
		for e in evs:
			label(tr("ui.common.wide_space") + e)
	var rel := 0
	for f in st.story["films"]:
		if f["status"] == "released" and f["result"] != null and f["result"].get("month", -1) == st.ym - 1:
			rel += 1
			label(tr("ui.main.show_summary.5") % [f["roles"]["name"], size_name(f["size"]), tr("ui.main.fill_status.9") if f["result"].get("hit", false) else tr("ui.main.show_summary.6")])
	if st.finished:
		button(tr("ui.main.show_summary.7"), func(): reply(null))
	else:
		var hs := HBoxContainer.new()
		body.add_child(hs)
		label(tr("ui.main.show_summary.8"), hs)
		for slot in ["1", "2", "3"]:
			var sl: String = slot
			button(slot_name(slot), func(): save_slot(sl), hs)
		button(tr("ui.main.show_summary.9"), func(): reply(null))


func _show_ending() -> void:
	refresh_status()
	clear_body()
	var v = EndingScene.instantiate()
	body.add_child(v)
	v.build(self)
	var back := func():
		if thread != null:
			thread.wait_to_finish()
		_title()
	v.again.connect(back)
	v.quit_to_title.connect(back)
	if shot_path == "":      # the worker thread may finish now; with --shot the picture is taken first
		reply(null)
