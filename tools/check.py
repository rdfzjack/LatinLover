"""改完数据表后跑这个：一条命令查完所有问题。

    python3 tools/check.py          （Windows：双击仓库根目录的 检查数据.bat）

依次检查：
1. JSON 格式：少逗号、多逗号、中文引号这类错误，指出第几行。
2. 重复：同一张表里两条记录 id 相同，或同一条记录里一个字段写了两遍。
3. 内容：tools/check_data.py 的全部检查（字段齐全、引用的东西存在、条件和效果写法对）。
4. 试玩：几种机器人各跑一整局，确认游戏不会跑崩。
"""
import json
import os
import sys
import runpy
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'new')
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

JSON_HINTS = [
    ('Illegal trailing comma', '这里多了一个逗号：列表 [ ] 或 { } 里最后一项后面不能有逗号'),
    ("Expecting ',' delimiter", '这里少了一个英文逗号 ,（上一项和这一项之间要用逗号隔开）'),
    ('Expecting property name enclosed in double quotes', '多半是上一行末尾多了一个逗号（列表或 {} 里最后一项后面不能有逗号），或者字段名没用英文双引号括起来'),
    ('Expecting value', '这里缺了值：可能多了一个逗号，或者用了中文引号 “ ”，或者把 null / true / false 写错了'),
    ("Expecting ':' delimiter", '字段名后面要跟英文冒号 :'),
    ('Unterminated string', '引号没关上：一对英文双引号 " 要成对出现'),
    ('Invalid control character', '引号里面不能直接换行；要分段就写成两个字段，或者先写在一行里'),
    ('Extra data', '文件结尾多了东西：括号多了一个，或者在最外层的 } 后面还写了内容'),
]


def json_problem(path, e):
    lines = open(path, encoding='utf-8').read().split('\n')
    ln = e.lineno
    line = lines[ln - 1] if 0 < ln <= len(lines) else ''
    hint = next((h for k, h in JSON_HINTS if e.msg.startswith(k)), e.msg)
    out = [f'{os.path.basename(path)} 第 {ln} 行第 {e.colno} 个字符：{hint}']
    if ln > 1:
        out.append(f'    {ln - 1:>5} | {lines[ln - 2]}')
    out.append(f'    {ln:>5} | {line}')
    out.append('            ' + ' ' * (e.colno - 1) + '^ 大概在这里')
    for s in (lines[ln - 2] if ln > 1 else '', line):
        if any(c in s for c in '“”‘’：，'):
            out.append('    这附近有中文标点（“ ” ： ，），JSON 里的引号、冒号、逗号都要用英文的')
            break
    return '\n'.join(out)


def load_strict(path, problems):
    """读 JSON，同时找一条记录里写了两遍的字段。"""
    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                who = dict(pairs).get('id') or dict(pairs).get('名字') or ''
                problems.append(f'{os.path.basename(path)}：{("记录 " + str(who) + " 里") if who else "某条记录里"}字段“{k}”写了两遍，只能留一个')
            seen[k] = v
        return seen
    with open(path, encoding='utf-8-sig') as fh:
        return json.load(fh, object_pairs_hook=hook)


def step_json():
    problems, tables = [], {}
    for n in sorted(os.listdir(DATA)):
        if not n.endswith('.json'):
            continue
        p = os.path.join(DATA, n)
        raw = open(p, 'rb').read()
        if raw.startswith(b'\xef\xbb\xbf'):
            problems.append(f'{n}：文件开头带了 BOM（有的编辑器另存为“UTF-8 with BOM”），请存成不带 BOM 的 UTF-8')
        try:
            tables[n] = load_strict(p, problems)
        except json.JSONDecodeError as e:
            problems.append(json_problem(p, e))
        except UnicodeDecodeError:
            problems.append(f'{n}：不是 UTF-8 编码，请用 UTF-8 保存')
    return problems, tables


def step_dup(tables):
    problems = []
    seen_event = {}
    for n, t in tables.items():
        if not isinstance(t, dict):
            continue
        for k, v in t.items():
            if not (isinstance(v, list) and v and all(isinstance(x, dict) for x in v)):
                continue
            key = 'id' if any('id' in x for x in v) else ('名字' if all('名字' in x for x in v) else None)
            if key is None:
                continue
            ids = {}
            for x in v:
                i = x.get(key)
                if i is None:
                    continue
                if i in ids:
                    problems.append(f'{n} 的“{k}”里有两条 {key} 都是 {i}：复制一条改内容时别忘了改 {key}')
                ids[i] = 1
                if n in ('events.json', 'outing.json') and k == '事件' and key == 'id':
                    if i in seen_event and seen_event[i] != n:
                        problems.append(f'事件 id {i} 在 events.json 和 outing.json 里都有，事件 id 要全局唯一')
                    seen_event[i] = n
    return problems


KIND = {bool: '真假（true / false）', int: '数字（不加引号）', str: '文字（加英文双引号）', list: '列表 [ ]', dict: '{ } 块'}


def kind(v):
    return type(v) if type(v) in KIND else None


def step_types(tables):
    """同一张表的同一个字段，别的记录都是数字、这条却是文字之类：多半是笔误。
    只比数字、文字、真假；null 和列表、{} 块不管（概率、条件这些本来就有几种写法）。"""
    problems = []
    for n, t in tables.items():
        if not isinstance(t, dict):
            continue
        for k, v in t.items():
            if not (isinstance(v, list) and len(v) >= 3 and all(isinstance(x, dict) for x in v)):
                continue
            fields = {}
            for x in v:
                for f, val in x.items():
                    if val is not None:
                        fields.setdefault(f, []).append((kind(val), x))
            for f, lst in fields.items():
                count = {}
                for kd, _ in lst:
                    count[kd] = count.get(kd, 0) + 1
                if len(count) < 2:
                    continue
                main, m = max(count.items(), key=lambda a: a[1])
                if m < 3 or m < len(lst) * 0.8:
                    continue      # 本来就混着写的字段（比如 条件 可以是 [] 也可以是别的），不管
                if main not in (int, str, bool):
                    continue
                for kd, x in lst:
                    if kd != main and kd in (int, str, bool):
                        who = x.get('id') or x.get('名字') or '某条'
                        problems.append(f'{n}：{who} 的“{f}”写成了{KIND.get(kd, "?")}，这张表别的记录都是{KIND[main]}，'
                                        f'现在的值是 {json.dumps(x[f], ensure_ascii=False)}')
    return problems


def step_content():
    """跑 check_data.py，把它的输出原样带回来。"""
    import io
    import contextlib
    buf = io.StringIO()
    ok = True
    try:
        with contextlib.redirect_stdout(buf):
            runpy.run_path(os.path.join(ROOT, 'tools', 'check_data.py'), run_name='__main__')
    except SystemExit as e:
        ok = not e.code
    except KeyError as e:
        ok = False
        buf.write(f'有一条记录少了字段 {e}。把同一张表里别的记录拿来对照，看少写了哪个字段。\n')
        buf.write(_where())
    except Exception as e:
        ok = False
        buf.write(f'检查时出错：{type(e).__name__}: {e}\n多半是某个字段的值类型不对（例如该写数字的地方写成了 "文字"，或该写列表 [] 的地方写成了单个值）。\n')
        buf.write(_where())
    lines = [x for x in buf.getvalue().split('\n') if x.strip()]
    errs = [x for x in lines if not x.startswith(('通过', '注：', '失败：'))]
    return ok, errs, lines


def _where():
    tb = traceback.extract_tb(sys.exc_info()[2])
    fr = [f for f in tb if f.filename.endswith('check_data.py')]
    if fr:
        return f'（出错的检查在 tools/check_data.py 第 {fr[-1].lineno} 行：{fr[-1].line}）\n'
    return ''


def step_play():
    from sim import bots
    problems = []
    for cls in (bots.Hard, bots.Lover, bots.Culture, bots.Wrist, bots.Crime, bots.Random):
        for seed in (1, 2):
            try:
                bots.play(cls, seed)
            except Exception as e:
                tb = traceback.extract_tb(sys.exc_info()[2])
                fr = [f for f in tb if os.sep + 'sim' + os.sep in f.filename]
                at = f'{os.path.relpath(fr[-1].filename, ROOT)} 第 {fr[-1].lineno} 行' if fr else '?'
                problems.append(f'机器人“{cls.name}”第 {seed} 局跑到一半出错：{type(e).__name__}: {e}（{at}）')
                break
    return problems


def main():
    print('1/4 检查 JSON 格式……')
    problems, tables = step_json()
    if problems:
        print('\n\n'.join(problems))
        print('\n没通过：先把上面的格式错误改掉，再跑一次。')
        return 1
    print('2/4 检查重复和类型……')
    problems = step_dup(tables) + step_types(tables)
    if problems:
        print('\n'.join(problems))
        print('\n没通过：先把上面这些改掉，再跑一次。')
        return 1
    print('3/4 检查内容……')
    ok, errs, lines = step_content()
    if not ok:
        print('\n'.join(errs))
        print(f'\n没通过：内容有 {len(errs)} 处问题。每行开头是文件名，后面是哪一条、什么问题。')
        return 1
    print('4/4 机器人试玩……')
    problems = step_play()
    if problems:
        print('\n'.join(problems))
        print('\n没通过：表本身没问题，但游戏跑的时候出错了。多半是新加的内容用到了代码还不支持的写法，把上面这段发给模型。')
        return 1
    print('\n全部通过，可以提交。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
