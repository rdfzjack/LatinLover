extends "res://core/month.gd".Hooks
## Connects board, film, events and ending to the month flow: this script implements Month.Hooks; Agent is the questions the
## player (UI or bot) must answer. Port of sim/story.py.
##
## Usage:
##   var g = Story.new_game(data, seed, [0, 1, 2], agent)     # a Month whose hooks are a Story (agent null = SimpleAgent)
##   while not g.st.finished:
##       g.start_month()                  # living costs, board (agent signs up, plays), agent.month_start
##       g.run_month(plan)                # the three periods; periods locked by shooting ignore the plan
##   g.st.story["ending"]
## Python raises on a month-start action that cannot be done; here write_script / send_detox / leak_news return "" or the reason.
## Python's Story.log is event_log here (`log` is a built-in function).

const Month = preload("res://core/month.gd")
const Rules = preload("res://core/rules.gd")
const Schedule = preload("res://core/schedule.gd")
const Audition = preload("res://core/audition.gd")
const Board = preload("res://core/board.gd")
const Film = preload("res://core/film.gd")
const Events = preload("res://core/events.gd")
const Ending = preload("res://core/ending.gd")


## The decisions the player has to make. The UI and bots implement these methods; see SimpleAgent for the defaults.
## deck and play (auditions) are inherited from Audition.Player.
class Agent:
	extends Audition.Player

	## Board: pick one of the signable indexes ok to audition for; null means stop trying. b = st.story["board"].
	func pick_role(_st, _b: Dictionary, _ok: Array):
		return null

	## On a narrow loss: whether to take a supporting part in the same film.
	func accept_support(_st, _role: Dictionary) -> bool:
		return false

	## Board with nothing the player can sign up for: only shown (roles greyed out with the reason).
	func view_board(_st, _b: Dictionary) -> void:
		pass

	## Swap role / steal role (GDD 11.1): shown before the audition; returns whether to play it.
	## kind "swap": declining means no audition. kind "steal": only shown, it cannot be declined (the answer is ignored).
	## info: {role, rival, period: [month index, period] the swap role would take (swap only)}.
	func role_event(_st, _kind: String, _info: Dictionary) -> bool:
		return true

	## When a role that allows stunt_self is won: whether to do it yourself.
	func go_personally(_st, _role: Dictionary) -> bool:
		return false

	## Event option: avail is the list of pickable option indexes; returns one of them.
	func option(_st, _ev: Dictionary, avail: Array) -> int:
		return avail[0]

	## Annual event: returns the occasion id; null means rest.
	func annual(_st, _opts: Array):
		return null

	## Studio boss backs transition: returns a tag family name (tag_families of endings.json).
	func family(st) -> String:
		return st.d.tag_families.keys()[0]

	## Whether to suppress a scandal: kind is "free" or "paid" (200).
	func suppress(_st, _kind: String) -> bool:
		return false

	## Free actions at the start of the month: story.write_script / send_detox / leak_news, the street etc. (no schedule slot).
	func month_start(_story, _st) -> void:
		pass

	## Step 12c: free actions just before period i (not void, not detained; shooting periods included): story.boost(st, i).
	func before_period(_story, _st, _i: int) -> void:
		pass


## The simplest player, for tests:
##   deck: main color (highest level) 3 cards + the color with the second-highest level 2 cards; plays at random with the logic stream;
##   signs up for the first role of the highest signable size; takes supporting parts; does the stunt when possible; picks the first
##   pickable event option; annual event: attends the road with the highest reputation; transition picks the first family;
##   suppresses a scandal when possible; does nothing else at month start.
class SimpleAgent:
	extends Agent

	func deck(_st, ctx) -> Array:
		var lv: Array = ctx["levels"]
		var order := [0, 1, 2, 3]
		order.sort_custom(func(a, b): return lv[a] > lv[b] if lv[a] != lv[b] else a < b)
		return [order[0], order[0], order[0], order[1], order[1]]

	func play(st, ctx) -> int:
		return st.rng.logic.below(ctx["hand"].size())

	func pick_role(_st, b: Dictionary, ok: Array):
		var best = null
		for i in ok:
			if best == null or Board.RANK[b["roles"][i]["size"]] > Board.RANK[b["roles"][best]["size"]]:
				best = i
		return best

	func accept_support(_st, _role: Dictionary) -> bool:
		return true

	func go_personally(_st, _role: Dictionary) -> bool:
		return true

	func annual(st, opts: Array):
		var b: Dictionary = st.bonus()
		var best = null
		var bv := 0
		for x in opts:
			var v: int = st.rep(x["road"], b)
			if best == null or v > bv:
				best = x
				bv = v
		return best["id"]

	func suppress(_st, _kind: String) -> bool:
		return true


var agent
var cur_period := 0
var event_log := []    # records of the events fired in this game (not saved; Python Story.log)
var boards := []       # audition results of each board (not saved)
var annuals := []      # annual event records (not saved)


func _init(ag = null) -> void:
	Ending.register()
	agent = ag if ag != null else SimpleAgent.new()


## A new game (a Month) with a Story as its hooks.
static func new_game(data, sd := 1, origin := [0, 0, 0], ag = null):
	return Month.new(data, sd, origin, load("res://core/story.gd").new(ag))


## Replaces the entries of a fixed schedule that cannot be scheduled this month with resting at home
## (sick cannot go out, book finished, job not unlocked ...).
static func fit_plan(g, plan: Array) -> Array:
	var out := []
	for i in plan.size():
		if g.hooks.locked(g.st, i) != null or Schedule.validate(g.st, plan[i]) == "":
			out.append(plan[i])
		else:
			out.append("rest_home")
	return out


# ---------- event notifications (step 15: the UI shows a dialog; no effect on the game) ----------

## An event is about to be settled (called by Events.fire; triggered events nest).
func event_begin(_st, _eid: String) -> void:
	pass


## The event is settled: rec is its record {id, month, check?, options?}.
func event_end(_st, _rec: Dictionary) -> void:
	pass


# ---------- month start ----------

func board(st) -> void:
	Board.make(st)
	boards.append({"month": st.date(), "audition": Board.run(st, agent)})


func month_start(st) -> void:
	Events.dealer_month(st)
	agent.month_start(self, st)


# month-start actions (called by the player); each returns "" or the reason it cannot be done

func write_script(st, kind: String, color := -1) -> String:
	return Board.write_script(st, kind, color)


## Send to detox: allowed once he is addicted (drug_stage >= 1); the withdrawal event fires at the end of that month.
func send_detox(st) -> String:
	if st.drug < 1:
		return "not addicted"
	st.flags["detox_sent"] = 1
	return ""


## Take a dose (step 12c c3, stats.drug): a free action before period i; returns "" or the reason.
func boost(st, i: int) -> String:
	return Events.boost(st, i)


## Buy n doses from the dealer when he is around this month (month start); returns "" or the reason.
func buy_drug(st, n: int) -> String:
	return Events.buy_drug(st, n)


## Newspaper line favor 80: one news leak per year, fame +10%, counts as exposure.
func leak_news(st) -> String:
	var y: int = Rules.fdiv(st.ym, 12) + 1
	if not Schedule.truthy(st.flags.get("leak_news")) or st.story["leak_year"] == y:
		return "cannot leak news now"
	st.story["leak_year"] = y
	Events.fame_pct(st, 10)
	st.exposed = 1
	return ""


# ---------- the three periods ----------

func locked(st, i: int):
	return Film.locked(st, i)


func film_period(st, i: int, f, days: Array) -> void:
	Film.shoot(st, i, f, days)


func film_breach(st) -> void:
	Film.breach_month(st, st.ym + 1)


func before_period(st, i: int) -> void:
	cur_period = i
	st.status["drug_high"] = 0
	agent.before_period(self, st, i)
	Events.drug_period(st, i)


func period_start(st, i: int, _entry: String) -> void:
	cur_period = i


func period_end(st, i: int, entry: String, out: Dictionary) -> void:
	Events.period_end(self, st, i, entry, out)
	after_period(st, i, entry, out)


## The checks of GDD 11.1 (swap role, steal role) happen at the END of the period (step 15c; they used to run before it).
func after_period(st, i: int, entry: String, _out: Dictionary) -> void:
	Events.period_check(self, st, i, entry)


func day(st, dd: int) -> void:
	Events.day(self, st, dd)


func outing(st, place: String) -> void:
	Events.outing(self, st, place)


func class_chain(st, chain, n: int) -> void:
	Events.class_chain(self, st, chain, n)


func book_done(st, bid: String) -> void:
	Events.book_done(self, st, bid)


func job_period(st, jid: String, good: bool) -> void:
	Events.job_period(self, st, jid, good)


# ---------- month end, settlement ----------

func month_events(st) -> void:
	cur_period = 3          # an arrest at month end detains the first period of next month
	Events.drug_month(st)
	Events.month_end(self, st)


func discharge(st) -> void:
	Events.discharge(self, st)


func release(st) -> void:
	Film.release(st)


## Named rivals switch stage by the `from` date of rivals.json, unnamed rivals by the half-year count; nothing extra in October.
func rival_growth(_st) -> void:
	pass


func annual(st) -> void:
	Events.annual(self, st)


func era(st, ids) -> void:
	Events.era(self, st, ids)


func ending(st) -> void:
	Ending.judge(st)
