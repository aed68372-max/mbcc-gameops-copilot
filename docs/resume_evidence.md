# AI 应用 / Agent 实习简历证据

状态：VERIFIED 的内容可按下列边界使用；项目整体 PARTIAL。以下是用户与AI协作开发的工程成果，使用者需能独立讲清代码、指标与取舍；不据此声称全部个人手写、生产上线或真实营收提升。

## 三条可用项目描述

1. 基于 Java 17、Spring Boot 3 与 LangChain4j 实现来源可追溯的游戏知识 RAG，整理45条官方短事实摘要、10个来源URL，完成1024维真实Embedding、分块、元数据过滤及引用校验；42条冻结语料上的48题检索诊断 Recall@5 为98.96%，另完成Milvus适配与持久化测试代码，实机部署待验证。
2. 接入 Ollama Qwen3 的 AI Services 自主工具调用，开发4个带参数校验和审计的工具及6类SQL指标查询；独立Synthetic库实现只读执行、固定参数化SQL、精确日留存与零分母处理，23项SQL/Python独立计算对账全部一致；80题内存Tools实验中工具选择51/80，保留错误与真实调用日志。
3. 构建10类80题冻结评测及4组实际对照（C/D为内存补充实验），分别统计检索、工具参数、任务完成、引用和P95，并分析前10个失败案例；同1.7B、同20题工作流对照中工具选择由5/20至12/20，完成本机REST、会话隔离、深色演示页与分阶段Git交付，明确Milvus部署阻塞和Agent可靠性边界。

## 主张—证据映射

| 主张 | 可核验证据 | 边界 |
|---|---|---|
| 45条 / 10 URL / 1024维 | data/source-index.json、knowledge-v2.json、stage-f/e2e-initial.json health | 最后3条在80题之后补充；异能档案不等于完整战斗技能数值 |
| Recall@5 98.96% | stage-e/retrieval-at5.jsonl、summary.json | 42条语料、48题已知来源、source_id宏平均；非全80题准确率 |
| 4工具 / 6SQL类型 / 23对账 | AgentTools、MetricsGateway、scripts/sql_bridge.py、stage-c/reconciliation.json | 新建Synthetic，未找到Gacha工程；非官方运营数据 |
| 51/80工具选择 | stage-e/D_MEMORY_DIAGNOSTIC.jsonl、summary.json | 集合匹配，最终任务仅34/80；不能称63.75%回答准确率 |
| 同模型5/20→12/20 | stage-a/final-guided-control、final-two-stage | 小样本开发集单次运行；不是模型升级收益，亦非统计显著性结论 |
| 测试与部署 | stage-g/final-build.log、final-real-llm.log、stage-c/junit-database.log、stage-f/e2e-*.json | 默认单元14项、SQL6项、旧真实LLM综合1项；E2E失败单列，Milvus跳过不算通过 |

表中stage-*路径均相对evidence/v2。不得写“Milvus已部署并持久化”“生产级Agent”“检索消除幻觉”“真实游戏流水增长”“复用Gacha成功”“SQL采用专用低权限Windows登录”。尚未验证的内容不得通过简历措辞补齐。

面试应准备解释：为什么高Recall与低任务完成率共存、为何关键词组优于向量组、两阶段工具与结构化输出的取舍、不同测试分母、注册cohort截尾、整数分计费、匿名令牌与正式账号体系的差别，以及本机Windows数据库传输身份的限制。
