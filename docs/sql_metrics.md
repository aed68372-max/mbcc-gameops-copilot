# Synthetic SQL 口径与安全边界

状态：参数化SQL与独立对账 VERIFIED；原Gacha数据复用 BLOCKED；生产专用低权限传输身份 PARTIAL。

未在可访问本机目录、已保存项目和数据库列表中找到gacha-liveops-analytics。用户也未提供路径。因此本轮新生成独立MBCC Synthetic教学数据，绝不冒充复用成功：seed20261016，1500用户、18931活跃记录、1856支付、4655参与记录，2025-01-01至2025-02-14。原始CSV、生成脚本和SHA256清单可复现。活动ID和日期均为模拟，公开规则的教学关联不表示真实同期活动，更不能建立因果。

仅新建MBCCCopilotSynthetic数据库及本项目表。原SQLServer仅启用Windows认证，未改认证、TCP或实例配置，也未重启现有SQL服务；不连接WideWorldImportersDW业务表。为避免配置变更，Java通过有25秒期限的本地Python ODBC桥接调用现有共享内存连接。没有另装SQLServer。

查询连接进入mbcc_reader WITHOUT LOGIN数据库用户，EXECUTE AS USER WITH NO REVERT，禁用连接池，身份固定至连接关闭。只授予users/activity/payments/event_participation/dataset_meta的SELECT，DENY INSERT/UPDATE/DELETE/ALTER。真实测试确认写入、REVERT均失败。

重要限制：Windows传输身份原本是本机SQL sysadmin；查询切换后以不可撤销的只读数据库上下文执行，但这不是专用低权限Windows服务登录。生产环境仍应配置专用服务身份/只读登录，不能把本轮验证描述成完成生产权限加固。

## 指标定义

| 指标 | 分子/分母与窗口 |
| --- | --- |
| DAU | 每自然日distinct活跃用户；可按平台及当日活动参与过滤 |
| PAYMENT | 期间distinct付费用户/期间distinct活跃用户，不对每日比例取均值 |
| ARPU / ARPPU | 期间收入/期间活跃人数，或/期间付费人数；金额以整数分存储，展示CNY |
| RETENTION_D1/D7 | 期间注册队列在精确第1/7天活跃的人数/已成熟注册队列人数；排除观察截止后才到目标日的用户，并返回censored_users |
| EVENT_REVENUE | 允许活动ID关联支付的收入分，按event_id分组 |
| EVENT_PARTICIPATION | 期间distinct活动参与用户/期间distinct活跃用户 |

日期为闭区间、Asia/Shanghai教学日历。超出数据覆盖窗口拒绝；零分母返回null，不能伪装成0%或100%。留存采用注册队列，不允许将eventId隐式当暴露队列。平台、日期、eventId和指标均校验；表名/SQL仅由封闭代码定义，所有用户值均为绑定参数。不接受LLM任意SQL。

## 已执行验证

- scripts/reconcile_sql.py：23/23案例，使用CSV集合运算独立计算，与SQL结果对账；不共用SQL聚合函数。
- SqlIntegrationTest：6/6参数化Java数据库集成测试，实际身份mbcc_reader，结果Synthetic=true。
- Java HTTP PAYMENT查询已真实返回口径、窗口和来源：2025-01-11..20为654活跃用户、308付费用户、3380600分；这些数值只属于本项目模拟数据。
- evidence/v2/stage-c/ 保留建库、对账、只读权限证明、JUnit与HTTP证据。
