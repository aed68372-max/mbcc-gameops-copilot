"""Paired experiments on 80 frozen tasks. Milvus groups never silently use memory."""
import argparse,hashlib,json,pathlib,time,sys
from compare_models import http,percentile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from reconcile_sql import reference,equivalent

def evidence(run):
    hits=list(run.get('retrievalEvidence',[]))
    for trace in run.get('tools',[]):
        if isinstance(trace.get('result',{}).get('data'),list):hits+=trace['result']['data']
    return [h for h in hits if isinstance(h,dict) and isinstance(h.get('source'),dict)]

def score(task,run):
    reply=run.get('reply') or {};tools=run.get('tools',[])
    actual={t['tool'] for t in tools};expected=set(task['expectedTools'])
    selection=actual==expected
    retrieved=evidence(run);ids={h['source']['source_id'] for h in retrieved}
    expected_ids=set(task['expectedSources'])
    citations=reply.get('citations',[])
    valid=sum(c in ids or any(c==h['source']['source_url'] for h in retrieved) for c in citations)
    args=[];sql_checks=[]
    for t in tools:
        args.append(t['status']!='INVALID_ARGUMENT')
        if t['tool']=='queryGameMetrics' and task.get('metric'):
            a=t['arguments'];want={k:task[k] for k in ['metric','startDate','endDate','eventId'] if k in task}
            good_args=all(a.get(k)==v for k,v in want.items());data=t['result'].get('data') or {}
            request={k:task[k] for k in ['metric','startDate','endDate','eventId','platform'] if k in task}
            good_rows=data.get('status')=='OK' and equivalent(data.get('rows',[]),reference(request))
            sql_checks.append(good_args and good_rows)
    answer=reply.get('answer','');terms=all(term.lower() in answer.lower() for term in task['answerContains'])
    abstention=None
    if task.get('expectedAbstain'):abstention=bool(reply.get('abstained'))
    if task.get('expectedClarification'):abstention=bool(reply.get('clarification'))
    if abstention is not None:completed=abstention
    else:
        completed=terms and not reply.get('abstained') and not reply.get('clarification')
        if expected_ids:completed=completed and expected_ids.issubset(set(citations))
        if task.get('metric'):
            completed=completed and bool(sql_checks) and all(sql_checks) and ('synthetic' in answer.lower() or '模拟' in answer)
    completed=completed and run.get('status')=='OK'
    return {'task_completed':completed,'tool_selection_correct':selection,
            'parameter_schema_pass':all(args) if args else (False if expected else None),
            'metric_query_matches_csv':all(sql_checks) if sql_checks else (False if task.get('metric') else None),
            'citation_valid':valid,'citation_total':len(citations),'abstention_correct':abstention,
            'retrieved_source_ids':sorted(ids),'source_coverage':len(expected_ids & ids)/len(expected_ids) if expected_ids else None,
            'answer_term_check':terms}

def average(rows,key):
    values=[r['scores'][key] for r in rows if r['scores'].get(key) is not None]
    return {'correct':sum(bool(v) for v in values),'eligible':len(values),'rate':sum(bool(v) for v in values)/len(values) if values else None}

def invoke(base,model,profile,question,history=None):
    try:return http(base+'/api/v2/agent',{'question':question,'model':model,'profile':profile,'history':history or []})
    except Exception as e:return {'status':'HTTP_ERROR','tools':[],'error':str(e)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base-url',default='http://127.0.0.1:18081');ap.add_argument('--model',default='qwen3:1.7b');args=ap.parse_args()
    path=ROOT/'evaluation/tasks80.json';tasks=json.loads(path.read_text(encoding='utf-8'));assert len(tasks)>=80
    out=ROOT/'evidence/v2/stage-e';out.mkdir(parents=True,exist_ok=True)
    health=http(args.base_url+'/api/v2/health');is_milvus=health['knowledge']['store']=='MILVUS'
    groups=[('A_DIRECT','direct'),('B_KEYWORD','keyword')]
    if is_milvus:groups += [('C_MILVUS_RAG','rag'),('D_MILVUS_TOOLS','tools')]
    else:groups += [('C_MEMORY_DIAGNOSTIC','rag'),('D_MEMORY_DIAGNOSTIC','tools')]
    metadata={'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tasks':len(tasks),'model':args.model,
              'temperature':0,'seed':42,'think':False,'num_ctx':8192,'num_predict':768,'health':health,
              'method':'Serial requests. Dialogue seeds are actual model responses, not golden assistant text. Exact answer-term checks are conservative automated rubrics, not human semantic accuracy.',
              'limits':'Single run per task; no statistical significance or causality claims. Model output shape/citation validation failures count as errors. SQL verification is independent CSV arithmetic; answer wording is not a full semantic judge.'}
    metadata_path=out/'conditions.json'
    if metadata_path.exists():
        previous=json.loads(metadata_path.read_text(encoding='utf-8'))
        if any(previous[k]!=metadata[k] for k in ['dataset_sha256','model','num_ctx','num_predict']):raise SystemExit('Cannot resume under changed conditions')
        if previous['health']['knowledge']!=metadata['health']['knowledge']:raise SystemExit('Cannot mix changed vector-store/corpus conditions in one experiment directory')
    else:metadata_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    # Retrieval metric is a separate frozen question-only diagnostic, never the expected answer fed to the model.
    recall_file=out/'retrieval-at5.jsonl';recall=[]
    if recall_file.exists():recall=[json.loads(line) for line in recall_file.read_text(encoding='utf-8').splitlines()]
    done={r['taskId'] for r in recall}
    with recall_file.open('a',encoding='utf-8') as f:
        for task in tasks:
            if not task['expectedSources'] or task.get('history') or task['id'] in done:continue
            try:hits=http(args.base_url+'/api/knowledge/search',{'question':task['question'],'topK':5})
            except Exception as e:hits=[]
            got={h['source']['source_id'] for h in hits};want=set(task['expectedSources'])
            row={'taskId':task['id'],'expected':sorted(want),'retrieved':sorted(got),'recall_at5':len(got&want)/len(want),'hits':hits}
            recall.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
    summary={'status':'VERIFIED' if is_milvus else 'PARTIAL','model':args.model,'task_count':len(tasks),
             'milvus_groups_status':'VERIFIED_EXECUTION' if is_milvus else 'BLOCKED_NO_MILVUS_SERVER',
             'rag_store':health['knowledge']['store'],'recall_at5':sum(r['recall_at5'] for r in recall)/len(recall) if recall else None,
             'recall_eligible':len(recall),'recall_definition':'Macro-average relevant source-id coverage in top5, only tasks with known sources and without pronoun history; deduplicated source ids.',
             'groups':[]}
    for name,profile in groups:
        dest=out/(name+'.jsonl');rows=[]
        if dest.exists():rows=[json.loads(line) for line in dest.read_text(encoding='utf-8').splitlines()]
        finished={r['task']['id'] for r in rows}
        with dest.open('a',encoding='utf-8') as f:
            for task in tasks:
                if task['id'] in finished:continue
                history=[];seeds=[];start=time.perf_counter()
                for turn in task.get('history',[]):
                    seed=invoke(args.base_url,args.model,profile,turn['user'],history);seeds.append(seed)
                    history.append({'user':turn['user'],'assistant':(seed.get('reply') or {}).get('answer','[invalid model response]'),
                        'toolSummary':' '.join(t['tool']+':'+t['status'] for t in seed.get('tools',[]))})
                run=invoke(args.base_url,args.model,profile,task['question'],history)
                row={'task':task,'run':run,'dialogueSeeds':seeds,'wall_ms':(time.perf_counter()-start)*1000,'scores':score(task,run)}
                rows.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
                print(name,task['id'],run.get('status'),row['scores']['task_completed'],flush=True)
        group={'name':name,'profile':profile,'executed':len(rows),'task_completion':average(rows,'task_completed'),
            'tool_selection':average(rows,'tool_selection_correct'),'parameter_schema':average(rows,'parameter_schema_pass'),
            'metric_query_matches_csv':average(rows,'metric_query_matches_csv'),'unanswerable_handling':average(rows,'abstention_correct'),
            'p50_ms':percentile([r['wall_ms'] for r in rows],.5),'p95_ms':percentile([r['wall_ms'] for r in rows],.95),
            'error_count':sum(r['run'].get('status')!='OK' for r in rows),'error_rate':sum(r['run'].get('status')!='OK' for r in rows)/len(rows)}
        total=sum(r['scores']['citation_total'] for r in rows);valid=sum(r['scores']['citation_valid'] for r in rows)
        group['citation_validity']={'valid':valid,'total':total,'rate':valid/total if total else None}
        summary['groups'].append(group)
        (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    if not is_milvus:summary['required_unexecuted_groups']=['C_MILVUS_RAG','D_MILVUS_TOOLS']
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
