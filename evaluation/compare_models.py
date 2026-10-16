"""Frozen task-level genuine Java AI Services benchmark. No fabricated tool responses."""
import argparse, hashlib, json, math, pathlib, time, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]

def http(url, data=None, timeout=260):
    req=urllib.request.Request(url, None if data is None else json.dumps(data,ensure_ascii=False).encode(),
                               headers={'Content-Type':'application/json; charset=utf-8'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)

def percentile(values,p):
    if not values: return None
    s=sorted(values); pos=(len(s)-1)*p; lo=math.floor(pos);hi=math.ceil(pos)
    return s[lo]+(s[hi]-s[lo])*(pos-lo)

def score(task,run):
    traces=run.get('tools',[])
    actual={t['tool'] for t in traces}
    expected=set(task['tools'])
    selection=actual==expected and len(traces)>=task.get('minimum_calls',len(expected))
    valid=bool(traces) and all(t['status']!='INVALID_ARGUMENT' for t in traces)
    semantic_args=True
    for tool, checks in task.get('args',{}).items():
        if not any(t['tool']==tool and all(t['arguments'].get(k)==v for k,v in checks.items()) for t in traces):
            semantic_args=False
    reply=run.get('reply') or {}
    return {'tool_selection_correct':selection,'parameter_schema_pass':valid if expected else None,
            'annotated_arguments_correct':semantic_args if task.get('args') else None,
            'multi_tool_success':selection if len(expected)>1 or task.get('minimum_calls',0)>1 else None,
            'abstention_correct':bool(reply.get('abstained')) if task.get('abstain') else None,
            'output_schema_pass':run.get('status')=='OK'}

def fraction(rows,key):
    values=[r['scores'][key] for r in rows if r['scores'].get(key) is not None]
    return {'correct':sum(bool(v) for v in values),'eligible':len(values),'rate':sum(bool(v) for v in values)/len(values) if values else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base-url',default='http://127.0.0.1:18081');ap.add_argument('--models',nargs='+',default=['qwen3:0.6b','qwen3:1.7b']);ap.add_argument('--profile',default='guided');ap.add_argument('--output',required=True); args=ap.parse_args()
    source=ROOT/'evaluation/tool_tasks.json'; tasks=json.loads(source.read_text(encoding='utf-8'))
    output=ROOT/args.output;output.mkdir(parents=True,exist_ok=True)
    metadata={'dataset_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'task_count':len(tasks),'profile':args.profile,
              'temperature':0,'seed':42,'think':False,'num_ctx':8192,'num_predict':768,'transport':'Java LangChain4j AI Services',
              'metric_tool_backend_note':'Stage A metrics may return BLOCKED until independent SQL is configured; selection is not task completion.'}
    metadata['health']=http(args.base_url+'/api/v2/health')
    metadata['architecture_note']='guided/baseline use one AI Services stage; structured uses autonomous tool stage then evidence-only schema-constrained synthesis. Limits apply per model call.'
    (output/'conditions.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    summaries=[]
    for model in args.models:
        rows=[];safe=model.replace(':','-');dest=output/(safe+'.jsonl')
        if dest.exists():
            raise SystemExit(f'Refusing to overwrite original benchmark: {dest}')
        # Warm-up is excluded from latency statistics, and its response is retained.
        warm=http(args.base_url+'/api/v2/agent',{'question':'你好，请说明你是非官方助手。','model':model,'profile':args.profile})
        (output/(safe+'-warmup.json')).write_text(json.dumps(warm,ensure_ascii=False,indent=2),encoding='utf-8')
        with dest.open('w',encoding='utf-8') as f:
            for task in tasks:
                start=time.perf_counter()
                try:run=http(args.base_url+'/api/v2/agent',{'question':task['question'],'model':model,'profile':args.profile})
                except Exception as e:run={'status':'HTTP_ERROR','error':str(e),'tools':[]}
                row={'task':task,'run':run,'wall_ms':(time.perf_counter()-start)*1000,'scores':score(task,run)}
                rows.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
                print(model,task['id'],run.get('status'),row['scores']['tool_selection_correct'],flush=True)
        try:memory=http('http://localhost:11434/api/ps')
        except Exception as e:memory={'error':str(e)}
        (output/(safe+'-memory.json')).write_text(json.dumps(memory,ensure_ascii=False,indent=2),encoding='utf-8')
        summary={'model':model,'profile':args.profile,'tasks':len(rows),'p50_ms':percentile([r['wall_ms'] for r in rows],.5),'p95_ms':percentile([r['wall_ms'] for r in rows],.95)}
        for key in ['tool_selection_correct','parameter_schema_pass','annotated_arguments_correct','multi_tool_success','abstention_correct','output_schema_pass']:summary[key]=fraction(rows,key)
        summary['memory_method']='Ollama /api/ps size and size_vram, not OS peak RSS'
        summaries.append(summary)
        (output/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
