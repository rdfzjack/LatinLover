"""Game asset access: LBX archives (FLIB) and script decoding.

LBX trailer: u16 count, u32 dir_offset; dir entry = 12-byte name, u32 offset, u32 size.
Script (*.TXT) encoding, PM2.EXE seg 0000:
  magic 01 04 (ds:2376); body minus 6-byte key ds:2378 (0000:0C54);
  word-LZ: u16 n -> n literal words; u16 0x8000|n, u16 dist -> copy n words (0000:35CC);
  0x0C -> CRLF, 0x0B -> end of text (0000:0BA4).
"""
import os, struct

KEY = bytes.fromhex('13a2b46c794c')

def read_lbx(path):
    b = open(path, 'rb').read()
    n, diroff = struct.unpack('<HI', b[-6:])
    out = {}
    for i in range(n):
        e = b[diroff + i*20: diroff + i*20 + 20]
        off, size = struct.unpack('<II', e[12:])
        out[e[:12].decode('ascii').strip()] = b[off:off+size]
    return out

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

def decode_script(c):
    if c[:2] != b'\x01\x04': return c
    t = unlz(bytes((x - KEY[i % 6]) & 255 for i, x in enumerate(c[2:])))
    out = bytearray(); i = 0
    while i < len(t):
        b = t[i]
        if b == 0x0c: out += b'\r\n'
        elif b == 0x0b: break
        elif b >= 0x80: out += t[i:i+2]; i += 1
        else: out.append(b)
        i += 1
    return bytes(out)

class Assets:
    def __init__(self, game_dir):
        self.dir = game_dir
        self.exe = open(os.path.join(game_dir, 'PM2.EXE'), 'rb').read()
        self.scripts = {}
        for f in sorted(os.listdir(game_dir)):
            if f.startswith('TX') and f.endswith('.LBX'):
                for name, data in read_lbx(os.path.join(game_dir, f)).items():
                    key = name[:-4] if name.endswith('.TXT') else name
                    self.scripts.setdefault(key, decode_script(data))
    def script(self, name):
        return self.scripts.get(name.strip().upper())
