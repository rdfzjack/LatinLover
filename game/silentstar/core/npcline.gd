extends RefCounted
## NPC special events: encounters on map locations, party and year-end texts, lines (romance beats). Only the part that is
## done lives here; see design/GDD.md section 13.3 for the rules. All functions are static.
##
## State of one NPC is st.story["npc"][id] = {enc: {stage: true}, line: "none", beat: 0, ...} (saved with the game).
## Random numbers of these events come from the dice stream (st.rng.dice), never from the logic stream.

const Rules = preload("res://core/rules.gd")
const Events = preload("res://core/events.gd")
const Schedule = preload("res://core/schedule.gd")

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


# ---------- film dialogue (rival and co-star small talk) ----------

## Fires the first of these events that exists, has not been seen and whose condition holds. Returns whether one fired.
static func fire_first(story, st, ids: Array) -> bool:
	if not _switch_on(st):
		return false
	for eid in ids:
		if st.d.events.has(eid) and Events.ready(st, st.d.events[eid]):
			Events.fire(story, st, eid)
			return true
	return false


## After the auditions of a board: every named star the player played gets his small talk, by who won that match.
static func after_auditions(story, st, results: Array) -> void:
	for res in results:
		for m in res.get("rounds", []):
			var npc := str(m.get("npc", ""))
			if npc == "" or not npc_has_text(st, npc):
				continue
			var won: bool = m["score_line"][0] > m["score_line"][1]
			fire_first(story, st, ["film_%s_%s" % [npc, "rival_lose" if won else "rival_win"]])


## After the co-star mini game of film f: the partner's small talk (women: the first of two not seen yet).
static func costar(story, st, npc: String) -> void:
	if npc_has_text(st, npc):
		fire_first(story, st, ["film_%s_costar_1" % npc, "film_%s_costar_2" % npc, "film_%s_costar" % npc])


static func npc_has_text(st, npc: String) -> bool:
	return st.d.npc_with_text.has(npc)


# ---------- weekend party ----------

## Month start: the month before a casting board gets one party, on one of its Sundays (dice stream). The invitation letter is not built yet.
static func party_plan(st) -> void:
	st.story.erase("party")
	if not _switch_on(st):
		return
	var nxt: int = st.ym + 1
	if nxt >= st.d.months.size() or not st.d.months[nxt]["board"]:
		return
	var sundays: Array = st.d.months[st.ym]["sundays"]
	if sundays.is_empty():
		return
	st.story["party"] = {"ym": st.ym, "day": sundays[st.rng.dice.below(sundays.size())], "done": false}


## Named stars of the next board (fixed in the board table): their weight at the party is doubled.
static func next_board_cast(st) -> Array:
	var d = st.d
	var out := []
	var date: String = str(d.months[st.ym + 1]["month"]) if st.ym + 1 < d.months.size() else ""
	for row in d.t["roles"]["board_schedule"]:
		if row["month"] != date:
			continue
		for k in row:
			if k == "month" or not d.roles.has(row[k]):
				continue
			var r: Dictionary = d.roles[row[k]]
			for o in r["opponents"]:
				if o.has("named") and d.rivals_named.has(o["named"]):
					var n := str(d.rivals_named[o["named"]].get("npc", ""))
					if n != "" and not out.has(n):
						out.append(n)
			var h := str(r.get("heroine", ""))
			if d.npcs.has(h) and not out.has(h):
				out.append(h)
	return out


## Before period i: the party, when its Sunday falls in this period and he is not sick. Two stars are drawn (the dice stream; the
## ones on the next board count double), both get favor and are met; the player talks to one of them.
static func party_period(story, st, i: int) -> void:
	var p = st.story.get("party")
	if p == null or p["done"] or p["ym"] != st.ym or st.status.get("sick", 0):
		return
	var hit := false
	for dd in Schedule.days_of(st, i):
		if dd[0] == p["day"]:
			hit = true
	if not hit:
		return
	p["done"] = true
	var d = st.d
	var boost := next_board_cast(st)
	var ids := []
	var ws := []
	for nid in d.npcs:
		var n: Dictionary = d.npcs[nid]
		if not n.get("actor", false) or not n.has("present") or not (n["present"][0] <= st.date() and st.date() <= n["present"][1]):
			continue
		if nid == "dancequeen" and st.flags.get("dance.dead", 0) > 0:
			continue
		ids.append(nid)
		ws.append(2 if boost.has(nid) else 1)
	var guests := []
	for _k in 2:
		var tot := 0
		for w in ws:
			tot += w
		if tot <= 0:
			break
		var v: int = st.rng.dice.below(tot)
		for k in ids.size():
			if v < ws[k]:
				guests.append(ids[k])
				ids.remove_at(k)
				ws.remove_at(k)
				break
			v -= ws[k]
	if guests.is_empty():
		return
	for g in guests:
		st.meet(g)
		Rules.apply_effect(st, "favor.%s+5" % g, "event")
	st.story["last_party"] = {"ym": st.ym, "guests": guests}
	var pick: int = story.agent.party_guest(st, guests)
	var who: String = guests[clampi(pick, 0, guests.size() - 1)]
	var texts := []
	for n in range(1, 7):
		texts.append("party_%s_%d" % [who, n])
	if not fire_first(story, st, texts):
		Events.fire(story, st, "party_generic")


# ---------- year-end party (Christmas), together with the 12-31 annual placeholder ----------

## December: who can be talked to: people of the player's studio (once signed) and the fixed Sil, Duv, dance queen.
static func year_end(story, st) -> void:
	if not _switch_on(st):
		return
	var d = st.d
	var studio = st.story.get("studio")
	var cand := ["sil", "duv", "dancequeen"]
	if studio != null:
		for nid in d.npcs:
			if d.npcs[nid].get("studio") == studio and d.npcs[nid].get("actor", false) and not cand.has(nid):
				cand.append(nid)
	var who := []
	for nid in cand:
		var n: Dictionary = d.npcs[nid]
		if n.has("present") and not (n["present"][0] <= st.date() and st.date() <= n["present"][1]):
			continue
		if nid == "dancequeen" and st.flags.get("dance.dead", 0) > 0:
			continue
		who.append(nid)
	if who.is_empty():
		return
	var pick: int = story.agent.party_guest(st, who)
	var npc: String = who[clampi(pick, 0, who.size() - 1)]
	st.meet(npc)
	var texts := []
	for n in range(1, 7):
		texts.append("yearend_%s_%d" % [npc, n])
	if not fire_first(story, st, texts):
		Events.fire(story, st, "yearend_generic")
