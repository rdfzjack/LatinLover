extends SceneTree
## Report of the strategy bots in tools/sbots.gd (PLAN step 2, 2026-11).
##
##   godot --headless --path game/silentstar --script res://tools/sreport.gd -- --n=40 [--bots=a,b] [--out=path.json]
##
## Type 1 (full_<road>): the game stops when the main road's three skills are trained to 100; reports that month and what it took.
## Type 2 (the rest): whole games; reports the four road reputations, the strongest base attribute, the total score, ending,
## grade, fame, money and the films led.

const Data = preload("res://core/data.gd")
const Rules = preload("res://core/rules.gd")
const Story = preload("res://core/story.gd")
const SBots = preload("res://tools/sbots.gd")

const BASE := ["stamina", "education", "loyalty", "looks", "discipline", "crime"]


func _init() -> void:
	var root := ProjectSettings.globalize_path("res://").path_join("../..").simplify_path()
	var args := {}
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var i := a.find("=")
			if i < 0:
				args[a.substr(2)] = "1"
			else:
				args[a.substr(2, i - 2)] = a.substr(i + 1)
	var d = Data.new(root.path_join("data/new"))
	var n := int(args.get("n", "20"))
	var all: Dictionary = SBots.all_bots()
	var names: Array = all.keys()
	if args.has("bots"):
		names = Array(String(args["bots"]).split(","))
	var dump := {}
	var t1 := []
	var t2 := []
	for nm in names:
		var recs := []
		for sd in range(1, n + 1):
			recs.append(play(all[nm], sd, d))
		dump[nm] = recs
		if SBots.TYPE1.has(nm):
			t1.append(type1_line(nm, recs, d))
		else:
			t2.append(type2_line(nm, recs))
		printerr("%s done" % nm)
	print("== %d games per bot ==" % n)
	if not t1.is_empty():
		print("-- type 1: main road only, stopped when its three skills are trained to 100")
		print("bot              full at (median, p10-p90)   share of 72 months | money then | periods class/job/rest | not full")
		for x in t1:
			print(x)
	if not t2.is_empty():
		print("-- type 2: whole games")
		print("bot                    total p50 (p10-p90) | grade S/A/B/C/D % | category % | reps T/L/C/S p50 | top base attr | fame p50 | money p50 | leads s/m/b, support | hit/flop | arrest | collapse")
		for x in t2:
			print(x)
		print("-- money over the game, median: all income = film fees + release dividends + the rest (jobs and other) | final speech")
		for nm in names:
			if SBots.TYPE1.has(nm):
				continue
			var inc := []
			var fe := []
			var dv := []
			var rest := []
			var sp := []
			for r in dump[nm]:
				inc.append(r["income"])
				fe.append(r["fee"])
				dv.append(r["dividend"])
				rest.append(r["income"] - r["fee"] - r["dividend"])
				sp.append(r["speech"])
			print("%-22s %6d = fees %6d + dividends %6d + jobs/other %6d | speech %d" % [nm, med(inc), med(fe), med(dv), med(rest), med(sp)])
		print("-- grade and the axis that gave it (rep / fame / rep_sum / dark)")
		for nm in names:
			if SBots.TYPE1.has(nm):
				continue
			print("%-22s %s" % [nm, top_counts(dump[nm], "grade_by", 4)])
		print("-- most common endings")
		for nm in names:
			if SBots.TYPE1.has(nm):
				continue
			print("%-22s %s" % [nm, top_counts(dump[nm], "ending", 4)])
	if args.has("out"):
		var f := FileAccess.open(String(args["out"]), FileAccess.WRITE)
		f.store_string(JSON.stringify(dump))
	quit()


func play(spec, sd: int, d) -> Dictionary:
	var bot = SBots.make(spec, sd)
	var g = Story.new_game(d, sd, bot.origin, bot)
	var st = g.st
	var full := -1
	while not st.finished:
		g.start_month()
		g.run_month(Story.fit_plan(g, bot.plan(g)))
		if bot.stop_when_full and main_full(st, bot.road):
			full = st.ym
			break
	var c: Dictionary = st.count
	var rec := {"seed": sd, "full_month": full, "money": st.money, "fame": st.attr["fame"]}
	var per := {"class": 0, "job": 0, "rest": 0}
	for k in c:
		if k.begins_with("count.period.class_"):
			per["class"] += c[k]
		elif k.begins_with("count.period.job_"):
			per["job"] += c[k]
		elif k.begins_with("count.period.rest_"):
			per["rest"] += c[k]
	rec["periods"] = per
	if bot.stop_when_full:
		return rec
	var res: Dictionary = st.story["ending"]
	rec["ending"] = str(res.get("ending"))
	rec["category"] = str(res.get("category"))
	rec["grade"] = str(res.get("grade"))
	rec["grade_by"] = "%s:%s" % [str(res.get("grade")), str(res.get("grade_by", ""))]
	rec["total"] = int(res.get("total", 0)) if res.get("total") != null else 0
	var b: Dictionary = st.bonus()
	var reps := []
	for r in d.roads:
		reps.append(st.rep(r, b))
	rec["reps"] = reps
	var top := BASE[0]
	for a in BASE:
		if st.val(a) > st.val(top):
			top = a
	rec["top_attr"] = top
	rec["top_attr_v"] = st.val(top)
	var fee := 0
	var div := 0
	for f in st.story["films"]:
		if f.get("fee") != null:
			fee += int(f["fee"])
		if f.get("result") != null:
			div += int(f["result"].get("dividend", 0))
	rec["income"] = int(st.src.get("income", 0))
	rec["fee"] = fee
	rec["dividend"] = div
	rec["speech"] = st.skill["speech"]
	for k in ["count.lead.small", "count.lead.medium", "count.lead.big", "count.support", "count.hit", "count.flop",
			"count.arrest", "count.hospital", "count.boost", "count.divine", "count.slack"]:
		rec[k.substr(6)] = c.get(k, 0)
	return rec


func main_full(st, road: String) -> bool:
	for s in st.d.road_skills[road]:
		if st.skill[s] < 100:
			return false
	return true


func type1_line(nm: String, recs: Array, _d) -> String:
	var ms := []
	var money := []
	var per := {"class": [], "job": [], "rest": []}
	var miss := 0
	for r in recs:
		if r["full_month"] < 0:
			miss += 1
			continue
		ms.append(r["full_month"] + 1)
		money.append(r["money"])
		for k in per:
			per[k].append(r["periods"][k])
	if ms.is_empty():
		return "%-16s never full" % nm
	var m50 := med(ms)
	return "%-16s %s (%d-%d)                %3d%%           | %6d     | %d/%d/%d               | %d of %d" % [
		nm, ym_text(m50), pct(ms, 10), pct(ms, 90), int(round(m50 * 100.0 / 72.0)), med(money),
		med(per["class"]), med(per["job"]), med(per["rest"]), miss, recs.size()]


func type2_line(nm: String, recs: Array) -> String:
	var tot := []
	var fame := []
	var money := []
	var reps := [[], [], [], []]
	var grades := {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
	var films := [0.0, 0.0, 0.0, 0.0]
	var hf := [0.0, 0.0]
	var arrest := 0.0
	var collapse := 0
	var attrs := {}
	for r in recs:
		tot.append(r["total"])
		fame.append(r["fame"])
		money.append(r["money"])
		for i in 4:
			reps[i].append(r["reps"][i])
		if grades.has(r["grade"]):
			grades[r["grade"]] += 1
		films[0] += r["lead.small"]
		films[1] += r["lead.medium"]
		films[2] += r["lead.big"]
		films[3] += r["support"]
		hf[0] += r["hit"]
		hf[1] += r["flop"]
		arrest += r["arrest"]
		if r["category"] == "forced":
			collapse += 1
		if not attrs.has(r["top_attr"]):
			attrs[r["top_attr"]] = []
		attrs[r["top_attr"]].append(r["top_attr_v"])
	var n := float(recs.size())
	var top_a := ""
	for a in attrs:
		if top_a == "" or attrs[a].size() > attrs[top_a].size():
			top_a = a
	var gtxt := "%d/%d/%d/%d/%d" % [pc(grades["S"], n), pc(grades["A"], n), pc(grades["B"], n), pc(grades["C"], n), pc(grades["D"], n)]
	return "%-22s %5d (%d-%d) | %s | %s | %d/%d/%d/%d | %s %d (%d%%) | %d | %d | %.1f/%.1f/%.1f, %.1f | %.1f/%.1f | %.1f | %d%%" % [
		nm, med(tot), pct(tot, 10), pct(tot, 90), gtxt, top_counts(recs, "category", 2),
		med(reps[0]), med(reps[1]), med(reps[2]), med(reps[3]), top_a, med(attrs[top_a]), pc(attrs[top_a].size(), n),
		med(fame), med(money), films[0] / n, films[1] / n, films[2] / n, films[3] / n, hf[0] / n, hf[1] / n, arrest / n,
		pc(collapse, n)]


func top_counts(recs: Array, key: String, k: int) -> String:
	var cnt := {}
	for r in recs:
		var v = r.get(key)
		cnt[v] = cnt.get(v, 0) + 1
	var ks: Array = cnt.keys()
	ks.sort_custom(func(a, b): return cnt[a] > cnt[b] if cnt[a] != cnt[b] else str(a) < str(b))
	var out := []
	for x in ks.slice(0, k):
		out.append("%s %d%%" % [x, pc(cnt[x], float(recs.size()))])
	return ", ".join(out)


func pc(x, n: float) -> int:
	return int(round(float(x) * 100.0 / n))


func med(xs: Array) -> int:
	return pct(xs, 50)


func pct(xs: Array, p: int) -> int:
	if xs.is_empty():
		return 0
	var s := xs.duplicate()
	s.sort()
	return int(s[clampi(int(round((s.size() - 1) * p / 100.0)), 0, s.size() - 1)])


func ym_text(m: int) -> String:
	var ym := m - 1
	return "%d-%02d" % [1924 + ym / 12, ym % 12 + 1]
