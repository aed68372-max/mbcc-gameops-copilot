# RAG 流程与来源边界

状态：PARTIAL（内存路径 VERIFIED；Milvus 实机持久化尚未验证）。

原版 knowledge.json 的12条与原测试保留，正式80题快照中V2追加30条，合计42条、9个官方URL。评测结束后另补3条2026周年限定追踪规则，最终45条、10个URL；这些补充只用于单独回归，不改写80题指标。新增事实来自官方角色档案，包含背景、职业、组织、异能名称与机制。原数据覆盖历史追踪规则、极域重构和生日通信。异能档案不是完整战斗技能系数表，不宣称已覆盖全部战斗定位、世界观或跨版本平衡变化。

data/source-index.json 保存 source_id、标题、URL、公告发布日期、公告版本标签、采集日期、核查状态与摘要SHA256。客户端版本未知时明确 UNKNOWN_NOT_INFERRED。传说和传闻在摘要中明确标注，不能当作已证实剧情。只有人工短事实摘要，没有复制剧情全文、攻略全文或美术。

流程：JSON加载 → 元数据校验/唯一source_id → 空白清洗 → 同URL同内容去重 → 每条作为结构边界，400字符上限 → 真实Qwen3 Embedding → 1024维向量 → 存储 → 过滤后Top-K → 0.70相关性阈值 → 实际来源对象 → 生成/拒答。

- 正式评测V2共有42块，最终补充后45块；旧版按句拆分16块，不能混为同一索引。
- 精确角色、公告版本、category过滤在向量查询之前执行。
- 角色工具返回的 query 可能只含“所属组织”；V2将工具给出的角色名并入查询向量文本，保留同一个元数据过滤。这个通用上下文补全不选择工具、不生成答案。
- Embedding缓存绑定实际Ollama模型digest及文本hash，缓存在.runtime，不当成Milvus持久化证明。
- 关键词对照组使用独立中文二元词重叠排名，不调用向量检索冒充关键词实验。
- 无命中返回空证据。模型应拒答，回答质量与召回命中分别评测；固定阈值未经大规模校准。

## Milvus 适配

依赖采用官方文档对应的 langchain4j-milvus-v2:1.22.0-beta32，实际解析SDK2.6.14，与Core/Ollama1.22.0同一发布系列。适配已编译，不等于服务器验证。Compose固定Milvus2.5.16及官方依赖镜像，端口仅映射127.0.0.1，使用独立命名卷。

MBCC_VECTOR_STORE=milvus显式启用，连接失败不会降级内存后继续宣称Milvus成功。collection由固定紧凑JSON的语料hash命名（不受输出缩进影响）；chunk使用确定性UUID和元数据chunk_id，启动时检查已有块避免重复插入。实际条目数必须从Milvus统计接口获得，不能只引用应用expectedChunks。

验证入口：scripts/verify_milvus.ps1 与 MBCC_MILVUS_TESTS=true 的 MilvusPersistenceTest。两者都要求真实写入、查询、统计、服务重启与重新连接后来源核对。当前状态以 evidence/v2/stage-b/milvus-persistence.json 为准；未完成重启前不写成VERIFIED。
