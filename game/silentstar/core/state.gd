extends RefCounted
## 一局的全部状态，以及显示值、声望、名气档这些派生值。照抄 sim/state.py。
##
## 存档就是 to_dict() 的 JSON：两个随机流、所有计数器、旗标、已触发事件表、每本书的剩余点数（GDD 16）。
## 用法：
##   var st = State.new(data)；st.start(seed, [0, 0, 0])      开新局
##   var s = st.dumps()；var st2 = State.new(data)；st2.loads(s)  存读档

const Rng = preload("res://core/rng.gd")
const Rules = preload("res://core/rules.gd")
const Jsonx = preload("res://core/jsonx.gd")

const STATUS_KEYS := ["生病", "重病", "失控", "恋爱", "长约", "拍摄旬", "当月有拍摄", "有未开拍角色"]

const SAVE_KEYS := ["ym", "attr", "skill", "money", "corr", "favor", "known", "flags", "count", "tags", "weights",
	"books", "read_books", "items", "equip", "lifestyle", "idx", "status", "romance_months",
	"debt_months", "drug", "collapse_months", "forced_rest", "void_next", "exposed",
	"month_used", "fired", "ended", "finished", "story"]

var d                          # core/data.gd
var rng
var ym := 0                    # 月序，0 = 1926-01
var attr := {}                 # 基础属性（底值，不含装备）
var skill := {}                # 技能训练值
var money := 0
var corr := {}                 # 声望修正值
var favor := {}
var known := []
var flags := {}                # 旗标：名字 -> 整数（多数是 0/1，口音期这类是倒数）
var count := {}                # 计数器：旬数.<课> 成功期数.<工> 期数.<路> 计数.<名> …
var tags := {}                 # 戏路标签计数
var weights := {}              # 上板权重
var books := {}                # 持有、未读完的书：id -> 剩余点数
var read_books := []           # 读过的书
var items := []                # 持有的物品 id（可重复）
var equip := {"服装": null, "配饰": []}
var lifestyle := "life_normal"
var idx := {"生病指数": 0, "失控指数": 0}   # 月结时算，整月沿用
var status := {}
var romance_months := 0
var debt_months := 0
var drug := 0
var collapse_months := 0       # 生病指数 = 100 连续的月数
var forced_rest := 0           # 1 = 下月日程强制疗养院（重病）
var void_next := 0             # 1 = 下月日程作废
var exposed := 0               # 本月有没有曝光
var month_used := {}           # 本月已用的限次服务
var fired := {}                # 已触发事件：id -> 次数
var ended = null               # 结局 id
var finished := 0              # 1929-12 月结之后为 1
var story := {}                # 第 6 步：选片板、片约、事件记录、结局（见 new_story）
var debug_log := []            # 调试用，不进存档（Python 里叫 log）


## 第 6 步的状态，都能直接存进 JSON。各字段含义见 sim/state.py 的 new_story。
static func new_story() -> Dictionary:
	return {"板": null, "片": [], "上过板": {}, "待上板": [], "告密": 0, "末次": {},
		"剧本": {"自己写": 0, "Duv写": 0, "合写": 0}, "长约拒绝": -99, "转型": [0, null],
		"压丑闻年": 0, "放消息年": 0, "序号": 0, "结局": null}


func _init(data) -> void:
	d = data
	rng = Rng.new(0)
	attr = data.attr_init.duplicate()
	skill = data.skill_init.duplicate()
	money = data.money_init
	for r in data.roads:
		corr[r] = 0
	for n in data.npcs:
		favor[n] = data.npcs[n]["好感初值"]
		if data.npcs[n].get("开局认识", false):
			known.append(n)
	known.sort()
	for k in STATUS_KEYS:
		status[k] = 0
	story = new_story()


# ---------- 开局 ----------

## origin：开局三问各选第几项（从 0 数）。对应 Python 的 State.new。
func start(sd: int, origin := [0, 0, 0]) -> void:
	rng = Rng.new(sd)
	for i in mini(d.origins.size(), origin.size()):
		var o: Dictionary = d.origins[i]["选项"][origin[i]]
		if o["效果"]:
			Rules.apply_effect(self, o["效果"], "origin")
		for t in o["标签计数"]:
			tags[t] = tags.get(t, 0) + o["标签计数"][t]
		for f in o["旗标"]:
			flags[f] = 1
		for it in o["物品"]:
			items.append(it)
	update_indices()


# ---------- 日历 ----------

func month() -> Dictionary:
	return d.months[ym]


func date() -> String:
	return d.months[mini(ym, d.months.size() - 1)]["月"]


# ---------- 计数器 ----------

func cnt(k: String) -> int:
	return count.get(k, 0)


func inc(k: String, n := 1) -> void:
	count[k] = count.get(k, 0) + n


# ---------- 装备加成 ----------

## 持有即生效的物品：同一互斥组只取价格最高的一件；同一件持有多个只算一次。
func _held() -> Array:
	var uniq := {}
	for iid in items:
		uniq[iid] = true
	var ids := uniq.keys()
	ids.sort()
	var best := {}
	var out := []
	for iid in ids:
		var it: Dictionary = d.items[iid]
		if it["类"] != "持有":
			continue
		var g = it.get("互斥组")
		if g == null:
			out.append(iid)
		elif not best.has(g) or it["价格"] > d.items[best[g]]["价格"]:
			best[g] = iid
	var gs := best.keys()
	gs.sort()
	for g in gs:
		out.append(best[g])
	return out


## 装备、持有物给的加成：{属性或技能: 值}。
## 服装按 GDD 14.1：服装值 × (50 + 打扮)/100，向零截断；这里的打扮是训练值加非服装加成。
func bonus() -> Dictionary:
	var b := {}
	var plain: Array = _held() + equip["配饰"]
	for iid in plain:
		for e in Rules.parse_effect(d.items[iid]["效果"]):
			var op: String = e[1]
			if (op == "+" or op == "-") and e[3] == "":
				b[e[0]] = b.get(e[0], 0) + (e[2] if op == "+" else -e[2])
	var cl = equip["服装"]
	if cl != null:
		var f: int = 50 + skill["打扮"] + b.get("打扮", 0)
		for e in Rules.parse_effect(d.items[cl]["效果"]):
			var op: String = e[1]
			if (op == "+" or op == "-") and e[3] == "":
				var v: int = e[2] if op == "+" else -e[2]
				b[e[0]] = b.get(e[0], 0) + Rules.tdiv(v * f, 100)
	return b


# ---------- 显示值 ----------

## 属性或技能的显示值。条件、成功线、判定都用它。b 不传就现算。
func val(name: String, b = null) -> int:
	if b == null:
		b = bonus()
	if attr.has(name):
		var rg: Array = d.attr_range[name]
		return clampi(attr[name] + b.get(name, 0), rg[0], rg[1])
	if skill.has(name):
		var v: int = skill[name] + b.get(name, 0)
		var sb = d.skill_bonus.get(name)
		if sb != null:
			v += mini(Rules.fdiv(val(sb["属性"], b), sb["除"]), sb["上限"])
		return maxi(0, v)
	push_error("不是属性也不是技能：%s" % name)
	return 0


func rep(road: String, b = null) -> int:
	if b == null:
		b = bonus()
	var v: int = corr[road]
	for s in d.road_skills[road]:
		v += val(s, b)
	return clampi(v, d.rep_range[0], d.rep_range[1])


func level(road: String) -> int:
	var r := rep(road)
	var lv := 0
	for i in d.level_gate.size():
		if r >= d.level_gate[i]:
			lv = i
	return lv


func fame_tier() -> int:
	var f: int = attr["名气"]
	for i in d.fame_tiers.size():
		if d.fame_tiers[i][0] <= f and f <= d.fame_tiers[i][1]:
			return i
	return d.fame_tiers.size() - 1


## 最高基础属性（GDD 10）：体力、教育、义气、相貌、自律、犯罪里最高的；并列取靠前的。
func highest_base() -> String:
	var b := bonus()
	var best := ""
	var bv := 0
	for n in ["体力", "教育", "义气", "相貌", "自律", "犯罪"]:
		var v := val(n, b)
		if best == "" or v > bv:
			best = n
			bv = v
	return best


# ---------- 指数 ----------

func calc_indices() -> Array:
	var b := bonus()
	var tired := val("疲劳", b)
	var sick := clampi(tired - val("体力", b), 0, 100)
	var wild := clampi(tired - val("自律", b), 0, 100)
	return [sick, wild]


## 月结时算两个指数并更新状态（GDD 10）。整月沿用这次的结果。
func update_indices() -> void:
	var si := calc_indices()
	var r: Dictionary = d.idx_rule
	idx["生病指数"] = si[0]
	idx["失控指数"] = si[1]
	status["生病"] = 1 if si[0] >= r["生病指数"]["状态线"] else 0
	status["重病"] = 1 if si[0] >= r["生病指数"]["重病线"] else 0
	status["失控"] = 1 if si[1] >= r["失控指数"]["状态线"] else 0


# ---------- 金钱 ----------

func add_money(n: int) -> void:
	money = mini(money + n, d.money_cap)


# ---------- 存档 ----------

func to_dict() -> Dictionary:
	var out := {"版本": 1, "rng": rng.dump()}
	for k in SAVE_KEYS:
		out[k] = get(k)
	return Jsonx.copy(out)


## 和 Python 的 State.dumps 逐字节一致。
func dumps() -> String:
	return Jsonx.dumps(to_dict())


func from_dict(sv: Dictionary) -> void:
	rng = Rng.load_from(sv["rng"])
	for k in SAVE_KEYS:
		if sv.has(k):
			set(k, Jsonx.copy(sv[k]))


func loads(s: String) -> void:
	from_dict(Jsonx.parse(s))
