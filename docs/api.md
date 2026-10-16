# 本地API

默认地址 http://127.0.0.1:18081，仅本机监听。JSON UTF-8，所有游戏来源为公开历史摘要，所有经营数据均Synthetic。

| 方法与路径 | 请求/用途 |
| --- | --- |
| GET /api/health | V2知识数量、维度、存储和模型；不是数据库持续健康探测 |
| GET /api/v2/health | 应用状态、知识存储配置、SQL配置和模型 |
| POST /api/sessions | 空JSON；返回sessionId/accessToken/闲置期限，令牌不能提交到仓库 |
| POST /api/chat | question、sessionId；header X-MBCC-Session-Token；实际有界多轮Agent |
| POST /api/knowledge/search | question、可选character/version/category/topK(1..10) |
| GET /api/characters | 当前目录角色名 |
| GET /api/events | 官方历史文档与Synthetic活动分列 |
| POST /api/metrics/query | metric/startDate/endDate，可选eventId/platform |
| GET /api/evaluation/summary | 已完成实验的实际统计，未完成不填数字 |
| POST /api/v2/agent | 评测入口：question/model/profile/可选有界history；仅允许本机模型与预定义实验路径 |

metric仅允许DAU、PAYMENT、RETENTION_D1、RETENTION_D7、EVENT_REVENUE、EVENT_PARTICIPATION，不接受SQL字符串。时间为YYYY-MM-DD闭区间、最长366天，且须在已观察数据覆盖内。留存eventId过滤不支持，防止错误队列定义。

V2响应含requestId、实际model、profile、耗时、状态、合格reply、模型原始输出、实际tools与调用参数/状态/耗时/来源结果。非OK时reply为空，rawAnswer只用于诊断。HTTP200只代表请求得到结果，不能代替检查内部状态与语义正确性。输入不合法400、错误会话令牌403、依赖执行异常503、整体期限504。

旧/api/search、/api/ask、/api/sources保留原12条兼容范围。/api/agent在正常V2运行中采用新工具链，不继续公开固定模拟指标作为真实经营查询。

示例：
```json
{"metric":"PAYMENT","startDate":"2025-01-11","endDate":"2025-01-20","eventId":"SYN-LIMITED-01"}
```

数据量、指标口径、空值、观察期截尾、权限局限见sql_metrics.md。评测profile只用于研究对照，不应作为生产安全接口对外公开。
