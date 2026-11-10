"""LBX (FLIB, 1993 R.Hashimoto) archive reader.
Trailer: u16 count, u32 dir_offset. Dir entry: 12-byte name, u32 offset, u32 size."""
import struct, sys, os
def read_lbx(path):
    b = open(path, 'rb').read()
    n, diroff = struct.unpack('<HI', b[-6:])
    out = {}
    for i in range(n):
        e = b[diroff + i*20: diroff + i*20 + 20]
        name = e[:12].decode('ascii').strip()
        off, size = struct.unpack('<II', e[12:])
        out[name] = b[off:off+size]
    return out
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    for f in sorted(os.listdir(src)):
        if f.upper().endswith('.LBX'):
            try: files = read_lbx(os.path.join(src, f))
            except Exception as ex: print('skip', f, ex); continue
            d = os.path.join(dst, f[:-4]); os.makedirs(d, exist_ok=True)
            for k, v in files.items(): open(os.path.join(d, k), 'wb').write(v)
            print(f, len(files))
