"""随机数：PCG32（XSH-RR，64 位状态），两个独立流。

GDD 16：逻辑流给规则用，表现流只给动画和文本用，互不影响。
约定（Godot 移植时照抄）：
- r(a, b) 取 a..b 的整数（含两端）。a == b 时直接返回 a，不消耗随机数。
- r0(n) = r(0, n)；r1(n) = r(1, n)。
- below(n) 取 0..n-1，用 PCG 官方的无偏做法（拒绝小于 2^32 mod n 的值）。
- chance(p, q) 为 below(q) < p，q 必须 >= 1；p <= 0 或 p >= q 时不消耗随机数。
"""
MASK64 = (1 << 64) - 1
MULT = 6364136223846793005


class PCG32:
    def __init__(self, seed=0, seq=0):
        self.state = 0
        self.inc = ((seq << 1) | 1) & MASK64
        self.next_u32()
        self.state = (self.state + seed) & MASK64
        self.next_u32()

    def next_u32(self):
        old = self.state
        self.state = (old * MULT + self.inc) & MASK64
        x = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return ((x >> rot) | (x << ((-rot) & 31))) & 0xFFFFFFFF

    def below(self, n):
        if n <= 0:
            raise ValueError('below(n) 需要 n >= 1')
        threshold = (0x100000000 - n) % n
        while True:
            v = self.next_u32()
            if v >= threshold:
                return v % n

    def r(self, a, b):
        if a == b:
            return a
        if b < a:
            raise ValueError(f'r({a},{b})')
        return a + self.below(b - a + 1)

    def r0(self, n):
        return self.r(0, n)

    def r1(self, n):
        return self.r(1, n)

    def chance(self, p, q):
        if p <= 0:
            return False
        if p >= q:
            return True
        return self.below(q) < p

    # 存档：64 位整数写成十六进制字符串，JSON 读进 Godot 不会丢精度
    def dump(self):
        return [f'{self.state:016x}', f'{self.inc:016x}']

    @classmethod
    def load(cls, d):
        g = cls.__new__(cls)
        g.state, g.inc = int(d[0], 16), int(d[1], 16)
        return g


class Rng:
    """两个流：logic（规则）、show（表现）。同一种子派生，序列号不同。"""

    def __init__(self, seed=0):
        self.logic = PCG32(seed, 1)
        self.show = PCG32(seed, 2)

    def dump(self):
        return {'logic': self.logic.dump(), 'show': self.show.dump()}

    @classmethod
    def load(cls, d):
        g = cls.__new__(cls)
        g.logic = PCG32.load(d['logic'])
        g.show = PCG32.load(d['show'])
        return g
