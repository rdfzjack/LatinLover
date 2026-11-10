"""Native (EXE-side) commands of PM2, re-implemented from the disassembly.

Each command documents its entry point in PM2.EXE (unrelocated seg:off).
Registers are DS words: AX=0226 BX=0228 CX=022A DX=022C SI=022E DI=0230.
"""
from .vm import VM, LoadProgram, EndProgram, s16, LITBUF
from .calendar import CalendarMixin

AX, BX, CX, DX, SI, DI = 0x226, 0x228, 0x22A, 0x22C, 0x22E, 0x230
GOLD = 0x422A            # 32-bit (lo, hi)
GOLD_MAX = 0x5D0C        # 32-bit cap = 99,999,999 ... stored in EXE (ds:5D0C)
RNG_OFFSET, RNG_INDEX, RNG_TABLE = 0x6744, 0x6746, 0x6748
IRND, IRND2 = 0x6740, 0x6742

# pure display / sound / timing commands: no effect on game state
NOOPS = '''PR PRES PRF PRV PRVH PRVB PRINT STR HEX BIN LLF CLS SLCTBAK SLCPOS FREE TXTSZ
TXOPEN TXCLOSE TXT TXPAUSE TXCLR TXLF TXFACE TXGIRL TXGIRK TXSYU TXLC TXF
GR_OPEN GR_CLOSE GR_F GRPOPEN GRPUPD GOLDOPEN GOLDUPD PROFILE PROPROPEN PROPRUPD STATUS PROLONG PRICON
TIMER1 TIMER2 WAIT1 WAIT2 SCHD_OPEN SCHD_CLOSE SCHD_ICON PALET_SET PALET_SETONLY
WWFRAME WWGIRL WWANIME WWIVENT WWPROF WWTOUR P98F PTBK PTMD PTLD PTLA PTX PTM PTF PTMF PTMFX PTCLR PTGT PTPLT
EFC PIC MUSIC PLAY GG_LINE XDBG GRPCLS ITEMPRN EDTX'''.split()


class Driver:
    """Supplies the player's decisions. Override in subclasses."""
    def select(self, eng, kind, options): return 0
    def wait(self, eng, kind): pass
    def profile(self, eng): pass
    def disk(self, eng, func, arg): return 0


class Engine(CalendarMixin):
    def __init__(self, assets, driver=None, reseed=None):
        self.assets = assets
        self.vm = VM(assets.exe, assets.script, self)
        self.driver = driver or Driver()
        self.reseed = reseed or (lambda: 0)   # timer value used at RNG reseed (0389:C06C)
        self.log = []          # text output
        self._line = ''
        self.rng_draws = 0
        vm = self.vm
        for n in NOOPS: vm.commands[n] = lambda vm: None
        for name in dir(self):
            if name.startswith('cmd_'): vm.commands[name[4:]] = getattr(self, name)

    # ---- text -----------------------------------------------------------
    def emit(self, s):
        self._line += s
    def flush_text(self):
        if self._line.strip(): self.log.append(self._line)
        self._line = ''
    def text(self, vm, b):
        self.emit(b.decode('big5', 'replace'))
        self.flush_text()
    def control(self, vm, code):
        self.flush_text()
        if code == b'@P': self.driver.wait(self, 'page')
    def unknown(self, vm, name):
        raise NotImplementedError('command %s (args AX=%d BX=%d CX=%d DX=%d) in %s line %r' % (
            name, vm.rw(AX), vm.rw(BX), vm.rw(CX), vm.rw(DX), vm.program_names, vm.lines[vm.pc[0]].body))

    def cmd_TXA(self, vm):        # 0389:0590 print string at AX
        self.emit(vm.text(vm.ruw(AX)))
    def cmd_TXGOLD(self, vm):     # 0389:0598 print number + gold unit
        self.emit('%dG' % vm.ruw(AX))
    def cmd_TXPOINT(self, vm):    # 0389:05A6
        self.emit('%d' % vm.rw(AX))
    def cmd_TXS2KETA(self, vm):   # 0389:05B4
        self.emit('%02d' % vm.rw(AX))

    # ---- arithmetic helpers (seg 0000) -------------------------------------
    def cmd_ABS(self, vm):        # 0000:0111
        vm.ww(AX, abs(vm.rw(AX)))
    def cmd_MOD(self, vm):        # 0000:011F  AX = AX mod BX (idiv remainder), 0 if BX==0
        a, b = vm.rw(AX), vm.rw(BX)
        if b == 0: vm.ww(AX, 0); return
        r = abs(a) % abs(b)
        vm.ww(AX, -r if a < 0 else r)
    def cmd_P1X100(self, vm):     # 0000:013A  AX = AX*BX/100 (unsigned)
        vm.ww(AX, (vm.ruw(AX) * vm.ruw(BX)) // 100)
    def cmd_P100PAR(self, vm):    # 0000:014A  AX = (10000/BX)*AX/100 ; BX==0 -> 100
        b = vm.ruw(BX)
        if b == 0: vm.ww(AX, 100); return
        vm.ww(AX, ((10000 // b) * vm.ruw(AX) & 0xFFFFFFFF) // 100)
    def cmd_CK_LVL(self, vm):     # 0000:03D6  (n, v0, v1, v2, v3) -> AX=level 0..3, DX=v[level]
        n = vm.ruw(AX)
        if n <= 5: lvl, v = 0, vm.rw(BX)
        elif n <= 10: lvl, v = 1, vm.rw(CX)
        elif n <= 15: lvl, v = 2, vm.rw(DX)
        else: lvl, v = 3, vm.rw(SI)
        vm.ww(AX, lvl); vm.ww(DX, v)
    def cmd_CK_GUARA(self, vm):   # 0000:0429  (times_worked, base_wage) -> AX=rank 0..4, DX=daily wage
        n, base = vm.ruw(AX), vm.ruw(BX)
        def raised(pct):          # 0000:04DE  ceil(base*pct/100)+base
            q, r = divmod(pct * base, 100)
            return (q + (1 if r else 0) + base) & 0xFFFF
        s = vm.rw(AX)
        if s in (-1, -2, -3, -4): rank = -s
        else: rank = 0 if n < 10 else 1 if n < 30 else 2 if n < 60 else 3 if n < 90 else 4
        pay = (base, raised(20), max(raised(44), 3), max(raised(73), 4), max(raised(108), 5))[rank]
        vm.ww(AX, rank); vm.ww(DX, pay)

    # ---- strings (seg 0000) --------------------------------------------------
    def cmd_STRSCLEAR(self, vm):  # 0000:02CE
        vm.strstack_used = 0
    def cmd_STRSTACK(self, vm):   # 0000:02D5  push copy of string SI; BX=ptr, AX=0 ok
        p = vm.push_string(vm.cstr(vm.ruw(SI)))
        vm.ww(BX, p); vm.ww(AX, 0)
    def cmd_STRCOPY(self, vm):    # 0000:0391  copy string SI -> AX
        vm.put_cstr(vm.ruw(AX), vm.cstr(vm.ruw(SI)))
    def cmd_STRLEN(self, vm):     # 0000:03AF
        vm.ww(AX, len(vm.cstr(vm.ruw(AX))))
    def cmd_VALSTR(self, vm):     # 0389:0AF2 number -> string (display only)
        vm.ww(AX, vm.push_string(b'%d' % vm.rw(AX)))

    # ---- program control -------------------------------------------------------
    def cmd_LOAD(self, vm):       # 0000:03BF
        self.flush_text()
        raise LoadProgram(vm.cstr(vm.ruw(SI)).decode('ascii'))
    def cmd_END(self, vm):        # 0000:02C7
        vm.halted = True

    # ---- gold (0389:4D01..) ------------------------------------------------------
    def gold(self):
        vm = self.vm
        v = vm.ruw(GOLD) | (vm.ruw(GOLD + 2) << 16)
        return v - (1 << 32) if v & 0x80000000 else v
    def set_gold(self, v):
        self.vm.ww(GOLD, v & 0xFFFF); self.vm.ww(GOLD + 2, (v >> 16) & 0xFFFF)
    def cmd_GOLDADD(self, vm):    # 0389:4D01  capped at ds:5D0C (dword)
        cap = vm.ruw(GOLD_MAX) | (vm.ruw(GOLD_MAX + 2) << 16)
        self.set_gold(min(self.gold() + vm.ruw(AX), cap))
    def cmd_GOLDSUB(self, vm):    # 0389:4D34  floor at 0
        self.set_gold(max(self.gold() - vm.ruw(AX), 0))
    def cmd_GOLDSUB2(self, vm):   # 0389:4D54  may go negative (debt)
        self.set_gold(self.gold() - vm.ruw(AX))
    def cmd_GOLDCMP(self, vm):    # 0389:4D5E  AX: 1 gold==n, 2 gold<n, 3 gold>n
        g, n = self.gold(), vm.ruw(AX)
        vm.ww(AX, 1 if g == n else 2 if g < n else 3)

    # ---- random numbers (0389:813D..8224) ---------------------------------------
    def rnd(self):
        """0389:81DA: 1..200 from a fixed 200-byte permutation table (ds:6748) plus an offset
        (ds:6744) taken from the timer every 200 draws (0389:8211)."""
        vm = self.vm
        idx = vm.ruw(RNG_INDEX)
        if idx >= 200:
            vm.ww(RNG_OFFSET, self.reseed() % 200); idx = 0
        v = vm.mem[RNG_TABLE + idx] + vm.ruw(RNG_OFFSET)
        while v > 200: v -= 200
        if v == 0: v = 1
        vm.ww(RNG_INDEX, idx + 1)
        self.rng_draws += 1
        return v
    def randam(self, n):
        """0389:813D RANDAM(n): uniform 1..n (n capped at 200); n<=1 -> 1 without drawing."""
        vm = self.vm
        if n <= 1:
            vm.ww(IRND, 1); return 1
        c = min(n, 200)
        r = (self.rnd() - 1) * 100 // (20000 // c) + 1
        r = min(r, c)
        vm.ww(IRND, r); vm.ww(IRND2, r)
        return r
    def irand999(self, n):
        """0389:8186 IRAND999X(n): 0..n (n capped at 999) using two draws; n<=1 -> n."""
        vm = self.vm
        if n <= 1:
            vm.ww(IRND, n); return n
        r1 = self.rnd(); r2 = self.rnd()
        v = (r2 % 5) * 200 + (r1 - 1)
        c = min(n, 999)
        r = min(v * 100 // (99900 // c), c)
        vm.ww(IRND, r); vm.ww(IRND2, r)
        return r
    def cmd_RANDAM(self, vm):     # 0389:0A76
        vm.ww(AX, self.randam(vm.ruw(AX)))
    def cmd_IRAND2(self, vm):     # 0389:0A80  AX = a + RANDAM(b-a+1) - 1
        a, b = vm.ruw(AX), vm.ruw(BX)
        vm.ww(AX, a + self.randam((b - a + 1) & 0xFFFF) - 1)
    def cmd_IRAND999X(self, vm):  # 0389:0A91
        vm.ww(AX, self.irand999(vm.ruw(AX)))
    def cmd_IRNDPAR(self, vm):    # 0389:0A9B  AX = max(0, a + IRAND999X(t) - t/2), t = a*(2*pct)/100
        a = vm.ruw(AX); t = (a * ((vm.ruw(BX) * 2) & 0xFFFF)) // 100 & 0xFFFF
        r = self.irand999(t)
        vm.ww(AX, max(0, s16(a + r - (t >> 1))))

    # ---- menus -------------------------------------------------------------------
    def _menu(self, vm, kind):    # 0000:016F  SI = "opt1,opt2,..."; ISLCT = index or -1
        self.flush_text()
        opts = vm.text(vm.ruw(SI)).split(',')
        r = self.driver.select(self, kind, opts)
        vm.set('ISLCT', r)
    def cmd_SLCT(self, vm): self._menu(vm, 'SLCT')
    def cmd_SLCTX(self, vm): self._menu(vm, 'SLCTX')     # 0000:0187 no-cancel variant
    def cmd_WAITU(self, vm): self.flush_text(); self.driver.wait(self, 'key')

    # ---- PARC: external "parts" (COM overlays) and misc (0389:0EEA) ------------------
    def cmd_PARC(self, vm):
        f = vm.rw(AX) & 0xFF
        if f == 1:                # load part SI and call function BX with arg CX (0389:1330/136E)
            self.part = vm.cstr(vm.ruw(SI)).decode('ascii')
            vm.ww(AX, 0)
            vm.ww(BX, self.call_part(vm, self.part, vm.rw(BX), vm.rw(CX)))
        elif f == 2:              # call function BX of the loaded part; BX = result
            vm.ww(BX, self.call_part(vm, self.part, vm.rw(BX), vm.rw(CX)))
        elif f == 4: vm.ww(AX, 0)     # wait for TIMER1 / click: 0 timeout, 1/2 click (0389:0F96)
        elif f == 6: vm.ww(AX, 0)     # EMS available?
        elif f == 9: vm.ww(AX, 0); vm.ww(BX, 0)
        elif f == 11:             # PM2.CNF: AX=1 found, BX=MUSIC, CX=EMS (0389:1270)
            vm.ww(AX, 1); vm.ww(BX, 0); vm.ww(CX, 0)
    part = None
    def call_part(self, vm, part, func, arg):
        h = getattr(self, 'part_' + part.split('.')[0], None)
        if h is None:
            raise NotImplementedError('part %s func %d' % (part, func))
        return h(vm, func, arg) or 0

    def reset_state(self):        # CLENDER(14), 0389:3B90: clear the whole game state
        vm = self.vm
        for a, n in ((0x41BC, 0x14), (0x41D0, 0x5A), (0x422A, 4), (0x423A, 0x26), (0x4260, 0x20), (0x4288, 0x20),
                     (0x42AE, 0x20), (0x42D6, 0x20), (0x42FC, 0xA), (0x4306, 0x2C), (0x433A, 6), (0x4346, 4),
                     (0x4350, 4), (0x435A, 2), (0x435E, 0x64), (0x43C2, 0x64), (0x4426, 0x64), (0x45B6, 0x10),
                     (0x45C6, 0x40), (0x4606, 0x12), (0x4618, 0x10), (0x4938, 0x40), (0x55B8, 0x12), (0x593C, 0x10),
                     (0x594C, 0x40), (0x598C, 0x12), (0x599E, 0x10), (0x59AE, 0x40), (0x59EE, 0x12), (0x5A00, 0x142),
                     (0x5B42, 0xE), (0x5B50, 0x126), (0x5C76, 0x1C), (0x5C96, 0x10)):
            vm.mem[a:a+n] = bytes(n)
        vm.ww(0x4338, 5)          # ROOM_PIC

    MAIN_MENU = ['日程', '狀態', '談話', '健康', '資料', '街道', '王城', '持有物', '守護神']
    def part_MIMA(self, vm, func, arg):       # MIMA.COM: main screen icon menu
        if func == 101:
            self.flush_text()
            return self.driver.select(self, 'MAIN', self.MAIN_MENU)
        return 0
    def part_NAMEIN(self, vm, func, arg):     # NAMEIN.COM: name / birthday / blood type entry
        self.driver.profile(self)
    def part_DSKTOOL(self, vm, func, arg): return self.driver.disk(self, func, arg)
    def part_ENDING(self, vm, func, arg): return 0
    def cmd_FFDISK(self, vm):     # 0389:0530 floppy-disk management; (4) -> AX=1 when running from HDD
        if vm.rw(AX) & 0xFF == 4: vm.ww(AX, 1)
