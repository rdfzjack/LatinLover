"""Random numbers: PCG32 (XSH-RR, 64-bit state), two independent streams.

GDD 16: the logic stream is for rules, the show stream only for animation and text; they never affect each other.
Conventions (Godot copies them when porting):
- r(a, b) returns an integer in a..b (both ends included). When a == b it returns a without consuming a random number.
- r0(n) = r(0, n); r1(n) = r(1, n).
- below(n) returns 0..n-1 using PCG's official unbiased method (rejecting values below 2^32 mod n).
- chance(p, q) is below(q) < p, q must be >= 1; when p <= 0 or p >= q no random number is consumed.
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
            raise ValueError('below(n) needs n >= 1')
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

    # Save: the 64-bit integers are written as hex strings so that Godot's JSON reader does not lose precision
    def dump(self):
        return [f'{self.state:016x}', f'{self.inc:016x}']

    @classmethod
    def load(cls, d):
        g = cls.__new__(cls)
        g.state, g.inc = int(d[0], 16), int(d[1], 16)
        return g


class Rng:
    """Two streams: logic (rules) and show (presentation). Derived from the same seed with different sequence numbers."""

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
