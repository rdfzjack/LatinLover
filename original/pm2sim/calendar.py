"""CLENDER command family: calendar, ages, monthly growth and derived-status update.
Calendar code is in seg 1037:2AC6-3073, growth/status code in seg 0389:4720-4F9B."""
from .vm import s16

MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)     # ds:3BD6
SEASON_END = ((59, 151, 243, 334), (60, 152, 244, 335))           # ds:3BE2 / ds:3BEA (leap)
# skills: trained value T_x (0..100), shadow copy, displayed value V_x (= T_x + equipment bonuses)
SKILLS = [(0x41F2 + 2*i, 0x420A + 2*i, 0x41D8 + 2*i) for i in range(12)]
B = dict(TAIRYOKU=0x41BC, KINRYOKU=0x41BE, CHINOH=0x41C0, KIHIN=0x41C2, IROKE=0x41C4,
         MORALS=0x41C6, SHINKOH=0x41C8, INGYO=0x41CA, KANJUSEI=0x41CC, STRESS=0x41CE)
B_ORDER = [0x41BC + 2*i for i in range(10)]


class CalendarMixin:
    # ---- calendar primitives -------------------------------------------------
    @staticmethod
    def is_leap(y):               # 1037:2E63 (note the (y-1) quirk for centuries)
        if (y - 1) % 400 == 0: return True
        if (y - 1) % 100 == 0: return False
        return y % 4 == 0
    def month_len(self, y, m):    # 1037:2C81
        return 29 if m == 2 and self.is_leap(y) else MONTH_DAYS[m - 1]
    def _doy(self):               # 1037:2E2F  VAL_A_DAY
        vm = self.vm; y, m, d = vm.get('VAL_YEAR'), vm.get('VAL_MONTH'), vm.get('VAL_DAY')
        n = d + sum(MONTH_DAYS[:m - 1]) + (1 if self.is_leap(y) and m > 2 else 0)
        vm.set('VAL_A_DAY', n); return n
    def _weekday(self):           # 1037:2DE4  0 = Sunday
        vm = self.vm; n = self._doy(); y = vm.get('VAL_YEAR')
        vm.set('VAL_WEEK', ((y-1)//4 - (y-1)//100 + (y-1)//400 + y - 1 + n) % 7)
    def _flags(self):             # 1037:2CA0
        vm = self.vm
        for f in ('FLG_SHOGATSU', 'FLG_URUBI', 'FLG_G_BORTH', 'FLG_M_BORTH', 'FLG_CHRISTMAS_EVE',
                  'FLG_HOLIDAY', 'FLG_SYUKAKU'): vm.set(f, 0)
        if vm.get('VAL_WEEK') == 0: vm.set('FLG_HOLIDAY', 1)
        n = self._doy(); y, m, d = vm.get('VAL_YEAR'), vm.get('VAL_MONTH'), vm.get('VAL_DAY')
        t = SEASON_END[1 if self.is_leap(y) else 0]
        vm.set('TM_SEASON', 4 if n <= t[0] else 1 if n <= t[1] else 2 if n <= t[2] else 3 if n <= t[3] else 4)
        if m == 2 and d == 29: vm.set('FLG_URUBI', 1)
        if m == 12 and d == 24: vm.set('FLG_CHRISTMAS_EVE', 1); vm.set('FLG_HOLIDAY', 1)
        if m == 1 and d == 1: vm.set('FLG_SHOGATSU', 1); vm.set('FLG_HOLIDAY', 1)
        if m == 9 and d >= 21: vm.set('FLG_SYUKAKU', 1)
    def age(self, by, bm, bd):    # 1037:2BE0
        vm = self.vm; y, m, d = vm.get('VAL_YEAR'), vm.get('VAL_MONTH'), vm.get('VAL_DAY')
        if by >= y: return 0
        a = y - by - 1
        if m > bm or (m == bm and d >= bd): a += 1
        return a
    def _advance_day(self):       # 1037:2C19
        vm = self.vm; y, m, d = vm.get('VAL_YEAR'), vm.get('VAL_MONTH'), vm.get('VAL_DAY')
        if self.is_leap(y) and m == 2 and d == 28: d = 29
        else:
            d += 1
            if d > MONTH_DAYS[m - 1]:
                d = 1; m += 1
                if m > 12: m = 1; y += 1
        vm.set('VAL_YEAR', y); vm.set('VAL_MONTH', m); vm.set('VAL_DAY', d)
        self._weekday(); vm.set('VAL_M_END', self.month_len(y, m))
    def _birthdays(self):         # 1037:2F95
        vm = self.vm; vm.set('FLG_G_BORTH', 0); vm.set('FLG_M_BORTH', 0)
        for i, flag in ((0, 'FLG_G_BORTH'), (1, 'FLG_M_BORTH')):
            if vm.get('P_BORTHDAY', i) == vm.get('VAL_DAY') and vm.get('P_BORTHMONTH', i) == vm.get('VAL_MONTH'):
                vm.set('P_NENREI', self.age(vm.get('P_BORTHYEAR', i), vm.get('P_BORTHMONTH', i), vm.get('P_BORTHDAY', i)), i)
                vm.set(flag, 1)
    def month_attr(self):         # 1037:3007
        """0 normal, 1 very first month (age 10, on the birthday), 2 age>=18 (ending),
        3..6 = 1..4 months before the 18th birthday."""
        vm = self.vm; age = vm.get('P_NENREI'); m = vm.get('VAL_MONTH'); bm = vm.get('P_BORTHMONTH')
        if age == 10 and m == bm and vm.get('VAL_DAY') == vm.get('P_BORTHDAY'): return 1
        if age >= 18: return 2
        if age >= 17:
            for k in range(1, 5):
                bm = 12 if bm - 1 == 0 else bm - 1
                if bm == m: return 2 + k
        return 0

    # ---- derived status --------------------------------------------------------
    def sync_skills(self):        # 0389:4DA7  V += clamp(T,0,100) - shadow
        vm = self.vm
        for t, sh, v in SKILLS:
            tv = max(0, min(100, vm.rw(t)))
            vm.ww(v, vm.rw(v) + tv - vm.rw(sh)); vm.ww(t, tv); vm.ww(sh, tv)
    def sync_attack(self):        # 0389:4B77  attack skill carries a KINRYOKU/10 bonus (ds:41F0)
        vm = self.vm
        a = max(0, vm.rw(0x41F4) - vm.rw(0x41F0))
        bonus = vm.ruw(B['KINRYOKU']) // 10
        vm.ww(0x41F0, bonus); vm.ww(0x41F4, a + bonus)
        self.sync_skills()
    def sync_evals(self):         # 0389:4732  each reputation follows the sum of its 3 skills, 0..999
        vm = self.vm
        for i in range(4):
            s = s16(sum(vm.rw(0x41D8 + 2*(3*i + k)) for k in range(3)))
            h = 0x41D0 + 2*i; last = 0x4222 + 2*i
            vm.ww(h, max(0, min(999, s16(vm.rw(h) + s - vm.rw(last))))); vm.ww(last, s)
    def clamp_base(self):         # 0389:4EEC
        vm = self.vm
        for a in B_ORDER: vm.ww(a, max(0, min(999, vm.rw(a))))
    def top_stat(self):           # 0389:4C61 -> (index 1..9, value); ties keep the earlier stat
        vm = self.vm; best, val = 1, vm.rw(B_ORDER[0])
        for i in range(1, 9):
            v = vm.rw(B_ORDER[i])
            if val < v: best, val = i + 1, v
        return best, val
    def body_type(self):          # 0389:4BA7  GIRL_BODY 1 normal / 2 fat
        vm = self.vm
        thr = s16((vm.ruw(0x4256) * 95 // 100) - 10500 + s16((18 - vm.rw(0x423E)) * 100))
        vm.set('GIRL_BODY', 2 if vm.rw(0x4258) >= thr else 1)
    def breast_type(self):        # 0389:4BD9
        self.vm.set('GIRL_BREAST', 1 if self.vm.get('URA_BREAST_TYPE') > 2 else 0)
    @staticmethod
    def _c100(v): return max(0, min(100, v))     # 0389:4CE0

    def monthly_growth(self):     # 0389:47D1
        vm = self.vm; r = self.randam
        age = vm.ruw(0x423E)
        self.breast_type()
        # height, 0.01 cm (0389:47F2)
        vm.ww(0x4256, vm.rw(0x4256) + (r(3) + 13 if age < 16 else r(5) + 2))
        # weight, 0.01 kg, by diet FLAG_KENKO (0389:481A)
        diet = vm.rw(0x4328); w = vm.rw(0x4258); tai = vm.ruw(B['TAIRYOKU'])
        if diet == 0: w += r(4) + 18 if age < 16 else r(4) + 4
        elif diet == 1:
            tai += 10; w += r(8) + 27 if age < 16 else r(6) + 14
        elif diet == 2:
            tai = max(0, tai - 5); w += r(6) + 9 if age < 16 else r(5)
        elif diet == 3:
            tai = max(0, tai - 20); w -= r(61) - 1 if age < 16 else r(51) + 49
        vm.ww(B['TAIRYOKU'], tai); vm.ww(0x4258, max(2500, min(8000, s16(w))))
        # bust by hidden breast type (0389:4930)
        bt = vm.rw(0x5B42)
        vm.ww(0x425A, vm.rw(0x425A) + (r(17) + 3 if bt == 1 else r(11) + 9 if bt == 2 else r(29) + 11))
        # waist (0389:4977)
        vm.ww(0x425C, (vm.ruw(0x4256) * 3 + 25000 + vm.ruw(0x4258) * 10) // 20)
        # hip by hidden hip type (0389:499E)
        ht = vm.rw(0x5B44)
        vm.ww(0x425E, vm.rw(0x425E) + (r(7) + 5 if ht == 1 else r(9) + 8 if ht == 2 else r(9) + 19))
        # blood type monthly effect (0389:49E5)
        bl = vm.rw(0x423A)
        if bl == 0:
            vm.ww(B['MORALS'], vm.rw(B['MORALS']) + 3); vm.ww(B['STRESS'], vm.rw(B['STRESS']) + 2)
        elif bl == 1: vm.ww(B['STRESS'], max(0, vm.rw(B['STRESS']) - 2))
        elif bl != 2: vm.ww(B['KANJUSEI'], vm.rw(B['KANJUSEI']) + 2)
        self.update_status()

    def update_status(self):      # 0389:4A34
        vm = self.vm
        stress = vm.rw(B['STRESS'])
        sick = self._c100(s16(stress - vm.rw(B['TAIRYOKU'])))
        bad = self._c100(s16(stress - max(vm.rw(B['MORALS']), vm.rw(B['SHINKOH']))))
        vm.set('S_BYOUKI', sick); vm.set('S_HIKOUKA', bad)
        f_sick = 1 if sick >= 10 else 0; f_bad = 1 if bad >= 10 else 0
        vm.set('FLAG_BYOUKI', f_sick); vm.set('FLAG_HIKOUKA', f_bad)
        vm.set('GIRL_DAMEG', 1 if sick >= 90 else 0)
        face = 1
        if f_sick and (not f_bad or bad < sick): face = 3
        elif f_bad: face = 2
        elif stress == 0: face = 4
        elif vm.rw(0x423E) != 10:
            top, val = self.top_stat()          # 0389:4C32
            if top == 5 and val >= 100 and sick < 30 and bad < 30: face = 5
        vm.set('GIRL_FACE', face)
        # romance expiry (0389:4BF0): started at E_ETC[76]/[77] (year/month)
        if vm.get('FLAG_RENAI') != 0:
            months = (vm.get('VAL_YEAR') * 12 + vm.get('VAL_MONTH')) - (vm.get('E_ETC', 76) * 12 + vm.get('E_ETC', 77))
            if months >= 3 and not (self.top_stat()[0] == 5 and vm.get('URA_FATHER') < 60):
                vm.set('FLAG_RENAI', 0)
        if vm.get('FLAG_RENAI') != 0:
            for n in ('URA_PRINCE', 'URA_FATHER', 'URA_STEWARD'): vm.set(n, max(0, vm.getu(n) - 2))
        self.body_type()
        if vm.get('GIRL_BODY') == 2: vm.ww(B['IROKE'], max(0, vm.ruw(B['IROKE']) - 2))

    # ---- the command ------------------------------------------------------------
    def cmd_CLENDER(self, vm):    # 0389:08F6
        AX, BX, CX, DX = 0x226, 0x228, 0x22A, 0x22C
        f = vm.rw(AX) & 0xFF
        if f == 3:                # advance one day
            self._advance_day(); self._flags(); self._birthdays()
            for i in (0, 1):
                vm.set('P_NENREI', self.age(vm.get('P_BORTHYEAR', i), vm.get('P_BORTHMONTH', i), vm.get('P_BORTHDAY', i)), i)
            self.sync_evals(); self.clamp_base()            # 0389:4720
        elif f == 4:              # next month: AX=year BX=month CX=days DX=weekday of tomorrow
            y, m = vm.get('VAL_YEAR'), vm.get('VAL_MONTH') + 1
            if m > 12: m = 1; y += 1
            vm.ww(AX, y); vm.ww(BX, m); vm.ww(CX, self.month_len(y, m)); vm.ww(DX, (vm.get('VAL_WEEK') + 1) % 7)
        elif f == 5: vm.ww(DX, self.age(vm.rw(BX), vm.rw(CX), vm.rw(DX)))
        elif f == 7:              # monthly growth; BX = what changed (0389:0A15)
            body, face, dmg = vm.get('GIRL_BODY'), vm.get('GIRL_FACE'), vm.get('GIRL_DAMEG')
            self.monthly_growth()
            if vm.get('GIRL_DAMEG') != dmg: r = 3 if vm.get('GIRL_DAMEG') == 1 else 2
            elif vm.get('GIRL_DAMEG') == 1: r = 0
            elif vm.get('GIRL_BODY') != body: r = 1
            elif vm.get('GIRL_FACE') != face: r = 4
            else: r = 0
            vm.ww(BX, r)
        elif f == 8:
            self._weekday(); self._flags(); self.breast_type(); self.body_type(); self.sync_evals()
        elif f == 9: self.sync_evals(); self.clamp_base()
        elif f == 10: self.breast_type(); self.body_type()
        elif f == 11:             # AX=days in month BX=tomorrow CX=tomorrow's weekday DX=month attribute
            ml = self.month_len(vm.get('VAL_YEAR'), vm.get('VAL_MONTH'))
            d = vm.get('VAL_DAY') + 1
            vm.ww(AX, ml); vm.ww(BX, 1 if d > ml else d); vm.ww(CX, (vm.get('VAL_WEEK') + 1) % 7)
            vm.ww(DX, self.month_attr())
        elif f == 12: self.sync_attack()
        elif f == 13: self.sync_skills()
        elif f == 14: self.reset_state()
        # 1, 2, 6: calendar display only
