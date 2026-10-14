# V3.3：摘要质量、海事浏览、安全同步与手机日报

日期：2026-10-14。以本地最新代码为基础；本轮开始主库实际3337条，结束仍3337条。原配置配额为水路10、陆上6、通用4，即50/30/20，未修改；V3.2文字中的60/30/10已经与实际配置不一致，本轮不再沿用该表述。期刊一区OR JIF Q1、CCF A及人工精读机制保持不变。

## 摘要污染根因与修复

示例 DOI `10.31673/2409-7292.2026.032817` 的实际摘要来源为OpenAlex `W7213956427`。本地入库的 `metadata_records[0].abstract` 与原摘要逐字一致，均含 `References1...18`；不是本轮出版社HTML提取器把邻近区域拼入摘要。来源提供的摘要已被污染，原流程缺少结构检查，直接用于评分、分类和机器翻译。[官方期刊页面](https://journals.duikt.edu.ua/index.php/dataprotect/article/view/3622)也显示关键词后连续参考文献。

现在保留 `raw_abstract` 及来源元数据，另设 `clean_abstract`、结构检查结果和原文哈希；兼容字段 `abstract` 只承载可用的干净摘要。入库评分、历史规范化及翻译入口均执行同一检查。

- 有明确章节标题及连续编号、年份等共同结构证据时截断；支持References、Bibliography及两种乌克兰语章节名。
- 没有章节名时，只对独立行的连续编号与多个DOI共同出现的引用尾部作保守截断。
- 单个句内references词不会触发截断；异常长摘要、多DOI/URL、疑似粘连或不充分章节证据标记review，原始文本保留，可用摘要暂为空，避免污染评分与翻译。
- 摘要变化导致旧机器译文哈希失效：旧结果保留到历史，页面不再显示，进入重译队列。人工修订保留。
- 网页JSON不包含raw_abstract、原始版本历史、旧机器译文历史或完整来源快照。原始证据仍在主库和私有审计备份中。

全库离线审计结果：

|指标|实际数量|
|---|---:|
|审计记录|3337|
|疑似污染或结构异常摘要|4|
|具有充分引用污染证据|2|
|自动清洗成功|2|
|待人工核查|2|
|评分/分类结果发生变化|4|
|需要重译的原机器译文|1|
|污染清洗后撤销错误海事分类|1|

另一条确认污染为 `10.58286/33659`；待审查为 `10.3389/fpls.2026.1924539` 和 `10.5281/zenodo.23202720`，没有强行截取或编造摘要。

示例：英文 **6125→1971字符**，截断后不含参考文献列表；应用从海事改为通用方法。使用本机离线模型实际重译成功，中文613字符，参考文献DOI数量为0。旧中文仍有历史证据，但不再展示。首次翻译因沙箱阻止读取已安装Stanza配置失败，随后在获准读取后重试成功；没有重新下载模型或PDF。

## 水路相关库与水路推荐

新增独立 `application_bucket`（water/land/general/other），以标题和干净摘要中描述任务、数据或研究场景的句子提供证据；不以推荐门槛确定应用类别。保留原 `recommendation.bucket` 和原配额机制。

- “全部已收录论文＋水路”：实际前端过滤 **152篇**，包括海事历史和非重点候选。
- 满足当前严格水路重点推荐资格：**2篇**。仍需相关研究内容、正式期刊发表证据及已核验一区OR JIF Q1，不能仅靠海事关键词入选。
- 单篇示例的错误海事标签已撤销；相关评分重新计算。
- 默认论文列表继续排除已确认失效、非论文资源及类型未知记录。2篇是全历史资格数量，不等同于当前时间窗或每天最终配额数量。

152篇是清洗后规则认定的相关论文数，不代表已逐篇人工核实全部全文；场景分类仍可能有边缘误判。没有把新规则包装成真实创新性评价。

## 自动同步与云端

桌面现有快捷方式指向项目 `更新论文.cmd`，仍调用同一个 `update_maritime.py`；本轮只在其现有完成阶段接入同步。首次发布白名单保存在 `config/maritime/publication.json`，之后复用：

- `papers/maritime/library.json`
- `daily_reports/maritime/**`
- `docs/maritime-data/**`
- `docs/maritime-daily.html`

自动流程只对实际变更且匹配白名单的文件执行逐路径 `git add -- ...`；不使用 `git add .`。核验用户Fork、main分支、暂存区、未提交代码及远端HEAD；存在重要非白名单修改、已有暂存、未同步提交或远端更新时停止，不reset/rebase/force push。主库出现私人阅读记录/分析冲突时也停止，避免公开个人内容。私有PDF、模型、缓存、备份及日志保持被忽略。

本地更新成功或部分完成后归档，独立输出GitHub推送与Pages发布结果，私有 `latest-sync.json`保留提交和部署URL。同步失败不会回滚已经获取的论文。现有Clash7897仅来自私有网络配置，不写入公开配置。

云端工作流继续执行既有多来源 `--action update`，没有退回单arXiv入口；部分来源失败仍保存此前成功批次。改为复用白名单同步与远端检查。云端GITHUB_TOKEN提交后不假设触发push：本地等待push部署，云端返回 `workflow_run_pending` 后结束，再由既有 `workflow_run`关系部署Pages，避免等待自身完成造成死锁。

真实链路验收：

1. 发布实现提交 `ebe940b`。
2. 使用桌面同一入口执行一次受限真实更新：Crossref/Ocean Engineering、query=ship detection、单页2条、网络10秒、任务20秒、批量翻译0。本轮没有擅自启动完整长检索。
3. API返回2条候选；单页上限导致incomplete，明确显示“部分完成”；新增0、合并0，主库3337条不丢失。
4. 完成摘要检查、去重、已有元数据补全、静态网页与日报重建。
5. **自动**白名单提交及推送 `37b62a1be11ad070346524ae3f25234ae5816d1e`。
6. [Pages运行38512012413](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/38512012413)实际completed/success。日志分别报告本地partial、GitHub success、Pages success。

真实日志：`v33-live-update-sync.log`、`papers/maritime/logs/latest-sync.json`。不是仅YAML解析成功；也不是完整多来源在线检索成功。完整长检索仍由用户双击桌面更新运行；云端改进的下一次每日任务尚未在本轮完整执行。

## 手机每日精选

[手机日报](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html)是独立静态HTML，包含当天最多5篇。小JSON及日期HTML/Markdown保存在 `docs/maritime-data/mobile/`。不请求整库，不要求登录、数据库或通知服务；每次构建当天保持稳定，近7天排除已推送身份，没有足够合格论文可以少于3篇。

2026-10-14实际精选示例：

- CmIVTP: Cross-Modal Interaction-Based Vessel Trajectory Prediction for Maritime Intelligence（IEEE TITS）。
- Toward Robust Collaborative 3-D Object Detection via Two-Stage Cross-Domain Knowledge Transfer in Autonomous Driving（IEEE TITS）。
- DiscoVL（arXiv），以及另外两篇符合现有通用候选要求的arXiv研究。

推荐理由只使用场景、相关性和已核验来源证据，不虚构贡献。用户已用实体手机反馈“能正常打开但是看不到摘要”，因此本轮追加摘要显示：每篇有“查看摘要（中文 / English）”，5篇中4篇有清洗后的英文及现有中文，另1篇明确缺失，不生成假摘要。实际HTML约13KB。

[摘要改进部署38512243421](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/38512243421)实际success。按随后反馈，顶部“5篇 · 规则推荐…”整行已删除；每篇新增现有推荐分数与等级，未新增推荐模型。相关性评分不等于真实创新性：后者仍由现有全文精读模板分析。没有开发自动付费LLM创新评价或设置ChatGPT手机通知。

最终简化与评分部署：[38512443363](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/38512443363)，提交 `e9f4e0e`，实际completed/success。直接读取线上HTML核验13427字节，与该提交Git blob完全一致；含摘要和推荐分数，不含已删除的说明行。

实体手机可访问已由用户实际确认；新增摘要展开效果还需用户刷新后确认。代理浏览器打开尝试超时，未把超时说成手机测试成功。

## 变更与测试

新增：`services/abstract_quality.py`、`services/mobile_digest.py`、`services/maritime_sync.py`、`config/maritime/publication.json`、`tests/test_maritime_v3_3.py`、手机HTML/JSON/Markdown和本报告。

修改：`services/maritime.py`、`services/maritime_v2.py`、`services/maritime_reading.py`、`update_maritime.py`、`docs/maritime.js`、`docs/maritime.html`、`tests/maritime.test.cjs`、`maritime-no-api.yml`、简明指南及真实主库/日报/静态数据。Pages工作流的既有workflow_run关系复用，没有重构检索客户端。

|验证|结果|
|---|---|
|主要Python回归|72通过|
|原技能Python回归|49通过|
|Node前端回归|22通过|
|参考文献结构、句内references误切保护、异常标记|通过|
|机器译文失效、人工译文保护、重复清洗幂等|通过|
|水路场景与质量独立、历史筛选与重点筛选区别|通过|
|发布白名单、代码变更/远端更新时禁止提交推送|通过|
|手机日报不加载整库、当天稳定与次日去重|通过|
|真实受限更新→自动提交→推送→Pages|通过，检索本身partial|
|实体手机能打开日报|用户确认|

原始审计、前库备份和逐条统计位于被Git忽略的 `papers/maritime/private/v3_3/`。未删除阅读记录、原始元数据、人工译文或私有PDF；测试样例未进入真实库。

## 用户操作与限制

- 日常双击桌面“论文更新”，结束后看三个阶段各自结果；不再需要每次提醒推送。
- 手机收藏日报URL，更新后刷新，点击每篇“查看摘要”。完整版选择“全部已收录论文＋水路”查看152篇。
- 两条review摘要需要人工核查；没有全库重新抓取或下载PDF。
- 若网络/API限流、远端更新、工作区代码或私人分析导致停止，同步日志会给原因；不会为了成功提示而覆盖用户修改。
- 页面推荐分数继续表示相关性；全文真实创新性判断使用已有ChatGPT/DeepSeek人工精读。手机消息通知是后续独立功能，本轮未启用。
