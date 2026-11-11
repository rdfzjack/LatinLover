extends SceneTree
## Step 9 reconciliation: prints the random-number sequences, save round trips, and the results of conditions and effects,
## following tools/trace_cases.json. The output must be byte-identical to the Python tools/trace.py. From the repository root:
##
##   godot --headless --path game/silentstar --script res://tools/trace.gd -- --out=work/trace_godot.txt
##   python3 tools/trace.py --out work/trace_py.txt
##   python3 tools/compare_trace.py work/trace_py.txt work/trace_godot.txt
##
## Optional arguments: --data=<data/new folder>  --cases=<cases file>  --out=<output file, a relative path is taken from the repository root>

const Data = preload("res://core/data.gd")
const State = preload("res://core/state.gd")
const Rng = preload("res://core/rng.gd")
const Rules = preload("res://core/rules.gd")
const Jsonx = preload("res://core/jsonx.gd")
const Schedule = preload("res://core/schedule.gd")
const Month = preload("res://core/month.gd")
const Audition = preload("res://core/audition.gd")


func _init() -> void:
	var root := ProjectSettings.globalize_path("res://").path_join("../..").simplify_path()
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--") and a.contains("="):
			var i := a.find("=")
			args[a.substr(2, i - 2)] = a.substr(i + 1)
	var data_dir: String = _abs(root, args.get("data", "data/new"))
	var cases_path: String = _abs(root, args.get("cases", "tools/trace_cases.json"))
	var out_path: String = _abs(root, args.get("out", "work/trace_godot.txt"))

	var d = Data.new(data_dir)
	var cases = Jsonx.read_file(cases_path)
	if not d.ok or cases == null:
		push_error("failed to read the tables or the cases")
		quit(1)
		return
	var text := run(d, cases)
	DirAccess.make_dir_recursive_absolute(out_path.get_base_dir())
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	if f == null:
		push_error("cannot write %s" % out_path)
		quit(1)
		return
	f.store_string(text)
	f.close()
	print("wrote %s, %d lines" % [out_path, text.count("\n")])
	quit(0)


func _abs(root: String, p: String) -> String:
	if p.is_absolute_path():
		return p
	return root.path_join(p).simplify_path()


static func js(v) -> String:
	return Jsonx.dumps(v)


func _u32s(g, n: int) -> String:
	var a := PackedStringArray()
	for i in n:
		a.append(str(g.next_u32()))
	return " ".join(a)


func run(d, cases: Dictionary) -> String:
	var out := PackedStringArray()

	var c: Dictionary = cases["rng"]
	for s in c["seed"]:
		var g = Rng.new(s)
		out.append("# rng seed=%d" % s)
		out.append("logic " + _u32s(g.logic, c["count"]))
		out.append("show " + _u32s(g.show, c["count"]))
		out.append("dump " + js(g.dump()))

	c = cases["mixed"]
	var g = Rng.new(c["seed"])
	out.append("# mixed seed=%d" % c["seed"])
	for step in c["steps"]:
		var op: String = step[0]
		var args: Array = step.slice(1)
		var res
		match op:
			"below": res = g.logic.below(args[0])
			"r": res = g.logic.r(args[0], args[1])
			"r0": res = g.logic.r0(args[0])
			"r1": res = g.logic.r1(args[0])
			"chance": res = g.logic.chance(args[0], args[1])
		out.append("%s %s -> %s" % [op, js(args), js(res)])
	out.append("dump " + js(g.dump()))
	var g2 = Rng.load_from(Jsonx.parse(js(g.dump())))
	out.append("cont " + _u32s(g.logic, 4))
	out.append("reload " + _u32s(g2.logic, 4))
	var p = Rng.PCG32.load_from(g.show.dump())
	out.append("show reload " + str(p.next_u32()) + " " + str(g.show.next_u32()))

	for oc in cases["origin"]:
		var st0 = State.new(d)
		st0.start(oc["seed"], oc["origin"])
		var save0: String = st0.dumps()
		out.append("# origin seed=%d origin=%s" % [oc["seed"], js(oc["origin"])])
		out.append("save " + save0)
		out.append("roundtrip " + _roundtrip(d, save0))

	c = cases["effect"]
	var st = State.new(d)
	st.start(c["seed"], c["origin"])
	out.append("# effect seed=%d origin=%s" % [c["seed"], js(c["origin"])])
	for step in c["steps"]:
		if typeof(step) == TYPE_DICTIONARY:
			if step.has("equip"):
				st.equip = Jsonx.copy(step["equip"])
				out.append("equip " + js(st.equip) + " gear " + js(st.bonus()))
			if step.get("update_indices", false):
				st.update_indices()
				out.append("update_indices " + js(st.idx) + " " + js(st.status))
			continue
		var text: String = step[0]
		var source: String = step[1] if step.size() > 1 else "event"
		var trig := Rules.apply_effect(st, text, source)
		out.append("effect %s [%s] -> %s money=%d favor=%s items=%s equip=%s bonus=%s" % [
			text, source, js(trig), st.money, js(st.favor), js(st.items), js(st.equip), js(st.bonus())])
	var lv := {}
	for r in d.roads:
		lv[r] = st.level(r)
	out.append("levels " + js(lv) + " fame_tiers " + str(st.fame_tier()))
	for name in cases["var"]:
		out.append("var %s = %s" % [name, js(Rules.get_var(st, name))])
	for cd in cases["cond"]:
		out.append("cond %s = %s" % [js(cd), js(Rules.cond(st, cd))])
	for ck in cases["check"]:
		out.append("check %s = %s" % [js(ck), js(Rules.check(st, ck))])
	for pr in cases["prob"]:
		out.append("prob %s = %s" % [js(pr), js(Rules.prob(st, pr))])
	var s1: String = st.dumps()
	out.append("save " + s1)
	out.append("roundtrip " + _roundtrip(d, s1))

	for mc in cases.get("month", []):
		_run_month_case(d, mc, out)
	if cases.has("audition"):
		_run_audition_cases(d, cases["audition"], out)
	return "\n".join(out) + "\n"


## Step 10: a fixed schedule for 48 months (default hooks); the same as run_month_case in tools/trace.py.
func _run_month_case(d, c: Dictionary, out: PackedStringArray) -> void:
	var g = Month.new(d, c["seed"], c["origin"])
	out.append("# month %s seed=%d origin=%s" % [c["name"], c["seed"], js(c["origin"])])
	if c.get("effect", "") != "":
		Rules.apply_effect(g.st, c["effect"], "origin")
		g.st.update_indices()
	var bk: Dictionary = c.get("books", {})
	for bid in bk:
		g.st.books[bid] = bk[bid]
	var n := 0
	while not g.st.finished:
		if n == c.get("restore_at", -1):
			var sv: String = g.save()
			g = Month.restore(sv, d)
			out.append("restore " + str(sv.length()))
		var date: String = g.st.date()
		if c.has("lifestyles"):
			g.set_lifestyle(c["lifestyles"][n % c["lifestyles"].size()])
		g.start_month()
		if c.get("month_effect", "") != "" and n < c.get("month_effect_months", 48):
			Rules.apply_effect(g.st, c["month_effect"], "origin")
		var plan := []
		var base: Array = c["plans"][n % c["plans"].size()]
		for e in base:
			plan.append(e if Schedule.validate(g.st, e) == "" else "rest_home")
		g.run_month(plan)
		out.append("plan " + js(plan) + " " + js(g.last))
		out.append(Month.trace_line(g.st, date))
		n += 1
	out.append("end finished=%d ended=%s debt=%d collapse=%d" % [g.st.finished, js(g.st.ended), g.st.debt_months, g.st.collapse_months])
	out.append("save " + g.st.dumps())


func _roundtrip(d, s1: String) -> String:
	var st2 = State.new(d)
	st2.loads(s1)
	var s2: String = st2.dumps()
	return "identical" if s1 == s2 else "differs " + s2


## Step 11: the same as _TracePlayer in tools/trace.py.
class TracePlayer:
	extends Audition.Player
	var colors := []

	func _init(c: Array) -> void:
		colors = c

	func deck(_st, _ctx) -> Array:
		return colors.duplicate()

	func play(st, ctx) -> int:
		return st.rng.logic.below(ctx["hand"].size())


## Step 11: c.count auditions; the same as run_audition_cases in tools/trace.py.
func _run_audition_cases(d, c: Dictionary, out: PackedStringArray) -> void:
	var st = State.new(d)
	st.start(c["seed"], c["origin"])
	var sh = st.rng.show
	out.append("# audition seed=%d origin=%s count=%d" % [c["seed"], js(c["origin"]), c["count"]])
	var named := []
	for x in d.t["rivals"]["named"]:
		named.append(x["id"])
	var tiers := ["small", "medium", "big"]
	var pools := [[15, 60, 10, 15], [25, 25, 25, 25], [70, 10, 10, 10], [10, 10, 10, 70], [0, 0, 100, 0], [40, 0, 0, 60]]
	for i in int(c["count"]):
		st.ym = sh.below(48)
		st.attr["fame"] = sh.r(0, 400)
		for r in d.roads:
			st.corr[r] = sh.r(-50, 300)
		var probs: Array = pools[sh.below(pools.size())].duplicate()
		var size: String = tiers[sh.below(3)]
		var rivals := []
		for k in (2 if size == "big" else 1):
			var nid: String = named[sh.below(named.size())]
			var pick: int = sh.below(2)
			if pick != 0 and Audition.rival_present(st, nid):
				rivals.append(Audition.named_rival(st, nid))
			else:
				rivals.append(Audition.unnamed_rival(st, size))
		var main := Audition.player_main(st)
		var sub: int = (main + 1 + sh.below(3)) % 4
		var k: int = 3 + sh.below(3)
		var cols := []
		for j in k:
			cols.append(main)
		for j in 5 - k:
			cols.append(sub)
		var pl = TracePlayer.new(cols)
		if sh.below(4) == 0:
			probs = Audition.remembered_probs(probs, main, 10)
		var role := {"id": "role%d" % i, "style_probs": probs}
		var res := Audition.audition(st, role, pl, rivals)
		out.append("%d %s fame=%d lv=%s probs=%s rivals=%s -> %s" % [i, st.date(), st.attr["fame"],
			js(Audition.player_levels(st)), js(probs), js(rivals), js(res)])
	out.append("state " + js(st.rng.dump()) + " " + js(st.count) + " " + js(st.favor))
	out.append("save " + st.dumps())
