"""Bots and the report: every bot finishes, the same seed repeats, the report has at most 60 lines."""
import unittest
from sim.bots import BOTS, play
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

    def test_report_lines(self):
        res = {n: [play(c, s) for s in (1, 2)] for n, c in BOTS.items()}
        lines = report.report(res, 2, True)
        self.assertLessEqual(len(lines), 60)


if __name__ == '__main__':
    unittest.main()
