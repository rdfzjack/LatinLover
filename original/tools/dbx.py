"""Drive DOSBox under Xvfb: start, keys, mouse, screenshot, guest memory peek/poke via /proc/pid/mem."""
import subprocess, os, time, re, struct, sys
DISPLAY=':99'
ENV=dict(os.environ, DISPLAY=DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy')
def sh(cmd): return subprocess.run(cmd, shell=True, env=ENV, capture_output=True, text=True).stdout
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = """[sdl]
fullscreen=false
output=surface
autolock=false
usescancodes=false
[dosbox]
machine=svga_s3
memsize=16
[render]
aspect=false
scaler=none
[cpu]
core=normal
cycles=fixed 3000
[mixer]
nosound=true
[autoexec]
mount c %s
c:
PM2
"""
def start():
    """Copy the game to work/run/PM2 (so the originals stay untouched) and launch it under Xvfb."""
    import shutil
    run = os.path.join(ROOT, 'work', 'run', 'PM2')
    if not os.path.isdir(run): shutil.copytree(os.path.join(ROOT, 'game_sample', 'PM2'), run)
    conf = os.path.join(ROOT, 'work', 'dosbox.conf'); open(conf, 'w').write(CONF % run)
    if not sh('pgrep Xvfb'):
        subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '800x600x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1)
    subprocess.Popen(['dosbox', '-conf', conf], env=ENV, stdout=open('/tmp/dosbox.log','w'), stderr=subprocess.STDOUT)
    time.sleep(3)
def pid(): return int(sh('pgrep -x dosbox').split()[0])
def shot(path): sh('import -window root %s' % path)
def key(*ks, delay=0.15):
    for k in ks:
        sh('xdotool keydown %s; sleep 0.08; xdotool keyup %s' % (k, k)); time.sleep(delay)
def click(x, y, button=1):
    sh('xdotool mousemove %d %d; sleep 0.1; xdotool mousedown %d; sleep 0.1; xdotool mouseup %d' % (x, y, button, button))
_base=None
def find_base():
    """Locate guest RAM in the dosbox process by scanning rw mappings for the BIOS data area (COM port table + 640K)."""
    global _base
    if _base: return _base
    p=pid()
    for line in open('/proc/%d/maps'%p):
        m=re.match(r'([0-9a-f]+)-([0-9a-f]+) rw.p ', line)
        if not m: continue
        s,e=int(m.group(1),16),int(m.group(2),16)
        if e-s < 16*1024*1024: continue
        with open('/proc/%d/mem'%p,'rb') as f:
            f.seek(s)
            try: d=f.read(e-s)
            except OSError: continue
        for m2 in re.finditer(rb'\xf8\x03\xf8\x02', d):
            b0=m2.start()-0x400
            if b0>=0 and d[b0+0x413:b0+0x415]==b'\x80\x02': _base=s+b0; return _base
    raise RuntimeError('guest RAM not found')
def peek(addr, n):
    with open('/proc/%d/mem'%pid(),'rb') as f: f.seek(find_base()+addr); return f.read(n)
def poke(addr, data):
    with open('/proc/%d/mem'%pid(),'r+b') as f: f.seek(find_base()+addr); f.write(data)
def dump(path, n=0x110000): open(path,'wb').write(peek(0,n))


# ---- PM2-specific helpers (used for real-machine verification, see TESTING.md) -----------------
class Guest:
    """DS-relative view of the running game's memory, API-compatible with pm2sim.vm.VM for save.dump()."""
    def __init__(self):
        img = peek(0, 0xA0000)
        i = img.find(b'PM2 <video mode>')
        if i < 0: raise RuntimeError('PM2.EXE not running')
        self.ds = i - 8                       # linear address of DS (seg 15E3 of the image)
        self.base = self.ds - 0x15E30         # linear address of the load image
    class _Mem:
        def __init__(s, g): s.g = g
        def __getitem__(s, k):
            if isinstance(k, slice): return peek(s.g.ds + k.start, k.stop - k.start)
            return peek(s.g.ds + k, 1)[0]
    @property
    def mem(self): return Guest._Mem(self)
    def ruw(self, a): return int.from_bytes(peek(self.ds + a, 2), 'little')
    def rw(self, a):
        v = self.ruw(a); return v - 0x10000 if v & 0x8000 else v
    def ww(self, a, v): poke(self.ds + a, (v & 0xFFFF).to_bytes(2, 'little'))
    def rng(self): return self.ruw(0x6744), self.ruw(0x6746)
    def set_rng(self, offset, index): self.ww(0x6744, offset); self.ww(0x6746, index)
    def patch_rng(self):
        """Make the RNG deterministic: replace `call C06C` (timer read) at 0389:81E8 by `mov ax,0`."""
        a = self.base + 0x3890 + 0x81E8
        cur = peek(a, 3)
        if cur == b'\xb8\x00\x00': return 'already patched'
        if cur[0] != 0xE8: raise RuntimeError('unexpected bytes at 0389:81E8: %s' % cur.hex())
        poke(a, b'\xb8\x00\x00'); return 'patched'
    def snapshot(self, path):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        from pm2sim import save
        open(path, 'wb').write(save.dump(self))

if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'start': start(); print('started')
    elif cmd == 'shot': shot(sys.argv[2])
    elif cmd == 'key': key(*sys.argv[2:])
    elif cmd == 'click': click(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    elif cmd == 'patch': print(Guest().patch_rng())
    elif cmd == 'rng':
        g = Guest()
        if len(sys.argv) > 3: g.set_rng(int(sys.argv[2]), int(sys.argv[3]))
        print(*g.rng())
    elif cmd == 'snapshot': Guest().snapshot(sys.argv[2]); print('wrote', sys.argv[2])
    else: print('usage: dbx.py start | shot f.png | key K.. | click x y [button] | patch | rng [offset index] | snapshot out.GNX')
