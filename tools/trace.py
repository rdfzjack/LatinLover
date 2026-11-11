"""第 9 步对账：按 tools/trace_cases.json 输出随机数序列、存档往返、条件和效果的结果。

Godot 那边是 game/silentstar/tools/trace.gd，两份输出要逐字节一致；用 tools/compare_trace.py 比。

    python3 tools/trace.py --out work/trace_py.txt
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sim import data as D, rules  # noqa: E402
from sim.rng import PCG32, Rng  # noqa: E402
from sim.state import State  # noqa: E402


def js(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def run(cases):
    out = []
    w = out.append
    d = D.load()

    c = cases['随机数']
    for s in c['种子']:
        g = Rng(s)
        w(f'# 随机数 种子={s}')
        w('logic ' + ' '.join(str(g.logic.next_u32()) for _ in range(c['个数'])))
        w('show ' + ' '.join(str(g.show.next_u32()) for _ in range(c['个数'])))
        w('dump ' + js(g.dump()))

    c = cases['混合']
    g = Rng(c['种子'])
    w(f'# 混合 种子={c["种子"]}')
    for step in c['步骤']:
        op, args = step[0], step[1:]
        w(f'{op} {js(args)} -> {js(getattr(g.logic, op)(*args))}')
    w('dump ' + js(g.dump()))
    g2 = Rng.load(json.loads(js(g.dump())))
    w('续 ' + ' '.join(str(g.logic.next_u32()) for _ in range(4)))
    w('读回 ' + ' '.join(str(g2.logic.next_u32()) for _ in range(4)))
    p = PCG32.load(g.show.dump())
    w('show 读回 ' + str(p.next_u32()) + ' ' + str(g.show.next_u32()))

    for c in cases['开局']:
        st = State.new(d, c['种子'], tuple(c['开局']))
        s1 = st.dumps()
        w(f'# 开局 种子={c["种子"]} 开局={js(c["开局"])}')
        w('存档 ' + s1)
        s2 = State.loads(d, s1).dumps()
        w('往返 ' + ('一致' if s1 == s2 else '不一致 ' + s2))

    c = cases['效果']
    st = State.new(d, c['种子'], tuple(c['开局']))
    w(f'# 效果 种子={c["种子"]} 开局={js(c["开局"])}')
    for step in c['步骤']:
        if isinstance(step, dict):
            if '装备' in step:
                st.equip = json.loads(js(step['装备']))
                w('装备 ' + js(st.equip) + ' 加成 ' + js(st.bonus()))
            if step.get('更新指数'):
                st.update_indices()
                w('更新指数 ' + js(st.idx) + ' ' + js(st.status))
            continue
        text = step[0]
        source = step[1] if len(step) > 1 else 'event'
        trig = rules.apply_effect(st, text, source=source)
        w(f'效果 {text} [{source}] -> {js(trig)} 金钱={st.money} 好感={js(st.favor)} 物品={js(st.items)}'
          f' 装备={js(st.equip)} 加成={js(st.bonus())}')
    w('等级 ' + js({r: st.level(r) for r in d.roads}) + ' 名气档 ' + str(st.fame_tier()))
    for name in cases['变量']:
        w(f'变量 {name} = {js(rules.get_var(st, name))}')
    for cd in cases['条件']:
        w(f'条件 {js(cd)} = {js(rules.cond(st, cd))}')
    for ck in cases['判定']:
        w(f'判定 {js(ck)} = {js(rules.check(st, ck))}')
    for pr in cases['概率']:
        w(f'概率 {js(pr)} = {js(rules.prob(st, pr))}')
    s1 = st.dumps()
    w('存档 ' + s1)
    s2 = State.loads(d, s1).dumps()
    w('往返 ' + ('一致' if s1 == s2 else '不一致 ' + s2))
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', default=os.path.join(ROOT, 'tools', 'trace_cases.json'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    with open(a.cases, encoding='utf-8') as fh:
        text = run(json.load(fh))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print(f'写到 {a.out}，{text.count(chr(10))} 行')
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
