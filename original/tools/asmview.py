"""Compact view of work/pm2.asm for a linear address range: python3 tools/asmview.py 0x4186 0x4400"""
import sys,re
a,b=int(sys.argv[1],16),int(sys.argv[2],16)
out=[]
for l in open('/home/user/LatinLover/work/pm2.asm'):
    if l[0]==';': continue
    x=int(l[:5],16)
    if a<=x<b:
        s=l[6:10]+' '+l[31:].strip()
        s=s.replace('word ptr ','').replace('byte ptr ','')
        out.append(s)
print(' | '.join(out))
