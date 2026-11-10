"""Self-checks that need no running game: python3 tests/test_sim.py  (also works under pytest).
The six F10x.GNX saves shipped with the game are real data, so the invariant checks below
verify the reverse-engineered formulas against the original program's own output."""
import glob, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from pm2sim.game import Game
from pm2sim import save
GAME = os.path.join(ROOT, 'game_sample', 'PM2')
SAVES = sorted(glob.glob(os.path.join(GAME, 'F10*.GNX')))
PLAN = [('上課學習', '劍術'), ('打工賺錢', '農場'), ('休    息', '自由行動')]

def loaded(path):
    g = Game(GAME); save.load(g.vm, open(path, 'rb').read()); return g

def test_save_roundtrip():
    assert len(SAVES) == 6
    for f in SAVES:
        d = open(f, 'rb').read(); g = loaded(f)
        assert save.dump(g.vm) == d, f

def test_calendar_matches_saves():       # 1037:2DE4 weekday, 1037:2BE0 age, 1037:2C81 month length
    for f in SAVES:
        g = loaded(f); vm, e = g.vm, g.eng
        wk = vm.get('VAL_WEEK'); e._weekday(); assert vm.get('VAL_WEEK') == wk, f
        assert e.age(vm.get('P_BORTHYEAR'), vm.get('P_BORTHMONTH'), vm.get('P_BORTHDAY')) == vm.get('P_NENREI'), f
        if vm.get('VAL_M_END'): assert e.month_len(vm.get('VAL_YEAR'), vm.get('VAL_MONTH')) == vm.get('VAL_M_END'), f

def test_derived_values_match_saves():   # 0389:4A34, 4732, 4DA7, 4977
    for f in SAVES:
        g = loaded(f); vm, e = g.vm, g.eng
        st, ta, mo, sh = (vm.get(n) for n in ('B_STRESS', 'B_TAIRYOKU', 'B_MORALS', 'B_SHINKOH'))
        assert vm.get('S_BYOUKI') == e._c100(st - ta), f
        assert vm.get('S_HIKOUKA') == e._c100(st - max(mo, sh)), f
        assert [sum(vm.rw(0x41D8 + 2*(3*i + k)) for k in range(3)) for i in range(4)] == [vm.rw(0x4222 + 2*i) for i in range(4)], f
        assert all(vm.rw(0x41F2 + 2*i) == vm.rw(0x420A + 2*i) for i in range(12)), f
        assert vm.get('P_WAIST') == (vm.ruw(0x4256)*3 + 25000 + vm.ruw(0x4258)*10) // 20, f

def test_rng_ranges():
    g = Game(GAME, seed=3); e = g.eng
    assert sorted(g.vm.mem[0x6748:0x6748+200]) == list(range(1, 201))
    for n in (2, 3, 7, 100, 200):
        v = [e.randam(n) for _ in range(4000)]; assert min(v) == 1 and max(v) == n
    for n in (5, 50, 999):
        v = [e.irand999(n) for _ in range(6000)]; assert min(v) == 0 and max(v) == n

def test_months_run_and_are_deterministic():
    for f in SAVES:
        res = []
        for _ in range(2):
            g = Game(GAME, seed=None); g.load_save(f); g.set_rng(0, 0)
            for _m in range(3): g.play_month(PLAN[:g.periods()])
            assert not g.vm.warnings, g.vm.warnings[:3]
            res.append(save.dump(g.vm))
        assert res[0] == res[1], f

def test_new_game_to_first_menu():
    g = Game(GAME, seed=1)
    assert g.new_game(dict(first_name='Ｍ', family_name='Ｔ', blood=0, birth_year=1200, birth_month=6, birth_day=15)) == 'main'
    s = g.state(); assert s['P_NENREI'] == 10 and s['GOLD'] == 500 and s['VAL_YEAR'] == 1210

if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn(); print('ok  ', name)
