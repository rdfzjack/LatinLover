extends RefCounted
## Month flow (GDD 4): month start, three periods, month-end events, month settlement. Port of sim/month.py.
##
## Everything step 12 plugs in (board, period-start checks, shooting, events, releases, rivals, annual events, era events, endings)
## is a method of Hooks; by default they do nothing here.
##
## Usage:
##   var g = Month.new(data, seed, [0, 1, 2])
##   while not g.st.finished:
##       g.start_month()                      # charge living costs, build the board
##       g.run_month(["class_acting", "job_dock", "rest_home"])   # returns [] or the list of schedule errors (nothing ran then)

const State = preload("res://core/state.gd")
const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")
const Film = preload("res://core/film.gd")


## The parts implemented in step 12. Every method gets the state and may change it. A subclass overrides what it needs.
class Hooks:
	extends RefCounted
	func board(_st) -> void: pass                         # the board in the audition months (board_month)
	func month_start(_st) -> void: pass                   # before the free actions of the month (write script, send to detox ...)
	func locked(_st, _i: int):                            # returns the film contract when period i is locked by shooting, else null
		return null
	func film_period(_st, _i: int, _film, _days: Array) -> void: pass    # shooting period
	func film_breach(_st) -> void: pass                   # very sick: the shoots already locked for next month breach
	func before_period(_st, _i: int) -> void: pass        # step 12c: before period i (not void, not detained), shooting or not: free actions such as the boost
	func period_start(_st, _i: int, _entry: String) -> void: pass        # period-start checks: swap role, steal role (11.1)
	func period_end(_st, _i: int, _entry: String, _out: Dictionary) -> void: pass   # after a period's schedule is done
	func day(_st, _day: int) -> void: pass                # per-day events such as birthdays
	func outing(_st, _place: String) -> void: pass        # outing event (5.5.2)
	func class_chain(_st, _chain, _n: int) -> void: pass  # Duv's story in tutoring (period n)
	func book_done(_st, _bid: String) -> void: pass       # finish-reading event
	func job_period(_st, _jid: String, _good: bool) -> void: pass        # job hook: period_random, milestones
	func month_events(_st) -> void: pass                  # month-end events (11.2)
	func release(_st) -> void: pass                       # release settlement (8)
	func rival_growth(_st) -> void: pass                  # rival table swap in October
	func annual(_st) -> void: pass                        # annual event in December
	func era(_st, _ids) -> void: pass                     # era events
	func ending(_st) -> void: pass                        # ending resolution in 1929-12
	func discharge(_st) -> void: pass                     # step 12c: after a month with a sanatorium period (discharge event)


var d
var st
var hooks
var started := false
var last := []                 # summary of each period of this month
# What run_month remembers across its periods (step 15d: a game can be saved before period i and resumed there, see carry()).
var m_forced := 0              # this month is the forced sanatorium month
var m_void := 0                # this month's schedule is void
var m_sanatorium := false      # a sanatorium period already happened this month


func _init(data, sd := 0, origin := [0, 0, 0], hk = null, state = null) -> void:
	d = data
	if state != null:
		st = state
	else:
		st = State.new(data)
		st.start(sd, origin)
	hooks = hk if hk != null else Hooks.new()


# ---------- 1. month start ----------

func start_month() -> void:
	if st.finished:
		push_error("this game is already over")
		return
	if started:
		push_error("the month has already started")
		return
	started = true
	st.month_used = {}
	st.exposed = 0
	st.status["shoot_this_month"] = 0
	# stamina <15 and the lifestyle is not fine: forced back to fine (GDD 5.7)
	if st.val("stamina") < 15 and st.lifestyle != "life_fine":
		st.lifestyle = "life_fine"
	var life: Dictionary = d.lifestyles[st.lifestyle]
	st.money = maxi(0, st.money - life["monthly_cost"][st.fame_tier()])      # six-year swap: money stops at 0
	if board_month(st):
		hooks.board(st)
	hooks.month_start(st)


## Fixed boards (user): the 15 audition months are the calendar's `board` months (the months of roles.json board_schedule).
static func board_month(st) -> bool:
	return Schedule.truthy(st.month()["board"])


## Changes the lifestyle before scheduling at month start; takes effect when it is charged next month.
func set_lifestyle(lid: String) -> void:
	if not d.lifestyles.has(lid):
		push_error("no such lifestyle %s" % lid)
		return
	st.lifestyle = lid


# ---------- 2. the three periods ----------

## Checks this month's schedule and returns [[period, reason], ...] (period -1 = the whole plan).
## Months with a shoot lock, forced sanatorium or void schedule are not checked.
func plan_errors(plan: Array, from_period := 0) -> Array:
	if from_period == 0 and (st.forced_rest or st.void_next):
		return []
	if from_period > 0 and (m_forced or m_void):
		return []
	if plan.size() != 3:
		return [[-1, "need 3 periods"]]
	var out := []
	for i in range(from_period, plan.size()):
		if hooks.locked(st, i) != null:
			continue
		var r: String = Schedule.validate(st, plan[i])
		if r != "":
			out.append([i, r])
	return out


## What the screen has to keep to resume a month at period i (with the saved state): see run_month(plan, from_period, carry).
func carry() -> Dictionary:
	return {"forced": m_forced, "void": m_void, "sanatorium": m_sanatorium}


## Runs the month. Returns the schedule errors when the plan cannot be used (then nothing has run), otherwise [].
## Resuming a saved month (step 15d): from_period = the period to continue with, carry = what carry() returned when saving; the state
## is the saved one and the earlier periods are not run again.
func run_month(plan: Array, from_period := 0, carried := {}) -> Array:
	if not started:
		start_month()
	if from_period > 0:
		m_forced = int(carried.get("forced", 0))
		m_void = int(carried.get("void", 0))
		m_sanatorium = bool(carried.get("sanatorium", false))
	var errs := plan_errors(plan, from_period)
	if not errs.is_empty():
		return errs
	if from_period == 0:
		m_forced = st.forced_rest
		m_void = st.void_next
		m_sanatorium = false
		st.forced_rest = 0
		st.void_next = 0
		last = []
	var forced: int = m_forced
	var void_: int = m_void
	for i in range(from_period, 3):
		var days := Schedule.days_of(st, i)
		if void_:
			last.append({"schedule": "void"})
			continue
		var ab: int = st.ym * 3 + i
		if st.void_periods.has(ab):          # detention (step 12c): this period is void; a shoot locked here breaches
			st.void_periods.erase(ab)
			Film.breach_period(st, st.ym, i)
			st.inc("count.void.detained")
			last.append({"schedule": "detained"})
			continue
		hooks.before_period(st, i)
		var film = hooks.locked(st, i)
		if film != null:
			st.status["shooting_period"] = 1
			st.status["shoot_this_month"] = 1
			hooks.film_period(st, i, film, days)
			st.status["shooting_period"] = 0
			last.append({"schedule": "shooting"})
			continue
		var e: String = plan[i] if not forced else _forced_entry(i)
		if e == "rest_sanatorium":
			m_sanatorium = true
			st.inc("count.void.sanatorium")
		hooks.period_start(st, i, e)
		var out := Schedule.run_period(st, i, e, hooks)
		hooks.period_end(st, i, e, out)
		last.append(out)
	if m_sanatorium:                       # discharge (step 12c): side effects, then the discharge event roll
		st.inc("count.sanatorium")
		var f: Dictionary = d.rest_forced[0]
		if Schedule.truthy(f.get("discharge_effect")):
			Rules.apply_effect(st, f["discharge_effect"], "schedule")
		hooks.discharge(st)
	if st.flags.get("accent_period", 0) > 0:      # 4-month bonus after the accent event, one less after each month
		st.flags["accent_period"] -= 1
	hooks.month_events(st)
	end_month()
	return []


## The month after very sick: sanatorium; when the money for that period cannot pay 8 a day it falls back to resting at home (GDD 10).
func _forced_entry(i: int) -> String:
	var f: Dictionary = d.rest_forced[0]
	var need: int = d.rests[f["schedule"]]["cost"] * Schedule.days_of(st, i).size()
	return f["schedule"] if st.money >= need else f["if_broke_switch"]


# ---------- 4. month settlement ----------

func end_month() -> void:
	var m: Dictionary = st.month()
	# 1 lifestyle
	var eff = d.lifestyles[st.lifestyle]["month_end_effect"]
	if Schedule.truthy(eff):
		Rules.apply_effect(st, eff, "schedule")
	# 2 releases
	hooks.release(st)
	# 3 fame decay
	if not st.exposed:
		var fr: Dictionary = d.t["stats"]["fame_rules"]
		var f: int = st.attr["fame"]
		st.attr["fame"] = maxi(0, f - maxi(fr["monthly_decay_min"], Rules.fdiv(f * fr["monthly_decay_pct"], 100)))
	# 4 indices and status
	st.update_indices()
	# 5 very sick, collapse
	if st.status["very_sick"]:
		st.forced_rest = 1
		hooks.film_breach(st)
	st.collapse_months = st.collapse_months + 1 if st.idx["sick_index"] >= 100 else 0
	if st.collapse_months >= 2:
		st.ended = "end_collapse"
		st.finished = 1
		hooks.ending(st)
		started = false
		return
	# 6 in_love timer
	var rr: Dictionary = d.t["romance"]["rules"]["love_state"]
	if st.status["in_love"]:
		st.romance_months += 1
		for n in rr["lines"]:
			st.favor[n] = maxi(0, st.favor.get(n, 0) + rr["monthly_favor"])
		if st.romance_months >= rr["duration_months"] and st.highest_base() != "looks":
			st.status["in_love"] = 0
			st.romance_months = 0
	# 7 debt
	st.debt_months = st.debt_months + 1 if st.money < 0 else 0
	# 8-11
	if Schedule.truthy(m["rival_growth"]):
		hooks.rival_growth(st)
	if Schedule.truthy(m["annual"]):
		hooks.annual(st)
	if Schedule.truthy(m["era_events"]):
		hooks.era(st, m["era_events"])
	if Schedule.truthy(m["ending_check"]):
		hooks.ending(st)
		st.finished = 1
	started = false
	if not st.finished:
		st.ym += 1
		if st.ym >= d.months.size():
			st.finished = 1


# ---------- save / load ----------

## Saving is only allowed between two months. Returns "" (and reports an error) in the middle of a month.
func save() -> String:
	if started:
		push_error("saving is only allowed between two months")
		return ""
	return st.dumps()


## Builds a Game from a save string; returns null when the save cannot be read.
static func restore(s: String, data, hk = null):
	var state = State.new(data)
	if not state.loads(s):
		return null
	return load("res://core/month.gd").new(data, 0, [0, 0, 0], hk, state)


# ---------- reconciliation output ----------

## One line per month: date, money, 8 attributes, 12 training values, 4 road reputations, the two indices, logic stream state.
## st.date() is already next month after settlement, so the caller passes the date.
static func trace_line(st, date = null) -> String:
	var d = st.d
	var a := PackedStringArray()
	for k in d.attrs:
		a.append(str(st.attr[k]))
	var s := PackedStringArray()
	for k in d.skills:
		s.append(str(st.skill[k]))
	var b: Dictionary = st.bonus()
	var r := PackedStringArray()
	for k in d.roads:
		r.append(str(st.rep(k, b)))
	var dt: String = date if date != null else st.date()
	return "%s $%d | %s | %s | %s | %d %d | %s" % [dt, st.money, " ".join(a), " ".join(s), " ".join(r),
		st.idx["sick_index"], st.idx["reckless_index"], st.rng.logic.dump()[0]]
