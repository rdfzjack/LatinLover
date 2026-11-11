import unittest
from sim.rng import PCG32, Rng


class TestRng(unittest.TestCase):
    def test_reference_vector(self):
        # PCG 官方 pcg32-demo：seed 42, seq 54
        g = PCG32(42, 54)
        self.assertEqual([g.next_u32() for _ in range(6)],
                         [0xa15c02b7, 0x7b47f409, 0xba1d3330, 0x83d2f293, 0xbfa4784b, 0xcbed606e])

    def test_ranges(self):
        g = PCG32(7, 1)
        seen = {g.r(3, 6) for _ in range(500)}
        self.assertEqual(seen, {3, 4, 5, 6})
        self.assertEqual({g.r0(1) for _ in range(200)}, {0, 1})
        self.assertEqual({g.r1(2) for _ in range(200)}, {1, 2})

    def test_fixed_range_does_not_draw(self):
        g = PCG32(7, 1)
        s = g.state
        self.assertEqual(g.r(5, 5), 5)
        self.assertEqual(g.r0(0), 0)
        self.assertTrue(g.chance(3, 3))
        self.assertFalse(g.chance(0, 3))
        self.assertEqual(g.state, s)

    def test_dump_load(self):
        r = Rng(99)
        for _ in range(10): r.logic.next_u32()
        r2 = Rng.load(r.dump())
        self.assertEqual([r.logic.next_u32() for _ in range(5)], [r2.logic.next_u32() for _ in range(5)])
        self.assertEqual(r.show.next_u32(), r2.show.next_u32())

    def test_streams_independent(self):
        a, b = Rng(5), Rng(5)
        for _ in range(20): a.show.next_u32()
        self.assertEqual(a.logic.next_u32(), b.logic.next_u32())
        self.assertNotEqual(Rng(5).logic.next_u32(), Rng(5).show.next_u32())


if __name__ == '__main__':
    unittest.main()
