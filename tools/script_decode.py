"""Decode PM2 script files (*.TXT inside TX*.LBX).
Format (PM2.EXE seg0000): magic 01 04 (ds:2376), body byte-subtracted with 6-byte key ds:2378 (0000:0C54),
then word-LZ (literal: u16 nwords + data; match: u16 0x8000|nwords, u16 byte distance) (0000:35CC),
then text expansion 0x0C->CRLF, 0x0B->EOF (0000:0BA4)."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from lbx import read_lbx
KEY = bytes.fromhex('13a2b46c794c')
def unlz(p):
    out = bytearray(); i = 0
    while i + 2 <= len(p):
        w = struct.unpack_from('<H', p, i)[0]; i += 2
        if w & 0x8000:
            n = (w & 0x7fff) * 2; dist = struct.unpack_from('<H', p, i)[0]; i += 2
            for _ in range(n): out.append(out[-dist])
        else:
            out += p[i:i + w*2]; i += w*2
    return bytes(out)
def decode(c):
    if c[:2] != b'\x01\x04': return c
    p = bytes((x - KEY[i % 6]) & 255 for i, x in enumerate(c[2:]))
    t = unlz(p); out = bytearray(); i = 0
    while i < len(t):
        b = t[i]
        if b == 0x0c: out += b'\r\n'
        elif b == 0x0b: break
        elif b >= 0x80: out += t[i:i+2]; i += 1
        else: out.append(b)
        i += 1
    return bytes(out)
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    for f in sorted(os.listdir(src)):
        if f.startswith('TX') and f.endswith('.LBX'):
            d = os.path.join(dst, f[:-4]); os.makedirs(d, exist_ok=True)
            for name, data in read_lbx(os.path.join(src, f)).items():
                txt = decode(data).decode('big5', 'replace').replace('\r\n', '\n')
                open(os.path.join(d, name), 'w', encoding='utf-8').write(txt)
