# PM2 with NO treasure/errantry/festival/merchant/palace/events/items: only classes, jobs, rest, food 30/mo, pension 500/yr.
# Question: when does each of the 4 reputations reach 300 by training, which skill is the bottleneck, what gets sacrificed.
import json,random,statistics as st
T='/home/user/LatinLover/original/data/tables/'
CL={c['name']:c for c in json.load(open(T+'classes.json'))}
ZH={'智力':'智力','信仰':'信仰','感受':'感受','氣質':'气质','魅力':'魅力','體力':'体力','抗魔(訓練值)':'抗魔','藝術(訓練值)':'艺术','戰鬥技術(訓練值)':'战技','攻擊(訓練值,含腕力/10)':'攻击','防禦(訓練值)':'防御','魔法技術(訓練值)':'魔技','魔力(訓練值)':'魔力','禮儀(訓練值)':'礼仪'}
SK=['战技','攻击','防御','魔技','魔力','抗魔','礼仪','艺术','话术','料理','扫除','待人']
AT=['体力','腕力','智力','气质','魅力','道德','信仰','罪孽','感受']
H=lambda:random.randint(0,1)
def add(s,k,v): s[k]=max(0,min(100 if k in SK else 999,s[k]+v))
r0=lambda n:random.randint(0,max(0,n))
JOBS={ # wage, stress/day, age, success(s), effects(s), refuses delinquents
 '家务':(0,1,10,lambda s:s['体力']-r0(s['疲劳'])>=5,[('料理','H'),('扫除','H'),('待人','H')],False),
 '农场':(10,3,10,lambda s:s['体力']-r0(s['疲劳'])>=30,[('体力',1),('腕力',1),('气质',-1)],True),
 '教堂':(1,1,10,lambda s:s['体力']-r0(s['疲劳'])>=10,[('信仰',2),('道德',1),('罪孽',-2)],False),
 '餐厅':(8,2,10,lambda s:s['体力']-r0(s['疲劳'])>=30,[('料理','H')],True),
 '美容院':(20,3,11,lambda s:s['艺术']-r0(s['疲劳'])>=40,[('感受',1),('腕力',-1)],True),
 '工地':(18,3,12,lambda s:s['体力']-r0(s['疲劳'])>=80,[('体力',2),('魅力',-1)],True),
 '墓园':(8,5,13,lambda s:s['信仰']-r0(s['疲劳'])>=10 and s['体力']-r0(s['疲劳'])>=10,[('抗魔','H'),('感受',1),('魅力',-1)],True),
 '家教':(20,7,14,lambda s:s['智力']-r0(s['疲劳'])>=120,[('道德',1),('魅力',-1)],True),
 '酒店':(12,5,14,lambda s:s['体力']-r0(s['疲劳'])>=60 and s['魅力']-r0(s['疲劳'])>=50,[('料理','H'),('话术','H'),('智力',-2)],True),
}
def rp(n): return 1 if n<10 else 1.2 if n<30 else 1.44 if n<60 else 1.73 if n<90 else 2.08
def run(policy,target,seed):
    random.seed(seed)
    s=dict(钱=500,疲劳=0,体力=19,腕力=18,智力=36,气质=14,魅力=14,道德=7,信仰=10,罪孽=0,感受=35,
           战技=5,攻击=6,防御=5,魔技=17,魔力=17,抗魔=18,礼仪=22,艺术=22,话术=21,料理=10,扫除=10,待人=9)
    start=dict(s); ct={};jt={};cnt={'课':0,'工':0,'休':0};first={};fee=earn=0;bad=0;used={}
    for m in range(96):
        age=10+m//12; s['钱']-=30
        if m%12==4: s['钱']+=500
        for p in range(3):
            act=policy(s,age)
            hik=max(0,min(100,s['疲劳']-max(s['道德'],s['信仰'])))
            if act[0]=='工' and JOBS[act[1]][5] and hik>=60: act=('休',)
            work=[d for d in range(10) if d%7!=6]
            if act[0]=='休':
                cnt['休']+=1; s['疲劳']=max(0,s['疲劳']-sum(random.choice((5,10)) for _ in range(10)))
            elif act[0]=='课':
                c=CL[act[1]]; n=ct.get(act[1],0); L=0 if n<5 else 1 if n<10 else 2 if n<15 else 3; ct[act[1]]=n+1; cnt['课']+=1; used[act[1]]=used.get(act[1],0)+1
                for d in work:
                    cost=c['cost_per_day_by_level'][L]
                    if s['钱']<cost: continue
                    s['钱']-=cost; fee+=cost; s['疲劳']+=1
                    if s['体力']//2+r0(s['体力']//2)>=r0(s['疲劳']):
                        for e in c['success_effects']:
                            a,b=e['range_by_level'][L]; v=random.randint(a,b); add(s,ZH[e['zh']],v if e['sign']=='+' else -v)
            else:
                w,sd,ua,ok,eff,_=JOBS[act[1]]; n=jt.get(act[1],0); pay=succ=0; cnt['工']+=1; used[act[1]]=used.get(act[1],0)+1
                for d in work:
                    good=ok(s)
                    if hik>=30 and random.random()<0.8: good=False
                    elif hik>=10 and random.random()<0.4: good=False
                    if good: pay+=int(w*rp(n)); succ+=1
                    for k,v in eff: add(s,k,H() if v=='H' else v)
                    s['疲劳']+=sd
                if succ==len(work): pay=int(pay*1.5)
                if succ: jt[act[1]]=n+1
                s['钱']+=pay; earn+=pay
            for k in target:
                if s[k]>=100 and k not in first: first[k]=m+1
        bad+= s['疲劳']-max(s['道德'],s['信仰'])>=10
        if all(k in first for k in target): break
    return dict(month=m+1 if all(k in first for k in target) else None,first=first,cnt=dict(cnt),fee=fee,earn=earn,bad=bad,used=used,end=dict(s),start=start)
def rest_or(s,ignore=False):
    cap=min(s['体力'],max(s['道德'],s['信仰']))
    return s['疲劳']>=max(cap-5,15)
def need_church(s,lv): return max(s['道德'],s['信仰'])<lv
def fighter(s,age):
    if rest_or(s): return ('休',)
    if need_church(s,50): return ('工','教堂')
    c=None
    if s['防御']<100 or s['战技']<100: c='格鬥術'
    if s['攻击']<100 and (c is None or s['攻击']<=s['防御']): c='劍術'
    if c and s['钱']>=CL[c]['cost_per_day_by_level'][3]*9: return ('课',c)
    return ('工','工地' if age>=12 and s['体力']>=110 else '农场')
def mage(s,age):
    if rest_or(s): return ('休',)
    if need_church(s,50): return ('工','教堂')
    c='魔法' if (s['魔技']<100 or s['魔力']<100) else '神學' if s['抗魔']<100 else None
    if s['抗魔']<100 and s['抗魔']<min(s['魔技'],s['魔力'])-30: c='神學'
    if c and s['钱']>=CL[c]['cost_per_day_by_level'][3]*9: return ('课',c)
    if age>=14 and s['智力']>=170: return ('工','家教')
    if age>=13 and s['抗魔']<100: return ('工','墓园')
    return ('工','农场')
def social(s,age):
    if rest_or(s): return ('休',)
    if need_church(s,50): return ('工','教堂')
    if age>=14 and s['话术']<100 and s['体力']>=75 and s['魅力']>=70: return ('工','酒店')
    c='禮儀' if s['礼仪']<100 else '繪畫' if s['艺术']<100 else '舞蹈' if (s['魅力']<75 or s['体力']<80) else None
    if c and s['钱']>=CL[c]['cost_per_day_by_level'][3]*9: return ('课',c)
    if s['话术']>=100 and c is None: return ('休',)
    return ('工','美容院' if age>=11 and s['艺术']>=60 else '餐厅' if s['体力']>=45 else '农场')
def house(s,age):
    if rest_or(s): return ('休',)
    if need_church(s,30): return ('工','教堂')
    return ('工','家务')
ROADS={'战士':(fighter,['战技','攻击','防御']),'魔法':(mage,['魔技','魔力','抗魔']),'社交':(social,['礼仪','艺术','话术']),'家事':(house,['料理','扫除','待人'])}
if __name__=='__main__':
    for name,(pol,tg) in ROADS.items():
        R=[run(pol,tg,sd) for sd in range(40)]
        done=[r['month'] for r in R if r['month']]
        med=lambda f:round(st.median(f(r) for r in R))
        print(f"\n== {name}  练满(三项都100) 中位数第 {st.median(done) if done else '—'} 个月 / 96（{len(done)}/40 局练满）")
        for k in tg: 
            v=[r['first'][k] for r in R if k in r['first']]
            print(f"   {k} 到100：第 {st.median(v) if v else '—'} 个月（{len(v)}/40）")
        print("   旬数 课/工/休:",med(lambda r:r['cnt']['课']),med(lambda r:r['cnt']['工']),med(lambda r:r['cnt']['休'])," 学费",med(lambda r:r['fee'])," 工钱",med(lambda r:r['earn'])," 不良月",med(lambda r:r['bad']))
        u={}
        for r in R:
            for k,v in r['used'].items(): u.setdefault(k,[]).append(v)
        print("   做了什么(旬，中位数):",{k:round(st.median(v)) for k,v in sorted(u.items(),key=lambda x:-st.median(x[1]))})
        print("   属性 开始→练满时:"," ".join(f"{k}{R[0]['start'][k]}→{med(lambda r:r['end'][k])}" for k in AT))
        oth=[x for x in SK if x not in tg]
        print("   别的技能:"," ".join(f"{k}{R[0]['start'][k]}→{med(lambda r:r['end'][k])}" for k in oth if med(lambda r:r['end'][k])!=R[0]['start'][k]))
