import unittest
from sim import rules
from tests.new.helpers import fresh, bare


class TestCond(unittest.TestCase):
    def test_or_and(self):
        st = bare()
        self.assertTrue(rules.cond(st, []))
        self.assertTrue(rules.cond(st, [[['体力', '>=', 80], ['教育', '==', 5]]]))
        self.assertFalse(rules.cond(st, [[['体力', '>=', 80], ['教育', '>', 5]]]))
        self.assertTrue(rules.cond(st, [[['教育', '>', 5]], [['体力', '<', 100]]]))

    def test_in_and_ref(self):
        st = bare()
        self.assertTrue(rules.cond(st, [[['最高基础属性', 'in', ['相貌', '体力']]]]))
        self.assertTrue(rules.cond(st, [[['相貌', '>=', '@体力']]]))
        self.assertFalse(rules.cond(st, [[['教育', '>=', '@体力']]]))

    def test_vars(self):
        st = bare()
        self.assertEqual(rules.get_var(st, '日期'), '1926-01')
        self.assertEqual(rules.get_var(st, '月份'), 1)
        self.assertEqual(rules.get_var(st, '情人'), 50)
        self.assertEqual(rules.get_var(st, '最高声望'), 50)
        self.assertEqual(rules.get_var(st, '最高声望所在路'), '情人')
        self.assertEqual(rules.get_var(st, '旗标.没有'), 0)
        self.assertEqual(rules.get_var(st, '成功期数.job_dock'), 0)
        self.assertEqual(rules.get_var(st, '状态.收尾期'), 0)
        st.ym = 44   # 1929-09
        self.assertEqual(rules.get_var(st, '状态.收尾期'), 1)
        self.assertTrue(rules.cond(st, [[['日期', '>=', '1927-09']]]))
        import sim.ending  # noqa: F401  第 6 步登记的结局变量
        self.assertEqual(rules.get_var(st, '档次'), 'D')
        self.assertEqual(rules.get_var(st, '低成本定型'), 0)
        with self.assertRaises(KeyError):
            rules.get_var(st, '没有这个变量')


class TestEffect(unittest.TestCase):
    def test_basic_and_clamp(self):
        st = bare()
        rules.apply_effect(st, '体力+2000 教育-50 演技+500 金钱+7')
        self.assertEqual((st.attr['体力'], st.attr['教育'], st.skill['演技'], st.money), (999, 0, 100, 507))

    def test_percent_and_set(self):
        st = bare()
        rules.apply_effect(st, '名气-15%')
        self.assertEqual(st.attr['名气'], 120 - 18)
        rules.apply_effect(st, '名气+10%')
        self.assertEqual(st.attr['名气'], 102 + 10)
        rules.apply_effect(st, '疲劳=30')
        self.assertEqual(st.attr['疲劳'], 30)

    def test_flags_items_status_trigger(self):
        st = bare()
        t = rules.apply_effect(st, '旗标.口音期=4 物品.拳套=1 状态.恋爱=1 修正.情人+10 权重.西部+1 触发.evt_x')
        self.assertEqual(t, ['evt_x'])
        self.assertEqual(st.flags['口音期'], 4)
        self.assertIn('拳套', st.items)
        self.assertEqual(st.status['恋爱'], 1)
        self.assertEqual(st.rep('情人'), 60)
        self.assertEqual(st.weights['西部'], 1)
        rules.apply_effect(st, '物品.拳套=0')
        self.assertNotIn('拳套', st.items)

    def test_favor_bonus(self):
        st = bare()
        rules.apply_effect(st, '好感.Sil+3')
        self.assertEqual(st.favor['Sil'], 3)
        st.attr['义气'] = 200
        rules.apply_effect(st, '好感.Sil+3')
        self.assertEqual(st.favor['Sil'], 7)
        rules.apply_effect(st, '好感.Sil+2', source='schedule')
        self.assertEqual(st.favor['Sil'], 9)
        rules.apply_effect(st, '好感.Sil-5')
        self.assertEqual(st.favor['Sil'], 4)

    def test_unknown(self):
        with self.assertRaises(KeyError):
            rules.apply_effect(bare(), '魔力+1')
        with self.assertRaises(ValueError):
            rules.apply_effect(bare(), '体力++1')

    def test_tdiv(self):
        self.assertEqual(rules.tdiv(-7, 2), -3)
        self.assertEqual(rules.tdiv(7, 2), 3)
        self.assertEqual(rules.tdiv(-7, -2), 3)


class TestCheckProb(unittest.TestCase):
    def test_check(self):
        st = bare()
        self.assertTrue(rules.check(st, None))
        self.assertTrue(rules.check(st, ['体力', '>=', 80]))
        st.skill['胆识'] = 100
        self.assertTrue(all(rules.check(st, {'判定': '胆识', '线': 100}) for _ in range(50)))
        st.skill['胆识'] = 0
        self.assertFalse(any(rules.check(st, {'判定': '胆识', '线': 21}) for _ in range(50)))
        r = [rules.check(st, {'判定': '胆识', '线': 10}) for _ in range(2000)]
        self.assertAlmostEqual(sum(r) / 2000, 11 / 21, delta=0.04)

    def test_prob(self):
        st = bare()
        self.assertTrue(rules.prob(st, None))
        self.assertTrue(rules.prob(st, [1, 1]))
        self.assertFalse(rules.prob(st, [0, 5]))
        tier = [{'条件': [[['最高声望', '>=', 300]]], '值': [1, 1]}, {'条件': [], '值': [0, 1]}]
        self.assertFalse(rules.prob(st, tier))
        st.corr['情人'] = 300
        self.assertTrue(rules.prob(st, tier))

    def test_prob_formula(self):
        st = bare()
        p = {'分子': '犯罪', '分母': 2000, '上限': [1, 5]}
        st.attr['犯罪'] = 0
        self.assertFalse(any(rules.prob(st, p) for _ in range(200)))
        st.attr['犯罪'] = 999   # 999/2000 > 1/5，取上限
        n = sum(rules.prob(st, p) for _ in range(5000))
        self.assertAlmostEqual(n / 5000, 0.2, delta=0.02)


if __name__ == '__main__':
    unittest.main()
