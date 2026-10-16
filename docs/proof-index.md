# 简历证明材料索引

本页供快速核查。项目由用户与AI协作开发，应用只在Windows本机运行；不是官方产品或生产部署。所有经营数字都是Synthetic。

| 可核查成果 | 证据入口 | 状态与口径 |
|---|---|---|
| Java17 / Spring Boot3 / LangChain4j 实际构建 | [最终构建日志](../evidence/v2/stage-g/final-build.log) | VERIFIED：14项Mock/单元通过，3类真实依赖测试显式skip |
| 真实Java模型、Embedding、RAG与AI Services综合探针 | [真实LLM日志](../evidence/v2/stage-g/final-real-llm.log) | VERIFIED：1项；原版0.6B探针含固定教学fixture，不能冒充真实SQL测试 |
| 独立SQL查询 | [数据库JUnit](../evidence/v2/stage-c/junit-database.log)、[独立对账](../evidence/v2/stage-c/reconciliation.json) | VERIFIED：6项数据库测试、23项独立CSV对账；Gacha复用BLOCKED |
| 真实来源与知识索引 | [来源清单](../data/source-index.json)、[RAG流程](rag_pipeline.md) | 最终45条、10URL、1024维；正式评测是先前42条快照 |
| 同模型工作流对照 | [工具调用报告](tool_calling.md) | 1.7B同20题：选择5/20→12/20；小样本开发集 |
| 80题×4组 | [评测报告](evaluation_report.md)、[原始统计](../evidence/v2/stage-e/summary.json)、[逐题D组](../evidence/v2/stage-e/D_MEMORY_DIAGNOSTIC.jsonl) | PARTIAL：C/D为内存补充，Milvus正式组BLOCKED；D完成34/80、选择51/80、P95 21977.4ms |
| Recall@5 | [逐题检索](../evidence/v2/stage-e/retrieval-at5.jsonl) | 98.96%，48题来源覆盖宏平均，非回答准确率 |
| 多轮/隔离/注入/联合案例 | [原始E2E](../evidence/v2/stage-f/e2e-initial.json)、[人工核验](../evidence/v2/stage-f/manual-review.json) | PARTIAL：自动7/8，人工最多6/8；无来源扩写与联合分析失败均保留 |
| 应用重启 | [重启记录](../evidence/v2/stage-f/e2e-restart.json)、[重启后资料追问](../evidence/v2/stage-f/restart-pronoun-followup.json) | 认证和真实SQL恢复、资料追问成功；元会话回答因无工具证据失败，另保留过期会话403 |
| SQL引用修复 | [8题单独回归](../evidence/v2/stage-f/sql-provenance-regression.json) | 3/8；未替换原80题数据，不能写成全局算法提升 |
| 页面 | [SQL截图](../evidence/v2/stage-f/sql-payment.jpg)、[实验截图](../evidence/v2/stage-f/evaluation.jpg)、[Agent截图](../evidence/v2/stage-f/agent.jpg) | 真实本机页面，无官方原画 |
| Milvus/安装阻塞 | [安装状态](../evidence/v2/stage-g/installation-current.json)、[持久化状态](../evidence/v2/stage-b/milvus-persistence.json) | BLOCKED：WSL组件已启用但待重启，未取得Milvus真实写入/重启持久化证据 |

[三条简历文案及主张—证据映射](resume_evidence.md) · [前10个真实失败](failure_analysis.md) · [API](api.md) · [部署复验](deployment.md)

[完整Git历史包与远程导入说明](git-history.md) · [分项验收JSON](../evidence/v2/acceptance.json) · [快照完整性清单](../evidence/v2/release-integrity.json)

原始JSONL可下载后逐行解析；较大文件在GitHub可能不直接渲染。Git提交是执行记录，不能单独证明模型正确率；请同时检查题集hash、原始输出、实际tool trace、评分分母与失败案例。
