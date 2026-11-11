"""比较 Python 和 Godot 的对账输出，只打印第一处不同。

    python3 tools/compare_trace.py work/trace_py.txt work/trace_godot.txt

一致时退出码 0；不一致时打印行号、两边那一行在第一个不同字符附近的片段，退出码 1。
第 10 步以后的逐月对账也用它。
"""
import sys


def main(a, b):
    x = open(a, 'rb').read()
    y = open(b, 'rb').read()
    if x == y:
        n = x.count(b'\n')
        print(f'一致：{n} 行，{len(x)} 字节')
        return 0
    lx = x.decode('utf-8', 'replace').split('\n')
    ly = y.decode('utf-8', 'replace').split('\n')
    for i in range(max(len(lx), len(ly))):
        p = lx[i] if i < len(lx) else '<没有这一行>'
        q = ly[i] if i < len(ly) else '<没有这一行>'
        if p != q:
            k = next((j for j in range(min(len(p), len(q))) if p[j] != q[j]), min(len(p), len(q)))
            s = max(0, k - 40)
            print(f'第 {i + 1} 行第 {k + 1} 个字符起不同')
            print(f'  {a}: …{p[s:k + 80]}')
            print(f'  {b}: …{q[s:k + 80]}')
            return 1
    print('内容相同，只有换行或编码不同（检查是否写成了 CRLF 或带 BOM）')
    return 1


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
