# 实机验证交接说明

目标：在真实游戏里采集"存档＋日程 → 结果"用例，放进 `tests/cases/`，让 `python3 tests/run_cases.py` 全部 PASS。
模拟器目前**没有任何实机用例**；只通过了不依赖实机的自测（`python3 tests/test_sim.py`）。

## 1. 仓库里有什么
| 路径 | 用途 |
|---|---|
| `pm2sim/` | 模拟器：`vm.py` 脚本虚拟机，`engine.py`/`calendar.py`/`items.py` 原生命令，`save.py` 存档，`game.py` 上层接口 |
| `data/scripts/` | 解密后的全部游戏脚本（UTF-8，只读参考）；`data/tables/*.json` 数据表 |
| `tools/dbx.py` | 驱动 DOSBox：启动、按键、点击、截图、读写游戏内存 |
| `tools/disasm_exe.py` `tools/asmview.py` `tools/logic_view.py` | 反汇编 EXE、看指定地址、看脚本的规则行 |
| `tests/test_sim.py` `tests/run_cases.py` | 自测；实机用例对比器 |
| `SUMMARY.md` | 机制摘要 |

## 2. 环境
```bash
apt-get update && apt-get install -y dosbox xdotool xvfb imagemagick
```
```bash
python3 tools/dbx.py start
```
`start` 会把游戏复制到 `work/run/PM2` 再启动（cycles 固定 3000，不要改成 max）。之后可用：
```bash
python3 tools/dbx.py shot work/s.png
```
```bash
python3 tools/dbx.py click 400 300
```
```bash
python3 tools/dbx.py key Return
```
游戏用鼠标操作：左键确认，右键取消。菜单坐标没有记录，需要你看截图自己定位。存档文件是 `work/run/PM2/F1xx.GNX`。

## 3. 必须先固定随机数
游戏每抽 200 次随机数就用定时器重新取偏移，不固定就无法复现。进游戏后（任何画面都行）执行一次：
```bash
python3 tools/dbx.py patch
```
它把 0389:81E8 的 `call C06C` 改成 `mov ax,0`。每次重启 DOSBox 都要重新执行。模拟器的 `Game(seed=None)` 与这个补丁等价。

## 4. 采集一条用例
1. 在游戏里读入一个存档（标题画面选"时光倒转"），停在主画面（能看到 9 个命令图标）。
2. 记录初始状态和随机数：
```bash
python3 tools/dbx.py snapshot tests/cases/c01_before.GNX
```
```bash
python3 tools/dbx.py rng 0 0
```
   第二条把随机数状态设为 偏移0、下标0（也可以设别的值，记下来即可）。
3. 在游戏里排好这个月的日程并执行，**记下每一个菜单的选择**（包括事件里出现的选择）。一直点到回到主画面。
4. 记录结果：
```bash
python3 tools/dbx.py snapshot tests/cases/c01_after.GNX
```
```bash
python3 tools/dbx.py rng
```
5. 写 `tests/cases/c01.json`：
```json
{"before": "c01_before.GNX", "after": "c01_after.GNX",
 "rng_before": [0, 0], "rng_after": [0, 37],
 "plan": [["上課學習", "劍術"], ["打工賺錢", "農場"], ["休    息", "自由行動"]],
 "answers": {"給　　她": 0},
 "note": "F102 起，7 月"}
```
   `plan` 每旬一项，写菜单上的文字或序号。`answers` 的键是该菜单里**任意一个选项的文字**，值是要选的文字或序号；没写的菜单默认选第 0 项。
   文字必须和 `data/scripts` 里的写法一致（全角空格也算），拿不准就用序号。
6. 运行：
```bash
python3 tests/run_cases.py
```
   FAIL 时会列出不一致的变量名（中文名查 `data/tables/variables.json`）。

`snapshot` 直接从内存按存档格式导出，不需要在游戏里存档，也不会改变游戏状态。

## 5. 建议的用例顺序
先简单后复杂，每类至少 2 条，初始存档用 `game_sample/PM2/F101–F106.GNX`：
1. 三旬全休息（验证日历、月结成长、伙食费）。
2. 三旬同一门课；再换不同课（验证上课判定和等级）。
3. 三旬同一份工（农场、教堂、育幼院各一条）。
4. 混合日程；跨生日的月份；9 月（收获祭）；10 月底。
5. 主画面其他命令：买东西并装备、去王城、换饮食方针（用 `Game.main_command`，对比器目前只支持日程，需要时自行扩展 `run_cases.py`）。
6. 武者修行（见第 7 节，最后做）。

## 6. 不一致时怎么查
- **只有 `RNG` 不一致**：随机数抽取次数不同，多半是动画或显示相关的抽取。对照该日程脚本里的 `RANDAM`/`IRAND*`，
  用 `python3 tools/logic_view.py data/scripts/TXJO/JOB003.TXT` 看规则行；脚本全文在 `data/scripts`。
- **个别数值不一致**：先确认 `answers` 是否漏了事件选择（对比器输出前可打印 `r['menus']` 看模拟器遇到的全部菜单）。
- **怀疑原生命令**：`python3 tools/disasm_exe.py` 生成 `work/pm2.asm`，再用
  `python3 tools/asmview.py 0xb9cd 0xba10` 看指定线性地址（线性 = 段×16＋偏移，0389 段加 0x3890，1037 段加 0x10370）。
  每个 Python 命令的注释里都写了对应的 EXE 地址。
- 修模拟器时只改 `pm2sim/`，保留地址注释；**不要改实机采集的 GNX 和 json 去迁就模拟器**。

## 7. 我没有把握的地方（优先怀疑）
1. **随机数抽取顺序**：`TXSLCT`、`TMCHK2`、`WAIT*`、`TIMER*` 等被当作无随机数的空操作；若实机里它们内部会抽随机数，`RNG` 会对不上。
2. **菜单返回值**：`SLCT` 取消时返回 −1 是推断；`ITEMST`、`TXSLCT`、`WWMUSYA(15)` 的返回寄存器是推断。
3. **PARC 部件**：`DSKTOOL.COM` 功能 1（月结时调用）被当作空操作；`MIMA.COM` 101 号功能返回主菜单序号 0–8 的顺序是按脚本推断的。
4. **未初始化的 `.变量`**：实机里是上一个脚本留下的内存值，模拟器只近似了分配顺序。
5. **武者修行**：地图行走没有复现。模拟器每个时段调用 `driver.adventure_fn(eng, state, mode)`，
   由它返回 `{'x':…, 'y':…, 'ground':…, 'event':0/1/3}`；不设置时女儿原地不动、不触发地点事件。
   `WWMUSYA(3)` 返回的坐标单位、地形值、`WWMUSYA(23)` 的时段长度都没有核对，需要读 0389:0BA3 和 `MUSYAE.COM`。
6. **命名界面**：`NAMEIN.COM` 写入哪些变量是推断（名字、血型、双方生日）。
7. **结局**：只冒烟跑通过一次（强制满 18 岁后走到 `EEWK44` 士兵结局并播完），判定结果没有和实机对照。
   `play_month()` 返回值里的 `programs` 列出本月加载过的脚本，结局表现为 `EECALC → EEWKnn/EEWEnn`。
8. `XDBG(5)` 固定返回 0、`FFDISK(4)` 固定返回 1（硬盘版）、`PARC(4)` 固定返回 0（没有点击）。

## 8. 完成标准
- `python3 tests/test_sim.py` 和 `python3 tests/run_cases.py` 全部通过。
- 第 5 节 1–4 类用例齐全；第 7 节每一条要么有用例覆盖，要么在 `SUMMARY.md` 第 11 节注明仍未验证。
- 若实测推翻了 `SUMMARY.md` 里的结论，直接改该文件对应条目并去掉或补上 ✔。
