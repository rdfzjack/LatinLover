"""机器人和报告：每种机器人跑得完、同种子可重复；报告不超过 60 行。"""
import unittest
from sim.bots import BOTS, play
from sim import report


class TestBots(unittest.TestCase):
    def test_all_bots_finish(self):
        for name, cls in BOTS.items():
            with self.subTest(bot=name):
                r = play(cls, 3)
                self.assertTrue(r['结局'])
                self.assertEqual(len(r['money']), len(r['train']))
                self.assertGreater(len(r['money']), 0)

    def test_deterministic(self):
        for name in ('专练情人', '乱选'):
            self.assertEqual(play(BOTS[name], 5), play(BOTS[name], 5))

    def test_report_lines(self):
        res = {n: [play(c, s) for s in (1, 2)] for n, c in BOTS.items()}
        lines = report.report(res, 2, True)
        self.assertLessEqual(len(lines), 60)


if __name__ == '__main__':
    unittest.main()
