"""Post-experiment regression: unchanged eight SQL questions; do not overwrite frozen results."""
import json,pathlib,time
from compare_models import http
from run_experiments import score
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    tasks=[t for t in json.loads((ROOT/'evaluation/tasks80.json').read_text(encoding='utf-8')) if t['kind']=='metrics']
    rows=[];out=ROOT/'evidence/v2/stage-f/sql-provenance-regression.json'
    health=http('http://127.0.0.1:18081/api/v2/health')
    for t in tasks:
        run=http('http://127.0.0.1:18081/api/v2/agent',{'question':t['question'],'profile':'tools'})
        scores=score(t,run);ids={x['result']['data']['source_id'] for x in run.get('tools',[]) if isinstance(x.get('result',{}).get('data'),dict) and x['result']['data'].get('source_id')}
        citations=(run.get('reply') or {}).get('citations',[])
        valid=bool(citations) and set(citations)<=ids
        rows.append({'task':t,'run':run,'original_rubric':scores,'sql_citation_valid':valid,'passed':scores['task_completed'] and valid})
        out.write_text(json.dumps({'status':'VERIFIED_MEASUREMENTS','limits':'Post-run fix plus 3 supplemental documents. Not a replacement or controlled improvement claim for the frozen 80-task experiment.','health':health,'passed':sum(r['passed'] for r in rows),'total':len(rows),'cases':rows},ensure_ascii=False,indent=2),encoding='utf-8')
        print(t['id'],rows[-1]['passed'],run['status'],flush=True)
if __name__=='__main__':main()
