# Git 历史与远程导入说明

本机没有可供非交互式Git推送使用的登录凭据，因此通过用户已连接、明确授权的GitHub账号将源码与证据导入目标仓库。远程导入提交与本地阶段提交不是同一批SHA，不能把导入时间当作全部开发时间。

原始阶段历史已在用户明确授权导出完整历史后上传为 [local-history.bundle](../evidence/v2/local-history.bundle)，覆盖至 `b86655abec17794930e1fb4963001ddc86809ed5`，已经过 `git bundle verify`。它包含原版 `c0dd5ee`、阶段A–G、模型比较、80题原始结果和验收；不含该bundle自身及之后的上传说明，避免递归打包。远端同时保留已检查的工作快照和可浏览的 [提交清单](../evidence/v2/local-commits.txt)。原始Git提交对象保存在bundle中，GitHub主分支显示的是导入提交，两者SHA不同。

历史包SHA256：`F6B3B1BE1E256C4183FE0CE28B4EDA8DC1222335505A4E9E7C72C61A34B0C5DA`。Git blob SHA为`8b7089d709b8d643d80fedbd6e023ce38dbf9e2d`；上传返回值与本地一致。大小和覆盖范围另见 [历史包元数据](../evidence/v2/history-bundle.json)。

下载bundle后，在一个新的目录中验证或克隆：

```powershell
git bundle verify local-history.bundle
git clone local-history.bundle mbcc-local-history
git -C mbcc-local-history log --oneline --all
```

`release-integrity.json`记录对应本地快照的Git blob字节SHA256；文本按Git规范化换行。当前远程快照还包括后续上传说明，不能假称其所有文件都包含在较早manifest的文件数内。会话令牌、.runtime、模型权重、target与真实口令没有纳入上传。
