extends "res://core/story.gd"
## The Story the UI plays: the same script, plus a call to the UI after each period (shooting periods included) so the
## player sees the periods one by one. ui is main.gd; its period_done() blocks until the player presses "continue".
## Also holds UiAgent, the questions of the script turned into prompts on the screen (the answers come from main.gd's ask()).

const StoryBase = preload("res://core/story.gd")

var ui


func _init(ag = null, ui_node = null) -> void:
	super(ag)
	ui = ui_node


func film_period(st, i: int, f, days: Array) -> void:
	super(st, i, f, days)
	ui.period_done(st, i, "shooting", {"film": f["roles"]["name"]})


func period_end(st, i: int, entry: String, out: Dictionary) -> void:
	super(st, i, entry, out)
	ui.period_done(st, i, entry, out)


## Every question of the script is a blocking prompt in the UI (ask runs on the game thread and waits for the screen).
class UiAgent:
	extends StoryBase.Agent
	var ui

	func _init(ui_node) -> void:
		ui = ui_node

	func deck(st, ctx) -> Array:
		return ui.ask("deck", ctx)

	func play(st, ctx) -> int:
		return ui.ask("play", ctx)

	func pick_role(st, b: Dictionary, ok: Array):
		return ui.ask("pick_role", {"board": b, "ok": ok})

	func accept_support(st, role: Dictionary) -> bool:
		return ui.ask("support", role)

	func go_personally(st, role: Dictionary) -> bool:
		return ui.ask("stunt", role)

	func option(st, ev: Dictionary, avail: Array) -> int:
		return ui.ask("option", {"event": ev, "avail": avail})

	func annual(st, opts: Array):
		return ui.ask("annual", opts)

	func family(st) -> String:
		return ui.ask("family", null)

	func suppress(st, kind: String) -> bool:
		return ui.ask("suppress", kind)

	func before_period(story, st, i: int) -> void:
		if Events.boost_reason(st, i) == "" and ui.ask("boost", i):
			var why: String = story.boost(st, i)
			if why != "":
				ui.note("用药失败：" + why)
