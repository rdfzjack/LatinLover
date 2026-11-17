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
