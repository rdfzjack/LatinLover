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
		ui.ask("notice", {"text": ui.audition_text(b["roles"][pick], res), "cue": "audition_win" if res["result"] == "won" else "audition_lose"})
	boards.append({"month": st.date(), "audition": out})


## Month-end releases: the films' results change the reputation bonus; the screen writes down how much and why.
func release(st) -> void:
	super(st)
	ui.after_release()


func event_begin(_st, eid: String) -> void:
	ui.event_started(eid)


func event_end(_st, rec: Dictionary) -> void:
	ui.event_ended(rec)


## December: the result page of the annual event.
func annual(st) -> void:
	super(st)
	ui.log_corr(tr("ui.main.show_annual_result.1"))
	ui.ask("annual_result", annuals.back())


## End of a period: first the report of the period, then the checks of GDD 11.1 (swap role, steal role) with the result of the match.
func after_period(st, i: int, entry: String, out: Dictionary) -> void:
	ui.period_done(st, i, entry, out)
	var films: Array = st.story["films"]
	var n0: int = films.size()
	var l0: int = event_log.size()
	var stolen0 := 0
	var declined0: int = st.cnt("count.swap_declined")
	var first_name := ""
	for f in films:
		if f["status"] == "stolen":
			stolen0 += 1
	for f in films:
		if f["status"] == "to_shoot":
			first_name = str(f["roles"]["name"])
			break
	super(st, i, entry, out)
	for k in range(l0, event_log.size()):
		var id: String = event_log[k]["id"]
		if id == "evt_swap_role":
			if films.size() > n0:
				ui.ask("notice", tr("ui.story.period_start.1") % films[films.size() - 1]["roles"]["name"])
			elif st.cnt("count.swap_declined") > declined0:
				pass                                  # declined (or blocked by a status trait): nothing to report
			else:
				ui.ask("notice", tr("ui.story.period_start.2"))
		elif id == "evt_steal_role":
			var stolen1 := 0
			for f in films:
				if f["status"] == "stolen":
					stolen1 += 1
			if stolen1 > stolen0:
				ui.ask("notice", tr("ui.story.period_start.3") % first_name)
			else:
				ui.ask("notice", tr("ui.story.period_start.4") % first_name)


## He ran off (GDD 5.1.1): told right after the period was picked, before the period runs.
func slacked(st, i: int, planned: String, entry: String) -> void:
	var what: String = tr("ui.story.slack.shooting") if planned == "shooting" else ui.nm(Schedule.parse_entry(planned)[1])
	var pe := Schedule.parse_entry(entry)
	var where: String = ui.nm(pe[2]) if pe.size() == 3 and pe[2] != null else ui.nm(pe[1])
	var t: String = tr("ui.story.slack.1") % [what, where]
	if planned == "shooting":
		for f in st.story["films"]:
			if f["status"] == "skipped" and int(f.get("skipped_ym", -1)) == st.ym:
				t += tr("ui.story.slack.film_gone") % str(f["roles"]["name"])
	ui.ask("notice", t)


func film_period(st, i: int, f, days: Array) -> void:
	var d0: int = f["shoot_days"]
	var k0: int = f["ok_days"]
	super(st, i, f, days)
	ui.period_done(st, i, "shooting", {"film": f["roles"]["name"], "size": f["size"], "days": f["shoot_days"] - d0, "ok": f["ok_days"] - k0})


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

	func view_board(st, b: Dictionary) -> void:
		ui.ask("pick_role", {"board": b, "ok": []})

	func role_event(st, kind: String, info: Dictionary) -> bool:
		var p := info.duplicate()
		p["kind"] = kind
		return ui.ask("role_event", p)

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
		# a dose: chosen on the map for this period (user: no question before every period); only a shooting period, which has
		# no map, still asks, and only when he has a dose in hand
		var picked := false
		var shooting: bool = story.locked(st, i) != null
		if not shooting and not ui.month_forced:
			ui.cur_plan[i] = ui.ask("pick_period", i)
			picked = ui.boost_pick == i
		ui.boost_pick = -1
		if Events.boost_reason(st, i) == "" and (picked or (shooting and ui.ask("boost", i))):
			var why: String = story.boost(st, i)
			if why != "":
				ui.note(tr("ui.story.before_period.1") + why)
