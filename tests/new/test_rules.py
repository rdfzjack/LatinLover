import unittest
from sim import rules
from tests.new.helpers import fresh, bare


class TestCond(unittest.TestCase):
    def test_or_and(self):
        st = bare()
        self.assertTrue(rules.cond(st, []))
        self.assertTrue(rules.cond(st, [[['stamina', '>=', 80], ['education', '==', 5]]]))
        self.assertFalse(rules.cond(st, [[['stamina', '>=', 80], ['education', '>', 5]]]))
        self.assertTrue(rules.cond(st, [[['education', '>', 5]], [['stamina', '<', 100]]]))

    def test_in_and_ref(self):
        st = bare()
        self.assertTrue(rules.cond(st, [[['top_base_attr', 'in', ['looks', 'stamina']]]]))
        self.assertTrue(rules.cond(st, [[['looks', '>=', '@stamina']]]))
        self.assertFalse(rules.cond(st, [[['education', '>=', '@stamina']]]))

    def test_vars(self):
        st = bare()
        self.assertEqual(rules.get_var(st, 'date'), '1926-01')
        self.assertEqual(rules.get_var(st, 'month'), 1)
        self.assertEqual(rules.get_var(st, 'lover'), 50)
        self.assertEqual(rules.get_var(st, 'max_rep'), 50)
        self.assertEqual(rules.get_var(st, 'top_road'), 'lover')
        self.assertEqual(rules.get_var(st, 'flag.none'), 0)
        self.assertEqual(rules.get_var(st, 'job_periods.job_dock'), 0)
        self.assertEqual(rules.get_var(st, 'status.wrap_up'), 0)
        st.ym = 44   # 1929-09
        self.assertEqual(rules.get_var(st, 'status.wrap_up'), 1)
        self.assertTrue(rules.cond(st, [[['date', '>=', '1927-09']]]))
        import sim.ending  # noqa: F401  ending variables registered in step 6
        self.assertEqual(rules.get_var(st, 'grade'), 'D')
        self.assertEqual(rules.get_var(st, 'lowbudget_typed'), 0)
        with self.assertRaises(KeyError):
            rules.get_var(st, 'no such variable')


class TestEffect(unittest.TestCase):
    def test_basic_and_clamp(self):
        st = bare()
        rules.apply_effect(st, 'stamina+2000 education-50 acting+500 money+7')
        self.assertEqual((st.attr['stamina'], st.attr['education'], st.skill['acting'], st.money), (999, 0, 100, 507))

    def test_percent_and_set(self):
        st = bare()
        rules.apply_effect(st, 'fame-15%')
        self.assertEqual(st.attr['fame'], 120 - 18)
        rules.apply_effect(st, 'fame+10%')
        self.assertEqual(st.attr['fame'], 102 + 10)
        rules.apply_effect(st, 'fatigue=30')
        self.assertEqual(st.attr['fatigue'], 30)

    def test_flags_items_status_trigger(self):
        st = bare()
        t = rules.apply_effect(st, 'flag.accent_period=4 item.boxing_gloves=1 status.in_love=1 rep_bonus.lover+10 weight.western+1 trigger.evt_x')
        self.assertEqual(t, ['evt_x'])
        self.assertEqual(st.flags['accent_period'], 4)
        self.assertIn('boxing_gloves', st.items)
        self.assertEqual(st.status['in_love'], 1)
        self.assertEqual(st.rep('lover'), 60)
        self.assertEqual(st.weights['western'], 1)
        rules.apply_effect(st, 'item.boxing_gloves=0')
        self.assertNotIn('boxing_gloves', st.items)

    def test_favor_bonus(self):
        st = bare()
        rules.apply_effect(st, 'favor.sil+3')
        self.assertEqual(st.favor['sil'], 3)
        st.attr['loyalty'] = 200
        rules.apply_effect(st, 'favor.sil+3')
        self.assertEqual(st.favor['sil'], 7)
        rules.apply_effect(st, 'favor.sil+2', source='schedule')
        self.assertEqual(st.favor['sil'], 9)
        rules.apply_effect(st, 'favor.sil-5')
        self.assertEqual(st.favor['sil'], 4)

    def test_unknown(self):
        with self.assertRaises(KeyError):
            rules.apply_effect(bare(), 'magic+1')
        with self.assertRaises(ValueError):
            rules.apply_effect(bare(), 'stamina++1')

    def test_tdiv(self):
        self.assertEqual(rules.tdiv(-7, 2), -3)
        self.assertEqual(rules.tdiv(7, 2), 3)
        self.assertEqual(rules.tdiv(-7, -2), 3)


class TestCheckProb(unittest.TestCase):
    def test_check(self):
        st = bare()
        self.assertTrue(rules.check(st, None))
        self.assertTrue(rules.check(st, ['stamina', '>=', 80]))
        st.skill['nerve'] = 100
        self.assertTrue(all(rules.check(st, {'check': 'nerve', 'line': 100}) for _ in range(50)))
        st.skill['nerve'] = 0
        self.assertFalse(any(rules.check(st, {'check': 'nerve', 'line': 21}) for _ in range(50)))
        r = [rules.check(st, {'check': 'nerve', 'line': 10}) for _ in range(2000)]
        self.assertAlmostEqual(sum(r) / 2000, 11 / 21, delta=0.04)

    def test_prob(self):
        st = bare()
        self.assertTrue(rules.prob(st, None))
        self.assertTrue(rules.prob(st, [1, 1]))
        self.assertFalse(rules.prob(st, [0, 5]))
        tier = [{'cond': [[['max_rep', '>=', 300]]], 'value': [1, 1]}, {'cond': [], 'value': [0, 1]}]
        self.assertFalse(rules.prob(st, tier))
        st.corr['lover'] = 300
        self.assertTrue(rules.prob(st, tier))

    def test_prob_formula(self):
        st = bare()
        p = {'numerator': 'crime', 'denominator': 2000, 'max': [1, 5]}
        st.attr['crime'] = 0
        self.assertFalse(any(rules.prob(st, p) for _ in range(200)))
        st.attr['crime'] = 999   # 999/2000 > 1/5, take the cap
        n = sum(rules.prob(st, p) for _ in range(5000))
        self.assertAlmostEqual(n / 5000, 0.2, delta=0.02)


if __name__ == '__main__':
    unittest.main()
