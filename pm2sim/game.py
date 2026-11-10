"""High-level simulator API on top of the script VM.

    from pm2sim.game import Game
    g = Game('game_sample/PM2', seed=0)          # seed=None -> deterministic "fixed" RNG (offset 0)
    g.load_save('game_sample/PM2/F101.GNX')      # or g.new_game(profile)
    r = g.play_month([('上課學習', '劍術'), ('打工賺錢', '農場'), ('休    息', '自由行動')])
    print(r['delta'], g.state())

Decisions other than the schedule are answered by `answers`: a dict {option text: choice index
or option text} matched against the menu's option list, or a callable(kind, options) -> index/None.
Unmatched menus take option 0.
"""
import os, random
from .assets import Assets
from .engine import Engine, Driver
from . import save as savefile

STATS = ['B_TAIRYOKU', 'B_KINRYOKU', 'B_CHINOH', 'B_KIHIN', 'B_IROKE', 'B_MORALS', 'B_SHINKOH', 'B_INGYO',
         'B_KANJUSEI', 'B_STRESS', 'H_SENSHI', 'H_MAHO', 'H_SYAKOH', 'H_KAJI',
         'V_SENTOH', 'V_KOUGEKI', 'V_BOUGYO', 'V_MAHOGIJUTSU', 'V_MARYOKU', 'V_KOHMARYOKU',
         'V_REIGI', 'V_GEIJYUTSU', 'V_WAJYUTU', 'V_RYOURI', 'V_SOUJISENTAKU', 'V_KIDATE',
         'P_NENREI', 'P_SHINCHO', 'P_TAIJYU', 'P_BUST', 'P_WAIST', 'P_HIP',
         'S_BYOUKI', 'S_HIKOUKA', 'S_JINMYAKU', 'FLAG_BYOUKI', 'FLAG_HIKOUKA', 'FLAG_RENAI', 'FLAG_KENKO',
         'URA_PRINCE', 'URA_FATHER', 'URA_STEWARD', 'URA_MOTHER_LOVE', 'URA_KILL_MONSTR',
         'VAL_YEAR', 'VAL_MONTH', 'VAL_DAY', 'VAL_WEEK']
SECTIONS = ['上課學習', '打工賺錢', '武者修行', '休    息']


class Pause(Exception):
    pass


class PlanDriver(Driver):
    def __init__(self):
        self.plan = []; self.pending = None; self.answers = {}; self.profile_data = None
        self.adventure_fn = None; self.started = False; self.main_queue = []; self.history = []

    def _pick(self, options, want):
        names = [o if isinstance(o, str) else o['name'] for o in options]
        if isinstance(want, int): return want
        for i, n in enumerate(names):
            if n.replace('　', '').replace(' ', '') == want.replace('　', '').replace(' ', ''): return i
        raise KeyError('option %r not offered; available: %s' % (want, names))

    def select(self, eng, kind, options):
        r = self._select(eng, kind, options)
        self.history.append((kind, options if not isinstance(options, list) else
                             [o if isinstance(o, str) else o['name'] for o in options], r))
        return r

    def _select(self, eng, kind, options):
        if kind == 'MAIN':
            if self.main_queue: return self._pick(options, self.main_queue.pop(0))
            if self.plan and not self.started: return 0
            self.plan = []; self.started = False
            raise Pause()
        if callable(self.answers):
            r = self.answers(kind, options)
            if r is not None: return r
        if kind == 'SLCT' and isinstance(options, list) and options[:1] == [SECTIONS[0]]:
            if not self.plan:
                raise KeyError('schedule needs %d entries this month; plan is too short' % eng.vm.get('SCH_COUNT'))
            self.pending = self.plan.pop(0); self.started = True
            return self._pick(SECTIONS, self.pending[0])
        if kind == 'ITEMSLCT' and self.pending is not None:
            want = self.pending[1]; self.pending = None
            return self._pick(options, want)
        if isinstance(options, list) and isinstance(self.answers, dict):
            for o in options:
                name = o if isinstance(o, str) else o['name']
                if name in self.answers: return self._pick(options, self.answers[name])
        return 0

    def profile(self, eng):
        p = self.profile_data or {}
        vm = eng.vm
        if 'first_name' in p: vm.put_cstr(vm.ruw(0x4232), p['first_name'].encode('big5'))
        if 'family_name' in p: vm.put_cstr(vm.ruw(0x4236), p['family_name'].encode('big5'))
        for key, name, idx in (('blood', 'P_BLOOD', 0), ('birth_year', 'P_BORTHYEAR', 0), ('birth_month', 'P_BORTHMONTH', 0),
                               ('birth_day', 'P_BORTHDAY', 0), ('father_birth_year', 'P_BORTHYEAR', 1),
                               ('father_birth_month', 'P_BORTHMONTH', 1), ('father_birth_day', 'P_BORTHDAY', 1)):
            if key in p: vm.set(name, p[key], idx)

    def adventure(self, eng, state, mode):
        return self.adventure_fn(eng, state, mode) if self.adventure_fn else None


class Game:
    def __init__(self, game_dir=None, seed=None):
        game_dir = game_dir or os.path.join(os.path.dirname(__file__), '..', 'game_sample', 'PM2')
        self.assets = Assets(game_dir)
        self.driver = PlanDriver()
        self.rand = random.Random(seed)
        # seed=None: every RNG reseed uses offset 0 (same as patching 0389:81E8 `call C06C` -> `mov ax,0`)
        self.eng = Engine(self.assets, self.driver, (lambda: 0) if seed is None else (lambda: self.rand.randrange(200)))
        self.vm = self.eng.vm

    # ---- state ----------------------------------------------------------------
    def state(self):
        vm = self.vm
        d = {n: vm.get(n) for n in STATS}
        d['GOLD'] = self.eng.gold()
        return d
    def get(self, name, idx=0): return self.vm.get(name, idx)
    def set(self, name, value, idx=0): self.vm.set(name, value, idx)
    def set_rng(self, offset, index):
        """RNG state = (ds:6744 offset 0..199, ds:6746 index 0..200)."""
        self.vm.ww(0x6744, offset); self.vm.ww(0x6746, index)
    def rng(self): return self.vm.ruw(0x6744), self.vm.ruw(0x6746)

    # ---- running ----------------------------------------------------------------
    def _run(self, max_steps=20_000_000):
        vm = self.vm; start = vm.steps
        while not vm.halted:
            try:
                vm.run(max_steps=vm.steps + 100000)
            except Pause:
                vm.pc = vm.call_pc; return 'main'
            if vm.steps - start > max_steps: raise RuntimeError('step limit exceeded in %s' % vm.program_names)
        return 'end'

    def new_game(self, profile=None, answers=None):
        """Start from the title: profile keys first_name, family_name, blood(0-3), birth_year/month/day,
        father_birth_year/month/day.  Runs the opening and stops at the first main menu."""
        self.driver.profile_data = profile or {}
        if answers is not None: self.driver.answers = answers
        self.vm.load('START')
        return self._run()

    def load_save(self, path):
        savefile.load(self.vm, open(path, 'rb').read())
        self.vm.load('MAINLOOP')
        return self._run()

    def periods(self):
        """Number of schedule periods the next play_month() will ask for (1037:397B)."""
        vm = self.vm; d, end = vm.get('VAL_DAY'), self.eng.month_len(vm.get('VAL_YEAR'), vm.get('VAL_MONTH'))
        start = 1 if d == end else d + 1
        if d == end:
            y, m = vm.get('VAL_YEAR'), vm.get('VAL_MONTH') + 1
            if m > 12: y, m = y + 1, 1
            end = self.eng.month_len(y, m)
        return 1 if start + 12 >= end else 2 if start + 22 >= end else 3

    def save(self, path): open(path, 'wb').write(savefile.dump(self.vm))

    def main_command(self, command, answers=None):
        """Run one main-menu command other than the schedule (e.g. '街道', '王城', '談話')."""
        if answers is not None: self.driver.answers = answers
        self.driver.main_queue.append(command)
        return self._run()

    def play_month(self, plan, answers=None):
        """plan: one (section, work) pair per schedule period of the coming month (normally 3; see
        periods()), each a menu text or an index.  Runs until the main menu comes back."""
        if answers is not None: self.driver.answers = answers
        before = self.state(); nlog = len(self.eng.log); self.driver.history.clear()
        self.driver.plan = list(plan)
        status = self._run()
        after = self.state()
        return dict(status=status, delta={k: after[k] - before[k] for k in after if after[k] != before[k]},
                    log=self.eng.log[nlog:], menus=list(self.driver.history), program=list(self.vm.program_names))
