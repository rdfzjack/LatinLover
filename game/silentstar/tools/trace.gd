extends SceneTree
## 第 9 步对账：按 tools/trace_cases.json 输出随机数序列、存档往返、条件和效果的结果。
## 和 Python 的 tools/trace.py 输出要逐字节一致。在仓库根目录运行：
##
##   godot --headless --path game/silentstar --script res://tools/trace.gd -- --out=work/trace_godot.txt
##   python3 tools/trace.py --out work/trace_py.txt
##   python3 tools/compare_trace.py work/trace_py.txt work/trace_godot.txt
##
## 可选参数：--data=<data/new 目录>  --cases=<用例文件>  --out=<输出文件，相对路径按仓库根算>

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
		push_error("读表或用例失败")
		quit(1)
		return
	var text := run(d, cases)
	DirAccess.make_dir_recursive_absolute(out_path.get_base_dir())
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	if f == null:
		push_error("写不了 %s" % out_path)
		quit(1)
		return
	f.store_string(text)
	f.close()
	print("写到 %s，%d 行" % [out_path, text.count("\n")])
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

	var c: Dictionary = cases["随机数"]
	for s in c["种子"]:
		var g = Rng.new(s)
		out.append("# 随机数 种子=%d" % s)
		out.append("logic " + _u32s(g.logic, c["个数"]))
		out.append("show " + _u32s(g.show, c["个数"]))
		out.append("dump " + js(g.dump()))

	c = cases["混合"]
	var g = Rng.new(c["种子"])
	out.append("# 混合 种子=%d" % c["种子"])
	for step in c["步骤"]:
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
	out.append("续 " + _u32s(g.logic, 4))
	out.append("读回 " + _u32s(g2.logic, 4))
	var p = Rng.PCG32.load_from(g.show.dump())
	out.append("show 读回 " + str(p.next_u32()) + " " + str(g.show.next_u32()))

	for oc in cases["开局"]:
		var st0 = State.new(d)
		st0.start(oc["种子"], oc["开局"])
		var save0: String = st0.dumps()
		out.append("# 开局 种子=%d 开局=%s" % [oc["种子"], js(oc["开局"])])
		out.append("存档 " + save0)
		out.append("往返 " + _roundtrip(d, save0))

	c = cases["效果"]
	var st = State.new(d)
	st.start(c["种子"], c["开局"])
	out.append("# 效果 种子=%d 开局=%s" % [c["种子"], js(c["开局"])])
	for step in c["步骤"]:
		if typeof(step) == TYPE_DICTIONARY:
			if step.has("装备"):
				st.equip = Jsonx.copy(step["装备"])
				out.append("装备 " + js(st.equip) + " 加成 " + js(st.bonus()))
			if step.get("更新指数", false):
				st.update_indices()
				out.append("更新指数 " + js(st.idx) + " " + js(st.status))
			continue
		var text: String = step[0]
		var source: String = step[1] if step.size() > 1 else "event"
		var trig := Rules.apply_effect(st, text, source)
		out.append("效果 %s [%s] -> %s 金钱=%d 好感=%s 物品=%s 装备=%s 加成=%s" % [
			text, source, js(trig), st.money, js(st.favor), js(st.items), js(st.equip), js(st.bonus())])
	var lv := {}
	for r in d.roads:
		lv[r] = st.level(r)
	out.append("等级 " + js(lv) + " 名气档 " + str(st.fame_tier()))
	for name in cases["变量"]:
		out.append("变量 %s = %s" % [name, js(Rules.get_var(st, name))])
	for cd in cases["条件"]:
		out.append("条件 %s = %s" % [js(cd), js(Rules.cond(st, cd))])
	for ck in cases["判定"]:
		out.append("判定 %s = %s" % [js(ck), js(Rules.check(st, ck))])
	for pr in cases["概率"]:
		out.append("概率 %s = %s" % [js(pr), js(Rules.prob(st, pr))])
	var s1: String = st.dumps()
	out.append("存档 " + s1)
	out.append("往返 " + _roundtrip(d, s1))
	return "\n".join(out) + "\n"


func _roundtrip(d, s1: String) -> String:
	var st2 = State.new(d)
	st2.loads(s1)
	var s2: String = st2.dumps()
	return "一致" if s1 == s2 else "不一致 " + s2
