import unittest
from sim.state import State
from tests.new.helpers import D, fresh, bare


class TestState(unittest.TestCase):
    def test_base_reputation(self):
        st = bare()
        # 硬汉 = 打斗 10 + 体力加成 min(80/10, 30)=8 + 骑马驾驶 10 + 胆识 5
        self.assertEqual({r: st.rep(r) for r in D.roads}, {'硬汉': 33, '情人': 50, '文化': 10, '手腕': 20})
        self.assertEqual(st.level('情人'), 2)
        self.assertEqual(st.fame_tier(), 1)

    def test_origin(self):
        st = fresh(origin=(0, 1, 2))   # 逃兵、演技派、欠他人情的人
        self.assertEqual(st.attr['体力'], 100)
        self.assertEqual(st.attr['自律'], 25)
        self.assertEqual(st.skill['演技'], 40)
        self.assertEqual(st.skill['人脉'], 20)
        self.assertEqual(st.attr['名气'], 100)
        self.assertEqual(st.flags, {'逃兵': 1, '人情': 1})
        self.assertEqual(st.tags, {'悲情': 1, '文艺': 1})
        st = fresh(origin=(4, 3, 1))   # 农学院学生、色情电影、旧西装
        self.assertEqual(st.items, ['旧西装'])
        self.assertEqual(st.flags, {'文凭': 1, '旧片': 1})

    def test_fight_bonus(self):
        st = bare()
        st.attr['体力'] = 500
        self.assertEqual(st.val('打斗'), 10 + 30)

    def test_clothing(self):
        st = bare()
        st.items.append('定制西装')
        st.equip['服装'] = '定制西装'
        # 30 × (50 + 打扮 10)/100 = 18
        self.assertEqual(st.val('相貌'), 120 + 18)
        st.skill['打扮'] = 100
        self.assertEqual(st.val('相貌'), 120 + 45)

    def test_held_exclusive_and_accessory(self):
        st = bare()
        st.items += ['福特车', '跑车', '相机', '相机', '拳套']
        self.assertEqual(st.val('骑马驾驶'), 10 + 15)   # 车只算最贵的一辆
        self.assertEqual(st.val('审美'), 5 + 15)        # 同一件持有两个只算一次
        self.assertEqual(st.val('打斗'), 18)            # 配饰没装上不算
        st.equip['配饰'].append('拳套')
        self.assertEqual(st.val('打斗'), 28)

    def test_indices(self):
        st = bare()
        st.attr['疲劳'] = 200
        st.update_indices()
        self.assertEqual(st.idx, {'生病指数': 100, '失控指数': 100})
        self.assertEqual((st.status['生病'], st.status['重病'], st.status['失控']), (1, 1, 1))
        st.attr['疲劳'] = 50
        st.update_indices()
        self.assertEqual(st.idx, {'生病指数': 0, '失控指数': 10})
        self.assertEqual((st.status['生病'], st.status['失控']), (0, 1))

    def test_save_roundtrip(self):
        st = fresh(origin=(1, 2, 5))
        st.books['book_tantu_1'] = 12
        st.count['旬数.class_acting'] = 4
        st.rng.logic.next_u32()
        s = st.dumps()
        st2 = State.loads(D, s)
        self.assertEqual(st2.dumps(), s)
        self.assertEqual(st.rng.logic.next_u32(), st2.rng.logic.next_u32())


if __name__ == '__main__':
    unittest.main()
