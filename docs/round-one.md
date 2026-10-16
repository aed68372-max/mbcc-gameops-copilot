# 第一轮验收记录 — 2026-10-16（Asia/Shanghai）

## 结论

Windows 本机、Java、Maven、Ollama、Qwen、真实 Embedding、内存 RAG、AI Services 工具链和 REST 接口均已实际执行。不是只交付代码或 Mock 演示。本轮没有 Windows/模型不可访问的 BLOCKED 项。Agent 的自然语言自主检索可靠性不达标，见下文。

## 可复核证据

| 项目 | 实际结果 | 证据 |
| --- | --- | --- |
| Windows | 本机可执行、目录可写；未修改全局环境变量 | `evidence/environment.json` |
| Java/Maven | Temurin 17.0.20.1、Maven 3.9.9，下载在本任务 work/runtime 中 | `evidence/environment.json` |
| Ollama | 本机 localhost:11434，0.40.5；复用现有两种模型 | `evidence/environment.json` |
| Java Chat | Qwen3 0.6B 对连通性请求返回“连接成功” | `evidence/real-tests.log` |
| Embedding | Qwen3 Embedding 0.6B，实际输出1024维 | `evidence/real-tests.log` |
| 知识 | 12 条人工整理的官方事实摘要、16 个块，角色/玩法分类；全部带来源/版本/采集日期 | `src/main/resources/knowledge.json` |
| 内存 RAG | 赫卡蒂问题实际召回 char-001，首项分数约0.928；真实生成回答并附来源 | `evidence/http-smoke.json` |
| 无证据 | 未收录角色、未收录版本、太阳质量问题均拒答 | `evidence/http-smoke.json` |
| Mock 测试 | 5 tests，0 failures，0 errors；固定三维假向量，只证明流程 | `evidence/junit-mock.txt` |
| 真实模型测试 | 1 个综合 JUnit 测试，0 failures，0 errors，未跳过；涵盖 Chat/Embedding/RAG/实际工具选择 | `evidence/junit-real.txt`、`evidence/real-tests.log` |
| HTTP | 真实 Tomcat 服务启动，search/ask/agent 返回200，空输入400 | `evidence/server.log`、`evidence/http-smoke.json` |
| 四个工具 | 显式指定工具的请求均观察到真实执行；工具原始结果可查 | `evidence/agent-explicit-probes.json`、`evidence/agent-probes.json`、`evidence/http-smoke.json` |
| Milvus | 未部署验证；本轮仅内存索引。TCP探测不是数据库功能验证 | `evidence/milvus-probe.json` |
| 关系数据库 | 本轮未接入；未连接 WideWorldImporters | `evidence/environment.json` |
| 实际依赖 | 官方文档核实后构建成功，运行包内依赖清单与校验值已保存 | `docs/dependencies.md`、`evidence/runtime-dependencies.txt`、`evidence/checksums.json` |

## Qwen 0.6B 工具调用评估

不能宣称它足以稳定承担通用自主 Agent：

1. 显式给出工具名称时，模拟指标、来源读取、角色检索、玩法检索四种工具均实际执行，有真实 toolEvidence；这证明 LangChain4j 与本机 Qwen 工具协议链路可用。
2. 两个自然语言问题（赫卡蒂生日通信、活动十次保底规则）均直接回答未收录，没有调用工具，即使知识中已有答案。自主工具路由在这两个样例中失败。HTTP 200 只代表接口成功，不能当成质量通过。
3. 指标复述曾把 activeUsers=1000 错说成付费用户数，另有错误金额标签。原始工具事实始终是 activeUsers=1000、payingUsers=50、revenueCny=2500、payerRate=5%、ARPU=2.5 CNY，全部 Synthetic。
4. 已加入已知错误保护：只执行模拟指标工具时，最终 answer 使用工具原文；错误风险较高的模型草稿放在 modelDraft。其他 Agent 摘要仍标为 UNVERIFIED_MODEL_SUMMARY，需对照原始工具证据。
5. 本轮没有自动下载更大模型，也没有把失败换成 Mock 来宣布成功。后续应测试更适合工具调用的本地模型，并建立包含自然语言路由、参数、空结果和事实一致性的评测集。知识问答可先使用直接 `/api/ask` 路径。

原始证据保留：`real-tests-baseline.log` 含早期指标错述；`http-smoke-before-metric-guard.json` 含修复前的真实 HTTP 错述；`agent-probes.json` 含自然语言路由失败。基线日志不是最终版本的验收结果。

## 工程边界与运行过程问题

- 初始环境 PATH 没有 java/mvn。任务内下载便携 JDK/Maven，不改用户全局安装、不改其他项目配置。
- 默认沙箱拒绝外网下载，并曾在读取依赖文件时触发访问错误；经执行环境审批后在同一任务目录完成下载/构建。没有凭此认定本机模型 BLOCKED。
- Windows 正在运行的 JAR 曾导致重新打包文件锁。已通过启动服务的原执行会话结束该服务，再重建并重启；失败日志保留在 `evidence/server-file-lock.log`。
- 服务只监听127.0.0.1，最终验证后保留运行。重启方法见 README；打包更新前应先停止该服务，避免 JAR 锁。
- 没有修改 WeatherSmart/Gacha/WideWorldImporters，没有连接其数据库。所有写入仅在本任务 work/ 和 outputs/ 范围内。
- Git 仓库独立初始化为 main，本地提交使用明确的自动化身份；不设置任何 remote，不 push，不创建远程仓库或 PR。
- 此版本未实现 Milvus/SQL、前端、重排序和增量索引。版本标签表示公告日期，不是未经核实的客户端版本号。
- 没有足够证据支撑完整角色身世、技能数值或技能跨版本变化。检索阈值未经系统校准，小样例通过不能证明普遍准确性。
