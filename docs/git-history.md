# Git 历史与远程导入说明

本机没有可供非交互式Git推送使用的登录凭据，因此通过用户已连接、明确授权的GitHub账号将源码与证据导入目标仓库。远程导入提交与本地阶段提交不是同一批SHA，不能把导入时间当作全部开发时间。

本地原始阶段历史保存在本机 `evidence/v2/local-history.bundle`，覆盖至 `b86655abec17794930e1fb4963001ddc86809ed5`，已经过 `git bundle verify`。它包含原版 `c0dd5ee`、阶段A–G、模型比较、80题原始结果和验收；不含该bundle自身及之后的上传说明，避免递归打包。**整个历史包未上传到远程仓库，需要单独明确授权导出。** 当前远端只导入已检查的工作快照和可浏览的 [提交清单](../evidence/v2/local-commits.txt)。清单是辅助索引，不等于远端已保存原始Git对象。

下载bundle后，在一个新的目录中验证或克隆：

```powershell
git bundle verify local-history.bundle
git clone local-history.bundle mbcc-local-history
git -C mbcc-local-history log --oneline --all
```

`release-integrity.json`记录对应本地快照的Git blob字节SHA256；文本按Git规范化换行。当前远程快照还包括后续上传说明，不能假称其所有文件都包含在较早manifest的文件数内。会话令牌、.runtime、模型权重、target与真实口令没有纳入上传。
