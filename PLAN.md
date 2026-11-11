# 实施计划：从 GDD 到 Godot

设计以 `design/GDD.md` 为准，推定的理由在 `design/DESIGN_NOTES.md`，目前做到哪一步见 `README.md`。一局是 1926-01 至 1929-12（48 个月、144 旬、16 块选片板、4 次年度大事）。原版的逆向资料都在 `original/`，只有第 1 步用过。实现细节（随机数顺序、GDD 没写到的做法）在 `design/IMPL_NOTES.md`，第 9–12 步移植时照它。

## 怎么用这份计划

- 每次新开一个对话，只说“做 PLAN.md 第 N 步”。每一步都写了要读什么、产出什么、怎样算完成。
- 一步一个对话，做完提交。不要在同一个对话里连做几步。
- 模型一栏：**Fable** 只做判断（看结果、定数值、审设计）；**Opus** 写有难度的逻辑；**Sonnet** 填表、移植、写界面、批量写文本。
- 难度：小（一个对话内很快做完）、中（一个对话）、大（可能要拆成两个对话，步骤里写了拆法）。

## 两条线的分工

| | Python 试算器（`sim/`） | Godot（`game/`） |
|---|---|---|
| 给谁用 | 模型测数值 | 你自己玩，感受手感 |
| 测什么 | 成长曲线、收支、试镜胜率、结局分布 | 操作顺不顺、节奏、界面 |
| 怎么跑 | 命令行，一次跑几百局，输出几十行报告 | 手动玩；另有无界面模式只用于和 Python 对账 |

- `original/pm2sim/` 是**原版**模拟器，测不了新规则。新游戏用 `sim/`，只读 `data/new` 的 JSON 表。
- 规则和数值都放在 `data/new/*.json`，两边读同一份。改数值只改 JSON，两边都不用改代码。
- 代价：逻辑要写两遍（Python 一遍，Godot 一遍）。用同一种子对账（第 9、11、13 步）来保证两边一致。规则变了要两边都改，所以规则尽量写成数据。

## 进度

第 1–12 步和 8b、9b 已完成（详见 `README.md`）。第 9 步的对账在 Godot 4.3 里跑过，和 Python 逐字节一致。

9c-1（英文 id 和字段名，Python 侧）和 9c-2（语言文件、Godot 侧、用户指南）已完成，Godot 对账已通过。第 10 步（日程和月结）已完成，对账一致。第 11 步（试镜）已完成，1000 场逐轮一致。第 12 步（选片板、拍摄、上映、事件、结局）已完成，38 局机器人录像在 Godot 里回放，每月状态和结局一致。下一步第 13 步。9c 的规格在 `design/STEP9C_IDS_AND_LOCALE.md`。9c 要在 10 之前做：越往后移植到 Godot 的代码越多，改名越贵。第 8 步可以重复做：读 `design/BALANCE_LOG.md` 的“没解决的”，改完重跑报告。

用户的修改意见记在 `design/CHANGE.md`，每条后面写了在哪一步处理。

用户要到第 13、14 步有界面以后才能自己试玩。最短的路是 9c → 10 → 11 → 13 → 14（只有日程和试镜的可玩版本），第 12、15 步之后补。

## 步骤

### A. 准备

| 步 | 做什么 | 读 | 产出 | 完成标准 | 难度 | 模型 |
|---|---|---|---|---|---|---|
| 1 | 核对原版生病、重病状态的实际效果，更新 GDD 5.1、10 和 N18。只改这两处的规则和来源标记，不动别的小节 | `original/INDEX.md`，用 `original/tools/logic_view.py` 看 `MAINBORN`、`RUNNING` 的相关标签；GDD 5.1、5.8（医院、餐厅在生病时的规则已核对过）、10 | 改 GDD 两处 | GDD 里这两条的来源从 [推] 改成 [原] 或写明差异 | 小 | Sonnet |
| 2 | 建核心数据表：属性、技能、等级、课程、书、打工（含解锁和接口字段）、休息和地点、街道、生活方式、开局三问、日历 | GDD 第 2、3、5 节 | `data/new/stats.json` `skills.json` `classes.json` `books.json` `jobs.json` `rest.json` `places.json` `street.json` `origins.json`；`tools/check_data.py` | 校验脚本通过：字段齐全、引用的属性、技能、NPC、物品名都存在；金钱都是整数 | 中 | Sonnet |
| 3 | 建其余数据表：角色（GDD 示例 8 个加教学角色）、对手（有名对手按 1926–1929 逐年；无名对手按半年数 `h`）、习惯、事件（含 11.3 的 7 个时代节点）、逛街事件、NPC 日程和链事件、年度、机遇、感情线和功能 NPC、物品、结局 | GDD 第 5.5、6–15 节 | `data/new/roles.json` `rivals.json` `habits.json` `events.json` `outing.json` `npc_schedule.json` `npc_chains.json` `annual.json` `opportunities.json` `romance.json` `items.json` `endings.json` | 校验脚本通过；条件和效果都用 GDD 16 节的格式 | 中 | Sonnet |

### B. Python 试算器

| 步 | 做什么 | 读 | 产出 | 完成标准 | 难度 | 模型 |
|---|---|---|---|---|---|---|
| 4 | 核心循环：随机数（PCG32 两个流）、日历、状态、条件和效果解释器（含旗标、判定）、上课、看书、打工（解锁、加薪，不含接口事件）、休息、街道、生活方式、月结指数 | GDD 第 2、4、5、10、16 节；第 2 步的表 | `sim/rng.py` `state.py` `rules.py` `schedule.py` `month.py`，`tests/new/` | 单元测试通过；给定种子和固定日程，48 个月（1926-01 至 1929-12）的状态可重复 | 中 | Opus |
| 5 | 试镜：组牌、有效点数、习惯、结果分档、对手组牌 | GDD 第 7、9 节 | `sim/audition.py`，测试 | 测试复现 GDD 7.7 的胜率表（误差 ±3 个百分点） | 中 | Opus |
| 6 | 选片板、拍摄、上映、名气、标签、事件、逛街和 NPC 日程、打工接口、剧本、年度大事、机遇、感情线、物品、结局 | GDD 第 5.4 接口表、5.5、6、8、10.1、11–15 节 | `sim/board.py` `film.py` `events.py` `ending.py` | 能从开局跑到结局不报错；每个结局条件有一条测试。**拆法**：先做板、拍摄、上映、名气；再做事件、逛街、接口和结局 | 大 | Opus |
| 7 | 策略机器人和报告 | `sim/` 的接口 | `sim/bots.py`（专练一路 ×4、两路、乱选、犯罪线、只读书的文化线）；`sim/report.py` | 一条命令跑 200 局 × 每种机器人，输出不超过 60 行：各路声望的月度分位数和练满月份、每年末金钱和负债月数、试镜场数和胜率、大片通过率、大卖率、主演部数、名气档分布、结局分布；差得多的项写进 `design/BALANCE_LOG.md` | 中 | Sonnet |
| 8 | 平衡轮（可重复多次） | `design/BALANCE_LOG.md` 和第 7 步的报告 | 改 `data/new/*.json`；在 `design/BALANCE_LOG.md` 记一行：改了什么、为什么、前后对比 | 报告满足：专练一路在第 16–21 月练满（中位数），四条路之间相差不超过 6 个月；前两年每年末金钱中位数不过千；“练满加普通上映”中位数落在 311–340，九成的局过 311；大卖率一成上下；期末金钱中位数和 90% 分位都不过万；大片通过率 10%–35%；每种机器人至少走到 3 个不同结局 | 小（每轮） | Fable |
| 8b | 用户改的休息规则（`design/CHANGE.md` 第 1 条）：休息只留在家（Sil 陪着）和外出（选去处，度假村也是去处）（**已完成**） | `design/CHANGE.md`；GDD 5.5；`rest.json` `places.json` `outing.json`；`sim/schedule.py` `bots.py` | 改 GDD、表、`sim/`、测试；重跑报告，变化记进 `BALANCE_LOG.md` | 测试通过；报告各项仍在第 8 步的目标内 | 中 | Opus |

### C. Godot 逻辑（无界面）

Godot 4.3，GDScript。工程在 `game/silentstar/`。逻辑和界面分开：`game/silentstar/core/` 不依赖任何节点。移植约定见 `design/IMPL_NOTES.md` 的 Godot 一节。

| 步 | 做什么 | 读 | 产出 | 完成标准 | 难度 | 模型 |
|---|---|---|---|---|---|---|
| 9 | 工程骨架：数据加载、随机数、状态、条件和效果解释器、存读档（**已完成，对账一致**） | `sim/rng.py` `state.py` `rules.py`；GDD 16 节；`design/IMPL_NOTES.md` | `game/silentstar/core/` 对应脚本；`game/silentstar/tools/trace.gd`；`tools/trace.py` `trace_cases.json` `compare_trace.py` | 无界面运行，输出随机数序列和存档往返，与 Python 逐字节一致 | 中 | Opus |
| 9b | 让用户自己改数据（`design/CHANGE.md` 第 3 条）。用户选了直接改 JSON，不做 Excel（**已完成**） | `data/new/README.md`；`tools/check_data.py` | `data/USER_GUIDE.md`（中文指南）；`tools/check.py` 一键检查（格式、重复、类型、内容、机器人试玩，报错用大白话）；`check_data.bat` | 指南里每个例子照抄进表都能通过检查、试玩时会触发 | 中 | Opus |
| 9c | 英文 id 和多语言：数据结构和代码只用英文 id，玩家看得到的文字搬到 `data/locale/text.csv`（用户定：要做多语言）。**规格见 `design/STEP9C_IDS_AND_LOCALE.md`** | `design/STEP9C_IDS_AND_LOCALE.md`；`data/new/README.md`；`design/IMPL_NOTES.md` | `design/GLOSSARY.md`、`tools/i18n_map.json`、`tools/migrate_ids.py`；改好的表、`sim/`、测试、检查脚本、`game/silentstar/core/`；`data/locale/text.csv`；新版 `data/USER_GUIDE.md` | 见规格：报告数字和改之前完全相同；测试、检查、Godot 对账通过；代码和数据里没有中文 id。**拆法**：9c-1 改 id 和字段名（Python 侧，**已完成**）；9c-2 抽语言文件、Godot、用户指南（**已完成**） | 大 | Opus |
| 10 | 移植日程和月结（**已完成，对账一致**） | `sim/schedule.py` `month.py` | `game/silentstar/core/schedule.gd` `month.gd` | 同种子、同日程，每月状态与 Python 一致（对账脚本 `tools/compare_trace.py`） | 中 | Sonnet |
| 11 | 移植试镜（**已完成，对账一致**） | `sim/audition.py` | `game/silentstar/core/audition.gd` | 同种子 1000 场试镜逐轮一致 | 小 | Sonnet |
| 12 | 移植选片板、拍摄、上映、事件、结局（**已完成，对账一致**） | `sim/board.py` `film.py` `events.py` `ending.py` | `game/silentstar/core/` 对应脚本 | 机器人的决策录成文件后在 Godot 里回放，整局每月状态和结局与 Python 一致。**拆法同第 6 步** | 大 | Opus |

### D. Godot 界面（无美术，占位）

| 步 | 做什么 | 读 | 产出 | 完成标准 | 难度 | 模型 |
|---|---|---|---|---|---|---|
| 13 | 主界面：状态栏（名气显示档位和来信）、月历、排三旬日程（含选书、选外出的去处）、街道和谈话、逐日播放、月结小结；导出时把 `data/new/` 打进包 | GDD 2.5、4、5 节；`game/silentstar/core/` 接口 | `game/silentstar/ui/main.tscn` 等 | 能从开局排日程玩到 1929-12；排一个月不超过 4 次点击 | 中 | Sonnet |
| 14 | 选片板和试镜界面：角色卡、组牌、亮牌、逐轮出牌、结果 | GDD 第 6、7 节 | `game/silentstar/ui/board.tscn` `audition.tscn` | 一场试镜 1 分钟内打完；对手习惯、场风、克制关系在界面上一眼能看懂 | 中 | Opus |
| 15 | 事件对话框、逛街事件和日程本、物品和装备、年度大事、存读档、结局页 | GDD 第 11–15 节 | `game/silentstar/ui/` 对应场景 | 所有 `events.json` 里的事件能弹出并生效；能存读档 | 中 | Sonnet |

### E. 内容和试玩

| 步 | 做什么 | 读 | 产出 | 完成标准 | 难度 | 模型 |
|---|---|---|---|---|---|---|
| 16 | 大片角色 20 个（16 个每板一个，4 个备用）：场风概率、看重属性、标签、对手、哪些带有声 | GDD 第 6、9 节；你给的设定 | `roles.json` 的大片部分 | 校验通过；跑第 7 步报告，大片通过率仍在目标范围 | 中 | Opus |
| 17 | 中小片角色 40 个（中 20、小 20）、逛街事件 32 个、NPC 链事件、打工接口事件、书目、物品 | GDD 5.3.2、5.4、5.5、6.3、11.4、14 | 对应 JSON | 校验通过；16 个标签每个至少有 3 个角色 | 中 | Sonnet |
| 18 | 事件（含 7 个时代节点）、结局、杂志和来信的文本 | GDD 第 11、15 节；你给的设定和文风样例 | `data/new/text/*.json` | 每个事件和结局都有文本；你抽查通过 | 大（量大，按事件、结局、杂志分三个对话） | Sonnet |
| 19 | 试玩反馈轮（可重复） | 你的试玩笔记；第 7 步的报告 | 改 JSON 或开新任务 | 你列的问题逐条有处理 | 小（每轮） | Fable |

依赖关系：1→2→3→4→5→6→7→8→8b；9 可在 4 之后开始；9c 依赖 9b；10、11、12 都依赖 9c（以及 8b、5、6）；13–15 依赖对应的逻辑步；16–18 可在 3 之后任何时候做。
