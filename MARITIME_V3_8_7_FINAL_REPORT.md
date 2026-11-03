# RS-PaperClaw V3.8.7 验收报告

## CFUNet真实链路与前后结果

对象：doi:10.21203/rs.3.rs-11121422/v1，CFUNet: An Adaptive RGB–Depth Cross-Modal Fusion Network for Pavement Crack Segmentation。

旧链路中，road触发交通信号；OpenAlex入库的Research Square记录resource_type=preprint被hard_eligible无条件视作前沿来源；旧模型direct_relevance=3、transferability=3、confidence足够，并提供双ResNet50及EWF模块的精确摘要引文和船舶迁移建议，故transfer_ok放行。规则分12，AI分60，主库无arxiv_id，来源不是arXiv。

新链路：application_bucket不再为land；基础设施巡检排除命中Pavement Crack；无真实arXiv身份，来源门槛不通过；ranking_info.eligible=False、state=domain_excluded，前台显示“不符合每日精选范围”。原始模型JSON、引文、英文、DeepSeek译文与元数据全部保留，cached_evaluation仍可读取。

评分改为16×direct+4×transfer（80/20）。CFUNet的3/3在两个公式下都等于60，不能靠换公式解决；其有效推荐分现在为空、资格被硬规则阻断，不伪造一个降低后的模型原始分。

## 通用修复

新增relevance_scope.py，由domain_exclusion、abstract_quality.application及每日来源资格共同调用。病害/巡检识别包含路面、沥青、桥梁、混凝土裂缝/缺陷/养护等明确对象和任务；road、segmentation或Transformer单词本身不作为排除条件。交通场景要求自动驾驶、车辆/行人/道路参与者或交通监测等对象与感知任务共同出现。

预印本需合法arxiv_id，或与arXiv来源相符的官方arXiv链接。只有Research Square/SSRN/Zenodo的预印本类型或DOI不够。海事正式高水平期刊门槛不变，已核实CCF-A正式会议仍可入选。没有因为平台名清空整个来源库。

最终AI资格分两路：直接任务路径需direct≥2、真实关注对象/任务范围、有效摘要方法证据；通用方法路径需direct≥1、transfer≥3、非“不推荐”、有效具体迁移路径，以及独立的通用学习/匹配机制审查。两路仍需当前缓存有效、confidence≥0.7。direct=0不能被高迁移分或confidence救回；confidence和迁移描述不作为范围证据。只含attention/fusion/network等宽泛词不够。

这是对旧缓存语义的一次兼容性判定：旧direct字段常把“无海事背景”当低直接相关，故不把它单独当通用方法的唯一门槛。SNAP原分1/4按新式为32仍可凭困难负样本机制入选；ROSETTA原分2/4为48仍凭跨模态坐标校准机制入选。没有上调原模型数值，没有把具体任务不同的数据集替换当作普适性证明。规则仍可能漏掉未知新机制，应保留候选供人工审查，不声称自动判断完美。

研究范围及来源硬规则独立于LLM缓存指纹。仅分类字段变化时，原来已验证且标题/英文/发表状态/venue/quality均未改变的缓存登记兼容指纹；正文、标题或质量变化不走此兼容。未全库重评，也没有因换Prompt清空上千条缓存。

## 历史与私人状态

11月1日原始归档保留，CFUNet及另两条缺少arXiv身份的Research Square预印本加入content-corrections.json，replacement=null，保留原文和译文。当前没有为旧批次硬凑替补，也没有标记用户已读。旧快照使用既有安全修正逻辑，仅移除这些不合适条目并保留待修正原始快照；其余身份、批次日期、shown、收藏、笔记、完成状态不变。缺少五篇时不允许冒充完整批次。

reading-index现在同时核对当前来源及AI范围资格，排除不再合格的历史批次；全库仍保留这些论文。没有读取、清空或重置用户浏览器localStorage。Node新增CFUNet旧快照用例验证日期、shown、未完成状态、英文与收藏笔记保留。

## 测试与真实发布

本地Python154项、Node46项通过，包含CFUNet、Pavement crack、Bridge crack、Road surface defect、Road infrastructure inspection、Concrete defect、Asphalt maintenance负例；船舶视觉、Radar–AIS、视觉–AIS、自动驾驶车辆、交通跟踪/融合及真实SNAP/ROSETTA缓存正例。另验证Research Square不能冒充arXiv、合法arXiv ID可用、正式CCF-A不误杀，以及direct=0/transfer=5/confidence=1仍不合格。

过程中安全合并了并发定时更新，未force push。因一次推送被并发提交拒绝，取消了旧代码手动任务41633459132，再确认新版提交后触发一次正式验收，未盲目重复同一dispatch。部分克隆惰性下载卡住时只终止了本次已确认进程，核实无Git进程后清理遗留锁，经代理安全快进；没有reset或删除索引数据。

新版云端运行[41633788608](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/41633788608) completed/success，head SHA a979f00a6b4b517e0f808ecc6eb06748f9cf1963。云端Python154项/Node45项及无Argos依赖检查通过；Node的CFUNet特定快照补充测试随后在本地通过，因此本地计数46。恢复模式跳过重新检索，不冒充新一轮来源抓取；后续AI、精译、完整五篇保护、同步均真实成功。云端数据提交a8f23d7231a5842e8de1f996abd927ae8e27d840已安全拉回。

11月3日正式五篇：

| ID | 标题 | AI分 |
|---|---|---|
| 2610.39848 | LiDAR-SHIELD: A Fully Dockerized Adversarial Robustness Assessment Framework for LiDAR-Based 3D Perception Models | 36 |
| 2610.06232 | AUTOPILOT An Advanced Perception, Localization and Path Planning Techniques for Autonomous Vehicles Using YOLOv7 and MiDaS | 40 |
| 2609.38511 | Onboard Vision and MPC Navigation for Underwater Robots: An Open BlueROV2 Platform for Multi-Robot Experiments & Docking | 56 |
| 2609.33230 | AevaScenes: An FMCW LiDAR Dataset and Benchmark for Long-Range Perception | 40 |
| 2609.32856 | PolyTopoBench: A Benchmark for Complex Vector Polygon Generation from Remote Sensing Imagery | 40 |

五篇均经有效既有AI缓存、当前范围与来源硬门槛，且未在历史日报出现；全部有DeepSeek中文及两句导读。AI筛选本次processed=0、cached=1233，新增筛选费用0，没有全库重复付费。本次只对新入选五篇产生5次必要精译调用，4187 tokens，按API响应时间计价0.00929000元，峰值口径上界0.01858元；不是独立账单差额。历史CFUNet译文没有重翻。

发现精译摘要计价字段原显示0，但API usage缓存实际为非零；已从真实响应计价修正公开汇总，并修复selected_translation.py后续统计，不把付费请求宣称为免费。模型、预算、Argos退役状态及Git白名单不变。最终后备可用11篇；不承诺以后候选不足时硬凑五篇。

最终Pages运行[41635304695](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/41635304695) completed/success，对应提交4f39bc09e3575dcbe6d7df16ae6512fa1505f020。用手机User-Agent真实HTTPS读取每日HTML、latest、11月3日归档JSON、reading-index、content-corrections、桌面maritime.js，共6项均HTTP200并与本地逐字一致。CFUNet移除清单及“不符合范围”的前台脚本已公开上线。证据在忽略目录papers/maritime/backups/v3_8_7的cloud-proof.json、cloud-logs、online-proof.json、cfunet-audit.json及测试日志。

入口：https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html?v=3.8.7 。没有让用户运行任何命令或完成非必要授权。

## 改动范围与限制

改动为abstract_quality.py、domain_exclusion.py、relevance_scope.py、mobile_digest.py、semantic_evaluation.py、maritime_v2.py的分类缓存兼容、desktop显示标签、必要测试及派生数据；附带修正实际验收发现的精译计价显示。旧归档仍保留原始发表事实，不把历史错误伪装成当时未发生。

本轮提供的是启发式研究范围资格审查，不宣称准确测量真实创新性。实体手机私人存储无法远程实测，行为由Node交互回归覆盖；线上文件另用真实HTTPS验证。用户无需执行命令。
