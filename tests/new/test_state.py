import unittest
from sim.state import State
from tests.new.helpers import D, fresh, bare


class TestState(unittest.TestCase):
    def test_base_reputation(self):
        st = bare()
        # tough = fight 10 + stamina bonus min(80/10, 30)=8 + riding 10 + nerve 5
        self.assertEqual({r: st.rep(r) for r in D.roads}, {'tough': 27, 'lover': 50, 'culture': 10, 'savvy': 20})
        self.assertEqual(st.level('lover'), 2)
        self.assertEqual(st.fame_tier(), 1)

    def test_origin(self):
        st = fresh(origin=(0, 1, 2))   # deserter, acting school, owes someone a favor
        self.assertEqual(st.attr['stamina'], 100)
        self.assertEqual(st.attr['discipline'], 25)
        self.assertEqual(st.skill['acting'], 40)
        self.assertEqual(st.skill['connections'], 20)
        self.assertEqual(st.attr['fame'], 100)
        self.assertEqual(st.flags, {'deserter': 1, 'owed_favor': 1})
        self.assertEqual(st.tags, {'tragic': 1, 'arthouse': 1})
        st = fresh(origin=(4, 3, 1))   # agriculture student, adult film, old suit
        self.assertEqual(st.items, ['suit_old'])
        self.assertEqual(st.flags, {'diploma': 1, 'old_film': 1})

    def test_fight_bonus(self):
        st = bare()
        st.attr['stamina'] = 500
        self.assertEqual(st.val('fight'), 10 + 10)

    def test_clothing(self):
        st = bare()
        st.items.append('suit_custom')
        st.equip['outfit'] = 'suit_custom'
        # 30 x (50 + grooming 10)/100 = 18
        self.assertEqual(st.val('looks'), 120 + 18)
        st.skill['grooming'] = 100
        self.assertEqual(st.val('looks'), 120 + 45)

    def test_held_exclusive_and_accessory(self):
        st = bare()
        st.items += ['car_ford', 'car_sports', 'camera', 'camera', 'boxing_gloves']
        self.assertEqual(st.val('riding'), 10 + 5)    # only the most expensive car counts
        self.assertEqual(st.val('taste'), 5 + 6)         # two copies of the same item count once
        self.assertEqual(st.val('fight'), 12)            # accessories that are not equipped do not count
        st.equip['accessory'].append('boxing_gloves')
        self.assertEqual(st.val('fight'), 17)

    def test_indices(self):
        st = bare()
        st.attr['fatigue'] = 200
        st.update_indices()
        self.assertEqual(st.idx, {'sick_index': 100, 'reckless_index': 100})
        self.assertEqual((st.status['sick'], st.status['very_sick'], st.status['reckless']), (1, 1, 1))
        st.attr['fatigue'] = 50
        st.update_indices()
        self.assertEqual(st.idx, {'sick_index': 0, 'reckless_index': 10})
        self.assertEqual((st.status['sick'], st.status['reckless']), (0, 1))

    def test_save_roundtrip(self):
        st = fresh(origin=(1, 2, 5))
        st.books['book_tantu_1'] = 12
        st.count['class_periods.class_acting'] = 4
        st.rng.logic.next_u32()
        s = st.dumps()
        st2 = State.loads(D, s)
        self.assertEqual(st2.dumps(), s)
        self.assertEqual(st.rng.logic.next_u32(), st2.rng.logic.next_u32())


if __name__ == '__main__':
    unittest.main()
