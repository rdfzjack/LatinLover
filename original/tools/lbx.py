"""Extract all LBX archives: python3 tools/lbx.py game_sample/PM2 outdir"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pm2sim.assets import read_lbx
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    for f in sorted(os.listdir(src)):
        if f.upper().endswith('.LBX'):
            d = os.path.join(dst, f[:-4]); os.makedirs(d, exist_ok=True)
            for k, v in read_lbx(os.path.join(src, f)).items(): open(os.path.join(d, k), 'wb').write(v)
