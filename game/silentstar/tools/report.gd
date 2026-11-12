extends SceneTree
## Runs the bots in bulk and prints a report (PLAN steps 7, 8; ported to Godot in step 12b). Port of sim/report.py:
## the output is character for character the same as `python3 -m sim.report` with the same arguments.
##
##   godot --headless --path game/silentstar --script res://tools/report.gd -- --n=200 --bots=all
##
## Arguments (after `--`, written as --name=value; the two switches have no value):
##   --n=200              games per bot (seeds 1..n)
##   --seeds=a-b          the seeds a..b instead of 1..n (to split a run into several processes, see --dump / --merge)
##   --bots=all           "all" or a comma-separated list of bot names (default all)
##   --no-buy             bots do not buy gear (and the "without buying gear" section is left out)
##   --random-play        bots play random cards (random_pick is unaffected)
##   --out=<file>         also write the report to this file (relative paths are taken from the repository root)
##   --dump=<file>        write the game records (JSON) instead of printing a report
##   --merge=<f1,f2,...>  read record files written by --dump (in this order) and print the report of all of them
##   --data=<data/new folder>
##   --random-options     bots pick event options at random (worst case) instead of by their preference table
##   --coverage           also print how often each event fired and each option was picked (events never fired are listed)
##   --guard=<file>       also print PASS / FAIL for every target in that file (design/targets.json); exit code 2 when any fails
##   --widen=10           widen every guard range by this percent of its bounds (check.py uses 10 with 30 games)
## The report has at most 60 lines. The brackets hold the targets of PLAN step 8.
## Full training = the target road's three training values sum to >= 300 (random_pick, crime_line and books_culture take whichever
## of the four roads is full first). Main road = the road with the highest final reputation. "Full training plus plain releases" =
## main road training value + the bonus from releases (no gear, stamina bonus, annual events or opportunities).
## A game takes roughly a minute of CPU in GDScript (see design/IMPL_NOTES.md for the timing of a full run); split with --seeds.

const Data = preload("res://core/data.gd")
const Jsonx = preload("res://core/jsonx.gd")
const Rules = preload("res://core/rules.gd")
const Bots = preload("res://tools/bots.gd")

const NAN_VALUE := NAN

var random_options := false


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
	var data_dir: String = _abs(root, args.get("data", "data/new"))
	var smart = false if args.has("random-play") else null
	var no_buy: bool = args.has("no-buy")
	random_options = args.has("random-options")

	var res := {}
	var nobuy: Dictionary = {}
	var lo := 1
	var hi := int(args.get("n", "200"))
	if args.has("seeds"):
		var ab: PackedStringArray = String(args["seeds"]).split("-")
		lo = int(ab[0])
		hi = int(ab[1])
	if args.has("merge"):
		var merged := {"res": {}, "nobuy": {}}
		var order: Array = []       # the bot order of the first file (JSON object keys are sorted, so --dump saves the order)
		for f in String(args["merge"]).split(","):
			var part = Jsonx.read_file(_abs(root, f))
			if part == null:
				push_error("cannot read %s" % f)
				quit(1)
				return
			if order.is_empty():
				order = part.get("order", Bots.BOTS.keys())
			for key in ["res", "nobuy"]:
				for nm in part[key]:
					if not merged[key].has(nm):
						merged[key][nm] = []
					merged[key][nm].append_array(part[key][nm])
		for nm in order:
			if merged["res"].has(nm):
				res[nm] = merged["res"][nm]
			if merged["nobuy"].has(nm):
				nobuy[nm] = merged["nobuy"][nm]
		if not res.is_empty():
			var k0: int = res[res.keys()[0]].size()
			lo = 1
			hi = k0
			# the seeds of the first and the last record give the range
			var first_rs: Array = res[res.keys()[0]]
			lo = first_rs[0]["seed"]
			hi = first_rs[first_rs.size() - 1]["seed"]
	else:
		var d = Data.new(data_dir)
		if not d.ok:
			push_error("failed to read the tables")
			quit(1)
			return
		var names: Array = []
		var want: String = args.get("bots", "all")
		if want == "all":
			names = Bots.BOTS.keys()
		else:
			names = Array(want.split(","))
		res = run(d, lo, hi, names, smart, false if no_buy else null)
		var pure := []
		for nm in names:
			if nm in Bots.PURE:
				pure.append(nm)
		if not pure.is_empty() and not no_buy:
			nobuy = run(d, lo, hi, pure, smart, false)
		if args.has("dump"):
			var p := _abs(root, args["dump"])
			DirAccess.make_dir_recursive_absolute(p.get_base_dir())
			var f := FileAccess.open(p, FileAccess.WRITE)
			f.store_string(Jsonx.dumps({"order": names, "res": res, "nobuy": nobuy}))
			f.close()
			print("wrote %s" % p)
			quit(0)
			return

	var lines := report(res, lo, hi, smart == null, nobuy)
	if args.has("coverage"):
		lines.append_array(coverage(res))
	var failed := 0
	if args.has("guard"):
		var tg = JSON.parse_string(FileAccess.get_file_as_string(_abs(root, args["guard"])))    # fractions allowed here (not Jsonx)
		if tg == null:
			push_error("cannot read %s" % args["guard"])
			quit(1)
			return
		var gl := guard(res, tg, float(args.get("widen", "0")))
		for x in gl:
			if x.begins_with("FAIL"):
				failed += 1
		lines.append_array(gl)
	for line in lines:
		print(line)
	if args.has("out"):
		var p2 := _abs(root, args["out"])
		DirAccess.make_dir_recursive_absolute(p2.get_base_dir())
		var f2 := FileAccess.open(p2, FileAccess.WRITE)
		f2.store_string("\n".join(lines) + "\n")
		f2.close()
	quit(2 if failed > 0 else 0)


func _abs(root: String, p: String) -> String:
	if p.is_absolute_path():
		return p
	return root.path_join(p).simplify_path()


## Plays seeds lo..hi of every bot in names. Returns {bot name: [record, ...]} in seed order.
func run(d, lo: int, hi: int, names: Array, smart, buy) -> Dictionary:
	var out := {}
	for nm in names:
		out[nm] = []
	for nm in names:
		for sd in range(lo, hi + 1):
			out[nm].append(Bots.play(Bots.BOTS[nm], sd, d, smart, buy, Callable(), random_options))
			printerr("%s seed %d done" % [nm, sd])
	return out


# ---------- number formatting (Python's format(), not GDScript's %f which rounds the last digit differently) ----------

## Python f"{x:{width}.{dec}f}" (right-aligned) with optional thousands separators; x is rounded half-even on its exact binary value.
static func ff(x: float, dec: int, width := 0, comma := false) -> String:
	var s := _fixed(x, dec, comma)
	return s.lpad(width, " ")


static func _fixed(x: float, dec: int, comma: bool) -> String:
	if is_nan(x):
		return "nan"
	var b := PackedByteArray()
	b.resize(8)
	b.encode_double(0, x)
	var bits: int = b.decode_u64(0)
	var neg: bool = bits < 0       # the sign bit (GDScript ints are signed 64-bit)
	if is_inf(x):
		return "-inf" if neg else "inf"
	var expo: int = (bits >> 52) & 0x7FF
	var mant: int = bits & 0xFFFFFFFFFFFFF
	if expo == 0:
		expo = 1
	else:
		mant |= (1 << 52)
	var e2: int = expo - 1075                  # x = mant * 2^e2
	var scale := 1
	for i in dec:
		scale *= 10
	var q: int
	if e2 >= 0:
		q = (mant << e2) * scale
	else:
		var k: int = -e2
		if k > 62:
			q = 0                              # below 2^-9, so below 0.002: rounds to zero for dec <= 1
		else:
			var num: int = mant * scale
			q = num >> k
			var rem: int = num & ((1 << k) - 1)
			var half: int = 1 << (k - 1)
			if rem > half or (rem == half and (q & 1) == 1):
				q += 1
	var digits := str(q)
	if dec > 0:
		digits = digits.lpad(dec + 1, "0")
		digits = digits.substr(0, digits.length() - dec) + "." + digits.substr(digits.length() - dec)
	if comma:
		var dot := digits.find(".")
		var ip: String = digits if dot < 0 else digits.substr(0, dot)
		var fp: String = "" if dot < 0 else digits.substr(dot)
		var g := ""
		while ip.length() > 3:
			g = "," + ip.substr(ip.length() - 3) + g
			ip = ip.substr(0, ip.length() - 3)
		digits = ip + g + fp
	return ("-" if neg else "") + digits


static func f0(x) -> String:
	return ff(float(x), 0)


static func idiv(a: int, b: int) -> int:
	return Rules.fdiv(a, b)


# ---------- statistics ----------

## xs[min(len-1, int(q * len))] of the sorted list; NaN for an empty list.
static func pct(xs_in: Array, q: float):
	if xs_in.is_empty():
		return NAN_VALUE
	var xs := xs_in.duplicate()
	xs.sort()
	return xs[mini(xs.size() - 1, int(q * xs.size()))]


static func med(xs: Array):
	return pct(xs, 0.5)


static func ratio(a, b) -> float:
	if b != 0:
		return 100.0 * float(a) / float(b)
	return NAN_VALUE


## Month index + 1 (counted from 1) of the first month whose value (month-end record) satisfies the test; null when none does.
static func full_month(rec: Dictionary):
	for m in rec["train"].size():
		if rec["train"][m].max() >= 300:
			return m + 1
	return null


static func rep_month(rec: Dictionary, line: int):
	for m in rec["rep"].size():
		if rec["rep"][m].max() >= line:
			return m + 1
	return null


## Median (p10-p90); null counts as not reached; flags it when the share reaching it is too low.
static func fmt_q(xs: Array, n: int) -> String:
	var got := []
	for x in xs:
		if x != null:
			got.append(x)
	if got.is_empty():
		return "—"
	var s := "%s(%s–%s)" % [f0(med(got)), f0(pct(got, 0.1)), f0(pct(got, 0.9))]
	if float(got.size()) < n * 0.9:
		s += "[%d%%]" % idiv(got.size() * 100, n)
	return s


static func sum_key(rs: Array, key: String) -> int:
	var s := 0
	for r in rs:
		s += int(r[key])
	return s


static func at_month(rs: Array, field: String, m: int) -> Array:
	var out := []
	for r in rs:
		out.append(r[field][mini(m, r[field].size() - 1)])
	return out


static func grades(rs: Array) -> String:
	var parts := PackedStringArray()
	for x in ["S", "A", "B", "C", "D"]:
		var c := 0
		for r in rs:
			if r["grade"] == x:
				c += 1
		parts.append(str(idiv(c * 100, rs.size())))
	return "/".join(parts)


## Counter.most_common(4): descending count, ties in order of first appearance.
static func most_common(keys: Array, n: int) -> Array:
	var counts := {}
	for k in keys:
		counts[k] = counts.get(k, 0) + 1
	var items := []
	for k in counts:
		items.append([k, counts[k]])
	var out := []
	while out.size() < n and not items.is_empty():
		var bi := 0
		for i in range(1, items.size()):
			if items[i][1] > items[bi][1]:
				bi = i
		out.append(items[bi])
		items.remove_at(bi)
	return out


static func report(res: Dictionary, lo: int, hi: int, smart: bool, nobuy: Dictionary) -> Array:
	var L := []
	var n: int = hi - lo + 1
	L.append("== each bot %d games (seeds %d-%d), cards played %s; targets: PLAN step 8 ==" % [n, lo, hi, "greedy" if smart else "random"])
	L.append("-- full-training month median (10%-90%) [target 16-21] | months with rep >= 210 | main-road rep median at months 12/24/36/48")
	for nm in res:
		var rs: Array = res[nm]
		var k := rs.size()
		var mm := PackedStringArray()
		for m in [11, 23, 35, 47]:
			var xs := []
			for x in at_month(rs, "rep", m):
				xs.append(x.max())
			mm.append(f0(med(xs)))
		var fulls := []
		var r210 := []
		for r in rs:
			fulls.append(full_month(r))
			r210.append(rep_month(r, 210))
		L.append("%s full %s 210:%s %s" % [nm.rpad(8), fmt_q(fulls, k).rpad(14), fmt_q(r210, k).rpad(12), "/".join(mm)])
	L.append("-- final main-road rep breakdown (mean): training+gear and stamina+releases+annual+opportunities | full training plus plain releases (no gear) median [311-340], over 311 [90%] | grade S/A/B/C/D %")
	for nm in res:
		var rs: Array = res[nm]
		var k := rs.size()
		var av := func(key: String) -> float:
			var s := 0
			for r in rs:
				s += int(r["breakdown"][key])
			return float(s) / float(k)
		var plain := []
		var max_reps := []
		var over := 0
		for r in rs:
			var p: int = r["breakdown"]["training"] + r["breakdown"]["release"]
			plain.append(p)
			max_reps.append(r["max_rep"])
			if p >= 311:
				over += 1
		L.append("%s %s+%s+%s+%s+%s = %s | %s over 311 %s%% | %s" % [nm.rpad(8), ff(av.call("training"), 0, 3), ff(av.call("gear"), 0, 2),
			ff(av.call("release"), 0, 2), ff(av.call("annual"), 0, 2), ff(av.call("opportunity"), 0, 2), ff(float(med(max_reps)), 0, 3),
			f0(med(plain)), ff(ratio(over, k), 0, 3), grades(rs)])
	L.append("-- cash at each year end, median (years 1-4) [first two years <1000] | final p90 [<10k] | final >10k | debt months | film fees total, gear spend (mean)")
	for nm in res:
		var rs: Array = res[nm]
		var k := rs.size()
		var y := PackedStringArray()
		for m in [11, 23, 35, 47]:
			y.append(ff(float(med(at_month(rs, "money", m))), 0, 0, true))
		var end := []
		var over10 := 0
		for r in rs:
			end.append(r["money"][r["money"].size() - 1])
			if end[end.size() - 1] > 10000:
				over10 += 1
		L.append("%s %s p90 %s  >10k %s%%  debt %s | %s %s" % [nm.rpad(8), " / ".join(y).rpad(32), ff(float(pct(end, 0.9)), 0, 7, true),
			ff(ratio(over10, k), 0, 3), ff(float(sum_key(rs, "debt")) / k, 1, 4), ff(float(sum_key(rs, "fee")) / k, 0, 6, true),
			ff(float(sum_key(rs, "gear_buy")) / k, 0, 5, true)])
	L.append("-- auditions per game, won% small/medium/big [big 10-35%] | releases per game, hit% [10%] flop% | leads small/medium/big | supports, breaches")
	for nm in res:
		var rs: Array = res[nm]
		var k := rs.size()
		var w := func(t: String) -> String:
			return f0(ratio(sum_key(rs, "count.audition_won." + t), sum_key(rs, "count.audition." + t)))
		L.append("%s %s games %s/%s/%s%% (big %s games) | release %s hit %s%% flop %s%% | %s/%s/%s | %s %s" % [nm.rpad(8),
			ff(float(sum_key(rs, "count.audition")) / k, 1, 4), w.call("small"), w.call("medium"), w.call("big"),
			ff(float(sum_key(rs, "count.audition.big")) / k, 1), ff(float(sum_key(rs, "count.release")) / k, 1, 4),
			ff(ratio(sum_key(rs, "count.hit"), sum_key(rs, "count.release")), 0, 3),
			ff(ratio(sum_key(rs, "count.flop"), sum_key(rs, "count.release")), 0, 3),
			ff(float(sum_key(rs, "count.lead.small")) / k, 1), ff(float(sum_key(rs, "count.lead.medium")) / k, 1),
			ff(float(sum_key(rs, "count.lead.big")) / k, 1), ff(float(sum_key(rs, "count.support")) / k, 1),
			ff(float(sum_key(rs, "count.breach")) / k, 1)])
	L.append("-- median fame at each year end | final fame tier unknown/familiar/famous/hot/superstar % | mean annual rank (years 1-4) | collapse% | endings (kinds [>=3]; top four)")
	for nm in res:
		var rs: Array = res[nm]
		var k := rs.size()
		var tiers := PackedStringArray()
		for i in 5:
			var c := 0
			for r in rs:
				if r["fame_tier"] == i:
					c += 1
			tiers.append(str(idiv(c * 100, k)))
		var endings := []
		for r in rs:
			endings.append(r["ending"])
		var counts := {}
		for e in endings:
			counts[e] = counts.get(e, 0) + 1
		var fy := PackedStringArray()
		for m in [11, 23, 35, 47]:
			fy.append(f0(med(at_month(rs, "fame", m))))
		var rk := PackedStringArray()
		for i in 4:
			var xs := []
			for r in rs:
				if r["annual_rank"].size() > i and Rules_truthy(r["annual_rank"][i]):
					xs.append(r["annual_rank"][i])
			if xs.is_empty():
				rk.append("-")
			else:
				var s := 0
				for x in xs:
					s += int(x)
				rk.append(ff(float(s) / xs.size(), 1))
		var top := PackedStringArray()
		for kv in most_common(endings, 4):
			top.append("%s%d%%" % [String(kv[0]).replace("end_", ""), idiv(kv[1] * 100, k)])
		L.append("%s %s %s rank %s  collapse %s%%  endings %d kinds: %s" % [nm.rpad(8), "/".join(fy).rpad(16), "/".join(tiers).rpad(14),
			"/".join(rk), f0(ratio(counts.get("end_collapse", 0), k)), counts.size(), " ".join(top)])
	if not nobuy.is_empty():
		L.append("-- without buying gear: final cash median / p90 | final main-road rep median | grade S/A/B/C/D %")
		for nm in nobuy:
			var rs: Array = nobuy[nm]
			var end := []
			var max_reps := []
			for r in rs:
				end.append(r["money"][r["money"].size() - 1])
				max_reps.append(r["max_rep"])
			L.append("%s %s / %s | %s | %s" % [nm.rpad(8), ff(float(med(end)), 0, 7, true), ff(float(pct(end, 0.9)), 0, 7, true),
				f0(med(max_reps)), grades(rs)])
	L.append("-- from events, median per game: main-road rep from events (skills + rep_bonus) [<=30] | event money net, % of all money gained [+-10%] | event fatigue net per year [+-60] | opportunity rep")
	for nm in res:
		var rs: Array = res[nm]
		var rep := []
		var mon := []
		var share := []
		var fat := []
		var opp := []
		for r in rs:
			rep.append(r.get("src_event_rep", 0))
			mon.append(r.get("src_event_money", 0))
			share.append(100.0 * float(r.get("src_event_money", 0)) / float(maxi(1, int(r.get("income", 0)))))
			fat.append(float(r.get("src_event_fatigue", 0)) / 4.0)
			opp.append(r.get("src_opp_rep", 0))
		L.append("%s ev rep %s | money %s (%s%%) | fatigue/yr %s | opp rep %s" % [nm.rpad(8), f0(med(rep)).lpad(3), ff(float(med(mon)), 0, 6, true),
			ff(float(med(share)), 1, 5), ff(float(med(fat)), 0, 4), f0(med(opp))])
	var strat_names := []
	for nm in res:
		if String(res[nm][0].get("strategy", "")) != "":
			strat_names.append(nm)
	if not strat_names.is_empty():
		L.append("-- step 12c strategies, median per game: rest% (home+outing+church of 144) resort% | void periods (detained/detox/missing/sanatorium means) | arrests detox sanatorium boosts crime-job periods | full month | cash y2 / end / end p10 | S/A/B/C-/collapse% | grade mean")
		for nm in strat_names:
			L.append(strat_line(nm, bot_metrics(res[nm]), res[nm]))
		for sname in Bots.STRATEGIES:
			var m := strategy_metrics(res, sname)
			if not m.is_empty():
				L.append(strat_line("= " + sname + " (mean of roads)", m, []))
		var dm := strategy_metrics(res, "disciplined")
		if not dm.is_empty():
			var parts := PackedStringArray()
			for sname in ["bad_boy", "addict"]:
				var m2 := strategy_metrics(res, sname)
				if not m2.is_empty():
					parts.append("%s %s" % [sname, ff(m2["grade_mean"] - dm["grade_mean"], 2)])
			var bs := strategy_metrics(res, "bad_boy")
			if not bs.is_empty():
				parts.append("bad_boy S spread across roads %s pp [<=8]" % f0(bs["s_spread"]))
			L.append("   grade mean vs disciplined [+-0.3]: " + ", ".join(parts))
	return L


# ---------- step 12c: strategy metrics, coverage, guard ----------

const GRADE_SCORE := {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0}


## The metrics of one bot (the names are the keys of design/targets.json).
static func bot_metrics(rs: Array) -> Dictionary:
	var k := rs.size()
	var m := {}
	var rest := []
	var resort := []
	var void_ := []
	var keys := {"arrests": "count.arrest", "detox": "count.detox", "sanatorium": "count.sanatorium", "boosts": "count.boost",
		"crime_periods": "crime_job_periods"}
	var vals := {}
	for key in keys:
		vals[key] = []
	var fulls := []
	var y2 := []
	var end := []
	var gc := {"S": 0, "A": 0, "B": 0, "C-": 0, "collapse": 0}
	var gsum := 0
	var vparts := {"count.void.detained": 0, "count.void.detox": 0, "count.void.missing": 0, "count.void.sanatorium": 0}
	for r in rs:
		rest.append(100.0 * float(int(r["count.period.rest_home"]) + int(r["count.period.rest_outing"]) + int(r["count.period.job_church"])) / 144.0)
		resort.append(100.0 * float(r["count.outing.place_resort"]) / 144.0)
		var v := 0
		for vk in vparts:
			v += int(r[vk])
			vparts[vk] += int(r[vk])
		void_.append(v)
		for key in keys:
			vals[key].append(r[keys[key]])
		var fm = full_month(r)
		if fm != null:
			fulls.append(fm)
		y2.append(r["money"][mini(23, r["money"].size() - 1)])
		end.append(r["money"][r["money"].size() - 1])
		if r["ending"] == "end_collapse":
			gc["collapse"] += 1
		elif r["grade"] in ["S", "A", "B"]:
			gc[r["grade"]] += 1
			gsum += GRADE_SCORE[r["grade"]]
		else:
			gc["C-"] += 1
			gsum += GRADE_SCORE.get(r["grade"], 0)
	m["rest_share"] = float(med(rest))
	m["resort_share"] = float(med(resort))
	m["void_periods"] = float(med(void_))
	for key in keys:
		m[key] = float(med(vals[key]))
	m["full_month"] = float(med(fulls)) if float(fulls.size()) >= k * 0.5 else 99.0
	m["cash_y2"] = float(med(y2))
	m["cash_end"] = float(med(end))
	m["cash_end_p10"] = float(pct(end, 0.1))
	for g in gc:
		m["pct_" + g] = 100.0 * float(gc[g]) / float(k)
	m["c_or_less"] = m["pct_C-"] + m["pct_collapse"]
	m["grade_mean"] = float(gsum) / float(k)
	for vk in vparts:
		m["mean_" + vk.replace("count.void.", "void_")] = float(vparts[vk]) / float(k)
	return m


## Mean over the road bots of one strategy; bad_boy also gets s_spread (max - min of the roads' S%).
static func strategy_metrics(res: Dictionary, sname: String) -> Dictionary:
	var ms := []
	for nm in res:
		if String(res[nm][0].get("strategy", "")) == sname:
			ms.append(bot_metrics(res[nm]))
	if ms.is_empty():
		return {}
	var out := {}
	for key in ms[0]:
		var s := 0.0
		for m in ms:
			s += m[key]
		out[key] = s / ms.size()
	var lo := 999.0
	var hi := -999.0
	for m in ms:
		lo = minf(lo, m["pct_S"])
		hi = maxf(hi, m["pct_S"])
	out["s_spread"] = hi - lo
	return out


static func strat_line(nm: String, m: Dictionary, _rs: Array) -> String:
	return "%s rest %s%% resort %s%% | void %s (%s/%s/%s/%s) | arr %s detox %s sana %s boost %s crimeP %s | full %s | %s / %s / %s | %s/%s/%s/%s/%s | %s" % [
		nm.rpad(19), ff(m["rest_share"], 0, 2), ff(m["resort_share"], 0, 2), ff(m["void_periods"], 0, 2),
		ff(m["mean_void_detained"], 1), ff(m["mean_void_detox"], 1), ff(m["mean_void_missing"], 1), ff(m["mean_void_sanatorium"], 1),
		ff(m["arrests"], 0), ff(m["detox"], 0), ff(m["sanatorium"], 0), ff(m["boosts"], 0, 2), ff(m["crime_periods"], 0, 2),
		ff(m["full_month"], 0, 2), ff(m["cash_y2"], 0, 6, true), ff(m["cash_end"], 0, 6, true), ff(m["cash_end_p10"], 0, 6, true),
		f0(m["pct_S"]), f0(m["pct_A"]), f0(m["pct_B"]), f0(m["pct_C-"]), f0(m["pct_collapse"]), ff(m["grade_mean"], 2)]


## --coverage: events fired per game (all bots together), options picked, and the events that never fired.
func coverage(res: Dictionary) -> Array:
	var L := []
	var n := 0
	var ev := {}
	var op := {}
	for nm in res:
		for r in res[nm]:
			n += 1
			for k in r.get("events", {}):
				ev[k] = ev.get(k, 0) + int(r["events"][k])
			for k in r.get("options", {}):
				op[k] = op.get(k, 0) + int(r["options"][k])
	L.append("-- coverage over %d games: event fires per game (options picked: index x times)" % n)
	var d = Data.new()
	var never := []
	var row := PackedStringArray()
	for eid in d.events:
		if not ev.has(eid):
			never.append(eid)
			continue
		var o := PackedStringArray()
		var e: Dictionary = d.events[eid]
		for k in e.get("options", []).size():
			var key: String = "%s#%d" % [eid, k]
			if op.has(key):
				o.append("%dx%d" % [k + 1, op[key]])
		row.append("%s %s%s" % [eid, ff(float(ev[eid]) / n, 2), (" [" + " ".join(o) + "]") if o.size() > 0 else ""])
		if row.size() == 4:
			L.append("   " + " | ".join(row))
			row = PackedStringArray()
	if row.size() > 0:
		L.append("   " + " | ".join(row))
	L.append("never fired (%d): %s" % [never.size(), " ".join(never)])
	return L


## --guard: compares design/targets.json with the run. Every target is [lo, hi] (null = open); the range is widened by widen%.
## "strategies" are checked on the mean of the roads, "bots" on that bot; "grade_mean_vs_disciplined" is the difference to the
## disciplined strategy. Returns lines "PASS ..." / "FAIL ..." / "SKIP ..." (bot not in this run).
static func guard(res: Dictionary, tg: Dictionary, widen: float) -> Array:
	var L := ["-- guard (targets widened by %s%%)" % ff(widen, 0)]
	var dm := strategy_metrics(res, "disciplined")
	for sect in ["strategies", "bots"]:
		for who in tg.get(sect, {}):
			var m := {}
			if sect == "strategies":
				m = strategy_metrics(res, who)
				if not m.is_empty() and not dm.is_empty():
					m["grade_mean_vs_disciplined"] = m["grade_mean"] - dm["grade_mean"]
			elif res.has(who):
				m = bot_metrics(res[who])
				m.merge(extra_metrics(res[who]))
			for key in tg[sect][who]:
				if key == "note":
					continue
				var rg: Array = tg[sect][who][key]
				if m.is_empty() or not m.has(key):
					L.append("SKIP %s %s (not in this run)" % [who, key])
					continue
				var lo = rg[0]
				var hi = rg[1]
				var span := 0.0
				if lo != null and hi != null:
					span = float(hi) - float(lo)
				var wlo = null if lo == null else float(lo) - maxf(absf(float(lo)), span) * widen / 100.0
				var whi = null if hi == null else float(hi) + maxf(absf(float(hi)), span) * widen / 100.0
				var v: float = m[key]
				var ok: bool = (wlo == null or v >= wlo) and (whi == null or v <= whi)
				L.append("%s %s %s %s [%s, %s]" % ["PASS" if ok else "FAIL", who, key, ff(v, 1), "-" if wlo == null else ff(wlo, 1),
					"-" if whi == null else ff(whi, 1)])
	return L


## The step-8 metrics of one bot for the guard (keys of targets.json "bots").
static func extra_metrics(rs: Array) -> Dictionary:
	var k := rs.size()
	var plain := []
	var over := 0
	var y1 := []
	var end := []
	var kinds := {}
	for r in rs:
		var p: int = r["breakdown"]["training"] + r["breakdown"]["release"]
		plain.append(p)
		if p >= 311:
			over += 1
		y1.append(r["money"][mini(11, r["money"].size() - 1)])
		end.append(r["money"][r["money"].size() - 1])
		kinds[r["ending"]] = true
	return {"plain_rep": float(med(plain)), "over_311": 100.0 * over / k, "cash_y1": float(med(y1)),
		"cash_end_p90": float(pct(end, 0.9)), "big_win": ratio(sum_key(rs, "count.audition_won.big"), sum_key(rs, "count.audition.big")),
		"hit_rate": ratio(sum_key(rs, "count.hit"), sum_key(rs, "count.release")), "ending_kinds": float(kinds.size())}


static func Rules_truthy(v) -> bool:
	return v != null and v != 0
