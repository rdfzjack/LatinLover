"""Inventory / equipment commands (0389:3D30-430D) and the item effect mini-language (0000:3228).

Item arrays (50 slots): ITEM_ICON ds:435E, ITEM_GOLD ds:43C2, ITEM_ATTR ds:4426, name/prog/help string
pointers ds:448A/44EE/4552 (16/64/18 bytes per slot).  ITEM_ATTR = type*1000 + id, bit0 = equipped.
type 1 armour (EQUIP slot), 2 weapon (ARMS slot), 3 dress (DRESS slot), 4 passive item (effect applied
while owned), 5 consumable (effect applied when removed/used), 0 other.
Effect program: "VAR+n VAR-n VAR=n VAR!n ..." ; undoing swaps + and - ('-' floors at 0) and '!' clears.
"""
import re
from .vm import s16

ICON, PRICE, ATTR, NAME, PROG, HELP = 0x435E, 0x43C2, 0x4426, 0x448A, 0x44EE, 0x4552
COUNT, DIM = 0x435A, 0x435C
SLOTS = {1: (0x4346, 0x4348, 0x434A, 0x434C, 0x434E),    # EQUIP icon, gold, name, prog, help
         2: (0x4350, 0x4352, 0x4354, 0x4356, 0x4358),    # ARMS
         3: (0x433C, 0x433E, 0x4340, 0x4342, 0x4344)}    # DRESS
LENS = (16, 64, 18)


class ItemMixin:
    def run_effect(self, prog, undo=False):      # 0000:3228
        vm = self.vm
        for name, idx, op, val in re.findall(rb'([A-Za-z_][A-Za-z_0-9]*)(?:\[(\d+)\])?\s*([!+\-=])\s*(-?\d*)', prog):
            try: a = vm.addr(name.decode()) + 2 * int(idx or 0)
            except KeyError: break
            v = int(val or 0); op = op.decode()
            if op == '!': vm.ww(a, 0 if undo else 1)
            elif op == '=': vm.ww(a, v)
            elif (op == '+') != undo: vm.ww(a, vm.ruw(a) + v)
            else: vm.ww(a, max(0, vm.ruw(a) - v))
    def item_type(self, i):                      # 0389:416B -> (type, equipped)
        vm = self.vm
        if i >= vm.ruw(COUNT): return 0, 0
        a = vm.ruw(ATTR + 2*i)
        return (a // 1000 if 1000 <= a < 6000 else 0), a & 1
    def item_count(self): return self.vm.ruw(COUNT)
    def item_prog(self, i): return self.vm.cstr(self.vm.ruw(PROG + 2*i))
    def inventory(self):
        vm = self.vm
        return [dict(index=i, icon=vm.ruw(ICON+2*i), price=vm.ruw(PRICE+2*i), attr=vm.ruw(ATTR+2*i),
                     name=vm.text(vm.ruw(NAME+2*i)), prog=self.item_prog(i).decode('ascii', 'replace'))
                for i in range(vm.ruw(COUNT))]
    def _copy(self, src, dst, n):
        b = self.vm.cstr(src)[:n]
        self.vm.mem[dst:dst+n] = b + bytes(n - len(b))

    def cmd_ITEM_KILL(self, vm):                 # 0389:3D30 remove item AX
        i = vm.ruw(0x226); n = vm.ruw(COUNT)
        if n == 0: return
        t, _ = self.item_type(i)
        if t == 4: self.run_effect(self.item_prog(i), undo=True)
        elif t == 5: self.run_effect(self.item_prog(i))
        n -= 1; vm.ww(COUNT, n)
        for j in range(i, n):
            for arr in (ICON, PRICE, ATTR): vm.ww(arr + 2*j, vm.ruw(arr + 2*(j+1)))
            for arr, ln in zip((NAME, PROG, HELP), LENS):
                a, b = vm.ruw(arr + 2*j), vm.ruw(arr + 2*(j+1)); vm.mem[a:a+ln] = vm.mem[b:b+ln]
        for arr in (ICON, PRICE, ATTR): vm.ww(arr + 2*n, 0)
        for arr, ln in zip((NAME, PROG, HELP), LENS):
            a = vm.ruw(arr + 2*n); vm.mem[a:a+ln] = bytes(ln)
    def cmd_ITEM_INST(self, vm):                 # 0389:3E22 add item (BX icon, CX price, DX attr, SI name, DI prog, BP help)
        n = vm.ruw(COUNT)
        if n >= vm.ruw(DIM): vm.ww(0x226, 1); return
        vm.ww(ICON + 2*n, vm.ruw(0x228)); vm.ww(PRICE + 2*n, vm.ruw(0x22A)); vm.ww(ATTR + 2*n, vm.ruw(0x22C))
        for reg, arr, ln in ((0x22E, NAME, 16), (0x230, PROG, 64), (0x232, HELP, 18)):
            self._copy(vm.ruw(reg), vm.ruw(arr + 2*n), ln)
        vm.ww(COUNT, n + 1)
        if self.item_type(n)[0] == 4: self.run_effect(self.item_prog(n))
        vm.ww(0x226, 0)
    def _unequip(self, t):                       # 0389:3F69
        vm = self.vm
        if t not in SLOTS: return
        for i in range(vm.ruw(COUNT)):           # 0389:4214 clear 'equipped' bit in this category
            a = vm.ruw(ATTR + 2*i)
            if t*1000 <= a < t*1000 + 1000: vm.ww(ATTR + 2*i, a & 0xFFFE)
        icon, gold, name, prog, hlp = SLOTS[t]
        self.run_effect(vm.cstr(vm.ruw(prog)), undo=True)
        vm.ww(icon, 0); vm.ww(gold, 0)
        for p, ln in zip((name, prog, hlp), LENS):
            a = vm.ruw(p); vm.mem[a:a+ln] = bytes(ln)
        if t == 3: vm.ww(0x433A, 0)
    def equip(self, i):                          # 0389:4031
        vm = self.vm
        if i >= vm.ruw(COUNT): return
        t, _ = self.item_type(i)
        if t not in SLOTS: return
        self._unequip(t)
        vm.ww(ATTR + 2*i, vm.ruw(ATTR + 2*i) | 1)
        icon, gold, name, prog, hlp = SLOTS[t]
        vm.ww(icon, vm.ruw(ICON + 2*i)); vm.ww(gold, vm.ruw(PRICE + 2*i))
        for p, arr, ln in zip((name, prog, hlp), (NAME, PROG, HELP), LENS):
            self._copy(vm.ruw(arr + 2*i), vm.ruw(p), ln)
        self.run_effect(vm.cstr(vm.ruw(prog)))
        if t == 3: vm.ww(0x433A, vm.ruw(icon) - 42)   # DRESS_NUM (0389:4161)
    def cmd_ITEM_SRCH(self, vm):                 # 0389:3E9F
        f, b = vm.rw(0x226) & 0xFF, vm.ruw(0x228)
        if f in (1, 2):                          # find (next) item by icon -> AX found, DX index
            start = 0 if f == 1 else getattr(self, '_srch_pos', 0)
            if f == 1: self._srch_icon = b
            for i in range(start, vm.ruw(COUNT)):
                if vm.ruw(ICON + 2*i) == self._srch_icon:
                    self._srch_pos = i + 1; vm.ww(0x226, 1); vm.ww(0x22C, i); return
            self._srch_pos = vm.ruw(COUNT); vm.ww(0x226, 0); vm.ww(0x22C, 0)
        elif f == 3:                             # AX = type, DX = equipped flag
            t, e = self.item_type(b); vm.ww(0x226, t); vm.ww(0x22C, e)
        elif f == 5: self._unequip(b)
        elif f in (4, 6): self.equip(b)
