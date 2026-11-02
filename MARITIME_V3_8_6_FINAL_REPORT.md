# V3.8.6 实施与阶段验收报告

## 已实际完成

安全快进至be33d3a，原主库及手机归档备份于papers/maritime/backups/v3_8_6。复用官方DeepSeek客户端及原Key读取，没有重做相关性评审，没有修改医学排除/可信来源/永久去重。

新建独立reading_translation模块和reading_translation.json配置。每篇一次JSON请求生成summary_zh、migration_zh和abstract_zh；保留模型、摘要SHA256、Prompt版本、时间、usage、计价、失败候选与审计记录。成功缓存直接复用。明确失败内容最多一次修正；网络不确定扣费POST不重试。分类预算每日0.5元、旧积压1元，总上限3.5元，与筛选分类分别记账。不是全库翻译。

真实处理：当前11月2日正式五篇 + 10月24日明确未读五篇，共10个唯一身份，均为真实API输出。其他reading-index旧批次尚未补译；日期范围不是精确浏览器未读状态，未读取用户私有localStorage。

本次筛选调用0次。精译费用与usage如下（包括校验失败的已完成响应，不隐瞒失败费用）：

{
  "daily_translation": {
    "requests": 6,
    "tokens": 5572,
    "priced_cny": 0.012871
  },
  "backlog_translation": {
    "requests": 7,
    "tokens": 5898,
    "priced_cny": 0.013413
  }
}

以上为API usage按请求时段价格计算的费用，不冒充独立账户账单差额。原文/旧Argos/新DeepSeek逐篇对照保留在忽略目录comparison.json，覆盖十篇。三份初译数值校验失败，分别有界修正；ForestQuery第二份实际忠实地将3D译为“三维”，经等价表达复核后离线重新验证成功，没有再付费。没有删除困难句子绕过校验。

导读示例：

论文内容：UnfoldCRF将掩码细化建模为像素标签与潜在区域变量上的条件随机场推断，通过展开阻尼平均场更新，在同等参数与监督下比黑箱递归细化器更准且更鲁棒。

迁移思路：研究推断：可将图像条件潜在区域一致性及零状态退出机制迁移到船舶检测/分割的掩码后处理模块，或作为Radar–AIS、视觉–AIS关联中多源证据一致性约束，以输入掩码与图像特征作监督、在关联头后加轻量区域消息传递。

## 兼容与发布实现

主发布流程增加DeepSeek精译分支，仍沿用有限时间、替补和完整五篇发布保护。人工译文优先；Argos历史数据保留。两句式独立展示，reason留作内部兼容字段。reading-enrichment.json是独立缓存，translation-upgrades.json为精简公开升级数据。手机旧快照核对ID及英文SHA256后仅替换中文导读/摘要/译文版本，不改日期、身份、完成状态、shown、笔记或收藏；编辑笔记时延后。英文Prompt模板不变。

## 尚未完成，不可视为全量验收

尚未运行一次新的完整云端自动更新作端到端验收；现有Actions安装Argos/PyTorch/Stanza步骤仍保留。本轮没有满足用户规定的模型清理前置条件，因此未删除模型、依赖或云缓存，释放空间为0。

项目专属待清理目录：D:\desktop\code\paper\RS-PaperClaw\papers\maritime\private\translation，实际文件大小150.65MiB。其他项目及用户级模型目录未删除。私有PDF、计费账本、备份和人工译文均保留。

待完成：reading-index中10月31日、11月1日等后续旧批次的有界补译、实体手机旧快照实测、新完整Actions验收、经核实后的Argos步骤/worker/依赖清理及项目专属模型实际删除。没有把本地测试或Pages成功等同于这些要求已经完成。

长时间云端更新按用户执行偏好不在本地擅自启动；完成本次代码同步后可从项目目录运行：

```powershell
cd D:\desktop\code\paper\RS-PaperClaw
python skills/rs-paper-pipeline/scripts/update_maritime.py --resume --no-open
```

该命令触发现有云端工作流并显示任务链接；本地模型清理应在真实成功后继续执行。

测试：Python149项、Node45项通过，含SHA/身份失配拒绝、中文字段定向升级、人工译文优先、原英文/标题/笔记保护；git diff --check及密钥模式扫描通过。核心提交c4a9d60对应Pages运行41458372134已completed/success。真实HTTPS读取每日HTML、latest五篇JSON、旧快照升级清单均HTTP200，与本地一致；补充升级函数提交5cb5ba2的第二次Pages部署尚在核验。完整云端更新和实体手机实测仍未完成。
