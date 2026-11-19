extends RefCounted
## Play record (user, 2026-11): one short plain-text file per game, written as the game goes, for balancing.
## Off unless st.story["record_file"] is set (the UI sets it at a new game; bots only when a script asks for it).
## The file keeps growing across saves and loads; a load writes a "记" line so a reloaded stretch can be told apart.
## Kept short on purpose (the user sends whole files): a 月 line only on board months and when a road level changes.
## The abbreviations are explained in the first line of the file. All functions are static; st is core/state.gd.

const SIZE := {"big": "大", "medium": "中", "small": "小"}
const WHY := {"trait_block": "状态不能试镜", "out_of_reach": "名气不够", "gates": "属性不够", "speech": "谈吐不够",
	"morals": "道德条款", "not a house role": "非本厂"}
const RESULT := {"remembered": "胜(被记住)", "won": "胜", "narrow_loss": "惜败", "lost": "负", "botched": "演砸"}
const ATTRS := {"stamina": "体", "education": "教", "loyalty": "义", "looks": "貌", "discipline": "律", "crime": "罪", "fatigue": "疲"}
const ROAD := ["硬", "情", "文", "手"]
const HEADER := "# 试镜和练度记录。月=月初（只在选片月和某路等级变化时记）：硬/情/文/手 声望/等级，名=名气，体教义貌律罪疲=基础属性，洞=洞悉。板=选片板：大中小+路、可报或原因、对手（无名或名字+四路等级 硬/情/文/手，k=主色张数）。试=一场试镜：来源 片 第几场|对手|习惯(知道/不知道)|名气 我:他|我的牌|他的牌|风=场风|每轮(>赢 <输 =平，平局写名气判的结果)|比分 结果。牌=路首字+点数。映=上映：片(配=配角)|片名|表现P 契合F 标签T 运气|得分X 结果|名气 声望变化。"


## audition.gd preloads this file, so this one loads it at run time (no preload cycle).
static func _aud():
	return load("res://core/audition.gd")


static func on(st) -> bool:
	return str(st.story.get("record_file", "")) != ""


## Starts a new record file for this game. tag: an extra name part (scripts that run many games in the same second).
static func start(st, tag := "") -> void:
	DirAccess.make_dir_recursive_absolute("user://records")
	var stamp := Time.get_datetime_string_from_system().replace(":", "-").replace("T", "_")
	st.story["record_file"] = "user://records/record_%s%s.txt" % [stamp, ("_" + tag) if tag != "" else ""]
	st.story["record_levels"] = []
	if FileAccess.file_exists(st.story["record_file"]):
		DirAccess.remove_absolute(st.story["record_file"])
	write(st, HEADER)


static func write(st, text: String) -> void:
	if not on(st):
		return
	var path: String = st.story["record_file"]
	var f := FileAccess.open(path, FileAccess.READ_WRITE) if FileAccess.file_exists(path) else FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return
	f.seek_end()
	f.store_line(text)
	f.close()


static func hand(cards: Array) -> String:
	var out := ""
	for c in cards:
		out += "%s%d" % [ROAD[int(c[0])], int(c[1])]
	return out


static func role_text(st, e: Dictionary) -> String:
	var r: int = st.d.roads.find(str(e.get("road", "")))
	return str(SIZE.get(str(e.get("size", "")), "?")) + (ROAD[r] if r >= 0 else "?")


static func rival_text(rv: Dictionary) -> String:
	var lv := PackedStringArray()
	for x in rv["levels"]:
		lv.append(str(x))
	if rv["id"] == null:
		return "无名" + "/".join(lv)
	return "%s%sk%d" % [str(rv["name"]), "/".join(lv), int(rv["k"])]


static func habit_name(st, hid: String) -> String:
	for h in st.d.t["habits"]["habits"]:
		if h["id"] == hid:
			return str(h["name"])
	return hid


# ---------- lines ----------

## Month start. Written on board months and whenever a road level changed since the last 月 line.
static func month(st, board_month := false) -> void:
	if not on(st):
		return
	var b: Dictionary = st.bonus()
	var lv: Array = _aud().player_levels(st)
	if not board_month and lv == st.story.get("record_levels", []):
		return
	st.story["record_levels"] = lv.duplicate()
	var reps := PackedStringArray()
	for i in st.d.roads.size():
		reps.append("%s%d/%d" % [ROAD[i], st.rep(st.d.roads[i], b), lv[i]])
	var at := PackedStringArray()
	for k in ATTRS:
		at.append("%s%d" % [ATTRS[k], st.val(k, b)])
	write(st, "|".join(["月", st.date(), " ".join(reps), "名%d 钱%d" % [st.attr["fame"], st.money], " ".join(at),
		"洞%d" % st.val("insight", b)]))


static func board(st, bd: Dictionary) -> void:
	if not on(st):
		return
	var parts := PackedStringArray(["板", st.date()])
	for e in bd["roles"]:
		var why = e["intel"].get("eligible")
		var ops := PackedStringArray()
		for rv in e["opponents"]:
			ops.append(rival_text(rv))
		parts.append("%s %s %s" % [role_text(st, e), "可报" if why == null else str(WHY.get(str(why), str(why))), ",".join(ops)])
	write(st, "|".join(parts))


## One match. src: 板 (board), 换角 (swap role) or 抢角 (steal role); n: match number (big films have 2); known: the player could see the habit.
static func match(st, role: Dictionary, rv: Dictionary, m: Dictionary, n: int, known: bool, src: String, result := "") -> void:
	if not on(st):
		return
	var rounds := PackedStringArray()
	for r in m["rounds"]:
		var v: Array = _aud().effective(st.d, r[0], r[1], m["style"])
		var mark := ">" if v[0] > v[1] else ("<" if v[0] < v[1] else ("=赢" if r[2] else "=输"))
		rounds.append("%s%d%s%s%d" % [ROAD[int(r[0][0])], int(r[0][1]), mark, ROAD[int(r[1][0])], int(r[1][1])])
	var sl: Array = m["score_line"]
	write(st, "|".join(["试", st.date(), "%s %s 第%d场" % [src, role_text(st, role), n + 1], rival_text(rv),
		"%s(%s)" % [habit_name(st, str(rv["habit"])), "知道" if known else "不知道"],
		"名%d:%d" % [st.attr["fame"], int(rv["fame"])], "我" + hand(m["my_cards"]), "他" + hand(m["rival_cards"]),
		"风" + ROAD[int(m["style"])], " ".join(rounds), "%d:%d %s" % [sl[0], sl[1], str(RESULT.get(result, result))]]))


## One released film (user 2026-11): the parts of the box-office score, to check the release odds against real play.
const BAND := {"hit": "大卖", "normal": "正常", "poor": "不行", "flop": "惨败"}
static func release(st, f: Dictionary) -> void:
	if not on(st):
		return
	var r: Dictionary = f["result"]
	var B: int = int(r["B"])
	write(st, "|".join(["映", st.date(), role_text(st, f["roles"]) + ("配" if f["support"] else ""), str(f["roles"].get("name", "")),
		"P%.2f F%.2f T%.2f 运%d%%" % [int(r["P"]) / 1000.0, int(r["F"]) / 1000.0, int(r["T"]) / 1000.0, int(r.get("luck", 100))],
		"X%.2f %s" % [int(r["S"]) / (B * 1000.0), str(BAND.get(str(r["band"]), r["band"]))],
		"名%+d 声%+d" % [int(r["fame"]), int(r["rep_bonus"])]]))


static func note(st, text: String) -> void:
	write(st, "|".join(["记", st.date(), text]))


static func ending(st) -> void:
	if not on(st):
		return
	var b: Dictionary = st.bonus()
	var reps := PackedStringArray()
	for i in st.d.roads.size():
		reps.append("%s%d" % [ROAD[i], st.rep(st.d.roads[i], b)])
	write(st, "|".join(["结局", st.date(), str(st.ended), " ".join(reps), "名%d 钱%d" % [st.attr["fame"], st.money]]))
