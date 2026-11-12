extends RefCounted
## Explains the dice: why a day of class, work or shooting succeeds or fails, and what the two indices (sick, reckless) mean.
## The formulas are the ones of core/schedule.gd (practice_ok, job_day_ok, extra_fail) and core/film.gd (shoot); they are only
## read here, never changed. If the numbers in extra_fail change there, change SLACK_* and LOVE_FAIL_PCT here.

const SLACK_HIGH := [30, 80]    # reckless index >= 30: 80% of the working and shooting days are skipped
const SLACK_LOW := [10, 40]     # reckless index >= 10: 40%
const LOVE_FAIL_PCT := 20       # in love: 20% of the days fail

var m               # main.gd (names, state, data)


func _init(main) -> void:
	m = main


## P(stat - r0(fatigue) >= line), r0(f) is uniform on 0..f.
func p_line(stat: int, line: int, fatigue: int) -> float:
	var room := stat - line
	if room < 0:
		return 0.0
	return float(mini(fatigue, room) + 1) / float(fatigue + 1)


## P(stamina/2 + r0(stamina/2) >= r0(fatigue)).
func p_practice(stamina: int, fatigue: int) -> float:
	var half := stamina / 2
	var total := 0.0
	for a in range(half + 1):
		total += float(mini(fatigue, half + a) + 1) / float(fatigue + 1)
	return total / float(half + 1)


## The chance that the day is not thrown away by being in love or being reckless (jobs and shooting only skip when reckless).
func p_no_extra_fail(job: bool) -> float:
	var st = m.st
	var p := 1.0
	if st.status["in_love"]:
		p *= 1.0 - LOVE_FAIL_PCT / 100.0
	if job:
		p *= 1.0 - slack_pct() / 100.0
	return p


func slack_pct() -> int:
	var w: int = m.st.idx["reckless_index"]
	if w >= SLACK_HIGH[0]:
		return SLACK_HIGH[1]
	if w >= SLACK_LOW[0]:
		return SLACK_LOW[1]
	return 0


func pct(p: float) -> String:
	return "%d%%" % int(round(p * 100.0))


## Text of the extra ways to fail (in love, reckless).
func extra_text(job: bool) -> String:
	var parts := PackedStringArray()
	if m.st.status["in_love"]:
		parts.append(tr("ui.explain.extra_text.1") % LOVE_FAIL_PCT)
	if job and slack_pct() > 0:
		parts.append(tr("ui.explain.extra_text.2") % [m.st.idx["reckless_index"], slack_pct()])
	return tr("ui.main.entry_effect.14").join(parts)


## Practice (class, book): one line with the chance per day and what it depends on.
func practice_text(stamina: int, fatigue: int) -> String:
	var p := p_practice(stamina, fatigue)
	return tr("ui.explain.practice_text.1") % [pct(p * p_no_extra_fail(false)), stamina, fatigue]


## Work and shooting: lines = [[stat id, line], ...]. Each line is its own roll: stat - random(0~fatigue) >= line.
func work_text(lines: Array, fatigue: int, job: bool) -> String:
	var st = m.st
	var b: Dictionary = st.bonus()
	var p := 1.0
	var parts := PackedStringArray()
	for x in lines:
		var stat: int = st.val(x[0], b)
		var pl := p_line(stat, int(x[1]), fatigue)
		p *= pl
		parts.append(tr("ui.explain.work_text.1") % [m.nm(x[0]), stat, fatigue, int(x[1]), pct(pl)])
	var extra := extra_text(job)
	var t := tr("ui.explain.work_text.2") % pct(p * p_no_extra_fail(job)) + tr("ui.main.entry_effect.14").join(parts) + tr("ui.board.show_board.13")
	if extra != "":
		t += tr("ui.main.entry_effect.14") + extra
	return t


## Shooting of a film of this size: the line comes from the table, the fatigue grows by the shooting itself each day.
func shoot_text(size: String, fatigue: int) -> String:
	var c: Dictionary = m.d.role_cfg["shoot"]
	var line: int = c["success_lines"][size]
	return work_text([["stamina", line]], fatigue, true) + tr("ui.explain.shoot_text.1") % int(c["fatigue"][size])


## What the two indices are and what they do, for the status page and the tooltip of the status bar.
func index_text() -> String:
	var st = m.st
	var b: Dictionary = st.bonus()
	var f: int = st.val("fatigue", b)
	var sick: int = st.idx["sick_index"]
	var wild: int = st.idx["reckless_index"]
	var s := tr("ui.explain.index_text.1") % [
		f, st.val("stamina", b), sick, int(m.d.idx_rule["sick_index"]["status_line"]), int(m.d.idx_rule["sick_index"]["very_sick_line"])]
	s += tr("ui.explain.index_text.2") % [
		f, st.val("discipline", b), wild, int(m.d.idx_rule["reckless_index"]["status_line"]), SLACK_LOW[0], SLACK_LOW[1], SLACK_HIGH[0], SLACK_HIGH[1]]
	s += tr("ui.explain.index_text.3")
	return s
