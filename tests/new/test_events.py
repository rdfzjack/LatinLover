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
    st.attr.update({'体力': 100, '义气': 50, '自律': 50, '犯罪': 0, '疲劳': 0, '名气': 200})
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
        self.assertEqual(st.attr['疲劳'], 10)
        st.ym += 1                                            # 同一年 7 月不再中暑
        self.assertFalse(events.can_fire(st, e))
        st.ym += 11
        self.assertTrue(events.can_fire(st, e))
        e = D.events['evt_swap_role']                         # 每季度一次
        events.fire(Story(), st, e['id'])
        st.ym += 1
        self.assertEqual(events.can_fire(st, e), st.ym // 3 != (st.ym - 1) // 3)
        e = D.events['outing_pickup']                         # 一次性
        st.fired[e['id']] = 1
        self.assertFalse(events.can_fire(st, e))

    def test_options_and_check(self):
        st = st_at()
        events.fire(Story(Yes(0)), st, 'evt_deposit_2000')    # 借 300
        self.assertEqual((st.money, st.attr['义气']), (700, 60))
        st.money = 100                                        # 钱不够时只能“不借”
        events.fire(Story(Yes(0)), st, 'evt_deposit_2000')
        self.assertEqual((st.money, st.attr['义气']), (100, 55))
        st.skill['谈判'] = 30
        events.fire(Story(), st, 'outing_director_lunch')     # 门槛判定
        self.assertEqual(st.flags.get('认识导演'), 1)

    def test_month_limit_two(self):
        st = st_at('1926-03')
        st.money = 6000                                       # 三档存款同时满足
        story = Story()
        events.month_end(story, st)
        self.assertEqual(len(story.log), 2)
        self.assertEqual([r['id'] for r in story.log], ['evt_deposit_1000', 'evt_deposit_2000'])
        events.month_end(story, st)
        self.assertEqual(story.log[2]['id'], 'evt_deposit_5000')
        self.assertEqual(st.flags['股票'], 1)


class TestCodeEvents(unittest.TestCase):
    def test_missing(self):
        st = st_at()
        st.corr['硬汉'] = 100
        f = film.new_film(st, board.placeholder(st, '小'), [[st.ym + 1, 0]])
        events.fire(Story(), st, 'evt_missing')
        self.assertEqual(st.void_next, 1)
        self.assertEqual(f['状态'], '违约')

    def test_missing_rep_cut(self):
        st = st_at(体力=0)                                     # 体力不给打斗加显示值
        for k in st.skill:
            st.skill[k] = 0
        st.corr['硬汉'] = 200
        events.fire(Story(), st, 'evt_missing')
        self.assertEqual(st.corr['硬汉'], 200 - 20)

    def test_arrest(self):
        st = st_at()
        events.fire(Story(), st, 'evt_arrest')
        self.assertEqual((st.money, st.attr['犯罪'], st.exposed), (500, 20, 1))
        st = st_at(义气=150)
        events.fire(Story(), st, 'evt_arrest')
        self.assertEqual((st.money, st.attr['义气'], st.exposed), (750, 120, 0))
        st = st_at(疲劳=100, 体力=50)                          # 生病不会被捕
        events.fire(Story(), st, 'evt_arrest')
        self.assertEqual(st.money, 1000)

    def test_scandal(self):
        st = st_at()
        events.fire(Story(), st, 'evt_scandal')
        self.assertEqual(st.attr['名气'], 200 - 30)
        st = st_at(义气=200)
        st.flags['警告'] = 1
        events.fire(Story(), st, 'evt_scandal')               # 警告加倍、义气减半：-15%
        self.assertEqual((st.attr['名气'], st.flags['警告']), (170, 0))
        st = st_at()
        st.tags.update({'反派': 2, '犯罪': 1})
        events.fire(Story(), st, 'evt_scandal')
        self.assertEqual(st.attr['名气'], 220)
        st = st_at()
        st.flags['免费压丑闻'] = 1
        events.fire(Story(), st, 'evt_scandal')
        self.assertEqual(st.attr['名气'], 200)
        st.flags['丑闻预知'] = 1
        events.fire(Story(), st, 'evt_scandal')               # 免费的今年用过了，花 200
        self.assertEqual((st.attr['名气'], st.money), (200, 800))

    def test_creditor(self):
        st = st_at(义气=150)
        st.money, st.debt_months = -300, 3
        events.fire(Story(), st, 'evt_creditor')
        self.assertEqual((st.money, st.debt_months, st.attr['义气']), (0, 0, 120))
        st = st_at()
        st.money, st.debt_months = -300, 3
        st.items += ['怀表', '留声机']
        events.fire(Story(), st, 'evt_creditor')
        self.assertEqual((st.items, st.money), (['怀表'], -200))
        st = st_at(名气=100)
        st.money = -300
        events.fire(Story(), st, 'evt_creditor')
        self.assertEqual((st.attr['名气'], st.exposed), (90, 1))

    def test_contract_decline_waits(self):
        st = st_at(名气=300)
        st.corr['情人'] = 300
        story = Story(Yes(1))
        events.fire(story, st, 'evt_contract')
        self.assertEqual(st.story['长约拒绝'], st.ym)
        st.ym += 1
        events.month_end(story, st)
        self.assertNotIn('evt_contract', [r['id'] for r in story.log[1:]])
        events.fire(Story(Yes(0)), st, 'evt_contract')
        self.assertEqual(st.status['长约'], 1)

    def test_drug(self):
        st = st_at()
        st.drug = 2
        events.fire(Story(), st, 'evt_drug_deeper')
        self.assertEqual((st.drug, st.attr['体力'], st.attr['犯罪']), (3, 70, 20))
        st.favor['Sil'] = 60
        events.fire(Story(), st, 'evt_detox')
        self.assertEqual((st.drug, st.favor['Sil'], st.void_next), (0, 70, 1))

    def test_crash(self):
        st = st_at()
        st.stock = 3000
        events.fire(Story(), st, 'era_crash')
        self.assertEqual((st.stock, st.flags.get('幸存者')), (300, None))
        st = st_at()
        st.money = 5000
        events.fire(Story(), st, 'era_crash')
        self.assertEqual(st.flags['幸存者'], 1)

    def test_opportunity_once(self):
        st = st_at('1928-01')
        st.flags['前辈三档_手腕'] = 1
        story = Story()
        events.month_end(story, st)
        events.month_end(story, st)
        self.assertEqual([r['id'] for r in story.log].count('opp_senior_shouwan'), 1)
        self.assertEqual(st.corr['手腕'], 10)


class TestScheduleEvents(unittest.TestCase):
    def test_outing_npc_then_table(self):
        st = st_at('1926-03')                                 # 3 月中旬女明星在片厂区
        story = Story()
        story.cur_period = 1
        self.assertEqual(events.outing(story, st, 'place_studio'), 'outing_actress_dressing')
        self.assertIn('女明星', st.known)
        self.assertEqual(events.outing(story, st, 'place_studio'), 'outing_director_lunch')   # 链看完了，没有常驻
        story.cur_period = 0
        self.assertEqual(events.present(st, 'place_studio', 0), [])

    def test_duv_tip_to_next_board(self):
        st = st_at('1926-03')
        st.favor['Duv'] = 30
        st.known.append('Duv')
        events.fire(Story(), st, 'outing_duv_tip')
        self.assertEqual(st.story['告密'], 1)
        st.ym = D.month_index['1926-04']
        b = board.make(st)
        shown = [e for e in b['角色'] if e['情报'].get('场风')]
        self.assertEqual(len(shown), 1)
        self.assertIn(shown[0]['档次'], ('中', '大'))

    def test_job_milestone_once(self):
        st = st_at()
        st.count['成功期数.job_church'] = 5
        story = Story()
        events.job_period(story, st, 'job_church', True)
        events.job_period(story, st, 'job_church', True)
        self.assertEqual(st.fired['job_church_m1'], 1)
        self.assertEqual(st.weights['宗教'], 1)
        self.assertIn('神父', st.known)

    def test_transform(self):
        st = st_at('1926-03')
        st.favor['片厂老板'] = 50
        events.job_period(Story(), st, 'job_studio', True)
        self.assertEqual(st.story['转型'], [3, '情人系'])
        st.ym = D.month_index['1926-04']
        es = board.make(st)['角色']
        self.assertEqual(len(es), 6)
        self.assertTrue(set(es[-1]['标签']) & set(D.tag_families['情人系']))
        self.assertEqual(st.story['转型'][0], 2)

    def test_annual(self):
        st = st_at('1926-12')
        for k in st.skill:
            st.skill[k] = 0
        st.corr['硬汉'] = 999
        story = Story()
        rec = events.annual(story, st)
        self.assertEqual((rec['场合'], rec['名次']), ('annual_yinghan', 1))
        self.assertEqual((st.corr['硬汉'], st.money), (999 + 20, 1000 + 500))

        class Rest(SimpleAgent):
            def annual(self, st, opts): return None
        st.attr['疲劳'] = 50
        events.annual(Story(Rest()), st)
        self.assertEqual(st.attr['疲劳'], 0)

    def test_birthday(self):
        import copy
        from sim.data import Data
        d = copy.copy(D)
        d.events = dict(D.events)
        d.events['evt_birthday'] = dict(D.events['evt_birthday'], 日期='03-15')
        st = st_at('1926-03')
        st.d = d
        story = Story()
        events.day(story, st, 14)
        events.day(story, st, 15)
        self.assertEqual([r['id'] for r in story.log], ['evt_birthday'])
        self.assertEqual((st.favor['Sil'], st.favor['女明星']), (3, 3))


if __name__ == '__main__':
    unittest.main()
