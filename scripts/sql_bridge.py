"""Fixed parameterised SQL only. No caller-supplied SQL, identifiers or connection credentials."""
import datetime as dt, decimal, json, os, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,os.environ.get('MBCC_PYDEPS',str(ROOT.parent.parent/'work/runtime/pydeps')))
import pyodbc
pyodbc.pooling=False  # NO REVERT execution context must never leak across pooled connections.
DB='MBCCCopilotSynthetic'
METRICS={'DAU','PAYMENT','RETENTION_D1','RETENTION_D7','EVENT_REVENUE','EVENT_PARTICIPATION'}
EVENTS={'SYN-LIMITED-01','SYN-RERUN-02'}

def connect(database=DB,readonly=True):
    server=os.environ.get('MBCC_SQL_SERVER','lpc:localhost')
    c=pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;',timeout=5,autocommit=True)
    c.timeout=15
    if readonly:c.cursor().execute("EXECUTE AS USER = 'mbcc_reader' WITH NO REVERT;")
    return c

def rows(cursor):
    columns=[d[0] for d in cursor.description]
    return [dict(zip(columns,row)) for row in cursor.fetchall()]

def normal(value):
    if isinstance(value,(dt.datetime,dt.date)):return value.isoformat()
    if isinstance(value,decimal.Decimal):return float(value)
    raise TypeError(type(value).__name__)

def validate(p):
    if p.get('metric') not in METRICS:raise ValueError('metric not allowed')
    start=dt.date.fromisoformat(p['startDate']);end=dt.date.fromisoformat(p['endDate'])
    if start>end or (end-start).days>366:raise ValueError('invalid date window')
    if p.get('platform') not in (None,'','android','ios','pc'):raise ValueError('platform not allowed')
    if p.get('eventId') not in (None,'',*EVENTS):raise ValueError('eventId not allowed')
    if p['metric'].startswith('RETENTION') and p.get('eventId'):raise ValueError('retention uses registration cohorts; event exposure filtering unsupported')
    return start,end,p.get('eventId') or None,p.get('platform') or None

def query(p):
    start,end,event,platform=validate(p)
    with connect() as c:
        cur=c.cursor();identity=rows(cur.execute('SELECT USER_NAME() AS database_user,DB_NAME() AS database_name'))[0]
        bounds=rows(cur.execute('SELECT observation_start,observation_end FROM dbo.dataset_meta'))[0]
        if start<bounds['observation_start'] or end>bounds['observation_end']:raise ValueError('outside observed data coverage')
        metric=p['metric']; definitions='';params=[]
        if metric=='DAU':
            sql="""SELECT a.activity_date,COUNT(DISTINCT a.user_id) AS dau FROM dbo.activity a JOIN dbo.users u ON u.user_id=a.user_id
             WHERE a.activity_date BETWEEN ? AND ? AND (? IS NULL OR u.platform=?)
             AND (? IS NULL OR EXISTS(SELECT 1 FROM dbo.event_participation ep WHERE ep.user_id=a.user_id AND ep.event_date=a.activity_date AND ep.event_id=?))
             GROUP BY a.activity_date ORDER BY a.activity_date"""
            params=[start,end,platform,platform,event,event];definitions='DAU = distinct active users per calendar date, optional same-day event participant filter.'
        elif metric=='PAYMENT':
            sql="""WITH active AS (SELECT DISTINCT a.user_id FROM dbo.activity a JOIN dbo.users u ON u.user_id=a.user_id
             WHERE a.activity_date BETWEEN ? AND ? AND (? IS NULL OR u.platform=?)
             AND (? IS NULL OR EXISTS(SELECT 1 FROM dbo.event_participation ep WHERE ep.user_id=a.user_id AND ep.event_date=a.activity_date AND ep.event_id=?))),
             pay AS (SELECT p.user_id,p.amount_cents FROM dbo.payments p JOIN dbo.users u ON u.user_id=p.user_id
             WHERE p.paid_date BETWEEN ? AND ? AND (? IS NULL OR u.platform=?) AND (? IS NULL OR p.event_id=?))
             SELECT (SELECT COUNT(*) FROM active) AS active_users,COUNT(DISTINCT user_id) AS payers,COALESCE(SUM(amount_cents),0) AS revenue_cents,
             COUNT(DISTINCT user_id)*1.0/NULLIF((SELECT COUNT(*) FROM active),0) AS paying_rate,
             COALESCE(SUM(amount_cents),0)*.01/NULLIF((SELECT COUNT(*) FROM active),0) AS arpu_cny,
             SUM(amount_cents)*.01/NULLIF(COUNT(DISTINCT user_id),0) AS arppu_cny FROM pay"""
            params=[start,end,platform,platform,event,event,start,end,platform,platform,event,event]
            definitions='Period distinct payers / period distinct active users; ARPU=revenue/active users; ARPPU=revenue/payers. Currency CNY, cents stored exactly. Zero denominator => null.'
        elif metric.startswith('RETENTION'):
            d=1 if metric=='RETENTION_D1' else 7
            sql="""SELECT COUNT(*) AS registered_users,
              SUM(CASE WHEN DATEADD(day,?,u.registered_date)<=? THEN 1 ELSE 0 END) AS eligible_users,
              SUM(CASE WHEN DATEADD(day,?,u.registered_date)>? THEN 1 ELSE 0 END) AS censored_users,
              SUM(CASE WHEN DATEADD(day,?,u.registered_date)<=? AND a.user_id IS NOT NULL THEN 1 ELSE 0 END) AS retained_users
              FROM dbo.users u LEFT JOIN dbo.activity a ON a.user_id=u.user_id AND a.activity_date=DATEADD(day,?,u.registered_date)
              WHERE registered_date BETWEEN ? AND ? AND (? IS NULL OR platform=?)"""
            cutoff=bounds['observation_end'];params=[d,cutoff,d,cutoff,d,cutoff,d,start,end,platform,platform]
            definitions=f'D{d} exact-day registration cohort retention; exclude cohorts whose D{d} is after observation_end; not rolling retention. Cohort window is inclusive.'
        elif metric=='EVENT_REVENUE':
            sql="""SELECT p.event_id,COUNT(DISTINCT p.user_id) AS payers,SUM(p.amount_cents) AS revenue_cents FROM dbo.payments p
             JOIN dbo.users u ON u.user_id=p.user_id WHERE p.paid_date BETWEEN ? AND ? AND p.event_id IS NOT NULL
             AND (? IS NULL OR p.event_id=?) AND (? IS NULL OR u.platform=?) GROUP BY p.event_id ORDER BY p.event_id"""
            params=[start,end,event,event,platform,platform];definitions='CNY cents of successful synthetic purchases assigned to an event, grouped by event_id.'
        else:
            sql="""SELECT (SELECT COUNT(DISTINCT a.user_id) FROM dbo.activity a JOIN dbo.users u ON u.user_id=a.user_id
             WHERE a.activity_date BETWEEN ? AND ? AND (? IS NULL OR u.platform=?)) AS active_users,
             COUNT(DISTINCT ep.user_id) AS participants FROM dbo.event_participation ep JOIN dbo.users u ON u.user_id=ep.user_id
             WHERE ep.event_date BETWEEN ? AND ? AND (? IS NULL OR ep.event_id=?) AND (? IS NULL OR u.platform=?)"""
            params=[start,end,platform,platform,start,end,event,event,platform,platform]
            definitions='Period distinct event participants / period distinct active users, optional event and platform filters; descriptive association only.'
        result=rows(cur.execute(sql,params))
        if metric.startswith('RETENTION'):
            for r in result:
                for key in ['eligible_users','censored_users','retained_users']:r[key]=r[key] or 0
                r['retention_rate']=r['retained_users']/r['eligible_users'] if r['eligible_users'] else None
        if metric=='EVENT_PARTICIPATION':
            for r in result:r['participation_rate']=r['participants']/r['active_users'] if r['active_users'] else None
        if metric=='DAU':
            by_date={r['activity_date']:r for r in result};result=[];day=start
            while day<=end:
                result.append(by_date.get(day,{'activity_date':day,'dau':0}));day+=dt.timedelta(days=1)
        return {'status':'OK','synthetic':True,'source':'MBCCCopilotSynthetic / data/synthetic/manifest.json',
            'metric':metric,'window':{'startDate':str(start),'endDate':str(end),'inclusive':True,'timezone':'Asia/Shanghai'},
            'filters':{'eventId':event,'platform':platform},'observation_end':str(bounds['observation_end']),
            'definition':definitions,'identity':identity,'rows':result,'parameterized':True}

if __name__=='__main__':
    try:
        payload=json.load(sys.stdin)
        result=query(payload)
    except ValueError as e:result={'status':'INVALID_ARGUMENT','synthetic':True,'error':str(e)}
    except Exception as e:result={'status':'UNAVAILABLE','synthetic':True,'error':type(e).__name__}
    print(json.dumps(result,ensure_ascii=False,default=normal))
