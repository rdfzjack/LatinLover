"""Bots and the report: every bot finishes, the same seed repeats, the report has at most 60 lines."""
import unittest
from sim.bots import BOTS, BotRng, play
from sim.rng import PCG32
from sim import report


class TestBots(unittest.TestCase):
    def test_all_bots_finish(self):
        for name, cls in BOTS.items():
            with self.subTest(bot=name):
                r = play(cls, 3)
                self.assertTrue(r['ending'])
                self.assertEqual(len(r['money']), len(r['train']))
                self.assertGreater(len(r['money']), 0)

    def test_deterministic(self):
        for name in ('only_lover', 'random_pick'):
            self.assertEqual(play(BOTS[name], 5), play(BOTS[name], 5))

    def test_bot_rng_is_its_own_pcg32_stream(self):
        # Step 12b: PCG32, sequence 3, seed * 1000003 + 17; Godot (tools/bots.gd) copies it
        g, ref = BotRng(7), PCG32(7 * 1000003 + 17, 3)
        self.assertEqual([g.below(10) for _ in range(20)], [ref.below(10) for _ in range(20)])
        g = BotRng(2)
        xs = ['a', 'b', 'c']
        ref = PCG32(2 * 1000003 + 17, 3)
        self.assertEqual(g.choice(xs), xs[ref.below(3)])
        self.assertEqual(g.chance(3, 5), ref.below(5) < 3)

    def test_on_month_called_every_month(self):
        seen = []
        r = play(BOTS['only_lover'], 2, on_month=lambda g, date: seen.append(date))
        self.assertEqual(len(seen), len(r['money']))
        self.assertEqual(seen[0], '1926-01')

    def test_report_lines(self):
        res = {n: [play(c, s) for s in (1, 2)] for n, c in BOTS.items()}
        lines = report.report(res, 2, True)
        self.assertLessEqual(len(lines), 60)


if __name__ == '__main__':
    unittest.main()
