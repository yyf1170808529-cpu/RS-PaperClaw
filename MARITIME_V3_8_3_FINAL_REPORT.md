# V3.8.3 永久去重、Argos修复、手机排版与作者单位

日期：2026-10-22。正式页面：[每日精选](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html?v=3.8.3)。

## 1. 重复推荐根因与修复

实际读取原2026-10-14、2026-10-22日报，确认 CmIVTP（2605.26524）、Sparse2comm（2610.08573）、DiscoVL（2610.11113）、Global Average Precision（2610.09863）重复出现。`candidate_pool()`仅排除最近7天；`refresh_reserve()`也在7天后重新开放，导致历史论文再次占位。

新增 `services/mobile_history.py`，遍历全部已发布归档，包括没有 `publication_status` 的早期JSON；明确partial/failed待发布批次不算已推送。按去版本arXiv ID、DOI、URL和 `library.aliases` 建立同一身份映射，不采用标题模糊匹配。持久化账本为 `docs/maritime-data/mobile/pushed-history.json`，本次59个身份标记，包含同篇论文的不同标识，并非59篇不同论文。

历史任意日期推送过的论文永久排除；后备中的相同论文标为不可用。即使之后修复归档，账本仍保留曾推送记录。同一天首次发布的有效论文可保留，以保证重建稳定；如果它还在其他日期出现过，仍然排除。选择阶段还避免不同版本占用两个位置。本轮未开发回顾模式。

原主库、全部手机归档、原页面和后备池先完整备份到本地 `papers/maritime/backups/v3_8_3_before/`（Git忽略）。原10月22日JSON另保存为公开修订证据：[原日报备份](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-data/mobile/revisions/2026-10-22-before-v3_8_3.json)。原14日日报JSON及其他历史JSON没有删除。

## 2. 10月22日真实重建

永久排除后检查到780篇候选，其中403篇有有效当前AI评价，16篇通过既有发布资格，足够补选。未重新检索，也未调用新的DeepSeek审核。保留当天首次推送的ROSETTA，移除上述四篇重复论文，新增下表后四篇。

| paper_id | 最终入选 | AI审核 | 中文摘要 |
|---|---|---|---|
| 2610.12871 | ROSETTA: Rotation Subspace Estimation for Training-free Transmodal Alignment（保留） | 当前指纹有效 | Argos有效缓存 |
| 2610.09411 | Shared Geometry As A Rosetta Stone: Cross-Modal Alignment Without Paired Data（新增） | 当前指纹有效 | Argos有效缓存 |
| 2610.03167 | Geometry-Aligned Semantic Matching for Cross-Modal Planar Image Registration（新增） | 当前指纹有效 | 本次Argos实际补译成功 |
| 2609.38637 | Template-Search Domain Adaptation via Multi-Stage Feature Alignment for Cross-Modal Object Tracking（新增） | 当前指纹有效 | 本次Argos实际补译成功 |
| 2609.25067 | SPARC: SuperPixel-Aware Region Contrastive Learning for Self-Supervised Dense Prediction（新增） | 当前指纹有效 | 本次Argos实际补译成功 |

五篇均为如实标记的arXiv论文，继续满足原有可迁移方法论文来源及AI证据要求，未将其改称正式期刊或CCF A。五篇均检查英文摘要哈希、有效AI结构与证据、中文结构校验。重建第二次的身份列表一致；均没有出现在此前其他日期的已发布日报中。新发布后可用后备11篇，目标仍为原配置15篇，未声称已经补满15篇。

`update-result.json`追加本次maintenance记录，保留原云端检索与费用统计，不把本次维护冒充新检索。新增DeepSeek请求、DeepSeek翻译请求和新增API费用均为0。

## 3. 三个真实Argos错误

先使用现有本地Argos模型，对三篇原摘要中受影响的真实句子运行旧代码，三项均实际复现失败；随后对三篇完整真实摘要重新翻译，均成功。

| 论文 | 根因 | 修复后真实结果 |
|---|---|---|
| CmIVTP | 保护阶段保留AIS而把derived译为中文，校验阶段却要求整串AIS-derived逐字出现 | 允许derived正常翻译，仅保留AIS；完整摘要machine，哈希及结构校验通过 |
| Sparse2comm | `/`被当成禁止的边界，AP@0.5/AP@0.7第二个AP被误判缺失；普通描述性连字符词也可能被过度保护 | 校验与保护使用统一技术标记规则；AP、阈值和全部数值保留，普通词可翻译；完整摘要machine |
| Global Average Precision | `$k$NN`的NN触发了旧词边界限制，即使公式原样保留仍被判缺失 | 数学表达式按原始字符串计数，不套普通词边界；完整摘要machine，保留`$k$NN` |

保护规则覆盖美元公式、LaTeX行内/展示公式、URL、数字和百分比。AP/mAP可接受有指标上下文的正确中文术语，不把通信接入点AP误当平均精度。未取消真正的数值、公式和URL缺失检查；人工译文优先级不变。

实际补译SPARC时另外定位到 `MoCo-v2` 被拆出 `v2`，该片段译写数字而失败。已保留完整模型版本及独立版本标记，随后真实重试成功。对问题片段最多重试一次；精选worker对校验失败再有限重试一次并保留错误记录，不无限重译。模型实例在同一worker中复用。

发布资格现要求五篇均有有效中文：无模型、数字错误、公式丢失等任一原因造成缺译，批次均为partial，不能标为完整；保留待恢复结果，并回退到真正有五篇中文的最近完整日报，保留原日期。三篇历史故障论文和本次三篇缺译精选共6篇完整摘要实际新翻译成功，另外两篇精选复用有效缓存；没有新下载Argos模型。

本地Argos仍有语序和术语表达生硬的问题，本轮结构校验通过不代表人工语言质量认证；英文摘要完整保留，未用付费模型改写译文。

## 4. 作者和第一单位

日报JSON现在携带作者、第一作者、第一作者单位、来源、核验状态及必要证据。HTML在标题下显示作者和第一单位，超过5位作者时可展开完整列表。单位缺失显示“待核实”。

日常流程只对精选做轻量补全：先已有元数据/缓存，有DOI则查既有Crossref/OpenAlex客户端；无DOI则有限OpenAlex标题查询，并要求明确arXiv身份关联；arXiv官方XML只接受第一author节点下的单位。核对论文ID、完整标题和第一作者，不修改论文身份、标题、摘要或AI评分字段。核验与失败均缓存。元数据补全不阻断检索。

本次五篇XML没有作者单位；又检查官方HTML，并为HTML不能明确关联的两篇合法下载官方公开PDF，仅核对首页。使用nature-downloader公开访问与证据核验流程；PDF、HTML及下载manifest仅保存在本地private目录，未上传私人PDF或笔记。

| 第一作者 | 第一署名单位 | 真实证据 |
|---|---|---|
| Alex Junho Lee | School of Mechanical Systems Engineering, Sookmyung Women’s University | [ROSETTA官方HTML作者脚注](https://arxiv.org/html/2610.12871v1)，单作者及明确单位 |
| Dominik Schnaus | TU Munich | [官方PDF](https://arxiv.org/pdf/2610.09411)，实际读取v2首页：第一作者标1,2，单位1为TU Munich；没有按HTML中未关联的机构列表猜测 |
| Zhiwei Wang | 待核实 | [官方HTML](https://arxiv.org/html/2610.03167v1)及实际PDF首页没有单位；OpenAlex/arXiv查询也未确认，不推断通讯作者机构 |
| Fereshteh Aghaee Meibodi | Department of Electrical and Computer Engineering, University of Victoria | [官方HTML](https://arxiv.org/html/2609.38637v1)第一作者独立作者块中的单位 |
| David Szczecina | Systems Design Engineering, University of Waterloo | [官方PDF首页](https://arxiv.org/pdf/2609.25067)，作者列表下的共同署名地址 |

四篇新增单位前后AI指纹逐一比对一致；五篇最终AI评价均仍有效。尚未完成项是2610.03167的单位核实，页面没有编造补齐。

## 5. 手机排版和功能验收

原文、阅读与笔记、Prompt、☆收藏放进同一个nowrap flex容器。`MaritimeFavorites.mount()`只增加可选的行内按钮/下方笔记容器参数，使用原存储键和原数据结构；不另做收藏逻辑。已收藏显示★已收藏，笔记为空也能收藏，编辑区在下方按需展开。Prompt的复制反馈和备用只读文本框也在下方，不挤占操作行。

实际浏览器发现顶部原有JSON恢复文件选择器会撑宽320像素页面，已仅限制其宽度。对相同发布文件做真实浏览器viewport检查：

| 视口宽度 | 文档scrollWidth | 五篇操作行 |
|---|---|---|
| 320 | 305 | 每篇四个操作的top相同，无横向溢出 |
| 360 | 345 | 同排，无横向溢出 |
| 390 | 375 | 同排，无横向溢出 |

15像素差为浏览器垂直滚动条。真实点击Prompt得到“已复制”；截图保存在本地 `papers/maritime/private/v3_8_3/mobile-390.png`。Node交互回归验证行内收藏、跳过笔记、保存笔记、双页面、JSON/Markdown/TXT导出和Prompt回退。没有清空或检查用户浏览器的私有localStorage，也没有用测试收藏覆盖真实收藏。

内置浏览器直连github.io本次超时，因此窄屏交互使用同一发布文件的本地短时HTTP测试实例；实例60秒自动停止。线上另通过真实HTTPS逐文件比对一致。上述验证没有冒充实体手机测试。

## 6. 测试与真实部署

- Python：`python -m unittest discover -s tests`，142项通过。
- Node：`node --test tests/*.test.cjs`，39项通过。
- 覆盖永久历史去重、旧无状态归档、arXiv版本/DOI/别名、归档修复后账本保留、同日稳定、版本只占一个位置、后备不可回收、缺中文拒绝完整发布、公式/指标/版本保护、第一作者身份和AI缓存保护、行内收藏与笔记布局。部分旧测试原本要求7天后重推，已按新需求改为永久排除；旧测试构造的不同论文共享同一DOI/arXiv URL，也已改成各自唯一身份。
- `git diff --check`通过。公开数据检查没有私人reading内容或密钥。没有修改DeepSeek模型、可信来源标准、推荐比例、Prompt模板、收藏备份格式或调度。
- 核心修复提交 `728d4ce`，[首次Pages 39729199109](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39729199109) success。
- 窄屏溢出修复提交 `c38c773`，[最终Pages 39729836696](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39729836696) completed/success，实际SHA为 `c38c77379458230104a68b720d30cd1323a21c8c`。
- 部署后使用手机Safari User-Agent真实读取HTML、latest/2026-10-22 JSON、永久历史账本、旧日报备份、收藏/Prompt脚本和14日/22日归档HTML，共9项，与本地发布文件逐字一致。线上日期2026-10-22，五个新身份、五篇中文、四篇已核实单位和五条行内操作栏；四篇指定重复论文均不在新日报中。

主要源码修改为 `services/mobile_history.py`、`mobile_digest.py`、`maritime_reading.py`、`maritime_update.py`、`maritime_metadata.py`、`clients/arxiv_client.py`，均位于 `skills/rs-paper-pipeline/scripts/`；以及收藏/Prompt脚本、完整库入口的缓存参数、新旧归档HTML和必要测试。主库与公开静态数据同步保留实际修复结果。
