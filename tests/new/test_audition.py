import unittest
from sim import audition as A
from tests.new.helpers import D, bare


class Scripted(A.Player):
    """Fixed deck, plays in the given order (indexes into the remaining hand)."""
    def __init__(self, colors, picks=None):
        self.colors, self.picks = colors, list(picks or [])

    def deck(self, st, ctx):
        return self.colors

    def play(self, st, ctx):
        return self.picks.pop(0) if self.picks else 0


def rival(levels, k=5, habit='habit_random', fame=100, rid=None):
    return {'id': rid, 'name': 'x', 'levels': levels, 'fame': fame, 'habit': habit, 'k': k}


class TestPoints(unittest.TestCase):
    def test_build_deck(self):
        self.assertEqual(A.build_deck([3, 6, 1, 1], [1, 1, 0, 1, 0]), [(1, 6), (1, 5), (0, 3), (1, 4), (0, 2)])
        self.assertEqual(A.build_deck([1, 1, 1, 1], [0, 0, 0]), [(0, 1), (0, 0), (0, 0)])

    def test_effective(self):
        # style x1.3; tough counters lover x1.3 / x0.8; the style color is not countered
        self.assertEqual(A.effective(D, (1, 6), (1, 6), 1), (780, 780))
        self.assertEqual(A.effective(D, (0, 6), (1, 6), 2), (780, 480))
        self.assertEqual(A.effective(D, (0, 6), (1, 6), 1), (600, 780))
        self.assertEqual(A.effective(D, (0, 6), (1, 6), 0), (1014, 480))
        self.assertEqual(A.effective(D, (0, 5), (2, 5), 3), (500, 500))   # the two opposite colors are unrelated
        self.assertEqual(A.effective(D, (3, 4), (0, 8), 1), (520, 640))    # savvy counters tough

    def test_tie(self):
        self.assertFalse(A.round_winner(D, (1, 6), (1, 6), 1, 100, 100))
        self.assertTrue(A.round_winner(D, (1, 6), (1, 6), 1, 101, 100))


class TestTable77(unittest.TestCase):
    """GDD 7.7: samples the complete match() (style drawn by the role's probabilities, rival deck built by 7.5, both sides random)
        and stays within 3 percentage points of the exactly enumerated win rate."""

    def check(self, fame_hi):
        st = bare(5)
        st.attr['fame'] = 200 if fame_hi else 0
        rv = A.opp_77(D)
        for name, deck_name, exact, on, off, cols in A.table_77(D, fame_hi):
            lv = dict(A.CASES_77)[name]
            n = 3000
            w = sum(A.match(st, A.build_deck(lv, cols), rv, A.ROLE_77, A.FixedRandomPlayer(cols))['score_line'][0] == 3
                    for _ in range(n))
            self.assertAlmostEqual(w / n, exact, delta=0.03, msg=name)

    def test_fame_low(self):
        self.check(False)

    def test_fame_high(self):
        self.check(True)

    def test_shape(self):
        """Shape of the table: on the same road the level difference decides, fame only matters on equal points."""
        t = {r[0]: r[2] for r in A.table_77(D)}
        self.assertLess(t['same road, 1 level lower'], 0.05)
        self.assertLess(t['same road, same level'], t['same road, 1 level higher'])
        self.assertLess(t['same road, 1 level higher'], t['same road, 2 levels higher'])
        self.assertGreater(t['same road, 2 levels higher'], 0.85)


class TestOpponent(unittest.TestCase):
    def test_deck_formula(self):
        # levels [5,9,2,3], style [15,60,10,15]: lover is the main color; the second color is the counter of counter (tough, which counters lover, is countered by savvy)
        rv = rival([5, 9, 2, 3], k=4)
        self.assertEqual(A.opponent_deck(D, rv, [15, 60, 10, 15]), [(1, 9), (1, 8), (1, 7), (1, 6), (3, 3)])
        self.assertEqual([A.guard_color(D, c) for c in range(4)], [2, 3, 0, 1])
        # 5 x (1 + 0.3x5%) = 5.075 is still above 4 x (1 + 0.3x60%) = 4.72; at equal level the style probability decides
        self.assertEqual(A.opponent_colors(D, [5, 1, 4, 1], [5, 30, 60, 5]), (0, 2))
        self.assertEqual(A.opponent_colors(D, [5, 1, 5, 1], [5, 30, 60, 5]), (2, 0))

    def test_unnamed(self):
        st = bare(3)
        st.ym = 0
        for _ in range(50):
            r = A.unnamed_rival(st, 'small', probs=[10, 60, 10, 20])
            self.assertIn(r['levels'][1], (1, 2))
            self.assertEqual(r['fame'], 40)
            self.assertEqual(r['k'], 3)
            self.assertEqual(r['levels'][0], 1)   # the second color is savvy (counter of counter), the rest are level 1
            self.assertEqual(r['levels'][2], 1)
        st.ym = 47   # h = 7: main 2 + 7/3 = 4, random -1..0
        ls = {A.unnamed_rival(st, 'small', probs=[10, 60, 10, 20])['levels'][1] for _ in range(100)}
        self.assertEqual(ls, {3, 4})
        r = A.unnamed_rival(st, 'big', main_level=7, probs=[15, 60, 10, 15])
        self.assertEqual(r['levels'], [1, 7, 1, 5])
        self.assertEqual(r['fame'], 300 + 15 * 7)
        # medium rival: base 4, +1 level at 1926-10, 1927-07 and 1928-07, random -1..+1
        st.ym = D.month_index['1928-07']
        self.assertIn(A.unnamed_rival(st, 'medium', probs=[15, 60, 10, 15])['levels'][1], (6, 7, 8))

    def test_named(self):
        st = bare()
        st.ym = D.month_index['1927-03']
        r = A.named_rival(st, 'rival_jilbo')
        self.assertEqual((r['levels'], r['fame']), ([4, 8, 3, 2], 650))
        st.ym = D.month_index['1929-02']
        self.assertEqual(A.named_rival(st, 'rival_fanban')['levels'], [8, 5, 3, 8])
        self.assertEqual(A.named_rival(st, 'rival_fanban')['fame'], 750)   # fame carried over
        st.ym = D.month_index['1927-08']
        self.assertEqual(A.named_rival(st, 'rival_valen')['id'], 'rival_valen')
        st.ym = D.month_index['1927-09']
        self.assertIn(A.named_rival(st, 'rival_valen')['id'], ('rival_nova', 'rival_jilbo'))
        self.assertFalse(A.rival_present(st, 'rival_valen'))
        self.assertFalse(A.rival_present(st, 'rival_jolson'))


class TestHabits(unittest.TestCase):
    def picks(self, habit, rnd=0, my_last=None, score=(0, 0), hand=None):
        st = bare(9)
        hand = hand or [(1, 6), (1, 5), (1, 4), (0, 6), (2, 1)]   # style lover: 780 650 520 600 100
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
        self.assertEqual(self.picks('habit_follow', rnd=0)[0], 3)            # the middle card: 600
        self.assertEqual(self.picks('habit_follow', rnd=1, my_last=(1, 4))[0], 3)   # smallest that beats 520: tough 600 (the style color is not countered)
        self.assertEqual(self.picks('habit_follow', rnd=1, my_last=(1, 9))[0], 4)   # cannot win: play the smallest
        self.assertEqual(self.picks('habit_score', score=(1, 1))[0], 0)
        self.assertEqual(self.picks('habit_score', score=(0, 1))[0], 4)
        _, rate = self.picks('habit_random')
        self.assertLess(rate, 0.3)


class TestAudition(unittest.TestCase):
    ROLE = {'id': 'role_x', 'style_probs': [10, 60, 10, 20]}

    def test_win_remembered(self):
        st = bare(1)
        r = A.audition(st, self.ROLE, Scripted([1] * 5), [rival([1, 1, 1, 1], rid='rival_kup')])
        self.assertEqual((r['result'], r['remembered']), ('won', True))
        self.assertEqual(st.flags['remembered.role_x'], 1)
        self.assertEqual(st.cnt('duels.rival_kup'), 1)

    def test_bomb(self):
        st = bare(1)
        st.attr['fame'] = 100
        r = A.audition(st, self.ROLE, Scripted([0] * 5), [rival([9, 9, 9, 9])])
        self.assertEqual(r['result'], 'botched')
        self.assertIn(st.attr['fame'], (95, 91))      # -5%, then -5% again for the report
        self.assertEqual(st.favor['sil'], 2)

    def test_big_two_matches(self):
        st = bare(1)
        st.attr['fame'] = 999
        r = A.audition(st, self.ROLE, Scripted([1] * 5), [rival([1, 1, 1, 1]), rival([9, 9, 9, 9])])
        self.assertEqual(len(r['rounds']), 2)
        self.assertEqual(r['result'], 'narrow_loss')
        self.assertFalse(r['remembered'])
        r = A.audition(st, self.ROLE, Scripted([1] * 5), [rival([9, 9, 9, 9], fame=999), rival([1, 1, 1, 1])])
        self.assertEqual(len(r['rounds']), 1)

    def test_classify(self):
        f = lambda s: A.classify(D, s)
        self.assertEqual([f((3, 0)), f((3, 2)), f((2, 3)), f((1, 3)), f((0, 3))], ['remembered', 'won', 'narrow_loss', 'lost', 'botched'])

    def test_remembered_probs(self):
        self.assertEqual(A.remembered_probs([15, 60, 10, 15], 2, 10), [15, 50, 20, 15])   # taken from the highest other color (lover)

    def test_bad_deck(self):
        with self.assertRaises(ValueError):
            A.audition(bare(), self.ROLE, Scripted([1] * 4), [rival([1, 1, 1, 1])])

    def test_reproducible(self):
        def run():
            st = bare(42)
            return [A.audition(st, self.ROLE, A.FixedRandomPlayer([1, 1, 1, 0, 3]),
                               [A.unnamed_rival(st, 'medium', probs=self.ROLE['style_probs'])])['result'] for _ in range(30)]
        self.assertEqual(run(), run())


if __name__ == '__main__':
    unittest.main()
