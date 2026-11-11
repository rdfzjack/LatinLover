"""Compares the reconciliation output of Python and Godot and prints only the first difference.

    python3 tools/compare_trace.py work/trace_py.txt work/trace_godot.txt

Exit code 0 when identical; otherwise prints the line number and the part of the line on both sides around the first differing character, exit code 1.
The month-by-month reconciliation from step 10 on uses it too.
"""
import sys


def main(a, b):
    x = open(a, 'rb').read()
    y = open(b, 'rb').read()
    if x == y:
        n = x.count(b'\n')
        print(f'identical: {n} lines, {len(x)} bytes')
        return 0
    lx = x.decode('utf-8', 'replace').split('\n')
    ly = y.decode('utf-8', 'replace').split('\n')
    for i in range(max(len(lx), len(ly))):
        p = lx[i] if i < len(lx) else '<no such line>'
        q = ly[i] if i < len(ly) else '<no such line>'
        if p != q:
            k = next((j for j in range(min(len(p), len(q))) if p[j] != q[j]), min(len(p), len(q)))
            s = max(0, k - 40)
            print(f'differs from line {i + 1}, char {k + 1}')
            print(f'  {a}: …{p[s:k + 80]}')
            print(f'  {b}: …{q[s:k + 80]}')
            return 1
    print('same content, only line endings or encoding differ (check for CRLF or a BOM)')
    return 1


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
