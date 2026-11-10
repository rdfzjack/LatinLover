"""Linear disassembly of PM2.EXE load image (segments: 0000, 0389, 1037 code; 15E3 data)."""
import sys, capstone
img = open('work/pm2.img','rb').read()
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
    with open('work/pm2.asm','w') as out:
        for seg, s, e in SEGS:
            out.write('; ---- segment %04x ----\n' % seg); dis(s, e, seg*16, out)
