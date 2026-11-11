# 交接：第 9c-2 步

分支：`claude/nice-cori-t66vua`（9c-1 已提交推送，9c-2 接着在这个分支上做，不要新开分支）。

## 先读
1. `design/STEP9C_IDS_AND_LOCALE.md`（规矩和 9c-2 的范围、完成标准）
2. `design/IMPL_NOTES.md`（英文；开头“Identifiers and ordering”，末尾 Godot 对账命令）
3. `data/new/README.md`、`design/GLOSSARY.md`

## 9c-1 留下的状态
- `python3 tools/check.py` 和 `python3 -m unittest discover -s tests/new -t .` 通过；`python3 -m sim.report` 的基线在 `work/report_before.txt`（`work/` 不进 git，新环境里没有；开工先在 9c-1 提交上重跑一份存到 `work/`，做完对比）。
- 数据和 `sim/` 全英文；中文只在显示字段（`name` `text` `body` `question` `film_title` `content` `identity`）。`roles.json` 新增 `tags`（id + 中文名）。
- 存档版本 2。`items.json` 行序有意义（见 IMPL_NOTES），不要重排。
- `tools/i18n_map.json` 是对照表，`tools/migrate_ids.py` 只是记录，不能重跑。

## 9c-2 要做
1. `tools/extract_text.py`：集中定义显示字段清单（以实际数据核对；`dynamic_name` 是技术字段 `top_job`，标签族没有显示名，由你判断要不要补一个 `name`）；生成 `data/locale/text.csv`（`key,zh_CN,en`，key 格式 `<类别>.<id>.<字段>`，`zh_CN` 每次重生成，`en` 保留，中文变了标“翻译过期”）；接进 `tools/check.py`：缺中文、多余 key、重复 key、翻译过期都要报。
2. 移植 `game/silentstar/core/`（`data.gd` `rules.gd` `state.gd` 等）和 `game/silentstar/tools/trace.gd` 到新的英文 id 和新数据结构（字段名对照 `design/GLOSSARY.md`，逻辑对照 `sim/` 现在的写法；前缀拆分用 `split_name`，不要按长度切）；Godot 运行时读 `text.csv` 注册到 `TranslationServer`（不依赖编辑器导入），缺翻译显示 key。Godot 4.3。
3. 对账：Python `tools/trace.py` 与 Godot 输出逐字节一致（命令见 IMPL_NOTES 末尾）。注意 `sort_keys` 的顺序因键改名变了，Python 和 Godot 都按码位排。
4. 用英文按新语法重写 `data/USER_GUIDE.md`（效果 `stamina+20`，条件 `["stamina", ">=", 50]`；开头放常用中英 id 对照；改显示名直接改 `name`，翻译去 `text.csv` 的 `en` 列；每个例子照抄进表都要能通过检查）。
5. 更新 PLAN/README 的进度，设计文档保持中文，技术文档英文。

## 规矩（用户定）
技术性的东西一律英文（代码、注释、检查输出、GDScript 里的标识符和字符串）；中文只在数据表显示字段；设计文档和交接文本中文；不留旧中文 id 的别名或兼容层；做法最规范、最干净、最省 token。完成标准：检查、测试、200 局报告数字不变、Godot 对账、用户按新指南加一件含中文名的物品能通过检查。做完提交并推送。
