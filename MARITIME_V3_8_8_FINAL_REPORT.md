# RS-PaperClaw V3.8.8 实际验收报告

## 当前基线与审计

2026-11-05执行。本地初始HEAD 1fcde80、工作区干净；fetch后安全快进至c9c9d4b，保留三次定时更新及4214条主库记录。没有覆盖未提交修改或force push。原V3.8.7代码已部署，近期自动更新41962053379及Pages41963787066成功。接力文档RS_PaperClaw_接力文档_20261105.md在本项目和父工作区递归检索未找到，未假称已读；已阅读V3.8.7报告及最新代码。修改前主库、后备池和API证据保存在忽略目录papers/maritime/backups/v3_8_8。

## 三篇完整处理链路

|论文|上游发现/主库|原场景/推荐bucket|旧AI原始分/置信度|原hard/ranking|正式归档|新判定|
|---|---|---|---|---|---|---|
|2609.30891 Adaptive Pilot Selection|OpenAlex，已入库，真实arXiv身份|land/candidate|direct2、transfer2、confidence0.82，decision不推荐|True/eligible，AI40|11月4日|通信导频优化，other/candidate，hard=False，ranking domain_excluded，不在候选与可用后备|
|2609.16336 Illusion of Depth|OpenAlex，已入库，真实arXiv身份|land/candidate|direct2、transfer2、confidence0.7，decision候选|True/eligible，AI40|11月4日|物理攻击/立体视觉漏洞，other/candidate，hard=False，ranking domain_excluded，不在候选与可用后备|
|10.1016/j.inffus.2026.104909 AIS-Vision|Crossref，10月29日02:32 UTC首次入库，11月5日仍被检索|water/candidate|无AI缓存，未评审|False/unassessed|从未正式推荐|已补核验JIF Q1、water/water；缺摘要仍不允许正式入选或虚构AI评价|

两篇负例的具体摘要证据、原始AI JSON、候选池、后备池及历史日期逐项保存在chain-audit.json，不只检查最后日报。通信论文旧method_evidence为“encoder … OFDM grid”及“pilot configuration … optimized … channel conditions”；安全论文为“similarity scores … suppress depth discrepancies”及“stereo-LiDAR fusion model”。前者AI自己已说明通信层不相关，后者也说明主要是攻击评测，但direct_task/traffic_task只凭摘要有车辆/感知而走直接路径。问题是核心任务和实验场景未区分，不是arXiv身份错误，也不是分数不足。

## AIS-Vision实际阻塞、来源与召回

Information Fusion原本已enabled，位于water/land/general检索期刊池；ISSN1566-2535正确，现补电子ISSN1872-6305。原配置只有JIF数值，没有CAS/JIF分区证据，所以high_journal=False。不是没有覆盖该期刊，也不是本文被排名挤走。

本次核验机构托管的[JCR分类表2024](https://kniznica.umb.sk/app/cmsSiteBoxAttachment.php?ID=6181&cmsDataID=0)与[人工智能学科表](https://cdn.umfcluj.ro/uploads/2024/08/JCR_2024_iunie2025.pdf)，保留两个学科JIF Q1；另核对[机构2026发布表](https://www.niic.nsc.ru/phocadownload/publications/2025/JCR_JournalImpactFactor_2026.pdf)，Information Fusion行明确JIF Quartile Q1，按表头2026 release及journal_overall保存，不编造缺失的学科。CAS2025未核实，仍为空；没有把JCI/SJR当JIF。

Crossref返回仅2026-10月份，OpenAlex返回2026-10-01；Elsevier官方coredata DOI、完整标题一致，coverDate明确2026-10-28，因此保留旧日期证据并修正在线日期。原90天水路窗口覆盖它。新增AIS vision、vessel instance segmentation、maritime visual perception短组合，实际Crossref查询AIS vision、2026-08-08至11-05返回8条且完整，其中包括目标DOI（query-proof.json），没有DOI白名单。

**仍未满足项：真实可用英文摘要。** Crossref无abstract、OpenAlex无abstract_inverted_index、Semantic Scholar官方API abstract=null；Elsevier公开API只返回coredata，META视图401，ScienceDirect页面403。聚合站搜索结果有摘要，但没有可靠再发布许可，未将它冒充授权官方摘要，也没有从用户列出的模块自行生成英文摘要。正例已在主库，期刊资格已修复；生产hard_eligible仍因缺摘要False，不会将未评审记录塞进日报。正向规则测试使用明确标注的测试摘要，不能冒充该论文真实API成功。现有补全链增加每日最多3篇高相关海事正式期刊的有限网络补全，A方向优先；失败保留abstract_check并次日重试。公开来源补齐后可自然进入AI队列，不重抓整库、不绕过访问限制。

## 研究范围与AI结构

新增核心目标证据层，按标题或“we/our/this work + propose/optimize/reveal”等研究贡献句识别通信系统优化、安全攻击漏洞及无关专用工业巡检。单独ISAC、adversarial、robust、segmentation不作为排除；ISAC目标定位、鲁棒跨模态表征（攻击仅为评估）保留反例测试。原医学及基础设施规则保留。标签A海事关联融合、B船舶视觉、C交通感知、D通用机制独立记录，发表门槛另行核验。范围阻断在AI候选之前及最终资格/储备/阅读队列均生效。

新API输出要求primary_domain、primary_problem、target_task、core_contribution、application_context、security_centric、communication_centric；原精确引文/迁移路径/分数/置信度字段保留。新响应强制校验新增结构，区分核心贡献和验证场景；任一核心排除flag为True仍阻断。旧响应允许原结构，先用确定性范围规则复审，无需全库重新付费。原fingerprint函数、schema2、preferences均未改变；原先有效的纯分类变化缓存沿用现有compatible_fingerprints机制。没有仅以AI decision标签代替领域/任务及证据判断。

为避免4篇扩展JSON被旧3000-token上限截断，仅把max_tokens改为5000；模型、非思考模式、每日2元审核预算、精译预算均不变，账本仍提前预留上界。

## 作者展示与用户数据

手机服务端HTML、手机持久阅读快照渲染、桌面卡片统一第一作者；只有明确来源+verified的corresponding_authors才显示通讯作者，第一作者同名标注一次，多通讯作者压缩。禁止最后作者推断。Crossref/OpenAlex只采纳明确is-corresponding/is_corresponding字段；原authors顺序和完整列表继续保留在主库与Prompt中。新增小型Python/JS展示函数，无新作者服务或批量查询。

11月4日两篇误推荐追加到content-corrections，replacement=null，保留原归档、英文、DeepSeek译文及原AI JSON；旧未读快照沿用既有安全修正机制，保留其余条目、日期、shown、完成状态及待修正原始内容，不强制已读、不凑替补。收藏、笔记及Prompt模板没有迁移或清空。不合格历史批次不再进入合格reading-index；原永久去重账本不清除，避免重新推送。

## 真实离线回放

修改前候选1256、已评审895、合格7、精选5；修改后{"candidate_count": 1253, "ai_reviewed": 893, "ai_states": {"evaluated": 893, "uncertain": 357, "unassessed": 3}, "stage_counts": {"1": 37, "2": 1166, "0": 11, "3": 39}, "ai_rejected": 885, "translation_deferred": 1, "qualified_count": 7, "selected_count": 5, "shortfall": 0}。可用后备3。原有效AI缓存1399→1399。新增范围排除15条（包括非论文编辑文章，仍以资源类型再核验），没有删除主库记录。dry-run自身API调用0、费用0；不是实际AI质量提升测量。

## 测试与部署

本地Python158项、Node49项通过，含核心通信/攻击负例、ISAC感知正例、船舶无AIS正例、真实SNAP/ROSETTA旧缓存、arXiv/正式来源、候选/精选/储备/reading-index、作者不同/同一/多个/未知通讯作者、桌面真实渲染及私人快照保留。云端与HTTPS真实发布证据见末节，不以单元测试代替上线。

## 云端首轮实际证据与验收发现

首次代码提交c0db920；作者Markdown补充提交cc0353d3108d5cfa89d7f25d685d36efdea7e400。

[云端42016246930](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/42016246930) completed/success，真实执行head cc0353d，数据提交c7c1aea已安全快进合并。恢复模式明确0项来源任务，不冒充完整多来源检索。实际完成主库去重/有限缺摘要补全、AI、精选缓存复用、静态构建及安全同步；新补全1条摘要（不是AIS-Vision），AI新审核1篇，缓存1250，3条当天尝试过的记录未重复POST。新审核2480 tokens、计价0.00358812元，上界0.00717624元；精译5条均命中缓存，新增翻译调用0、费用0。费用来自API usage及时段计价，不是独立账单差额。新响应实际包含七项研究目标字段，完整证据在忽略目录cloud-logs，不公开凭据与原始日志。

本轮不是只加标题黑名单：新响应primary_domain采用显式研究领域枚举并直接参与资格门槛；A/B/C领域才能走任务路径，D必须额外满足可复用机制及具体迁移证据，通信/安全/医学/巡检/其他不能通过实验场景或迁移高分绕过。旧缓存及初始自由文字领域响应保留兼容解析，优先确定性审查，不批量清空或重新收费；新付费响应强制校验枚举及全部结构。增补vessel/vessels视觉对象，同时继续防止blood vessel误判船舶。

真实云端补全同时暴露：Crossref的2026-10又覆盖了已核实的2026-10-28。已在统一merge_records中保护同月的精确日期与来源，保留月份原始版本；恢复官方日期，增加合并回归。明确通讯作者信息也不会被后续“未提供通讯标记”的元数据静默清除。补充修改已由后续云端恢复验收覆盖。

安全修正旧未读批次若少于五篇，保留原完成状态；只在用户主动点击后才完成剩余内容，次日按原队列推进，避免旧批次因删去两篇误推荐而被困住。未自动标记已读，收藏/笔记独立存储不变。全部Markdown日报也已改为同一作者简显规则，完整作者仍在数据和Prompt中。

## 最终边界回归与补选

第二次[42018165968](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/42018165968) completed/success，head 3b73bde348c9615977a31527f06377d727d7801d，数据3ee0a98已安全拉回。AI缓存1251，新增审核0、tokens0、费用0；精译缓存5、新增调用0。AIS-Vision日期仍为2026-10-28，证明精确日期保护在真实云端持续生效。

最终反例审查补充安全攻击工具箱和LiDAR攻击规划这两类明确安全目标，避免只匹配physical adversarial attack一种表述；可复用跨模态/特征学习以攻击为评估的标题及贡献句均有例外反例测试。实际历史LiDAR-SHIELD及当前TACTIC（完整标题为Temporal and Context-Aware LLM Tactical Planning for Roadside LiDAR Attacks，摘要明确安排物理攻击和诱发碰撞）因此被阻断，不把它们当交通感知算法。没有为标题建立单篇ID黑名单。11月3日原归档不重写；11月5日修正前JSON及永久历史账本先复制到忽略目录pre-final-scope，并保留Git原版本。

同日五篇保护继续生效：离线重建时，四篇有效内容保留，TACTIC由已有有效AI审核的正式期刊船舶检测论文MARS and ETMS（10.1109/tits.2026.3727609）替补候选；因该篇尚无DeepSeek精译，尝试状态为partial，没有把它冒充完全发布，也没有清空旧日报。最终仅对这篇必要正式精选生成精译并验收成功，无需全库重审。

本地已执行全部Python（含原report_site）160项及Node49项，均通过；云端此前执行maritime子集158项及Node49项。尚未核验来源/实体手机私人localStorage不会被写成真实手机操作成功。手机UA HTTPS已核对公开页面与JSON200，后续最终发布证据另补。

## 修改文件范围

- services/relevance_scope.py、domain_exclusion.py、abstract_quality.py：研究对象/贡献证据审查、A-D方向与场景。
- services/semantic_evaluation.py、config/maritime/semantic.json：主要领域、问题、任务、贡献和验证场景分离、兼容缓存、新输出校验。
- services/maritime_v2.py、maritime_update.py：范围标签、派生缓存兼容、精确日期/已核验通讯作者保护、核心缺摘要论文有限补全。
- config/maritime/venues.json、discovery.json：Information Fusion证据与ISSN、海事召回组合。
- clients/scholarly_client.py：只读取显式通讯作者标记。
- services/author_display.py、maritime.py、mobile_digest.py，docs/maritime_authors.js、maritime.js、maritime.html、maritime_daily_reading.js：统一作者简显和安全历史修正阅读入口。
- tests/test_maritime_v3_8_8.py、authors.test.cjs及必要的旧版本加载/交互测试：正反例、真实候选池、作者和阅读状态回归。
- 主库、公开派生JSON、历史日报HTML/Markdown与修正清单：按既有构建器重建，不发布private备份、API密钥或浏览器私人数据。

## 明确保留的限制

1. AIS-Vision仍缺可合法使用且身份核对通过的英文摘要，因此“真实通过AI并进入下一轮候选”未完全达成；不能把测试摘要或出版社受限页面当作验收成功。它没有被删除，来源/日期/期刊资格已核实，并会被有限摘要补全优先处理。
2. 研究范围规则是保守启发式与模型结构化判断的组合，不能保证未知表述永不误判；不能准确测量真实创新性。旧边界缓存保留供审查，没有为了更新字段付费重评千篇论文。
3. 只有可信机构公开JIF证据，CAS2025不补猜；机构2026发布表未列学科，其journal_overall记录与2024分学科记录分别保留。
4. 实体手机私人localStorage无法远程读取；采用现有真实JS交互回归及公开HTTPS/手机UA检查，未声称在用户实体手机操作收藏。

两篇负例的原始身份时间补充：2609.30891，DOI 10.48550/arxiv.2609.30891，发布日期2026-09-25，首次入库2026-10-14T03:23:01Z，最近见于2026-10-19T06:08:44Z；2609.16336无DOI，发布日期2026-09-14，首次入库2026-10-13T11:10:33Z，最近见于2026-10-13T12:44:59Z。二者均是preprint、publication_status=unknown，未假称顶会录用。它们拥有有效原AI缓存且原始方法引文/decision均保留；范围排除不需要再次付费。

## 最终交付证据

最终代码提交 **dc47cbbbe2d84436bfd38feeff4cd094303b570b**。

[最终云端42020045554](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/42020045554) completed/success，实际head dc47cbb，云端Python158项与Node49项通过，运行环境无Argos/PyTorch/Stanza。实际执行的是恢复/补选链路，未重新检索全部来源。新增AI审核0、缓存1250；必要精译1篇（MARS and ETMS）、缓存4篇，929 tokens，计价0.002045元，上界0.00409元；五篇均有有效AI、完整中文及两句导读。数据提交 **82dabf984fc23fbecaff1b0a988ff6ae1ebb245b** 已安全快进拉回，无冲突、无force push。

本轮合计仅2次必要付费请求：首次审核1篇2480 tokens+正式替补精译1篇929 tokens，共 **3409 tokens，按响应时段计价0.00563312元**（峰值口径上界0.01126624元）。中间完整重复运行审核/翻译新增调用均为0，未重复付费翻译旧精选或重审千篇库。审核与精译预算仍分别控制，不把本机预算说成账户全局预算。

最终2026-11-05正式五篇：

|ID|论文|
|---|---|
|doi:10.1109/tits.2026.3727609|MARS and ETMS: A Large-Scale Dataset and Ship-Size Sensitive Detection Method in Maritime Applications|
|2609.16919|NeuroSymbEAD: A Large Scale Neuro-Symbolic Caption Dataset for Omni-Directional Embodied Autonomous Driving|
|2609.25945|Towards Systematic Qualification of Vision-Language Models for Automotive Perception Systems|
|2610.10090|Temporal Residual Bottleneck for Robust Asynchronous Collaborative Perception|
|2609.17242|Trajectory CPHD Filtering for Multiple Turning Vehicles With Decoupled Orientation and Axial-Scale Estimation|

当前TACTIC被新合格船舶检测论文替补，另外四个身份保留；原TACTIC元数据、旧精译、旧归档Git版本及本地私有JSON备份均保留，原历史推送身份不会回收进后备。对用户原快照只按修正清单移除不适合条目，未更改完成日期或收藏笔记；新正式批次仍由既有用户阅读完成逻辑决定何时切换。

[Pages42020534060](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/42020534060) completed/success，对应数据提交82dabf9。手机UA HTTPS读取每日HTML、完整库HTML、桌面JS、共享作者JS、阅读快照JS、latest.json、11月5日归档、content-corrections、reading-index、完整库JSON共10项，全部HTTP200，按换行规范化后的文本与本地正式产物全部一致（Windows工作树CRLF与Pages LF不当作内容差异）。线上五篇中文全部存在，5个Prompt按钮、5个作者行，作者模块加载成功；四条明确负例2609.30891、2609.16336、LiDAR-SHIELD、TACTIC在公开库均为domain_excluded。AIS-Vision线上quality.high_journal=True、日期2026-10-28，但摘要仍缺失，未冒充AI审核成功。

证据：忽略目录final-online-proof.json、pages-proof.json、三轮cloud-state及各轮cloud-logs、final-audit.json、python-all.log、node.log。线上读取不是实体手机私人存储实测，不混淆二者。

最终全部本地Python **160项**、Node **49项**通过；最后一次完整测试针对云端最终产物执行。所有4214个论文身份保留。最终有效AI缓存1400（原1399+本轮必要新审核1），没有批量失效旧缓存。

入口：[手机/电脑每日精选](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html?v=3.8.8.1)；[完整论文库](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime.html?v=3.8.8)。原每日自动任务继续运行，无需用户执行命令。

最终真实候选池审计：{"candidate_count": 1253, "ai_reviewed": 893, "ai_states": {"evaluated": 893, "uncertain": 357, "unassessed": 3}, "stage_counts": {"1": 38, "2": 1165, "0": 11, "3": 39}, "ai_rejected": 885, "translation_deferred": 1, "qualified_count": 7, "selected_count": 5, "shortfall": 0}；可用未推送后备3篇；相比基线新增明确范围排除17条，主库不删除。最终正式五篇并非把未审核论文凑进去。
