# 交接：第 12 步

分支：`claude/laughing-einstein-ka4wqz`（第 10、11 步已提交推送，第 12 步接着在这个分支上做，不要新开分支）。

## 先读
1. `PLAN.md` 第 12 步一行、`README.md`
2. `design/IMPL_NOTES.md`（英文；“Structure of `sim/`”“Rule details”“Random-number conventions”，末尾 Godot 一节和 Step 10 conventions）
3. 要移植的源码：`sim/board.py` `film.py` `events.py` `ending.py`，以及把它们接起来的 `sim/story.py`（`Story` 实现 `month.Hooks`，`Agent` 是玩家要回答的问题）、`sim/street.py`（街道、物品，`Story` 用到）

## 已完成的状态
- Godot 已有：`core/` 下 `rng` `jsonx` `data` `rules` `state` `locale` `schedule` `month` `audition`。`month.gd` 里 `Month.Hooks` 是空钩子，第 12 步用子类（对应 Python `Story`）实现它们。`audition.gd` 里 `play_match()` 对应 Python `match()`。
- 对账：`tools/trace.py` 与 `game/silentstar/tools/trace.gd` 逐字节一致（1805 行，含 48 个月固定日程 7 组和 1000 场试镜）。`trace_cases.json` 可继续加段。
- `data.gd` 已经把 step 6 用的表读进来（roles、rivals_named、events、opps、chains、schedule_npc 等），但 `rules.gd` 的 `extra_vars`（结局派生变量）还是空的，要在这一步按 `ending.py` 注册。
- Python 侧：`python3 tools/check.py`、`python3 -m unittest discover -s tests/new -t .` 通过。

## 要做（拆法同第 6 步，建议分两个提交）
**12-1 板、拍摄、上映、名气**：`board.gd`、`film.gd`（可含 `street.gd`）；`state.story` 已有结构。
**12-2 事件、逛街、NPC 日程、打工接口、年度大事、机遇、感情线、物品、结局**：`events.gd`、`ending.gd`、`story.gd`（Hooks 子类 + Agent 接口）。

## 对账（完成标准）
机器人的决策录成文件，在 Godot 里回放，整局每月状态和结局与 Python 一致。建议：
- Python 侧写 `tools/record_game.py`：用 `sim/bots.py` 的机器人跑一局，把每个问题的答案（`Agent` 的各方法，含日程、买东西、试镜的出牌）按顺序录成 JSON（带种子、开局三问）。
- Godot 侧写 `Agent` 的回放实现，按顺序读答案；两边各输出每月 `trace_line` 加结局，用 `tools/compare_trace.py` 比。多录几局：8 种机器人各一局，加犯罪线、逮捕、丑闻、债主、崩溃等路径要有覆盖（看 `g.hooks.log` 记录了哪些事件触发过，缺的路径换种子补）。
- 随机数顺序以 `sim/` 各文件开头的注释为准，一个数都不能错；集合的遍历顺序用表的顺序（见 IMPL_NOTES “No behaviour may depend on the alphabetical order”）。

## 注意
- 规矩：技术性的东西一律英文（代码、注释、标识符、字符串）；中文只在数据表显示字段；文档里设计文档中文、技术文档英文；不留兼容层；做法最规范、最干净。
- GDScript：`match` 是保留字；`and`/`or` 的短路和 Python 一致，但“总要掷骰”的地方先掷再 `or`（见 `schedule.gd` 的 `extra_fail`）；Python 的真值（`None` `""` `0` `[]`）用 `Schedule.truthy`；字典键都是字符串，整数键要转换；untyped 变量不能用 `:=` 推断，写 `var x: int = ...`。
- 容器里没有 Godot，下载：`curl -sSL -o g.zip https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_linux.x86_64.zip`，解压后 `--headless --path game/silentstar --script res://tools/trace.gd -- --out=work/trace_godot.txt`（`work/` 不进 git）。
- 做完：更新 `PLAN.md`（第 12 步标已完成）、`README.md`、`design/IMPL_NOTES.md` 的 Godot 一节，**删掉本文件**，提交并推送。
