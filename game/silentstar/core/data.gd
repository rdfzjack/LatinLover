extends RefCounted
## 读 data/new/*.json，建好按 id 查找的索引。只读，不改表。照抄 sim/data.py。
##
## 表放在仓库根目录的 data/new/，和 Python 试算器共用一份。
## 默认从工程目录往上两级找（game/silentstar → 仓库根）；也可以传别的目录。

const Jsonx = preload("res://core/jsonx.gd")

const TABLES := ["stats", "skills", "classes", "books", "jobs", "rest", "places", "lifestyle", "street",
	"origins", "calendar", "habits", "rivals", "roles", "items", "events", "outing", "romance",
	"npc_schedule", "npc_chains", "annual", "opportunities", "endings"]

var t := {}
var ok := true

var attrs := []
var attr_init := {}
var attr_range := {}          # 名字 -> [lo, hi]
var money_init := 0
var money_cap := 0
var roads := []
var road_skills := {}
var rep_range := []
var level_gate := []
var fame_tiers := []          # [[下限, 上限], …]
var idx_rule := {}
var contract := {}

var skills := []
var skill_init := {}
var skill_range := {}
var skill_road := {}
var skill_bonus := {}

var classes := {}
var class_steps = null
var books := {}
var jobs := {}
var job_rules := {}
var rests := {}
var rest_forced = null
var places := {}
var lifestyles := {}
var street := {}
var discount = null
var items := {}
var item_rules := {}
var months := []
var month_index := {}
var npcs := {}
var romance_lines := []
var origins := []
var endings_forced := {}

var roles := {}
var role_cfg := {}
var tag_families := {}
var content_tags := []
var rivals_named := {}
var events := {}
var opps := []
var chains = null
var schedule_npc = null


static func default_dir() -> String:
	return ProjectSettings.globalize_path("res://").path_join("../../data/new").simplify_path()


func _init(path := "") -> void:
	if path == "":
		path = default_dir()
	for n in TABLES:
		var v = Jsonx.read_file(path.path_join(n + ".json"))
		if v == null:
			ok = false
			return
		t[n] = v

	var st: Dictionary = t["stats"]
	for a in st["基础属性"]:
		attrs.append(a["名字"])
		attr_init[a["名字"]] = a["初值"]
		attr_range[a["名字"]] = a["范围"]
	money_init = st["金钱"]["初值"]
	money_cap = st["金钱"]["上限"]
	for r in st["声望"]:
		roads.append(r["名字"])
		road_skills[r["名字"]] = r["技能"]
	rep_range = st["声望规则"]["范围"]
	level_gate = st["等级"]["门槛"]
	for x in st["名气档"]:
		fame_tiers.append([x["下限"], x["上限"]])
	idx_rule = st["指数"]
	contract = st["合同"]

	for s in t["skills"]["技能"]:
		skills.append(s["名字"])
		skill_init[s["名字"]] = s["初值"]
		skill_range[s["名字"]] = s["训练范围"]
		skill_road[s["名字"]] = s["路"]
		if s.has("显示加成"):
			skill_bonus[s["名字"]] = s["显示加成"]

	for c in t["classes"]["课"]:
		classes[c["id"]] = c
	class_steps = t["classes"]["等级门槛"]
	for b in t["books"]["书"]:
		books[b["id"]] = b
	for j in t["jobs"]["工"]:
		jobs[j["id"]] = j
	job_rules = t["jobs"]
	for r in t["rest"]["休息"]:
		rests[r["id"]] = r
	rest_forced = t["rest"]["强制"]
	for p in t["places"]["地点"]:
		places[p["id"]] = p
	for x in t["lifestyle"]["生活方式"]:
		lifestyles[x["id"]] = x
	for e in t["street"]["入口"]:
		street[e["名字"]] = e
	discount = t["street"]["折扣"]
	for i in t["items"]["物品"]:
		items[i["id"]] = i
	item_rules = t["items"]["规则"]
	months = t["calendar"]["月"]
	for i in months.size():
		month_index[months[i]["月"]] = i
	for n in t["romance"]["npc"]:
		npcs[n["名字"]] = n
		if n["类"] == "感情线":
			romance_lines.append(n["名字"])
	origins = t["origins"]["问"]
	for e in t["endings"]["强制"]:
		endings_forced[e["id"]] = e

	# 第 6 步：选片板、拍摄、上映、事件、结局（第 12 步移植时用）
	for r in t["roles"]["角色"]:
		roles[r["id"]] = r
	role_cfg = t["roles"]["默认"]
	tag_families = t["endings"]["标签族"]
	for k in tag_families:
		for x in tag_families[k]:
			content_tags.append(x)
	for r in t["rivals"]["有名"]:
		rivals_named[r["id"]] = r
	for e in t["events"]["事件"]:
		events[e["id"]] = e
	for e in t["outing"]["事件"]:
		events[e["id"]] = e
	opps = t["opportunities"]["机遇"]
	chains = t["npc_chains"]["链"]
	schedule_npc = t["npc_schedule"]["日程"]


## 一门课算哪条路的“期数”：收益里第一个技能所在的路（家教的第一个技能是创作，算文化）。
func class_road(cid: String):
	for e in classes[cid]["收益"]:
		if skill_road.has(e["项"]):
			return skill_road[e["项"]]
	return null


## 一种工算哪几条路的“期数”：每天效果里出现的技能所在的路，去重，按路的顺序。
func job_roads(jid: String) -> Array:
	var rs := {}
	for e in jobs[jid]["每天效果"]:
		if skill_road.has(e["项"]):
			rs[skill_road[e["项"]]] = true
	var out := []
	for r in roads:
		if rs.has(r):
			out.append(r)
	return out
