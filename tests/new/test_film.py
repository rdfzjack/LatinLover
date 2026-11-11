import unittest
from sim import board, film
from sim.schedule import days_of
from tests.new.helpers import D, bare


def role(tier='medium', tags=('western',), want=(('stamina', 200),), talkie=False, probs=(50, 20, 20, 10)):
    return {'id': 'r', 'name': 'r', 'size': tier, 'style_probs': list(probs), 'base_style': list(probs), 'road': 'tough',
            'wants': [{'stat': k, 'target': v} for k, v in want], 'tags': list(tags), 'bonus_skill': 'acting', 'talkie': talkie,
            'speech_line': {'small': 30, 'medium': 50, 'big': 70}[tier] if talkie else None,
            'fee': D.role_cfg['fee'][tier], 'lead': None}


def st0():
    st = bare()
    st.attr.update({'stamina': 200, 'education': 200, 'fame': 100, 'fatigue': 0, 'discipline': 100})
    st.ym = 1
    st.update_indices()
    return st


class TestFilm(unittest.TestCase):
    def test_locks_and_status(self):
        st = st0()
        self.assertEqual(film.board_locks(st, 'big'), [[2, 0], [2, 1], [2, 2]])
        self.assertEqual(film.board_locks(st, 'medium', support=True), [[2, 0]])
        self.assertEqual(film.board_locks(st, 'small', support=True), [[2, 0]])
        f = film.new_film(st, role(), film.board_locks(st, 'medium'))
        self.assertEqual(st.status['has_pending_role'], 1)
        st.ym = 2
        self.assertIs(film.locked(st, 1), f)
        self.assertIsNone(film.locked(st, 2))
        self.assertEqual(film.next_period(st, 2), [3, 0])

    def test_shoot_fee_release_timing(self):
        st = st0()
        st.skill['acting'] = 50
        st.skill['negotiation'] = 40
        f = film.new_film(st, role(), film.board_locks(st, 'medium'))
        st.ym = 2
        m0 = st.money
        for i in range(2):
            film.shoot(st, i, f, days_of(st, i))
        days = sum(1 for _, s in days_of(st, 0) + days_of(st, 1) if not s)
        self.assertEqual(f['shoot_days'], days)
        self.assertEqual(f['ok_days'], days)                     # stamina 200, fatigue low, succeeds every day
        self.assertEqual(f['perf'], 500 + 500 + 50 * 2)         # P = 1.1
        self.assertEqual(f['fee'], 800 * (600 + 40) // 600)           # education >= 100, no contract discount
        self.assertEqual(st.money, m0 + f['fee'])
        self.assertEqual(f['status'], 'to_release')
        self.assertEqual(f['release'], 4)
        self.assertEqual(st.attr['fatigue'], 3 * days)
        self.assertEqual(st.exposed, 1)

    def test_contract_discount_and_support(self):
        st = st0()
        st.attr['education'] = 50
        st.skill['negotiation'] = 0
        f = film.new_film(st, role('big'), [[2, 0]], support=True)
        self.assertEqual(film.fee(st, f), 2500 * 40 // 100 * 85 // 100)
        st.favor['sil'] = 50                                   # Sil favor >= 50 exempts
        self.assertEqual(film.fee(st, f), 2500 * 40 // 100)
        f['stunt_self'] = True
        f['support'] = False
        self.assertEqual(film.fee(st, f), 2500 * 130 // 100)

    def test_personally(self):
        st = st0()
        st.skill['nerve'] = 55
        self.assertFalse(film.can_go_personally(st, role(tags=('western',))))
        st.flags['stunt_line_50'] = 1
        self.assertTrue(film.can_go_personally(st, role(tags=('western',))))
        self.assertFalse(film.can_go_personally(st, role(tags=('romance',))))

    def _released(self, st, r, P=1000, support=False):
        f = film.new_film(st, r, [[0, 0]], support=support)
        f.update({'status': 'to_release', 'release': st.ym, 'perf': P, 'shoot_days': 1, 'ok_days': 1})
        film.release(st)
        return f['result']

    def test_release_plain(self):
        st = st0()
        r = role(want=(('stamina', 200),))                         # fit 1.0
        res = self._released(st, r)
        self.assertEqual((res['F'], res['T'], res['S']), (1000, 1000, 100000))
        self.assertEqual(res['fame'], 30)
        self.assertEqual(res['dividend'], 200)
        self.assertEqual(st.corr['tough'], 4)
        self.assertEqual(st.tags['western'], 1)
        self.assertEqual(st.cnt('count.lowbudget'), 0)               # medium film -1, minimum 0
        self.assertEqual(st.attr['fame'], 130)

    def test_release_hit_and_flop(self):
        st = st0()
        st.attr['stamina'] = 300                                   # fit 1.2
        st.tags['western'] = 3                                     # typed: T at full 1.15
        res = self._released(st, role(), P=1200)
        self.assertEqual(res['S'], 100 * 1200 * 1200 * 1150 // 1000000)
        self.assertTrue(res['hit'])
        self.assertEqual(st.corr['tough'], 8)                    # hit doubles
        st = st0()
        st.attr['stamina'] = 50                                    # fit 0.7
        res = self._released(st, role(), P=500)
        self.assertTrue(res['flop'])
        self.assertEqual(res['rep_bonus'], 0)
        self.assertEqual(res['fame'], res['S'] * 30 // 100000 // 2)

    def test_typecast_penalty_and_low_budget(self):
        st = st0()
        st.tags['romance'] = 3                                     # typed on another tag
        res = self._released(st, role())
        self.assertTrue(res['untyped'])
        self.assertEqual(res['S'], 100000 * 90 // 100)
        st = st0()
        st.count['count.lowbudget'] = 4
        res = self._released(st, role('small'))
        self.assertEqual(res['T'], 1150)                        # small film of low-budget typed: T at full
        self.assertEqual(st.cnt('count.lowbudget'), 5)

    def test_support_release(self):
        st = st0()
        res = self._released(st, role(), support=True)
        self.assertEqual(res['fame'], 30 * 30 // 100)
        self.assertEqual(st.corr['tough'], 5 * 30 // 100)
        self.assertEqual(st.tags['western'], 1)
        self.assertEqual(st.cnt('count.support'), 1)

    def test_talkie(self):
        st = st0()
        st.skill['speech'] = 30
        res = self._released(st, role(talkie=True))
        self.assertTrue(res['accent'])
        self.assertEqual(res['S'], 100000 * 60 // 100)
        self.assertEqual(st.flags['accent_pending'], 1)
        self.assertEqual(st.cnt('count.talkie_count'), 1)
        st = st0()
        st.skill['speech'] = 40
        st.flags['talkie_speech_line_minus_10'] = 1
        self.assertFalse(self._released(st, role(talkie=True))['accent'])

    def test_breach(self):
        st = st0()
        f = film.new_film(st, role(), film.board_locks(st, 'medium'))
        st.attr['fame'] = 200
        film.breach_month(st, 2)
        self.assertEqual(f['status'], 'breached')
        self.assertEqual(st.attr['fame'], 180)
        self.assertEqual(st.status['has_pending_role'], 0)


if __name__ == '__main__':
    unittest.main()
