# RS-PaperClaw V3.8.9 最终报告

验收日期：2026-11-08（北京时间）。正式日报已从11月5日恢复至**11月8日，恰好5篇**；五篇均通过当前来源、研究范围、有效AI评审、英文摘要哈希、DeepSeek中文摘要及两句导读检查，且此前没有正式推送记录。未降低原有质量门槛。

## 1. 基线、备份与连续停滞原因

本地最初HEAD为a37b0c5，安全快进到云端a36b1f9后开始修改，未reset、force push或覆盖远端数据。已阅读V3.8.7、V3.8.8报告；指定接力文档`RS_PaperClaw_接力文档_20261105.md`在本地未找到，未假称已读。

原始4300篇主库、原11月8日初版和永久推送账本均在忽略目录`papers/maritime/backups/v3_8_9/`备份。最终4675篇，原4300个身份均仍存在或有别名映射，缺失0；原AI缓存、英文、译文和历史pending保留。

已取回并审计42156714677、42366972769、42438884395三个失败运行的日志。11月8日63项任务中60成功、3失败，三个真实错误均为OpenAlex匿名游标分页HTTP401：`API key required for cursor paging`。查询分别为：

- 水路：maritime ship visual detection fusion
- 陆上：autonomous driving object detection sensor fusion
- 通用：cross modal visual representation object detection

日志前部HTTP500/503有一部分来自回归测试的模拟接口，不应当成真实线上来源失败。OpenAlex现改为匿名首屏不传cursor；有免费Key才使用游标。首屏满时保留数据并标记incomplete，不把截断冒充完整检索。已真实匿名查询vessel detection返回3条，complete=False，未混入主库。官方规则核对：[Authentication](https://help.openalex.org/api/authentication/)。

1259条来源候选不是1259条合格推荐：很多已有AI否定、低置信度、范围不合格或已推送。用新规则离线回放11月6/7/8，三天各1257候选、有效已评审889、uncertain364、模型范围排除4，最终仅1条合格。原来“2条可用”还包含两条范围误判。原流程既缺少数量不足后的新检索闭环，又把不足五篇与程序失败混在一起，导致每天保存partial但正式日期停留。

## 2. 两条待发布反例与精译故障

| 记录 | 原始AI证据 | 修复后 |
|---|---|---|
| 2609.24964，Perception-Aware Communication Middleware… | direct=2、transfer=0、confidence=.86、decision=不推荐、transfer_path=null；核心为QoS、UDP分片与重组、调度，YOLOv8n只是验证 | 通信middleware研究对象确定性排除，hard=false、domain_excluded |
| 2610.06121，Radar2Plan…Ego-Trajectory Planning | direct=2、transfer=1、confidence=.8、decision=不推荐、transfer_path=null；核心为自车开环轨迹规划基准、编码器/规划器接口比较 | ego-trajectory planning研究对象确定性排除，hard=false、domain_excluded |

旧直接任务路径被场景词放行，未阻止上述不相关核心贡献；修复的是通用研究对象规则，不是论文ID黑名单，原元数据、原AI及译文均保留。

2611.04034曾有两次已付费精译返回，却因原文`$2.82M$`被准确译成“282万”遭数值/公式检查拒绝。现使用Decimal验证数值严格等价后恢复原文数量形式，重验已有响应即可成功，新增翻译请求0；“281万”等不等值译文仍拒绝，数字/公式校验没有关闭。原失败证据及费用保留。

## 3. 自适应闭环与资源边界

正常流程后统计**真正具有合格AI和完整精译的数量**。已有五篇完整合格缓存时直接使用，不为更高规则分的未翻译论文额外付费；不足时依次复用后备与pending、增量审核已有主库、最多两轮补检。按缺额选任务，水路/陆上/通用轮转，复用OpenAlex、Crossref和原arXiv客户端，不机械重跑63项。

默认每轮最多6个任务、最多16篇增量AI；来源回溯365天、单任务35秒、补检总900秒；整体40分钟工作预算给45分钟Actions留构建同步余量。仍沿用2元AI预算、独立精译预算、不确定扣费保护及当前DeepSeek模型。任务游标、补检历史、待修复精译和pending持久保存，未执行任务会回退游标；下一次从保存位置继续，不每次从零开始。

精译失败继续替补其他有效AI候选，未尝试项目不虚标为已失败。已有成功翻译及AI指纹复用。收到但无法解析的付费AI响应单独保存审计，**不重发同批论文**，继续不同候选；网络失败/余额不足/扣费不确定仍停止新付费请求，费用不会因JSON无效而抹掉。

不足五篇是pending，保存数据、保留上次完整精选及真实日期，正常退出；真实异常仍报错。检索、AI、精译、精选、发布、同步、Pages分别记录。同步/Pages的最终结果在独立同步日志及Actions中记录，构建阶段`not_attempted`不冒充成功。

后备目标仍15篇，永久去重、医学排除、可信来源和通用方法门槛不变。

## 4. 真实补检和云端验收

### 首轮补检：42452360901

代码344ea55，运行成功，数据提交68b2827。恢复模式跳过普通63任务，实际执行1轮6个补检任务：

| 来源/方向 | 查询 | 召回 | 去重新增 | 结果 |
|---|---|---:|---:|---|
| OpenAlex水路 | vessel instance segmentation AIS vision | 100 | 91 | 首屏截断，已保存 |
| OpenAlex陆上 | camera lidar radar object detection fusion | 100 | 91 | 首屏截断，已保存 |
| OpenAlex通用 | visual hard negative contrastive learning | 100 | 99 | 首屏截断，已保存 |
| Crossref/Ocean Engineering | vessel instance segmentation AIS vision | 100 | 94 | 截断，已保存 |
| arXiv陆上 | camera lidar radar object detection fusion | — | 0 | 触及1页扫描上限 |
| arXiv通用 | visual hard negative contrastive learning | — | 0 | 触及1页扫描上限 |

总召回400，去重新增375；当时旧门槛方向合格66，真实AI新增成功16篇、AI合格5篇，复用1篇精译+4篇新精译，就绪1→5，耗时329.81秒。达到五篇后未执行第二轮，避免无用请求。两轮仍不足等场景由回归矩阵验证，没有把模拟第二轮声称为真实线上检索。

arXiv首轮扫描上限异常原来丢掉首屏。现异常携带partial_results，只有补检明确接收时保留首屏并标记incomplete；普通严格分页行为及真正API错误行为不变。该分支有回归覆盖，首轮失败没有改写成成功。

**终检发现首轮五篇存在继承的来源漏洞，不能作为最终合规结果**：

- ICMLT全称被“International Conference on Machine Learning”前缀误匹配为ICML。Crossref正式元数据实际为2026 11th International Conference on Machine Learning Technologies。已修正长会议名边界，ICMLT不再CCF A，真正ICML仍通过。
- CalibFusion明确water-surface、有效AI领域为maritime_fusion，却因旧场景字典落入通用组，绕过水路正式期刊要求。补足water-surface场景及有效AI海事领域的来源组判定，水路预印本不再绕过门槛。

两条原记录和已付费翻译保留，原初版及推送账本已备份，正式内容修正表使用真实替补快照。完成阅读的私人批次不重写；未完成批次只安全替换不合格项，不改完成标记、日期、英文、收藏或笔记。

### 后续两次真实恢复

| 运行ID | 代码 | 成功AI新评审 | AI tokens（包括付费无效输出） | AI时段计价/元 | 新精译/元 | 结果 |
|---|---|---:|---:|---:|---:|---|
| 42452360901 | 344ea55 | 16 | 27062 | .04774168 | 4篇/.008731 | 首轮达到5，随后来源终检发现2条需替补 |
| 42453895648 | 4264b2b050bb073e4e6dc6b99818ad60acdcebf3 | 4 | 14378 | .02566584 | 2篇/.004515 | 形成合规5篇；另有付费JSON错误促成本轮修复 |
| 42455564908 | 7f22679e9f28f941967c89a982fe3db0129555ca | 37 | 67921 | .11552912 | 0篇/0 | 已付费无效批次不重发，继续不同候选；合规5篇及Pages成功 |

三次任务均真实完成success，非模拟。最后一次AI状态partial：37篇成功、6篇结构/证据校验失败（4篇JSON无效、2篇证据非摘要逐字引句），失败未当合格。最终AI状态 evaluated910、uncertain389、domain_excluded11、unassessed10。译文全部缓存5篇，无新增翻译请求。

本轮成功AI新评审57篇，AI请求usage合计109361 tokens；新精译6篇5776 tokens。含无效JSON付费输出、含两条后来来源排除论文的精译，合计**0.20218264元**，对应保守费用上限0.40436528元；扣费不确定新增预留0。费用取真实响应usage及请求时段计价，不冒充账户账单差额。2611.04034此前费用不重复记作本轮新请求。没有全库重评或全库翻译。

最终新增375条中，按修复后的规则重新统计：来源合格71、研究方向合格63、具有有效AI且通过硬条件8。两种计数分开，不能把71来源合格称作71可推荐。

## 5. 最终正式五篇与后备状态

正式精选日期2026-11-08，全部此前未正式推送，5篇全部来源/AI合格、当前英文哈希匹配、中文摘要和两句导读有效：

| ID | 标题（缩写展示） | 来源 |
|---|---|---|
| 2504.09197 | Graph Learning-Driven Multi-Vessel Association: Fusing Multimodal Data for Maritime Intelligence | IEEE T-ITS，已核验JCR一区正式期刊 |
| 2604.24044 | CLLAP: Contrastive Learning-based LiDAR-Augmented Pretraining for Enhanced Radar-Camera Fusion | arXiv预印本 |
| doi:10.1609/aaai.v40i12.37916 | Towards Accurate 3D Object Detection in Adverse Weather by Leveraging 4D Radar for LiDAR Geometry Enhancement | AAAI 2026，CCF A正式会议 |
| 2606.09634 | ATN3D: Density-Aware LiDAR-Radar Early 3D Object Detection Under Extreme Sparsity | arXiv预印本 |
| 2611.04034 | Do Pretrained Backbones Transfer to Physical Sensors? A Systematic Study of Multimodal Initialization Across the Sensor Stack | arXiv预印本 |

原ICMLT和CalibFusion两条分别由CLLAP和ATN3D替补；通信middleware和Radar2Plan均未入正式五篇。原论文发表日期继续显示，没有把历史论文说成今日发表。

正式发布后后备可用数**5篇**（当前AI及来源条件有效，尚未推送），还未达到15篇维护目标。不会以此降低门槛；下次定时任务继续补审和必要的补检。已发布身份不会回收凑数。

11月6—8日pending与修复记录保留；最新11月8日正式归档/reading-index有效。恢复运行复用375篇及有效缓存，无重复入库、未重复翻译当天五篇。原私人浏览器存储从未读取、清空或上传。

## 6. 修改文件与验证

- 新增`services/adaptive_discovery.py`：complete_count、jobs_for、recover、来源与研究范围分开计数。
- 新增`config/maritime/supplement.json`：查询、来源、窗口、轮数、预算边界。
- `services/maritime_update.py`：接入补检、各阶段准确汇总、时间余量、pending正常退出。
- `clients/scholarly_client.py`：匿名OpenAlex首屏；`clients/arxiv_client.py`：扫描上限携带部分结果。
- `services/relevance_scope.py`、`abstract_quality.py`、`maritime_v2.py`：研究对象、场景、会议边界。
- `services/mobile_digest.py`：最终门槛、完整缓存优先、归档HTML刷新、来源日期。
- `services/reading_translation.py`、`selected_translation.py`：等值数量重验缓存、有限时间和失败替补准确记录。
- `services/semantic_evaluation.py`：无效已付费响应审计、不同候选继续；`maritime_sync.py`：最终状态字段。
- `.github/workflows/maritime-no-api.yml`：保存无效响应审计日志；原定时、单一写入、安全白名单不变。
- `docs/maritime.js`、`maritime.html`、`maritime_daily_reading.js`及生成HTML：正式日期/补检进度、独立私人批次日期、缓存版本。轮询状态覆盖更新，避免每分钟重复追加；已读历史不改写，未读更正保留笔记。
- `tests/test_maritime_v3_8_9.py`及既有Python/Node相关测试：新增场景与兼容断言。

最终本地**168项Python、50项Node全部通过**，git diff --check通过。真实云端7f22679版本Python165项（云端仅运行test_maritime*.py）、Node50项通过；本地test_maritime*.py为166项，另加通用报告站点2项，共168项，末次完整缓存优先新增测试已包含其中。覆盖5直接发布、4补1、2补3、2补后仍4/0、时间游标与pending、部分来源、翻译替补、永久去重、无效付费JSON继续、OpenAlex匿名、ICMLT反例/ICML正例、两篇范围反例、reading-index、收藏/笔记/Prompt/JSON导出及跨日未读恢复。

真实云端完成检索/恢复、AI、精译、归档、Git同步及Pages；Node DOM交互测试覆盖私人状态，但不能代替用户实体手机私人localStorage实测，未作此声称。

## 7. 部署证据与限制

- 云端更新：[42455564908](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/42455564908)，success。
- 对应数据commit：ae3baf0d863b6194b957d99c22a35f2ea2e317f7，已安全快进合并。
- 数据版本Pages：[42456131286](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/42456131286)，success。
- 正式手机入口：[每日精选](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html)；[完整库](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime.html)。

最终代码提交：`45dd4c6b0d0227e6b347b97557e031b70f35f6ba`。最终[Pages运行42456803245](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/42456803245)已success，实际部署的head与该代码提交一致。后续本报告单独提交不改变静态站点。

使用iPhone Safari User-Agent真实HTTPS核验9个文件：每日HTML、完整库HTML、桌面JS、手机版JS、latest.json、11月8日归档JSON、supplement-status、content-corrections、reading-index全部HTTP200；换行规范化后9/9与本地内容完全一致。公开JSON日期2026-11-08，5篇/5份中文；HTML内5个Prompt按钮，脚本版本3.8.9.2。证据public-proof.json，逐文件SHA256已保存。

这不是仅看Actions绿色：已同时核验公开HTML和JSON。最终补充的完整缓存优先与状态刷新细节由本地全回归验证；完整真实云端更新运行在7f22679，最终静态版本45dd4c6由Pages部署和公开文件一致性验证。未另外触发第四次付费更新来重复评价同批论文。

仍存在的限制：匿名OpenAlex不支持深分页；本轮补检有明确截断且保留标记。arXiv部分结果恢复分支已修复和回归，本轮未再次付费/联网重跑同一批检索来制造成功记录。模型仍会产生无效JSON或非逐字证据，均不算合格；不为每条失败无限重试。后备尚5/15，未来仍可能因质量与预算而保存pending；已实现继续补检和恢复，不能保证外部服务每天必然产出五篇。未读取用户手机私人状态，无法证明其实体手机网络是否通畅。

审计JSON、原始日志、回放及备份均位于忽略目录`papers/maritime/backups/v3_8_9/`，没有把私人PDF、Key、原始错误日志或浏览器笔记加入公开提交。
