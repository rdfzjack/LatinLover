extends "res://core/story.gd"
## The Story the UI plays: the same script, plus a call to the UI after each period (shooting periods included) so the
## player sees the periods one by one. ui is main.gd; its period_done() blocks until the player presses "continue".
## Also holds UiAgent, the questions of the script turned into prompts on the screen (the answers come from main.gd's ask()).

const StoryBase = preload("res://core/story.gd")

var ui


func _init(ag = null, ui_node = null) -> void:
	super(ag)
	ui = ui_node


## The board: same flow as Board.run, but every audition ends with a result screen.
func board(st) -> void:
	Board.make(st)
	var out := []
	while true:
		var b: Dictionary = Board.board(st)
		var ok := []
		for i in b["roles"].size():
			if Board.can_try(st, i) == "":
				ok.append(i)
		if ok.is_empty():
			break
		var pick = agent.pick_role(st, b, ok)
		if pick == null:
			break
		var res: Dictionary = Board.try_role(st, pick, agent)
		out.append(res)
		ui.ask("notice", ui.audition_text(b["roles"][pick], res))
	boards.append({"month": st.date(), "audition": out})


## Swap role / steal role happen inside Events.period_start; tell the player how the match went.
func period_start(st, i: int, entry: String) -> void:
	var films: Array = st.story["films"]
	var n0: int = films.size()
	var l0: int = event_log.size()
	var stolen0 := 0
	var first_name := ""
	for f in films:
		if f["status"] == "stolen":
			stolen0 += 1
	for f in films:
		if f["status"] == "to_shoot":
			first_name = str(f["roles"]["name"])
			break
	super(st, i, entry)
	for k in range(l0, event_log.size()):
		var id: String = event_log[k]["id"]
		if id == "evt_swap_role":
			if films.size() > n0:
				ui.ask("notice", "临时换角的试镜：赢了！接下了《%s》，下一旬去拍。" % films[films.size() - 1]["roles"]["name"])
			else:
				ui.ask("notice", "临时换角的试镜：输了，没拿到。")
		elif id == "evt_steal_role":
			var stolen1 := 0
			for f in films:
				if f["status"] == "stolen":
					stolen1 += 1
			if stolen1 > stolen0:
				ui.ask("notice", "有人来抢《%s》的角色，你输了，角色被抢走了，片约作废。" % first_name)
			else:
				ui.ask("notice", "有人来抢《%s》的角色，你赢了，角色保住了。" % first_name)


func film_period(st, i: int, f, days: Array) -> void:
	var d0: int = f["shoot_days"]
	var k0: int = f["ok_days"]
	super(st, i, f, days)
	ui.period_done(st, i, "shooting", {"film": f["roles"]["name"], "days": f["shoot_days"] - d0, "ok": f["ok_days"] - k0})


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
		# the activity of this period is picked now, one period at a time (run_month reads plan[i] right after this hook)
		if story.locked(st, i) == null and not ui.month_forced:
			ui.cur_plan[i] = ui.ask("pick_period", i)
		if Events.boost_reason(st, i) == "" and ui.ask("boost", i):
			var why: String = story.boost(st, i)
			if why != "":
				ui.note("用药失败：" + why)
