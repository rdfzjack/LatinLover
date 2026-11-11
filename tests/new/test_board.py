import unittest
from sim import audition, board, film
from sim.story import SimpleAgent
from tests.new.helpers import D, bare


def st_at(date, **attr):
    st = bare()
    st.ym = D.month_index[date]
    st.attr.update({'fame': 100, 'crime': 0})
    st.attr.update(attr)
    for k in st.skill:
        st.skill[k] = 0
    return st


class Picker(SimpleAgent):
    """Signs up in the given order; plays the first card every time."""
    def __init__(self, order=(), colors=(1, 1, 1, 1, 1)):
        self.order, self.colors = list(order), list(colors)

    def deck(self, st, ctx):
        return self.colors

    def play(self, st, ctx):
        return 0

    def pick_role(self, st, b, ok):
        while self.order:
            i = self.order.pop(0)
            if i in ok:
                return i
        return None


class TestCompose(unittest.TestCase):
    def test_counts(self):
        st = st_at('1926-04')
        b = board.make(st)
        self.assertEqual([e['size'] for e in b['roles']], ['big', 'medium', 'medium', 'small', 'small'])
        st = st_at('1926-04')
        st.skill['connections'] = 50
        self.assertEqual([e['size'] for e in board.make(st)['roles']], ['big', 'medium', 'medium', 'medium', 'small', 'small'])
        st = st_at('1926-04')
        st.skill['connections'] = 80
        self.assertEqual([e['size'] for e in board.make(st)['roles']], ['big', 'big', 'medium', 'medium', 'medium', 'small', 'small'])

    def test_rivals_and_road(self):
        st = st_at('1926-04')
        for e in board.make(st)['roles']:
            self.assertEqual(len(e['opponents']), 2 if e['size'] == 'big' else 1)
            self.assertIn(e['road'], D.roads)
            self.assertEqual(sum(e['style_probs']), 100)
            if e['size'] == 'big':
                self.assertIsNone(e['opponents'][0]['id'])
                self.assertIsNotNone(e['opponents'][1]['id'])

    def test_tutorial(self):
        st = st_at('1926-01')
        st.corr['culture'] = 50                                   # the player's highest reputation is culture
        b = board.make(st)
        tut = [e for e in b['roles'] if e['source'] == 'tutorial']
        self.assertEqual(len(tut), 1)
        t = tut[0]
        self.assertEqual(t['style_probs'], [14, 13, 60, 13])
        rv = t['opponents'][0]
        self.assertEqual(rv['levels'][2], 2)

    def test_repeat_limit(self):
        st = st_at('1926-04')
        seen = {}
        for _ in range(12):
            for e in board.make(st)['roles']:
                seen[e['id']] = seen.get(e['id'], 0) + 1
        for rid, n in seen.items():
            if rid in D.roles:
                self.assertLessEqual(n, 1 if D.roles[rid]['size'] == 'big' else 2, rid)

    def test_talkie_ratio(self):
        st = st_at('1927-07')
        self.assertFalse(any(e['talkie'] for e in board.make(st)['roles']))
        st = st_at('1927-10')
        es = board.make(st)['roles']
        self.assertEqual(sum(1 for e in es if e['talkie']), 1)
        t = next(e for e in es if e['talkie'])
        self.assertEqual(t['speech_line'], {'small': 30, 'medium': 50, 'big': 70}[t['size']])

    def test_valen_extra(self):
        st = st_at('1927-10')
        st.flags['valen_dead'] = 1
        es = board.make(st)['roles']
        self.assertEqual(len(es), 6)
        self.assertTrue(set(es[-1]['tags']) & {'exotic_lover', 'romance'})
        st = st_at('1929-01')
        st.flags['valen_dead'] = 1
        self.assertEqual(len(board.make(st)['roles']), 5)

    def test_remembered(self):
        st = st_at('1926-04')
        for rid in ('role_sheikh_son', 'role_swordsman'):     # only these two big films are in the pool
            st.flags['remembered.' + rid] = 1
        st.corr['tough'] = 100                                  # player's main color tough
        e = next(x for x in board.make(st)['roles'] if x['size'] == 'big')
        self.assertEqual(e['style_probs'], audition.remembered_probs(e['base_style'], 0, 10))
        self.assertNotEqual(e['style_probs'], e['base_style'])
        self.assertEqual(st.flags['remembered.' + e['id']], 0)

    def test_weights_on_small(self):
        st = st_at('1926-04')
        st.weights['crime'] = 5                                 # counts at most 2
        r = D.roles['role_boxer']
        self.assertEqual(board.role_weight(st, r), 3)


class TestEligibility(unittest.TestCase):
    def test_gates(self):
        st = st_at('1926-04', fame=260)
        b = board.make(st)
        big = next(e for e in b['roles'] if e['size'] == 'big')
        self.assertIsNone(board.eligible(st, big))
        st.count['count.lowbudget'] = 4                             # low-budget typed: big-film gate +50
        self.assertEqual(board.eligible(st, big), 'out_of_reach')
        st.count['count.lowbudget'] = 0
        st.attr['crime'] = 300
        self.assertEqual(board.eligible(st, big), 'morals')

    def test_contract_studio_roles(self):
        st = st_at('1926-04', fame=300)
        st.status['long_contract'] = 1
        b = board.make(st)
        mine = [e for e in b['roles'] if e['house']]
        self.assertEqual(len(mine), 3)
        for e in b['roles']:
            if not e['house']:
                self.assertEqual(board.eligible(st, e), 'not a house role')

    def test_two_tries_lower_tier(self):
        st = st_at('1926-04', fame=300)
        b = board.make(st)
        tiers = [e['size'] for e in b['roles']]
        mid = tiers.index('medium')
        small = tiers.index('small')
        big = tiers.index('big')
        b['tried'] = [mid]
        self.assertEqual(board.can_try(st, big), 'the second try must be a lower size than the first')
        self.assertEqual(board.can_try(st, mid + 1), 'the second try must be a lower size than the first')
        self.assertIsNone(board.can_try(st, small))
        b['tried'] = [mid, small]
        self.assertEqual(board.can_try(st, small + 1), 'this board was already tried twice')

    def test_run_gets_one_film(self):
        st = st_at('1926-04', fame=300)
        st.corr['lover'] = 500                                  # level 9, pure lover cards
        board.make(st)
        out = board.run(st, Picker(order=[3, 4]))
        self.assertEqual(out[0]['result'], 'won')
        self.assertEqual(len(out), 1)
        f = film.films(st)[0]
        n = D.role_cfg['shoot_periods'][f['size']]
        self.assertEqual(f['locks'], [[st.ym + 1, k] for k in range(n)])
        self.assertEqual(st.story['board']['won'], 3)


class TestScripts(unittest.TestCase):
    def test_self_and_duv(self):
        st = st_at('1927-02', education=300)
        st.skill['writing'] = 80
        self.assertTrue(board.script_ok(st, 'self_written'))
        self.assertFalse(board.script_ok(st, 'duv_written'))
        board.write_script(st, 'self_written', 3)
        self.assertFalse(board.script_ok(st, 'self_written'))         # once per year
        r = st.story['pending_board'][0]
        self.assertEqual((r['size'], r['style_probs']), ('medium', [14, 13, 13, 60]))
        st.flags['duv_writes_script'] = 1
        st.favor['duv'] = 80
        self.assertFalse(board.script_ok(st, 'co_written'))           # already self-written this year
        board.write_script(st, 'duv_written')
        self.assertEqual(st.favor['duv'], 83)
        r = st.story['pending_board'][1]
        self.assertEqual([k['stat'] for k in r['wants']], ['education', 'looks'])
        st.ym += 12
        self.assertTrue(board.script_ok(st, 'co_written'))
        board.write_script(st, 'co_written', 1)
        self.assertFalse(board.script_ok(st, 'self_written'))
        self.assertFalse(board.script_ok(st, 'co_written'))
        es = board.make(st)['roles']
        extra = [e for e in es if e['source'] == 'script']
        self.assertEqual([e['size'] for e in extra], ['medium', 'medium', 'big'])
        self.assertEqual(len(extra[2]['opponents']), 2)


if __name__ == '__main__':
    unittest.main()
