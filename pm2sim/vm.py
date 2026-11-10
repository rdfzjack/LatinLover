"""PM2 script virtual machine.

PM2.EXE is a script compiler + VM; all game rules live in the *.TXT scripts inside TX*.LBX.
This module re-implements the VM semantics read from the EXE (addresses are seg:off in the
unrelocated image; seg 0000 = compiler/VM, 0389 = engine, 15E3 = data segment "DS").

Semantics (with source addresses):
  * all values are signed 16-bit words living in DS; registers AX,BX,CX,DX,SI,DI,BP,ES,C1..C8
    are plain DS words at 0226.. (symbol table 21F1:0000 names, 22F0:0000 far pointers).
  * line indent = number of leading TABs (0000:1141).  ';' or ':' start a comment (0000:1B50).
  * expression `X = a op b op c`: strict left-to-right accumulator, no precedence
    (0000:1E5D compile, 0000:1433-1557 exec). mul = low 16 bits of imul, div = idiv
    truncating toward zero, divide by zero leaves the accumulator unchanged (0000:1466,152C).
  * IF ( c1 c2 )( c3 ): conditions inside one paren group are ANDed, groups are ORed
    (0000:17E4-1A93, flag word 23E6 shifted by opcode 1A).  Comparisons are signed,
    lhs must be a variable, rhs variable or constant; operators = ! < > <= >= (0000:2343).
    A false IF jumps to the next non-blank line whose indent <= the IF line (0000:28B6).
  * LOOP v: if v==0 fall through; v-=1; if v==0 fall through; else jump back to the first
    line of the deeper-indented block immediately above (0000:159F exec, 0000:290C target).
  * calls: numeric args go to AX,BX,CX,DX,SI,DI.. in order (opcodes 19/1A/1B, 0000:16BD);
    a string literal arg is copied to a temp buffer and its address stored in SI (opcode 08).
  * bare label name = GOSUB (return stack 0000:2ACF); RET with empty stack restarts the
    program from its first line (0000:1655).
  * LOAD("A,B") replaces the program with file A followed by file B, clears the return
    stack and the user symbol table (0000:05D0-06F8).
  * `.NAME[n]=v,v,"s"` allocates n words in the user area and stores initial values once,
    at compile time of that line, i.e. the first time the line is reached (0000:2BB0).
"""
import struct, re

DS_SEG = 0x15E3
EXE_HEADER = 4432
DS_FILE_OFF = EXE_HEADER + DS_SEG * 16
SYM_NAMES_OFF = EXE_HEADER + 0x21F10      # length-prefixed names
SYM_PTRS_OFF = EXE_HEADER + 0x22F00       # far pointers (off, seg)

USER_AREA = 0x8000      # '.' variables (real game: separate area, 0000:2D7B)
DEFSTR_AREA = 0xA000    # strings in '.' definitions
STRSTACK_AREA = 0xC000  # string stack, 0x800 bytes (ds:11A6 used, ds:11A8 size)
STRSTACK_SIZE = 0x800
LITBUF = 0xE000         # temp buffer for string literal call args (ds:10A2)
EMPTY_STR = 0xE7F0


class LoadProgram(Exception):
    def __init__(self, names): self.names = names

class EndProgram(Exception):
    pass

class ScriptError(Exception):
    pass


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


class Line:
    __slots__ = ('raw', 'indent', 'ops', 'body', 'defined')
    def __init__(self, raw):
        n = 0
        while n < len(raw) and raw[n] == 9: n += 1
        self.raw = raw; self.indent = n; self.body = raw[n:]; self.ops = None; self.defined = False


class VM:
    def __init__(self, exe_bytes, script_source, engine=None):
        """script_source(name) -> bytes (decoded Big5 script text) or None."""
        self.mem = bytearray(0x10000)
        ds = exe_bytes[DS_FILE_OFF:DS_FILE_OFF + 0x8000]
        self.mem[:len(ds)] = ds
        self.builtin_syms = {}   # name -> (seg, off)
        a = SYM_NAMES_OFF; i = 0
        while exe_bytes[a]:
            n = exe_bytes[a]; name = exe_bytes[a+1:a+1+n].decode('ascii'); a += 1 + n
            off, seg = struct.unpack_from('<HH', exe_bytes, SYM_PTRS_OFF + i*4); i += 1
            self.builtin_syms[name] = (seg, off)
        self.vars = {n: o for n, (s, o) in self.builtin_syms.items() if s == DS_SEG}
        self.reg = {n: self.vars[n] for n in ('AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'BP', 'ES')}
        self.script_source = script_source
        self.engine = engine
        self.commands = {}       # builtin name -> python callable(vm)
        self.lines = []; self.labels = {}; self.user = {}
        self.user_ptr = USER_AREA; self.defstr_ptr = DEFSTR_AREA
        self.stack = []; self.pc = (0, 0)
        self.strstack_used = 0
        self.halted = False
        self.program_names = []
        self.trace = None
        self.warnings = []
        self.steps = 0

    # ---- memory -------------------------------------------------------
    def rw(self, addr):
        addr &= 0xFFFF
        v = self.mem[addr] | (self.mem[(addr + 1) & 0xFFFF] << 8)
        return v - 0x10000 if v & 0x8000 else v
    def ruw(self, addr):
        addr &= 0xFFFF
        return self.mem[addr] | (self.mem[(addr + 1) & 0xFFFF] << 8)
    def ww(self, addr, v):
        addr &= 0xFFFF; v &= 0xFFFF
        self.mem[addr] = v & 0xFF; self.mem[(addr + 1) & 0xFFFF] = v >> 8
    def get(self, name, idx=0): return self.rw(self.addr(name) + 2*idx)
    def getu(self, name, idx=0): return self.ruw(self.addr(name) + 2*idx)
    def set(self, name, v, idx=0): self.ww(self.addr(name) + 2*idx, v)
    def addr(self, name):
        if name in self.vars: return self.vars[name]
        if name in self.user: return self.user[name]
        raise KeyError(name)
    def cstr(self, addr):
        addr &= 0xFFFF
        e = self.mem.find(b'\0', addr)
        return bytes(self.mem[addr:e if e >= 0 else 0x10000])
    def text(self, addr): return self.cstr(addr).decode('big5', 'replace')
    def put_cstr(self, addr, b):
        addr &= 0xFFFF
        self.mem[addr:addr+len(b)] = b; self.mem[addr+len(b)] = 0
    def push_string(self, b):
        """string stack push (0000:1782 / STRSTACK 0000:02D5); returns pointer."""
        if len(b) == 0: return EMPTY_STR
        if len(b) + 1 > STRSTACK_SIZE - self.strstack_used: return EMPTY_STR
        p = STRSTACK_AREA + self.strstack_used
        self.put_cstr(p, b); self.strstack_used += len(b) + 1
        return p

    # ---- program loading ---------------------------------------------
    def load(self, names):
        """LOAD("A,B") (0000:05D0)."""
        names = [n.strip() for n in names.split(',') if n.strip()]
        raw = b''
        for n in names:
            src = self.script_source(n)
            if src is None: raise ScriptError('file not found: %s' % n)
            if raw and not raw.endswith(b'\n'): raw += b'\r\n'
            raw += src
        self.program_names = names
        self.lines = [Line(l.rstrip(b'\r')) for l in raw.split(b'\n')]
        self.lines = [l for l in self.lines if l.body.strip(b' \t')]
        self.labels = {}
        for i, l in enumerate(self.lines):
            if l.body[:1] == b'*':
                m = re.match(rb'\*([^\s]+)', l.body)
                self.labels.setdefault(m.group(1).decode('latin-1'), i)
        self.user = {}; self.user_ptr = USER_AREA; self.defstr_ptr = DEFSTR_AREA
        self.stack = []; self.pc = (0, 0)

    # ---- tokenizer / line compiler -------------------------------------
    IDENT = re.compile(rb'[A-Za-z_0-9]+')
    NUM = re.compile(rb'-?[0-9]+')

    def _skip(self, b, i):
        while i < len(b) and b[i] in (0x20, 9): i += 1
        return i

    def _operand(self, b, i):
        """number | var | var[idx] -> (('n', value) | ('v', addr, idxaddr|None), newpos)"""
        i = self._skip(b, i)
        m = self.IDENT.match(b, i)
        if not m:
            m2 = self.NUM.match(b, i)
            if m2: return ('n', int(m2.group())), m2.end()
            raise ScriptError('operand expected: %r' % b[i:i+20])
        tok = m.group().decode()
        if tok.isdigit(): return ('n', int(tok)), m.end()
        if tok[0].isdigit() and tok[-1] in 'Hh':
            return ('n', int(tok[:-1], 16)), m.end()
        return self._varref(b, tok, m.end())

    def _varref(self, b, tok, i):
        try: base = self.addr(tok)
        except KeyError: raise ScriptError('symbol undefined: %s' % tok)
        j = self._skip(b, i)
        if j < len(b) and b[j] == 0x5B:   # '['
            k = b.index(b']', j)
            inner = b[j+1:k].strip()
            if re.fullmatch(rb'-?[0-9]+', inner):
                return ('v', base + 2*int(inner), None), k + 1
            return ('v', base, self.addr(inner.decode())), k + 1
        return ('v', base, None), i

    def _string(self, b, i):
        q = b[i]; j = i + 1; out = bytearray()
        while j < len(b) and b[j] != q:
            if b[j] >= 0x80 and j + 1 < len(b): out += b[j:j+2]; j += 2
            else: out.append(b[j]); j += 1
        return bytes(out), j + 1

    def _args(self, b, i):
        """( a, b, "s" ) -> list of ('n'..)/('v'..)/('s', bytes); returns (args, newpos)."""
        j = self._skip(b, i)
        if j >= len(b) or b[j] != 0x28: return [], i
        j += 1; args = []
        while True:
            j = self._skip(b, j)
            if j >= len(b): break
            c = b[j]
            if c == 0x29: j += 1; break
            if c == 0x2C: j += 1; continue
            if c in (0x22, 0x27):
                s, j = self._string(b, j); args.append(('s', s)); continue
            op, j = self._operand(b, j); args.append(op)
        return args, j

    def compile_line(self, line):
        b = line.body; i = 0; ops = []; text = bytearray()
        def flush():
            if text: ops.append(('text', bytes(text))); text.clear()
        while True:
            i = self._skip(b, i)
            if i >= len(b): break
            c = b[i]
            if c >= 0x80:
                text += b[i:i+2]; i += 2; continue
            if c in (0x22, 0x27):
                s, i = self._string(b, i); text += s; continue
            if c in (0x3B, 0x3A): break
            if c == 0x2A:
                while i < len(b) and b[i] not in (0x20, 9): i += 1
                continue
            if c == 0x40:
                flush(); ops.append(('ctl', b[i:i+2])); i += 2; continue
            if c == 0x2E:
                flush(); i = self._define(b, i, ops); continue
            m = self.IDENT.match(b, i)
            if not m: raise ScriptError('cannot compile: %r' % b[i:i+30])
            tok = m.group().decode(); i = m.end(); flush()
            if tok == 'IF':
                groups = [[]]
                while True:
                    i = self._skip(b, i)
                    if i < len(b) and b[i] == 0x28:
                        i += 1
                        while True:
                            i = self._skip(b, i)
                            if b[i] == 0x29: i += 1; break
                            cond, i = self._cond(b, i); groups[-1].append(cond)
                        j = self._skip(b, i)
                        if j < len(b) and b[j] == 0x28: groups.append([]); i = j; continue
                        break
                    cond, i = self._cond(b, i); groups[-1].append(cond); break
                ops.append(('if', groups))
            elif tok == 'GOTO':
                i = self._skip(b, i); m = re.compile(rb'[^\s]+').match(b, i)
                ops.append(('goto', m.group().decode('latin-1'))); i = m.end()
            elif tok == 'RET': ops.append(('ret',))
            elif tok == 'LOOP':
                op, i = self._operand(b, i); ops.append(('loop', op))
            elif tok in self.labels:
                args, i = self._args(b, i); ops.append(('gosub', tok, args))
            elif tok in self.vars or tok in self.user:
                i = self._assign(b, tok, i, ops)
            elif tok in self.builtin_syms:
                args, i = self._args(b, i); ops.append(('call', tok, args))
            else:
                raise ScriptError('symbol undefined: %s' % tok)
        flush()
        return ops

    def _cond(self, b, i):
        lhs, i = self._operand(b, i)
        if lhs[0] != 'v': raise ScriptError('IF lhs must be variable')
        i = self._skip(b, i)
        two = b[i:i+2]
        if two in (b'<=', b'=<'): op = '<='; i += 2
        elif two in (b'>=', b'=>'): op = '>='; i += 2
        elif b[i:i+1] == b'=': op = '='; i += 1
        elif b[i:i+1] == b'<': op = '<'; i += 1
        elif b[i:i+1] == b'>': op = '>'; i += 1
        elif b[i:i+1] == b'!': op = '!'; i += 1
        else: return (lhs, 'nz', None), i
        rhs, i = self._operand(b, i)
        return (lhs, op, rhs), i

    def _assign(self, b, tok, i, ops):
        dest, i = self._varref(b, tok, i)
        i = self._skip(b, i)
        two = b[i:i+2]
        if two == b'++': ops.append(('inc', dest)); return i + 2
        if two == b'--': ops.append(('dec', dest)); return i + 2
        first = None
        if two in (b'+=', b'-=', b'*=', b'/='):
            first = chr(two[0]); i += 2
        elif b[i:i+1] == b'=':
            i += 1
            j = self._skip(b, i)
            if j < len(b) and b[j] in (0x22, 0x27):
                s, i = self._string(b, j); ops.append(('sets', dest, s)); return i
        else:
            # bare variable reference: opcode 17 store of an empty accumulator (0000:2151)
            ops.append(('expr', dest, [])); return i
        terms = []
        if first:   # X op= expr  ==  acc = X; acc op expr...; X = acc  (0000:1EDB)
            terms.append(('=', dest))
            op = first
        else: op = '='
        while True:
            operand, i = self._operand(b, i); terms.append((op, operand))
            j = self._skip(b, i)
            if j < len(b) and b[j:j+1] in (b'+', b'-', b'*', b'/') and b[j:j+2] not in (b'++', b'--'):
                op = chr(b[j]); i = j + 1; continue
            break
        ops.append(('expr', dest, terms)); return i

    def _define(self, b, i, ops):
        m = self.IDENT.match(b, i + 1)
        name = m.group().decode(); i = m.end(); dim = 1
        j = self._skip(b, i)
        if j < len(b) and b[j] == 0x5B:
            k = b.index(b']', j); dim = int(b[j+1:k].strip() or b'1'); i = k + 1
        vals = []
        j = self._skip(b, i)
        if j < len(b) and b[j] == 0x3D:
            j += 1
            while True:
                j = self._skip(b, j)
                if j < len(b) and b[j] in (0x22, 0x27):
                    s, j = self._string(b, j); vals.append(('s', s))
                else:
                    m2 = self.NUM.match(b, j)
                    if not m2: break
                    vals.append(('n', int(m2.group()))); j = m2.end()
                k = self._skip(b, j)
                if k < len(b) and b[k] == 0x2C: j = k + 1; continue
                break
            i = j
        # definition takes effect at compile time
        if name not in self.user:
            self.user[name] = self.user_ptr; self.user_ptr += 2 * max(dim, 1)
        base = self.user[name]
        for n, (kind, v) in enumerate(vals):
            if kind == 's':
                p = self.defstr_ptr; self.put_cstr(p, v); self.defstr_ptr += len(v) + 1; v = p
            self.ww(base + 2*n, v)
        return i

    # ---- execution ------------------------------------------------------
    def _ea(self, ref):
        _, base, idx = ref
        return base + 2 * self.rw(idx) if idx is not None else base
    def _val(self, operand):
        return operand[1] if operand[0] == 'n' else self.rw(self._ea(operand))

    def _set_args(self, args):
        n = 0; regs = (0x226, 0x228, 0x22A, 0x22C, 0x22E, 0x230, 0x232, 0x234)
        for a in args:
            if a[0] == 's':
                self.put_cstr(LITBUF, a[1]); self.ww(0x22E, LITBUF)
            else:
                self.ww(regs[n], self._val(a)); n += 1

    def _target_after_block(self, li):
        ind = self.lines[li].indent; j = li + 1
        while j < len(self.lines) and self.lines[j].indent > ind: j += 1
        return j

    def step_line(self):
        li, oi = self.pc
        if li >= len(self.lines):
            raise EndProgram('fell off end of %s' % self.program_names)
        line = self.lines[li]
        if line.ops is None:
            try: line.ops = self.compile_line(line)
            except (ScriptError, KeyError, ValueError, IndexError) as e:
                self.warnings.append((self.program_names[:], li, line.body, str(e)))
                self.pc = (li + 1, 0); return
        ops = line.ops
        if self.trace and oi == 0: self.trace(self, li, line)
        while oi < len(ops):
            op = ops[oi]; oi += 1; k = op[0]
            if k == 'expr':
                acc = 0
                for o, operand in op[2]:
                    v = self._val(operand)
                    if o == '=': acc = v
                    elif o == '+': acc = s16(acc + v)
                    elif o == '-': acc = s16(acc - v)
                    elif o == '*': acc = s16(acc * v)
                    elif o == '/':
                        if v != 0:
                            q = abs(acc) // abs(v)
                            acc = s16(-q if (acc < 0) != (v < 0) else q)
                self.ww(self._ea(op[1]), acc)
            elif k == 'if':
                ok = False
                for g in op[1]:
                    t = True
                    for lhs, o, rhs in g:
                        a = self.rw(self._ea(lhs))
                        if o == 'nz': r = a != 0
                        else:
                            v = self._val(rhs)
                            r = (a == v if o == '=' else a != v if o == '!' else a < v if o == '<'
                                 else a > v if o == '>' else a <= v if o == '<=' else a >= v)
                        if not r: t = False
                    if t: ok = True
                if not ok:
                    self.pc = (self._target_after_block(li), 0); return
            elif k == 'call':
                self._set_args(op[2])
                self.pc = (li, oi)
                fn = self.commands.get(op[1])
                if fn is None: self.engine.unknown(self, op[1])
                else: fn(self)
                if self.pc != (li, oi): return     # LOAD / program change
            elif k == 'gosub':
                self._set_args(op[2])
                self.stack.append((li, oi))
                self.pc = (self.labels[op[1]], 0); return
            elif k == 'goto':
                if op[1] not in self.labels:
                    self.warnings.append((self.program_names[:], li, line.body, 'undefined label')); continue
                self.pc = (self.labels[op[1]], 0); return
            elif k == 'ret':
                self.pc = self.stack.pop() if self.stack else (0, 0); return
            elif k == 'loop':
                ea = self._ea(op[1]); c = self.ruw(ea)
                if c != 0:
                    c -= 1; self.ww(ea, c)
                    if c != 0:
                        j = li
                        while j > 0 and self.lines[j-1].indent > line.indent: j -= 1
                        self.pc = (j, 0); return
            elif k == 'inc': ea = self._ea(op[1]); self.ww(ea, self.rw(ea) + 1)
            elif k == 'dec': ea = self._ea(op[1]); self.ww(ea, self.rw(ea) - 1)
            elif k == 'sets': self.ww(self._ea(op[1]), self.push_string(op[2]))
            elif k == 'text': self.engine.text(self, op[1])
            elif k == 'ctl': self.engine.control(self, op[1])
        self.pc = (li + 1, 0)

    def run(self, max_steps=None):
        while not self.halted:
            try:
                self.step_line()
            except LoadProgram as e:
                self.load(e.names)
            self.steps += 1
            if max_steps and self.steps >= max_steps: return False
        return True
