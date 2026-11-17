extends SceneTree
## Checks of the NPC event system (core/npcline.gd). Run from the repository root:
##   godot --headless --path game/silentstar --script res://tools/npc_test.gd
## Prints OK lines and one FAIL line per problem; exit code 1 when anything fails.

const Data = preload("res://core/data.gd")
const Story = preload("res://core/story.gd")
const Npcline = preload("res://core/npcline.gd")
const Rules = preload("res://core/rules.gd")
const State = preload("res://core/state.gd")

var fails := 0


func _init() -> void:
	var root := ProjectSettings.globalize_path("res://").path_join("../..").simplify_path()
	var d = Data.new(root.path_join("data/new"))
	_dice(d)
	_blocked(d)
	_encounter(d)
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
