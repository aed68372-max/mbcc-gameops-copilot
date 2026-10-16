# 本机部署与复验

状态：Windows Java/Ollama/SQL 混合运行 VERIFIED；Milvus 服务及其持久化 BLOCKED。2026-10-16 已获准安装 Docker Desktop/WSL，Windows 两项组件已启用、WSL 2.7.13 包已安装，仍存在待重启状态。安装程序的成功输出不代表容器引擎或 Milvus 已运行；未自动重启 Windows。

## Windows 应用

依赖 Java 17/21、Maven、Ollama、`qwen3:1.7b` 和 `qwen3-embedding:0.6b`。本机便携 JDK/Maven 放在任务根的 work/runtime，迁移时通过 JAVA_HOME/MAVEN_HOME 提供。模型和依赖版本、digest 见 evidence/v2/environment.json 与 docs/dependencies.md。项目不附带模型权重。

```powershell
.\scripts\build.ps1
.\scripts\run.ps1
# 启用已配置的真实 SQL，而非固定演示数字：
.\scripts\run.ps1 -EnableSql -Python '你的Python可执行文件完整路径'
```

脚本将工作目录切换到仓库，避免会话、审计日志和 SQL 脚本相对路径漂移。默认端口仅绑定 127.0.0.1:18081，首页 http://127.0.0.1:18081/。健康状态见 /api/v2/health；UP 只表示应用已启动，应继续检查 knowledge.store、metrics 与实际查询，不能当作所有依赖持续健康的保证。Java 控制台记录启动错误；每次 Agent 的审计写入  .runtime/agent-v2.jsonl（被 Git 忽略）。本地会话与 embedding 缓存在 .runtime（被忽略），不应公开上传。

环境变量：MBCC_PORT、OLLAMA_BASE_URL、OLLAMA_CHAT_MODEL、OLLAMA_EMBEDDING_MODEL、MBCC_VECTOR_STORE(memory/milvus)、MBCC_MILVUS_URI、MBCC_SQL_ENABLED、MBCC_PYTHON、MBCC_SQL_SERVER、MBCC_PYDEPS。`.env.example` 只是模板；Spring 不会自动读取 .env，需在启动终端设置环境变量。不要把真实口令写进源码或 Git。

## SQL Server

复用现有本机 MSSQLSERVER 与 ODBC Driver 17，Python 需 pyodbc 5.3.0。当前采用 Windows 集成认证、共享内存 lpc:localhost，不开启 TCP、不改 SQL Server 身份认证设置。可用 MBCC_PYDEPS 指向独立安装的 pyodbc 所在目录。另机运行必须先检查这些依赖。

数据生成脚本 scripts/generate_synthetic.py、独立建库 scripts/setup_sql.py、只读桥 scripts/sql_bridge.py、独立对账 scripts/reconcile_sql.py。先阅读 sql_metrics.md。建库脚本只允许目标 MBCCCopilotSynthetic，已有该库会拒绝覆盖；不要删除旧库来绕过保护。当前 SQL 执行上下文为 mbcc_reader、WITH NO REVERT，五张允许表仅 SELECT，写入和 REVERT 均经实际拒绝验证。传输仍使用本机既有 Windows 身份，尚未配置专用低权限 Windows 登录；不能称为生产级数据库身份隔离。

## Milvus（待实际验收）

重启需由用户安排；重启后确认 Docker Desktop 引擎可用，再在仓库终端设置仅本机使用的 MinIO 用户与强口令：

```powershell
$env:MBCC_MINIO_USER='自行设置'
$env:MBCC_MINIO_PASSWORD='自行设置强口令，不提交'
docker info
docker compose -p mbcc -f deploy/compose.milvus.yml up -d
docker compose -p mbcc -f deploy/compose.milvus.yml ps
.\scripts\run.ps1 -VectorStore milvus
# 另开终端，保持相同 Compose 环境变量
.\scripts\verify_milvus.ps1
```

Compose 固定 Milvus 2.5.16、etcd 3.5.18、MinIO 2024-05-28 标签，三组命名卷保留数据，仅 127.0.0.1 暴露 19530/9091。不使用 down -v。镜像与依赖可能需联网下载。Milvus 模式连接失败会启动失败，不会偷偷切换内存。当前已编译兼容连接代码与重启测试，但必须真实写入、计数、查询、重启、重新查询并核对来源后才可改为 VERIFIED。仅安装 Docker 或运行 Compose 均不满足验收。

## 分开执行测试

默认 build 运行 Mock/单元测试，真实依赖测试显式跳过。真实模型、数据库和 Milvus 通过各自环境开关启用；不要把跳过的测试计为通过。JUnit 5 报告在 target/surefire-reports。

```powershell
# 以下在配置好 JAVA_HOME/Maven/Python 的仓库终端执行
$env:MBCC_SQL_TESTS='true'
mvn -Dtest=SqlIntegrationTest test
$env:MBCC_SQL_TESTS='false'
$env:MBCC_REAL_TESTS='true'
mvn -Dtest=RealOllamaTest test
# Milvus 实际运行并同意测试重启该项目容器后：
$env:MBCC_MILVUS_TESTS='true'
mvn -Dtest=MilvusPersistenceTest test
```

正式 80 题：`python evaluation/run_experiments.py`。应独占本机模型、固定数据集及运行条件。脚本拒绝在同一证据目录混入不同模型/知识库；保留原目录，另建新运行目录再评测。无 Milvus 时 C/D 明确改名为 MEMORY_DIAGNOSTIC，不能用于声称完成 Milvus 四组对照。

会话是匿名持有令牌的本地隔离机制，不是登录系统。服务只供本机演示，未实现公网访问控制、分布式会话、生产监控或多人容量验证。应用未部署到公网；用户随后授权将项目与证明材料上传其GitHub仓库，远程上传以实际提交记录为准。
