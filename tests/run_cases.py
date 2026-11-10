"""Replay real-machine cases in the simulator and compare: python3 tests/run_cases.py [tests/cases]
A case is a JSON file (see TESTING.md):
  {"before": "x_before.GNX", "after": "x_after.GNX", "rng_before": [offset, index], "rng_after": [o, i],
   "plan": [["上課學習","劍術"], ...], "answers": {"option text": "choice text or index"}, "note": "..."}
"""
import glob, json, os, struct, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from pm2sim.game import Game
from pm2sim import save

def named_diff(a, b):
    names = {}
    for v in json.load(open(os.path.join(ROOT, 'data', 'tables', 'variables.json'), encoding='utf-8')):
        if 'save_offset' in v: names[v['save_offset']] = v['name']
    out = []; known = sorted(names)
    for off in range(0, min(len(a), len(b)) - 1, 2):
        x, y = struct.unpack_from('<h', a, off)[0], struct.unpack_from('<h', b, off)[0]
        if x != y:
            base = max([k for k in known if k <= off], default=None)
            label = '%s[%d]' % (names[base], (off - base) // 2) if base is not None else 'header'
            out.append((off, label, x, y))
    return out

def run_case(path):
    c = json.load(open(path, encoding='utf-8')); d = os.path.dirname(path)
    g = Game(seed=None); g.load_save(os.path.join(d, c['before']))
    if 'rng_before' in c: g.set_rng(*c['rng_before'])
    g.play_month([tuple(p) for p in c['plan']], c.get('answers', {}))
    sim = save.dump(g.vm); real = open(os.path.join(d, c['after']), 'rb').read()
    diff = named_diff(sim, real)
    if 'rng_after' in c and list(g.rng()) != list(c['rng_after']):
        diff.append((-1, 'RNG(offset,index)', g.rng(), tuple(c['rng_after'])))
    return diff

if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'tests', 'cases')
    files = sorted(glob.glob(os.path.join(d, '*.json'))); bad = 0
    for f in files:
        diff = run_case(f)
        print('%s  %s' % ('PASS' if not diff else 'FAIL', os.path.basename(f)))
        for off, label, s, r in diff[:40]: print('    %-28s sim=%s real=%s (file offset %d)' % (label, s, r, off))
        bad += bool(diff)
    print('%d case(s), %d failed' % (len(files), bad)); sys.exit(1 if bad else 0)
