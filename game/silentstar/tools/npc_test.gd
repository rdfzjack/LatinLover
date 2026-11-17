extends SceneTree
## Checks of the NPC event system (core/npcline.gd). Run from the repository root:
##   godot --headless --path game/silentstar --script res://tools/npc_test.gd
## Prints OK lines and one FAIL line per problem; exit code 1 when anything fails.

const Data = preload("res://core/data.gd")
const Story = preload("res://core/story.gd")
const Npcline = preload("res://core/npcline.gd")
const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")
const State = preload("res://core/state.gd")

var fails := 0


func _init() -> void:
	var root := ProjectSettings.globalize_path("res://").path_join("../..").simplify_path()
	var d = Data.new(root.path_join("data/new"))
	_dice(d)
	_blocked(d)
	_encounter(d)
	_film_talk(d)
	_party(d)
	_year_end(d)
	_line(d)
	_showdown(d)
	_ending(d)
	print("npc_test: %d failure(s)" % fails)
	quit(1 if fails > 0 else 0)


func ok(cond: bool, what: String) -> void:
	if cond:
		print("OK   ", what)
	else:
		fails += 1
		print("FAIL ", what)


func _go_to(g, year: int, month: int) -> void:
	g.st.ym = (year - 1924) * 12 + month - 1


func _dice(d) -> void:
	var g = Story.new_game(d, 7)
	var a: int = g.st.rng.dice.below(1000)
	var s: String = g.st.dumps()
	var b: int = g.st.rng.dice.below(1000)
	var g2 = Story.new_game(d, 99)
	g2.st.loads(s)
	ok(g2.st.rng.dice.below(1000) == b, "dice stream is saved and restored (same roll after load)")
	var g3 = Story.new_game(d, 7)
	var l0: int = g3.st.rng.logic.below(1000)
	var g4 = Story.new_game(d, 7)
	g4.st.rng.dice.below(1000)
	ok(g4.st.rng.logic.below(1000) == l0, "rolling dice does not move the logic stream")
	ok(a >= 0, "dice roll works")


func _blocked(d) -> void:
	var g = Story.new_game(d, 1)
	_go_to(g, 1925, 3)
	ok(Npcline.blocked_month(g.st, g.st.ym), "1925-03 (board month) is blocked")
	_go_to(g, 1925, 8)
	ok(Npcline.blocked_month(g.st, g.st.ym), "August is blocked")
	_go_to(g, 1925, 12)
	ok(Npcline.blocked_month(g.st, g.st.ym), "December is blocked")
	_go_to(g, 1925, 4)
	ok(not Npcline.blocked_month(g.st, g.st.ym), "1925-04 is free")


func _encounter(d) -> void:
	var g = Story.new_game(d, 1)
	var st = g.st
	_go_to(g, 1925, 4)
	st.favor["cooper"] = 20
	# Cooper, early stage: studio location, early period, April 1925: the studio odd job (job_runner) of period 0
	Npcline.period_end(g.hooks, st, 1, "job_runner")
	ok(not Npcline.npc_state(st, "cooper")["enc"].get("early", false), "no encounter in the wrong period")
	Npcline.period_end(g.hooks, st, 0, "job_dock1")
	ok(not Npcline.npc_state(st, "cooper")["enc"].get("early", false), "no encounter at another location")
	var n0: int = st.favor["cooper"]
	Npcline.period_end(g.hooks, st, 0, "job_runner")
	ok(Npcline.npc_state(st, "cooper")["enc"].get("early", false), "Cooper's early encounter fires at the studio")
	ok(st.known.has("cooper"), "Cooper is in the people list after the encounter")
	ok(st.favor["cooper"] > n0, "an option of the encounter changed favor")
	var again: int = st.favor["cooper"]
	Npcline.period_end(g.hooks, st, 0, "job_runner")
	ok(st.favor["cooper"] == again, "an encounter fires once per stage")
	# a blocked month never fires
	var g2 = Story.new_game(d, 1)
	_go_to(g2, 1925, 3)
	Npcline.period_end(g2.hooks, g2.st, 0, "job_runner")
	ok(not Npcline.npc_state(g2.st, "cooper")["enc"].get("early", false), "no encounter in a board month")
	# renyang and flags through the effect parser
	var g3 = Story.new_game(d, 1)
	Rules.apply_effect(g3.st, "renyang-1 flag.nova.x=1 looks-20", "event")
	ok(g3.st.story["renyang"] == -1 and g3.st.story["renyang_hint"] == -1, "renyang changes and leaves a hint")
	ok(g3.st.flags.get("nova.x", 0) == 1, "a flag with a dot in its name is set")
	ok(Rules.cond(g3.st, [[["renyang", "<", 0]]]), "renyang can be read in a condition")
	ok(Rules.cond(g3.st, [[["line.cooper", "==", "none"]]]), "line state defaults to none")


func _film_talk(d) -> void:
	var g = Story.new_game(d, 1)
	var st = g.st
	Npcline.after_auditions(g.hooks, st, [{"rounds": [{"npc": "cooper", "score_line": [3, 1]}]}])
	ok(st.fired.get("film_cooper_rival_lose", 0) == 1 and st.fired.get("film_cooper_rival_win", 0) == 0, "winning a match against Cooper gives the 'he lost' small talk")
	Npcline.after_auditions(g.hooks, st, [{"rounds": [{"npc": "valen", "score_line": [1, 3]}]}])
	ok(st.fired.size() == 1, "a star without text gives no small talk")
	Npcline.costar(g.hooks, st, "iceberg")
	Npcline.costar(g.hooks, st, "iceberg")
	Npcline.costar(g.hooks, st, "iceberg")
	ok(st.fired.get("film_iceberg_costar_1", 0) == 1 and st.fired.get("film_iceberg_costar_2", 0) == 1, "co-star small talk plays 1 then 2, each once")


func _party(d) -> void:
	var g = Story.new_game(d, 3)
	var st = g.st
	_go_to(g, 1925, 2)                    # the month before the 1925-03 board
	Npcline.party_plan(st)
	ok(st.story.has("party"), "the month before a board has a party")
	var day: int = st.story["party"]["day"]
	ok(st.d.months[st.ym]["sundays"].has(day), "the party is on a Sunday")
	var per := -1
	for i in 3:
		for dd in Schedule.days_of(st, i):
			if dd[0] == day:
				per = i
	var fav0: Dictionary = st.favor.duplicate()
	Npcline.party_period(g.hooks, st, (per + 1) % 3)
	ok(not st.story["party"]["done"], "no party in another period")
	Npcline.party_period(g.hooks, st, per)
	ok(st.story["party"]["done"], "the party happens in its period")
	var gs: Array = st.story["last_party"]["guests"]
	ok(gs.size() == 2 and gs[0] != gs[1], "two different guests")
	var up := 0
	for x in gs:
		if st.favor[x] > fav0[x]:
			up += 1
		ok(st.known.has(x), "%s is met at the party" % x)
	ok(up == 2, "both guests like you more after the party")
	_go_to(g, 1925, 5)
	Npcline.party_plan(st)
	ok(not st.story.has("party"), "no party before a month without a board")
	var cast := []
	_go_to(g, 1925, 2)
	cast = Npcline.next_board_cast(st)
	ok(cast is Array, "next board cast is computed (%s)" % str(cast))


func _year_end(d) -> void:
	var g = Story.new_game(d, 1)
	var st = g.st
	_go_to(g, 1925, 12)
	Npcline.year_end(g.hooks, st)
	ok(st.fired.get("yearend_dancequeen_1", 0) + st.fired.get("yearend_sil_1", 0) + st.fired.get("yearend_generic", 0) >= 1, "a year-end talk happens")
	var g2 = Story.new_game(d, 1)
	_go_to(g2, 1928, 12)
	Npcline.year_end(g2.hooks, g2.st)
	ok(g2.st.fired.get("yearend_dancequeen_1", 0) == 0, "the dance queen is gone by 1928")


func _line(d) -> void:
	var g = Story.new_game(d, 1)
	var st = g.st
	_go_to(g, 1925, 4)
	st.favor["cooper"] = 59
	ok(not Npcline.contact_cross(g.hooks, st, "cooper"), "no line-crossing event under favor 60")
	st.favor["cooper"] = 60
	ok(Npcline.contact_cross(g.hooks, st, "cooper"), "favor 60 offers the line-crossing event")
	var ns := Npcline.npc_state(st, "cooper")
	ok(ns["line"] == "active" and ns["beat"] == 1, "the first option (cross) starts the line at beat 1")
	ok(not Npcline.contact_cross(g.hooks, st, "cooper"), "the crossing event is not offered again in an active line")
	Npcline.beat_period(g.hooks, st, 0)
	ok(not st.fired.has("beat_cooper_2"), "no beat in the month of crossing")
	_go_to(g, 1925, 6)
	Npcline.beat_period(g.hooks, st, 0)
	ok(st.fired.get("beat_cooper_2", 0) == 1, "beat 2 comes two months after")
	Npcline.beat_period(g.hooks, st, 1)
	ok(not st.fired.has("beat_cooper_3"), "one beat per period / cooldown again")
	_go_to(g, 1925, 8)
	Npcline.beat_period(g.hooks, st, 0)
	ok(not st.fired.has("beat_cooper_3"), "no beat in an occupied month (August)")
	_go_to(g, 1925, 10)
	Npcline.beat_period(g.hooks, st, 0)
	ok(st.fired.get("beat_cooper_3", 0) == 1, "beat 3 after the cooldown in a free month")
	# anchored beat: the dance queen's death point 1927-10 comes in a board-free month regardless of cooldown, earlier beats are dropped
	var g2 = Story.new_game(d, 1)
	var s2 = g2.st
	_go_to(g2, 1926, 5)
	s2.favor["dancequeen"] = 70
	Npcline.contact_cross(g2.hooks, s2, "dancequeen")
	_go_to(g2, 1927, 10)
	Npcline.beat_period(g2.hooks, s2, 0)
	ok(s2.fired.get("beat_dancequeen_5", 0) == 1 and not s2.fired.has("beat_dancequeen_2"), "the anchored beat comes in its month; unplayed earlier beats are dropped")
	# no line: she dies by default at the death point
	var g3 = Story.new_game(d, 1)
	_go_to(g3, 1927, 10)
	Npcline.beat_period(g3.hooks, g3.st, 0)
	ok(g3.st.flags.get("dance.dead", 0) == 1, "the dance queen dies in 1927-10 without a line")
	# a botched crossing puts favor under 60
	var g4 = Story.new_game(d, 1)
	_go_to(g4, 1925, 4)
	g4.st.favor["cooper"] = 80
	var e: Dictionary = g4.st.d.events["cross_cooper"]
	Rules.apply_effect(g4.st, e["options"][2]["success_effect"], "event")
	Npcline.apply_line(g4.st, e, e["options"][2])
	ok(g4.st.favor["cooper"] < 60 and Npcline.npc_state(g4.st, "cooper")["line"] == "none", "a botched crossing sends favor under 60 and starts nothing")


func _start(g, npc: String, favor := 70) -> void:
	g.st.favor[npc] = favor
	Npcline.contact_cross(g.hooks, g.st, npc)


func _showdown(d) -> void:
	var g = Story.new_game(d, 1)
	var st = g.st
	_go_to(g, 1925, 4)
	_start(g, "cooper")
	_start(g, "sweetheart")
	ok(st.fired.get("showdown_cooper_sweetheart", 0) == 1, "a second line with an 'accept' incumbent plays the showdown")
	ok(Npcline.npc_state(st, "sweetheart")["line"] == "broken" and Npcline.npc_state(st, "cooper")["line"] == "active", "the first option picks the incumbent: the new line breaks")
	# three lines: everybody at once, the 'reject' type is found out
	var g2 = Story.new_game(d, 1)
	var s2 = g2.st
	_go_to(g2, 1925, 4)
	_start(g2, "cooper")
	_start(g2, "vamp")                     # vamp is a reject type: cooper is an accept incumbent, so a showdown plays and breaks vamp's line
	_go_to(g2, 1925, 6)
	var g3 = Story.new_game(d, 2)
	var s3 = g3.st
	_go_to(g3, 1925, 4)
	_start(g3, "vamp")
	ok(not s3.fired.has("showdown_vamp_cooper"), "a 'reject' line alone: no showdown")
	_start(g3, "cooper")
	ok(not s3.fired.has("showdown_all") and Npcline.npc_state(s3, "vamp")["line"] == "active", "a reject incumbent does not find out at once")
	_start(g3, "iceberg")
	ok(s3.fired.get("showdown_all", 0) == 1, "three active lines: the all-hands showdown")
	ok(Npcline.npc_state(s3, "vamp")["line"] == "broken", "the all-hands showdown breaks the 'reject' line")
	# exposure by roll
	var g4 = Story.new_game(d, 5)
	var s4 = g4.st
	_go_to(g4, 1925, 4)
	s4.attr["fame"] = 900
	_start(g4, "vamp")
	_start(g4, "dancequeen")
	var n := 0
	while Npcline.npc_state(s4, "vamp")["line"] == "active" and n < 200:
		Npcline.exposure_roll(g4.hooks, s4, "vamp")
		n += 1
	ok(Npcline.npc_state(s4, "vamp")["line"] == "broken" and s4.fired.get("found_vamp", 0) == 1, "a 'reject' line is found out by the exposure roll (%d rolls)" % n)
	# special pair iceberg x gilbert: gilbert's line breaks at once
	var g5 = Story.new_game(d, 1)
	_go_to(g5, 1926, 4)
	_start(g5, "iceberg")
	_start(g5, "gilbert")
	ok(Npcline.npc_state(g5.st, "gilbert")["line"] == "broken" and Npcline.npc_state(g5.st, "iceberg")["line"] == "active", "iceberg x gilbert: gilbert breaks")
	# running away freezes both for a year, then 'why are you back'
	var g6 = Story.new_game(d, 1)
	_go_to(g6, 1925, 4)
	var e: Dictionary = g6.st.d.events["showdown_cooper_sweetheart"]
	_start(g6, "cooper")
	Npcline.npc_state(g6.st, "sweetheart")["line"] = "active"
	Npcline.apply_line(g6.st, e, e["options"][3])
	ok(Npcline.npc_state(g6.st, "cooper")["line"] == "frozen" and Npcline.npc_state(g6.st, "sweetheart")["line"] == "frozen", "running away freezes both lines")
	_go_to(g6, 1926, 3)
	Npcline.beat_period(g6.hooks, g6.st, 0)
	ok(Npcline.npc_state(g6.st, "cooper")["line"] == "frozen", "still frozen before the year is over")
	_go_to(g6, 1926, 4)
	Npcline.beat_period(g6.hooks, g6.st, 0)
	ok(Npcline.npc_state(g6.st, "cooper")["line"] == "active" and g6.st.fired.get("back_cooper", 0) == 1, "after the year the line thaws with the 'why are you back' line")


func _ending(d) -> void:
	var g = Story.new_game(d, 1)
	var st = g.st
	_go_to(g, 1925, 4)
	_start(g, "novaro")
	st.flags["nova.soldConfession"] = 1
	var r: Array = Npcline.rumors(st, "end_x")
	ok(r.size() == 1 and str(r[0]).find("忏悔录") >= 0, "a flag override replaces the tier rumor")
	st.flags.erase("nova.soldConfession")
	r = Npcline.rumors(st, "end_x")
	ok(r.size() == 1, "one rumor per live line (%s)" % str(r))
	ok(Npcline.rumor_tier(st, "end_underworld") == "crime", "the underworld ending is the crime emperor tier")
	Npcline.npc_state(st, "novaro")["line"] = "broken"
	ok(Npcline.rumors(st, "end_x").is_empty(), "a broken line has no rumor")
	# the studio offer
	var g2 = Story.new_game(d, 1)
	g2.st.attr["fame"] = 200
	Npcline.studio_offer(g2.hooks, g2.st)
	ok(g2.st.story.get("studio") == null and not g2.st.story.has("studio_asked"), "no studio offer under fame 300")
	g2.st.attr["fame"] = 320
	Npcline.studio_offer(g2.hooks, g2.st)
	ok(g2.st.story.has("studio_asked"), "the offer is made at fame 300 (the default agent says not now)")
