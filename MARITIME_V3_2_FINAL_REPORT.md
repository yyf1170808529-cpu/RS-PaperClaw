# RS-PaperClaw V3.2 修复与实测报告

日期：2026-10-13。基于本地 V3.1 继续小范围修改，未改变分类、60%/30%/10%比例、期刊标准或CCF规则。没有新增付费API、数据库、推荐模型或浏览器爬虫；本轮没有推送或发布到GitHub。

## 1. 实测结果

V3.1报告的2526条/160篇译文不是本轮起点：用户之后执行过更新。本轮开始与结束的主库均为 **3082条**。

|指标|本轮开始|本轮结束|变化|
|---|---:|---:|---:|
|有英文摘要|2181（70.77%）|2183（70.83%）|+2|
|缺英文摘要|901|899|-2|
|成功中文机器译文|165（5.35%）|193（6.26%）|+28|
|本轮确认可合并的历史重复|—|0|合并0|
|疑似重复组|4|4|保留，等待确认|

覆盖率分母为全库3082，包括历史非论文资源；不是精选论文覆盖率。原165篇成功译文及原有英文摘要没有被覆盖，论文身份、已有阅读和分析内容保留。浏览器localStorage未被清理。

## 2. 实际磁盘占用

用Windows `GetFileInformationByHandleEx(FILE_STANDARD_INFO).AllocationSize`逐文件测量。下表是修复及真实批次之后的快照，单位MiB（1,048,576字节）；实际分配包含文件块开销，不含NTFS目录/MFT开销。

|部分及路径|文件数|文件内容大小|硬盘实际分配|
|---|---:|---:|---:|
|主库 `papers/maritime/library.json`|1|23.149|23.152|
|网页JSON `docs/maritime-data/library.json`|1|23.316|23.316|
|日报：`daily_reports/maritime`及网页报告副本|338|2.006|2.417|
|HTTP缓存 `papers/maritime/private/metadata-cache`|118|62.561|62.770|
|日志：`papers/maritime/logs`及根目录日志|43|0.243|0.330|
|翻译运行环境 `.venv-maritime`（包括Python与依赖）|29727|958.169|1013.866|
|翻译模型及其本地配置缓存 `private/translation`|12|150.576|150.591|
|私有PDF目录 `private/reading`（包括manifest等）|4|6.357|6.364|
|历史备份 `papers/maritime/backups`|1|0.646|0.648|
|私有审计材料：V3/V3.1/V3.2及分区证据|33|37.789|37.839|

最大占用是翻译运行环境，约0.99GiB；不是论文PDF。正常无API `fetch/update/enrich/translate-history`只处理元数据、摘要及缓存，不批量下载PDF。明确执行既有 `prepare-pdf` 才下载单篇私有PDF；原遥感模式不在本次结论范围内。已有PDF内容哈希与manifest一致。

未删除任何文件。现有缓存和日志可以用于复核，空间不构成紧急问题，暂不清理。测量脚本和前后原始字节数留在被Git忽略的 `papers/maritime/private/v3_2/measure_disk.py`、`disk-before.json`、`disk-after.json`；日志继续增长会使后续数字略有变化。

## 3. 中文翻译与续跑

- 日常更新的顺序：新入选且进入重点推荐 → 其他重点推荐 → 其他新增 → 按相关性及高水平证据排序的历史记录。
- 新增独立 `translate-history` 入口和 `补齐中文摘要.cmd`。默认历史每批25篇/180秒；日常默认5篇/180秒。配置保存在 `skills/rs-paper-pipeline/scripts/config/maritime/translation.json`。
- 支持 `--translation-limit`、`--translation-timeout`、`--batches`。逐篇保存，下一次从尚未成功的记录继续，不需要单独的数据库或队列。
- 已成功译文复用原有摘要哈希缓存；人工译文优先；缺英文摘要不调用模型。历史失败默认跳过，加 `--retry-failed` 可重试，原失败原因保留。
- 继续使用原有独立进程和时间预算，检索与归档先保存，翻译超时/失败不回滚论文库。

本机CPU离线模型实测：第一批25篇全部成功（21:30:47—21:31:13，北京时间），第二批续跑3篇全部成功（21:37:57—21:38:03）。**165→190→193**，新增失败0；旧失败3条仍保留原因。第一批跳过161篇可复用译文，第二批跳过186篇；与全库成功数的差异是非入选历史资源没有进入该翻译队列。

真实新译文包括 `2610.07928`、`2610.06226`、`2609.38968`、`doi:10.3390/a19100850` 等28条；全部ID在私有 `final-audit.json`，没有使用测试论文填充真实结果。

最简单操作：**双击项目里的 `补齐中文摘要.cmd`，等显示Finished后关闭窗口；下次双击会继续。** 大批次由用户自行运行：

```powershell
cd D:\desktop\code\paper\RS-PaperClaw
.\.venv-maritime\Scripts\python.exe skills/rs-paper-pipeline/scripts/cli.py maritime --action translate-history --translation-limit 25 --batches 3 --translation-timeout 180
```

## 4. 增量去重审计

普通arXiv入口原先独立处理，现在调用既有 `maritime_v2.merge_records`；Crossref、OpenAlex的入库路径继续调用同一函数。没有重新设计匹配算法。DOI、arXiv ID及别名持续更新；存在明确正式发表证据时保留正式来源、日期和期刊信息，并关联原预印本。较新arXiv版本不会把正式元数据降级。

对3082条真实历史库执行既有安全去重：本轮新确认重复 **0组**、实际合并 **0组**，疑似 **4组/8条**。V3.1曾合并的3组不重新计入本轮成果。

保留的疑似组：

1. Zenodo `23267832` / `23268955`。
2. DOI `10.1080/21622671.2026.2684486` / Figshare `32835575`。
3. Research Square `10.21203/rs.3.rs-10724957/v1` / `10.1186/s42779-026-00333-6`。
4. OpenAlex `W7213692908` / DOI `10.14712/9788024662206`。

未凭相似标题强制合并。回归测试验证三种来源入库均走统一逻辑、预印本升级、不同正式DOI保护、重复审计幂等、阅读记录及人工译文保留、冲突内容归档。当前库原内容对比检查通过。

## 5. 英文摘要缺失与10条真实补全尝试

本轮开始缺失901条：来源Crossref812、Crossref+OpenAlex4、OpenAlex85；类型正式期刊829、正式会议1、预印本67、未知3、其他1。主要原因是已入库来源元数据没有返回摘要；不能把缺失说成论文没有摘要。

完善既有 `enrich` 顺序：本地其他版本及元数据缓存 → 已关联arXiv → Crossref → OpenAlex → 正式论文官方出版社页面。每次记录DOI、原缺失原因、尝试来源和最终来源；成功补全加入待翻译队列。禁止模型生成摘要。

下列10条原缺失原因均为“既有来源元数据没有摘要”；本地版本与缓存先检查，未找到可用摘要。网络尝试及结果如下：

|DOI|实际尝试|结果 / 最终摘要来源|
|---|---|---|
|10.1007/978-3-032-39382-1_4|关联arXiv `2609.31658`|成功，arXiv官方摘要，1293字符|
|10.1007/978-3-032-38407-2_6|关联arXiv `2606.01737`|成功，arXiv官方摘要，1508字符|
|10.1007/978-3-031-20047-2_1（ByteTrack）|Crossref、OpenAlex、Springer|未补全：Crossref无摘要；OA额度耗尽；Springer程序访问返回Client Challenge|
|10.1007/s11804-026-00926-2|Crossref、OpenAlex、Springer|未补全：Crossref无摘要；OA暂停；Springer返回Client Challenge|
|10.1016/j.oceaneng.2026.126889|Crossref、OpenAlex、Elsevier官方DOI落地页|未补全：Crossref无摘要；OA暂停；Elsevier重定向壳无可核对摘要|
|10.1016/j.oceaneng.2026.127514|同上|未补全，原因同上|
|10.1016/j.oceaneng.2026.127860|同上|未补全，原因同上|
|10.1016/j.oceaneng.2026.126652|同上|未补全，原因同上|
|10.1016/j.oceaneng.2026.127393|同上|未补全，原因同上|
|10.1109/tits.2025.3621477|Crossref、OpenAlex、IEEE官方页|未补全：Crossref无摘要；OA暂停；返回页面没有可核对的DOI/标题/摘要组合|

出版社真实成功补全 **0条**，不是8条成功。Springer [ByteTrack公开摘要页](https://link.springer.com/chapter/10.1007/978-3-031-20047-2_1)和[船舶检测公开摘要页](https://link.springer.com/article/10.1007/s11804-026-00926-2)能通过网页检索看到摘要，但本机程序通过DOI访问收到浏览器校验；两种访问结果明确区分。未尝试绕过校验或付费墙。

出版社适配仅获取一次官方HTML，不扩大抓取范围，不下载PDF；严格核对DOI与完整标题，只接受明确摘要字段/区块，拒绝一般description、推荐阅读和错论文。未经核实公开转载许可的出版社摘要只进入私有缓存，不进入网页、日报、公开主库或机器翻译队列；明确CC BY/CC0时附许可链接。

官方接口研究结论：Springer [Metadata API](https://dev.springernature.com/docs/api-endpoints/metadata-api/)需要相应注册配置；[Elsevier API](https://www.elsevier.support/sciencedirect/answer/sciencedirect-apis)与[IEEE许可](https://ieeexplore.ieee.org/Xplorehelp/downloads/license-information/IEEE.html)存在访问/使用条件。公开可读不等于可以公开转载全文摘要，本轮未申请或假装拥有这些权限。

## 6. OpenAlex与最近检索失败原因

真实补全首个OA请求返回HTTP429，响应明确为 **无API Key、共享IP免费日预算耗尽、剩余0、UTC午夜重置**。后续7条OA补全在本地暂停，没有继续发送请求或无限重试。本机环境变量及用户环境变量中未检测到有效Key；未输出任何密钥。

支持可选免费 `OPENALEX_API_KEY`，以Authorization Bearer头发送，不把Key写入URL、缓存或日志。预算耗尽暂停至服务端重置时间/UTC午夜；普通429尊重Retry-After；暂停按密钥身份区分，已有缓存仍可用。参见[OpenAlex官方认证](https://help.openalex.org/api/authentication/)及[错误处理](https://help.openalex.org/api/errors/)。它不是付费LLM API。

最近一次完整检索不是本轮启动的：2026-10-13 20:40—20:52，共42任务、40成功、1失败、1截断，新增556条。

- 失败：OA陆上任务返回空标题，触发 `normalize() argument 2 must be str, not None`。本轮已修复空标题/作者处理并加入回归测试；不能声称该任务已重新在线成功，因为没有重跑完整检索。
- 截断：OA通用任务候选达到500条上限，标记incomplete，已得到的数据保存；没有把截断伪装成完整。
- 本轮补全另遇OA预算429，与上述旧检索失败不是同一问题。

最简单设置免费Key：打开 `https://openalex.org/settings/api` 获取Key，在Windows“编辑账户的环境变量”中新建用户变量 `OPENALEX_API_KEY`，值填Key；不用发送到聊天。代码也可读取用户环境变量，新的终端会直接继承该设置。

## 7. 网页状态

顶部按最后一次检索结果显示成功、部分完成或失败；全部成功且新增0时补充“本次没有新论文”。限流及截断计入非完整状态，详情按来源汇总，默认折叠，不逐项罗列几十个期刊成功信息。

使用现有本地预览服务实际打开页面，显示：

> 最近更新部分完成，部分来源未成功，其余数据已保存

“查看更新详情”默认关闭。展开后只显示Crossref、OpenAlex、arXiv三组汇总；当前示例统计仍为 **水路1篇 · 陆上6篇 · 通用方法4篇**，来自当前筛选结果，没有改配额。没有停止用户已有预览服务。

## 8. 修改文件与验证

本轮直接涉及：

- `skills/rs-paper-pipeline/scripts/services/maritime.py`：统一arXiv去重、历史翻译CLI、配置、公开更新摘要。
- `services/maritime_v2.py`：沿用去重，保留较新预印本、修复空元数据。
- `services/maritime_reading.py`、`services/maritime_update.py`：历史分批与优先队列、缓存/失败重试、预算。
- `services/maritime_metadata.py`：完善已有enrich顺序和逐条证据。
- `clients/scholarly_client.py`：可选免费Key、429暂停、空标题修复。
- 新增 `clients/publisher_abstract.py`、`config/maritime/translation.json`。
- `docs/maritime.js`、`docs/maritime.html`：简短状态及折叠详情。
- 新增 `tests/test_maritime_v3_2.py`；扩展 `tests/maritime.test.cjs`。
- 新增 `补齐中文摘要.cmd`；更新 `README.md`、`简明操作指南.md`、本报告。
- 真实批次更新主库、网页JSON及相应日期日报；私有证据和日志不公开发布。

仓库存在此前V3/V3.1未提交变更，本轮保留，没有重置，也不把所有git差异都算成本轮新增。

|验证|实际结果|
|---|---|
|主要Python回归 `python -m unittest discover -s tests`|66通过|
|原技能Python回归|49通过|
|Node前端回归|21通过|
|三来源入库、正式发表升级、不同DOI误合并保护|通过|
|空标题/作者处理、429一次请求后跨调用暂停、Key不泄漏|通过|
|真实历史去重审计、个人内容对比、已有PDF哈希|通过|
|真实10条摘要补全|2成功、8受限或缺元数据，完整留痕|
|真实历史翻译及第二批续跑|25+3成功，新增失败0|
|真实网页顶部与默认折叠状态|通过|

测试日志：根目录 `v32-all-python-tests.log`、`v32-original-tests.log`、`v32-node-tests.log`；真实执行日志 `v32-enrichment-ten.log`、`v32-history-translation.log`、`v32-history-resume.log`。私有逐条证据在 `papers/maritime/private/v3_2/enrichment-ten.json`、`dedup-audit.json`、`final-audit.json`。

中途用翻译venv直接发现全套测试时，第三方同名tests包导致导入冲突；最后用项目原Python运行完整回归66通过。真实离线翻译始终使用已安装模型的venv。

## 9. 剩余限制与下一步

还有899条没有英文摘要；其中很多需要来源提供摘要或允许程序访问，不能承诺靠本地翻译解决。还有2885条未成功翻译（含缺英文、非入选资源等），3条旧失败及1条已标记缺英文；可持续分批补齐适合阅读的历史论文。本轮没有跑全库翻译或完整网络检索长任务。

建议先设置免费OA Key，再正常更新或小批enrich；有英文的历史论文可以立即用补齐入口继续。出版社访问和许可未解决时保留缺失状态，不编造摘要；无必要为此接入付费LLM API。
