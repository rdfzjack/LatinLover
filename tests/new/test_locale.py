"""tools/extract_text.py: key format, stale English, extra and duplicate keys, stray Chinese, missing Chinese."""
import csv
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import extract_text as X  # noqa: E402


class LocaleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = (X.DATA, X.LOCALE, X.CSV_PATH, X.BASIS_PATH)
        X.DATA = os.path.join(self.tmp, 'new')
        X.LOCALE = os.path.join(self.tmp, 'locale')
        X.CSV_PATH = os.path.join(X.LOCALE, 'text.csv')
        X.BASIS_PATH = os.path.join(X.LOCALE, 'en_basis.json')
        shutil.copytree(self.saved[0], X.DATA)

    def tearDown(self):
        X.DATA, X.LOCALE, X.CSV_PATH, X.BASIS_PATH = self.saved
        shutil.rmtree(self.tmp)

    def edit(self, name, fn):
        p = os.path.join(X.DATA, name)
        with open(p, encoding='utf-8') as fh:
            d = json.load(fh)
        fn(d)
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False)

    def rows(self):
        with open(X.CSV_PATH, encoding='utf-8', newline='') as fh:
            return {r[0]: r[1:] for r in list(csv.reader(fh))[1:]}

    def set_en(self, key, en):
        rows = self.rows()
        rows[key][1] = en
        with open(X.CSV_PATH, 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh, lineterminator='\n')
            w.writerow(['key', 'zh_CN', 'en'])
            w.writerows([k] + v for k, v in rows.items())

    def test_keys_and_clean_run(self):
        errs, _ = X.sync()
        self.assertEqual(errs, [])
        r = self.rows()
        for k in ('item.gold_watch.name', 'attr.stamina.name', 'street.restaurant.service.steak.name',
                  'event.evt_deposit_2000.option.0.text', 'origin.origin_past.option.0.text'):
            self.assertIn(k, r)
        self.assertEqual(X.sync()[0], [])

    def test_add_item_with_chinese_name(self):
        X.sync()
        self.edit('items.json', lambda d: d['items'].append({**d['items'][0], 'id': 'test_cane', 'name': '手杖'}))
        errs, notes = X.sync()
        self.assertEqual(errs, [])
        self.assertEqual(self.rows()['item.test_cane.name'][0], '手杖')
        self.assertIn('1 new', notes[0])

    def test_stale_then_ack(self):
        X.sync()
        self.set_en('item.gold_watch.name', 'Gold watch')
        self.assertEqual(X.sync()[0], [])
        self.edit('items.json', lambda d: d['items'][[i['id'] for i in d['items']].index('gold_watch')].update(name='金表'))
        errs, _ = X.sync()
        self.assertTrue(any('stale' in e and 'item.gold_watch.name' in e for e in errs))
        self.assertEqual(self.rows()['item.gold_watch.name'], ['金表', 'Gold watch'])
        X.ack(['item.'])
        self.assertEqual(X.sync()[0], [])

    def test_extra_key_and_prune(self):
        X.sync()
        self.edit('items.json', lambda d: d['items'].pop())
        errs, _ = X.sync(write=False)
        self.assertTrue(any('extra key' in e for e in errs))
        self.assertEqual(X.sync(prune=True)[0], [])

    def test_missing_and_stray_chinese(self):
        self.edit('items.json', lambda d: d['items'][0].pop('name'))
        self.edit('jobs.json', lambda d: d['jobs'][0].update(note='中文'))
        errs, _ = X.sync(write=False)
        self.assertTrue(any(e.startswith('missing Chinese: item.') for e in errs))
        self.assertTrue(any('outside the display fields' in e for e in errs))

    def test_duplicate_id(self):
        self.edit('items.json', lambda d: d['items'].append(dict(d['items'][0])))
        errs, _ = X.sync(write=False)
        self.assertTrue(any('duplicate key in the tables' in e for e in errs))


if __name__ == '__main__':
    unittest.main()
