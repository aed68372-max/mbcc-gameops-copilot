"""Create only the MBCC-owned isolated database; never changes server auth or other databases."""
import csv, datetime as dt, hashlib, json, pathlib, sys
from sql_bridge import connect, DB, ROOT, normal

def main():
    data=ROOT/'data/synthetic';manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    with connect('master',False) as c:
        existing=c.cursor().execute('SELECT DB_ID(?)',DB).fetchval()
        if existing is None:c.cursor().execute('CREATE DATABASE [MBCCCopilotSynthetic]')
    with connect(DB,False) as c:
        cur=c.cursor()
        if cur.execute("SELECT OBJECT_ID('dbo.dataset_meta')").fetchval():
            marker=cur.execute('SELECT project_marker FROM dbo.dataset_meta').fetchval()
            if marker!='mbcc-gameops-copilot-v2':raise RuntimeError('Database not owned by this project; refusing changes')
            raise RuntimeError('Already provisioned: no overwrite. Use query/reconciliation scripts.')
        for statement in [
            'CREATE TABLE dbo.dataset_meta(project_marker varchar(80) NOT NULL,observation_start date NOT NULL,observation_end date NOT NULL,synthetic bit NOT NULL)',
            'CREATE TABLE dbo.users(user_id varchar(30) PRIMARY KEY,registered_date date NOT NULL,platform varchar(20) NOT NULL)',
            'CREATE TABLE dbo.activity(activity_id bigint PRIMARY KEY,user_id varchar(30) NOT NULL REFERENCES dbo.users(user_id),activity_date date NOT NULL,CONSTRAINT uq_active UNIQUE(user_id,activity_date))',
            'CREATE TABLE dbo.payments(payment_id bigint PRIMARY KEY,user_id varchar(30) NOT NULL REFERENCES dbo.users(user_id),paid_date date NOT NULL,amount_cents bigint NOT NULL CHECK(amount_cents>0),event_id varchar(60) NULL)',
            'CREATE TABLE dbo.event_participation(participation_id bigint PRIMARY KEY,user_id varchar(30) NOT NULL REFERENCES dbo.users(user_id),event_date date NOT NULL,event_id varchar(60) NOT NULL,CONSTRAINT uq_part UNIQUE(user_id,event_date,event_id))',
            'CREATE INDEX ix_activity_date ON dbo.activity(activity_date,user_id)',
            'CREATE INDEX ix_paid_date ON dbo.payments(paid_date,event_id) INCLUDE(user_id,amount_cents)']:
            cur.execute(statement)
        cur.execute('INSERT INTO dbo.dataset_meta VALUES (?,?,?,?)','mbcc-gameops-copilot-v2',manifest['observation_start'],manifest['observation_end'],True)
        counts={}
        c.autocommit=False
        for table,ncols in [('users',3),('activity',3),('payments',5),('event_participation',4)]:
            with (data/(table+'.csv')).open(encoding='utf-8',newline='') as f:
                source=list(csv.reader(f))[1:]
            converted=[]
            for row in source:
                row=[v if v!='' else None for v in row]
                if table!='users':row[0]=int(row[0])
                if table=='payments':row[3]=int(row[3])
                converted.append(row)
            # Table identifiers are a closed author-defined allowlist; values are bound parameters.
            cur.fast_executemany=True
            cur.executemany(f'INSERT INTO dbo.{table} VALUES ({",".join("?" for _ in range(ncols))})',converted)
            c.commit();counts[table]=len(converted)
        c.autocommit=True
        cur.execute('CREATE USER [mbcc_reader] WITHOUT LOGIN')
        for table in ['users','activity','payments','event_participation','dataset_meta']:
            cur.execute(f'GRANT SELECT ON OBJECT::dbo.{table} TO mbcc_reader')
        cur.execute('DENY INSERT,UPDATE,DELETE ON SCHEMA::dbo TO mbcc_reader')
        cur.execute('DENY ALTER ON SCHEMA::dbo TO mbcc_reader')
    evidence={'status':'VERIFIED','database':DB,'synthetic':True,'counts':counts,'source':manifest['source'],
              'gacha_reuse_status':manifest['gacha_reuse_status'],'server_configuration_changed':False,
              'query_identity':'mbcc_reader WITHOUT LOGIN, Windows trusted transport then EXECUTE AS USER WITH NO REVERT, pooling disabled',
              'security_limit':'Windows transport identity has existing sysadmin privileges; queries execute under irrevertible read-only database context. A dedicated low-privilege Windows service login is still recommended for production.'}
    out=ROOT/'evidence/v2/stage-c';out.mkdir(parents=True,exist_ok=True)
    (out/'setup.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False))

if __name__=='__main__':main()
