extends RefCounted
## The whole state of one game, plus the derived values: displayed values, reputation, fame tier. Port of sim/state.py.
##
## A save is the JSON of to_dict(): both random streams, all counters, flags, the table of fired events, the points left in each book (GDD 16).
## Usage:
##   var st = State.new(data); st.start(seed, [0, 0, 0])            new game
##   var s = st.dumps(); var st2 = State.new(data); st2.loads(s)    save and load

const Rng = preload("res://core/rng.gd")
const Rules = preload("res://core/rules.gd")
const Jsonx = preload("res://core/jsonx.gd")

const STATUS_KEYS := ["sick", "very_sick", "reckless", "in_love", "long_contract", "shooting_period", "shoot_this_month", "has_pending_role"]

## 2: English ids and keys (step 9c-1); older saves are not readable
const SAVE_VERSION := 2
const SAVE_KEYS := ["ym", "attr", "skill", "money", "corr", "favor", "known", "flags", "count", "tags", "weights",
	"books", "read_books", "items", "equip", "lifestyle", "idx", "status", "romance_months",
	"debt_months", "drug", "collapse_months", "forced_rest", "void_next", "exposed",
	"month_used", "fired", "ended", "finished", "story", "drug_points", "void_periods"]

var d                          # core/data.gd
var rng
var ym := 0                    # month index, 0 = 1924-01
var attr := {}                 # base attributes (base values, gear not included)
var skill := {}                # skill training values
var money := 0
var corr := {}                 # reputation bonus values
var favor := {}
var known := []
var flags := {}                # flags: name -> integer (mostly 0/1; accent_period style ones count down)
var count := {}                # counters: class_periods.<class> job_periods.<job> road_periods.<road> count.<name> ...
var tags := {}                 # film tag counts
var weights := {}              # board weights (weight.<tag>)
var books := {}                # books held and not finished: id -> points left
var read_books := []           # books already read (can be sold at half price)
var items := []                # ids of held items (may repeat)
var equip := {"outfit": null, "accessory": []}
var lifestyle := "life_normal"
var idx := {"sick_index": 0, "reckless_index": 0}   # computed at month end, kept for the whole month
var status := {}
var romance_months := 0
var debt_months := 0
var drug := 0                  # drug_stage 0-3; from step 12c derived from drug_points (stats.drug.stage_lines)
var drug_points := 0           # step 12c: +1 per boost, 0 after detox
var collapse_months := 0       # months in a row with sick_index = 100
var forced_rest := 0           # 1 = the sanatorium is forced next month (very sick)
var void_next := 0             # 1 = next month's schedule is void
var void_periods := []         # step 12c: absolute periods (ym * 3 + i) that are void (detention after an arrest)
var exposed := 0               # whether there was exposure this month
var month_used := {}           # limited services already used this month
var fired := {}                # fired events: id -> times
var ended = null               # ending id
var finished := 0              # 1 after the 1929-12 month settlement
var story := {}                # step 6: board, film contracts, event records, ending (see new_story)
var debug_log := []            # for debugging, not saved (called log in Python)
var src := {}                  # not saved: effect totals by source, src[source][name] (Rules.apply_effect); "income" = all money gained


## The state of step 6, all directly storable in JSON. The fields are explained in new_story of sim/state.py.
static func new_story() -> Dictionary:
	return {"board": null, "films": [], "boarded": {}, "pending_board": [], "tipoff": 0, "last_fired": {},
		"script": {"self_written": 0, "duv_written": 0, "co_written": 0}, "contract_refused": -99, "transition": [0, null],
		"scandal_cover_year": 0, "leak_year": 0, "seq": 0, "ending": null}


func _init(data) -> void:
	d = data
	rng = Rng.new(0)
	attr = data.attr_init.duplicate()
	skill = data.skill_init.duplicate()
	money = data.money_init
	for r in data.roads:
		corr[r] = 0
	for n in data.npcs:
		favor[n] = data.npcs[n]["favor_init"]
		if data.npcs[n].get("known_at_start", false):
			known.append(n)
	known.sort()
	for k in STATUS_KEYS:
		status[k] = 0
	story = new_story()


# ---------- origin ----------

## origin: which option was picked for each opening question (counting from 0). Python's State.new.
func start(sd: int, origin := [0, 0, 0]) -> void:
	rng = Rng.new(sd)
	for i in mini(d.origins.size(), origin.size()):
		var o: Dictionary = d.origins[i]["options"][origin[i]]
		if o["effect"]:
			Rules.apply_effect(self, o["effect"], "origin")
		for t in o["tag_counts"]:
			tags[t] = tags.get(t, 0) + o["tag_counts"][t]
		for f in o["flags"]:
			flags[f] = 1
		for it in o["items"]:
			items.append(it)
	update_indices()


# ---------- calendar ----------

func month() -> Dictionary:
	return d.months[ym]


func date() -> String:
	return d.months[mini(ym, d.months.size() - 1)]["month"]


# ---------- counters ----------

func cnt(k: String) -> int:
	return count.get(k, 0)


func inc(k: String, n := 1) -> void:
	count[k] = count.get(k, 0) + n


# ---------- gear bonus ----------

## Held items that take effect by being held: within one exclusive group only the highest price counts;
## several copies of one item count once. Iterated in table order (item_order).
func _held() -> Array:
	var uniq := {}
	for iid in items:
		uniq[iid] = true
	var ids := uniq.keys()
	ids.sort_custom(func(a, b): return d.item_order[a] < d.item_order[b])
	var best := {}
	var out := []
	for iid in ids:
		var it: Dictionary = d.items[iid]
		if it["class"] != "held":
			continue
		var g = it.get("exclusive_group")
		if g == null:
			out.append(iid)
		elif not best.has(g) or it["price"] > d.items[best[g]]["price"]:
			best[g] = iid     # keeps the position of the group's first appearance, like a Python dict
	for g in best:
		out.append(best[g])
	return out


## Bonus from gear and held items: {attribute or skill: value}.
## Outfits follow GDD 14.1: outfit value x (50 + grooming)/100, truncated toward zero; grooming here is the training value plus the non-outfit bonus.
func bonus() -> Dictionary:
	var b := {}
	var plain: Array = _held() + equip["accessory"]
	for iid in plain:
		for e in Rules.parse_effect(d.items[iid]["effect"]):
			var op: String = e[1]
			if (op == "+" or op == "-") and e[3] == "":
				b[e[0]] = b.get(e[0], 0) + (e[2] if op == "+" else -e[2])
	var cl = equip["outfit"]
	if cl != null:
		var f: int = 50 + skill["grooming"] + b.get("grooming", 0)
		for e in Rules.parse_effect(d.items[cl]["effect"]):
			var op: String = e[1]
			if (op == "+" or op == "-") and e[3] == "":
				var v: int = e[2] if op == "+" else -e[2]
				b[e[0]] = b.get(e[0], 0) + Rules.tdiv(v * f, 100)
	return b


# ---------- displayed values ----------

## Displayed value of an attribute or skill. Conditions, success lines and checks all use it. b is computed when not passed.
func val(name: String, b = null) -> int:
	if b == null:
		b = bonus()
	if attr.has(name):
		var rg: Array = d.attr_range[name]
		return clampi(attr[name] + b.get(name, 0), rg[0], rg[1])
	if skill.has(name):
		var v: int = skill[name] + b.get(name, 0)
		var sb = d.skill_bonus.get(name)
		if sb != null:
			v += mini(Rules.fdiv(val(sb["attr"], b), sb["div"]), sb["max"])
		return maxi(0, v)
	push_error("not an attribute or a skill: %s" % name)
	return 0


func rep(road: String, b = null) -> int:
	if b == null:
		b = bonus()
	var v: int = corr[road]
	for s in d.road_skills[road]:
		v += val(s, b)
	return clampi(v, d.rep_range[0], d.rep_range[1])


func level(road: String) -> int:
	var r := rep(road)
	var lv := 0
	for i in d.level_gate.size():
		if r >= d.level_gate[i]:
			lv = i
	return lv


func fame_tier() -> int:
	var f: int = attr["fame"]
	for i in d.fame_tiers.size():
		if d.fame_tiers[i][0] <= f and f <= d.fame_tiers[i][1]:
			return i
	return d.fame_tiers.size() - 1


## Highest base attribute (GDD 10): the highest of stamina, education, loyalty, looks, discipline and crime; ties go to the earlier one.
func highest_base() -> String:
	var b := bonus()
	var best := ""
	var bv := 0
	for n in ["stamina", "education", "loyalty", "looks", "discipline", "crime"]:
		var v := val(n, b)
		if best == "" or v > bv:
			best = n
			bv = v
	return best


# ---------- indices ----------

func calc_indices() -> Array:
	var b := bonus()
	var tired := val("fatigue", b)
	var sick := clampi(tired - val("stamina", b), 0, 100)
	return [sick, 0]       # six-year swap: the reckless index is gone (kept at 0 so saves and old conditions still read)


## Computes the two indices at month end and updates the status (GDD 10). The result is kept for the whole month.
func update_indices() -> void:
	var si := calc_indices()
	var r: Dictionary = d.idx_rule
	idx["sick_index"] = si[0]
	idx["reckless_index"] = si[1]
	status["sick"] = 1 if si[0] >= r["sick_index"]["status_line"] else 0
	status["very_sick"] = 1 if si[0] >= r["sick_index"]["very_sick_line"] else 0
	status["reckless"] = 1 if si[1] >= r["reckless_index"]["status_line"] else 0


# ---------- money ----------

func add_money(n: int) -> void:
	var before := money
	money = mini(money + n, d.money_cap)
	if money > before:
		src["income"] = src.get("income", 0) + money - before


## Adds to the per-source totals (report only, not saved).
func track(source: String, name: String, delta: int) -> void:
	if delta == 0:
		return
	if not src.has(source):
		src[source] = {}
	src[source][name] = src[source].get(name, 0) + delta


## drug_stage from drug_points (stats.drug.stage_lines).
func drug_stage_of(points: int) -> int:
	var s := 0
	for line in d.t["stats"]["drug"]["stage_lines"]:
		if points >= line:
			s += 1
	return s


# ---------- save ----------

func to_dict() -> Dictionary:
	var out := {"version": SAVE_VERSION, "rng": rng.dump()}
	for k in SAVE_KEYS:
		out[k] = get(k)
	return Jsonx.copy(out)


## Byte-identical to Python's State.dumps.
func dumps() -> String:
	return Jsonx.dumps(to_dict())


## Returns false (and leaves the state untouched) when the save version is not SAVE_VERSION.
func from_dict(sv: Dictionary) -> bool:
	if sv.get("version") != SAVE_VERSION:
		push_error("unsupported save version %s, expected %d" % [sv.get("version"), SAVE_VERSION])
		return false
	rng = Rng.load_from(sv["rng"])
	for k in SAVE_KEYS:
		if sv.has(k):
			set(k, Jsonx.copy(sv[k]))
	return true


func loads(s: String) -> bool:
	return from_dict(Jsonx.parse(s))
