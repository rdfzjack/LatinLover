# 规则索引：想查某个机制，看哪里

给 AI 的三步查法（省 token）：
1. 先看 `SUMMARY.md`（要点）和 `data/tables/*.json`（已整理的数值）。够用就停。
2. 不够再按下表找到脚本和标签，只看规则行：
   `python3 tools/logic_view.py data/scripts/TXRT/MAINEVNT.TXT EVENT009`（文件后跟标签名，可多个）。
3. 只有涉及原生命令（`CLENDER`、`RANDAM`、`ITEM_*` 等）才看 `pm2sim/*.py`，里面有 Python 实现和 EXE 地址。
不要通读 `data/scripts/`（约 8.4 万行）。所有脚本的标签清单在 `data/tables/script_index.json`。

## 读脚本须知
- 变量名是日文罗马字，中文对照在 `data/tables/variables.json`（如 `B_TAIRYOKU` 体力、`B_STRESS` 疲劳、`URA_FATHER` 父女关系）。
- `*名字` 是标签；单独写名字是调用；`IF (a b)(c)` 表示 (a 且 b) 或 c；缩进是代码块；`LOOP v` 循环 v 次。
- `X = a + b * c` 从左到右算，没有优先级。`RANDAM(n)` 得 1..n，结果在 `IRND` 和 `AX`。
- `E_ETC[n]`、`RUN_MONTH[n]` 是杂项旗标／计数器，含义要看上下文。

## 系统 → 文件
| 系统 | 文件（`data/scripts/` 下） | 关键标签 |
|---|---|---|
| 开局、星座初值、身材初值 | `TXRT/PARAINIT` | 顶层代码；`zodiac.json` |
| 主菜单、排日程、伙食费、零用钱 | `TXRT/MAINLOOP` | `SCHED_MAIN` `SCHED_KITAERU` `SCHED_HATARAKU` `SCHED_YASUMI` `CALC_SYOKUHI` `TALKGIRL` |
| 逐旬执行日程、日程中事件 | `TXRT/RUNNING` | `EVENT021` `EVENT022` `EVENT025` `EVENT026` `BORTHCHECKX` |
| 月末事件判定 | `TXRT/MAINEVNT` | `EVENT003`~`EVENT052`（每个事件的触发条件） |
| 月结：成长、状态变化、死亡、年俸、对手成长 | `TXRT/MAINBORN` | `MONTH_BORNUP` `CHK_SCNDEATH` `STOP_THE_DIET` `GET_HOKYU` `BRONING` |
| 上课 10 门 | `TXTR/TRG000`~`009` | `R_*` 主流程、`SUCCESS_CHK`；`classes.json` |
| 打工 15 种 | `TXJO/JOB000`~`014` | `R_*`、`CHK_HIKOUKA`、`CHK_RENAI`；`jobs.json` |
| 休息、疗养、监视 | `TXRT/SCNKYUSO` | `R_FREE` `R_OBSERVE` `R_RESTCURE` `R_SANATORIUM` |
| 度假 | `TXRT/SCNVACAN` | |
| 饮食方针 | `TXRT/SCNKENKO` | |
| 和女儿谈话、说教、零用钱 | `TXRT/SCNGIRL` | |
| 街道：武器店、服装店、杂货、教堂、医院等 | `TXRT/KAIMONO`、餐馆 `TXRT/KRYORIYA` | `items.json` |
| 王城拜访（人脉、王子等） | `TXRT/SCNCASTL` | |
| 守护神、存读档 | `TXRT/SCNSYUGO` | |
| 生病致死 | `TXRT/SCNDEATH` | |
| 收获祭：武斗／舞会 | `TXS/SSRUNS` `SSTOUR` `SSBATL` `SSDANC` | 对手 `SSBT02`~`18` |
| 收获祭：艺术／烹饪 | `TXS2/SSARTS` `SSCOOK` | |
| 武者修行：流程、扎营、战斗、遇人 | `TXRP/RPGRUN` `RPGLOP` `RPGCMP` `RPGMNS` `RPGMEN` | 四张图 `RPG000`~`003`；怪物 `RPZ*`；路人 `RPY*`；`monsters.json` |
| 结局判定 | `TXEE/EECALC` | `CALC_SET` `WORKING_*` `CALC_SPECIAL_WEDD` `CALC_WEDDING` `WORKS_HYOKA`；`endings.json` |
| 结局演出 | `TXEE/EEWK01`~`74` 职业、`EEWE01`~`05` 婚姻、`EETN*` 评语 | |

## 事件文件（`TXEV/`，名称按脚本首句推断，条件以脚本为准）
003 酷暑 · 004 寒流 · 005/006/007/008/010/011/013/020 访客类（条件见 `MAINEVNT` 同号标签）· 015 师傅认可 ·
016 烹饪赛冠军后续 · 017 物品放置一个月 · 021/025 路上被搭讪 · 022 踢馆（战斗在 `TXS/SSEV022`）·
023 道场被踢（`TXS/SSEV023`）· 026 对手登场 · 028 泉水精灵 · 029/033 恶魔 · 030 独角兽 · 031 精灵神木 ·
032/034 龙 · 035 山中小屋 · 036 人鱼（度假）· 039 成绩 · 041 恩赐之剑 · 042 女儿生日 · 043 父亲生日 ·
044 新年 · 045/046 被捕 · 047/048/049 修行奇遇 · 051 墓园 · 052 官员来访 · BSIN/BSN2/BSN3 战神。
028~035、047~049 只在武者修行中出现。

## 原生命令 → Python
| 命令 | 位置 |
|---|---|
| `RANDAM` `IRAND2` `IRAND999X` `IRNDPAR`、`GOLD*`、`CK_LVL`（课程等级）、`CK_GUARA`（薪资等级）、`P1X100` `MOD` | `pm2sim/engine.py` |
| `CLENDER(n)`：3 过一天、7 月成长、8/9/13 同步评价与技能、11 月属性 | `pm2sim/calendar.py` |
| `ITEM_INST` `ITEM_KILL` `ITEM_SRCH`、物品效果语言 | `pm2sim/items.py` |
| 存档格式 | `pm2sim/save.py` |
