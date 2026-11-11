import unittest
from sim import board, events, film
from sim.story import SimpleAgent, Story
from tests.new.helpers import D, bare


class Yes(SimpleAgent):
    def __init__(self, opt=0, sup=True):
        self.opt, self.sup = opt, sup

    def option(self, st, ev, avail):
        return avail[min(self.opt, len(avail) - 1)]

    def suppress(self, st, kind):
        return self.sup


def st_at(date='1926-03', **attr):
    st = bare()
    st.ym = D.month_index[date]
    st.attr.update({'stamina': 100, 'loyalty': 50, 'discipline': 50, 'crime': 0, 'fatigue': 0, 'fame': 200})
    st.attr.update(attr)
    st.money = 1000
    st.update_indices()
    return st


class TestRunner(unittest.TestCase):
    def test_frequency(self):
        st = st_at('1926-06')
        e = D.events['evt_heatstroke']
        self.assertTrue(events.can_fire(st, e))
        events.fire(Story(), st, e['id'])
        self.assertEqual(st.attr['fatigue'], 10)
        st.ym += 1                                            # no heatstroke again in July of the same year
        self.assertFalse(events.can_fire(st, e))
        st.ym += 11
        self.assertTrue(events.can_fire(st, e))
        e = D.events['evt_swap_role']                         # once per quarter
        events.fire(Story(), st, e['id'])
        st.ym += 1
        self.assertEqual(events.can_fire(st, e), st.ym // 3 != (st.ym - 1) // 3)
        e = D.events['outing_pickup']                         # once only
        st.fired[e['id']] = 1
        self.assertFalse(events.can_fire(st, e))

    def test_options_and_check(self):
        st = st_at()
        events.fire(Story(Yes(0)), st, 'evt_deposit_2000')    # borrow 300
        self.assertEqual((st.money, st.attr['loyalty']), (700, 60))
        st.money = 100                                        # without the money only "don't lend" is possible
        events.fire(Story(Yes(0)), st, 'evt_deposit_2000')
        self.assertEqual((st.money, st.attr['loyalty']), (100, 55))
        st.skill['negotiation'] = 30
        events.fire(Story(), st, 'outing_director_lunch')     # gate check
        self.assertEqual(st.flags.get('knows_director'), 1)

    def test_month_limit_two(self):
        st = st_at('1926-03')
        st.money = 6000                                       # both savings tiers qualify at once
        story = Story()
        events.month_end(story, st)
        self.assertEqual([r['id'] for r in story.log], ['evt_deposit_1000', 'evt_deposit_2000'])


class TestCodeEvents(unittest.TestCase):
    def test_missing(self):
        st = st_at()
        st.corr['tough'] = 100
        f = film.new_film(st, board.placeholder(st, 'small'), [[st.ym + 1, 0]])
        events.fire(Story(), st, 'evt_missing')
        self.assertEqual(st.void_next, 1)
        self.assertEqual(f['status'], 'breached')

    def test_missing_rep_cut(self):
        st = st_at(stamina=0)                                     # stamina adds no displayed value to fight
        for k in st.skill:
            st.skill[k] = 0
        st.corr['tough'] = 200
        events.fire(Story(), st, 'evt_missing')
        self.assertEqual(st.corr['tough'], 200 - 20)

    def test_arrest(self):
        st = st_at()
        events.fire(Story(), st, 'evt_arrest')
        self.assertEqual((st.money, st.attr['crime'], st.exposed), (500, 20, 1))
        st = st_at(loyalty=150)
        events.fire(Story(), st, 'evt_arrest')
        self.assertEqual((st.money, st.attr['loyalty'], st.exposed), (750, 120, 0))
        st = st_at(fatigue=100, stamina=50)                          # a sick player is not arrested
        events.fire(Story(), st, 'evt_arrest')
        self.assertEqual(st.money, 1000)

    def test_scandal(self):
        st = st_at()
        events.fire(Story(), st, 'evt_scandal')
        self.assertEqual(st.attr['fame'], 200 - 30)
        st = st_at(loyalty=200)
        st.flags['warning'] = 1
        events.fire(Story(), st, 'evt_scandal')               # warning doubles it, loyalty halves it: -15%
        self.assertEqual((st.attr['fame'], st.flags['warning']), (170, 0))
        st = st_at()
        st.tags.update({'villain': 2, 'crime': 1})
        events.fire(Story(), st, 'evt_scandal')
        self.assertEqual(st.attr['fame'], 220)
        st = st_at()
        st.flags['free_scandal_cover'] = 1
        events.fire(Story(), st, 'evt_scandal')
        self.assertEqual(st.attr['fame'], 200)
        st.flags['scandal_foresight'] = 1
        events.fire(Story(), st, 'evt_scandal')               # the free one was used this year, pay 200
        self.assertEqual((st.attr['fame'], st.money), (200, 800))

    def test_creditor(self):
        st = st_at(loyalty=150)
        st.money, st.debt_months = -300, 3
        events.fire(Story(), st, 'evt_creditor')
        self.assertEqual((st.money, st.debt_months, st.attr['loyalty']), (0, 0, 120))
        st = st_at()
        st.money, st.debt_months = -300, 3
        st.items += ['gold_watch', 'phonograph']
        events.fire(Story(), st, 'evt_creditor')
        self.assertEqual((st.items, st.money), (['gold_watch'], -200))
        st = st_at(fame=100)
        st.money = -300
        events.fire(Story(), st, 'evt_creditor')
        self.assertEqual((st.attr['fame'], st.exposed), (90, 1))

    def test_contract_decline_waits(self):
        st = st_at(fame=300)
        st.corr['lover'] = 300
        story = Story(Yes(1))
        events.fire(story, st, 'evt_contract')
        self.assertEqual(st.story['contract_refused'], st.ym)
        st.ym += 1
        events.month_end(story, st)
        self.assertNotIn('evt_contract', [r['id'] for r in story.log[1:]])
        events.fire(Story(Yes(0)), st, 'evt_contract')
        self.assertEqual(st.status['long_contract'], 1)

    def test_drug(self):
        st = st_at()
        st.drug = 2
        events.fire(Story(), st, 'evt_drug_deeper')
        self.assertEqual((st.drug, st.attr['stamina'], st.attr['crime']), (3, 70, 20))
        st.favor['sil'] = 60
        events.fire(Story(), st, 'evt_detox')
        self.assertEqual((st.drug, st.favor['sil'], st.void_next), (0, 70, 1))

    def test_opportunity_once(self):
        st = st_at('1928-01')
        st.flags['senior_tier3_savvy'] = 1
        story = Story()
        events.month_end(story, st)
        events.month_end(story, st)
        self.assertEqual([r['id'] for r in story.log].count('opp_senior_shouwan'), 1)
        self.assertEqual(st.corr['savvy'], 10)


class TestScheduleEvents(unittest.TestCase):
    def test_outing_npc_then_table(self):
        st = st_at('1926-03')                                 # mid-March the actress is in the studio area
        story = Story()
        story.cur_period = 1
        self.assertEqual(events.outing(story, st, 'place_studio'), 'outing_actress_dressing')
        self.assertIn('actress', st.known)
        self.assertEqual(events.outing(story, st, 'place_studio'), 'outing_director_lunch')   # chain used up, no resident events
        story.cur_period = 0
        self.assertEqual(events.present(st, 'place_studio', 0), [])

    def test_duv_tip_to_next_board(self):
        st = st_at('1926-03')
        st.favor['duv'] = 30
        st.known.append('duv')
        events.fire(Story(), st, 'outing_duv_tip')
        self.assertEqual(st.story['tipoff'], 1)
        st.ym = D.month_index['1926-04']
        b = board.make(st)
        shown = [e for e in b['roles'] if e['intel'].get('style')]
        self.assertEqual(len(shown), 1)
        self.assertIn(shown[0]['size'], ('medium', 'big'))

    def test_job_milestone_once(self):
        st = st_at()
        st.count['job_periods.job_church'] = 5
        story = Story()
        events.job_period(story, st, 'job_church', True)
        events.job_period(story, st, 'job_church', True)
        self.assertEqual(st.fired['job_church_m1'], 1)
        self.assertEqual(st.weights['religious'], 1)
        self.assertIn('priest', st.known)

    def test_transform(self):
        st = st_at('1926-03')
        st.favor['studio_boss'] = 50
        events.job_period(Story(), st, 'job_studio', True)
        self.assertEqual(st.story['transition'], [3, 'lover_family'])
        st.ym = D.month_index['1926-04']
        es = board.make(st)['roles']
        self.assertEqual(len(es), 6)
        self.assertTrue(set(es[-1]['tags']) & set(D.tag_families['lover_family']))
        self.assertEqual(st.story['transition'][0], 2)

    def test_annual(self):
        st = st_at('1926-12')
        for k in st.skill:
            st.skill[k] = 0
        st.corr['tough'] = 999
        story = Story()
        rec = events.annual(story, st)
        self.assertEqual((rec['occasions'], rec['rank']), ('annual_yinghan', 1))
        self.assertEqual((st.corr['tough'], st.money), (999 + 20, 1000 + 500))

        class Rest(SimpleAgent):
            def annual(self, st, opts): return None
        st.attr['fatigue'] = 50
        events.annual(Story(Rest()), st)
        self.assertEqual(st.attr['fatigue'], 0)

    def test_birthday(self):
        import copy
        from sim.data import Data
        d = copy.copy(D)
        d.events = dict(D.events)
        d.events['evt_birthday'] = dict(D.events['evt_birthday'], date='03-15')
        st = st_at('1926-03')
        st.d = d
        story = Story()
        events.day(story, st, 14)
        events.day(story, st, 15)
        self.assertEqual([r['id'] for r in story.log], ['evt_birthday'])
        self.assertEqual((st.favor['sil'], st.favor['actress']), (3, 3))


if __name__ == '__main__':
    unittest.main()
