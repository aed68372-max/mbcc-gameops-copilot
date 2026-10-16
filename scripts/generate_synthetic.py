"""Independent MBCC Synthetic fallback; never claims to be a recovered Gacha dataset."""
import csv, datetime as dt, hashlib, json, pathlib, random
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data/synthetic'

def main():
    OUT.mkdir(parents=True,exist_ok=True);rng=random.Random(20261016)
    start=dt.date(2025,1,1);end=dt.date(2025,2,14)
    users=[];activity=[];payments=[];participation=[]
    for i in range(1,1501):
        reg=start+dt.timedelta(days=rng.randrange(45)); platform=rng.choice(['android','ios','pc'])
        users.append([f'SYN-{i:05}',reg,platform])
        day=reg
        while day<=end:
            age=(day-reg).days
            active=age==0 or rng.random() < max(.12,.72-.012*age)
            if active:
                activity.append([len(activity)+1,f'SYN-{i:05}',day])
                event='SYN-LIMITED-01' if dt.date(2025,1,11)<=day<=dt.date(2025,1,20) else ('SYN-RERUN-02' if dt.date(2025,2,1)<=day<=dt.date(2025,2,10) else None)
                paid=rng.random() < (.08+(.04 if event else 0))
                if paid:payments.append([len(payments)+1,f'SYN-{i:05}',day,rng.choice([600,3000,9800,19800]),event])
                if event and (paid or rng.random()<.42):participation.append([len(participation)+1,f'SYN-{i:05}',day,event])
            day+=dt.timedelta(days=1)
    tables={'users':(['user_id','registered_date','platform'],users),
            'activity':(['activity_id','user_id','activity_date'],activity),
            'payments':(['payment_id','user_id','paid_date','amount_cents','event_id'],payments),
            'event_participation':(['participation_id','user_id','event_date','event_id'],participation)}
    manifest={'synthetic':True,'generator_seed':20261016,'source':'NEW_MBCC_SYNTHETIC_FALLBACK',
              'gacha_reuse_status':'BLOCKED_NOT_FOUND','note':'Searched accessible local user directories, Documents/Codex, desktop, D drive and SQL database names; no gacha-liveops-analytics located. This is newly generated, not reused Gacha data.',
              'observation_start':str(start),'observation_end':str(end),'timezone':'Asia/Shanghai; synthetic calendar dates',
              'events':[{'event_id':'SYN-LIMITED-01','start_date':'2025-01-11','end_date':'2025-01-20','public_rule_reference':'play-001','note':'Teaching association with historical public rules only; synthetic dates are NOT official event dates'},
                        {'event_id':'SYN-RERUN-02','start_date':'2025-02-01','end_date':'2025-02-10','public_rule_reference':None}], 'tables':{}}
    for name,(columns,rows) in tables.items():
        path=OUT/(name+'.csv')
        with path.open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(columns);writer.writerows(rows)
        manifest['tables'][name]={'rows':len(rows),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=='__main__':main()
