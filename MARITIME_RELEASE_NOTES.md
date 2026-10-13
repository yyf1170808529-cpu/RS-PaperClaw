# 2026-10-13 本地版与个人 Fork 发布

推送目标：`https://github.com/yyf1170808529-cpu/RS-PaperClaw`。原作者地址保留为 upstream，不推送到 upstream。

重点推荐改为每批最多20篇：水路12、陆上强相关6、通用计算机高水平2，目标60%/30%/10%。比例用于精选列表与日报，完整候选库保留。某组不足不补位，也不声称已达到目标比例。

水路要求水路场景与感知、检测、融合或关联内容同时出现，排除低优先级领域；陆上要求道路交通、机器人等场景、感知内容与高度相关等级同时满足；通用组要求已核验高水平期刊/会议，并与感知或可迁移方法有联系。水路、陆上候选的分区待核验状态继续如实显示，不冒称已核验高水平论文。配置位于 `skills/rs-paper-pipeline/scripts/config/maritime/recommendation.json`。

新增独立 Pages 工作流，仅发布 docs 静态文件。模型、PDF、私有缓存、备份、虚拟环境均不发布。阅读分析保存在各浏览器，各站点地址之间也不自动同步。

启用方法：个人仓库 Settings → Pages → Source 选择 GitHub Actions，然后在 Actions 手动运行 Publish personal reading page。只有工作流成功后才算实际公开部署成功。

本轮验证：Python 无 API 与 V2 回归33项通过；前端回归8项通过，涵盖专题/应用筛选、Prompt、PDF链接、阅读状态及备份。没有启动模型下载或长时间在线论文检索。
