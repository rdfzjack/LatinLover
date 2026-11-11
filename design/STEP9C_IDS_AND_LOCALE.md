# 第 9c 步：英文 id 和多语言（交接规格）

用户定：游戏要做多语言。原来数据表和代码直接用中文当名字（字段名、属性和技能名、物品 id、枚举值），显示文字和内部 id 是同一个东西，没法换语言，改一个显示名要全项目一起改。这一步把它们分开。

**模型：Opus。** 牵涉数据表、Python、测试、校验脚本、Godot 五处，而且要保证游戏结果一点不变。
**分两个对话做**：9c-1（id 和字段名改英文，Python 侧，**已完成**）；9c-2（语言文件、Godot 侧、用户指南）。每个对话做完提交。

## 规矩（用户定，全仓库适用）

- **技术性的东西一律英文**：JSON 字段名、id、枚举值、效果和条件里的名字、存档的键、代码里的标识符和字符串、代码注释和 docstring、开发者备注字段（`note`、`source`、`original`、`favor_sources` 等）、检查脚本的输出、`data/new/README.md`、`design/IMPL_NOTES.md`、`data/USER_GUIDE.md`、`design/GLOSSARY.md`。用户看得懂英文，不要为了“方便用户”留中文。
- **设计文档保持中文，不翻译**：GDD.md、DESIGN_NOTES.md、BALANCE_LOG.md、PLAN.md、README.md、CHANGE.md，以及交接文本（本文件）。GDD 开头有一句“id 对照见 GLOSSARY.md”。
- **中文原文只出现在数据表的显示字段里**，作为原文。所有表同一规矩：每条记录一个英文 `id`，显示字段直接写中文。用户加内容只写一处，不需要另外去改语言文件。
- **显示字段清单**（9c-2 在 `tools/extract_text.py` 里集中定义一份，其余字段都不是显示文字）。按现在的数据核对过：
  - 所有表的 `name`（含属性、技能、四条路、名气档、书档、隐藏值、课、书、工、去处、生活方式、街道入口和服务、物品、事件、外出事件、机遇、年度场合、NPC、对手、角色、结局大类和结局、习惯、**`roles.json` 的 `tags`**）。
  - `text`：事件、外出事件、开局三问选项的文字。
  - `body`：事件、外出事件、结局的正文（现在几乎都是 `null`，第 18 步写）。
  - `question`：开局三问的问题。
  - `film_title`：角色的片名。
  - 结局的 `content`（内容）。将来每个结局的评语用 `comment`（现在没有；`endings.json` 的 `scoring.comment_rule` 是开发者备注，不是显示字段）。
  - NPC 的 `identity`（身份）。
  - 没有 `name` 记录的东西 9c-2 要补：标签族（`tag_families` 的键）、状态和派生变量不需要显示名（内部用），标签族要不要显示名由 9c-2 判断。`dynamic_name`（结局名由最常打的工拼出来）现在存的是派生变量 id `top_job`，是技术性字段；这类结局的显示名怎么拼，9c-2 定。
- **id 命名**：英文 snake_case，一看就懂。效果和条件里用英文 id：`stamina+20`、`favor.sil+5`、`["stamina", ">=", 50]`、`flag.member=1`。对照表见 `design/GLOSSARY.md`（`tools/i18n_map.json` 生成）。不给旧的中文 id 留别名或兼容层；旧存档读不了（存档版本改成 2，读到别的版本报错）。
- **语言文件** `data/locale/text.csv`（Godot 翻译 CSV：`key,zh_CN,en`）由脚本从数据表自动生成：`zh_CN` 列每次重新生成，`en` 列保留人工填的翻译；中文原文变了的条目标成“翻译过期”。key 格式 `<类别>.<id>.<字段>`，如 `item.gold_watch.name`、`event.evt_deposit_2000.option.0.text`、`event.evt_deposit_2000.body`、`place.place_dock.name`、`attr.stamina.name`。
- 做事的准则：最规范、最干净、最省 token。

## 9c-1（已完成，Python 侧）

做了什么：
1. `tools/i18n_map.json`（中文 → 英文 id，按类别）、`design/GLOSSARY.md`（中文 | id | 类别，由 `python3 tools/migrate_ids.py --glossary` 生成）。
2. `tools/migrate_ids.py`：改写 `data/new/*.json` 和 `tools/trace_cases.json`（键、枚举值、效果字符串、条件里的变量和值；原来拿中文名当 id 的记录拆成 `id` + `name`；开发者备注翻成英文）。脚本留在仓库里做记录，跑过一次后不能重跑。
3. 改了 `sim/`、`tests/new/`、`tools/check_data.py`、`tools/check.py`、`tools/trace.py`、`tools/compare_trace.py`；批量替换的脚本不进仓库（一次性的），要查改了什么看 `git diff` 和 `tools/migrate_ids.py`。`检查数据.bat` 改名 `check_data.bat`。
4. 排序：`sim/` 里不再有靠名字字母序的地方。会影响并列取舍的顺序都按数据表原始顺序：`Data.item_order`（`items.json` 的行序）、`Data.npc_order`、`Data.roads` / `Data.skills`、`order` 字段。**`items.json` 的行序是改名前代码按中文 id 排出来的顺序，故意保留，这样报告数字不变**；`sil_hint` 的并列改按感情线顺序（只给界面用）。对手 `easter_egg: true` 取代了“说明以某个词开头”的判断。
5. 存档版本 2。
6. `roles.json` 新增 `tags`（16 个标签的 id 和中文名），因为标签原来只是列表里的名字，没有 `name`。

验证：`python3 tools/check.py`、单元测试通过；`python3 -m sim.report`（200 局）每个数字和改之前一致（只有标签文字变成英文，`>1万` 变成 `>10k`）；trace 输出（`python3 tools/trace.py`）每行的数字集合和改之前一致（JSON 键改名后 `sort_keys` 的顺序变了，Godot 侧一起改后再逐字节对）。

遗留（交给 9c-2）：
- `tools/` 里还有中文的只有两处，故意的：`tools/i18n_map.json`（对照表本身）和 `tools/check_data.py` / `tools/check.py` 里用来检测全角标点的那几个字符。
- `data/USER_GUIDE.md` 还是旧写法（中文字段名），9c-2 按新语法用英文重写；开头已加了“已过期”提示。
- `game/silentstar/core/` 和 `tools/trace.gd` 还用中文名，数据现在是英文 id，Godot 侧暂时跑不起来。

## 9c-2（已完成，Godot 对账待跑）

做了什么：`tools/extract_text.py` 和 `data/locale/text.csv`、`en_basis.json`（接进 `tools/check.py` 第 4 步，测试 `tests/new/test_locale.py`）；`game/silentstar/core/` 和 `tools/trace.gd` 按 `sim/` 移植成英文 id，新增 `core/locale.gd`；`data/USER_GUIDE.md` 英文重写，里面每个例子都照抄进表跑过检查。定下的事：标签族不加显示名；`dynamic_name` 的两个结局，`name` 写成 `以{top_job}为业` 这样带占位符，运行时替换成那个工的译名。**没做到的**：本环境装不了 Godot，Godot 对账和 `locale.gd` 没执行过，Python 侧（检查、测试、200 局报告、trace 输出）与改之前一致。

下面是当时的规格：

1. `tools/extract_text.py`：集中定义显示字段清单，生成 `data/locale/text.csv`（`key,zh_CN,en`；`zh_CN` 每次重生成，`en` 保留；中文变了的标“翻译过期”），并接进 `tools/check.py`：缺中文、多余 key、翻译过期都要报；同一个 key 不重复。
2. 移植 `game/silentstar/core/`（data、rules、state 里的中文字面量改英文 id，数据结构跟 `sim/` 一致，存档版本 2）和 `tools/trace.gd`（Godot 4.3），读 `trace_cases.json` 的新键名；对账仍要和 Python 逐字节一致（命令见 `design/IMPL_NOTES.md` 末尾）。加一个读 `text.csv` 并注册到 `TranslationServer` 的小脚本（运行时读，不依赖编辑器导入）。缺翻译时显示 key 本身并在检查里报出来。
3. 用英文按新语法重写 `data/USER_GUIDE.md`：效果写 `stamina+20`，条件写 `["stamina", ">=", 50]`；开头放常用的中英 id 对照（属性、技能、四条路、NPC、去处、标签），完整的指向 `design/GLOSSARY.md`；改显示名直接改表里的 `name`，翻译去 `data/locale/text.csv` 的 `en` 列。
4. 完成标准：数据表、`sim/`、`game/silentstar/core/` 里没有中文 id 和中文显示文字（显示字段除外）；`tools/check.py`、测试、200 局报告（和 9c-1 之后相同）、Godot 对账都通过；用户按新指南加一件物品（含中文名）能通过检查。

## 以后的规矩（已写进 README 的“用户定过的事”）

- 代码和数据结构只用英文 id；玩家看得到的文字只放在数据表的显示字段（`data/locale/` 由它生成）。
- 新加内容时同时写中文显示字段；`en` 可以空，检查会列出缺多少。
