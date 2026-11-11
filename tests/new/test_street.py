import unittest
from sim import street as T
from sim.street import StreetError
from tests.new.helpers import bare


class TestStreet(unittest.TestCase):
    def test_discount(self):
        st = bare()
        self.assertEqual(T.discount_pct(st), 0)
        st.skill['connections'] = 40
        self.assertEqual(T.discount_pct(st), 10)
        self.assertEqual(T.price(st, 'clothing_store', 15), 14)     # 13.5 rounded up
        self.assertEqual(T.price(st, 'church', 100), 100)     # no discount at the church
        st.skill['connections'] = 100
        self.assertEqual(T.discount_pct(st), 25)

    def test_books(self):
        st = bare()
        self.assertNotIn('book_tantu_2', T.shelf(st, 'bookstore'))   # only on the shelf from 1926-08
        st.ym = 7
        self.assertIn('book_tantu_2', T.shelf(st, 'bookstore'))
        self.assertEqual(T.buy(st, 'bookstore', 'book_tantu_1'), 15)
        self.assertEqual(st.books['book_tantu_1'], 35)
        with self.assertRaises(StreetError):
            T.buy(st, 'bookstore', 'book_tantu_1')
        del st.books['book_tantu_1']; st.read_books.append('book_tantu_1')
        self.assertEqual(T.sell(st, 'book_tantu_1'), 7)
        with self.assertRaises(StreetError):
            T.buy(st, 'general_store', 'book_tantu_1')

    def test_items_and_equip(self):
        st = bare(); st.money = 100
        T.buy(st, 'clothing_store', 'boxing_gloves'); T.buy(st, 'clothing_store', 'boxing_gloves'); T.buy(st, 'clothing_store', 'gold_watch')
        T.equip(st, 'boxing_gloves'); T.equip(st, 'boxing_gloves')
        with self.assertRaises(StreetError):
            T.equip(st, 'gold_watch')          # 2 accessory slots
        with self.assertRaises(StreetError):
            T.sell(st, 'boxing_gloves')           # both are equipped
        self.assertEqual(st.val('fight'), 10 + 2 + 10)
        T.unequip(st, 'boxing_gloves')
        self.assertEqual(T.sell(st, 'boxing_gloves'), 3)
        with self.assertRaises(StreetError):
            T.buy(st, 'general_store', 'car_luxury')

    def test_consumable(self):
        st = bare(); T.buy(st, 'general_store', 'tonic')
        T.use(st, 'tonic')
        self.assertEqual(st.attr['stamina'], 82)
        self.assertEqual(st.items, [])

    def test_restaurant(self):
        st = bare(); st.attr['fatigue'] = 40
        T.restaurant(st, 'nightclub_dinner')
        self.assertEqual((st.money, st.attr['fatigue']), (480, 10))
        with self.assertRaises(StreetError):
            T.restaurant(st, 'dessert')     # the three together are once a month
        st.month_used = {}; st.status['sick'] = 1
        T.restaurant(st, 'steak')
        self.assertEqual((st.money, st.attr['stamina']), (470, 80))

    def test_church_hospital(self):
        st = bare(); st.attr['crime'] = 50
        T.church(st)
        self.assertEqual((st.money, st.attr['crime']), (400, 40))
        with self.assertRaises(StreetError):
            T.church(st)
        with self.assertRaises(StreetError):
            T.hospital(st)
        st.attr['fatigue'] = 120; st.update_indices()
        self.assertEqual(T.hospital(st), 80)
        self.assertEqual(st.attr['fatigue'], 120 - 41)

    def test_sil(self):
        st = bare(); st.favor['sil'] = 40; st.attr['fatigue'] = 70; st.update_indices()
        self.assertEqual(T.sil_hint(st)[0], 'reckless')
        T.sil_persuade(st)
        self.assertEqual((st.attr['fatigue'], st.favor['sil']), (50, 42))
        with self.assertRaises(StreetError):
            T.sil_persuade(st)
        st.attr['fatigue'] = 0; st.update_indices()
        self.assertEqual(T.sil_hint(st), ('top attribute', 'looks'))


if __name__ == '__main__':
    unittest.main()
