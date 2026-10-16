"""Versioned derived report. Never changes frozen tasks, raw answers, or original scores."""
import json,pathlib,collections,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1];E=ROOT/'evidence/v2/stage-e'
def main():
    summary=json.loads((E/'summary.json').read_text(encoding='utf-8'));groups=summary['groups'];assert len(groups)==4 and all(g['executed']==80 for g in groups)
    raw={g['name']:[json.loads(s) for s in (E/(g['name']+'.jsonl')).read_text(encoding='utf-8').splitlines()] for g in groups}
    derived={'version':1,'note':'Post-run definitions clarified; frozen answers and original score files unchanged. Exact argument metric is limited to 16 tasks with explicit SQL field annotations.','groups':{}}
    for name,rows in raw.items():
        annotated=[r for r in rows if r['task'].get('metric')];correct=0
        for r in annotated:
            task=r['task'];calls=[t for t in r['run'].get('tools',[]) if t['tool']=='queryGameMetrics']
            fields=['metric','startDate','endDate','eventId','platform'];expected={k:task[k] for k in fields if k in task}
            correct+=bool(calls) and all(all(t['arguments'].get(k)==v for k,v in expected.items()) for t in calls)
        multi=[r for r in rows if len(r['task']['expectedTools'])>1]
        multi_ok=sum(r['scores']['tool_selection_correct'] and all(t['status']=='OK' for t in r['run'].get('tools',[])) and r['run'].get('status')=='OK' for r in multi)
        derived['groups'][name]={'annotated_sql_arguments':{'correct':correct,'eligible':len(annotated)},'multi_tool_execution_and_selection':{'correct':multi_ok,'eligible':len(multi)},'category_completion':{k:{'correct':sum(r['scores']['task_completed'] for r in rows if r['task']['kind']==k),'total':sum(r['task']['kind']==k for r in rows)} for k in sorted({r['task']['kind'] for r in rows})}}
    (E/'derived-v1.json').write_text(json.dumps(derived,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 80 题算法评测报告','', '状态：PARTIAL。A/B 与补充内存 C/D 各实际执行 80 题；正式 C_MILVUS_RAG、D_MILVUS_TOOLS 为 BLOCKED，未伪装成已部署。','',
           '## 固定条件','',f"模型 {summary['model']}；温度0、seed42、think=false、上下文8192、输出768 token。题集 SHA256 `{hashlib.sha256((ROOT/'evaluation/tasks80.json').read_bytes()).hexdigest()}`。42条知识、9个官方URL，1024维真实 Embedding，内存存储。原始软件快照见 commit 2b0cc03 与 conditions.json。后续增加的限定追踪摘要只用于补充回归，不混入本轮结果。",'',
           '80条内部人工题，10类各8条，非外部盲测。逐组串行，未隔离整个桌面负载，每题一次，无显著性或总体可靠性声明。多轮前文来自模型真实输出，未填入黄金助手答案。SQL数字独立从CSV计算对账。','',
           '## 实测结果','', '| 组 | 规则判定完成 | 工具选择 | 参数Schema | 无答案/澄清 | 引用有效 | P50 ms | P95 ms | 错误 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    def ratio(d):return f"{d['correct']}/{d['eligible']}"
    for g in groups:
        tools=g['profile']=='tools';c=g['citation_validity'];lines.append(f"| {g['name']} | {ratio(g['task_completion'])} | {ratio(g['tool_selection']) if tools else 'N/A'} | {ratio(g['parameter_schema']) if tools else 'N/A'} | {ratio(g['unanswerable_handling'])} | {c['valid']}/{c['total']} | {g['p50_ms']:.1f} | {g['p95_ms']:.1f} | {g['error_count']}/80 |")
    lines+=['',f"独立检索诊断 Recall@5 = {summary['recall_at5']:.4%}（{summary['recall_eligible']}题）。按有已知来源、无代词历史的题统计Top5中去重source_id的覆盖率，再宏平均；不是全80题的端到端事实准确率。",'',
        '## 指标解释与可比较边界','',
        '- 完成率要求全部标注关键词、全部预期来源引用、非无端拒答；SQL题还要求日期/指标匹配、实际SQL结果与独立CSV相等并声明Synthetic。无答案/歧义题要求相应标志。是保守规则评分，不能替代逐句事实审查。',
        '- Direct组无法取得真实检索来源，因此有来源要求的事实题会失败；此处测的是“可核查证据任务完成”，不能把A与D差值宣传成通用语言理解准确率提升。',
        '- 引用有效只表示引用来自本次实际召回，既不表示每条引文完整支持结论，也不表示在线URL每次HTTP检查成功；缺失引用不进入有效率分母，但会影响完成率。',
        '- 原始tool_selection在无工具组仍计算空集合匹配，本报告显示N/A。parameter_schema_pass仅检验已执行调用未被标为INVALID_ARGUMENT；不是所有字段的语义准确率。',
        '- 额外字段准确率仅用预先标注的16道SQL题，检查metric/startDate/endDate/eventId/platform；不将其外推为所有自然语言工具参数准确率。派生定义和分层结果见derived-v1.json。',
        '- 原20题summary中的multi_tool_success只代表选择集合/次数；derived-v1另计算80题中集合正确、各工具OK、最终门禁OK的多工具执行率，仍不等于业务结论正确。',
        '- 错误率指HTTP/模型/格式/引用/证据门禁未OK；status=OK并不代表语义完全正确。P50/P95为HTTP实测wall time，多轮题包含实际前置轮次；不是首token延迟。',
        '- 关键词B完成率高于内存向量C；不能声称向量检索在本小语料上全面优于关键词。高Recall也未消除路由、参数、拒答与整合错误。', '', '## 复现与证据','',
        'run_experiments.py固定题集、保留原始逐题JSONL和实际工具结果；report_results.py只写派生报告，不覆盖原题或原评分。conditions.json、retrieval-at5.jsonl、四组JSONL、summary.json可逐项核对。模型比较与同模型架构比较见tool_calling.md；SQL、JUnit、E2E单独统计。']
    (ROOT/'docs/evaluation_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    failures=[r for r in raw['D_MEMORY_DIAGNOSTIC'] if not r['scores']['task_completed']]
    failure_lines=['# 主要失败案例（真实原始输出）','','状态：VERIFIED_MEASUREMENTS / PARTIAL_CAPABILITY。以下从D内存Tools组失败项按题号取前10条，未删除失败或修改答案。完整逐题结果优先于摘要。','', '| 题号 / 类别 | 问题 | 观测 | 失败证据 |','|---|---|---|---|']
    for r in failures[:10]:
        run=r['run'];s=r['scores'];task=r['task'];answer=(run.get('reply') or {}).get('answer') or run.get('rawAnswer') or run.get('error') or ''
        reason=[]
        if run['status']!='OK':reason.append('门禁:'+run['status'])
        if not s['tool_selection_correct']:reason.append('工具集合不符')
        if s['parameter_schema_pass'] is False:reason.append('参数/缺调用')
        if not s['answer_term_check']:reason.append('缺标注事实词')
        if s['metric_query_matches_csv'] is False:reason.append('SQL参数/结果缺失或不符')
        if s['abstention_correct'] is False:reason.append('拒答/澄清不符')
        missing=set(task['expectedSources'])-set((run.get('reply') or {}).get('citations',[]))
        if missing:reason.append('缺引用:'+','.join(sorted(missing)))
        short=str(answer).replace('|','/').replace('\n',' ')[:170]
        failure_lines.append(f"| {task['id']} / {task['kind']} | {task['question']} | {'；'.join(reason) or '未满足完整规则'} | {short} |")
    failure_lines+=['','## 根因与后续动作','','召回、工具选择、字段生成、证据整合分别验收。少量参数合法或格式合格不能代表答案正确。部分失败来自模型漏调第二角色/SQL工具、把常规追踪误当限定、缺事实词或引用，以及无证据时误答。先核对对应原始trace，再针对工具说明或通用检索上下文修复；不得写问题关键词路由器或把测试答案塞进提示。新增修改需要独立回归，不能重写本轮基线。','','4B在早期20题出现长思考/截断及高延迟；该结果受当前运行参数与协议影响，不意味着所有4B模型能力都低于1.7B。Milvus因主机待重启未验证、Gacha工程未找到、SQL传输仍用本机Windows身份，均保留为交付边界。']
    (ROOT/'docs/failure_analysis.md').write_text('\n'.join(failure_lines)+'\n',encoding='utf-8')
    print(json.dumps(derived,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
