"""SQL versus independently computed CSV set-based reference. No shared aggregation helper."""
import csv, datetime as dt, json, math
from sql_bridge import ROOT,query,connect,normal

DATA=ROOT/'data/synthetic'
def read(name):
    with (DATA/(name+'.csv')).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
USERS={r['user_id']:r for r in read('users')};ACTIVE=read('activity');PAY=read('payments');PART=read('event_participation')
CUTOFF=dt.date.fromisoformat(json.loads((DATA/'manifest.json').read_text())['observation_end'])

def reference(p):
    start,end=p['startDate'],p['endDate'];event=p.get('eventId');platform=p.get('platform');metric=p['metric']
    allowed={u for u,r in USERS.items() if not platform or r['platform']==platform}
    participants={(r['user_id'],r['event_date']) for r in PART if not event or r['event_id']==event}
    active=[r for r in ACTIVE if r['user_id'] in allowed and start<=r['activity_date']<=end and (not event or (r['user_id'],r['activity_date']) in participants)]
    payments=[r for r in PAY if r['user_id'] in allowed and start<=r['paid_date']<=end and (not event or r['event_id']==event)]
    if metric=='DAU':
        result=[];day=dt.date.fromisoformat(start)
        while str(day)<=end:
            result.append({'activity_date':str(day),'dau':len({r['user_id'] for r in active if r['activity_date']==str(day)})});day+=dt.timedelta(days=1)
        return result
    if metric=='PAYMENT':
        a=len({r['user_id'] for r in active});payers=len({r['user_id'] for r in payments});cents=sum(int(r['amount_cents']) for r in payments)
        return [dict(active_users=a,payers=payers,revenue_cents=cents,paying_rate=payers/a if a else None,arpu_cny=cents/100/a if a else None,arppu_cny=cents/100/payers if payers else None)]
    if metric.startswith('RETENTION'):
        d=1 if metric=='RETENTION_D1' else 7;cohort=[(u,dt.date.fromisoformat(r['registered_date'])) for u,r in USERS.items() if u in allowed and start<=r['registered_date']<=end]
        eligible=[(u,reg) for u,reg in cohort if reg+dt.timedelta(days=d)<=CUTOFF];dates={(r['user_id'],r['activity_date']) for r in ACTIVE}
        retained=sum((u,str(reg+dt.timedelta(days=d))) in dates for u,reg in eligible)
        return [dict(registered_users=len(cohort),eligible_users=len(eligible),censored_users=len(cohort)-len(eligible),retained_users=retained,retention_rate=retained/len(eligible) if eligible else None)]
    if metric=='EVENT_REVENUE':
        result=[]
        for eid in sorted({r['event_id'] for r in payments if r['event_id']}):
            rows=[r for r in payments if r['event_id']==eid];result.append(dict(event_id=eid,payers=len({r['user_id'] for r in rows}),revenue_cents=sum(int(r['amount_cents']) for r in rows)))
        return result
    a=len({r['user_id'] for r in ACTIVE if r['user_id'] in allowed and start<=r['activity_date']<=end})
    part=len({r['user_id'] for r in PART if r['user_id'] in allowed and start<=r['event_date']<=end and (not event or r['event_id']==event)})
    return [dict(active_users=a,participants=part,participation_rate=part/a if a else None)]

def equivalent(a,b):
    if isinstance(a,dict):return set(a)==set(b) and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    if isinstance(a,(dt.date,dt.datetime)):a=a.isoformat()
    if a is None or b is None:return a is b
    if isinstance(b,(float,int)):return math.isclose(float(a),float(b),rel_tol=1e-5,abs_tol=1e-6)
    return a==b

def main():
    cases=[]
    for metric in ['DAU','PAYMENT','RETENTION_D1','RETENTION_D7','EVENT_REVENUE','EVENT_PARTICIPATION']:
        for start,end,platform in [('2025-01-01','2025-01-07',None),('2025-01-11','2025-01-20','ios'),('2025-02-08','2025-02-14',None)]:
            cases.append(dict(metric=metric,startDate=start,endDate=end,platform=platform))
    for metric in ['DAU','PAYMENT','EVENT_REVENUE','EVENT_PARTICIPATION']:
        cases.append(dict(metric=metric,startDate='2025-01-01',endDate='2025-01-07',eventId='SYN-LIMITED-01'))
    cases.append(dict(metric='RETENTION_D7',startDate='2025-02-14',endDate='2025-02-14'))
    results=[]
    for i,p in enumerate(cases,1):
        try:actual=query(p);expected=reference(p);ok=equivalent(actual['rows'],expected)
        except Exception as e:actual={'error':str(e)};expected=None;ok=False
        results.append({'case':i,'request':p,'sql':actual,'python_reference':expected,'passed':ok})
    with connect() as c:
        cur=c.cursor();identity=cur.execute("SELECT USER_NAME(),HAS_PERMS_BY_NAME('dbo.users','OBJECT','SELECT'),HAS_PERMS_BY_NAME('dbo.users','OBJECT','INSERT')").fetchone()
        denied=False;revert_denied=False
        try:
            cur.execute("BEGIN TRAN; INSERT INTO dbo.users VALUES ('SYN-PERMISSION-PROBE','2025-01-01','pc'); ROLLBACK;")
        except Exception:
            denied=True
            try:cur.execute('IF @@TRANCOUNT>0 ROLLBACK;')
            except Exception:pass
        try:cur.execute('REVERT;')
        except Exception:revert_denied=True
    result={'status':'VERIFIED' if all(r['passed'] for r in results) and denied and revert_denied else 'PARTIAL',
            'case_count':len(results),'passed':sum(r['passed'] for r in results),'synthetic':True,'cases':results,
            'readonly_proof':{'identity':list(identity),'write_denied':denied,'revert_denied':revert_denied},
            'method':'Independent CSV set arithmetic versus parameterized SQL, with exact-day cohort censoring and zero-denominator controls.'}
    out=ROOT/'evidence/v2/stage-c';out.mkdir(parents=True,exist_ok=True)
    (out/'reconciliation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=normal),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False,default=normal))
    if result['status']!='VERIFIED':raise SystemExit(1)

if __name__=='__main__':main()
