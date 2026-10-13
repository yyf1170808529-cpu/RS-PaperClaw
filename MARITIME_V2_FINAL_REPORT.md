# Maritime V2 实际交付与验证报告

日期：2026-10-12（北京时间）。仓库：`D:\desktop\code\paper\RS-PaperClaw`。

## 结论与验收边界

V2 已接通正式来源、双分区 OR 判定、海事优先推荐、发表/第一作者信息、双语摘要接口、可选 Argos 翻译、私有 PDF 精读准备及原人工分析闭环。没有重写原项目，没有引入付费 LLM API、数据库或浏览器自动控制 DeepSeek。

**真实 Crossref/OpenAlex 元信息合并、真实期刊网页筛选与 Prompt 复制、真实 ECCV PDF/全文准备已成功。离线中文翻译尚未验收：当前未安装 Argos 和语言模型，5篇真实英文摘要翻译尝试明确失败，英文保留。期刊池的分区覆盖也尚未完成：仅 TIM 的 JIF 2025 条件完成公开证据交叉核验，CAS 官方 2025 大类没有可靠核验记录，其他期刊保持待核验。** 这些限制不能包装成完整 V2 验收成功。

## 本轮新增与修改

新增核心模块（均在现有 skill scripts 内）：

- `clients/scholarly_client.py`：Crossref/OpenAlex 标准库客户端，日期/DOI/ISSN、第一作者机构、摘要倒排还原、OA位置、限流重试与24小时私有缓存。
- `services/maritime_v2.py`：分区证据、正式会议记录、独立推荐、跨来源身份合并与每来源归档状态。
- `services/maritime_reading.py`：可选 CPU Argos、摘要hash缓存/术语保护、人工修订保护、单篇OA或本地PDF、私有Prompt及pdftotext。
- `config/maritime/venues.json`、`recommendation.json`；`requirements-translation.txt`（可选，不改变原 requirements）。
- `tests/test_maritime_v2.py`；`MARITIME_V2_PLAN.md`、`MARITIME_V2_README.md`、`MARITIME_V2_RECOMMENDATION_AUDIT.md`、本报告。

修改：现有 `services/maritime.py` 的 CLI/归档和身份兼容；`clients/arxiv_client.py` 添加官方 DOI/journal_ref 元信息；B专题补充船舶/目标检测同义词；原13项Prompt加入DOI/来源和上传PDF证据要求；原 maritime HTML/JS 增加范围、分区、推荐组、摘要语言控件及信息；原前端测试增加 V2 用例；README和.gitignore补充说明、虚拟环境/私有PDF/备份隔离。

原遥感模式入口、LLM、Issues、页面与旧工作流保留。未修改 GitHub 远端，未 commit/push/创建PR，未部署V2长期调度。新增文件目前仍在工作区，需用户后续提交到自己的Fork。

## 期刊池与分区规则

19本候选：JOES、Ocean Engineering、IEEE JOE、TIV、TITS、TIM、Information Fusion、IEEE TMM、TCYB、Information Sciences、Knowledge-Based Systems、TPAMI、TIP、TCSVT、Pattern Recognition、Transportation Research Part C、TGRS、Remote Sensing of Environment、ISPRS JPRS。完整名称和ISSN种子在 venues.json。

种子只是待核对标识，不是宣称19本均为一区。Crossref检索先检查ISSN对应的实际期刊名；本轮实际验证了TIM的标识和检索，未逐一完成另外18本的在线身份和分区核验。池外OpenAlex来源可保留候选，但不能自动升级高水平。

规则严格区分：

- CAS：scheme=CAS、scope=major、official_table=true、默认year=2025、partition=1，有核验证据。
- JCR：scheme=JCR、metric=JIF Quartile，保留各年份/学科；只用最新已核验年份的有效学科分区，任一Q1即可。JCI/SJR不会进入判断。
- 正式期刊门槛为 CAS OR JIF；“同时一区”单独取 AND。通过发表质量仍须相关性/推荐策略筛选。
- 未核验显示待核验，不根据期刊名称、Crossref或OpenAlex一般字段推断分区。多年份/多学科原始记录保留，相同年份同学科冲突不采用该学科为Q1。

TIM当前核验：JIF 2025=7.0，JCR学科 INSTRUMENTS & INSTRUMENTATION、ENGINEERING, ELECTRICAL & ELECTRONIC。IEEE官方指标页列JCR JIF学科百分位94.4、87.9，对应Q1范围；Comillas大学研究所明确提供2025年JCR-JIF=7.0、Q1，分别于2026-10-12核对。**学科Q1为已核对JIF百分位所对应的分区，证据中明确保存了这个推导方法，并非直接购买JCR原表导出，也不是用JCI或SJR推断。**

证据：[IEEE官方TIM指标](https://ieee-ims.org/publication/ieee-tim/metrics)、[大学JCR-JIF年份表](https://www.iit.comillas.edu/publicacion/info_revista/en/29/ieee-transactions-on-instrumentation-and-measurement)、[Clarivate JIF学科分区说明](https://clarivate.com/academia-government/blog/a-primer-on-ties-in-the-jcr/)。TIM的CAS大类仍待核验。

SJTU公开资料提及JOES“2025中科院一区”，但本轮未取得清楚标示官方**大类**字段的原始表记录，因此没有直接填成已核验大类一区。2026第三方分区不替代官方2025口径。

## 正式来源与真实样例

单期期刊有界查询：TIM、最近366天、最多5条，Crossref成功返回5篇真实正式论文，因还有更多结果标记 incomplete、退出码1。这些5篇主要不是海事感知，保留元信息，但未进入重点推荐；没有把这次截断检索称为全年完整检索。

随后按DOI分别从Crossref和OpenAlex获取并合并：

1. [Maritime Infrared Ship Detection in AAV Imagery Based on Two-Stage Region-Segmentation-Guided Learning Network](https://doi.org/10.1109/TIM.2025.3559575)。IEEE TIM，2025，第一作者Jian Fu，第一作者对应单位 School of Instrumentation and Optoelectronic Engineering, Beihang University, Beijing, China。OpenAlex补全英文摘要，与Crossref同DOI合成一条；JIF通过、CAS待核验，进入海事正式重点组。
2. [ByteTrack: Multi-object Tracking by Associating Every Detection Box](https://doi.org/10.1007/978-3-031-20047-2_1)。ECCV 2022，第一作者Yifu Zhang，单位 Huazhong University of Science and Technology, Wuhan, China。有[官方ECCV论文集PDF](https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136820001.pdf)与出版社DOI关系，独立会议体系核验，进入跨领域正式方法组。英文摘要未从本次两套元信息获得，明确保留缺失，不生成摘要。

两者是历史链路验证样例，不冒充最近7天新文献。DOI查询无日期硬限制；来源任务日志现区分doi_lookup与date_search。Crossref只给年份时不补造精确日期，OpenAlex首日日期也不把Crossref的年精度升级为已核实日；原来源日期保留在metadata_records。海事样例实际展示2025，精确日待出版社核对。

## 数据保护与来源故障

迁移前备份236篇至gitignored `papers/maritime/backups/pre-v2-library.json`；当前243篇唯一记录，其中原236篇全部存在，原145篇入选未删除，现规则入选147篇（加2篇正式样例）。旧reading字段逐条保护测试通过，旧localStorage key与arXiv身份保持。

仅用规范DOI、arXiv或可信元信息的显式对应关系合并，标题相同也不自动合并。若原条目有人工分析冲突，保留到merge_conflicts；别名留存。新DOI/OpenAlex阅读身份已支持备份和CLI导入。正式元信息不会被随后空DOI/原arXiv刷新抹掉。

Crossref/OpenAlex/arXiv按来源执行，每来源/期刊成功即写库、重建网站；其他来源失败不会丢成功数据，整体返回非零。截断标记incomplete。每次任务带run_id，网站展示整个最近来源任务的是否完整，不用最后一个来源成功掩盖其他失败。来源内还没有逐页断点续传。

## 推荐变化与比例

A/B/C/D分类继续保留，另设 direct_relevance、maritime、publication_quality、method_transfer_signal、low_priority 和可解释理由。排序依次考虑感知联系、海事、正式质量、方法信号和时间；机构没有分数。

原高分中的纯轨迹预测、医学VLM、MR配准、EEG解码退到一般候选；不删除有潜在方法价值的工作。25篇旧高分候选已进行标题/摘要片段层的适配检查，见 `MARITIME_V2_RECOMMENDATION_AUDIT.md`。不是论文创新性或全文质量审稿，有些匹配/缺失模态工作仍需要用户复核优先级。

147篇入选的规则场景标签：海事3、交通26、通用118，约2.0%/17.7%/80.3%；这是**整个历史候选库**比例，不是重点推荐比例。推荐资格组：海事正式1、跨域正式1、前沿预印本8、一般候选137。日报和7/14天界面按配置限制分组展示，不再关键词前25篇强行填满。

真实浏览器最近7天默认只显示3篇，其中1篇海事预印本、2篇通用方法预印本；没有近期正式期刊样例。海事70–80%目标、重点前10篇至少8篇相关标准尚未证明；不补造论文或把历史样例当近期样例。需用户执行6–12个月正式来源回溯并扩充分区证据后再次评估。

## 网页与双语摘要

实际浏览器加载了243篇库，新控件正常。切换历史库+JCR JIF Q1后仅显示相关TIM海事论文，显示作者/机构、DOI、2025年JIF两学科、CAS待核验；改成中科院一区显示0篇，证明没有把JIF替代CAS。真实Prompt点击显示复制成功；摘要展开显示“中文暂不可用”，完整英文保留。

Argos作为可选依赖：CPU、本地en→zh模型、英文hash缓存、少量术语/公式保护、失败不阻塞检索/归档、人工译文不被覆盖。安装后同一虚拟环境执行检索可自动翻译新入选；模型只通过显式install-model安装，不在普通检索中偷偷下载。

当前未安装Argos。实际5篇有英文摘要的真实记录翻译尝试均失败，没有中文成功结果。缓存/术语/人工保护的测试使用明确的模拟translator，只证明逻辑，不代表Argos质量。中文质量与Windows依赖安装仍待用户按指南运行安装/模型下载长命令，再做5篇实测；本轮不能评价其科研摘要质量。

## PDF精读与人工闭环

ByteTrack真实PDF从ECCV官方开放源下载至私有目录：6,596,981字节；SHA256 `64f343592e1ccd8b190bafed6d45dfef7d0f9b631dbcc3a4c074d8592bea2435`。pdftotext成功导出64,337字符，标题匹配为true，13项Prompt生成成功。

目录：`papers/maritime/private/reading/0e875c78bf9f135e/`，含paper.pdf、paper.txt、prompt.md、manifest.json；不会进入docs或Git。HTML/登录页会因PDF签名失败被拒绝。非OA论文支持--file指定用户合法本地PDF；不绕过访问控制，不上传DeepSeek或GitHub。该样例仅验证PDF和Prompt准备，不是已阅读全文并审核方法/实验。

现有Markdown粘贴、状态、JSON恢复、CLI导入继续工作。真实DeepSeek PDF上传、模型分析、用户人工粘贴和之后再导入这一完整真人闭环仍待用户验收，没有虚构分析结果来代替。

## 实际测试

|命令/检查|结果|
|---|---|
|根目录 Python unittest discover|33项通过：原网站2 + maritime17 + V2新增14|
|原skill流水线 unittest discover|49项通过|
|Node maritime + 原report-loading|16项通过（8+8）|
|合计|98项，不重复累计子集|
|无Key doctor、site/rescore|成功；doctor报告Argos=False、pdftotext=True|
|Crossref/OpenAlex 两个DOI实取|成功，每次正确记录各来源状态|
|5条TIM有限检索|数据成功保留，明确incomplete/exit1|
|真实期刊网页/机构/OR相关筛选/Prompt|实际浏览器验证成功|
|真实ECCV PDF、全文与Prompt|成功|
|5篇真实摘要Argos翻译|失败：未安装依赖，不计成功|
|git diff --check|通过|

自动化覆盖CAS/JIF OR与AND、最新年份与多学科、JCI/SJR不可替代、年份/大小类错误、证据缺失、身份不符、第一作者机构映射、倒排摘要、弱领域降级、DOI/显式身份合并、标题不合并、旧记录/reading保护、部分来源失败、分区单侧导入保护、DOI阅读备份、译文缓存/失败/人工保护、PDF登录页拒绝、前端时间窗/质量/推荐排序/恢复。

## 操作与剩余工作

操作指南：`MARITIME_V2_README.md`。用户双击start-maritime.cmd启动服务；历史库可直接查看正式样例。正式来源回溯、Argos安装模型、批量翻译按用户习惯提供命令，未擅自启动长程序。

剩余限制：18本期刊分区和多数标识未逐一完成核验；尚无已验证CAS官方2025大类一区记录；JIF记录需定期人工更新，最新核实年份不等于自动获得全球最新JCR；Crossref许多摘要/精确日期缺失；OA链接未必可下载；规则仍会误判领域与迁移联系；原候选库的一般论文多但已从重点入口分离；人工修订中文目前通过CLI；无OCR、无全文全文质量自动评价、无跨设备自动同步；全库静态加载、无并发写锁或跨文件事务。

依需求暂不进行V2长期Actions/Pages部署。建议先完成分区证据扩充、6–12个月相关正式论文回溯、5篇Argos实际翻译和1篇真实DeepSeek人工闭环，再部署自己的Fork。旧V1工作流文件仍在，但本轮未修改或启用用户GitHub设置。
