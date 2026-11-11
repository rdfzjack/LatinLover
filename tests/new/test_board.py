import unittest
from sim import audition, board, film
from sim.story import SimpleAgent
from tests.new.helpers import D, bare


def st_at(date, **attr):
    st = bare()
    st.ym = D.month_index[date]
    st.attr.update({'名气': 100, '犯罪': 0})
    st.attr.update(attr)
    for k in st.skill:
        st.skill[k] = 0
    return st


class Picker(SimpleAgent):
    """按给定顺序报名；出牌固定第一张。"""
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
        self.assertEqual([e['档次'] for e in b['角色']], ['大', '中', '中', '小', '小'])
        st = st_at('1926-04')
        st.skill['人脉'] = 50
        self.assertEqual([e['档次'] for e in board.make(st)['角色']], ['大', '中', '中', '中', '小', '小'])
        st = st_at('1926-04')
        st.skill['人脉'] = 80
        self.assertEqual([e['档次'] for e in board.make(st)['角色']], ['大', '大', '中', '中', '中', '小', '小'])

    def test_rivals_and_road(self):
        st = st_at('1926-04')
        for e in board.make(st)['角色']:
            self.assertEqual(len(e['对手']), 2 if e['档次'] == '大' else 1)
            self.assertIn(e['路'], D.roads)
            self.assertEqual(sum(e['场风概率']), 100)
            if e['档次'] == '大':
                self.assertIsNone(e['对手'][0]['id'])
                self.assertIsNotNone(e['对手'][1]['id'])

    def test_tutorial(self):
        st = st_at('1926-01')
        st.corr['文化'] = 50                                   # 玩家最高声望在文化
        b = board.make(st)
        tut = [e for e in b['角色'] if e['来源'] == '教学']
        self.assertEqual(len(tut), 1)
        t = tut[0]
        self.assertEqual(t['场风概率'], [14, 13, 60, 13])
        rv = t['对手'][0]
        self.assertEqual(rv['等级'][2], 2)

    def test_repeat_limit(self):
        st = st_at('1926-04')
        seen = {}
        for _ in range(12):
            for e in board.make(st)['角色']:
                seen[e['id']] = seen.get(e['id'], 0) + 1
        for rid, n in seen.items():
            if rid in D.roles:
                self.assertLessEqual(n, 1 if D.roles[rid]['档次'] == '大' else 2, rid)

    def test_talkie_ratio(self):
        st = st_at('1927-07')
        self.assertFalse(any(e['有声'] for e in board.make(st)['角色']))
        st = st_at('1927-10')
        es = board.make(st)['角色']
        self.assertEqual(sum(1 for e in es if e['有声']), 1)
        t = next(e for e in es if e['有声'])
        self.assertEqual(t['谈吐线'], {'小': 30, '中': 50, '大': 70}[t['档次']])

    def test_valen_extra(self):
        st = st_at('1927-10')
        st.flags['瓦伦去世'] = 1
        es = board.make(st)['角色']
        self.assertEqual(len(es), 6)
        self.assertTrue(set(es[-1]['标签']) & {'异国情人', '浪漫'})
        st = st_at('1929-01')
        st.flags['瓦伦去世'] = 1
        self.assertEqual(len(board.make(st)['角色']), 5)

    def test_remembered(self):
        st = st_at('1926-04')
        for rid in ('role_sheikh_son', 'role_swordsman'):     # 池里只有这两个大片
            st.flags['记住.' + rid] = 1
        st.corr['硬汉'] = 100                                  # 玩家主色 硬汉
        e = next(x for x in board.make(st)['角色'] if x['档次'] == '大')
        self.assertEqual(e['场风概率'], audition.remembered_probs(e['基础场风'], 0, 10))
        self.assertNotEqual(e['场风概率'], e['基础场风'])
        self.assertEqual(st.flags['记住.' + e['id']], 0)

    def test_weights_on_small(self):
        st = st_at('1926-04')
        st.weights['犯罪'] = 5                                 # 最多算 2
        r = D.roles['role_boxer']
        self.assertEqual(board.role_weight(st, r), 3)


class TestEligibility(unittest.TestCase):
    def test_gates(self):
        st = st_at('1926-04', 名气=260)
        b = board.make(st)
        big = next(e for e in b['角色'] if e['档次'] == '大')
        self.assertIsNone(board.eligible(st, big))
        st.count['计数.低成本'] = 4                             # 低成本定型：大片门槛 +50
        self.assertEqual(board.eligible(st, big), '够不着')
        st.count['计数.低成本'] = 0
        st.attr['犯罪'] = 300
        self.assertEqual(board.eligible(st, big), '道德条款')

    def test_contract_studio_roles(self):
        st = st_at('1926-04', 名气=300)
        st.status['长约'] = 1
        b = board.make(st)
        mine = [e for e in b['角色'] if e['本厂']]
        self.assertEqual(len(mine), 3)
        for e in b['角色']:
            if not e['本厂']:
                self.assertEqual(board.eligible(st, e), '不是本厂的角色')

    def test_two_tries_lower_tier(self):
        st = st_at('1926-04', 名气=300)
        b = board.make(st)
        tiers = [e['档次'] for e in b['角色']]
        mid = tiers.index('中')
        small = tiers.index('小')
        big = tiers.index('大')
        b['试过'] = [mid]
        self.assertEqual(board.can_try(st, big), '第二次的档次必须比第一次低')
        self.assertEqual(board.can_try(st, mid + 1), '第二次的档次必须比第一次低')
        self.assertIsNone(board.can_try(st, small))
        b['试过'] = [mid, small]
        self.assertEqual(board.can_try(st, small + 1), '这块板已经试过两次')

    def test_run_gets_one_film(self):
        st = st_at('1926-04', 名气=300)
        st.corr['情人'] = 500                                  # 9 级，纯情人牌
        board.make(st)
        out = board.run(st, Picker(order=[3, 4]))
        self.assertEqual(out[0]['结果'], '拿到')
        self.assertEqual(len(out), 1)
        f = film.films(st)[0]
        n = D.role_cfg['拍摄旬数'][f['档次']]
        self.assertEqual(f['锁'], [[st.ym + 1, k] for k in range(n)])
        self.assertEqual(st.story['板']['拿到'], 3)


class TestScripts(unittest.TestCase):
    def test_self_and_duv(self):
        st = st_at('1927-02', 教育=300)
        st.skill['创作'] = 80
        self.assertTrue(board.script_ok(st, '自己写'))
        self.assertFalse(board.script_ok(st, 'Duv写'))
        board.write_script(st, '自己写', 3)
        self.assertFalse(board.script_ok(st, '自己写'))         # 每年一次
        r = st.story['待上板'][0]
        self.assertEqual((r['档次'], r['场风概率']), ('中', [14, 13, 13, 60]))
        st.flags['Duv写剧本'] = 1
        st.favor['Duv'] = 80
        self.assertFalse(board.script_ok(st, '合写'))           # 当年已经自己写过
        board.write_script(st, 'Duv写')
        self.assertEqual(st.favor['Duv'], 83)
        r = st.story['待上板'][1]
        self.assertEqual([k['项'] for k in r['看重']], ['教育', '相貌'])
        st.ym += 12
        self.assertTrue(board.script_ok(st, '合写'))
        board.write_script(st, '合写', 1)
        self.assertFalse(board.script_ok(st, '自己写'))
        self.assertFalse(board.script_ok(st, '合写'))
        es = board.make(st)['角色']
        extra = [e for e in es if e['来源'] == '剧本']
        self.assertEqual([e['档次'] for e in extra], ['中', '中', '大'])
        self.assertEqual(len(extra[2]['对手']), 2)


if __name__ == '__main__':
    unittest.main()
