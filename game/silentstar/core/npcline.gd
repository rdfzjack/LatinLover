extends RefCounted
## NPC special events: encounters on map locations, party and year-end texts, lines (romance beats). Only the part that is
## done lives here; see design/GDD.md section 13.3 for the rules. All functions are static.
##
## State of one NPC is st.story["npc"][id] = {enc: {stage: true}, line: "none", beat: 0, ...} (saved with the game).
## Random numbers of these events come from the dice stream (st.rng.dice), never from the logic stream.

const Rules = preload("res://core/rules.gd")
const Events = preload("res://core/events.gd")

const SLOTS := ["early", "mid", "late"]


static func npc_state(st, npc: String) -> Dictionary:
	var all: Dictionary = st.story["npc"]
	if not all.has(npc):
		all[npc] = {"enc": {}, "line": "none", "beat": 0}
	return all[npc]


## 1924-25 early, 1926-27 mid, 1928-29 late.
static func stage_of(year: int) -> String:
	return "early" if year <= 1925 else ("mid" if year <= 1927 else "late")


## A month with no encounters and no line beats: August (birthday), December (year-end party), and the months with a casting board.
static func blocked_month(st, ym: int) -> bool:
	var m: Dictionary = st.d.months[ym]
	var mo := int(str(m["month"]).substr(5, 2))
	return mo == 8 or mo == 12 or m["board"]


static func _switch_on(st) -> bool:
	return st.d.t["npc_events"].get("enabled", true)


## After a class or job period has been settled: if an NPC is at the map location of this entry this period, the encounter
## pops (once per stage). The class / job result is already settled; the encounter changes only favor, flags and renyang.
static func period_end(story, st, i: int, entry: String) -> void:
	if not _switch_on(st):
		return
	var d = st.d
	if not d.entry_loc.has(entry):
		return
	if blocked_month(st, st.ym):
		return
	var loc: String = d.entry_loc[entry]
	var year: int = 1924 + Rules.fdiv(st.ym, 12)
	var mo: int = st.ym % 12 + 1
	var stage := stage_of(year)
	var hits := []
	for k in d.encounters.size():
		var r: Dictionary = d.encounters[k]
		if r["loc"] != loc or r.get("stage") != stage or not r["years"].has(year) or not r["months"].has(mo):
			continue
		if r["slot"] != SLOTS[i]:
			continue
		if r.has("entry") and r["entry"] != entry:
			continue
		var ns := npc_state(st, r["npc"])
		if ns["enc"].get(stage, false) or ns["line"] == "broken":
			continue
		if not Rules.cond(st, r.get("cond")):
			continue
		hits.append([ns["line"] == "active", st.favor.get(r["npc"], 0), -k, r])
	if hits.is_empty():
		return
	# Priority when two NPCs overlap: already in a line > higher favor > table order.
	hits.sort_custom(func(a, b):
		if a[0] != b[0]:
			return a[0]
		if a[1] != b[1]:
			return a[1] > b[1]
		return a[2] > b[2])
	var r: Dictionary = hits[0][3]
	npc_state(st, r["npc"])["enc"][stage] = true
	st.meet(r["npc"])
	Events.fire(story, st, r["event"])
