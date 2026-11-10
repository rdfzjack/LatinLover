"""Linear disassembly of PM2.EXE into work/pm2.asm (segments 0000, 0389, 1037 code; 15E3 data).
Needs `pip install capstone`. View ranges with tools/asmview.py <linear_from> <linear_to> (hex);
linear = segment*16 + offset, e.g. 0389:813D -> 0x3890+0x813D."""
import sys, capstone
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
img = open(os.path.join(ROOT, 'game_sample', 'PM2', 'PM2.EXE'), 'rb').read()[4432:]   # strip MZ header
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
SEGS = [(0x0, 0x0, 0x3890), (0x389, 0x3890, 0x10370), (0x1037, 0x10370, 0x15e30)]
def dis(start, end, segbase, out):
    a = start
    while a < end:
        ins = next(md.disasm(img[a:a+16], a - segbase), None)
        if ins is None:
            out.write('%05x %04x: db %02x\n' % (a, a-segbase, img[a])); a += 1; continue
        out.write('%05x %04x: %-18s %s %s\n' % (a, a-segbase, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        a += ins.size
if __name__ == '__main__':
    os.makedirs(os.path.join(ROOT, 'work'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'pm2.asm'),'w') as out:
        for seg, s, e in SEGS:
            out.write('; ---- segment %04x ----\n' % seg); dis(s, e, seg*16, out)
