# 平衡记录

每轮改数值在“改动记录”里加一段：改了什么、为什么、前后对比。改完重跑 Godot 报告（第 12b 步起，命令见 `README.md`；`sim/` 冻结），把下面“现在的报告”整段换掉。

## 第 12c 步 c3 之后

定下来的数、护栏、交给 Opus 的活在 `design/C3_ROUND1.md`。每一轮的前后对比在下面的改动记录里。**“现在的报告”是 c3 第 3 轮之前跑的，用药线的几行还是旧规则的，等 Opus 重跑。**

## 知道但不用修的

- **两路（硬汉+情人）**只有 22% 的局两路都练满，期末主路声望 318。用户确认：没事，不用修。
- 小片拿到率 100%：小片当保底。
- 机器人不写剧本、不放消息、不谈恋爱。这些对钱和声望的影响没测，等有了界面由用户试玩。

## 用户已同意的决定（第 8 步，仍然有效的）

- S 线 421 → 451（A 381、B 311、C 211 没动）。练满以外有五处往上加，正常打完的专练玩家在 440 上下，421 人人都过；451 正好是 9 级的门槛。
- 手腕路收钱的做法：片厂区逛街 2 → 8 一天（当作应酬），谈判的片酬系数 /400 → /600。
- 打斗的体力加成从“体力/10 封顶 30”降到“体力/30 封顶 10”，开局硬汉声望 33 → 27。
- 新加舞鞋（体态 +5，12 元）、化妆箱（打扮 +5，25 元）。
- 无名对手的成长改成每档各自的涨级月。

## 改动记录

### 第 8 步第一轮

先查了钱和声望的来源（给每一笔进出按来源记账，40 局平均）。

钱（专练硬汉，一局合计）：中片片酬 10.0k、大片片酬 6.9k（含配角）、分红 3.6k、替身打工 3.9k、年度奖金 2.8k、长约月薪 2.5k、码头两个赚钱事件 2.0k；支出是生活费 13.9k、学费 5.9k。和“至少一天成功算一期”关系不大，主要是片子拿得太多：中片拿到率 87%–89%，一局主演 12 部中片、2–3 部大片。

声望（专练硬汉，期末 540 = 练满 300 + 体力加成 30 + 下面这些）：年度大事 +112、上映 +82、机遇 +60 到 +100（两个本路机遇几乎必出，前辈的机遇必出）。买装备再加 40–70。

| 改了什么 | 原来 | 现在 | 为什么 |
|---|---|---|---|
| 上映修正 小/中/大 | 2/5/10 | 2/4/8 | 一局 15 部主演，原来合计 +70 到 +90，预算是 +20 到 +35 |
| 大卖线 | S ≥ 1.3B | S ≥ 1.4B | 大卖率 18%–25% 降到一成 |
| 年度大事 修正；奖金 | 40/20/10；1000/500/200 | 20/10/5；500/250/100 | 见上 |
| 机遇 | +25 / +30，每月 1/6、1/8 | +20 / +25，每月 1/12、1/16 | 条件一满足几乎必出 |
| 机遇条件 | 事故：亲自上 ≥2；探险队：硬汉 ≥300；瓦伦的位置：情人 ≥280；摆平：人脉 80 谈判 60 | ≥4；≥350；≥330；人脉 100 谈判 80 | 原条件专练的人自动满足 |
| 前辈的机遇；前辈的装备 | +20；+20/+10 | +10；+10/+5 | 练满必得，等于白送 |
| 可买装备的技能加成 | 拳套 +10、相机 +15、打字机 +15、留声机 +10/+5、车 +10/+15/+15 … | 拳套 +5、相机 +6、打字机 +6、留声机 +5/+3、车 +3/+5/+8 … | 文化路花 120 元就 +35；四路拉平到 +15 到 +20 |
| 打斗的体力加成 | 体力/10，封顶 30 | 体力/30，封顶 10 | 硬汉路白多 30 |
| S 线 | 421 | 451 | 见上 |
| 无名对手成长 | 三档都是 1927-07、1929-01 各涨一级 | 中片、大片第一场改为 1926-10、1927-07、1928-07 各涨一级；小片不变 | 玩家第 18 个月到 7 级，对手还是 4–6 级，中片从第二年起稳赢 |
| 有名对手 | 范班克 硬 9/8/7 手 6；库普 1929 硬 8；诺瓦 情 8；乔森 手 7；巴里 1928 起文 9 | 范班克 硬 9（1929 起 8）手 8；库普 1929 硬 9；诺瓦 1929 情 9；乔森 手 8（1929 起 9）；巴里 1929 起文 9 | 手腕色没有强对手，大片 60% 通过、年度次次第一；后两年各路的年度第一都没人争 |
| 学费/天 | 拳馆 12/16/20/24，马术 16/26/38/50，表演 12/16/20/24，舞蹈 10/14/18/24，礼仪 10/14/18/22，家教 8/10/12/14 | 9/12/15/18，14/22/30/40，8/11/14/17，6/9/12/15，6/9/12/15，6/9/12/15 | 片子少了以后前两年更缺钱，练满拖到 22–26 个月 |
| 书 | 收益 +1 / +r(1,2) / +r(1,2)；价格 5/25/90 | +r(1,2) / +r(1,3) / +r(1,3)；15/60/150 | 文化路第 27 个月才练满；读书不花钱，涨一点价 |
| 逛街花费/天 | 片厂区 2、市中心 2、海滨 4、码头 1 | 8、3、10、2 | 手腕、情人常去的地方当应酬收钱 |
| 长约月薪 | 250 | 150 | 后两年白拿 2.5k |
| 替身日薪 | 15 | 10 | 硬汉路练胆识的工，边练边赚 |
| 谈判的片酬系数 | /400 | /600 | 手腕路片酬合计比别的路多 3k–4k |
| 码头两个赚钱事件 | +100、+150 | +60、+100 | 常去码头的人一局拿 2k |

没改的：片酬 300/800/2500、分红 S×2、生活费表、名气系数和衰减。期末名气中位 408–553，和 N63 设想的“第三年当红、第四年前后巨星”一致。

机器人和报告也改了：机器人月初买本路装备（`--no-buy` 关掉）；专练文化缺钱时先去报馆、给画家当模特（两个文化机遇要这两种工的期数）；专练情人改去市中心休息；犯罪线每月去一旬拳馆。报告加了声望拆分、分档拿到率、各年名气、结局档次、不买装备的对照；去掉了和 N60 并排的一段（粗算脚本已删）。

### 删股票、休息合并成两种（第 9、8b 步，用户的规则改动，不是调数值）

- 删股票系统（存款 5000 开户、风声、股灾的数值效果）。机器人本来不买股票，报告没变。
- 休息只留在家（Sil 陪着：疲劳每天 −5、Sil 好感每旬 +2）和外出（选去处）；陪同休息并进在家，度假变成去处“度假村”（每天按名气档 6/8/12/18/30，疲劳每天 −30）；疗养院只在重病时强制。
- 前后对比（200 局）：四种专练和只读书文化的各项几乎不变（专练情人期末现金中位 2,923 → 2,945）；两路的第 4 年名气 242 → 244、期末主路声望 318 → 331；乱选的负债月数不变。都在目标内，没有要修的。
- 机器人照旧不去度假村。

### 机器人随机数换成 PCG32（第 12b 步）

机器人随机数换成 PCG32，数字有小幅变动，规则没变。（换随机数前后各跑一遍 200 局核对过：只有乱选机器人 `random_pick` 的数字变了，另外七种用不到这条随机流，输出逐字相同。下面“现在的报告”比上一版多出的差别来自上一版报告没有随 8b 的改动重跑，不是这次造成的。）

### 第 12c 步 c1、c2（规则改动和新机器人，不是调数值）

- 规则：上课疲劳每天 +3、看书 +2；城里四处外出 −10 → −3，度假村 −30 → −20 并加“玩过头”（权重 1/4，疲劳 +15）；年度大事参加时疲劳 +15。毒品改成街道动作“提神”（20 元，疲劳 −40，自律 −5，药瘾点数 +1；点数 1/5/10 为阶段 1/2/3；阶段 2 某月没用疲劳 +20，阶段 3 每月体力 −5、相貌 −3；自律 ≥150 不能用；“加深”删除；Sil/Duv 在阶段 3 才拉他去戒）。被捕：罚款 `max(200, 30%)`、拘留作废下一旬、3 个月不能报大片；搜查概率 ×(1+犯罪/100)，看本路技能。道德条款改成被捕或丑闻后 3 个月。硬汉、情人、手腕各两级犯罪工（舞厅伴舞、私人男伴改成情人路的一、二级；手腕新加两种占位）。疗养院出院相貌 −10、体态 −10，1/3 “疗养院里的人”。结局“演员”排到“黑暗”前。
- 机器人：新加 `disciplined_*`（4 路）、`bad_boy_*`（硬汉、情人、手腕）、`addict_*`（4 路）。所有机器人（乱选的除外）按偏好表选事件选项，以前一律选第一个；做计划时上课、看书的疲劳按表估。这两处让旧机器人的数也变了。
- 报告加了“来自事件”和“12c 策略”两段，`--coverage`、`--guard`；`check.py` 第 5 步改用 Godot 跑 30 局对护栏。
- 前后对比：专练四路练满月 19–21 → 24–33；期末现金中位 3.7k–4.3k → 0.7k–1.2k；专练情人 S 55% → 22%。其余见下面的报告。

### 第 12c 步 c3 第 0 轮：练得慢一点、学费贵一点

只动表。

| 改了什么 | 原来 | 现在 |
|---|---|---|
| 年度名次声望修正（奖金不动） | +20 / +10 / +5 | +8 / +4 / +2 |
| 八个机遇的声望修正（前辈的 +10 不动） | +25 / +30 | +15 |
| 上课 3、4 级主收益上限 | 拳馆打斗 [1,2][1,3]；马术 [1,3][1,4]；表演、舞蹈、礼仪 [1,3][2,4]；家教教育 [3,8][4,12] | [1,1][1,2]；[1,2][1,3]；[1,2][2,3]；[3,6][4,9] |
| 学费/天 | 拳馆 9–18、马术 14–40、表演 8–17、另三门 6–15 | ×1.5 向上取整 |
| 书 | 进阶、专著每天 +r(1,3) | +r(1,2)，点数 35 不动 |
| 明星助理 | 日薪 3；谈判、人脉、生意各 +0/1 | 日薪 1；谈判、人脉各 +0/1 |
| `evt_birthday` | 没定日期 | 8 月 19 日 |

- 书没有按原计划把点数降到 28：点数是一本书能给的技能总量，28 够不着技能上限，自律文化只有 40% 的局练满。改成降每天收益。
- 年度名次先试 +10/+5/+2，自律线 A 70%，再降到 +8/+4/+2。

| 200 局 | 之前 | 之后 |
|---|---|---|
| 自律线练满月（硬汉/情人/文化/手腕） | 22 / 25 / 24 / 24 | 28 / 30 / 31 / 27 |
| 自律线 S/A/B，均分 | 32 / 66 / 2，3.30 | 0 / 64 / 35，2.64 |
| 自律线第 2 年末 / 期末现金 | 1,064 / 3,867 | 715 / 1,496 |

### 第 12c 步 c3 第 1 轮：坏孩子线的钱和被捕

| 改了什么 | 原来 | 现在 | 为什么 |
|---|---|---|---|
| 犯罪工的偷懒（`reckless_slack`） | 失控指数高时偷懒 | 不偷懒 | 坏孩子自律是 0，二级工一旬 400 实际只拿到 170 |
| 搜查判定 | `技能 + r0(20) >= 线` | `r0(技能) + 20 >= 线` | 原来技能过 60 就永远不被抓 |
| 搜查概率 `raid_crime_div` | 100 | 70 | 码头不再白抓人以后被捕不到 3 次 |
| 拘留 `detain_periods` | 1 旬 | 2 旬 | 作废的旬要到 6–10 |
| 二级犯罪工日薪 | 40 | 50 | |
| 码头“酒吧后门的生意” | 只有“做” | 加“不做” | 自律硬汉为了探险队去码头，中位被捕 1 次 |
| 坏孩子机器人 | 钱低于一条线才做犯罪工 | 二级工开放后每月第一旬固定做；月末失控指数 <60 | 原来钱一过线就去上副路的课，现金停在线上（2.6k），不是挣不到 |
| 三条线的硬汉路 | 不去码头 | 先去码头凑满 3 次 | 探险队机遇的条件 |

度假村涨价（原计划的第 2 轮）取消。对照（各 100 局）：

| 实验 | 结果 |
|---|---|
| 坏孩子，度假村现价 / ×2 / ×3 | 期末现金 5.9k / 3.9k / 2.4k |
| 自律线疲劳 ≥50 时改去度假村，现价 / ×2 / ×3 | 练满月 30 → 32 / 34 / 34，均分 2.67 → 2.59 / 2.54 / 2.49 |
| 坏孩子月末失控指数到 30 / 55 才歇；度假村每天 −25 / −30 | 休息占比都是 32%，不变 |

自律线去度假村在现价下已经是亏的（它缺的是钱，不是旬数）。坏孩子休息 32% 是月节奏，每月最后一旬必歇。

| 200 局 | 第 0 轮之后 | 第 1 轮之后 | 目标 |
|---|---|---|---|
| 坏孩子第 2 年末 / 期末现金 | 585 / 753 | 2,119 / 5,408 | 2k–4k / 5k–10k |
| 被捕 / 作废的旬 | 4 / 3.9 | 3.3 / 6.9 | 3–5 / 6–10 |
| 练满月（硬汉/情人/手腕） | 硬汉 50% 的局练不满 | 27 / 25 / 31 | 24–30 |
| S/A/B/C 以下，均分差 | 0 / 44 / 38 / 18，−0.45 | 0 / 73 / 26 / 2，+0.02 | ±0.3 |
| 自律线被捕 | 0 | 0 | 0 |

护栏挪了五处（理由在 `targets.json` 的说明里）：练满月自律 27–33、坏孩子 24–30；自律线期末现金 1k–3k；坏孩子休息 28–34%、期末现金 5k–10k。

### 第 12c 步 c3 第 3 轮：药贩、药和毒瘾

规则整个换了（GDD 5.8.1，用户逐条定的方向）：药贩看概率刷新、存货在药贩身上、价格浮动、药大概率状态好、暗掷上瘾、断药发作、上瘾后自己用药。原来的“提神”（20 元、自律 −5、点数过线换阶段）删除。机器人换成“自律线的打法 + 买药”。

各 100 局，情人、手腕两路，数是相对自律线的均分差：

| 调了什么 | 碰到就买 | 发作后戒掉 | 只在拍摄旬用 |
|---|---|---|---|
| 神仙附体 10%，药价 60–200 | −0.14 | −0.11 | −0.17 |
| 神仙附体 30% | −0.09 | −0.03 | −0.16 |
| 药价 20–190，神仙附体的主演片另加声望 30（已否掉） | +0.03 | +0.02 | +0.15，S 12% |
| **现在的数**：药价 20–190，神仙附体 30%，拍摄表现 P +0.2，不另给声望 | −0.06 | −0.01 | −0.09 |

- 现在三种用法之间没有优劣，也不比不碰差多少，S 都是 0%。
- “只在拍摄旬用”有 39%–59% 的局拍出过神仙附体的大卖片，均分却没动：一次大卖只多 +2/+4/+8 声望。大卖交给 Opus 重调。
- 坏孩子 + 买药（`wild`）：0/44/37/5/14（S/A/B/C 以下/倒下），均分差 −0.60。这是机器人打法的问题（买光、从不主动戒），不调数，见 `C3_ROUND1.md`。

## 现在的报告

第 12c 步 c3 第 0、1 轮和 Fable 复核之后，Godot `report.gd --n=200 --bots=all`（4 个进程分段再 `--merge`，约 7 分钟）。护栏的逐条结果用 `--guard=design/targets.json` 看；现在不过的 21 条：自律线和坏孩子线的档次分布 7 条（等 NPC 线和机遇）、嗑药线 9 条（等第 3 轮）、专练机器人 5 条。

```
== each bot 200 games (seeds 1-200), cards played greedy; targets: PLAN step 8 ==
-- full-training month median (10%-90%) [target 16-21] | months with rep >= 210 | main-road rep median at months 12/24/36/48
only_tough full 39(33–45)      210:22(18–28)    151/251/350/378
only_lover full 42(36–47)[77%] 210:25(19–36)    154/205/299/373
only_culture full 39(33–46)[25%] 210:29(19–45)[67%] 130/167/218/255
only_savvy full 33(29–36)      210:20(18–21)    112/294/366/376
two_roads full —              210:43(35–48)[14%] 99/142/161/191
crime_line full —              210:24(22–34)    138/210/237/247
books_culture full 37(31–43)      210:20(16–25)    140/273/353/370
random_pick full —              210:44(36–47)[22%] 84/112/144/180
disciplined_tough full 30(25–35)      210:18(15–22)    163/300/371/392
disciplined_lover full 30(25–40)      210:19(14–27)    170/277/369/393
disciplined_culture full 31(26–42)      210:21(15–27)    137/267/372/389
disciplined_savvy full 27(24–30)      210:19(17–21)    99/325/368/385
bad_boy_tough full 27(22–32)      210:12(11–14)    217/343/372/393
bad_boy_lover full 25(22–28)      210:14(12–16)    197/353/381/401
bad_boy_savvy full 31(28–36)      210:21(19–25)    95/281/371/394
addict_tough full 35(28–42)[51%] 210:21(15–33)    152/244/321/349
addict_lover full 33(27–42)[81%] 210:20(14–34)    165/253/353/378
addict_culture full 34(25–45)[41%] 210:27(16–40)[77%] 130/162/248/301
addict_savvy full 26(23–30)      210:18(16–21)    115/335/369/385
-- final main-road rep breakdown (mean): training+gear and stamina+releases+annual+opportunities | full training plus plain releases (no gear) median [311-340], over 311 [90%] | grade S/A/B/C/D %
only_tough 299+35+15+11+17 = 378 | 314 over 311  68% | 0/45/54/0/0
only_lover 291+35+14+ 6+17 = 373 | 311 over 311  52% | 0/29/60/11/0
only_culture 215+20+10+ 6+18 = 255 | 212 over 311  15% | 0/13/20/33/33
only_savvy 300+27+13+13+24 = 376 | 312 over 311  58% | 0/35/64/0/0
two_roads 175+ 8+ 7+ 6+ 0 = 191 | 179 over 311   0% | 0/0/0/14/85
crime_line 224+10+ 6+ 7+ 0 = 247 | 230 over 311   0% | 0/0/0/100/0
books_culture 299+32+15+13+10 = 370 | 314 over 311  69% | 0/13/85/1/0
random_pick 185+ 0+ 2+ 1+-8 = 180 | 186 over 311   0% | 0/0/0/21/79
disciplined_tough 300+40+19+13+21 = 392 | 317 over 311  79% | 0/75/24/0/0
disciplined_lover 300+37+20+10+26 = 393 | 318 over 311  78% | 1/69/29/0/0
disciplined_culture 297+34+15+14+24 = 389 | 313 over 311  64% | 0/71/26/2/0
disciplined_savvy 300+30+15+13+28 = 385 | 314 over 311  70% | 0/59/40/0/0
bad_boy_tough 300+42+18+15+12 = 393 | 316 over 311  77% | 0/70/28/1/0
bad_boy_lover 300+37+25+14+23 = 401 | 324 over 311  89% | 0/76/23/0/0
bad_boy_savvy 298+34+13+13+28 = 394 | 312 over 311  56% | 0/72/25/1/1
addict_tough 264+30+ 7+ 9+ 0 = 349 | 302 over 311  20% | 0/21/38/26/14
addict_lover 287+33+13+ 8+17 = 378 | 312 over 311  52% | 0/42/43/11/3
addict_culture 239+21+ 8+ 8+19 = 301 | 258 over 311  24% | 0/24/25/28/22
addict_savvy 298+30+13+14+27 = 385 | 314 over 311  66% | 0/61/37/2/0
-- cash at each year end, median (years 1-4) [first two years <1000] | final p90 [<10k] | final >10k | debt months | film fees total, gear spend (mean)
only_tough 225 / 477 / 621 / 811            p90   1,460  >10k   0%  debt  0.1 |  7,896   459
only_lover 147 / 221 / 444 / 966            p90   2,290  >10k   0%  debt  0.4 |  8,030   122
only_culture 214 / 170 / 208 / 314            p90     847  >10k   0%  debt  0.3 |  5,988   161
only_savvy 402 / 655 / 900 / 767            p90   1,926  >10k   0%  debt  0.3 |  9,651   578
two_roads 198 / 264 / 231 / 309            p90     517  >10k   0%  debt  0.0 |  6,089   118
crime_line 823 / 1,010 / 1,242 / 1,983      p90   3,102  >10k   0%  debt  0.0 |  4,884     0
books_culture 342 / 418 / 798 / 2,546          p90   4,398  >10k   0%  debt  0.1 |  8,455   402
random_pick -694 / -1,407 / -1,802 / -1,994  p90    -168  >10k   0%  debt 43.8 |  1,927     0
disciplined_tough 307 / 607 / 830 / 1,295          p90   2,465  >10k   0%  debt  0.0 | 10,018   966
disciplined_lover 244 / 404 / 832 / 1,089          p90   3,108  >10k   0%  debt  0.1 | 10,376   150
disciplined_culture 351 / 380 / 723 / 841            p90   2,615  >10k   0%  debt  0.1 |  8,137   390
disciplined_savvy 484 / 1,433 / 1,407 / 2,669      p90   4,812  >10k   0%  debt  0.0 | 10,880 1,613
bad_boy_tough 409 / 925 / 2,607 / 3,644        p90   6,236  >10k   0%  debt  0.4 |  8,705 4,048
bad_boy_lover 316 / 3,224 / 5,597 / 6,286      p90  10,259  >10k  10%  debt  0.2 | 10,099   166
bad_boy_savvy 349 / 2,209 / 3,573 / 6,294      p90   9,905  >10k   9%  debt  0.8 |  8,961 5,563
addict_tough 196 / 286 / 264 / 193            p90   1,018  >10k   0%  debt 12.0 |  6,997   339
addict_lover 198 / 262 / 538 / 652            p90   1,752  >10k   0%  debt  4.6 |  9,051   131
addict_culture 252 / 186 / 287 / 347            p90   1,334  >10k   0%  debt  4.3 |  6,038   195
addict_savvy 413 / 1,269 / 1,426 / 2,247      p90   4,468  >10k   0%  debt  0.8 | 10,292 1,404
-- auditions per game, won% small/medium/big [big 10-35%] | releases per game, hit% [10%] flop% | leads small/medium/big | supports, breaches
only_tough 18.1 games 100/57/21% (big 0.2 games) | release 15.1 hit   3% flop  39% | 5.5/6.6/0.0 | 3.0 0.1
only_lover 19.0 games 100/53/22% (big 0.4 games) | release 15.1 hit  10% flop  20% | 5.5/6.7/0.1 | 2.8 0.0
only_culture 17.9 games 100/42/23% (big 0.1 games) | release 15.0 hit   4% flop  25% | 10.3/2.8/0.0 | 1.9 0.0
only_savvy 18.7 games 100/60/13% (big 0.3 games) | release 15.4 hit   2% flop  28% | 5.5/7.5/0.0 | 2.4 0.0
two_roads 19.1 games 100/38/nan% (big 0.0 games) | release 14.7 hit   9% flop  24% | 9.5/3.1/0.0 | 2.1 0.0
crime_line 17.8 games 100/39/nan% (big 0.0 games) | release 14.3 hit   1% flop  67% | 10.2/2.3/0.0 | 1.8 0.5
books_culture 18.5 games 100/53/18% (big 0.2 games) | release 15.3 hit   4% flop  26% | 6.6/6.0/0.0 | 2.7 0.0
random_pick 10.0 games 84/11/nan% (big 0.0 games) | release  7.1 hit   0% flop  58% | 6.6/0.1/0.0 | 0.4 0.4
disciplined_tough 18.4 games 100/63/18% (big 0.8 games) | release 15.7 hit   6% flop  28% | 4.6/8.4/0.1 | 2.5 0.2
disciplined_lover 19.0 games 100/60/21% (big 1.5 games) | release 15.7 hit  11% flop  21% | 3.9/8.5/0.2 | 3.0 0.0
disciplined_culture 18.5 games 100/55/14% (big 0.5 games) | release 15.5 hit   4% flop  32% | 6.4/6.5/0.0 | 2.6 0.0
disciplined_savvy 18.5 games 100/64/14% (big 1.2 games) | release 16.0 hit   5% flop  24% | 5.0/8.4/0.1 | 2.4 0.0
bad_boy_tough 17.7 games 100/66/21% (big 0.2 games) | release 15.5 hit   6% flop  42% | 4.3/8.8/0.0 | 2.4 0.7
bad_boy_lover 18.3 games 100/71/20% (big 0.8 games) | release 16.0 hit  14% flop  20% | 2.6/11.0/0.1 | 2.2 0.7
bad_boy_savvy 18.1 games 100/60/5% (big 0.1 games) | release 15.5 hit   5% flop  24% | 7.2/6.4/0.0 | 1.9 0.4
addict_tough 18.1 games 100/57/0% (big 0.0 games) | release 13.7 hit   1% flop  71% | 6.1/5.3/0.0 | 2.3 1.6
addict_lover 18.9 games 100/58/16% (big 0.7 games) | release 15.0 hit   5% flop  42% | 4.4/7.7/0.1 | 2.8 0.7
addict_culture 17.7 games 99/48/10% (big 0.1 games) | release 14.7 hit   3% flop  51% | 9.9/3.1/0.0 | 1.6 0.5
addict_savvy 17.9 games 100/68/14% (big 0.6 games) | release 15.5 hit   3% flop  37% | 5.3/8.1/0.0 | 2.0 0.4
-- median fame at each year end | final fame tier unknown/familiar/famous/hot/superstar % | mean annual rank (years 1-4) | collapse% | endings (kinds [>=3]; top four)
only_tough 145/177/200/231  0/0/84/16/0    rank 4.0/2.3/2.1/2.3  collapse 0%  endings 8 kinds: tough_stunt42% tough_adventurer30% act_action12% tough_rider11%
only_lover 162/207/282/352  0/0/28/67/4    rank 5.5/4.0/3.1/2.1  collapse 0%  endings 12 kinds: act_lover35% lover_widow19% act_art17% lover_dance_hall9%
only_culture 124/155/172/197  0/1/96/3/0     rank 3.2/3.7/3.1/2.9  collapse 0%  endings 5 kinds: cult_editor33% cult_street_photo33% cult_tabloid30% act_voice2%
only_savvy 122/156/186/245  0/1/79/20/0    rank 2.4/3.0/2.0/2.3  collapse 0%  endings 7 kinds: biz_broker61% biz_agent19% act_voice8% act_character6%
two_roads 162/191/205/235  0/0/94/5/0     rank 4.8/3.1/3.2/3.2  collapse 0%  endings 7 kinds: biz_sales69% tough_thug13% biz_boss7% act_second5%
crime_line 125/120/106/97   8/66/24/1/0    rank 4.5/2.6/3.2/3.0  collapse 0%  endings 4 kinds: dark_thug_boss60% dark_boss39% act_lowbudget0% act_silent0%
books_culture 124/160/211/253  0/0/75/24/0    rank 3.1/2.8/1.9/2.0  collapse 0%  endings 5 kinds: cult_tabloid74% act_voice19% act_art4% act_lowbudget1%
random_pick 95/62/41/24      95/4/0/0/0     rank 5.5/5.3/5.2/5.0  collapse 0%  endings 7 kinds: biz_sales42% dark_prison26% dark_con14% biz_boss14%
disciplined_tough 144/182/219/312  0/1/43/53/2    rank 3.7/2.0/2.0/2.1  collapse 0%  endings 9 kinds: act_voice40% tough_adventurer27% tough_rider17% act_action8%
disciplined_lover 161/219/316/413  0/0/9/74/16    rank 5.3/3.6/2.0/2.0  collapse 0%  endings 10 kinds: act_lover43% act_art17% act_voice11% lover_widow9%
disciplined_culture 122/151/196/249  0/0/74/25/0    rank 3.1/2.8/1.6/2.0  collapse 0%  endings 6 kinds: cult_writer46% cult_screenwriter26% act_voice21% act_art3%
disciplined_savvy 120/157/218/324  0/0/32/68/0    rank 2.7/2.9/2.0/2.2  collapse 0%  endings 7 kinds: act_voice53% biz_broker19% biz_agent13% act_undefined4%
bad_boy_tough 131/154/156/195  0/24/55/18/2   rank 2.5/2.0/2.0/2.2  collapse 0%  endings 7 kinds: dark_thug_boss80% act_voice11% act_action5% act_undefined1%
bad_boy_lover 165/209/281/318  0/1/45/34/19   rank 5.0/2.4/1.7/1.9  collapse 0%  endings 10 kinds: dark_thug_boss41% act_lover25% idol8% act_character7%
bad_boy_savvy 115/127/146/219  1/25/43/29/1   rank 2.8/2.9/1.9/2.2  collapse 0%  endings 10 kinds: dark_con68% act_voice9% act_lover7% act_character4%
addict_tough 128/139/136/140  4/55/37/3/0    rank 3.9/2.5/2.5/2.7  collapse 0%  endings 13 kinds: tough_thug52% dark_thug_boss20% dark_con19% act_voice2%
addict_lover 149/190/249/289  0/5/51/42/1    rank 5.3/3.7/2.5/2.2  collapse 0%  endings 16 kinds: lover_widow37% act_lover25% act_voice9% lover_dance_hall9%
addict_culture 107/126/140/152  1/46/46/6/0    rank 3.2/3.6/2.8/2.7  collapse 0%  endings 7 kinds: cult_tabloid43% cult_editor28% cult_street_photo22% act_voice4%
addict_savvy 109/136/186/274  0/10/54/35/0   rank 2.3/2.8/1.9/2.2  collapse 0%  endings 11 kinds: biz_agent32% biz_broker30% act_voice25% act_lover5%
-- without buying gear: final cash median / p90 | final main-road rep median | grade S/A/B/C/D %
only_tough     588 /   1,467 | 341 | 0/0/97/2/0
only_lover     802 /   1,410 | 326 | 0/0/76/23/0
only_culture     313 /     916 | 264 | 0/0/36/27/36
only_savvy     582 /   1,367 | 345 | 0/0/100/0/0
-- from events, median per game: main-road rep from events (skills + rep_bonus) [<=30] | event money net, % of all money gained [+-10%] | event fatigue net per year [+-60] | opportunity rep
only_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 10
only_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 10
only_culture ev rep  12 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 15
only_savvy ev rep  43 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
two_roads ev rep  66 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 0
crime_line ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 0
books_culture ev rep  25 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 10
random_pick ev rep  15 | money      0 (  0.0%) | fatigue/yr   12 | opp rep 0
disciplined_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
disciplined_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
disciplined_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
disciplined_savvy ev rep   9 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
bad_boy_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   31 | opp rep 25
bad_boy_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   38 | opp rep 25
bad_boy_savvy ev rep   5 | money      0 (  0.0%) | fatigue/yr   39 | opp rep 40
addict_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr  -15 | opp rep 10
addict_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr  -11 | opp rep 25
addict_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr  -12 | opp rep 15
addict_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr   -8 | opp rep 25
-- step 12c strategies, median per game: rest% (home+outing+church of 144) resort% | void periods (detained/detox/missing/sanatorium means) | arrests detox sanatorium boosts crime-job periods | full month | cash y2 / end / end p10 | S/A/B/C-/collapse% | grade mean
disciplined_tough   rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 30 |    607 /  1,295 /    608 | 0/75/24/0/0 | 2.76
disciplined_lover   rest 34% resort  0% | void  0 (0.1/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 30 |    404 /  1,089 /    620 | 1/70/30/0/0 | 2.71
disciplined_culture rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 31 |    380 /    841 /    388 | 0/72/26/2/0 | 2.69
disciplined_savvy   rest 33% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 27 |  1,433 /  2,669 /  1,148 | 0/60/40/0/0 | 2.60
bad_boy_tough       rest 33% resort 18% | void  6 (6.8/0.0/0.8/0.0) | arr 3 detox 0 sana 0 boost  0 crimeP 31 | full 27 |    925 /  3,644 /  1,769 | 0/70/28/2/0 | 2.69
bad_boy_lover       rest 31% resort 22% | void  6 (6.3/0.0/0.6/0.0) | arr 3 detox 0 sana 0 boost  0 crimeP 28 | full 25 |  3,224 /  6,286 /  1,679 | 0/76/24/0/0 | 2.75
bad_boy_savvy       rest 31% resort 23% | void  8 (7.5/0.0/0.5/0.0) | arr 4 detox 0 sana 0 boost  0 crimeP 32 | full 31 |  2,209 /  6,294 /  2,754 | 0/72/26/2/0 | 2.69
addict_tough        rest 17% resort  0% | void 15 (13.1/4.9/1.6/0.0) | arr 2 detox 1 sana 0 boost 12 crimeP  0 | full 35 |    286 /    193 / -1,592 | 0/21/38/40/0 | 1.66
addict_lover        rest 26% resort  0% | void  5 (1.0/4.6/0.3/0.0) | arr 0 detox 1 sana 0 boost 13 crimeP  0 | full 33 |    262 /    652 /   -367 | 0/42/43/14/0 | 2.25
addict_culture      rest 33% resort  0% | void  6 (0.0/4.1/0.1/0.0) | arr 0 detox 2 sana 0 boost 15 crimeP  0 | full 99 |    186 /    347 /   -327 | 0/24/25/50/0 | 1.51
addict_savvy        rest 31% resort  0% | void  3 (0.0/3.9/0.1/0.0) | arr 0 detox 1 sana 0 boost 17 crimeP  0 | full 26 |  1,269 /  2,247 /    748 | 0/61/37/2/0 | 2.59
= disciplined (mean of roads) rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 30 |    706 /  1,474 /    691 | 0/69/30/0/0 | 2.69
= bad_boy (mean of roads) rest 32% resort 21% | void  7 (6.9/0.0/0.6/0.0) | arr 3 detox 0 sana 0 boost  0 crimeP 30 | full 28 |  2,119 /  5,408 /  2,067 | 0/73/26/2/0 | 2.71
= addict (mean of roads) rest 27% resort  0% | void  7 (3.5/4.4/0.5/0.0) | arr 0 detox 1 sana 0 boost 14 crimeP  0 | full 48 |    501 /    860 /   -384 | 0/37/36/27/0 | 2.00
   grade mean vs disciplined [+-0.3]: bad_boy 0.02, addict -0.69, bad_boy S spread across roads 0 pp [<=8]
```
