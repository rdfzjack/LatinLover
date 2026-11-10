"""Drive DOSBox under Xvfb: start, keys, mouse, screenshot, guest memory peek/poke via /proc/pid/mem."""
import subprocess, os, time, re, struct, sys
DISPLAY=':99'
ENV=dict(os.environ, DISPLAY=DISPLAY, SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy')
def sh(cmd): return subprocess.run(cmd, shell=True, env=ENV, capture_output=True, text=True).stdout
def start(conf='/home/user/LatinLover/work/dosbox.conf'):
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
