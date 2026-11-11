extends RefCounted
## Ending resolution (GDD 15): forced -> special -> category -> grade -> ending table -> character tier -> destiny -> comment and
## total score. Data is in endings.json. Port of sim/ending.py.
##
## register() adds the derived variables the ending conditions need to Rules.extra_vars: grade, top_tag_family, undefined,
## lowbudget_typed. Story calls it when it is created (Python registers them on import).
## All functions are static; st is an instance of core/state.gd.

const Rules = preload("res://core/rules.gd")
const Film = preload("res://core/film.gd")

const GRADES := ["S", "A", "B", "C"]
const SCORE_ATTRS := ["stamina", "education", "loyalty", "looks", "discipline"]


static func register() -> void:
	var me = load("res://core/ending.gd")
	var film = load("res://core/film.gd")
	Rules.extra_vars["grade"] = Callable(me, "tier")
	Rules.extra_vars["top_tag_family"] = Callable(me, "biggest_family")
	Rules.extra_vars["undefined"] = Callable(film, "undefined")
	Rules.extra_vars["lowbudget_typed"] = Callable(film, "low_budget")


static func tier(st) -> String:
	var lines: Dictionary = st.d.t["endings"]["grade_lines"]
	var v: int = Rules.get_var(st, "max_rep")
	for k in GRADES:
		if v >= lines[k]:
			return k
	return "D"


## The tag family with the largest sum of counts; ties follow the table order; null when all are 0.
static func biggest_family(st):
	var best = null
	var bv := 0
	for fam in st.d.tag_families:
		var v := 0
		for t in st.d.tag_families[fam]:
			v += st.tags.get(t, 0)
		if v > bv:
			best = fam
			bv = v
	return best


## The job with the most job_periods (ties go to the earlier row of the table); null when no job was ever done.
static func most_job(st):
	var best = null
	var bv := 0
	for j in st.d.jobs:
		var v: int = st.cnt("job_periods." + j)
		if v > bv:
			best = j
			bv = v
	return best


## The class taken most often (reading counts as one class, recorded as "book"), by class_periods; ties go to the earlier one.
static func most_class(st):
	var best = null
	var bv := 0
	for c in st.d.classes:
		var v: int = st.cnt("class_periods." + c)
		if v > bv:
			best = c
			bv = v
	if st.cnt("count.book_periods") > bv:
		best = "book"
	return best


## Career ending: returns [ending id, category]. The forced ending (collapse) was already written to st.ended mid-game.
static func career(st) -> Array:
	var t: Dictionary = st.d.t["endings"]
	for e in t["special"]:
		if Rules.cond(st, e["cond"]):
			return [e["id"], "special"]
	var big = null
	for c in t["categories"]:
		if Rules.cond(st, c["cond"]):
			big = c["id"]
			break
	var lst := []
	for e in t["endings"]:
		if e["category"] == big:
			lst.append([e["order"], lst.size(), e])
	lst.sort_custom(func(a, b): return a[0] < b[0] if a[0] != b[0] else a[1] < b[1])
	for x in lst:
		if Rules.cond(st, x[2]["cond"]):
			return [x[2]["id"], big]
	push_error("%s has no fallback ending" % big)
	return [null, big]


## Character tier 1/2/3 (pine/bamboo/plum). An ending may write character: [{cond, tier}], otherwise the default tier is used.
static func character(st, eid: String) -> int:
	var t: Dictionary = st.d.t["endings"]
	for e in t["endings"]:
		if e["id"] == eid:
			for x in e.get("character", []):
				if Rules.cond(st, x["cond"]):
					return x["tier"]
			break
	return t["scoring"]["character_tiers"]["default_tier"]


## Destiny: of the four romance lines the one meeting its condition with the highest favor (ties go to the table order);
## otherwise the three ordinary destiny modes. In the Imperial screen idol run the Sil line is broken.
## Returns {class: special/ordinary, target or mode, good}.
static func home(st, eid: String) -> Dictionary:
	var d = st.d
	var best = null
	for n in d.romance_lines:
		var c = d.npcs[n].get("destiny_cond")
		if c == null or c.is_empty() or (n == "sil" and eid == "end_idol"):
			continue
		if Rules.cond(st, c) and (best == null or st.favor.get(n, 0) > st.favor.get(best, 0)):
			best = n
	if best != null:
		return {"class": "special", "target": best, "good": true}
	for m in d.t["endings"]["destiny"]["ordinary"]["mode"]:
		if Rules.cond(st, m["cond"]):
			var line: Array = m["good_destiny_line"]
			return {"class": "ordinary", "mode": m["mode"], "good": st.val(line[0]) >= line[1]}
	push_error("no ordinary destiny mode holds")
	return {}


static func score(st, rank: String, ch: int, hm: Dictionary) -> int:
	var sc: Dictionary = st.d.t["endings"]["scoring"]
	var b: Dictionary = st.bonus()
	var base: int = st.attr["fame"]
	for n in SCORE_ATTRS:
		base += st.val(n, b)
	var s: int = Rules.fdiv(base, 6) - st.val("crime", b)
	s += sc["ending_score"][rank]
	s += sc["character_tiers"]["score"][str(ch)]
	if hm["class"] == "special":
		s += sc["destiny_score"]["special"]
	else:
		s += sc["destiny_score"]["ordinary_good" if hm["good"] else "ordinary"]
	return s


## Ending resolution after the 1929-12 month end (or on a collapse). The result is written to st.story["ending"] and st.ended.
static func judge(st) -> Dictionary:
	if st.ended != null:          # forced ending mid-game
		var forced := {"ending": st.ended, "category": "forced", "grade": tier(st)}
		st.story["ending"] = forced
		return forced
	var cb := career(st)
	var eid: String = cb[0]
	var rank := tier(st)
	var ch := character(st, eid)
	var hm := home(st, eid)
	var res := {"ending": eid, "category": cb[1], "grade": rank, "character": ch, "destiny": hm,
		"top_job": most_job(st), "top_class": most_class(st), "total": score(st, rank, ch, hm)}
	st.ended = eid
	st.story["ending"] = res
	return res
