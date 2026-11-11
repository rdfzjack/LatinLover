import unittest
from sim.month import Game, run_fixed
from sim.schedule import ScheduleError
from sim import street
from tests.new.helpers import D, Rec

PLAN = ['class_acting', 'job_dock', 'rest_home']
O = (4, 1, 3)   # 农学院学生、演技派、戒指：体力 80、相貌 120、自律 40、名气 100、金钱 500


class TestMonth(unittest.TestCase):
    def test_lifestyle(self):
        g = Game(D, seed=1, origin=O)
        g.start_month()
        self.assertEqual(g.st.money, 500 - 150)          # 眼熟档普通 150
        g.run_month(['rest_home'] * 3)
        g.set_lifestyle('life_diet')
        g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.attr['体力'], 60)
        self.assertEqual(g.st.attr['相貌'], 123)
        g.st.attr['体力'] = 10
        g.start_month()
        self.assertEqual(g.st.lifestyle, 'life_fine')     # 体力 <15 强制讲究

    def test_fame_decay(self):
        g = Game(D, seed=1, origin=O)
        g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.attr['名气'], 100 - 2)
        g.st.attr['名气'] = 30
        g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.attr['名气'], 29)            # 至少 -1
        g.start_month(); g.st.exposed = 1
        g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.attr['名气'], 29)

    def test_board_hook(self):
        rec = Rec()
        g = Game(D, seed=1, origin=O, hooks=rec)
        for _ in range(7):
            g.run_month(['rest_home'] * 3)
        self.assertEqual([c[1] for c in rec.calls if c[0] == 'board'], ['1926-01', '1926-04', '1926-07'])

    def test_bad_plan(self):
        g = Game(D, seed=1, origin=O)
        with self.assertRaises(ScheduleError):
            g.run_month(['job_studio', 'rest_home', 'rest_home'])
        with self.assertRaises(ScheduleError):
            g.run_month(['rest_home'])

    def test_heavy_sickness_and_collapse(self):
        rec = Rec()
        g = Game(D, seed=1, origin=O, hooks=rec)
        g.st.attr['疲劳'] = 900; g.st.money = 10000
        g.run_month(['job_dock'] * 3)
        self.assertEqual(g.st.idx['生病指数'], 100)
        self.assertEqual(g.st.forced_rest, 1)
        self.assertIn(('breach',), rec.calls)
        g.run_month(['job_dock'] * 3)                    # 被强制成疗养院，日程不检查
        self.assertEqual([x['日程'] for x in g.last], ['rest_sanatorium'] * 3)
        self.assertEqual(g.st.collapse_months, 2)
        self.assertEqual(g.st.ended, 'end_collapse')
        self.assertTrue(g.st.finished)

    def test_forced_rest_without_money(self):
        g = Game(D, seed=1, origin=O)
        g.st.attr['疲劳'] = 400; g.st.money = 150
        g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.forced_rest, 1)
        g.run_month(['job_dock'] * 3)
        self.assertEqual([x['日程'] for x in g.last], ['rest_home'] * 3)

    def test_romance_timer(self):
        g = Game(D, seed=1, origin=O)
        g.st.status['恋爱'] = 1; g.st.favor['Sil'] = 10
        g.st.attr['体力'] = 300
        for _ in range(3):
            g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.status['恋爱'], 0)
        self.assertEqual(g.st.favor['Sil'], 4)

    def test_romance_stays_if_looks_highest(self):
        g = Game(D, seed=1, origin=O)
        g.st.status['恋爱'] = 1
        for _ in range(4):
            g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.status['恋爱'], 1)

    def test_debt_and_stock_and_accent(self):
        g = Game(D, seed=1, origin=O)
        g.st.money = 100; g.st.stock = 1000; g.st.flags['口音期'] = 2
        g.run_month(['rest_home'] * 3)
        self.assertEqual((g.st.debt_months, g.st.stock, g.st.flags['口音期']), (1, 1030, 1))
        g.run_month(['rest_home'] * 3)
        self.assertEqual((g.st.debt_months, g.st.stock, g.st.flags['口音期']), (2, 1060, 0))
        g.st.money = 5000
        g.run_month(['rest_home'] * 3)
        self.assertEqual(g.st.debt_months, 0)

    def test_void_month(self):
        g = Game(D, seed=1, origin=O)
        g.st.void_next = 1
        g.run_month(['job_dock'] * 3)
        self.assertEqual([x['日程'] for x in g.last], ['作废'] * 3)
        self.assertEqual(g.st.cnt('计数.旬.job_dock'), 0)

    def test_full_game_ends(self):
        lines = run_fixed(3, (2, 2, 0), PLAN)
        self.assertEqual(len(lines), 48)
        self.assertTrue(lines[0].startswith('1926-01'))
        self.assertTrue(lines[-1].startswith('1929-12'))


class TestReproducible(unittest.TestCase):
    def test_same_seed_same_game(self):
        for origin in ((0, 0, 0), (4, 1, 5), (3, 3, 2)):
            self.assertEqual(run_fixed(11, origin, PLAN), run_fixed(11, origin, PLAN))
        self.assertNotEqual(run_fixed(11, (0, 0, 0), PLAN), run_fixed(12, (0, 0, 0), PLAN))

    def test_save_restore_midgame(self):
        def plan(st):
            return ['class_tutor', 'job_assistant', 'rest_outing@place_dock'] if st.ym % 2 else PLAN

        def play(g, n):
            out = []
            for _ in range(n):
                g.start_month()
                if g.st.ym == 5:
                    g.st.money = max(g.st.money, 50)
                    street.buy(g.st, '书店', 'book_tantu_1')
                g.run_month(plan(g.st))
                out.append(g.st.dumps())
            return out

        a = Game(D, seed=7, origin=(1, 2, 0))
        full = play(a, 48)
        b = Game(D, seed=7, origin=(1, 2, 0))
        play(b, 20)
        c = Game.restore(b.save(), D)
        self.assertEqual(play(c, 28), full[20:])
        self.assertTrue(c.st.finished)


if __name__ == '__main__':
    unittest.main()
