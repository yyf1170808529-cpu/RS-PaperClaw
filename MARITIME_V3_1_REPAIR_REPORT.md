# RS-PaperClaw V3.1 修复报告

日期：2026-10-13（北京时间）。依据本地最新工作区实施；未用远端覆盖本地修改，未新增论文来源或更改推荐比例。

## 1. CmIVTP 端到端结果

| 原问题 | 实际根因 | 本轮结果 |
|---|---|---|
| 两条重复记录 | Crossref DOI记录与OpenAlex arXiv记录没有共享ID；原去重仅识别显式ID | 完整规范标题一致、5位作者一致，合并为主ID `2605.26524`；旧DOI ID建立别名 |
| 期刊版缺英文摘要 | Crossref未提供摘要，虽然arXiv对应的OpenAlex记录已保存全文摘要，却没有跨来源补全 | 保留1886字符真实英文摘要，保存来源；未根据标题生成摘要 |
| 中文缺失 | CmIVTP未触发翻译；过去若用基础Python会缺Argos，分句器默认还会联网刷新资源 | 正确虚拟环境和本地模型实际翻译成功；机器译文已写入库及网页 |
| T-ITS待核验 | 期刊级配置没有可信JCR记录 | 写入高校明确标注的2025 JCR-JIF Q1记录；CAS2025官方大类仍待核验 |
| IF暂无 | 同上，期刊级IF配置缺失 | IEEE学会官网明确9.1（2025），全部同刊论文统一复用 |
| 信息复杂／缺链接 | 源标签和PDF原文按钮未分别暴露正式DOI与arXiv | 一行显示期刊＋JCR一区＋IF9.1；三个来源链接分别可用 |

实际浏览器已验证：搜索CmIVTP只显示1条，作者及The Hong Kong Polytechnic University单位保留；展开详情同时显示真实中英文摘要；复制Prompt含正确arXiv PDF。当前近期精选也能显示它。

来源证据：

- [IEEE ITS Society官网](https://ieee-itss.org/pub/t-its/)：明确 `T-ITS Impact Factor: 9.1 (2025)`。
- [Comillas大学研究机构期刊表](https://www.iit.comillas.edu/publicacion/info_revista/en/204/ieee-transactions-on-intelligent-transportation-systems)：独立JCR-JIF列列出2025、9.100、Q1，旁边SJR列未被用于本次判断。该页未提供分学科明细，因此后台明确标注为期刊层面的JIF分区汇总，不编造学科。
- [真实arXiv摘要](https://arxiv.org/abs/2605.26524)：标题、5位作者、AIS/CCTV方法和英文摘要与对应库记录一致。
- 正式 DOI：`10.1109/TITS.2026.3703388`；真实Crossref原始记录及作者单位在元数据历史中保留。正式发表日期只有2026-10，未伪造某一天。月精度已发表记录仅用保守时间窗判断，不修改原日期字段。

## 2. 真实去重和历史保护

修复开始共2511条；实际合并3组，去重后2508条。之后受控T-ITS更新新增18条，最终2526条。

实际合并样本：

1. CmIVTP：`10.1109/TITS.2026.3703388` ↔ `2605.26524`，正式期刊优先。
2. Bridging the Gap Between Image Restoration and Navigational Safety in Hazy Conditions: A New Visibility Estimation Metric for Maritime Surveillance：`10.1016/j.oceaneng.2026.126774` ↔ `2606.30049`，正式期刊优先。
3. Trajectory-Aware Adaptive Inference in Object Detection Models：Zenodo副本 `10.5281/zenodo.20537264` ↔ `2605.16397`；arXiv记录已具有MDM正式DOI `10.1109/mdm71479.2026.00073`，保留正式会议发表信息。这是会议案例，不冒充第三组期刊案例。

目前真实期刊/arXiv重复组仅2组，全部跨来源实际重复组3组，**没有凑出5组在线验收样本**。另4组完整标题重复保留待确认，包括数据集版本、Figshare副本、非arXiv预印本及来源身份不充分的记录；没有按标题局部相似强行合并。

判据为显式DOI/arXiv，或完整规范标题一致且作者集合至少80%一致、第一作者一致，并有预印本与正式发表关联。两个不同正式DOI不只凭标题合并。保留正式元数据、最完整非空摘要、PDF、所有元数据来源和历史快照；原ID别名及原日期候选成员关系保留。人工分析冲突归档并可在网页查看，旧ID浏览器备份可恢复。

核对最初2511条原身份均可解析到现记录；原有阅读记录、155条成功翻译缓存和人工修订均未丢失。三个旧失败翻译记录只补上错误分类，不覆盖英文。备份与冲突、原ID迁移另有自动化测试，不声称已替用户验证其所有真实浏览器笔记。

## 3. 英文摘要数量

| 阶段 | 缺失英文摘要 |
|---|---:|
| 修复开始 | 848 |
| 两条缺摘要的正式记录与已有摘要版本合并后 | 846 |
| 现有来源缓存实际补齐1条后 | 845 |
| 后续新增18条Crossref无摘要记录后 | 863 |

CmIVTP及另一期刊主记录通过合并补齐；另1条历史记录通过已有真实源缓存补齐。额外实际尝试3条Ocean Engineering DOI：Crossref未提供摘要，OpenAlex都返回429共享匿名额度耗尽，未补写、未删论文。本机检查未读到OPENALEX_API_KEY，不能声称OpenAlex补全在线成功。

新增 `maritime --action enrich --limit 5 --timeout 15 --retries 1`，只处理缺摘要记录，可用 `--id` 针对某篇。优先已有摘要与真实缓存，再尝试已有Crossref/OpenAlex、关联arXiv单篇元数据；空字符串和较短内容不会覆盖更完整摘要。日常更新的摘要补全先用已有批次和缓存，避免每次对历史全库联网；主动补全命令可联网。

## 4. 真实中文翻译

环境 `.venv-maritime` 存在，Argos 1.11.0实际可导入，`translate-en_zh-1_9`模型已安装，全部使用CPU。

本轮5篇新译文实际生成时间为北京时间20:14:44—20:14:50（不含解释器加载），已归档；真实浏览器逐篇确认英文和中文均能展开：

- CmIVTP（`2605.26524`）。
- Semantic-Guided Diffusion for UAV Maritime Target Detection（`10.32894/kujss.2026.172069.1330`）。
- PhysFusion（`10.1109/jsen.2026.3697429`）。
- A Scene-Aware Degradation Universal Re-Identification Framework for Adverse Weather（`10.3390/s26102951`）。
- Weak Calibration Cross-Fusion Framework for Multi-Modal 3D Object Detection on Unmanned Surface Vehicles（`10.3390/jmse14090867`）。

真实首次尝试停在第一篇。发现Argos分句器默认刷新Stanza远程资源；改为明确加载已安装的本地分句模型并禁用下载，离线重试成功。实际初次译文还出现Transformer译成“变压器”、fusion译成“聚变”、代码URL断开等问题；补齐通用术语、数值、公式、模型名与完整URL保护后，在入库前重验5篇。没有用手写中文代替机器执行，也没有放弃术语完整性检查。

最终全库：机器翻译160条、失败3条、缺英文状态1条、未尝试2362条。失败3条原错误均为缺Argos（之前基础Python运行），现在保留 `dependency_missing` 分类；它们不是本轮5篇模型失败。缺英文状态只统计已尝试翻译的记录，不等于全部863条空摘要。

已成功的旧版本4缓存继续复用，新译文使用保护版本5，不为术语配置改动强制重翻全库；5篇再次调用实际缓存命中，无模型执行。人工译文优先。翻译失败明确分类并保留英文；日常更新每次默认最多5篇、阶段上限180秒，剩余待处理，避免长时间阻塞。机器译文仍有断句、语序和少量英语残留，不能当成人工学术翻译；英文是核查依据。

## 5. 期刊指标实际覆盖

19本原候选期刊不变。已核验实际IF共6本：T-ITS 9.1、TIM 7.0、Information Fusion 15.5、Knowledge-Based Systems 7.6、IEEE TIP 13.7、Pattern Recognition 7.6；来源与核验日期保存在期刊配置。没有提供确切指标年份的来源仍保存year=null，不猜年份。

已核验JCR-JIF Q1覆盖2本（T-ITS、TIM）；CAS2025官方大类核验覆盖0本。其余有IF但没有分区证据的期刊仍显示待核验，绝不靠IF大小推断Q1。本轮主要补齐T-ITS，未假装完成全部19本分区核验。

ISSN/eISSN优先。没有ISSN时按标准名称或经核验别名完全匹配，不做宽松包含匹配；存在不匹配ISSN时不靠名称强行覆盖。

## 6. 指定旧日志和桌面更新

`update-20261013-194346.log` 实际为0字节。核查时没有论文更新Python进程；唯一其他Python进程是用户另一个radar程序，未触碰。空日志不足以还原当时的来源、重试或结束原因，不能说那次更新成功或仍在运行。

旧启动器把子进程所有输出重定向到文件，窗口只显示开头。现改为实时双写窗口和日志，Python无缓冲，每15秒无新输出时明确提示仍在运行；四阶段分别显示开始、完成、耗时，检索显示任务序号与来源。源任务默认180秒可配置，超时终止对应检索子进程并继续保留已成功批次；翻译独立预算，失败也继续生成网页。窗口等待子进程确实退出后才显示完成时间、退出码和结果，不借用过期summary宣称成功。

防重复锁使用本机文件锁，退出自动释放；双进程实际测试第二次启动返回3且没有启动检索。CMD保留子进程退出码；原只打开网页入口保留，也支持 `--only-open`。

真实桌面同入口测试发现Windows新检索子进程误加载旧Unix入口fcntl；已修复 `cli.py` 的multiprocessing入口隔离。第一次测试明确失败并保留库，修复后受控重跑成功：

```powershell
.\.venv-maritime\Scripts\python.exe -u skills/rs-paper-pipeline/scripts/update_maritime.py --no-open --source crossref --journal tits --query "ship detection" --page-size 100 --max-pages 1 --retries 1 --timeout 15 --task-timeout 30 --limit 0
```

实际日志：`papers/maritime/logs/update-20261013-201617.log`。Crossref1项任务成功，候选33条，新增18条，0项来源失败；北京时间20:18:30明确“更新完成”、退出码0。`--limit 0`仅为该次隔离检索/进度验证禁用额外翻译，五篇真实译文另行完成。**没有把这次单来源成功说成全来源在线验收成功。**

另在忽略提交的空测试目录执行真实1秒总期限测试：对应子进程被终止、返回失败退出码1、仍完成网页阶段；人为设置的1秒期限，不冒充真实接口长期故障。全部成功／部分失败／全失败在有明确模拟标识的自动化测试中分别验证0／2／1。未重新启动完整多来源长检索。

本地更新、GitHub同步、Pages发布分别记录；本轮未推送或发布。Actions的可选翻译安装失败也不会阻止检索步骤。

## 7. 网页、文件与回归

页面实际一行：`IEEE Transactions on Intelligent Transportation Systems · JCR一区 · IF 9.1`。会议为会议名＋CCF等级，没IF；后台年份、学科、来源证据继续保留。顶部近期精选实际为水路1篇、陆上6篇、通用方法4篇，搜索CmIVTP后动态变为1／0／0；全部库模式显示总归档2526条。

主要修改：`services/maritime_v2.py`（匹配与合并）、新增 `services/maritime_metadata.py`（缺摘要补全）、`clients/arxiv_client.py`（复用原客户端的有界单篇元数据）、`services/maritime_reading.py`（离线分句、术语及缓存）、`services/maritime_update.py`（阶段、任务限时）、`update_maritime.py`（实时日志、锁、结束状态）、`cli.py`、`services/maritime.py`、期刊/术语配置、`docs/maritime.js`、CMD、可选翻译Actions处理、README和简明操作指南；同步生成JSON与既有日报。新增 `tests/test_maritime_v3_1.py`，更新相关Python与Node测试。

实际回归：根tests Python **59项通过**，原项目skill Python **49项通过**，Node **20项通过**。真实浏览器验证CmIVTP单条、3个链接、IF同一行、中英双语、Prompt PDF，并逐篇确认另外4篇双语。没有使用Selenium/Playwright项目依赖，没有控制ChatGPT/DeepSeek网页。

详细原始审计、修复前库、5篇机器结果与缓存验证保存在忽略提交的 `papers/maritime/private/v3_1/`；测试日志为仓库根目录 `v31-*.log`。研究兴趣、期刊来源池与后台10/6/4配额未改。

## 8. 仍存在的限制

- OpenAlex匿名额度仍429，本机尚未读到免费Key；863条缺摘要并非都可通过当前来源获取。
- 非arXiv的4组疑似重复需要人工确认；实际期刊/arXiv样本不足5组。
- 除T-ITS/TIM外分区证据覆盖仍不足，CAS官方大类未核验；未推测分区。
- 机器译文只辅助阅读，保护术语后仍可能语序不自然；每次更新有限翻译预算，不能宣称2526条全库都已有中文。
- 有界检索会如实标记截断/失败；本轮只做T-ITS受控在线更新，其他来源完整在线验收尚未完成。
- 临时浏览器验收服务会自行结束；日常请使用原 `start-maritime.cmd` 或桌面“论文更新”。无需付费LLM API。
