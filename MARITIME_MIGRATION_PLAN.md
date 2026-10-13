# 无 API 个人论文库迁移计划

基线：用户指定的 thinson/RS-PaperClaw main 浅克隆（跳过 papers/previews 图片）。已阅读 README、CUSTOMIZATION_GUIDE、PROJECT_OVERVIEW 及入口、客户端、配置、筛选代码与页面。

原链路：cli run → run_rs_daily_workday → daily_arxiv_cross_filter（遥感硬过滤 + LLM，GitHub Issue 去重）→ paper_processor（PDF、预览、翻译、十问、Issue）→ daily_digest_llm_upgrade → sync_daily_reports_to_repo。原网页读取静态日报索引，并通过 GitHub API 读取 Issue 详情；旧 Actions 使用 LLM/GitHub secrets 和原 CLI。Python 现有测试采用 unittest，网页测试采用 Node 内置 test。

复用 clients/arxiv_client.py 的官方 API、网络重试、限流与备用传输，pipeline_config 的代理配置、现有目录和 unittest/Node test。添加可选通用专题检索函数，保持旧检索函数和遥感规则不变。CLI 最先分派 maritime，避免导入旧 LLM/Issue 链路。

新增 services/maritime.py、config/maritime/*.json、prompts/maritime_analysis.md、docs/maritime.html 与 JS、papers/maritime/library.json、daily_reports/maritime、docs/maritime-data、独立 Actions 和测试、使用说明及最终报告。修改原 cli.py、arxiv_client.py、filter_assets.py 和 README；原 daily_arxiv_cross_filter 和 filter_keywords.json 保留，因为替换它们会改变旧模式。

详细研究兴趣定义按 A/B/C/D 四个专题实现（任务后半部分仍出现三专题，视为旧表述），应用场景是独立加分标签。采用分组封顶的关键词证据和共同概念加分，不能用 Transformer 单词单独入选，不宣称创新性判断。

验证：无 key 本地环境检查、离线候选评分与去重、跨日期合并与失败不写空日报、分析备份往返、网页筛选/排序/Prompt/安全显示、原测试回归。在线检索只运行短、有界请求；正常多页检索可能因上游退避耗时较长，提供完整命令由用户执行。任何在线失败均单独记录，绝不伪装成空结果。
