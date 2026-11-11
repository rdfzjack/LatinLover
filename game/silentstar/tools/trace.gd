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
	return "\n".join(out) + "\n"


func _roundtrip(d, s1: String) -> String:
	var st2 = State.new(d)
	st2.loads(s1)
	var s2: String = st2.dumps()
	return "identical" if s1 == s2 else "differs " + s2
