"""Print only the rule-bearing lines of a decoded script (drops text, UI, animation).
usage: python3 tools/logic_view.py data/scripts/TXTR/TRG004.TXT [LABEL ...]"""
import re, sys
UI = re.compile(r'^(TX[A-Z0-9]*|PT[A-Z]*|WW(?!MUSYA)[A-Z]*|GR_[A-Z]*|GRP[A-Z]*|GOLDOPEN|GOLDUPD|PIC|EFC|MUSIC|PLAY|TIMER[12]|WAIT[12U]|WAIT1XX|SLCPOS|'
                r'PALET_[A-Z]*|STRSCLEAR|P98F|IGRP_[A-Z0-9]*|ITEMPRN|PRICON|GXX[A-Z]*|ALOC[A-Z]*|ALC[A-Z]*|BLC[A-Z]*|FILM[0-9]*|APUT[A-Z]*|'
                r'ANIM[A-Z_]*|ANMT[A-Z0-9]*|ALL_OPEN[A-Z_0-9]*|ALL_CLOSE|FACEOPEN|FACECLOSE|SHORTWAIT|CLENDER\((1|2|6)[,)]|TXF|PROLONG|XDBG|FFDISK|EDTX|SS\$|OPEN|CLOSE|TTL\$?|GN|PPP1)\b')
SKIP_LABEL = re.compile(r'^\*(ANIME|ANMT|ALL_OPEN|ALL_CLOSE|GXX|APUT|ANIM)')
def logic_lines(path, labels=None):
    out = []; skipping = False; want = not labels
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        s = line.strip()
        if not s: continue
        if s.startswith('*'):
            skipping = bool(SKIP_LABEL.match(s))
            if labels: want = s[1:].split()[0] in labels
        if skipping or not want: continue
        if s[0] in '「@' or ord(s[0]) > 127: continue
        if s.startswith('.') and '=' not in s: continue
        if UI.match(s): continue
        s2 = re.sub(r'\s+', ' ', s)
        out.append('\t' * (len(line) - len(line.lstrip('\t'))) + s2)
    # drop IF lines whose block became empty
    res = []
    for i, l in enumerate(out):
        ind = len(l) - len(l.lstrip('\t'))
        if re.match(r'\t*IF ?\(.*\)\s*$', l):
            nxt = out[i+1] if i + 1 < len(out) else ''
            if len(nxt) - len(nxt.lstrip('\t')) <= ind: continue
        res.append(l)
    return res
if __name__ == '__main__':
    print('\n'.join(logic_lines(sys.argv[1], set(sys.argv[2:]) or None)))
