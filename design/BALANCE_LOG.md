# 平衡记录

每轮改数值在“改动记录”里加一段：改了什么、为什么、前后对比。改完重跑 Godot 报告（第 12b 步起，命令见 `README.md`；`sim/` 冻结），把下面“现在的报告”整段换掉。

## 目标和现状（第 8 步第一轮之后）

四个数是专练硬汉 / 情人 / 文化 / 手腕，200 局中位数，机器人会买装备。

| 目标 | 第 7 步 | 现在 | 达标 |
|---|---|---|---|
| 练满月 16–21，四路相差 ≤6 | 21 / 21 / 27 / 21 | 19 / 21 / 21 / 19 | 是 |
| 练满加普通上映 311–340 | 386–430（算法不同，含机遇和装备） | 322–326 | 是 |
| 过 311 的局约九成 | 100% | 88%–91% | 是 |
| 大片通过率 10%–35% | 52 / 52 / 35 / 60 | 24 / 30 / 23 / 22 | 是 |
| 大卖率一成上下 | 18 / 21 / 13 / 14 | 11 / 15 / 8 / 10 | 是 |
| 期末现金中位和 p90 不过万 | p90 1.3 万–2.1 万 | 中位 3.7k–4.3k，p90 6.2k–6.8k | 是 |
| 前两年年末现金不过千 | 第 2 年 2.2k / 1.2k / 2.7k / 4.3k | 第 2 年 868 / 801 / 833 / **1,357** | 手腕没到，见下 |
| 每种机器人至少 3 种结局 | 专练的 2–5 种，74%–99% 是同一个 | 6–9 种，最多的一个占 35%–54% | 是 |

## 第 12c 步 c3 要做的（交给 Fable 看报告，Opus 改表）

c1、c2 做完后的 200 局报告在下面。护栏（`design/targets.json`，不放宽）25 条不过。规则按规格的起点数写了，**一个数都没调**。看报告看到的：

1. **自律线太强，是现在的“更优解”。** 四路平均 S 32%、A 66%、B 2%，档次均分 3.30（目标约 2.3，S ≤2%）。练满月 24（目标 21–26，达标），休息旬 34%（达标）。规格的办法是先加疲劳来源，不要削坏孩子线。注意均分的基准变了：三条线的目标都是相对自律线的。
2. **坏孩子线没起来。** 期末现金中位 2.5k（目标 6–10k），第 2 年末 864（目标 2–4k），被捕 1 次（目标 3–5），作废的旬 1.3（目标 6–10），休息 33%（目标 20–25%，其中度假村 21%）。犯罪工赚不到钱的原因：犯罪工让自律很快掉到 0，失控指数 = 疲劳，打工时失控 ≥30 有 80% 偷懒（只有成功日有薪水）。机器人因此每月最后一旬都得去度假村，休息占比降不下来。可调的旋钮：犯罪工的自律惩罚、度假村价格、偷懒规则对犯罪工是否生效、二级日薪。三路 S 档相差 34 个百分点（情人 42%、手腕 13%、硬汉 8%，目标 ≤8）。
3. **嗑药线没有“两头”。** S 17%（目标 30–35%）、倒下 0%（目标 12–18%）、C 以下 7%（目标 40–45%）。戒断 2 次、作废的旬 9 达标。休息 24%（目标 10–15%）：拿到“提神”要靠“递药”（拍摄月月末疲劳 ≥60，1/4），拿到之前机器人只能照常休息；阶段 3 前一个月就送去戒，所以从没到过阶段 3，体力、相貌的消耗也就没发生。要两头，可能要让阶段 3 更容易碰到，或让“递药”更早出现。
4. **专练机器人（旧 8 个）**：疲劳变大后练满月从 19–21 推到 24–33，过 311 的局从九成降到 52%–86%。第 12c 规格说练满 16–21 只对嗑药线成立；`targets.json` 里专练四个还挂着第 8 步的目标，Fable 决定挪不挪。
5. **事件**：九个事件 3800 局里一次都没触发：`evt_birthday`（没定日期）、`job_studio_m1/m2/m3`、`job_ballroom_m2/m3`、`job_bodyguard_r1`、`job_radio_m1`、`opp_painting`（`--coverage`）。“来自事件”各项都在线内（手腕专练的事件主路声望 45 超过 30，来自前辈认可的选项）。
6. 原“下一轮要修的”三条（情人 S 档、只读书文化的钱、手腕第 2 年的钱）在新基线下：专练情人 S 22%、只读书文化第 2 年末 571、专练手腕第 2 年末 1,067。第一、二条已不明显，第三条还在。

机器人和规格不同的地方（照字面写机器人会卡死）：坏孩子只在每月最后一旬按月末失控指数决定去不去度假村（自律 0 时每旬都判会一直休息）；坏孩子和还没拿到“提神”的嗑药线另外避免失控指数到 60；坏孩子在本路犯罪工做不了时退回普通打工；文化路没有犯罪工，所以没有 `bad_boy_culture`。规格写“餐厅每旬只生效一次”，现在餐厅本来就是每月一次（更严），没改。

## 下一轮要修的（第 8 步第二轮，交给下一个模型）

每条先用报告确认现象还在，再改；改完在“改动记录”加一段，并把“现在的报告”换掉。

1. **专练情人 S 档 55%，另外三路 30%–36%。目标：四路都在 25%–40%。**
   推测的原因，按可能性排：
   - 情人色的大片最好过（通过率 30%，别的路 22%–24%），大片多所以名气最高（期末 553）、上映修正也最多。1927-08 瓦伦去世后到 1928 年底，情人色最强的有名对手只有诺瓦和吉尔伯（都是 8 级），而且吉尔伯 1929 年掉到 6 级。
   - 瓦伦去世后每块板多一个浪漫或异国情人的小片角色（到 1928-12），情人路多拿片。
   - 机遇均值 +47，四路最高：“一支探戈”的条件（体态 100、浪漫系大卖过一次）对专练情人的人几乎必满足。
   方向：先试把吉尔伯 1929 年的情人等级从 6 提到 7、诺瓦升 9 级的时间从 1929-01 提前到 1928-07（`rivals.json`），看大片通过率能不能回到 22%–25%；不够再把“一支探戈”的条件加严（例如浪漫系大卖 ≥2 次，`opportunities.json`）。不要动 S 线和年度奖励。
2. **只读书文化：第 2 年末现金 1,707（目标 <1,000），期末 p90 10,491（目标 <1 万）。**
   推测的原因：读书不交学费，9 本书合计 675 元；它没有第二条路，第 21 个月练满后只打工和拍片，钱没有去处。专练文化（接着练情人路）没有这个问题，所以这更像机器人的问题，不一定是数值的问题。
   方向：先改机器人（`sim/bots.py` 的 `BookCulture`）：练满后和专练文化一样接着练一条副路。改完如果第 2 年末仍然过千，再考虑数值：书价再涨一档（现 15/60/150），或把每本书的点数从 35 降到 20，让每档要买两本（`books.json`，同时改 `档` 和 `书` 两处，校验脚本会对）。改数值后要确认专练文化的练满月还在 21 以内。
3. **手腕路第 2 年末 1,357**（目标 <1,000）。已经加了片厂区逛街涨价和谈判系数降低两处，还差一点。可以试的：片厂办公室、明星助理的日薪各降 1–2；或再把谈判系数降到 /800。

## 知道但不用修的

- **两路（硬汉+情人）**只有 22% 的局两路都练满，期末主路声望 318。用户确认：没事，不用修。
- 小片拿到率 100%：小片当保底。
- 机器人不写剧本、不放消息、不去度假村、不谈恋爱；事件选项一律选第一个。这些对钱和声望的影响没测，等有了界面由用户试玩。

## 用户已同意的决定（第 8 步第一轮）

- S 线 421 → 451（A 381、B 311、C 211 没动）。练满以外有五处往上加，正常打完的专练玩家在 440 上下，421 人人都过；451 正好是 9 级的门槛。
- 年度大事 +40/+20/+10 → +20/+10/+5，奖金 1000/500/200 → 500/250/100。
- 手腕路收钱的做法：片厂区逛街 2 → 8 一天（当作应酬），谈判的片酬系数 /400 → /600。
- 打斗的体力加成从“体力/10 封顶 30”降到“体力/30 封顶 10”，开局硬汉声望 33 → 27。
- 新加舞鞋（体态 +5，12 元）、化妆箱（打扮 +5，25 元）。
- 无名对手的成长改成每档各自的涨级月（改了 `sim/audition.py` 一行）。

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

### 第 12c 步 c3 第 0 轮（Fable 定的数，`design/C3_ROUND1.md`）

只动表，照 C3_ROUND1 第 0 轮的表改：

| 改了什么 | 原来 | 现在 |
|---|---|---|
| 年度名次声望修正（奖金不动） | +20 / +10 / +5 | +10 / +5 / +2 |
| 八个机遇的声望修正（前辈的 +10 不动） | +25 / +30 | +15 |
| 上课 3、4 级主收益上限 | 拳馆打斗 [1,2][1,3]；马术 [1,3][1,4]；表演、舞蹈、礼仪 [1,3][2,4]；家教教育 [3,8][4,12] | [1,1][1,2]；[1,2][1,3]；[1,2][2,3]；[3,6][4,9]。副收益不动 |
| 学费/天 | 拳馆 9–18、马术 14–40、表演 8–17、另三门 6–15 | ×1.5 向上取整：14/18/23/27、21/33/45/60、12/17/21/26、9/14/18/23 |
| 书（`档` 和 `书` 两处） | 点数 35；进阶、专著每天 +r(1,3) | 点数不动；进阶、专著每天 +r(1,2)。C3_ROUND1 写的是点数 35 → 28，跑出来文化路只有 40% 的局练满：点数是一本书给的技能总量，每档要补 30–40，28 点够不着上限，所以改成降每天收益（和课一样上限 −1） |
| 明星助理 | 日薪 3；谈判、人脉、生意各 +0/1 | 日薪 1；谈判、人脉各 +0/1（`daily_effect` 没有“随机两项”的写法，按备选去掉生意；生意仍可从片厂办公室、赌档记账、运私酒、书里练） |

顺手：`evt_birthday` 日期定为 `08-19`（用户定）。GDD 2.3、5.3.1、5.3.2、5.4、12.1、12.2 的数同步。

**还没跑报告**：这次的环境里没有 Godot，`check.py` 前 4 步通过，第 5 步（护栏）跳过。下面“现在的报告”仍是 c1、c2 之后的，跑完 `report.gd --n=200 --bots=all` 再换掉，并把三条线的练满月报给 Fable。

## 现在的报告

第 12c 步 c1、c2 之后，Godot `report.gd --n=200 --bots=all`（4 个进程分段再 `--merge`，约 5 分钟）。护栏的逐条结果用 `--guard=design/targets.json` 看。

```
== each bot 200 games (seeds 1-200), cards played greedy; targets: PLAN step 8 ==
-- full-training month median (10%-90%) [target 16-21] | months with rep >= 210 | main-road rep median at months 12/24/36/48
only_tough full 30(24–42)      210:19(13–31)    167/292/377/417
only_lover full 33(28–42)      210:19(16–27)    172/277/378/422
only_culture full 31(25–42)[72%] 210:21(15–31)    139/261/383/412
only_savvy full 24(22–27)      210:18(16–19)    117/353/402/422
two_roads full —              210:43(37–47)[42%] 106/144/168/204
crime_line full —              210:24(21–34)    136/211/244/258
books_culture full 30(25–37)      210:18(15–21)    141/287/380/396
random_pick full 42(41–47)[1%]  210:41(30–48)[57%] 88/123/167/218
disciplined_tough full 22(19–25)      210:13(12–16)    208/367/391/411
disciplined_lover full 25(21–30)      210:15(11–20)    189/349/417/449
disciplined_culture full 24(21–30)      210:15(13–21)    158/362/411/433
disciplined_savvy full 24(21–26)      210:16(14–18)    145/364/417/462
bad_boy_tough full 20(18–27)[85%] 210:11(10–12)    252/368/391/411
bad_boy_lover full 22(21–25)      210:13(11–15)    204/365/417/442
bad_boy_savvy full 27(24–31)      210:19(16–23)    108/324/385/416
addict_tough full 25(19–36)      210:13(10–20)    199/344/378/395
addict_lover full 27(21–37)      210:15(12–25)    189/332/397/421
addict_culture full 27(19–42)[74%] 210:20(13–33)    137/264/388/413
addict_savvy full 23(18–26)      210:16(12–18)    147/360/411/443
-- final main-road rep breakdown (mean): training+gear and stamina+releases+annual+opportunities | full training plus plain releases (no gear) median [311-340], over 311 [90%] | grade S/A/B/C/D %
only_tough 300+38+17+31+29 = 417 | 315 over 311  73% | 8/77/14/0/0
only_lover 300+36+22+27+39 = 422 | 320 over 311  86% | 22/67/10/0/0
only_culture 274+30+15+32+30 = 412 | 311 over 311  52% | 4/65/12/12/6
only_savvy 300+28+16+45+36 = 422 | 316 over 311  72% | 13/84/3/0/0
two_roads 183+16+10+ 6+ 0 = 204 | 189 over 311   0% | 0/0/1/41/58
crime_line 222+10+ 6+17+-1 = 258 | 231 over 311   0% | 0/0/0/96/4
books_culture 300+33+17+37+10 = 396 | 316 over 311  78% | 0/92/8/0/0
random_pick 220+ 0+ 2+ 3+-7 = 218 | 225 over 311   0% | 0/0/3/54/42
disciplined_tough 300+42+24+36+10 = 411 | 323 over 311  94% | 3/93/4/0/0
disciplined_lover 300+37+25+39+46 = 449 | 325 over 311  88% | 47/49/3/0/0
disciplined_culture 300+37+18+47+31 = 433 | 317 over 311  74% | 15/84/0/0/0
disciplined_savvy 300+33+20+52+53 = 462 | 318 over 311  82% | 63/36/0/0/0
bad_boy_tough 290+38+21+37+ 1 = 411 | 321 over 311  75% | 8/67/10/10/3
bad_boy_lover 300+37+24+41+38 = 442 | 324 over 311  89% | 41/50/7/0/0
bad_boy_savvy 300+29+16+37+33 = 416 | 314 over 311  64% | 13/73/12/1/0
addict_tough 299+34+13+31+ 4 = 395 | 312 over 311  54% | 2/63/27/7/0
addict_lover 299+36+16+31+31 = 421 | 316 over 311  68% | 19/58/21/0/0
addict_culture 276+29+10+34+30 = 413 | 308 over 311  38% | 4/67/9/10/8
addict_savvy 299+31+16+49+47 = 443 | 316 over 311  74% | 41/55/3/0/0
-- cash at each year end, median (years 1-4) [first two years <1000] | final p90 [<10k] | final >10k | debt months | film fees total, gear spend (mean)
only_tough 215 / 535 / 775 / 1,140          p90   2,176  >10k   0%  debt  0.3 |  8,341   778
only_lover 217 / 378 / 802 / 1,167          p90   2,394  >10k   0%  debt  0.2 |  9,240   137
only_culture 273 / 296 / 693 / 710            p90   2,315  >10k   0%  debt  0.3 |  7,905   313
only_savvy 408 / 1,067 / 1,182 / 1,247      p90   3,807  >10k   0%  debt  0.2 | 11,252   929
two_roads 175 / 228 / 189 / 270            p90     532  >10k   0%  debt  0.2 |  6,169   113
crime_line 481 / 739 / 1,112 / 1,704        p90   2,785  >10k   0%  debt  0.7 |  4,947     0
books_culture 354 / 571 / 1,965 / 4,256        p90   6,023  >10k   0%  debt  0.0 |  9,572   443
random_pick -655 / -1,469 / -1,864 / -2,024  p90    -227  >10k   0%  debt 42.7 |  1,966     0
disciplined_tough 404 / 855 / 1,555 / 3,376        p90   5,702  >10k   0%  debt  0.0 | 12,294 1,894
disciplined_lover 278 / 720 / 1,428 / 3,984        p90   6,462  >10k   0%  debt  0.1 | 12,014   157
disciplined_culture 390 / 896 / 1,673 / 3,724        p90   6,246  >10k   0%  debt  0.0 | 10,243   462
disciplined_savvy 568 / 1,786 / 3,045 / 4,385      p90   6,227  >10k   0%  debt  0.0 | 13,329 4,369
bad_boy_tough 490 / 654 / 775 / 2,585          p90   5,572  >10k   0%  debt  6.0 |  9,627 1,280
bad_boy_lover 315 / 878 / 1,085 / 1,929        p90   3,933  >10k   0%  debt  1.5 | 11,280   148
bad_boy_savvy 375 / 1,061 / 1,164 / 2,900      p90   5,112  >10k   0%  debt  2.2 | 10,436 1,414
addict_tough 287 / 448 / 611 / 1,120          p90   3,376  >10k   0%  debt  7.4 |  9,395   879
addict_lover 239 / 527 / 744 / 1,532          p90   3,977  >10k   0%  debt  3.5 | 10,098   148
addict_culture 255 / 347 / 812 / 867            p90   4,383  >10k   0%  debt  3.7 |  7,824   328
addict_savvy 459 / 1,488 / 2,412 / 3,545      p90   5,534  >10k   0%  debt  0.4 | 11,616 2,804
-- auditions per game, won% small/medium/big [big 10-35%] | releases per game, hit% [10%] flop% | leads small/medium/big | supports, breaches
only_tough 18.2 games 100/61/21% (big 0.5 games) | release 15.1 hit   6% flop  32% | 4.8/7.6/0.1 | 2.6 0.3
only_lover 19.1 games 100/61/19% (big 1.4 games) | release 15.4 hit  13% flop  16% | 3.8/8.5/0.2 | 3.0 0.0
only_culture 18.2 games 100/56/17% (big 0.5 games) | release 15.4 hit   5% flop  24% | 6.9/6.0/0.1 | 2.4 0.0
only_savvy 18.2 games 100/70/19% (big 1.5 games) | release 15.6 hit   5% flop  21% | 4.4/8.7/0.2 | 2.3 0.0
two_roads 19.4 games 100/39/100% (big 0.0 games) | release 14.6 hit   9% flop  20% | 9.0/3.4/0.0 | 2.2 0.0
crime_line 17.5 games 100/39/nan% (big 0.0 games) | release 14.8 hit   1% flop  65% | 10.9/2.1/0.0 | 1.7 0.2
books_culture 18.5 games 100/61/14% (big 0.5 games) | release 15.6 hit   3% flop  28% | 5.6/7.6/0.0 | 2.4 0.0
random_pick 10.1 games 84/12/nan% (big 0.0 games) | release  7.2 hit   1% flop  55% | 6.7/0.1/0.0 | 0.3 0.4
disciplined_tough 18.3 games 100/72/23% (big 2.3 games) | release 16.6 hit   9% flop  22% | 2.8/10.7/0.4 | 2.7 0.0
disciplined_lover 18.5 games 100/69/27% (big 2.5 games) | release 16.3 hit  13% flop  20% | 2.7/10.2/0.5 | 2.9 0.0
disciplined_culture 17.9 games 100/68/19% (big 1.4 games) | release 16.1 hit   5% flop  31% | 4.2/9.1/0.2 | 2.6 0.0
disciplined_savvy 18.4 games 100/74/20% (big 2.7 games) | release 16.5 hit   6% flop  22% | 3.5/10.2/0.4 | 2.4 0.0
bad_boy_tough 17.7 games 99/74/18% (big 0.9 games) | release 15.9 hit   6% flop  39% | 3.5/10.2/0.1 | 2.1 0.7
bad_boy_lover 18.3 games 100/72/24% (big 1.7 games) | release 16.6 hit  11% flop  19% | 2.4/11.3/0.3 | 2.6 0.4
bad_boy_savvy 18.0 games 100/66/16% (big 1.0 games) | release 16.2 hit   7% flop  22% | 6.2/7.7/0.1 | 2.2 0.1
addict_tough 17.8 games 100/71/20% (big 0.6 games) | release 14.8 hit   2% flop  55% | 3.9/8.8/0.1 | 2.0 1.8
addict_lover 18.7 games 100/65/20% (big 1.3 games) | release 15.2 hit   6% flop  37% | 3.1/9.3/0.2 | 2.7 1.1
addict_culture 17.8 games 100/60/21% (big 0.3 games) | release 15.2 hit   2% flop  51% | 7.3/5.9/0.0 | 2.0 0.6
addict_savvy 17.9 games 100/74/21% (big 1.5 games) | release 15.9 hit   3% flop  35% | 4.6/9.2/0.1 | 1.9 0.5
-- median fame at each year end | final fame tier unknown/familiar/famous/hot/superstar % | mean annual rank (years 1-4) | collapse% | endings (kinds [>=3]; top four)
only_tough 148/175/199/267  0/7/56/35/0    rank 3.8/2.4/2.1/2.0  collapse 0%  endings 10 kinds: tough_adventurer50% act_voice19% tough_rider9% act_legend7%
only_lover 165/224/324/415  0/0/5/80/14    rank 5.2/3.5/2.0/1.8  collapse 0%  endings 10 kinds: act_lover38% act_legend16% act_art15% idol9%
only_culture 125/160/199/253  0/0/69/30/0    rank 3.1/2.9/1.9/2.2  collapse 0%  endings 8 kinds: cult_tabloid51% act_voice21% cult_editor12% cult_street_photo6%
only_savvy 121/161/229/323  0/0/35/64/0    rank 2.4/2.4/1.4/1.9  collapse 0%  endings 12 kinds: act_voice35% biz_agent33% act_legend11% act_lover6%
two_roads 164/195/210/243  0/0/90/9/0     rank 5.1/3.5/3.7/3.4  collapse 0%  endings 12 kinds: tough_thug27% tough_gym26% biz_sales14% lover_gigolo10%
crime_line 126/112/99/96    7/66/21/5/0    rank 4.5/2.6/3.1/3.1  collapse 0%  endings 5 kinds: dark_boss47% dark_thug_boss45% act_lowbudget4% dark_prison2%
books_culture 124/167/232/285  0/0/61/38/0    rank 3.1/2.5/1.5/2.0  collapse 0%  endings 5 kinds: cult_tabloid61% act_voice32% act_art4% act_undefined1%
random_pick 94/62/41/27      94/6/0/0/0     rank 5.4/5.2/5.1/5.0  collapse 2%  endings 6 kinds: biz_boss41% biz_sales25% dark_prison16% dark_con14%
disciplined_tough 148/205/311/424  0/0/4/75/20    rank 2.8/2.0/2.0/2.0  collapse 0%  endings 10 kinds: act_voice48% act_action16% act_art10% idol9%
disciplined_lover 161/225/358/468  0/0/1/61/37    rank 5.0/2.6/1.3/1.6  collapse 0%  endings 10 kinds: act_legend34% act_lover26% idol19% act_art9%
disciplined_culture 122/158/239/325  0/0/34/62/3    rank 3.1/1.8/1.1/1.9  collapse 0%  endings 9 kinds: act_voice43% cult_writer34% act_legend13% act_art5%
disciplined_savvy 120/169/273/415  0/0/4/84/11    rank 2.2/2.1/1.2/1.6  collapse 0%  endings 10 kinds: act_legend59% act_voice20% act_lover7% idol4%
bad_boy_tough 136/169/234/267  6/15/46/29/4   rank 2.2/2.0/2.1/2.2  collapse 0%  endings 10 kinds: dark_thug_boss63% act_voice13% act_action8% dark_prison3%
bad_boy_lover 168/227/310/367  0/0/30/50/19   rank 5.0/2.1/1.3/1.7  collapse 0%  endings 11 kinds: dark_thug_boss29% act_legend22% act_lover18% idol11%
bad_boy_savvy 117/132/194/305  2/9/38/45/4    rank 2.6/2.7/1.8/2.0  collapse 0%  endings 10 kinds: dark_con50% act_voice27% act_legend10% act_lover5%
addict_tough 128/148/180/236  3/25/45/26/0   rank 3.0/2.1/2.1/2.3  collapse 0%  endings 10 kinds: tough_thug45% dark_thug_boss20% act_voice14% dark_con6%
addict_lover 151/206/284/311  0/0/45/49/5    rank 5.1/2.9/1.8/1.9  collapse 0%  endings 16 kinds: lover_widow30% act_lover19% act_legend17% act_art6%
addict_culture 108/128/161/191  0/28/60/11/0   rank 3.1/2.7/1.9/2.2  collapse 0%  endings 7 kinds: cult_tabloid70% cult_editor9% cult_street_photo8% act_voice6%
addict_savvy 109/143/218/309  0/3/42/53/1    rank 2.3/2.2/1.3/1.7  collapse 0%  endings 12 kinds: biz_agent27% act_legend26% biz_producer14% act_voice12%
-- without buying gear: final cash median / p90 | final main-road rep median | grade S/A/B/C/D %
only_tough   1,079 /   2,470 | 366 | 0/40/59/0/0
only_lover     925 /   1,993 | 358 | 0/25/74/0/0
only_culture     741 /   1,976 | 392 | 0/68/16/10/4
only_savvy   1,150 /   3,328 | 382 | 1/53/46/0/0
-- from events, median per game: main-road rep from events (skills + rep_bonus) [<=30] | event money net, % of all money gained [+-10%] | event fatigue net per year [+-60] | opportunity rep
only_tough ev rep   5 | money    900 (  5.5%) | fatigue/yr   10 | opp rep 40
only_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 40
only_culture ev rep  14 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 35
only_savvy ev rep  45 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 35
two_roads ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 0
crime_line ev rep   5 | money  1,400 ( 12.7%) | fatigue/yr   10 | opp rep 0
books_culture ev rep  24 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 10
random_pick ev rep  16 | money      0 (  0.0%) | fatigue/yr   11 | opp rep 0
disciplined_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 10
disciplined_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 40
disciplined_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 35
disciplined_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 65
bad_boy_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   32 | opp rep 10
bad_boy_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   34 | opp rep 40
bad_boy_savvy ev rep   5 | money      0 (  0.0%) | fatigue/yr   40 | opp rep 35
addict_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr  -32 | opp rep 10
addict_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr  -26 | opp rep 40
addict_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr  -15 | opp rep 35
addict_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr  -12 | opp rep 40
-- step 12c strategies, median per game: rest% (home+outing+church of 144) resort% | void periods (detained/detox/missing/sanatorium means) | arrests detox sanatorium boosts crime-job periods | full month | cash y2 / end / end p10 | S/A/B/C-/collapse% | grade mean
disciplined_tough   rest 35% resort  0% | void  0 (0.1/0.0/0.1/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 22 |    855 /  3,376 /  1,793 | 3/93/4/0/0 | 2.99
disciplined_lover   rest 35% resort  0% | void  0 (0.1/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 25 |    720 /  3,984 /  1,620 | 48/50/3/0/0 | 3.44
disciplined_culture rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 24 |    896 /  3,724 /  1,477 | 15/84/0/0/0 | 3.15
disciplined_savvy   rest 33% resort  0% | void  0 (0.0/0.0/0.0/0.1) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 24 |  1,786 /  4,385 /  2,357 | 64/36/0/0/0 | 3.63
bad_boy_tough       rest 33% resort 20% | void  2 (4.0/0.0/1.5/0.0) | arr 1 detox 0 sana 0 boost  0 crimeP 29 | full 20 |    654 /  2,585 /   -456 | 8/68/10/14/0 | 2.66
bad_boy_lover       rest 33% resort 19% | void  1 (1.5/0.0/0.6/0.0) | arr 1 detox 0 sana 0 boost  0 crimeP 20 | full 22 |    878 /  1,929 /   -651 | 42/50/8/0/0 | 3.33
bad_boy_savvy       rest 33% resort 24% | void  1 (1.5/0.0/0.5/0.0) | arr 1 detox 0 sana 0 boost  0 crimeP 20 | full 27 |  1,061 /  2,900 /    981 | 13/74/12/1/0 | 2.98
addict_tough        rest 16% resort  0% | void 15 (5.2/7.8/1.2/0.0) | arr 1 detox 2 sana 0 boost 22 crimeP  0 | full 25 |    448 /  1,120 /   -986 | 2/64/27/7/0 | 2.62
addict_lover        rest 20% resort  0% | void  9 (1.0/7.1/0.6/0.0) | arr 0 detox 2 sana 0 boost 27 crimeP  0 | full 27 |    527 /  1,532 /      9 | 20/58/21/1/0 | 2.96
addict_culture      rest 33% resort  0% | void  6 (0.0/5.2/0.1/0.0) | arr 0 detox 2 sana 0 boost 18 crimeP  0 | full 27 |    347 /    867 /   -130 | 4/68/10/18/0 | 2.50
addict_savvy        rest 28% resort  0% | void  6 (0.0/5.0/0.1/0.0) | arr 0 detox 2 sana 0 boost 18 crimeP  0 | full 23 |  1,488 /  3,545 /  1,655 | 41/55/4/0/0 | 3.37
= disciplined (mean of roads) rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 24 |  1,064 /  3,867 /  1,812 | 32/66/2/0/0 | 3.30
= bad_boy (mean of roads) rest 33% resort 21% | void  1 (2.4/0.0/0.9/0.0) | arr 1 detox 0 sana 0 boost  0 crimeP 23 | full 23 |    864 /  2,471 /    -42 | 21/64/10/5/0 | 2.99
= addict (mean of roads) rest 24% resort  0% | void  9 (1.6/6.3/0.5/0.0) | arr 0 detox 2 sana 0 boost 21 crimeP  0 | full 26 |    702 /  1,766 /    137 | 17/61/15/7/0 | 2.86
   grade mean vs disciplined [+-0.3]: bad_boy -0.31, addict -0.44, bad_boy S spread across roads 34 pp [<=8]
```
