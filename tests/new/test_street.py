import unittest
from sim import street as T
from sim.street import StreetError
from tests.new.helpers import bare


class TestStreet(unittest.TestCase):
    def test_discount(self):
        st = bare()
        self.assertEqual(T.discount_pct(st), 0)
        st.skill['人脉'] = 40
        self.assertEqual(T.discount_pct(st), 10)
        self.assertEqual(T.price(st, '服装店', 15), 14)     # 13.5 向上取整
        self.assertEqual(T.price(st, '教堂', 100), 100)     # 教堂不打折
        st.skill['人脉'] = 100
        self.assertEqual(T.discount_pct(st), 25)

    def test_books(self):
        st = bare()
        self.assertNotIn('book_tantu_2', T.shelf(st, '书店'))   # 1926-08 才上架
        st.ym = 7
        self.assertIn('book_tantu_2', T.shelf(st, '书店'))
        self.assertEqual(T.buy(st, '书店', 'book_tantu_1'), 5)
        self.assertEqual(st.books['book_tantu_1'], 35)
        with self.assertRaises(StreetError):
            T.buy(st, '书店', 'book_tantu_1')
        del st.books['book_tantu_1']; st.read_books.append('book_tantu_1')
        self.assertEqual(T.sell(st, 'book_tantu_1'), 2)
        with self.assertRaises(StreetError):
            T.buy(st, '杂货店', 'book_tantu_1')

    def test_items_and_equip(self):
        st = bare(); st.money = 100
        T.buy(st, '服装店', '拳套'); T.buy(st, '服装店', '拳套'); T.buy(st, '服装店', '怀表')
        T.equip(st, '拳套'); T.equip(st, '拳套')
        with self.assertRaises(StreetError):
            T.equip(st, '怀表')          # 配饰槽 2 个
        with self.assertRaises(StreetError):
            T.sell(st, '拳套')           # 两件都装着
        self.assertEqual(st.val('打斗'), 10 + 8 + 20)
        T.unequip(st, '拳套')
        self.assertEqual(T.sell(st, '拳套'), 3)
        with self.assertRaises(StreetError):
            T.buy(st, '杂货店', '进口豪车')

    def test_consumable(self):
        st = bare(); T.buy(st, '杂货店', '补药')
        T.use(st, '补药')
        self.assertEqual(st.attr['体力'], 82)
        self.assertEqual(st.items, [])

    def test_restaurant(self):
        st = bare(); st.attr['疲劳'] = 40
        T.restaurant(st, '夜总会晚餐')
        self.assertEqual((st.money, st.attr['疲劳']), (480, 10))
        with self.assertRaises(StreetError):
            T.restaurant(st, '点心')     # 三项合计每月一次
        st.month_used = {}; st.status['生病'] = 1
        T.restaurant(st, '牛排')
        self.assertEqual((st.money, st.attr['体力']), (470, 80))

    def test_church_hospital(self):
        st = bare(); st.attr['犯罪'] = 50
        T.church(st)
        self.assertEqual((st.money, st.attr['犯罪']), (400, 40))
        with self.assertRaises(StreetError):
            T.church(st)
        with self.assertRaises(StreetError):
            T.hospital(st)
        st.attr['疲劳'] = 120; st.update_indices()
        self.assertEqual(T.hospital(st), 80)
        self.assertEqual(st.attr['疲劳'], 120 - 41)

    def test_sil(self):
        st = bare(); st.favor['Sil'] = 40; st.attr['疲劳'] = 70; st.update_indices()
        self.assertEqual(T.sil_hint(st)[0], '失控')
        T.sil_persuade(st)
        self.assertEqual((st.attr['疲劳'], st.favor['Sil']), (50, 42))
        with self.assertRaises(StreetError):
            T.sil_persuade(st)
        st.attr['疲劳'] = 0; st.update_indices()
        self.assertEqual(T.sil_hint(st), ('最高属性', '相貌'))

    def test_stock(self):
        st = bare(); st.money = 1000
        with self.assertRaises(StreetError):
            T.stock_buy(st, 100)
        st.flags['股票'] = 1
        with self.assertRaises(StreetError):
            T.stock_buy(st, 150)
        T.stock_buy(st, 500)
        st.stock = 515
        T.stock_sell(st, 515)
        self.assertEqual((st.money, st.stock), (1015, 0))


if __name__ == '__main__':
    unittest.main()
