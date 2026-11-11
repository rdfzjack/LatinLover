import unittest
from sim import audition as A
from tests.new.helpers import D, bare


class Scripted(A.Player):
    """固定组牌，按给定顺序出牌（下标指剩余手牌）。"""
    def __init__(self, colors, picks=None):
        self.colors, self.picks = colors, list(picks or [])

    def deck(self, st, ctx):
        return self.colors

    def play(self, st, ctx):
        return self.picks.pop(0) if self.picks else 0


def rival(levels, k=5, habit='habit_random', fame=100, rid=None):
    return {'id': rid, '名字': 'x', '等级': levels, '名气': fame, '习惯': habit, 'k': k}


class TestPoints(unittest.TestCase):
    def test_build_deck(self):
        self.assertEqual(A.build_deck([3, 6, 1, 1], [1, 1, 0, 1, 0]), [(1, 6), (1, 5), (0, 3), (1, 4), (0, 2)])
        self.assertEqual(A.build_deck([1, 1, 1, 1], [0, 0, 0]), [(0, 1), (0, 0), (0, 0)])

    def test_effective(self):
        # 场风 ×1.3；硬汉克情人 ×1.5 / ×0.7；场风色不受克制
        self.assertEqual(A.effective(D, (1, 6), (1, 6), 1), (780, 780))
        self.assertEqual(A.effective(D, (0, 6), (1, 6), 2), (900, 420))
        self.assertEqual(A.effective(D, (0, 6), (1, 6), 1), (600, 780))
        self.assertEqual(A.effective(D, (0, 6), (1, 6), 0), (1170, 420))
        self.assertEqual(A.effective(D, (0, 5), (2, 5), 3), (500, 500))   # 相对两色互不相干
        self.assertEqual(A.effective(D, (3, 4), (0, 8), 1), (600, 560))    # 手腕克硬汉

    def test_tie(self):
        self.assertFalse(A.round_winner(D, (1, 6), (1, 6), 1, 100, 100))
        self.assertTrue(A.round_winner(D, (1, 6), (1, 6), 1, 101, 100))


class TestTable77(unittest.TestCase):
    """GDD 7.7：双方随机出牌的胜率，误差 ±3 个百分点。"""

    def test_exact(self):
        for name, v, gdd in A.table_77(D):
            if gdd == 13:
                continue   # 第 3 行和现行规则对不上（现行 0%），等用户定，见 README 交接
            self.assertAlmostEqual(v, gdd, delta=3, msg=name)

    @unittest.skip('GDD 7.7 第 3 行（13%）在现行规则下是 0%，等用户定')
    def test_row3(self):
        self.assertAlmostEqual(A.table_77(D)[2][1], 13, delta=3)

    def test_through_match(self):
        """同样的局面走完整的 match()（对手随性、玩家随机），抽样结果也在 ±3 内。"""
        st = bare(5)
        st.attr['名气'] = 0
        for name, ml, mc, ol, k, f, gdd in A.TABLE_77:
            if gdd == 13:
                continue
            rv = rival(ol, k)
            deck = A.build_deck(ml, mc)
            n = 3000
            w = sum(A.match(st, deck, rv, [25, 25, 25, 25], A.FixedRandomPlayer(mc), field=f)['比分'][0] == 3
                    for _ in range(n))
            self.assertAlmostEqual(w * 100 / n, gdd, delta=3, msg=name)


class TestOpponent(unittest.TestCase):
    def test_deck_formula(self):
        # 等级 [5,9,2,3]，场风 [15,60,10,15]：情人主色；第二大 9 之后是硬汉 5
        rv = rival([5, 9, 2, 3], k=4)
        self.assertEqual(A.opponent_deck(D, rv, [15, 60, 10, 15]), [(1, 9), (1, 8), (1, 7), (1, 6), (0, 5)])
        # 5 × (1 + 0.3×5%) = 5.075 仍大于 4 × (1 + 0.3×60%) = 4.72；同级时场风概率决定
        self.assertEqual(A.opponent_colors(D, [5, 1, 4, 1], [5, 30, 60, 5])[:2], [0, 2])
        self.assertEqual(A.opponent_colors(D, [5, 1, 5, 1], [5, 30, 60, 5])[:2], [2, 0])

    def test_unnamed(self):
        st = bare(3)
        st.ym = 0
        for _ in range(50):
            r = A.unnamed_rival(st, '小', probs=[10, 60, 10, 20])
            self.assertIn(r['等级'][1], (1, 2))
            self.assertEqual(r['名气'], 40)
            self.assertEqual(r['k'], 4)
            self.assertEqual(r['等级'][0], 1)
            self.assertEqual(r['等级'][2], 1)
        st.ym = 47   # h = 7：主色 2 + 7/3 = 4，随机 -1..0
        ls = {A.unnamed_rival(st, '小', probs=[10, 60, 10, 20])['等级'][1] for _ in range(100)}
        self.assertEqual(ls, {3, 4})
        r = A.unnamed_rival(st, '大', main_level=7, probs=[15, 60, 10, 15])
        self.assertEqual(r['等级'], [5, 7, 1, 1])
        self.assertEqual(r['名气'], 300 + 15 * 7)
        st.ym = 18   # 1927-07 涨一级：h = 3
        self.assertEqual(A.half_years(st) // 3, 1)

    def test_named(self):
        st = bare()
        st.ym = D.month_index['1927-03']
        r = A.named_rival(st, 'rival_jilbo')
        self.assertEqual((r['等级'], r['名气']), ([4, 8, 3, 2], 650))
        st.ym = D.month_index['1929-02']
        self.assertEqual(A.named_rival(st, 'rival_fanban')['等级'], [7, 5, 3, 6])
        self.assertEqual(A.named_rival(st, 'rival_fanban')['名气'], 750)   # 名气沿用
        st.ym = D.month_index['1927-08']
        self.assertEqual(A.named_rival(st, 'rival_valen')['id'], 'rival_valen')
        st.ym = D.month_index['1927-09']
        self.assertIn(A.named_rival(st, 'rival_valen')['id'], ('rival_nova', 'rival_jilbo'))
        self.assertFalse(A.rival_present(st, 'rival_valen'))
        self.assertFalse(A.rival_present(st, 'rival_jolson'))


class TestHabits(unittest.TestCase):
    def picks(self, habit, rnd=0, my_last=None, score=(0, 0), hand=None):
        st = bare(9)
        hand = hand or [(1, 6), (1, 5), (1, 4), (0, 6), (2, 1)]   # 场风情人：780 650 520 600 100
        out = [A.opponent_pick(st, habit, hand, 1, rnd, my_last, score) for _ in range(2000)]
        return max(set(out), key=out.count), out.count(max(set(out), key=out.count)) / 2000

    def test_follow_rate(self):
        top, rate = self.picks('habit_lead')
        self.assertEqual(top, 0)
        self.assertAlmostEqual(rate, 0.8 + 0.2 / 5, delta=0.03)

    def test_each(self):
        self.assertEqual(self.picks('habit_lead')[0], 0)
        self.assertEqual(self.picks('habit_finish')[0], 4)
        self.assertEqual(self.picks('habit_open', rnd=0)[0], 0)
        self.assertEqual(self.picks('habit_open', rnd=2)[0], 4)
        self.assertEqual(self.picks('habit_follow', rnd=0)[0], 3)            # 中间那张：600
        self.assertEqual(self.picks('habit_follow', rnd=1, my_last=(1, 4))[0], 3)   # 赢 520 的最小：硬汉 600（场风色不吃克制）
        self.assertEqual(self.picks('habit_follow', rnd=1, my_last=(1, 9))[0], 4)   # 赢不了出最小
        self.assertEqual(self.picks('habit_score', score=(1, 1))[0], 0)
        self.assertEqual(self.picks('habit_score', score=(0, 1))[0], 4)
        _, rate = self.picks('habit_random')
        self.assertLess(rate, 0.3)


class TestAudition(unittest.TestCase):
    ROLE = {'id': 'role_x', '场风概率': [10, 60, 10, 20]}

    def test_win_remembered(self):
        st = bare(1)
        r = A.audition(st, self.ROLE, Scripted([1] * 5), [rival([1, 1, 1, 1], rid='rival_kup')])
        self.assertEqual((r['结果'], r['记住']), ('拿到', True))
        self.assertEqual(st.flags['记住.role_x'], 1)
        self.assertEqual(st.cnt('交手次数.rival_kup'), 1)

    def test_bomb(self):
        st = bare(1)
        st.attr['名气'] = 100
        r = A.audition(st, self.ROLE, Scripted([0] * 5), [rival([9, 9, 9, 9])])
        self.assertEqual(r['结果'], '演砸')
        self.assertIn(st.attr['名气'], (95, 91))      # -5%，上报再 -5%
        self.assertEqual(st.favor['Sil'], 2)

    def test_big_two_matches(self):
        st = bare(1)
        st.attr['名气'] = 999
        r = A.audition(st, self.ROLE, Scripted([1] * 5), [rival([1, 1, 1, 1]), rival([9, 9, 9, 9])])
        self.assertEqual(len(r['场次']), 2)
        self.assertEqual(r['结果'], '惜败')
        self.assertFalse(r['记住'])
        r = A.audition(st, self.ROLE, Scripted([1] * 5), [rival([9, 9, 9, 9], fame=999), rival([1, 1, 1, 1])])
        self.assertEqual(len(r['场次']), 1)

    def test_classify(self):
        f = lambda s: A.classify(D, s)
        self.assertEqual([f((3, 0)), f((3, 2)), f((2, 3)), f((1, 3)), f((0, 3))], ['记住', '拿到', '惜败', '落选', '演砸'])

    def test_remembered_probs(self):
        self.assertEqual(A.remembered_probs([15, 60, 10, 15], 2, 10), [15, 50, 20, 15])   # 从最高的其他色（情人）扣

    def test_bad_deck(self):
        with self.assertRaises(ValueError):
            A.audition(bare(), self.ROLE, Scripted([1] * 4), [rival([1, 1, 1, 1])])

    def test_reproducible(self):
        def run():
            st = bare(42)
            return [A.audition(st, self.ROLE, A.FixedRandomPlayer([1, 1, 1, 0, 3]),
                               [A.unnamed_rival(st, '中', probs=self.ROLE['场风概率'])])['结果'] for _ in range(30)]
        self.assertEqual(run(), run())


if __name__ == '__main__':
    unittest.main()
