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
| 年度名次声望修正（奖金不动） | +20 / +10 / +5 | +8 / +4 / +2（先改成 +10/+5/+2，跑出来自律线 A 70%，按 C3_ROUND1 的后手再降） |
| 八个机遇的声望修正（前辈的 +10 不动） | +25 / +30 | +15 |
| 上课 3、4 级主收益上限 | 拳馆打斗 [1,2][1,3]；马术 [1,3][1,4]；表演、舞蹈、礼仪 [1,3][2,4]；家教教育 [3,8][4,12] | [1,1][1,2]；[1,2][1,3]；[1,2][2,3]；[3,6][4,9]。副收益不动 |
| 学费/天 | 拳馆 9–18、马术 14–40、表演 8–17、另三门 6–15 | ×1.5 向上取整：14/18/23/27、21/33/45/60、12/17/21/26、9/14/18/23 |
| 书（`档` 和 `书` 两处） | 点数 35；进阶、专著每天 +r(1,3) | 点数不动；进阶、专著每天 +r(1,2)。C3_ROUND1 写的是点数 35 → 28，跑出来文化路只有 40% 的局练满：点数是一本书给的技能总量，每档要补 30–40，28 点够不着上限，所以改成降每天收益（和课一样上限 −1） |
| 明星助理 | 日薪 3；谈判、人脉、生意各 +0/1 | 日薪 1；谈判、人脉各 +0/1（`daily_effect` 没有“随机两项”的写法，按备选去掉生意；生意仍可从片厂办公室、赌档记账、运私酒、书里练） |

顺手：`evt_birthday` 日期定为 `08-19`（用户定）。GDD 2.3、5.3.1、5.3.2、5.4、12.1、12.2 的数同步。

前后对比（200 局，c1/c2 → 第 0 轮）：

| | c1/c2 | 第 0 轮 |
|---|---|---|
| 自律线练满月（硬汉/情人/文化/手腕） | 22 / 25 / 24 / 24 | 28 / 30 / 31 / 27（相差 4） |
| 自律线 S/A/B，均分 | 32 / 66 / 2，3.30 | 0 / 64 / 35，2.64 |
| 自律线第 2 年末 / 期末现金 | 1,064 / 3,867 | 715 / 1,496 |
| 坏孩子 S/A/B/C 以下，均分差 | 21 / 64 / 10 / 5，−0.31 | 0 / 44 / 38 / 18，−0.45 |
| 嗑药 S/A/B/C 以下，均分差 | 17 / 61 / 15 / 7，−0.44 | 0 / 34 / 41 / 26，−0.65 |
| 专练四路练满月 | 30 / 33 / 31 / 24 | 42 / 42 / 39 / 33（硬汉、情人、文化只有 55% / 77% / 25% 的局练满） |

- 书的点数照 C3_ROUND1 改成 28 时，自律文化只有 40% 的局练满、嗑药文化 13%：点数是一本书能给的技能总量，每档要补 30–40，28 够不着上限，机器人也不会重买读过的书。改成点数不动、降每天收益后文化回到 31 个月。
- 年度名次先改 +10/+5/+2，自律线 A 70%，按 C3_ROUND1 的后手再降到 +8/+4/+2（A 64%）。
- 自律线第 2 年末 715，没掉到 0 以下，学费不退。
- 坏孩子硬汉变得很差（被捕 9、档次均分 1.55）：练得慢以后长期停在一级犯罪工，钱不够去度假村，疲劳过百被捕。第 1 轮处理。
- 嗑药文化只有 41% 的局练满，留给第 3 轮。
- 练满月的护栏（自律 21–26 等）照 C3_ROUND1 的说法不回调，等 Fable 整体后移。

### 第 12c 步 c3 第 1 轮（坏孩子线的钱和被捕，C3_ROUND1）

规则（GDD 5.1、5.4.1、11.2 同步）：
- 犯罪工不偷懒：`crime_tiers` 每级加 `reckless_slack: false`，`Schedule.job_slacks`；普通工和拍摄照旧。
- 搜查判定 `技能 + r0(20) >= 线` → `r0(技能) + 20 >= 线`（`arrest.raid_check_add` 20）。
- 拘留作废 1 → 2 旬（`arrest.detain_periods`）。
- 二级犯罪工日薪 40 → 50（C3_ROUND1 的后手：日薪 40 时期末现金 2.4k，不到 6k）。

机器人：
- 坏孩子做犯罪工的存钱线加 1,500，**只在二级犯罪工能做时加**。照字面一直加时，坏孩子硬汉 97% 的局练不满：他攒不过线，就一直做日薪 8 的看场子，没钱上马术课，而运私酒要骑马驾驶 30，死锁。
- 坏孩子补上“月末失控指数不到 60”：在最后一旬之前，只有最后一旬歇得回 60 以下（按他付得起的休息算）才去干活。BALANCE_LOG 原来就这么写，代码里只有嗑药线有。没有这条时，钱花在学费上、去不起度假村，疲劳过百，失控指数 100 每月被捕一次（单局 45 次）。
- 三条线的硬汉路要休息时先去码头，凑满 3 次外出（探险队机遇的条件）；“亲自上”本来就是一律上。

前后对比（200 局，第 0 轮 → 第 1 轮）：

| | 第 0 轮 | 第 1 轮 | 目标 |
|---|---|---|---|
| 坏孩子第 2 年末 / 期末现金 | 585 / 753 | 1,821 / 2,653 | 2k–4k / 6k–10k |
| 被捕 / 作废的旬（均值） | 4 / 3.9 | 3 / 6.6 | 3–5 / 6–10 |
| 练满月 | 27（硬汉 50% 的局练不满） | 31（硬汉 36、情人 25、手腕 31） | — |
| S/A/B/C 以下，均分差 | 0 / 44 / 38 / 18，−0.45 | 0 / 65 / 34 / 1，−0.04 | 均分差 ±0.3 |
| 三路 S 档差 | 0 | 0 | ≤8 |
| 休息 / 度假村 | 33% / 14% | 32% / 22% | 20%–25% |

- 期末现金还差得远：日薪 40 → 50 只多了 250。钱主要花在学费（×1.5 以后）和度假村（22% 的旬）上。第 2 轮把度假村涨三倍会再吃掉一大块，和 6k–10k 的目标冲突，**第 2 轮先不做，交给 Fable**。
- 码头事件“酒吧后门的生意”只有一个选项“做”（胆识 50，不过就被捕），去码头的人都可能被捕。自律硬汉为了探险队去码头以后平均被捕 0.2 次，护栏 `disciplined arrests [0,0]` 因此不过。这是内容问题，要不要加一个“不做”的选项由用户定。
- 坏孩子线和自律线现在几乎一样好（均分差 −0.04），A 都在六成以上。

## 现在的报告

第 12c 步 c3 第 0、1 轮之后，Godot `report.gd --n=200 --bots=all`（4 个进程分段再 `--merge`，约 5 分钟）。护栏的逐条结果用 `--guard=design/targets.json` 看。

```
== each bot 200 games (seeds 1-200), cards played greedy; targets: PLAN step 8 ==
-- full-training month median (10%-90%) [target 16-21] | months with rep >= 210 | main-road rep median at months 12/24/36/48
only_tough full 42(34–48)[42%] 210:34(23–44)    115/156/245/350
only_lover full 42(36–47)[77%] 210:25(19–36)    154/205/299/373
only_culture full 39(33–46)[25%] 210:29(19–45)[67%] 130/167/218/255
only_savvy full 33(29–36)      210:20(18–21)    112/294/366/376
two_roads full —              210:43(35–48)[14%] 99/142/161/191
crime_line full —              210:27(22–34)    131/208/235/248
books_culture full 37(31–43)      210:20(16–25)    140/273/353/370
random_pick full —              210:43(36–48)[20%] 84/109/144/181
disciplined_tough full 32(27–39)      210:21(16–26)    152/276/367/389
disciplined_lover full 30(25–40)      210:19(14–27)    170/277/369/393
disciplined_culture full 31(26–42)      210:21(15–27)    137/267/372/389
disciplined_savvy full 27(24–30)      210:19(17–21)    99/325/368/385
bad_boy_tough full 36(29–43)      210:13(11–15)    208/290/360/383
bad_boy_lover full 25(24–30)      210:14(13–17)    196/340/382/398
bad_boy_savvy full 31(28–36)      210:22(19–27)    95/265/368/389
addict_tough full 36(27–43)[44%] 210:22(15–33)[85%] 149/227/292/317
addict_lover full 33(27–42)[81%] 210:20(14–34)    165/253/353/378
addict_culture full 34(25–45)[41%] 210:27(16–40)[77%] 130/162/248/301
addict_savvy full 26(23–30)      210:18(16–21)    115/335/369/385
-- final main-road rep breakdown (mean): training+gear and stamina+releases+annual+opportunities | full training plus plain releases (no gear) median [311-340], over 311 [90%] | grade S/A/B/C/D %
only_tough 267+30+10+ 6+10 = 350 | 300 over 311  26% | 0/15/54/19/12
only_lover 291+35+14+ 6+17 = 373 | 311 over 311  52% | 0/29/60/11/0
only_culture 215+20+10+ 6+18 = 255 | 212 over 311  15% | 0/13/20/33/33
only_savvy 300+27+13+13+24 = 376 | 312 over 311  58% | 0/35/64/0/0
two_roads 175+ 8+ 7+ 6+ 0 = 191 | 179 over 311   0% | 0/0/0/14/85
crime_line 224+10+ 7+ 7+-0 = 248 | 231 over 311   0% | 0/0/0/99/0
books_culture 299+32+15+13+10 = 370 | 314 over 311  69% | 0/13/85/1/0
random_pick 182+ 0+ 2+ 1+-8 = 181 | 185 over 311   0% | 0/0/0/19/80
disciplined_tough 300+39+18+12+20 = 389 | 316 over 311  80% | 0/70/30/0/0
disciplined_lover 300+37+20+10+26 = 393 | 318 over 311  78% | 1/69/29/0/0
disciplined_culture 297+34+15+14+24 = 389 | 313 over 311  64% | 0/71/26/2/0
disciplined_savvy 300+30+15+13+28 = 385 | 314 over 311  70% | 0/59/40/0/0
bad_boy_tough 299+40+14+14+12 = 383 | 312 over 311  60% | 0/53/45/1/0
bad_boy_lover 300+37+23+13+25 = 398 | 322 over 311  90% | 0/79/20/0/0
bad_boy_savvy 298+30+15+13+27 = 389 | 312 over 311  60% | 0/62/35/0/1
addict_tough 256+28+ 7+ 9+ 2 = 317 | 288 over 311  18% | 0/21/31/30/17
addict_lover 287+33+13+ 8+17 = 378 | 312 over 311  52% | 0/42/43/11/3
addict_culture 239+21+ 8+ 8+19 = 301 | 258 over 311  24% | 0/24/25/28/22
addict_savvy 298+30+13+14+27 = 385 | 314 over 311  66% | 0/61/37/2/0
-- cash at each year end, median (years 1-4) [first two years <1000] | final p90 [<10k] | final >10k | debt months | film fees total, gear spend (mean)
only_tough 141 / 237 / 367 / 653            p90   1,227  >10k   0%  debt  2.3 |  5,869   290
only_lover 147 / 221 / 444 / 966            p90   2,290  >10k   0%  debt  0.4 |  8,030   122
only_culture 214 / 170 / 208 / 314            p90     847  >10k   0%  debt  0.3 |  5,988   161
only_savvy 402 / 655 / 900 / 767            p90   1,926  >10k   0%  debt  0.3 |  9,651   578
two_roads 198 / 264 / 231 / 309            p90     517  >10k   0%  debt  0.0 |  6,089   118
crime_line 501 / 1,115 / 1,749 / 2,920      p90   4,026  >10k   0%  debt  0.3 |  4,582     0
books_culture 342 / 418 / 798 / 2,546          p90   4,398  >10k   0%  debt  0.1 |  8,455   402
random_pick -687 / -1,420 / -1,856 / -1,971  p90    -420  >10k   0%  debt 43.6 |  1,914     0
disciplined_tough 270 / 545 / 746 / 1,276          p90   2,734  >10k   0%  debt  0.1 |  9,671   921
disciplined_lover 244 / 404 / 832 / 1,089          p90   3,108  >10k   0%  debt  0.1 | 10,376   150
disciplined_culture 351 / 380 / 723 / 841            p90   2,615  >10k   0%  debt  0.1 |  8,137   390
disciplined_savvy 484 / 1,433 / 1,407 / 2,669      p90   4,812  >10k   0%  debt  0.0 | 10,880 1,613
bad_boy_tough 397 / 1,009 / 2,059 / 2,410      p90   3,172  >10k   0%  debt  1.1 |  7,627 1,864
bad_boy_lover 322 / 2,224 / 2,513 / 2,750      p90   3,735  >10k   0%  debt  0.2 |  9,877   184
bad_boy_savvy 349 / 2,230 / 2,821 / 2,799      p90   4,336  >10k   0%  debt  1.2 |  9,151 1,974
addict_tough 172 / 224 / 227 / 108            p90     920  >10k   0%  debt 12.9 |  6,948   315
addict_lover 198 / 262 / 538 / 652            p90   1,752  >10k   0%  debt  4.6 |  9,051   131
addict_culture 252 / 186 / 287 / 347            p90   1,334  >10k   0%  debt  4.3 |  6,038   195
addict_savvy 413 / 1,269 / 1,426 / 2,247      p90   4,468  >10k   0%  debt  0.8 | 10,292 1,404
-- auditions per game, won% small/medium/big [big 10-35%] | releases per game, hit% [10%] flop% | leads small/medium/big | supports, breaches
only_tough 17.9 games 100/47/0% (big 0.0 games) | release 14.1 hit   4% flop  34% | 9.1/3.1/0.0 | 1.9 0.8
only_lover 19.0 games 100/53/22% (big 0.4 games) | release 15.1 hit  10% flop  20% | 5.5/6.7/0.1 | 2.8 0.0
only_culture 17.9 games 100/42/23% (big 0.1 games) | release 15.0 hit   4% flop  25% | 10.3/2.8/0.0 | 1.9 0.0
only_savvy 18.7 games 100/60/13% (big 0.3 games) | release 15.4 hit   2% flop  28% | 5.5/7.5/0.0 | 2.4 0.0
two_roads 19.1 games 100/38/nan% (big 0.0 games) | release 14.7 hit   9% flop  24% | 9.5/3.1/0.0 | 2.1 0.0
crime_line 17.2 games 100/40/nan% (big 0.0 games) | release 14.0 hit   2% flop  64% | 10.9/1.7/0.0 | 1.4 1.0
books_culture 18.5 games 100/53/18% (big 0.2 games) | release 15.3 hit   4% flop  26% | 6.6/6.0/0.0 | 2.7 0.0
random_pick 10.0 games 84/10/nan% (big 0.0 games) | release  7.0 hit   1% flop  55% | 6.6/0.1/0.0 | 0.3 0.4
disciplined_tough 18.4 games 100/61/26% (big 0.5 games) | release 15.7 hit   5% flop  29% | 5.3/7.8/0.1 | 2.5 0.2
disciplined_lover 19.0 games 100/60/21% (big 1.5 games) | release 15.7 hit  11% flop  21% | 3.9/8.5/0.2 | 3.0 0.0
disciplined_culture 18.5 games 100/55/14% (big 0.5 games) | release 15.5 hit   4% flop  32% | 6.4/6.5/0.0 | 2.6 0.0
disciplined_savvy 18.5 games 100/64/14% (big 1.2 games) | release 16.0 hit   5% flop  24% | 5.0/8.4/0.1 | 2.4 0.0
bad_boy_tough 18.0 games 100/63/0% (big 0.0 games) | release 14.8 hit   4% flop  49% | 5.3/7.4/0.0 | 2.1 1.2
bad_boy_lover 18.4 games 100/71/16% (big 0.9 games) | release 15.8 hit  13% flop  19% | 2.7/10.7/0.1 | 2.3 0.7
bad_boy_savvy 17.9 games 100/62/23% (big 0.4 games) | release 15.6 hit   7% flop  21% | 7.3/6.5/0.1 | 1.8 0.5
addict_tough 18.1 games 100/56/12% (big 0.0 games) | release 13.9 hit   1% flop  71% | 6.6/5.1/0.0 | 2.2 1.5
addict_lover 18.9 games 100/58/16% (big 0.7 games) | release 15.0 hit   5% flop  42% | 4.4/7.7/0.1 | 2.8 0.7
addict_culture 17.7 games 99/48/10% (big 0.1 games) | release 14.7 hit   3% flop  51% | 9.9/3.1/0.0 | 1.6 0.5
addict_savvy 17.9 games 100/68/14% (big 0.6 games) | release 15.5 hit   3% flop  37% | 5.3/8.1/0.0 | 2.0 0.4
-- median fame at each year end | final fame tier unknown/familiar/famous/hot/superstar % | mean annual rank (years 1-4) | collapse% | endings (kinds [>=3]; top four)
only_tough 134/150/161/178  0/31/66/2/0    rank 4.8/3.6/3.1/2.8  collapse 0%  endings 10 kinds: tough_stunt30% tough_rider23% tough_gym19% tough_adventurer13%
only_lover 162/207/282/352  0/0/28/67/4    rank 5.5/4.0/3.1/2.1  collapse 0%  endings 12 kinds: act_lover35% lover_widow19% act_art17% lover_dance_hall9%
only_culture 124/155/172/197  0/1/96/3/0     rank 3.2/3.7/3.1/2.9  collapse 0%  endings 5 kinds: cult_editor33% cult_street_photo33% cult_tabloid30% act_voice2%
only_savvy 122/156/186/245  0/1/79/20/0    rank 2.4/3.0/2.0/2.3  collapse 0%  endings 7 kinds: biz_broker61% biz_agent19% act_voice8% act_character6%
two_roads 162/191/205/235  0/0/94/5/0     rank 4.8/3.1/3.2/3.2  collapse 0%  endings 7 kinds: biz_sales69% tough_thug13% biz_boss7% act_second5%
crime_line 114/107/90/83    16/63/17/3/0   rank 4.8/2.6/3.1/3.1  collapse 0%  endings 4 kinds: dark_thug_boss65% dark_boss31% act_lowbudget3% dark_prison0%
books_culture 124/160/211/253  0/0/75/24/0    rank 3.1/2.8/1.9/2.0  collapse 0%  endings 5 kinds: cult_tabloid74% act_voice19% act_art4% act_lowbudget1%
random_pick 94/63/42/25      93/6/0/0/0     rank 5.6/5.3/5.0/5.1  collapse 0%  endings 6 kinds: biz_sales45% dark_prison26% dark_con13% biz_boss13%
disciplined_tough 144/178/212/285  0/2/54/42/1    rank 4.0/2.2/2.0/2.1  collapse 0%  endings 7 kinds: tough_adventurer30% act_voice29% tough_rider26% act_action9%
disciplined_lover 161/219/316/413  0/0/9/74/16    rank 5.3/3.6/2.0/2.0  collapse 0%  endings 10 kinds: act_lover43% act_art17% act_voice11% lover_widow9%
disciplined_culture 122/151/196/249  0/0/74/25/0    rank 3.1/2.8/1.6/2.0  collapse 0%  endings 6 kinds: cult_writer46% cult_screenwriter26% act_voice21% act_art3%
disciplined_savvy 120/157/218/324  0/0/32/68/0    rank 2.7/2.9/2.0/2.2  collapse 0%  endings 7 kinds: act_voice53% biz_broker19% biz_agent13% act_undefined4%
bad_boy_tough 130/147/139/170  2/41/42/13/0   rank 2.5/2.0/2.0/2.3  collapse 0%  endings 6 kinds: dark_thug_boss86% act_action5% act_art2% act_voice2%
bad_boy_lover 164/202/288/345  0/6/33/42/18   rank 5.0/2.7/1.6/2.0  collapse 0%  endings 12 kinds: dark_thug_boss38% act_lover28% act_voice9% idol9%
bad_boy_savvy 117/119/158/253  1/19/42/31/6   rank 2.9/3.0/1.9/2.3  collapse 0%  endings 10 kinds: dark_con61% act_voice23% act_character4% act_art3%
addict_tough 128/141/139/142  2/55/39/3/0    rank 4.0/2.7/2.6/2.8  collapse 0%  endings 11 kinds: tough_thug46% dark_thug_boss25% dark_con21% act_voice2%
addict_lover 149/190/249/289  0/5/51/42/1    rank 5.3/3.7/2.5/2.2  collapse 0%  endings 16 kinds: lover_widow37% act_lover25% act_voice9% lover_dance_hall9%
addict_culture 107/126/140/152  1/46/46/6/0    rank 3.2/3.6/2.8/2.7  collapse 0%  endings 7 kinds: cult_tabloid43% cult_editor28% cult_street_photo22% act_voice4%
addict_savvy 109/136/186/274  0/10/54/35/0   rank 2.3/2.8/1.9/2.2  collapse 0%  endings 11 kinds: biz_agent32% biz_broker30% act_voice25% act_lover5%
-- without buying gear: final cash median / p90 | final main-road rep median | grade S/A/B/C/D %
only_tough     516 /   1,069 | 328 | 0/0/63/24/12
only_lover     802 /   1,410 | 326 | 0/0/76/23/0
only_culture     313 /     916 | 264 | 0/0/36/27/36
only_savvy     582 /   1,367 | 345 | 0/0/100/0/0
-- from events, median per game: main-road rep from events (skills + rep_bonus) [<=30] | event money net, % of all money gained [+-10%] | event fatigue net per year [+-60] | opportunity rep
only_tough ev rep   5 | money    400 (  3.1%) | fatigue/yr   10 | opp rep 10
only_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 10
only_culture ev rep  12 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 15
only_savvy ev rep  43 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
two_roads ev rep  66 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 0
crime_line ev rep   5 | money  1,500 ( 11.2%) | fatigue/yr   10 | opp rep 0
books_culture ev rep  25 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 10
random_pick ev rep  14 | money      0 (  0.0%) | fatigue/yr   12 | opp rep 0
disciplined_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
disciplined_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
disciplined_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
disciplined_savvy ev rep   9 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
bad_boy_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   31 | opp rep 25
bad_boy_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   40 | opp rep 25
bad_boy_savvy ev rep   5 | money      0 (  0.0%) | fatigue/yr   39 | opp rep 25
addict_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr  -14 | opp rep 10
addict_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr  -11 | opp rep 25
addict_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr  -12 | opp rep 15
addict_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr   -8 | opp rep 25
-- step 12c strategies, median per game: rest% (home+outing+church of 144) resort% | void periods (detained/detox/missing/sanatorium means) | arrests detox sanatorium boosts crime-job periods | full month | cash y2 / end / end p10 | S/A/B/C-/collapse% | grade mean
disciplined_tough   rest 33% resort  0% | void  2 (1.5/0.0/0.0/0.0) | arr 1 detox 0 sana 0 boost  0 crimeP  0 | full 32 |    545 /  1,276 /    560 | 0/70/30/0/0 | 2.70
disciplined_lover   rest 34% resort  0% | void  0 (0.1/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 30 |    404 /  1,089 /    620 | 1/70/30/0/0 | 2.71
disciplined_culture rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 31 |    380 /    841 /    388 | 0/72/26/2/0 | 2.69
disciplined_savvy   rest 33% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 27 |  1,433 /  2,669 /  1,148 | 0/60/40/0/0 | 2.60
bad_boy_tough       rest 32% resort 18% | void 10 (9.6/0.0/0.6/0.0) | arr 5 detox 0 sana 0 boost  0 crimeP 36 | full 36 |  1,009 /  2,410 /  1,804 | 0/54/46/1/0 | 2.52
bad_boy_lover       rest 33% resort 24% | void  4 (4.7/0.0/0.4/0.0) | arr 2 detox 0 sana 0 boost  0 crimeP 24 | full 25 |  2,224 /  2,750 /  1,874 | 0/80/20/0/0 | 2.81
bad_boy_savvy       rest 32% resort 24% | void  4 (5.4/0.0/0.5/0.0) | arr 2 detox 0 sana 0 boost  0 crimeP 24 | full 31 |  2,230 /  2,799 /  1,968 | 0/62/36/2/0 | 2.59
addict_tough        rest 17% resort  0% | void 17 (15.4/4.4/1.4/0.0) | arr 3 detox 1 sana 0 boost 11 crimeP  0 | full 99 |    224 /    108 / -1,864 | 0/21/32/48/0 | 1.56
addict_lover        rest 26% resort  0% | void  5 (1.0/4.6/0.3/0.0) | arr 0 detox 1 sana 0 boost 13 crimeP  0 | full 33 |    262 /    652 /   -367 | 0/42/43/14/0 | 2.25
addict_culture      rest 33% resort  0% | void  6 (0.0/4.1/0.1/0.0) | arr 0 detox 2 sana 0 boost 15 crimeP  0 | full 99 |    186 /    347 /   -327 | 0/24/25/50/0 | 1.51
addict_savvy        rest 31% resort  0% | void  3 (0.0/3.9/0.1/0.0) | arr 0 detox 1 sana 0 boost 17 crimeP  0 | full 26 |  1,269 /  2,247 /    748 | 0/61/37/2/0 | 2.59
= disciplined (mean of roads) rest 34% resort  0% | void  0 (0.4/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 30 |    690 /  1,469 /    679 | 0/68/32/0/0 | 2.68
= bad_boy (mean of roads) rest 32% resort 22% | void  6 (6.6/0.0/0.5/0.0) | arr 3 detox 0 sana 0 boost  0 crimeP 28 | full 31 |  1,821 /  2,653 /  1,882 | 0/65/34/1/0 | 2.64
= addict (mean of roads) rest 27% resort  0% | void  8 (4.1/4.2/0.4/0.0) | arr 1 detox 1 sana 0 boost 14 crimeP  0 | full 64 |    485 /    838 /   -452 | 0/37/34/29/0 | 1.98
   grade mean vs disciplined [+-0.3]: bad_boy -0.04, addict -0.70, bad_boy S spread across roads 0 pp [<=8]
```
