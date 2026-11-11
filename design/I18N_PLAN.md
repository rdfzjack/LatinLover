# 第 9c 步：英文 id 和多语言（交接规格）

用户定：游戏要做多语言。现在数据表和代码直接用中文当名字（字段名、属性和技能名、物品 id、枚举值），显示文字和内部 id 是同一个东西，没法换语言，改一个显示名要全项目一起改。这一步把它们分开。

**模型：Opus。** 牵涉数据表、Python、测试、校验脚本、Godot 五处，而且要保证游戏结果一点不变，不适合 Sonnet。
**分两个对话做**：9c-1（id 和字段名改英文，Python 侧）；9c-2（显示文字抽到语言文件、Godot 侧、文档）。每个对话做完提交。

## 目标

1. **代码和数据结构里不出现中文。** JSON 的字段名、所有会被引用的名字（id、枚举值、效果和条件里的变量名）一律用英文小写加下划线。Python 和 GDScript 的字符串字面量不再有中文 id。
2. **玩家看得到的文字全部在语言文件里**，按 key 查。先有 `zh_CN`，留好 `en` 列。
3. **游戏结果完全不变。** 同一种子，改之前和改之后的机器人报告逐字一致（只有显示用的标签可以变）。
4. 注释、设计文档（GDD、DESIGN_NOTES 等）、给开发者的备注字段可以继续用中文。

## 要改的东西（先用脚本列全，别靠眼睛找）

写一个脚本扫 `data/new/*.json` 和 `sim/*.py`，列出所有中文的：

| 类 | 例子 | 改成 |
|---|---|---|
| JSON 字段名（约 380 个） | `"名字"` `"价格"` `"效果"` `"条件"` `"成功线"` | `"name"` `"price"` `"effect"` `"cond"` `"success_line"` |
| 属性、技能、四条路 | `体力` `打斗` `硬汉` | `stamina` `fight` `tough` |
| 物品 id（现在 id = 名字） | `定制西装` | `suit_custom` |
| NPC、去处名、标签 | `Sil` `女明星` `浪漫` | `sil` `actress` `romance` |
| 枚举值 | 类 `服装/配饰/持有`，档次 `小/中/大`，旬 `上/中/下`，频次 `每局一次`，时机 `月末`，触发 `外出` | `outfit/accessory/held`，`small/medium/big`，`1/2/3`（或 `early/mid/late`），`once_per_game`，`month_end`，`outing` |
| 效果和条件里的前缀 | `好感.` `旗标.` `状态.` `计数.` `修正.` `权重.` `物品.` `触发.` `成功期数.` `旬数.` `期数.` `标签.` | `favor.` `flag.` `status.` `count.` `rep_bonus.` `weight.` `item.` `trigger.` `job_periods.` `class_periods.` `road_periods.` `tag.` |
| 派生变量 | `最高声望` `日期` `月份` `生病指数` | `max_rep` `date` `month` `sick_index` |
| 旗标名、计数器名（数据里自由起的） | `旗标.会员` `计数.亲自上` | `flag.member` `count.stunt_self` |
| 存档的键 | `attr` 下的 `体力`、`story` 下的 `板` `片` | 跟着改；存档 `版本` 改成 2 |

**对照表**写进 `design/GLOSSARY.md`（中文 | 英文 id | 类别），以后所有人按它对照。英文名直接定，不用问用户；要求是一看就懂、不缩写成谜语。

## 9c-1：id 和字段名改英文（Python 侧）

1. 生成对照表（上面那张），存成 `tools/i18n_map.json` 和 `design/GLOSSARY.md`。
2. 写一次性脚本 `tools/migrate_ids.py`：按对照表改写 `data/new/*.json` 的键、枚举值、效果字符串、条件里的变量名和值。脚本留在仓库里，方便查改了什么。
3. 改 `sim/*.py`、`tests/new/*.py`、`tools/check_data.py`、`tools/check.py`、`tools/trace.py`、`tools/trace_cases.json` 里的字符串字面量。这一步手改加脚本替换都行，改完 `grep -P '[\x{4e00}-\x{9fff}]'` 只应剩注释、docstring 和给人看的 print。
4. **当心排序。** `sim/` 里有 16 处 `sorted(` / `.sort(`，按名字排的顺序在中文和英文下不一样。凡是排序结果会影响随机数消耗顺序、并列时取哪个、遍历顺序的地方，改成按数据表里的原始顺序（或显式的 `order` 字段），不要依赖名字的字母序。`State._held`、`known`、`highest_base`、各种 `max(..., key=...)` 都要看。
5. 完成标准：
   - `python3 tools/check.py` 通过；`python3 -m unittest discover -s tests/new -t .` 通过。
   - `python3 -m sim.report`（200 局）的数字和改之前**完全相同**。先在改之前跑一份存到 `work/`，改完 diff。不同就是排序或漏改，找到原因再继续。
   - 显示名暂时还在数据里（`name` 字段），9c-2 再搬走。

## 9c-2：显示文字抽到语言文件，Godot 侧，文档

1. **语言文件**：`data/locale/text.csv`，列 `key,zh_CN,en`（Godot 原生的翻译 CSV 格式，Excel 也能直接打开改）。`en` 先空着。
   - key 规则：`<类别>.<id>.<字段>`，例如 `item.suit_custom.name`、`attr.stamina.name`、`event.evt_deposit_2000.option.0.text`、`event.evt_deposit_2000.body`、`place.place_dock.name`。
   - 搬进去的：所有玩家看得到的 `name`、选项文字、事件和结局的正文（现在的 `文本` 字段，大多还是 null）、问题文字、片名。
   - 不搬的：`note`（原来的 `说明`、`来源`、`原版对应` 这类给开发者看的备注），可以留中文在 JSON 里。
   - 数据表里删掉这些显示字段，代码和界面一律按 key 查。缺翻译时显示 key 本身，并在检查里报出来。
2. **检查**：`tools/check.py` 加一项：每个 id 都有 `zh_CN` 的名字；语言文件里没有对不上 id 的多余 key；同一个 key 不重复。
3. **Godot**：`game/silentstar/core/` 跟着改（data、rules、state 里的中文字面量），加一个读 `text.csv` 并注册到 `TranslationServer` 的小脚本（运行时读，不依赖编辑器导入）。`tools/trace.gd` 和 Python 的 trace 一起更新，对账仍要逐字节一致。
4. **文档**：
   - `data/USER_GUIDE.md` 重写例子：效果写 `stamina+20`，条件写 `["stamina", ">=", 50]`；开头放一张常用中英对照（属性、技能、四条路、NPC、去处、标签），完整的指向 `design/GLOSSARY.md`；改显示名、加翻译去 `data/locale/text.csv`。
   - `data/new/README.md`、`design/IMPL_NOTES.md` 同步。GDD 正文保留中文，开头加一句“文中名字对应的 id 见 GLOSSARY”。
5. 完成标准：
   - 数据表、`sim/`、`game/silentstar/core/` 里没有中文 id 和中文显示文字（注释除外）。
   - `tools/check.py`、测试、200 局报告（和 9c-1 之后相同）、Godot 对账都通过。
   - 用户按新指南加一件物品（含中文名）能通过检查。

## 以后的规矩（写进 README 的“用户定过的事”）

- 代码和数据结构只用英文 id；玩家看得到的文字只放在 `data/locale/`。
- 新加内容时同时加 `zh_CN` 文本；`en` 可以空，检查会列出缺多少。
