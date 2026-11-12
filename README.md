# 小咪养成计划

一个 1920 年代好莱坞题材的养成游戏。玩家培养男演员“小咪”，从 1926-01 到 1929-12，每月排三旬日程（上课、看书、打工、休息、拍戏），每季度在选片板上用卡牌试镜抢角色，最后按四条路的声望、名气和品性进结局。规则骨架借自《美少女梦工厂 2》，题材、数值和试镜是新做的。

## 现在做到哪

- **PLAN 第 1–12 步和 8b、9b、9c、12b 已完成；第 12c 步做完了 c1（规则）和 c2（三个新机器人、报告、护栏），c3 的数已定（`design/C3_ROUND1.md`：现状、定下来的数、交给 Opus 的活），下一步是 Opus 重调大卖并重跑整份报告**（Fable 看报告定数，Opus 改表，见 `design/BALANCE_LOG.md`“现在的报告”），再到第 13 步（界面）。12b、12c 的规格在 `design/STEP12B_12C_BALANCE.md`。**从 12b 起 `sim/` 冻结：不再改规则，只留作历史参考；规则只改 `game/silentstar/core/`，机器人和报告在 `game/silentstar/tools/bots.gd` `report.gd`；之后的规矩见 `design/BALANCE_WORKFLOW.md`。**数据、`sim/` 和 Godot 的 `core/` 里的 id、字段名全是英文（对照表 `design/GLOSSARY.md`），中文只在数据表的显示字段里；`data/locale/text.csv` 由 `tools/extract_text.py` 生成（`tools/check.py` 会跑它），`data/USER_GUIDE.md` 已按新写法用英文重写。Godot 对账（命令在 `design/IMPL_NOTES.md` 的 Godot 一节）已通过。
- 用户会自己改 `data/new/` 的表（指南 `data/USER_GUIDE.md`）。开工先跑 `python3 tools/check.py`，不通过先告诉用户。
- 第 12 步：`core/` 加了 `board.gd` `film.gd` `street.gd`（12-1）和 `events.gd` `ending.gd` `story.gd`（12-2；`story.gd` 是 `Month.Hooks` 的子类，内含 `Agent` 和 `SimpleAgent`）。对账：`tools/record_game.py` 把机器人一整局的每个决定录下来（`--extras` 再加剧本、戒毒、放消息、餐厅等月初动作和一份“偏爱的打工”），`tools/trace.py` 录 `trace_cases.json` 的 `games` 段 38 局到 `work/games/`，Godot 回放；每月状态（含整份存档的 md5）、触发过的事件、每块板的试镜和结局逐字节一致。改了表以后，`python3 tools/record_game.py --coverage` 看各机器人还走得到哪些路径。
- 第 12c 步（c1、c2）：疲劳成了约束（上课每天 +3、看书 +2、城里外出只 −3、度假村 −20 带“玩过头”、年度大事 +15）；毒品变成街道动作“提神”（药瘾点数定阶段，阶段 2、3 有后果，“加深”事件删除）；被捕罚款 `max(200, 30%)`、拘留作废下一旬、搜查概率随犯罪升高；道德条款改成被捕或丑闻后 3 个月不能报大片；硬汉、情人、手腕各有两级犯罪工（`crime_tier`，形状由 `check_data.py` 核对）；疗养院出院有副作用；结局“演员”排在“黑暗”前。新机器人 `disciplined_*` `bad_boy_*` `addict_*`；所有机器人按偏好表选事件选项；报告加了“来自事件”和“12c 策略”两段、`--coverage`、`--guard`；`design/targets.json` 是护栏，`tools/check.py` 第 5 步用 Godot 跑 30 局对它（没有 Godot 就跳过）；事件都有了 `tier`，`check_data.py` 查预算。`sim/` 改读 `sim/data_12b/`（12b 时的表），Python 和 Godot 不再对账。细节见 `design/IMPL_NOTES.md` 的 Step 12c 一节。
- 第 12b 步：机器人和报告搬进了 Godot（`tools/bots.gd` `tools/report.gd`），没改任何规则和数值。先把 Python 机器人的随机数换成 PCG32（单独一条流，序号 3），再移植；`trace_cases.json` 的 `bots` 段让 8 种机器人各跑 5 个种子（每月存档 md5 + `summarize` 的 JSON），Godot 和 Python 逐字节一致；`report.gd --n=200 --bots=all` 的输出和 `python3 -m sim.report` 逐字符相同（基准是 `design/BALANCE_LOG.md`“现在的报告”）。耗时和移植时发现的 Python 侧问题见 `design/IMPL_NOTES.md`。
- 第 11 步：`core/audition.gd` 移植了试镜（组牌、有效点数、对手习惯、对手组牌、结果档、`audition()`）；`trace_cases.json` 的 `audition` 段跑 1000 场（月份、名气、声望、场风、有名和无名对手、大片两场、被记住、搞砸都有），Godot 和 Python 逐轮一致。
- 第 10 步：`core/schedule.gd`、`month.gd` 移植了日程和月结（钩子为空，选片板等第 12 步接）；`tools/trace_cases.json` 的 `month` 段跑 7 组 48 个月的固定日程（含外出、看书、病倒、疗养院、崩溃结局、存读档），Godot 和 Python 逐字节一致。
- 第 9 步：Godot 工程 `game/silentstar/` 有了数据加载、随机数、状态、条件和效果、存读档，和 Python 对账逐字节一致（命令在 `design/IMPL_NOTES.md` 的 Godot 一节）。
- 股票系统已删；休息只剩在家（Sil 陪着）和外出（选去处）两种（`design/CHANGE.md`）。
- `sim/`（Python 试算器）能从开局跑到结局，数值调过一轮（第 8 步）；之后的数值都在 Godot 里调，现状见 `design/C3_ROUND1.md`。
- 用户要等第 13、14 步有界面以后才能自己试玩。角色、事件、NPC、文本大多是占位（第 16–18 步补）。

## 文档各管什么

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| `README.md` | 现状、文件地图、用户定过和待定的事 | 每次开工先读 |
| `PLAN.md` | 分步计划，一步一个对话 | 找这一步要读什么、产出什么 |
| `design/BALANCE_WORKFLOW.md` | 12b 之后的规矩：改哪里（规则只改 Godot，`sim/` 冻结）、加内容／加系统／调平衡各怎么做、事件预算、护栏 | 12b 完成后，每次开工先读 |
| `design/CHANGE.md` | 用户的修改意见，和每条在哪一步处理 | 每次开工先读 |
| `design/GDD.md` | 全部规则和数值，以它为准 | 只读这一步涉及的小节 |
| `design/DESIGN_NOTES.md` | GDD 里每个 [推N…] 的理由 | 想改某条规则前查它为什么这样定 |
| `design/BALANCE_LOG.md` | 数值调过什么、现在的报告、没解决的项 | 改数值前 |
| `design/STEP9C_IDS_AND_LOCALE.md` | 第 9c 步的规格：英文 id、语言文件、规矩和完成标准 | 做 9c 时 |
| `design/GLOSSARY.md` | 中文名 → 英文 id 对照表（英文文档，由 `tools/i18n_map.json` 生成） | 在设计文档里看到中文名、要找 id 时 |
| `tools/extract_text.py` | 显示字段清单；生成 `data/locale/text.csv`（`key,zh_CN,en`）；`--prune` `--ack` | 加内容、改名、翻译时 |
| `design/IMPL_NOTES.md` | `sim/` 和 Godot 的结构、接口、GDD 没写到的实现细节、对账命令 | 移植 Godot、改 `sim/` 时 |
| `data/new/README.md` | JSON 表的条件、效果语法 | 改表时 |
| `data/USER_GUIDE.md` | 给用户的改表指南（中文、带例子） | 改了表的写法、加了字段时同步更新 |

数值有三处：`data/new/*.json` 是真源，GDD 是说明，两边不一致时以 JSON 为准并改 GDD。

## 目录

| 目录 | 内容 |
|---|---|
| `data/new/` | 数据表，手工维护。`sim/` 和以后的 Godot 读同一份 |
| `sim/` | Python 试算器：规则的旧参考实现。**12b 起冻结**，读 `sim/data_12b/`（12b 时的表快照），只留作历史参考 |
| `tests/new/` | 试算器的单元测试 |
| `game/silentstar/` | Godot 4.3 工程：`core/` 逻辑（不依赖节点），`tools/trace.gd` 对账，`tools/bots.gd` 机器人，`tools/report.gd` 批量报告 |
| `tools/check.py` | 一键检查：格式、重复、类型、内容（调 `check_data.py`，含事件预算）、文本、Godot 机器人试玩和护栏（`design/targets.json`）。`check_data.bat` 是它的双击版 |
| `tools/check_data.py` | 数据表的内容校验 |
| `tools/trace.py` `trace_cases.json` `compare_trace.py` `record_game.py` | Python 和 Godot 对账（`record_game.py` 录机器人整局、回放） |
| `original/` | 原版游戏的逆向资料和原版模拟器。做新游戏不用读 |

## 常用命令

```bash
python3 tools/check.py
```

```bash
python3 -m unittest discover -s tests/new -t .
```

```bash
python3 -m sim.report
```

```bash
python3 -m sim.story --seed 1 --origin 0,1,2 --plan class_acting,job_dock,rest_home
```

12b 之后批量试算在 Godot 里跑（`sim/` 冻结）：

```bash
godot --headless --path game/silentstar --script res://tools/report.gd -- --n=200 --bots=all
```

第三条是冻结的 Python 试算器（读 12b 时的表），只作历史参考。Godot 报告另有 `--coverage`（每个事件触发几次、从没触发的事件）、`--guard=design/targets.json`（逐条 PASS/FAIL）、`--random-options`；整份 200 局（23 组机器人）4 核分 4 个进程约 5 分钟，按 `--seeds` 分段跑再 `--merge`。`--n` 改局数，`--bots` 选机器人，`--no-buy` 不买装备。第四条用固定日程跑一局，每月一行状态。Godot 报告的参数和第三条一致（`--n` `--bots` `--no-buy`），另有 `--seeds=a-b`（分段跑）、`--dump` `--merge`（分段结果合并），见 `design/IMPL_NOTES.md` 的 Godot 一节。Godot 对账命令也在那一节。`python3 -m sim.month` 只跑日程，`python3 -m sim.audition` 重算 GDD 7.7 的胜率表。

## 用户定过的事（不要改）

- GDD 里标 [用] 的全部。
- 一局 1926-01 至 1929-12，每月 3 旬，逐日结算。
- 节奏目标：专练一路在第 16–21 个月练满；前两年钱紧；期末现金不过万；练满加普通上映能过 311；大卖不能是常态。
- 大事件按故事节奏排，不必符合史实。瓦伦去世在 1927-08。
- 金钱是当年的美元，没有小数。物价可以为了游戏需要偏离史实。
- 名字都是占位；人物细节等用户给，不要自己编。
- 开局声望不写死，由底值和开局三问算出（GDD 3.1）。
- 重病强制疗养院、拍摄违约保留（原版没有）。
- 对手组牌要防被克：副色取“克星的克星”（GDD 7.5）。
- GDD 7.7 的试算用“对手贴合角色”的局面。
- 打工“成功一期”= 这一旬至少有一天成功（照原版）。
- 数值合理就直接改，不用逐条问；改完记进 `design/BALANCE_LOG.md`。
- 第 8 步第一轮的决定（S 线 451、年度奖励减半等，见 BALANCE_LOG“用户已同意的决定”）。
- 两路都练的玩法走不通没关系，不用为它调数值。
- 删掉股票系统（1929-10 股灾只留剧情）。
- 休息只留两种：在家（Sil 陪着，便宜）、外出（一个人，选去处：度假村、城里等，遇到各种人和选项；代码上是同一套）。
- 四路等级照旧随声望自动变，不做手动升级。
- 用户自己直接改 JSON（不做 Excel），按 `data/USER_GUIDE.md`；改了表的写法要同步更新指南。
- 要做多语言。**技术性的东西一律英文**（字段名、id、枚举值、效果和条件、存档的键、代码和注释、开发者备注、检查脚本的输出、`data/new/README.md`、`design/IMPL_NOTES.md`、`data/USER_GUIDE.md`、`design/GLOSSARY.md`）；**中文原文只放在数据表的显示字段里**（`name`、`text`、`body`、`question`、`film_title`、`content`、`identity`），每条记录一个英文 `id`，加内容只写一处；`data/locale/text.csv` 由 `tools/extract_text.py` 从数据表生成。设计文档（GDD、DESIGN_NOTES、BALANCE_LOG、PLAN、README、CHANGE）和交接文本保持中文。
- 只把必须用户定的设计决策列出来问；占位内容、模型能自己检查的细节不要列给用户。

## 等用户定的事

只列必须用户拍板的设计决策。占位的名字、文本、事件内容不在这里，等用户给（清单在 `design/DESIGN_NOTES.md` 末尾），不用催。

- 目前没有。
