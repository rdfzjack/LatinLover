# 平衡记录

每轮改数值在“改动记录”里加一段：改了什么、为什么、前后对比。改完重跑 Godot 报告（第 12b 步起，命令见 `README.md`；`sim/` 冻结），把下面“现在的报告”整段换掉。

## 第 12c 步 c3 之后

定下来的数、护栏、交给 Opus 的活在 `design/C3_ROUND1.md`。每一轮的前后对比在下面的改动记录里。“现在的报告”是第 4 轮（机器人改过以后）跑的。

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

### 第 12c 步 c3 第 4 轮：机器人改得会玩；大卖收益的试算（只试算，没改数）

**机器人**（`bots.gd`，规则和数值没动）：

| 机器人 | 改了什么 | 之前 → 之后（200 局） |
|---|---|---|
| `wild`（坏孩子 + 买药） | 瘾到最深一段（阶段 3）当月去戒，不买 | 倒下 14% → 0%；均分差 −0.60 → −0.06 |
| 用药四种 | 买药前留够一个月生活费 + 这个月的学费；有拍戏的月份，手里的药先留给拍摄旬 | 均分差 −0.01～−0.09 → −0.00～+0.01 |
| `only_*` | 用自律线的休息规则（`RoadBot.disc_pick`，原来疲劳 ≥45 才歇） | 过 311：文化 15% → 61%，四路 61–80% |
| 新加 `bold_*` | 肯冒险的坏孩子：月末失控指数只压在 100 以下（100 必被捕），二级犯罪工每月做两旬 | 见下：还不能用 |

`bold` 还是笨：两旬犯罪工挤掉了练习，三路都练不满（练满月中位 79 = 没练满），均分差 −0.72。它量不出“坏孩子的下行”，只量出“不练习”。**下面整份报告里的 `bold` 几行是更早的版本（月末失控指数不设上限，硬汉路一局被捕 39 次），不要看**；压在 100 以下的版本只在下面大卖试算里跑过。

另外把大卖的倍数从代码挪进表：`roles.json` 的 `release.hit_mult`（现为 2，结果不变）。

**大卖收益的试算**（用户问：大卖收益 ×2 或 ×3 会不会破坏平衡）。各 100 局，17 个策略机器人。“×2”指大卖的收益翻倍：现在大卖让上映声望翻倍（`hit_mult` 2），×2 即 `hit_mult` 4、×3 即 `hit_mult` 6。表里是 S/A/B %，均分：

| | 现在（2） | 收益 ×2（4） | 收益 ×3（6） |
|---|---|---|---|
| 自律 | 0/72/27，2.71 | 1/74/24，2.75 | 4/74/21，2.82 |
| 坏孩子 | 0/78/21，2.77 | 6/75/18，2.85 | 11/71/18，2.91 |
| 坏孩子 + 买药（`wild`） | 0/65/33，2.64 | 3/66/30，2.70 | 11/60/28，2.79 |
| 只在拍摄旬用药（`shoot`） | 0/71/27，2.69 | 2/74/22，2.77 | 8/72/20，2.86 |
| 对自律线的均分差 | ≤ ±0.08 | ≤ +0.10 | ≤ +0.09 |
| 坏孩子 S 档三路相差（护栏 ≤8） | 1 | 14 | 21 |

按路看 S（收益 ×3）：自律情人 11%、自律文化 0%；坏孩子情人 22%、坏孩子手腕 1%；`wild` 情人 26%、`wild` 手腕 2%。

各路的大卖率（现在，各机器人的范围）：情人 8–16%，硬汉 2–9%，文化 3–7%，手腕 3–9%。原因在规则：表现 P 的加分技能所有 16 个角色都是默认的演技（`roles.json` `defaults.bonus_skill`），演技只有情人路在练，情人路的 P 高约 0.2。

读法：大卖收益是全局旋钮，三条线一起抬，线和线之间的差几乎不动；S 几乎全落在情人路。×3 时自律线 S 4%（护栏 ≤2%）。

## 现在的报告

第 12c 步 c3 第 4 轮（机器人改过之后，数值没动），Godot `report.gd --n=200 --bots=all`，4 个进程分段再 `--merge`，带 `--guard=design/targets.json`。`bold_*` 几行是旧版本，不要看（见第 4 轮）。护栏不过 9 条：自律线档次分布 3 条、坏孩子线 3 条（S 和下行要靠大卖和以后的 NPC 线）、专练文化和手腕的大卖率 2 条、专练手腕第 2 年现金 1 条。

```
== each bot 200 games (seeds 1-200), cards played greedy; targets: PLAN step 8 ==
-- full-training month median (10%-90%) [target 16-21] | months with rep >= 210 | main-road rep median at months 12/24/36/48
only_tough full 30(26–35)      210:19(15–23)    161/298/371/392
only_lover full 31(26–39)      210:19(15–27)    166/265/369/392
only_culture full 32(27–40)      210:20(15–27)    137/262/372/386
only_savvy full 27(25–30)      210:19(18–21)    99/323/367/385
two_roads full —              210:46(39–48)[25%] 99/143/165/195
crime_line full —              210:25(22–34)    139/210/239/248
books_culture full 37(31–45)      210:21(16–26)    141/264/337/367
random_pick full —              210:43(35–48)[18%] 83/113/139/173
disciplined_tough full 30(26–35)      210:19(15–23)    161/298/371/392
disciplined_lover full 31(26–39)      210:19(15–27)    166/265/369/392
disciplined_culture full 32(27–40)      210:20(15–27)    137/262/372/386
disciplined_savvy full 27(25–30)      210:19(18–21)    99/323/367/385
bad_boy_tough full 26(22–31)      210:12(11–13)    217/345/379/397
bad_boy_lover full 25(22–28)      210:14(12–17)    196/352/382/402
bad_boy_savvy full 31(27–37)      210:21(19–28)    96/281/370/391
bold_tough full 38(28–43)[14%] 210:13(11–30)[67%] 187/215/221/222
bold_lover full 42(34–46)[48%] 210:14(12–18)    196/259/293/359
bold_savvy full 43(40–47)[1%]  210:22(20–25)    100/249/324/339
wild_tough full 29(22–34)      210:12(11–15)    213/321/370/388
wild_lover full 25(22–30)      210:14(13–17)    194/349/382/401
wild_savvy full 33(28–40)      210:22(19–29)    98/260/361/378
addict_tough full 30(25–35)      210:19(15–23)    160/297/371/393
addict_lover full 31(27–39)      210:19(15–27)    166/265/371/391
addict_culture full 33(27–42)      210:21(16–27)    137/258/370/386
addict_savvy full 27(24–30)      210:19(17–21)    99/328/370/382
quit_tough full 30(25–35)      210:19(15–23)    160/297/371/393
quit_lover full 31(27–39)      210:19(15–27)    166/265/371/391
quit_culture full 33(27–42)      210:21(16–27)    137/259/370/387
quit_savvy full 27(24–30)      210:19(17–21)    99/328/371/386
shoot_tough full 30(25–35)      210:19(15–23)    160/297/372/392
shoot_lover full 32(27–39)      210:19(15–27)    166/265/367/391
shoot_culture full 34(27–45)[85%] 210:21(16–27)    137/253/366/386
shoot_savvy full 27(24–30)      210:19(17–21)    99/321/370/386
allin_tough full 30(25–35)      210:19(15–23)    160/297/371/393
allin_lover full 31(27–39)      210:19(15–27)    166/265/371/391
allin_culture full 33(27–42)      210:21(16–27)    137/258/370/386
allin_savvy full 27(24–30)      210:19(17–21)    99/329/370/383
-- final main-road rep breakdown (mean): training+gear and stamina+releases+annual+opportunities | full training plus plain releases (no gear) median [311-340], over 311 [90%] | grade S/A/B/C/D %
only_tough 300+40+18+13+21 = 392 | 317 over 311  80% | 0/77/22/0/0
only_lover 300+37+20+10+26 = 392 | 319 over 311  78% | 0/73/26/0/0
only_culture 296+34+14+14+24 = 386 | 312 over 311  60% | 0/72/25/3/0
only_savvy 300+30+15+14+28 = 385 | 314 over 311  65% | 0/61/39/0/0
two_roads 178+ 9+ 7+ 6+ 0 = 195 | 184 over 311   0% | 0/0/0/25/75
crime_line 224+10+ 7+ 7+-1 = 248 | 231 over 311   0% | 0/0/0/99/0
books_culture 298+32+14+12+10 = 367 | 312 over 311  60% | 0/10/87/2/0
random_pick 177+ 1+ 1+ 1+-9 = 173 | 180 over 311   0% | 0/0/0/17/83
disciplined_tough 300+40+18+13+21 = 392 | 317 over 311  80% | 0/77/22/0/0
disciplined_lover 300+37+20+10+26 = 392 | 319 over 311  78% | 0/73/26/0/0
disciplined_culture 296+34+14+14+24 = 386 | 312 over 311  60% | 0/72/25/3/0
disciplined_savvy 300+30+15+14+28 = 385 | 314 over 311  65% | 0/61/39/0/0
bad_boy_tough 300+43+20+15+17 = 397 | 318 over 311  83% | 0/81/18/0/0
bad_boy_lover 300+37+24+14+25 = 402 | 324 over 311  88% | 0/81/18/0/0
bad_boy_savvy 299+34+13+13+27 = 391 | 312 over 311  57% | 0/66/32/0/0
bold_tough 225+26+ 5+ 8+-25 = 222 | 213 over 311   7% | 0/8/12/33/47
bold_lover 286+35+15+ 6+10 = 359 | 306 over 311  36% | 0/22/65/12/0
bold_savvy 270+33+ 7+ 9+10 = 339 | 277 over 311   0% | 0/0/80/19/0
wild_tough 300+39+16+15+15 = 388 | 314 over 311  69% | 0/65/33/1/0
wild_lover 300+37+23+14+27 = 401 | 321 over 311  83% | 1/83/15/0/0
wild_savvy 298+31+11+13+24 = 378 | 310 over 311  46% | 0/48/49/1/1
addict_tough 300+40+19+13+21 = 393 | 318 over 311  82% | 0/83/16/0/0
addict_lover 300+37+20+10+27 = 391 | 318 over 311  82% | 1/76/23/0/0
addict_culture 296+34+14+14+24 = 386 | 313 over 311  61% | 0/69/25/5/0
addict_savvy 300+29+15+14+27 = 382 | 314 over 311  66% | 0/54/45/0/0
quit_tough 300+40+19+13+21 = 393 | 317 over 311  82% | 0/81/19/0/0
quit_lover 300+37+20+10+26 = 391 | 318 over 311  81% | 1/75/24/0/0
quit_culture 296+34+15+14+24 = 387 | 314 over 311  66% | 0/70/25/4/0
quit_savvy 300+30+15+14+28 = 386 | 314 over 311  68% | 0/61/38/0/0
shoot_tough 300+40+20+13+21 = 392 | 318 over 311  84% | 1/81/18/0/0
shoot_lover 300+37+20+10+26 = 391 | 319 over 311  76% | 0/71/29/0/0
shoot_culture 295+33+15+13+24 = 386 | 313 over 311  63% | 0/68/27/4/0
shoot_savvy 300+29+17+14+27 = 386 | 316 over 311  73% | 0/63/37/0/0
allin_tough 300+40+19+13+21 = 393 | 318 over 311  82% | 0/83/16/0/0
allin_lover 300+37+20+10+27 = 391 | 319 over 311  82% | 1/76/23/0/0
allin_culture 296+34+14+14+24 = 386 | 313 over 311  61% | 0/69/25/5/0
allin_savvy 300+29+15+14+27 = 383 | 314 over 311  66% | 0/55/44/0/0
-- cash at each year end, median (years 1-4) [first two years <1000] | final p90 [<10k] | final >10k | debt months | film fees total, gear spend (mean)
only_tough 297 / 588 / 792 / 1,126          p90   2,423  >10k   0%  debt  0.1 |  9,713   831
only_lover 249 / 390 / 887 / 1,130          p90   2,769  >10k   0%  debt  0.2 | 10,243   153
only_culture 337 / 372 / 837 / 969            p90   3,100  >10k   0%  debt  0.1 |  8,265   393
only_savvy 481 / 1,338 / 1,492 / 2,622      p90   4,865  >10k   0%  debt  0.0 | 10,628 1,547
two_roads 217 / 269 / 235 / 309            p90     491  >10k   0%  debt  0.1 |  6,115   113
crime_line 792 / 1,002 / 1,238 / 2,009      p90   3,098  >10k   0%  debt  0.0 |  4,886     0
books_culture 330 / 406 / 711 / 2,205          p90   4,364  >10k   0%  debt  0.1 |  8,208   392
random_pick -704 / -1,385 / -1,871 / -1,968  p90    -100  >10k   0%  debt 42.8 |  1,914     0
disciplined_tough 297 / 588 / 792 / 1,126          p90   2,423  >10k   0%  debt  0.1 |  9,713   831
disciplined_lover 249 / 390 / 887 / 1,130          p90   2,769  >10k   0%  debt  0.2 | 10,243   153
disciplined_culture 337 / 372 / 837 / 969            p90   3,100  >10k   0%  debt  0.1 |  8,265   393
disciplined_savvy 481 / 1,338 / 1,492 / 2,622      p90   4,865  >10k   0%  debt  0.0 | 10,628 1,547
bad_boy_tough 408 / 851 / 2,552 / 4,028        p90   6,452  >10k   0%  debt  0.5 |  8,877 4,163
bad_boy_lover 310 / 3,343 / 5,510 / 6,077      p90  10,084  >10k  10%  debt  0.1 | 10,152   169
bad_boy_savvy 363 / 2,255 / 3,470 / 5,614      p90   9,771  >10k   9%  debt  0.9 |  8,846 5,481
bold_tough 164 / -284 / -464 / -549         p90   4,612  >10k   0%  debt 26.1 |  4,775   988
bold_lover 309 / 4,336 / 5,149 / 4,842      p90  10,253  >10k  12%  debt  0.6 |  7,591   191
bold_savvy 364 / 2,444 / 3,653 / 5,043      p90  10,145  >10k  11%  debt  3.1 |  6,467 5,330
wild_tough 395 / 551 / 1,330 / 1,903        p90   3,738  >10k   0%  debt  0.3 |  8,214 1,522
wild_lover 305 / 2,059 / 2,712 / 2,701      p90   5,709  >10k   0%  debt  0.3 |  9,502   168
wild_savvy 346 / 1,277 / 2,407 / 2,513      p90   4,686  >10k   0%  debt  1.1 |  7,576 2,762
addict_tough 292 / 620 / 779 / 1,116          p90   2,492  >10k   0%  debt  0.1 | 10,000   815
addict_lover 249 / 387 / 830 / 1,088          p90   2,531  >10k   0%  debt  0.2 | 10,308   153
addict_culture 327 / 356 / 701 / 715            p90   1,819  >10k   0%  debt  0.2 |  8,061   376
addict_savvy 465 / 1,348 / 1,151 / 2,144      p90   4,355  >10k   0%  debt  0.1 | 10,815 1,397
quit_tough 292 / 620 / 797 / 1,171          p90   2,492  >10k   0%  debt  0.1 |  9,989   918
quit_lover 249 / 387 / 830 / 1,110          p90   2,587  >10k   0%  debt  0.2 | 10,264   153
quit_culture 327 / 357 / 721 / 783            p90   2,363  >10k   0%  debt  0.1 |  8,055   379
quit_savvy 465 / 1,348 / 1,283 / 2,533      p90   4,634  >10k   0%  debt  0.1 | 10,823 1,505
shoot_tough 278 / 617 / 701 / 1,020          p90   2,127  >10k   0%  debt  0.1 |  9,763   760
shoot_lover 251 / 387 / 821 / 1,130          p90   2,808  >10k   0%  debt  0.3 | 10,299   154
shoot_culture 327 / 347 / 678 / 696            p90   1,768  >10k   0%  debt  0.3 |  7,948   375
shoot_savvy 465 / 1,337 / 1,153 / 1,749      p90   4,069  >10k   0%  debt  0.4 | 10,808 1,146
allin_tough 292 / 620 / 779 / 1,116          p90   2,492  >10k   0%  debt  0.1 | 10,000   815
allin_lover 249 / 387 / 831 / 1,088          p90   2,519  >10k   0%  debt  0.2 | 10,314   153
allin_culture 327 / 356 / 701 / 716            p90   1,815  >10k   0%  debt  0.2 |  8,073   376
allin_savvy 465 / 1,338 / 1,134 / 2,137      p90   4,341  >10k   0%  debt  0.3 | 10,841 1,413
-- auditions per game, won% small/medium/big [big 10-35%] | releases per game, hit% [10%] flop% | leads small/medium/big | supports, breaches
only_tough 18.3 games 100/62/13% (big 0.7 games) | release 15.5 hit   6% flop  28% | 4.6/8.1/0.1 | 2.8 0.3
only_lover 18.9 games 100/60/19% (big 1.2 games) | release 15.8 hit  11% flop  22% | 4.0/8.6/0.2 | 3.0 0.0
only_culture 18.3 games 100/56/17% (big 0.5 games) | release 15.6 hit   4% flop  32% | 6.4/6.5/0.1 | 2.6 0.0
only_savvy 18.6 games 100/63/19% (big 1.1 games) | release 15.9 hit   5% flop  23% | 5.2/8.1/0.1 | 2.5 0.0
two_roads 19.1 games 100/39/nan% (big 0.0 games) | release 14.6 hit   8% flop  23% | 9.2/3.2/0.0 | 2.2 0.0
crime_line 17.8 games 100/39/nan% (big 0.0 games) | release 14.3 hit   2% flop  65% | 10.4/2.2/0.0 | 1.7 0.6
books_culture 18.6 games 100/51/23% (big 0.1 games) | release 15.2 hit   5% flop  25% | 6.8/5.7/0.0 | 2.7 0.0
random_pick 10.0 games 84/8/nan% (big 0.0 games) | release  7.1 hit   0% flop  57% | 6.6/0.1/0.0 | 0.4 0.4
disciplined_tough 18.3 games 100/62/13% (big 0.7 games) | release 15.5 hit   6% flop  28% | 4.6/8.1/0.1 | 2.8 0.3
disciplined_lover 18.9 games 100/60/19% (big 1.2 games) | release 15.8 hit  11% flop  22% | 4.0/8.6/0.2 | 3.0 0.0
disciplined_culture 18.3 games 100/56/17% (big 0.5 games) | release 15.6 hit   4% flop  32% | 6.4/6.5/0.1 | 2.6 0.0
disciplined_savvy 18.6 games 100/63/19% (big 1.1 games) | release 15.9 hit   5% flop  23% | 5.2/8.1/0.1 | 2.5 0.0
bad_boy_tough 17.9 games 100/68/5% (big 0.1 games) | release 15.4 hit   6% flop  41% | 4.0/9.2/0.0 | 2.2 0.8
bad_boy_lover 18.2 games 100/72/22% (big 0.8 games) | release 16.0 hit  13% flop  20% | 2.5/11.1/0.1 | 2.3 0.5
bad_boy_savvy 17.9 games 100/61/16% (big 0.1 games) | release 15.4 hit   5% flop  25% | 7.1/6.3/0.0 | 2.0 0.5
bold_tough 17.2 games 98/61/nan% (big 0.0 games) | release 13.2 hit   0% flop  78% | 9.1/2.7/0.0 | 1.4 2.0
bold_lover 18.7 games 100/62/36% (big 0.1 games) | release 13.8 hit  10% flop  22% | 3.7/7.8/0.0 | 2.3 2.1
bold_savvy 18.0 games 100/48/nan% (big 0.0 games) | release 13.7 hit   4% flop  36% | 8.7/3.3/0.0 | 1.8 1.7
wild_tough 18.0 games 100/65/17% (big 0.1 games) | release 14.8 hit   5% flop  46% | 4.5/8.2/0.0 | 2.1 1.2
wild_lover 18.2 games 100/71/20% (big 0.7 games) | release 15.1 hit  16% flop  21% | 2.5/10.3/0.1 | 2.2 1.3
wild_savvy 18.0 games 100/58/8% (big 0.1 games) | release 14.3 hit   8% flop  28% | 7.8/4.9/0.0 | 1.6 1.3
addict_tough 18.2 games 100/63/19% (big 0.8 games) | release 15.8 hit   8% flop  27% | 4.7/8.3/0.1 | 2.7 0.2
addict_lover 18.9 games 100/60/20% (big 1.2 games) | release 15.8 hit  12% flop  21% | 4.0/8.7/0.2 | 3.0 0.0
addict_culture 18.3 games 100/56/26% (big 0.4 games) | release 15.4 hit   4% flop  33% | 6.4/6.3/0.1 | 2.7 0.0
addict_savvy 18.6 games 100/63/16% (big 1.3 games) | release 15.9 hit   5% flop  24% | 5.0/8.3/0.1 | 2.5 0.1
quit_tough 18.2 games 100/63/21% (big 0.8 games) | release 15.7 hit   7% flop  27% | 4.7/8.3/0.1 | 2.7 0.2
quit_lover 18.9 games 100/60/19% (big 1.2 games) | release 15.8 hit  12% flop  21% | 4.0/8.7/0.2 | 3.0 0.0
quit_culture 18.3 games 100/56/22% (big 0.4 games) | release 15.4 hit   4% flop  32% | 6.3/6.3/0.0 | 2.7 0.0
quit_savvy 18.5 games 100/63/17% (big 1.4 games) | release 15.9 hit   4% flop  24% | 5.0/8.3/0.1 | 2.6 0.0
shoot_tough 18.4 games 100/61/14% (big 0.8 games) | release 15.6 hit   9% flop  28% | 4.7/8.0/0.1 | 2.8 0.2
shoot_lover 18.9 games 100/60/24% (big 1.2 games) | release 15.7 hit  12% flop  22% | 4.0/8.5/0.2 | 3.0 0.0
shoot_culture 18.3 games 100/56/12% (big 0.4 games) | release 15.3 hit   7% flop  29% | 6.5/6.2/0.0 | 2.5 0.0
shoot_savvy 18.6 games 100/64/11% (big 1.3 games) | release 15.9 hit   8% flop  22% | 5.1/8.3/0.1 | 2.5 0.1
allin_tough 18.2 games 100/63/19% (big 0.8 games) | release 15.8 hit   8% flop  27% | 4.7/8.3/0.1 | 2.7 0.2
allin_lover 18.9 games 100/60/20% (big 1.2 games) | release 15.9 hit  12% flop  21% | 4.0/8.7/0.2 | 3.0 0.0
allin_culture 18.3 games 100/56/25% (big 0.4 games) | release 15.4 hit   4% flop  33% | 6.4/6.3/0.1 | 2.7 0.0
allin_savvy 18.6 games 100/63/18% (big 1.3 games) | release 15.9 hit   5% flop  24% | 5.0/8.3/0.1 | 2.5 0.0
-- median fame at each year end | final fame tier unknown/familiar/famous/hot/superstar % | mean annual rank (years 1-4) | collapse% | endings (kinds [>=3]; top four)
only_tough 144/180/220/305  0/0/47/52/0    rank 3.7/2.0/2.0/2.1  collapse 0%  endings 8 kinds: act_voice33% tough_adventurer30% tough_rider17% act_action8%
only_lover 158/213/316/408  0/0/8/76/15    rank 5.3/3.6/1.9/2.0  collapse 0%  endings 9 kinds: act_lover41% act_voice16% act_art14% lover_widow8%
only_culture 121/152/197/258  0/0/71/29/0    rank 3.1/2.8/1.7/2.0  collapse 0%  endings 8 kinds: cult_writer44% cult_screenwriter23% act_voice21% act_art4%
only_savvy 120/154/212/322  0/0/39/60/0    rank 2.7/2.9/1.9/2.2  collapse 0%  endings 8 kinds: act_voice49% biz_broker25% biz_agent14% act_art4%
two_roads 162/193/207/234  0/0/93/6/0     rank 4.6/3.1/3.2/3.1  collapse 0%  endings 9 kinds: biz_sales62% biz_boss15% tough_thug7% act_second4%
crime_line 122/118/103/98   3/76/19/1/0    rank 4.6/2.6/3.1/3.1  collapse 0%  endings 5 kinds: dark_thug_boss62% dark_boss36% act_silent0% dark_prison0%
books_culture 124/157/209/250  0/0/78/21/0    rank 3.1/2.9/2.0/2.0  collapse 0%  endings 7 kinds: cult_tabloid76% act_voice17% act_art2% cult_editor2%
random_pick 92/63/41/26      90/10/0/0/0    rank 5.2/5.3/5.1/5.0  collapse 4%  endings 7 kinds: biz_sales41% dark_prison25% dark_con16% biz_boss12%
disciplined_tough 144/180/220/305  0/0/47/52/0    rank 3.7/2.0/2.0/2.1  collapse 0%  endings 8 kinds: act_voice33% tough_adventurer30% tough_rider17% act_action8%
disciplined_lover 158/213/316/408  0/0/8/76/15    rank 5.3/3.6/1.9/2.0  collapse 0%  endings 9 kinds: act_lover41% act_voice16% act_art14% lover_widow8%
disciplined_culture 121/152/197/258  0/0/71/29/0    rank 3.1/2.8/1.7/2.0  collapse 0%  endings 8 kinds: cult_writer44% cult_screenwriter23% act_voice21% act_art4%
disciplined_savvy 120/154/212/322  0/0/39/60/0    rank 2.7/2.9/1.9/2.2  collapse 0%  endings 8 kinds: act_voice49% biz_broker25% biz_agent14% act_art4%
bad_boy_tough 132/154/170/198  0/27/53/18/1   rank 2.4/2.0/2.0/2.1  collapse 0%  endings 8 kinds: dark_thug_boss80% act_voice11% act_action3% act_character2%
bad_boy_lover 163/214/286/350  0/8/31/38/22   rank 5.0/2.4/1.6/2.0  collapse 0%  endings 10 kinds: act_lover32% dark_thug_boss32% idol15% act_art4%
bad_boy_savvy 114/127/147/211  1/28/40/28/1   rank 2.8/2.9/2.0/2.2  collapse 0%  endings 10 kinds: dark_con70% act_voice14% act_lover4% act_lowbudget3%
bold_tough 120/100/82/71    25/54/18/2/0   rank 3.1/2.7/3.3/3.4  collapse 0%  endings 5 kinds: dark_thug_boss52% dark_prison46% act_lowbudget1% act_character0%
bold_lover 163/191/187/193  1/38/23/29/7   rank 5.0/3.8/3.1/2.1  collapse 0%  endings 9 kinds: dark_prison37% dark_con26% act_lover15% act_character6%
bold_savvy 114/112/103/103  10/61/22/5/0   rank 2.8/3.0/2.9/2.9  collapse 0%  endings 6 kinds: dark_con94% act_character2% act_lover1% act_art1%
wild_tough 132/147/148/173  0/40/43/16/0   rank 2.5/2.0/2.0/2.2  collapse 0%  endings 8 kinds: dark_thug_boss83% act_action7% act_voice5% act_art1%
wild_lover 162/202/258/316  0/12/34/38/14  rank 5.0/2.5/1.5/2.0  collapse 0%  endings 11 kinds: dark_thug_boss28% act_lover26% dark_con11% dark_prison7%
wild_savvy 113/117/117/166  3/41/41/15/0   rank 2.8/3.0/2.1/2.3  collapse 0%  endings 8 kinds: dark_con83% act_character7% act_voice2% dark_prison2%
addict_tough 144/185/220/310  0/0/45/53/1    rank 3.7/2.0/2.0/2.1  collapse 0%  endings 10 kinds: act_voice35% tough_adventurer32% tough_rider13% act_action9%
addict_lover 158/214/317/415  0/0/9/72/18    rank 5.3/3.6/1.9/2.0  collapse 0%  endings 10 kinds: act_lover43% act_voice17% act_art14% lover_widow9%
addict_culture 122/150/196/248  0/0/77/22/0    rank 3.1/2.9/1.7/2.0  collapse 0%  endings 8 kinds: cult_writer47% cult_screenwriter25% act_voice19% cult_editor5%
addict_savvy 120/154/219/320  0/0/36/61/2    rank 2.6/2.8/1.9/2.3  collapse 0%  endings 10 kinds: act_voice47% biz_broker23% biz_agent12% act_lover8%
quit_tough 144/185/220/310  0/0/43/54/2    rank 3.7/2.0/2.0/2.1  collapse 0%  endings 9 kinds: act_voice35% tough_adventurer30% tough_rider13% act_action11%
quit_lover 158/214/316/411  0/0/9/73/18    rank 5.3/3.6/1.9/2.0  collapse 0%  endings 9 kinds: act_lover43% act_voice17% act_art14% lover_widow9%
quit_culture 122/150/197/251  0/0/74/26/0    rank 3.1/2.9/1.7/2.0  collapse 0%  endings 7 kinds: cult_writer44% cult_screenwriter25% act_voice20% cult_editor4%
quit_savvy 120/154/217/322  0/0/36/61/2    rank 2.6/2.7/1.9/2.2  collapse 0%  endings 7 kinds: act_voice46% biz_broker24% biz_agent12% act_lover7%
shoot_tough 143/185/219/301  0/0/49/48/2    rank 3.7/2.0/2.0/2.1  collapse 0%  endings 9 kinds: tough_adventurer34% act_voice30% tough_rider15% act_action9%
shoot_lover 157/211/314/413  0/0/9/72/19    rank 5.3/3.6/2.0/2.0  collapse 0%  endings 9 kinds: act_lover38% act_voice18% act_art11% idol10%
shoot_culture 122/152/196/255  0/0/73/26/0    rank 3.1/2.9/1.8/2.0  collapse 0%  endings 8 kinds: cult_writer42% cult_screenwriter26% act_voice22% cult_editor4%
shoot_savvy 120/155/225/333  0/0/33/66/0    rank 2.6/2.9/1.8/2.2  collapse 0%  endings 8 kinds: act_voice45% biz_broker23% biz_agent10% act_lover8%
allin_tough 144/185/220/310  0/0/45/53/1    rank 3.7/2.0/2.0/2.1  collapse 0%  endings 10 kinds: act_voice35% tough_adventurer32% tough_rider13% act_action9%
allin_lover 158/214/317/415  0/0/9/72/18    rank 5.3/3.6/1.9/2.0  collapse 0%  endings 10 kinds: act_lover43% act_voice18% act_art13% lover_widow9%
allin_culture 122/150/196/248  0/0/77/23/0    rank 3.1/2.9/1.7/2.0  collapse 0%  endings 8 kinds: cult_writer47% cult_screenwriter25% act_voice19% cult_editor5%
allin_savvy 120/154/220/322  0/0/34/63/2    rank 2.6/2.8/1.9/2.3  collapse 0%  endings 10 kinds: act_voice49% biz_broker22% biz_agent12% act_lover8%
-- without buying gear: final cash median / p90 | final main-road rep median | grade S/A/B/C/D %
only_tough     981 /   2,434 | 347 | 0/6/94/0/0
only_lover     925 /   1,915 | 342 | 0/6/93/0/0
only_culture     740 /   2,271 | 364 | 0/7/89/4/0
only_savvy   2,538 /   4,790 | 349 | 0/3/96/0/0
-- from events, median per game: main-road rep from events (skills + rep_bonus) [<=30] | event money net, % of all money gained [+-10%] | event fatigue net per year [+-60] | opportunity rep
only_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
only_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
only_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
only_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
two_roads ev rep  69 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 0
crime_line ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 0
books_culture ev rep  26 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 10
random_pick ev rep  16 | money      0 (  0.0%) | fatigue/yr   14 | opp rep 0
disciplined_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
disciplined_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
disciplined_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
disciplined_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
bad_boy_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   30 | opp rep 25
bad_boy_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   39 | opp rep 25
bad_boy_savvy ev rep   5 | money      0 (  0.0%) | fatigue/yr   38 | opp rep 40
bold_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr    9 | opp rep 0
bold_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   38 | opp rep 15
bold_savvy ev rep   5 | money      0 (  0.0%) | fatigue/yr   34 | opp rep 25
wild_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   11 | opp rep 25
wild_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr   -1 | opp rep 25
wild_savvy ev rep   5 | money      0 (  0.0%) | fatigue/yr    3 | opp rep 25
addict_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
addict_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
addict_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
addict_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
quit_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
quit_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
quit_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
quit_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
shoot_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
shoot_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
shoot_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
shoot_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
allin_tough ev rep   5 | money      0 (  0.0%) | fatigue/yr   10 | opp rep 25
allin_lover ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
allin_culture ev rep   5 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
allin_savvy ev rep   7 | money      0 (  0.0%) | fatigue/yr    8 | opp rep 25
-- step 12c strategies, median per game: rest% (home+outing+church of 144) resort% | void periods (detained/detox/missing/sanatorium means) | arrests detox sanatorium boosts crime-job periods | full month | cash y2 / end / end p10 | S/A/B/C-/collapse% | grade mean
disciplined_tough   rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 30 |    588 /  1,126 /    518 | 0/78/22/0/0 | 2.77
disciplined_lover   rest 34% resort  0% | void  0 (0.1/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 31 |    390 /  1,130 /    660 | 0/74/26/0/0 | 2.75
disciplined_culture rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 32 |    372 /    969 /    438 | 0/72/25/3/0 | 2.69
disciplined_savvy   rest 33% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 27 |  1,338 /  2,622 /  1,033 | 0/61/39/0/0 | 2.61
bad_boy_tough       rest 33% resort 18% | void  6 (6.9/0.0/0.5/0.0) | arr 3 detox 0 sana 0 boost  0 crimeP 32 | full 26 |    851 /  4,028 /  1,795 | 0/81/18/0/0 | 2.81
bad_boy_lover       rest 31% resort 22% | void  6 (6.4/0.0/0.4/0.0) | arr 3 detox 0 sana 0 boost  0 crimeP 28 | full 25 |  3,343 /  6,077 /  1,698 | 0/81/18/0/0 | 2.81
bad_boy_savvy       rest 31% resort 22% | void  8 (7.8/0.0/0.5/0.0) | arr 4 detox 0 sana 0 boost  0 crimeP 32 | full 31 |  2,255 /  5,614 /  2,467 | 0/66/32/1/0 | 2.65
bold_tough          rest 15% resort  0% | void 78 (60.5/0.0/4.5/0.0) | arr 39 detox 0 sana 0 boost  0 crimeP 22 | full 99 |   -284 /   -549 / -1,677 | 0/8/12/80/0 | 0.81
bold_lover          rest 30% resort 20% | void 16 (15.9/0.0/0.9/0.0) | arr 8 detox 0 sana 0 boost  0 crimeP 43 | full 99 |  4,336 /  4,842 /  1,353 | 0/22/65/13/0 | 2.08
bold_savvy          rest 28% resort 19% | void 19 (19.9/0.0/1.3/0.0) | arr 9 detox 0 sana 0 boost  0 crimeP 46 | full 99 |  2,444 /  5,043 /  1,567 | 0/0/80/20/0 | 1.79
wild_tough          rest 31% resort 15% | void 13 (5.5/6.8/0.5/0.0) | arr 3 detox 2 sana 0 boost 32 crimeP 34 | full 29 |    551 /  1,903 /  1,076 | 0/66/34/1/0 | 2.65
wild_lover          rest 30% resort 19% | void 14 (4.2/10.2/0.3/0.0) | arr 2 detox 4 sana 0 boost 38 crimeP 27 | full 25 |  2,059 /  2,701 /    938 | 1/84/16/0/0 | 2.85
wild_savvy          rest 28% resort 19% | void 17 (7.0/9.5/0.4/0.0) | arr 3 detox 3 sana 0 boost 38 crimeP 32 | full 33 |  1,277 /  2,513 /  1,260 | 0/48/49/2/0 | 2.44
addict_tough        rest 33% resort  0% | void  0 (0.1/0.2/0.0/0.0) | arr 0 detox 0 sana 0 boost  6 crimeP  0 | full 30 |    620 /  1,116 /    488 | 0/84/16/0/0 | 2.83
addict_lover        rest 33% resort  0% | void  0 (0.0/0.1/0.0/0.0) | arr 0 detox 0 sana 0 boost  2 crimeP  0 | full 31 |    387 /  1,088 /    630 | 1/76/23/0/0 | 2.78
addict_culture      rest 33% resort  0% | void  0 (0.0/0.1/0.0/0.1) | arr 0 detox 0 sana 0 boost  7 crimeP  0 | full 33 |    356 /    715 /    358 | 0/70/26/5/0 | 2.65
addict_savvy        rest 32% resort  0% | void  0 (0.0/0.5/0.0/0.1) | arr 0 detox 0 sana 0 boost  8 crimeP  0 | full 27 |  1,348 /  2,144 /    691 | 0/54/46/0/0 | 2.54
quit_tough          rest 33% resort  0% | void  0 (0.1/0.1/0.0/0.0) | arr 0 detox 0 sana 0 boost  4 crimeP  0 | full 30 |    620 /  1,171 /    565 | 0/81/19/0/0 | 2.81
quit_lover          rest 33% resort  0% | void  0 (0.0/0.1/0.0/0.0) | arr 0 detox 0 sana 0 boost  2 crimeP  0 | full 31 |    387 /  1,110 /    608 | 1/75/24/0/0 | 2.77
quit_culture        rest 33% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  4 crimeP  0 | full 33 |    357 /    783 /    406 | 0/70/26/4/0 | 2.65
quit_savvy          rest 33% resort  0% | void  0 (0.0/0.3/0.0/0.0) | arr 0 detox 0 sana 0 boost  5 crimeP  0 | full 27 |  1,348 /  2,533 /    840 | 0/62/38/0/0 | 2.62
shoot_tough         rest 33% resort  0% | void  0 (0.0/0.3/0.0/0.0) | arr 0 detox 0 sana 0 boost  5 crimeP  0 | full 30 |    617 /  1,020 /    483 | 1/81/18/0/0 | 2.83
shoot_lover         rest 33% resort  0% | void  0 (0.0/0.1/0.0/0.0) | arr 0 detox 0 sana 0 boost  2 crimeP  0 | full 32 |    387 /  1,130 /    612 | 0/71/29/0/0 | 2.71
shoot_culture       rest 34% resort  0% | void  0 (0.0/0.3/0.0/0.0) | arr 0 detox 0 sana 0 boost  7 crimeP  0 | full 34 |    347 /    696 /    308 | 0/68/27/4/0 | 2.64
shoot_savvy         rest 33% resort  0% | void  0 (0.0/0.8/0.0/0.1) | arr 0 detox 0 sana 0 boost  9 crimeP  0 | full 27 |  1,337 /  1,749 /    539 | 0/63/37/0/0 | 2.63
allin_tough         rest 33% resort  0% | void  0 (0.1/0.2/0.0/0.0) | arr 0 detox 0 sana 0 boost  6 crimeP  0 | full 30 |    620 /  1,116 /    488 | 0/84/16/0/0 | 2.83
allin_lover         rest 33% resort  0% | void  0 (0.0/0.1/0.0/0.0) | arr 0 detox 0 sana 0 boost  2 crimeP  0 | full 31 |    387 /  1,088 /    630 | 1/76/23/0/0 | 2.78
allin_culture       rest 33% resort  0% | void  0 (0.0/0.1/0.0/0.1) | arr 0 detox 0 sana 0 boost  7 crimeP  0 | full 33 |    356 /    716 /    358 | 0/70/26/5/0 | 2.65
allin_savvy         rest 32% resort  0% | void  0 (0.0/0.4/0.0/0.2) | arr 0 detox 0 sana 0 boost  8 crimeP  0 | full 27 |  1,338 /  2,137 /    667 | 0/56/44/0/0 | 2.56
= disciplined (mean of roads) rest 34% resort  0% | void  0 (0.0/0.0/0.0/0.0) | arr 0 detox 0 sana 0 boost  0 crimeP  0 | full 30 |    672 /  1,462 /    662 | 0/71/28/1/0 | 2.70
= bad_boy (mean of roads) rest 32% resort 21% | void  7 (7.0/0.0/0.5/0.0) | arr 3 detox 0 sana 0 boost  0 crimeP 31 | full 27 |  2,150 /  5,240 /  1,987 | 0/76/23/1/0 | 2.76
= bold (mean of roads) rest 24% resort 13% | void 38 (32.1/0.0/2.2/0.0) | arr 19 detox 0 sana 0 boost  0 crimeP 37 | full 99 |  2,165 /  3,112 /    414 | 0/10/52/38/0 | 1.56
= wild (mean of roads) rest 30% resort 18% | void 15 (5.6/8.8/0.4/0.0) | arr 3 detox 3 sana 0 boost 36 crimeP 31 | full 29 |  1,296 /  2,372 /  1,091 | 0/66/33/1/0 | 2.65
= addict (mean of roads) rest 32% resort  0% | void  0 (0.0/0.2/0.0/0.0) | arr 0 detox 0 sana 0 boost  6 crimeP  0 | full 30 |    678 /  1,266 /    542 | 0/71/28/1/0 | 2.70
= quit (mean of roads) rest 33% resort  0% | void  0 (0.0/0.1/0.0/0.0) | arr 0 detox 0 sana 0 boost  4 crimeP  0 | full 30 |    678 /  1,399 /    605 | 0/72/27/1/0 | 2.71
= shoot (mean of roads) rest 34% resort  0% | void  0 (0.0/0.3/0.0/0.0) | arr 0 detox 0 sana 0 boost  6 crimeP  0 | full 31 |    672 /  1,149 /    486 | 0/71/28/1/0 | 2.70
= allin (mean of roads) rest 32% resort  0% | void  0 (0.0/0.2/0.0/0.1) | arr 0 detox 0 sana 0 boost  6 crimeP  0 | full 30 |    675 /  1,264 /    536 | 0/71/27/1/0 | 2.70
-- drugs (step 12c c3 round 3), mean per game
wild_tough          doses 32.0 | dealer months 27.9 | addicted in 100% of games | attack months 5.0 | divine 9.5 side 6.7 | detox 2.3 | divine hit film in 32% of games
wild_lover          doses 37.9 | dealer months 27.4 | addicted in 100% of games | attack months 5.8 | divine 11.5 side 7.8 | detox 3.4 | divine hit film in 61% of games
wild_savvy          doses 35.8 | dealer months 29.0 | addicted in 98% of games | attack months 5.0 | divine 10.8 side 7.4 | detox 3.2 | divine hit film in 31% of games
addict_tough        doses 6.4 | dealer months 14.7 | addicted in 66% of games | attack months 1.1 | divine 1.9 side 1.4 | detox 0.1 | divine hit film in 18% of games
addict_lover        doses 2.7 | dealer months 14.7 | addicted in 32% of games | attack months 0.4 | divine 0.8 side 0.6 | detox 0.0 | divine hit film in 4% of games
addict_culture      doses 7.7 | dealer months 15.1 | addicted in 72% of games | attack months 1.7 | divine 2.2 side 1.7 | detox 0.0 | divine hit film in 9% of games
addict_savvy        doses 9.2 | dealer months 14.7 | addicted in 74% of games | attack months 1.7 | divine 2.8 side 2.1 | detox 0.2 | divine hit film in 24% of games
quit_tough          doses 4.6 | dealer months 14.6 | addicted in 66% of games | attack months 0.7 | divine 1.4 side 1.0 | detox 0.0 | divine hit film in 14% of games
quit_lover          doses 2.3 | dealer months 14.7 | addicted in 32% of games | attack months 0.3 | divine 0.7 side 0.5 | detox 0.0 | divine hit film in 4% of games
quit_culture        doses 4.4 | dealer months 14.7 | addicted in 72% of games | attack months 0.9 | divine 1.3 side 1.0 | detox 0.0 | divine hit film in 5% of games
quit_savvy          doses 5.3 | dealer months 14.5 | addicted in 74% of games | attack months 0.9 | divine 1.6 side 1.2 | detox 0.1 | divine hit film in 12% of games
shoot_tough         doses 5.7 | dealer months 14.9 | addicted in 56% of games | attack months 0.9 | divine 1.7 side 1.2 | detox 0.1 | divine hit film in 34% of games
shoot_lover         doses 2.5 | dealer months 14.7 | addicted in 28% of games | attack months 0.4 | divine 0.8 side 0.5 | detox 0.0 | divine hit film in 21% of games
shoot_culture       doses 7.4 | dealer months 14.8 | addicted in 68% of games | attack months 1.7 | divine 2.2 side 1.7 | detox 0.1 | divine hit film in 36% of games
shoot_savvy         doses 9.9 | dealer months 15.2 | addicted in 79% of games | attack months 2.0 | divine 3.1 side 2.0 | detox 0.2 | divine hit film in 44% of games
allin_tough         doses 6.4 | dealer months 14.7 | addicted in 66% of games | attack months 1.1 | divine 1.9 side 1.4 | detox 0.1 | divine hit film in 18% of games
allin_lover         doses 2.8 | dealer months 14.7 | addicted in 32% of games | attack months 0.5 | divine 0.8 side 0.6 | detox 0.0 | divine hit film in 4% of games
allin_culture       doses 7.7 | dealer months 15.1 | addicted in 72% of games | attack months 1.7 | divine 2.2 side 1.7 | detox 0.0 | divine hit film in 9% of games
allin_savvy         doses 9.2 | dealer months 14.8 | addicted in 74% of games | attack months 1.9 | divine 2.8 side 2.1 | detox 0.1 | divine hit film in 23% of games
   grade mean vs disciplined [+-0.3]: bad_boy 0.05, bold -1.14, wild -0.06, addict -0.00, quit 0.01, shoot -0.00, allin -0.00, bad_boy S spread across roads 0 pp [<=8]
-- guard (targets widened by 0%)
PASS disciplined rest_share 33.9 [30.0, 35.0]
PASS disciplined void_periods 0.0 [-, 3.0]
PASS disciplined arrests 0.0 [0.0, 0.0]
PASS disciplined detox 0.0 [0.0, 0.0]
PASS disciplined full_month 30.0 [27.0, 33.0]
PASS disciplined cash_y2 672.0 [-, 1000.0]
PASS disciplined cash_end 1461.8 [1000.0, 3000.0]
PASS disciplined cash_end_p10 662.2 [0.0, -]
PASS disciplined pct_S 0.1 [-, 2.0]
FAIL disciplined pct_A 71.0 [30.0, 45.0]
FAIL disciplined pct_B 28.1 [45.0, 60.0]
PASS disciplined c_or_less 0.8 [-, 10.0]
PASS disciplined pct_collapse 0.0 [-, 1.0]
FAIL disciplined grade_mean 2.7 [2.0, 2.6]
PASS bad_boy rest_share 31.7 [28.0, 34.0]
PASS bad_boy void_periods 6.7 [6.0, 10.0]
PASS bad_boy arrests 3.3 [3.0, 5.0]
PASS bad_boy detox 0.0 [0.0, 0.0]
PASS bad_boy full_month 27.3 [24.0, 30.0]
PASS bad_boy cash_y2 2149.7 [2000.0, 4000.0]
PASS bad_boy cash_end 5239.7 [5000.0, 10000.0]
FAIL bad_boy cash_end_p10 1986.7 [-, 1000.0]
PASS bad_boy pct_S 0.2 [-, 20.0]
FAIL bad_boy pct_A 76.2 [25.0, 30.0]
PASS bad_boy pct_B 23.0 [20.0, 25.0]
FAIL bad_boy c_or_less 0.7 [25.0, 35.0]
PASS bad_boy pct_collapse 0.0 [-, 2.0]
PASS bad_boy grade_mean_vs_disciplined 0.1 [-0.3, 0.3]
PASS bad_boy s_spread 0.5 [-, 8.0]
PASS addict rest_share 32.5 [30.0, 35.0]
PASS addict void_periods 0.0 [-, 3.0]
PASS addict arrests 0.0 [0.0, 1.0]
PASS addict detox 0.0 [-, 1.0]
PASS addict full_month 30.2 [27.0, 33.0]
PASS addict cash_y2 677.8 [-, 1000.0]
PASS addict cash_end 1265.8 [1000.0, 3000.0]
PASS addict cash_end_p10 541.8 [-, -]
PASS addict pct_S 0.2 [-, 35.0]
PASS addict pct_A 70.9 [-, -]
PASS addict pct_B 27.6 [-, -]
PASS addict c_or_less 1.2 [-, 10.0]
PASS addict pct_collapse 0.0 [-, 2.0]
PASS addict grade_mean_vs_disciplined -0.0 [-0.3, 0.3]
PASS only_tough plain_rep 317.0 [311.0, 340.0]
PASS only_tough over_311 80.0 [50.0, -]
PASS only_tough cash_y1 297.0 [-, 1000.0]
PASS only_tough cash_y2 588.0 [-, 1000.0]
PASS only_tough cash_end 1126.0 [-, 10000.0]
PASS only_tough cash_end_p90 2423.0 [-, 10000.0]
PASS only_tough big_win 13.4 [10.0, 35.0]
PASS only_tough hit_rate 6.2 [5.0, 15.0]
PASS only_tough ending_kinds 8.0 [3.0, -]
PASS only_lover plain_rep 319.0 [311.0, 340.0]
PASS only_lover over_311 78.5 [50.0, -]
PASS only_lover cash_y1 249.0 [-, 1000.0]
PASS only_lover cash_y2 390.0 [-, 1000.0]
PASS only_lover cash_end 1130.0 [-, 10000.0]
PASS only_lover cash_end_p90 2769.0 [-, 10000.0]
PASS only_lover big_win 19.4 [10.0, 35.0]
PASS only_lover hit_rate 11.3 [5.0, 15.0]
PASS only_lover ending_kinds 9.0 [3.0, -]
PASS only_culture plain_rep 312.0 [311.0, 340.0]
PASS only_culture over_311 60.5 [50.0, -]
PASS only_culture cash_y1 337.0 [-, 1000.0]
PASS only_culture cash_y2 372.0 [-, 1000.0]
PASS only_culture cash_end 969.0 [-, 10000.0]
PASS only_culture cash_end_p90 3100.0 [-, 10000.0]
PASS only_culture big_win 17.2 [10.0, 35.0]
FAIL only_culture hit_rate 4.0 [5.0, 15.0]
PASS only_culture ending_kinds 8.0 [3.0, -]
PASS only_savvy plain_rep 314.0 [311.0, 340.0]
PASS only_savvy over_311 65.0 [50.0, -]
PASS only_savvy cash_y1 481.0 [-, 1000.0]
FAIL only_savvy cash_y2 1338.0 [-, 1000.0]
PASS only_savvy cash_end 2622.0 [-, 10000.0]
PASS only_savvy cash_end_p90 4865.0 [-, 10000.0]
PASS only_savvy big_win 18.8 [10.0, 35.0]
FAIL only_savvy hit_rate 4.6 [5.0, 15.0]
PASS only_savvy ending_kinds 8.0 [3.0, -]
```
