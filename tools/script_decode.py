"""Decode all scripts to UTF-8: python3 tools/script_decode.py game_sample/PM2 data/scripts"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pm2sim.assets import read_lbx, decode_script
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    for f in sorted(os.listdir(src)):
        if f.startswith('TX') and f.endswith('.LBX'):
            d = os.path.join(dst, f[:-4]); os.makedirs(d, exist_ok=True)
            for name, data in read_lbx(os.path.join(src, f)).items():
                txt = decode_script(data).decode('big5', 'replace').replace('\r\n', '\n')
                open(os.path.join(d, name), 'w', encoding='utf-8').write(txt)
