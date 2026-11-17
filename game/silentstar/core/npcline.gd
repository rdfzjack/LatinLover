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
	if not contact_cross(story, st, r["npc"]):
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
			if contact_cross(story, st, npc):
				continue
			fire_first(story, st, ["film_%s_%s" % [npc, "rival_lose" if won else "rival_win"]])


## After the co-star mini game of film f: the partner's small talk (women: the first of two not seen yet).
static func costar(story, st, npc: String) -> void:
	if npc_has_text(st, npc) and not contact_cross(story, st, npc):
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


## Month start, the mail: for now the only letter is the party invitation of this month; the player answers yes or no.
## Declined: the party does not happen. (The letter pool, the number of letters and who reads them are not built yet.)
static func mail(story, st) -> void:
	var p = st.story.get("party")
	if p == null or p["ym"] != st.ym:
		return
	p["invited"] = true
	p["declined"] = not story.agent.party_invite(st, int(p["day"]))


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
## ones on the next board count double); the player talks to one of them. No base favor: only the option picked changes it.
static func party_period(story, st, i: int) -> void:
	var p = st.story.get("party")
	if p == null or p["done"] or p["ym"] != st.ym or st.status.get("sick", 0) or p.get("declined", false):
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
	st.story["last_party"] = {"ym": st.ym, "guests": guests}
	var pick: int = story.agent.party_guest(st, guests)
	var who: String = guests[clampi(pick, 0, guests.size() - 1)]
	st.meet(who)      # only the one talked to is met and only his or her option changes favor; the other guest is not met at all
	var texts := []
	for n in range(1, 7):
		texts.append("party_%s_%d" % [who, n])
	if contact_cross(story, st, who):
		return
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
	if contact_cross(story, st, npc, true):
		return
	if not fire_first(story, st, texts):
		Events.fire(story, st, "yearend_generic")


# ---------- crossing the line (越线) and the beats of a line ----------

const BEATS := [2, 3, 4, 5]
const COOLDOWN_MONTHS := 2


static func ym_of(date: String) -> int:
	return (int(date.substr(0, 4)) - 1924) * 12 + int(date.substr(5, 2)) - 1


## The option of an NPC event has a `line` action (events.gd calls this after the option's effects).
static func apply_line(st, e: Dictionary, o: Dictionary) -> void:
	var npc := str(e.get("npc", ""))
	if npc == "":
		return
	var ns := npc_state(st, npc)
	match str(o["line"]):
		"drop_new":                                   # showdown: the player picks the one already there
			npc_state(st, str(e["new"]))["line"] = "broken"
		"drop_inc":                                   # showdown: the player picks the new one
			npc_state(st, str(e["inc"]))["line"] = "broken"
		"both":                                       # both go on: remembered for the ending rumor
			st.story["fights"] = st.story.get("fights", []) + [[str(e["inc"]), str(e["new"])]]
		"both_break":                                 # both go on, except the special pair where both end
			npc_state(st, str(e["new"]))["line"] = "broken"
			npc_state(st, str(e["inc"]))["line"] = "broken"
		"run":                                        # both lines freeze for a year
			for k in [str(e["inc"]), str(e["new"])]:
				var x := npc_state(st, k)
				x["line"] = "frozen"
				x["frozen_until"] = st.ym + int(st.d.t["npc_events"].get("frozen_months", 12))
		"active":
			ns["line"] = "active"
			ns["beat"] = 1
			ns["start_ym"] = st.ym
			ns["last_ym"] = st.ym
			ns["played"] = [e["id"]]
			st.inc("count.line_started")
			st.story["pending_showdown"] = npc          # run after the crossing event is shown (contact_cross)
		"botched":
			st.favor[npc] = mini(st.favor.get(npc, 0), 59)     # back under 60: has to be raised again
		"end":
			ns["line"] = "finished"


## A contact with an NPC (encounter, party, year-end party, co-star): with favor >= 60 and no line yet, the line-crossing event
## replaces the normal text. Not in an occupied month, except at the year-end party. Returns whether it fired.
static func contact_cross(story, st, npc: String, year_end := false) -> bool:
	if not _switch_on(st) or (blocked_month(st, st.ym) and not year_end):
		return false
	var eid := "cross_" + npc
	if not st.d.events.has(eid) or not Events.ready(st, st.d.events[eid]):
		return false
	Events.fire(story, st, eid)
	var p = st.story.get("pending_showdown")
	if p != null:
		st.story.erase("pending_showdown")
		showdown(story, st, str(p))
	return true


static func _beat_event(st, npc: String, n: int):
	var eid := "beat_%s_%d" % [npc, n]
	return st.d.events.get(eid)


## Before period i: the next beat of a line that is active. An anchored beat (a date in its `anchor`) comes in that month whatever
## the cooldown and whatever the occupied months, and the beats before it that were not played are dropped; a beat whose anchor has
## passed before the line began is skipped. Other beats come 2 months after the last beat, not in an occupied month. One beat per
## period; with several lines the one that began first goes first. Then the default death of the dance queen (1927-10).
static func beat_period(story, st, i: int) -> void:
	if not _switch_on(st):
		return
	if thaw(story, st):
		return
	var lines := []
	for npc in st.story["npc"]:
		var ns: Dictionary = st.story["npc"][npc]
		if ns["line"] == "active":
			lines.append([ns.get("start_ym", 0), npc])
	lines.sort()
	for x in lines:
		var npc: String = x[1]
		var ns: Dictionary = st.story["npc"][npc]
		var played: Array = ns.get("played", [])
		var due = null
		for n in BEATS:                           # an anchored beat whose month is now: it comes, the unplayed beats before it are dropped
			var e = _beat_event(st, npc, n)
			if e != null and e.has("anchor") and not played.has(e["id"]) and ym_of(str(e["anchor"])) == st.ym:
				due = e
				for m in range(2, n):
					var b = _beat_event(st, npc, m)
					if b != null and not played.has(b["id"]):
						played.append(b["id"])
				break
		for n in BEATS:
			if due != null:
				break
			var e = _beat_event(st, npc, n)
			if e == null or played.has(e["id"]):
				continue
			if e.has("anchor"):
				if ym_of(str(e["anchor"])) < st.ym:
					played.append(e["id"])        # the date has passed: skipped
					continue
				break                             # an anchored beat waits for its month and holds back the later beats
			if st.ym - ns.get("last_ym", st.ym) >= COOLDOWN_MONTHS and not blocked_month(st, st.ym):
				due = e
			break
		ns["played"] = played
		if due != null:
			_play_beat(story, st, npc, ns, due)
			break
	_default_deaths(st)


static func _play_beat(story, st, npc: String, ns: Dictionary, e: Dictionary) -> void:
	ns["played"].append(e["id"])
	ns["beat"] = maxi(ns.get("beat", 1), int(e["beat"]))
	ns["last_ym"] = st.ym
	Events.fire(story, st, e["id"])
	exposure_roll(story, st, npc)
	if ns["line"] == "active":
		var left := false
		for n in BEATS:
			var b = _beat_event(st, npc, n)
			if b != null and not ns["played"].has(b["id"]) and not (b.has("anchor") and ym_of(str(b["anchor"])) < st.ym):
				left = true
		if not left:
			ns["line"] = "finished"


## Players who are not in her line (or whose line is not active) lose the dance queen at the point of death, 1927-10; she
## is only news for them. Saving her is possible only through her line (flag dance.saved).
static func _default_deaths(st) -> void:
	if st.ym < ym_of("1927-10") or st.flags.get("dance.dead", 0) > 0 or st.flags.get("dance.saved", 0) > 0:
		return
	var ns := npc_state(st, "dancequeen")
	if ns["line"] == "active" and not ns.get("played", []).has("beat_dancequeen_5"):
		return
	st.flags["dance.dead"] = 1


# ---------- showdown (修罗场), exposure, thawing ----------

static func active_lines(st) -> Array:
	var out := []
	for npc in st.story["npc"]:
		var ns: Dictionary = st.story["npc"][npc]
		if ns["line"] == "active":
			out.append([ns.get("start_ym", 0), npc])
	out.sort()
	return out


static func _multi(st, npc: String) -> String:
	return str(st.d.npcs[npc].get("multi", "accept"))


## A new line has just begun. Only the 'accept' types find out on the spot; the 'reject' ones are found out by a roll later
## (exposure). With 3 or more active lines everybody is there at once.
static func showdown(story, st, new: String) -> void:
	var act := active_lines(st)
	if act.size() < 2:
		return
	if act.size() >= 3:
		Events.fire(story, st, "showdown_all")
		for x in act:
			if _multi(st, x[1]) in ["reject", "reject_soft"]:
				_found(story, st, x[1], false)
		return
	var inc: String = act[0][1] if act[0][1] != new else act[1][1]
	if not _multi(st, inc) in ["accept", "accept_conditional"]:
		return                  # the others are all 'reject' types: nothing happens, the player is doing it behind their back
	var eid := "showdown_%s_%s" % [inc, new]
	if st.d.events.has(eid):
		Events.fire(story, st, eid)


## A 'reject' NPC finds out: the line breaks ('reject_soft' would only cost favor).
static func _found(story, st, npc: String, show := true) -> void:
	if show and st.d.events.has("found_" + npc):
		Events.fire(story, st, "found_" + npc)
	if _multi(st, npc) == "reject_soft":
		Rules.apply_effect(st, "favor.%s-30" % npc, "event")
	else:
		npc_state(st, npc)["line"] = "broken"


## After a beat of a 'reject' NPC while the player has other active lines: one roll by the fame tier whether he or she finds out.
static func exposure_roll(story, st, npc: String) -> void:
	if not _multi(st, npc) in ["reject", "reject_soft"] or npc_state(st, npc)["line"] != "active":
		return
	var others := 0
	for x in active_lines(st):
		if x[1] != npc:
			others += 1
	if others == 0:
		return
	var pct: int = int(st.d.t["npc_events"]["expose_pct"][st.fame_tier()])
	if st.rng.dice.below(100) < pct:
		_found(story, st, npc)


## A frozen line thaws after its year: the "why are you back" line, then the line goes on (the cooldown starts again).
static func thaw(story, st) -> bool:
	for npc in st.story["npc"]:
		var ns: Dictionary = st.story["npc"][npc]
		if ns["line"] == "frozen" and st.ym >= int(ns.get("frozen_until", 0)):
			ns["line"] = "active"
			ns["last_ym"] = st.ym
			if st.d.events.has("back_" + npc):
				Events.fire(story, st, "back_" + npc)
			return true
	return false


# ---------- studio ----------

## Month start: with fame >= sign_fame and no studio yet the player may sign with one of the four (declined: asked again later).
static func studio_offer(story, st) -> void:
	var c: Dictionary = st.d.t["npc_events"]
	if not _switch_on(st) or st.story.get("studio") != null or st.attr["fame"] < int(c["sign_fame"]):
		return
	if st.ym < int(st.story.get("studio_asked", -99)) + int(c["reoffer_months"]):
		return
	st.story["studio_asked"] = st.ym
	var pick: int = story.agent.choose_studio(st, c["studios"])
	if pick >= 0 and pick < c["studios"].size():
		st.story["studio"] = c["studios"][pick]["id"]


# ---------- ending rumors (结算传闻) ----------

## The tier of the rumors: crime emperor (the underworld ending), hot (fame tier "hot" or more), flop (has won a role), back to the dock.
static func rumor_tier(st, eid: String) -> String:
	if eid == "end_underworld":
		return "crime"
	if st.fame_tier() >= 3:
		return "hot"
	if st.cnt("count.audition_won") > 0:
		return "flop"
	return "dock"


## One rumor per line that is active or finished (a broken line says nothing), in the order the lines began.
## Flag overrides first, then the tier text, then a sentence for each variant flag; a prefix when two lines went on after a fight.
static func rumors(st, eid: String) -> Array:
	var d = st.d
	var tier := rumor_tier(st, eid)
	var rows: Array = d.t["npc_lines"]["rumors"]
	var live := []
	for npc in st.story["npc"]:
		var ns: Dictionary = st.story["npc"][npc]
		if ns["line"] == "active" or ns["line"] == "finished":
			live.append([ns.get("start_ym", 0), npc])
	live.sort()
	var out := []
	for x in live:
		var npc: String = x[1]
		var text := ""
		for r in rows:
			if r["npc"] == npc and r["kind"] == "override":
				var all := true
				for f in r["flags"]:
					if st.flags.get(f, 0) <= 0:
						all = false
				if all:
					text = r["text"]
					break
		if text == "":
			for r in rows:
				if r["npc"] == npc and r["kind"] == "tier" and r["tier"] == tier:
					text = r["text"]
		for r in rows:
			if r["npc"] == npc and r["kind"] == "variant" and st.flags.get(r["flag"], 0) > 0:
				text += r["text"]
		var prefix := ""
		for fgt in st.story.get("fights", []):
			var other: String = fgt[1] if fgt[0] == npc else (fgt[0] if fgt[1] == npc else "")
			if other != "" and live.any(func(y): return y[1] == other):
				for r in rows:
					if r["kind"] == "fight":
						prefix = str(r["text"]).replace("{inc}", str(d.npcs[fgt[0]]["name"])).replace("{new}", str(d.npcs[fgt[1]]["name"]))
		if text != "":
			out.append(prefix + text)
	return out
