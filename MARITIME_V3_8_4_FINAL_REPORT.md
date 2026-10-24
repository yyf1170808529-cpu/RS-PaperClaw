# RS-PaperClaw V3.8.4 完成报告

## 1. 故障证据与修复

已先阅读 V3.8.3 报告，安全 fast-forward 到云端最新 `4f443d2`，没有用旧代码覆盖数据。修复前主库、latest、23/24日 pending、后备池已保存至忽略目录 `papers/maritime/backups/v3_8_4_before/`；没有清理用户浏览器数据。

GitHub API核实自动工作流为 active，23日运行 [39931613956](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39931613956)、24日运行 [40079962312](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/40079962312) 均 completed/failure，实际失败步骤是 `Report incomplete source update`。两天 pending 都为同一五篇、四份中文成功，唯一阻塞为 `2610.00319`。

真实本地 Argos 复现：摘要被保护词拆分后，尾部片段 `respectively. The source code will be made publicly available at` 被译为 `页:1 源代码将在`；加句号重试仍输出 `页:1`。原片段没有数字，模型引入了“1”，因此 numeric_mismatch 正确拦截；不是原论文数值错误，也没有证据表明数字恢复丢失。

在现有 translation_terms.json 加入 `respectively → 分别`，使这类孤立连接词不再交给模型。没有关闭或放宽数字、百分比、URL、公式、缩写或摘要哈希校验。真实重译 EgoRefine 成功，英文摘要哈希仍为 `826a723990d37f620fc31644384314282c3abae5414c8175251dc0c74bdb545e`；其他四篇复用有效缓存。五篇逐一通过 translation_error 和摘要哈希检查。

## 2. 自动替补与恢复发布

translate_selected 现在在同一总时间预算内循环：选择有效AI及来源合格候选 → 有限翻译/重试 → 失败记入 selected_translation_repairs → 同次排除失败身份 → 保留成功项并尝试下一合格候选。失败条目保留日期、原摘要哈希和实际原因，不写入已推送账本。后续日期可重试；相同日期若译文已修复或摘要变化，也重新具备资格。

selected_translation_plan 只稳定当前云端尝试的身份，不涉及个人阅读状态。失败候选不会在一次循环中反复被挑中。build_mobile_digest 重建时执行同一筛选，不会再次把刚失败的论文放回正式日报。最终已发布五篇无错误时，前面被替补的失败记入单独审计，不再错误地导致整批工作流 failure。后备耗尽或预算不足时仍保留最近完整日报。

另外完成了隔离的真实失败替补回放：使用修复前主库、历史账本和旧版术语表（仅移除新加入的respectively映射），真实Argos两次重现2610.00319失败；自动保留四篇并选中2610.04601，真实翻译成功，得到五篇完整批次。共检查6个身份，4个缓存、1个成功新译、1个失败后排队，新增API调用0。该回放不写正式主库或推送账本，不能混同为线上正式六篇发布。证据在 real-replacement-replay.json。

本次没有重新检索或付费重评。原库3745篇身份完整保留。修复前后备19篇；正式发布五篇后可用14篇。以24日为准共有784条候选、524条有效已评审记录，19条满足现有最终入选条件（包括同日已经正式发布的5篇）；回看23日现有永久历史约束下为779条候选、14条符合AI及来源门槛。没有伪造23日补发：23日原始partial保留，恢复的是24日真实完整归档。

| ID | 标题 | 来源与审核 | 中文 |
|---|---|---|---|
| 2610.14598 | Bidirectional Adaptive Transformers for Multimodal Anomaly Detection | arXiv / 有效既有AI审核 | Argos，有效 |
| 2610.03403 | ForestQuery: Boundary-Aware and Spatially Anchored Query Learning for Unified Forest Point Cloud Segmentation | arXiv / 有效既有AI审核 | Argos，有效 |
| 2610.00319 | EgoRefine: Ego-Referenced Predictive Alignment and Trajectory-Conditioned Reliability-Aware Fusion for Asynchronous Collaborative Perception | arXiv / 有效既有AI审核 | Argos，有效 |
| 2609.28159 | Depth-Guided Contrastive Learning for 2D Representations with 3D Spatial Awareness | arXiv / 有效既有AI审核 | Argos，有效 |
| 2610.06837 | Anatomy-aware Fine-grained Multimodal Fusion for Laryngopharyngeal Cancer T-Staging Prediction Using CT and Radiology Report | arXiv / 有效既有AI审核 | Argos，有效 |

本次新翻译1篇、缓存4篇，DeepSeek新调用0次、费用0元。模型、研究偏好、可信来源标准和推荐比例未修改；本轮没有重新评估既有AI迁移判断的学术准确性。

## 3. 个人阅读批次

新增独立键 `rs-paperclaw-maritime-daily-reading-v1`，保存当前五篇公开元数据完整快照、模板、批次身份和真实精选日期、完成状态、北京时间完成日期、已展示批次列表。favorites、notes及旧reading键不变；私人阅读进度不上传GitHub、不进入云端去重账本。

- 未完成：刷新、关闭重开或跨日均继续当前五篇；顶部北京时间阅读日期更新，真实批次日期保持。
- 点击底部“✓ 本批五篇已阅读完成”：当天保持当前内容，显示“已阅读完成 · 明日更新”，允许撤销。
- 次日：只有云端最新结果为完整五篇、每篇有中文及AI分、日期更新、身份与当前批次不重叠且不是已展示批次，才切换并清除完成状态。没有可用新批次、网络失败或partial均不换批。
- 只在完成后的次日请求轻量latest；页面打开时每分钟检查日期。收藏笔记编辑框打开时延后自动换批，避免丢失输入。
- 所有快照内容以文本节点渲染，链接只接受HTTP(S)；复制Prompt复用原模块和原13项模板。旧的不完整归档继续沿用原收藏/Prompt初始化，不强行初始化“五篇”阅读进度。
- 不同浏览器、设备的阅读进度独立，页面已有明确说明。首次启用以当前完整五篇安全初始化，无法追溯功能上线前用户在手机上正在阅读的旧批次。

云端任务完全不读取个人进度，继续自动检索、AI审核、储备、Argos及归档。schedule、预算、15篇储备目标和单一云端写入流程均未更改；默认无需每天双击桌面入口。Actions调度可延迟，不承诺07:20/12:20准点。

## 4. 实测与回归

- Python：146项通过；Node：43项通过；git diff --check通过。
- 覆盖失败替补、保留合格项、修复后恢复资格、后备耗尽保留完整日报、分别/数值保护、旧归档兼容。
- Node含真实模块联动的DOM测试：未完成跨日、快照重开、当天完成不换、撤销、次日有效换批、partial/重叠/同一批次拒绝、DOI别名、存储失败保留、收藏笔记与Prompt联动。
- 独立localhost真实浏览器测试：390px宽，五篇、五条单行操作栏，无横向滚动；点击完成、刷新后仍完成、撤销均成功，Prompt显示“已复制”。截图：`papers/maritime/backups/v3_8_4_before/reading-complete-mobile.png`。
- 跨日由可控时钟回归验证；无法代替实体手机连续两天的实际使用。未读取、清空或迁移用户手机私人存储。

## 5. 修改范围

源码：services/mobile_digest.py、selected_translation.py、config/maritime/translation_terms.json；新增 docs/maritime_daily_reading.js；对 maritime_favorites.js 与 maritime_daily_prompt.js 只增加协同初始化入口，更新完整库缓存参数。同步更新日报生成HTML、24日正式JSON/Markdown、latest、pending、发布状态、永久账本、后备池、主库和公开静态主库。

测试：新增 tests/test_maritime_v3_8_4.py、daily-reading.test.cjs；既有版本断言同步；test_maritime_v3.py改为与其他测试一致的本地fixture导入，解决本机环境中第三方同名tests包冲突。没有修改收藏笔记格式、导出机制、Prompt模板、Argos模型、DeepSeek客户端或Git同步白名单。

## 6. 线上发布

待本次提交后填写真实Pages运行及线上HTML/JSON核验结果，不以本地测试代替上线成功。
