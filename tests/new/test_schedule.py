import unittest
from sim import schedule as S
from sim.month import Hooks
from tests.new.helpers import D, bare, Rec

H = Hooks()


def strong(st):
    """A state that cannot fail: stamina, education and all skills maxed, fatigue 0."""
    for k in ('stamina', 'education', 'looks'):
        st.attr[k] = 999
    for k in st.skill:
        st.skill[k] = 100
    st.attr['fatigue'] = 0
    return st


class TestClass(unittest.TestCase):
    def test_level_and_fee(self):
        st = bare()
        st.money = 100000
        levels = []
        for _ in range(11):
            levels.append(S.class_level(st, 'class_boxing'))
            S.run_period(st, 0, 'class_boxing', H)
        self.assertEqual(levels, [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4])
        # the early part of 1926-01 has 2 Sundays (3rd and 10th), 8 class days
        st = bare(); st.money = 1000
        S.run_period(st, 0, 'class_boxing', H)
        self.assertEqual(st.money, 1000 - 8 * 9)
        self.assertEqual(st.attr['fatigue'], 8)
        self.assertEqual(st.cnt('road_periods.tough'), 1)

    def test_no_money_days(self):
        st = bare(); st.money = 30
        S.run_period(st, 0, 'class_boxing', H)
        self.assertEqual(st.money, 3)
        self.assertEqual(st.cnt('count.broke_class_days'), 5)
        st = bare(); st.money = 0
        S.run_period(st, 0, 'class_boxing', H)
        self.assertEqual(st.cnt('class_periods.class_boxing'), 0)

    def test_gains_when_fresh(self):
        st = strong(bare()); st.money = 1000
        st.skill['fight'] = 10
        S.run_period(st, 0, 'class_boxing', H)
        self.assertEqual(st.skill['fight'], 18)   # level 1 gives +1 a day, all 8 days succeed
        self.assertEqual(st.attr['stamina'], 999)

    def test_tutor_chain_and_duv(self):
        st = bare(); st.money = 100000
        rec = Rec()
        for _ in range(10):
            S.run_period(st, 0, 'class_tutor', rec)
        self.assertEqual([c[2] for c in rec.calls if c[0] == 'chain'], [1, 4, 7, 10])
        self.assertEqual(st.favor['duv'], 20)
        self.assertEqual(st.cnt('road_periods.culture'), 10)

    def test_accent_bonus(self):
        st = strong(bare()); st.money = 1000
        st.skill['speech'] = 10
        st.flags['accent_period'] = 2
        S.run_period(st, 0, 'class_acting', H)
        self.assertGreaterEqual(st.skill['speech'], 19)


class TestBook(unittest.TestCase):
    def test_read_and_finish(self):
        st = strong(bare()); st.skill['speech'] = 0
        st.books['book_tantu_1'] = 35
        self.assertIsNone(S.validate(st, 'book_tantu_1'))
        rec = Rec()
        S.run_period(st, 0, 'book_tantu_1', rec)
        self.assertEqual((st.skill['speech'], st.books['book_tantu_1']), (12, 23))
        for _ in range(4):
            S.run_period(st, 0, 'book_tantu_1', rec)
        self.assertEqual(st.skill['speech'], 35)
        self.assertNotIn('book_tantu_1', st.books)
        self.assertIn('book_tantu_1', st.read_books)
        self.assertIn(('book_done', 'book_tantu_1'), rec.calls)
        self.assertEqual(st.cnt('road_periods.culture'), 5)

    def test_cap(self):
        st = strong(bare()); st.skill['speech'] = 38
        st.books['book_tantu_1'] = 35
        S.run_period(st, 0, 'book_tantu_1', H)
        self.assertEqual((st.skill['speech'], st.books['book_tantu_1']), (40, 33))

    def test_validate(self):
        st = bare()
        self.assertIsNotNone(S.validate(st, 'book_tantu_1'))   # none
        st.books['book_tantu_1'] = 35
        self.assertIsNotNone(S.validate(st, 'book_tantu_1'))   # education 5 < 100
        st.attr['education'] = 100
        self.assertIsNone(S.validate(st, 'book_tantu_1'))


class TestJob(unittest.TestCase):
    def test_wage_tiers(self):
        st = bare()
        exp = {0: 30, 4: 30, 5: 36, 14: 36, 15: 43, 30: 51, 45: 62, 99: 62}
        for n, w in exp.items():
            st.count['job_periods.job_bootleg'] = n
            self.assertEqual(S.wage_of(st, 'job_bootleg'), w, n)

    def test_full_attendance(self):
        st = strong(bare()); st.money = 0
        rec = Rec()
        out = S.run_period(st, 0, 'job_dock', rec)
        self.assertEqual(out['ok_days'], 8)
        self.assertEqual(st.money, 6 * 8 * 150 // 100)
        self.assertEqual(st.cnt('job_periods.job_dock'), 1)
        self.assertEqual(rec.calls, [('job', 'job_dock', True)])
        self.assertEqual(st.attr['fatigue'], 24)

    def test_period_counts_roads(self):
        st = strong(bare())
        S.run_period(st, 0, 'job_assistant', H)
        self.assertEqual(st.cnt('road_periods.savvy'), 1)
        S.run_period(st, 0, 'job_bar', H)
        self.assertEqual(st.cnt('road_periods.tough'), 1)

    def test_fail_all(self):
        st = bare(); st.attr['stamina'] = 0
        S.run_period(st, 0, 'job_bar', H)
        self.assertEqual(st.money, 500)
        self.assertEqual(st.cnt('job_periods.job_bar'), 0)

    def test_unlock(self):
        st = bare()
        self.assertIsNotNone(S.validate(st, 'job_studio'))
        st.ym = 3
        self.assertIsNone(S.validate(st, 'job_studio'))
        st.ym = 12
        self.assertIsNotNone(S.validate(st, 'job_bootleg'))
        st.count['job_periods.job_bar'] = 3
        self.assertIsNone(S.validate(st, 'job_bootleg'))
        st.count['job_periods.job_bar'] = 0
        st.flags['smuggling'] = 1
        self.assertIsNone(S.validate(st, 'job_bootleg'))

    def test_refuse(self):
        st = bare()
        st.idx['reckless_index'] = 60
        self.assertIsNotNone(S.validate(st, 'job_dock'))
        for j in ('job_church', 'job_assistant', 'job_bar'):
            self.assertIsNone(S.validate(st, j))

    def test_diploma_line(self):
        st = bare()
        self.assertEqual(S.job_lines(st, D.jobs['job_news']), [['education', 60]])
        st.flags['diploma'] = 1
        self.assertEqual(S.job_lines(st, D.jobs['job_news']), [['education', 40]])

    def test_slacking(self):
        st = strong(bare())
        st.idx['reckless_index'] = 30
        ok = sum(S.run_period(st, 0, 'job_church', H)['ok_days'] for _ in range(100))
        st.attr['fatigue'] = 0
        self.assertAlmostEqual(ok / 800, 0.2, delta=0.05)

    def test_romance_fail(self):
        st = strong(bare())
        st.status['in_love'] = 1
        ok = 0
        for _ in range(100):
            st.attr['fatigue'] = 0
            ok += S.run_period(st, 0, 'class_tutor', H)['ok_days']
            st.money = 1000
        self.assertAlmostEqual(ok / 800, 0.8, delta=0.05)


class TestRest(unittest.TestCase):
    def test_home(self):
        st = bare(); st.attr['fatigue'] = 100
        S.run_period(st, 0, 'rest_home', H)
        self.assertEqual((st.attr['fatigue'], st.favor['sil']), (50, 2))   # Sil keeps company: +2 per period

    def test_outing(self):
        st = bare(); st.attr['fatigue'] = 200; st.money = 13
        rec = Rec()
        S.run_period(st, 0, 'rest_outing@place_seaside', rec)
        # 10/day, only the first day is affordable: -10, the other 9 days -5
        self.assertEqual((st.money, st.attr['fatigue']), (3, 200 - 10 - 45))
        self.assertEqual(rec.calls, [('outing', 'place_seaside')])
        self.assertEqual(st.cnt('count.outing.place_seaside'), 1)
        self.assertIsNotNone(S.validate(st, 'rest_outing'))
        self.assertIsNotNone(S.validate(st, 'rest_home@place_dock'))

    def test_sanatorium(self):
        st = bare(); st.attr['fatigue'] = 200; st.money = 20
        self.assertIsNotNone(S.validate(st, 'rest_sanatorium'))   # the player cannot pick it, it is forced only when very sick
        S.run_period(st, 0, 'rest_sanatorium', H)
        self.assertEqual((st.money, st.attr['fatigue']), (4, 178))

    def test_resort(self):
        st = bare(); st.attr['fatigue'] = 400
        rec = Rec()
        self.assertEqual(S.place_cost(st, 'place_resort'), 8)    # familiar tier 8 per day
        S.run_period(st, 0, 'rest_outing@place_resort', rec)
        self.assertEqual((st.money, st.attr['fatigue']), (420, 100))
        self.assertEqual(rec.calls, [('outing', 'place_resort')])

    def test_sick_restriction(self):
        st = bare(); st.status['sick'] = 1
        self.assertIsNone(S.validate(st, 'rest_home'))
        for r in ('rest_outing@place_resort', 'rest_outing@place_dock'):
            self.assertIsNotNone(S.validate(st, r))
        self.assertIsNone(S.validate(st, 'job_dock'))   # being sick does not change the schedule success rate and does not forbid jobs

    def test_options(self):
        st = bare()
        o = S.options(st)
        self.assertIn('job_dock', o)
        self.assertNotIn('job_studio', o)
        self.assertIn('rest_outing@place_dock', o)
        self.assertEqual(sum(1 for x in o if x.startswith('class_')), 6)


if __name__ == '__main__':
    unittest.main()
