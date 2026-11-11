extends RefCounted
## Loads data/new/*.json and builds id lookup indexes. Read-only: never modifies the tables. Port of sim/data.py.
##
## The tables live in data/new/ at the repository root, shared with the Python simulator.
## By default they are found two levels above the project folder (game/silentstar -> repository root); another folder can be passed.

const Jsonx = preload("res://core/jsonx.gd")

const TABLES := ["stats", "skills", "classes", "books", "jobs", "rest", "places", "lifestyle", "street",
	"origins", "calendar", "habits", "rivals", "roles", "items", "events", "outing", "romance",
	"npc_schedule", "npc_chains", "annual", "opportunities", "endings"]

var t := {}
var ok := true

# Table order is the canonical order wherever a tie or an iteration order matters.
var attrs := []
var attr_init := {}
var attr_range := {}          # id -> [lo, hi]
var money_init := 0
var money_cap := 0
var roads := []
var road_skills := {}
var rep_range := []
var level_gate := []
var fame_tiers := []          # [[min, max], ...]
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
var item_order := {}          # item id -> row number in items.json, for stable iteration
var item_rules := {}
var months := []
var month_index := {}
var npcs := {}
var npc_order := {}           # npc id -> row number in romance.json
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
	for a in st["attrs"]:
		attrs.append(a["id"])
		attr_init[a["id"]] = a["init"]
		attr_range[a["id"]] = a["range"]
	money_init = st["money"]["init"]
	money_cap = st["money"]["max"]
	for r in st["roads"]:
		roads.append(r["id"])
		road_skills[r["id"]] = r["skills"]
	rep_range = st["rep_rules"]["range"]
	level_gate = st["levels"]["gate"]
	for x in st["fame_tiers"]:
		fame_tiers.append([x["min"], x["max"]])
	idx_rule = st["indices"]
	contract = st["contract"]

	for s in t["skills"]["skills"]:
		skills.append(s["id"])
		skill_init[s["id"]] = s["init"]
		skill_range[s["id"]] = s["train_range"]
		skill_road[s["id"]] = s["road"]
		if s.has("display_bonus"):
			skill_bonus[s["id"]] = s["display_bonus"]

	for c in t["classes"]["classes"]:
		classes[c["id"]] = c
	class_steps = t["classes"]["class_steps"]
	for b in t["books"]["books"]:
		books[b["id"]] = b
	for j in t["jobs"]["jobs"]:
		jobs[j["id"]] = j
	job_rules = t["jobs"]
	for r in t["rest"]["rests"]:
		rests[r["id"]] = r
	rest_forced = t["rest"]["forced"]
	for p in t["places"]["places"]:
		places[p["id"]] = p
	for x in t["lifestyle"]["lifestyles"]:
		lifestyles[x["id"]] = x
	for e in t["street"]["entries"]:
		street[e["id"]] = e
	discount = t["street"]["discount"]
	for i in t["items"]["items"]:
		item_order[i["id"]] = items.size()
		items[i["id"]] = i
	item_rules = t["items"]["rules"]
	months = t["calendar"]["months"]
	for i in months.size():
		month_index[months[i]["month"]] = i
	for n in t["romance"]["npcs"]:
		npc_order[n["id"]] = npcs.size()
		npcs[n["id"]] = n
		if n["class"] == "romance":
			romance_lines.append(n["id"])
	origins = t["origins"]["questions"]
	for e in t["endings"]["forced"]:
		endings_forced[e["id"]] = e

	# step 6: board, shooting, release, events, endings (ported in step 12)
	for r in t["roles"]["roles"]:
		roles[r["id"]] = r
	role_cfg = t["roles"]["defaults"]
	tag_families = t["endings"]["tag_families"]
	for k in tag_families:
		for x in tag_families[k]:
			content_tags.append(x)
	for r in t["rivals"]["named"]:
		rivals_named[r["id"]] = r
	for e in t["events"]["events"]:
		events[e["id"]] = e
	for e in t["outing"]["events"]:
		events[e["id"]] = e
	opps = t["opportunities"]["opportunities"]
	chains = t["npc_chains"]["chains"]
	schedule_npc = t["npc_schedule"]["schedule"]


## The road a class counts for in road_periods: the road of the first skill in its gain list
## (tutoring's first skill is writing, which counts for culture).
func class_road(cid: String):
	for e in classes[cid]["gain"]:
		if skill_road.has(e["stat"]):
			return skill_road[e["stat"]]
	return null


## The roads a job counts for in road_periods: roads of the skills in its daily_effect, deduplicated, in road order.
func job_roads(jid: String) -> Array:
	var rs := {}
	for e in jobs[jid]["daily_effect"]:
		if skill_road.has(e["stat"]):
			rs[skill_road[e["stat"]]] = true
	var out := []
	for r in roads:
		if rs.has(r):
			out.append(r)
	return out
