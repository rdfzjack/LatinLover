import unittest
from sim import board, film
from sim.schedule import days_of
from tests.new.helpers import D, bare


def role(tier='中', tags=('西部',), want=(('体力', 200),), talkie=False, probs=(50, 20, 20, 10)):
    return {'id': 'r', '名字': 'r', '档次': tier, '场风概率': list(probs), '基础场风': list(probs), '路': '硬汉',
            '看重': [{'项': k, '目标': v} for k, v in want], '标签': list(tags), '加分技能': '演技', '有声': talkie,
            '谈吐线': {'小': 30, '中': 50, '大': 70}[tier] if talkie else None,
            '片酬': D.role_cfg['片酬'][tier], '女主': None}


def st0():
    st = bare()
    st.attr.update({'体力': 200, '教育': 200, '名气': 100, '疲劳': 0, '自律': 100})
    st.ym = 1
    st.update_indices()
    return st


class TestFilm(unittest.TestCase):
    def test_locks_and_status(self):
        st = st0()
        self.assertEqual(film.board_locks(st, '大'), [[2, 0], [2, 1], [2, 2]])
        self.assertEqual(film.board_locks(st, '中', support=True), [[2, 0]])
        self.assertEqual(film.board_locks(st, '小', support=True), [[2, 0]])
        f = film.new_film(st, role(), film.board_locks(st, '中'))
        self.assertEqual(st.status['有未开拍角色'], 1)
        st.ym = 2
        self.assertIs(film.locked(st, 1), f)
        self.assertIsNone(film.locked(st, 2))
        self.assertEqual(film.next_period(st, 2), [3, 0])

    def test_shoot_fee_release_timing(self):
        st = st0()
        st.skill['演技'] = 50
        st.skill['谈判'] = 40
        f = film.new_film(st, role(), film.board_locks(st, '中'))
        st.ym = 2
        m0 = st.money
        for i in range(2):
            film.shoot(st, i, f, days_of(st, i))
        days = sum(1 for _, s in days_of(st, 0) + days_of(st, 1) if not s)
        self.assertEqual(f['拍摄日'], days)
        self.assertEqual(f['成功日'], days)                     # 体力 200、疲劳低，天天成功
        self.assertEqual(f['表现'], 500 + 500 + 50 * 2)         # P = 1.1
        self.assertEqual(f['片酬'], 800 * 440 // 400)           # 教育 ≥100，无合同折扣
        self.assertEqual(st.money, m0 + f['片酬'])
        self.assertEqual(f['状态'], '待映')
        self.assertEqual(f['上映'], 4)
        self.assertEqual(st.attr['疲劳'], 3 * days)
        self.assertEqual(st.exposed, 1)

    def test_contract_discount_and_support(self):
        st = st0()
        st.attr['教育'] = 50
        st.skill['谈判'] = 0
        f = film.new_film(st, role('大'), [[2, 0]], support=True)
        self.assertEqual(film.fee(st, f), 2500 * 40 // 100 * 85 // 100)
        st.favor['Sil'] = 50                                   # Sil 好感 ≥50 免除
        self.assertEqual(film.fee(st, f), 2500 * 40 // 100)
        f['亲自上'] = True
        f['配角'] = False
        self.assertEqual(film.fee(st, f), 2500 * 130 // 100)

    def test_personally(self):
        st = st0()
        st.skill['胆识'] = 55
        self.assertFalse(film.can_go_personally(st, role(tags=('西部',))))
        st.flags['亲自上线50'] = 1
        self.assertTrue(film.can_go_personally(st, role(tags=('西部',))))
        self.assertFalse(film.can_go_personally(st, role(tags=('浪漫',))))

    def _released(self, st, r, P=1000, support=False):
        f = film.new_film(st, r, [[0, 0]], support=support)
        f.update({'状态': '待映', '上映': st.ym, '表现': P, '拍摄日': 1, '成功日': 1})
        film.release(st)
        return f['结果']

    def test_release_plain(self):
        st = st0()
        r = role(want=(('体力', 200),))                         # 契合 1.0
        res = self._released(st, r)
        self.assertEqual((res['F'], res['T'], res['S']), (1000, 1000, 100000))
        self.assertEqual(res['名气'], 30)
        self.assertEqual(res['分红'], 200)
        self.assertEqual(st.corr['硬汉'], 5)
        self.assertEqual(st.tags['西部'], 1)
        self.assertEqual(st.cnt('计数.低成本'), 0)               # 中片 -1，最低 0
        self.assertEqual(st.attr['名气'], 130)

    def test_release_hit_and_flop(self):
        st = st0()
        st.attr['体力'] = 300                                   # 契合 1.2
        st.tags['西部'] = 3                                     # 定型：T 取满 1.15
        res = self._released(st, role(), P=1200)
        self.assertEqual(res['S'], 100 * 1200 * 1200 * 1150 // 1000000)
        self.assertTrue(res['大卖'])
        self.assertEqual(st.corr['硬汉'], 10)                   # 大卖翻倍
        st = st0()
        st.attr['体力'] = 50                                    # 契合 0.7
        res = self._released(st, role(), P=500)
        self.assertTrue(res['扑街'])
        self.assertEqual(res['修正'], 0)
        self.assertEqual(res['名气'], res['S'] * 30 // 100000 // 2)

    def test_typecast_penalty_and_low_budget(self):
        st = st0()
        st.tags['浪漫'] = 3                                     # 定型在别的标签
        res = self._released(st, role())
        self.assertTrue(res['非定型'])
        self.assertEqual(res['S'], 100000 * 90 // 100)
        st = st0()
        st.count['计数.低成本'] = 4
        res = self._released(st, role('小'))
        self.assertEqual(res['T'], 1150)                        # 低成本定型的小片 T 取满
        self.assertEqual(st.cnt('计数.低成本'), 5)

    def test_support_release(self):
        st = st0()
        res = self._released(st, role(), support=True)
        self.assertEqual(res['名气'], 30 * 30 // 100)
        self.assertEqual(st.corr['硬汉'], 5 * 30 // 100)
        self.assertEqual(st.tags['西部'], 1)
        self.assertEqual(st.cnt('计数.配角'), 1)

    def test_talkie(self):
        st = st0()
        st.skill['谈吐'] = 30
        res = self._released(st, role(talkie=True))
        self.assertTrue(res['口音'])
        self.assertEqual(res['S'], 100000 * 60 // 100)
        self.assertEqual(st.flags['口音待触发'], 1)
        self.assertEqual(st.cnt('计数.有声片部数'), 1)
        st = st0()
        st.skill['谈吐'] = 40
        st.flags['有声谈吐线减10'] = 1
        self.assertFalse(self._released(st, role(talkie=True))['口音'])

    def test_breach(self):
        st = st0()
        f = film.new_film(st, role(), film.board_locks(st, '中'))
        st.attr['名气'] = 200
        film.breach_month(st, 2)
        self.assertEqual(f['状态'], '违约')
        self.assertEqual(st.attr['名气'], 180)
        self.assertEqual(st.status['有未开拍角色'], 0)


if __name__ == '__main__':
    unittest.main()
