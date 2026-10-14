# V3 文献有效性与统计修复报告

核验日期：2026-10-13（北京时间）。本轮只调整现有入库记录的类型、有效性、推荐资格、精读 Prompt 与网页统计；未重新开发检索系统。

## MarVAIS 审计与证据

- DOI：`10.5281/zenodo.23267832`；由 OpenAlex `W7221072147` 入库，不是 Crossref 期刊检索结果。
- 原始发表日期：2026-10-09；首次入库及最近检索时间均为 `2026-10-12T11:37:06.968370+00:00`（北京时间19:37）。原始 `publication_evidence.type=other`，来源名称为 Zenodo；原始 `venue_type=unknown`、`publication_status=unknown`。
- 原始摘要说明：40分钟视频、AIS CSV、约72000帧；Zenodo仅提供占位ReadMe，完整数据需申请外部Google Drive权限。它是数据集发布记录，没有正式期刊论文证据。
- 实际访问 [Zenodo官方API](https://zenodo.org/api/records/23267832) 返回 **HTTP 410**，JSON为 `{"status":410,"message":"The record has been deleted."}`。
- 实际访问 [DOI](https://doi.org/10.5281/zenodo.23267832) 返回410，页面标题为 `Tombstone | Zenodo | Zenodo`；Crossref查询返回404，404仅表示该接口未找到，删除判断依据是Zenodo明确410消息。
- 修复前这条记录在当前后端已经属于普通候选，而不是已核验高水平期刊；问题是资源类型和删除标记缺失，候选库仍能当论文展示并复制13项Prompt。现已标记 **数据集／已确认删除**，保留原身份及历史信息，排除默认论文展示、重点推荐、日报和研究论文Prompt。
- 第二条同名 DOI `10.5281/zenodo.23268955`：官方API实际返回200，资源类型为video；结合数据集标题与摘要分类为数据集。**它仍存在，不能说两条都删除。** 同样不占论文配额。

## 同类记录复查

本轮在线检查11条带Zenodo或Figshare DOI的记录：7条可访问、1条确认删除、3条超时。分类为3条数据集、1条软件、2条其他资源、4条研究预印本、1条正式期刊论文。

- 6条明确非论文资源（3数据集、1软件、2其他资源）不再默认展示为论文，全部保留归档。
- 4条研究预印本保留，包括2条具有真实arXiv身份的论文，未因关联Zenodo DOI而整个平台排除。
- 1条 `10.5281/zenodo.19872616` 另有OpenAlex正式期刊发表证据（International Journal on Emerging Research Areas），保留期刊信息；其分区仍待核验，不成为高水平推荐。
- 软件 `10.5281/zenodo.21827856`、资源 `10.5281/zenodo.21415220`、数据集 `10.5281/zenodo.23202720` 本轮均超时，标记暂时无法访问，**未判为删除**。
- 原始网络审计与前后保护字段对照保存在忽略提交的 `papers/maritime/private/` 中。公开库保留核验链接、状态、HTTP状态码、原因与时间，不含API Key。

## 推荐与网页行为

- 按本轮最新要求，水路必须是相关、具备正式期刊发表证据、已核验CAS2025大类一区或JCR JIF Q1、未确认失效的论文；CCF A会议和arXiv海事预印本仍可归档，但不能进入水路精选。
- 陆上／通用原有高水平期刊、CCF A、强相关arXiv规则保留。后台配额仍为修改前配置的10/6/4，未调整比例。
- 顶部只动态显示 `水路 N 篇 · 陆上 N 篇 · 通用方法 N 篇`。按当前筛选结果去重计数；不再使用后端未筛选的counts，不展示比例、分母或不足补位说明。全部论文库显示当前论文数和总归档记录数。
- 当前重新生成的近期精选：**水路0篇 · 陆上6篇 · 通用方法4篇**。水路0表示当前时间窗口内没有满足已核验高水平正式期刊条件的记录；本轮没有为凑数量降低门槛或改配额。
- 有可信PDF地址的研究论文Prompt先尝试读取／核对全文，获取全文后才开展13项分析；没读到则简短请求上传后停止。无PDF地址直接复制短Prompt，不附13项要求。数据集、软件等不生成研究论文精读Prompt。

## 修改文件

- 新增 `skills/rs-paper-pipeline/scripts/services/maritime_validity.py`：基础资源类型、正式发表证据、有效性分类与缓存检查。
- 修改 `services/maritime_v2.py`：类型注释、失效排除、水路资格、归档保留。
- 修改 `services/maritime_update.py`：新入库与精选记录优先核验；默认每批最多20条，7天缓存，避免反复检查整个历史库。
- 修改 `clients/scholarly_client.py`：保留OpenAlex明确撤回字段。
- 修改 `services/maritime.py`：日报排除非论文与明确失效记录，可选核验CLI；更新水路日报标题。
- 修改 `services/maritime_reading.py`、`prompts/maritime_analysis.md`：资源保护与全文条件Prompt。
- 修改 `docs/maritime.js`、`docs/maritime.html`：短Prompt、实际筛选计数及简化标签。
- 新增 `tests/test_maritime_validity.py`；更新 `tests/test_maritime_v2.py`、`tests/maritime.test.cjs`。
- 更新论文归档JSON、网页JSON及已有日期的派生Markdown日报；没有删除历史论文身份。

## 实际测试与结果

- `python -m unittest discover -s tests`：**50项通过**，含有效性、正式发表、预印本保留、水路资格、阅读/翻译保护、来源失败等测试。
- `python -m unittest discover -s skills/rs-paper-pipeline/tests`：**原项目49项通过**。
- `node --test tests/*.test.cjs`：**19项通过**，含真实渲染事件的专题／日期／时间范围切换计数、无PDF短Prompt、13项全文条件、备份恢复与既有日报解析。
- 实际在线检查上述11条资源，并额外检查MarVAIS DOI解析和Crossref接口；不是用模拟响应替代线上删除判定。
- 实际重建网页与日报，核对 **2511条记录** 的阅读状态、分析、翻译缓存、英文摘要、首次/最近检索时间、原始元数据快照前后完全一致。

## 使用与限制

在仓库目录运行：

```powershell
# 复查单条记录
python skills/rs-paper-pipeline/scripts/cli.py maritime --action verify --id doi:10.5281/zenodo.23267832 --timeout 15
# 默认仅复查精选，限制20条
python skills/rs-paper-pipeline/scripts/cli.py maritime --action verify --limit 20 --timeout 15
# 可选历史批量复查（长程序自行运行）
python skills/rs-paper-pipeline/scripts/cli.py maritime --action verify --all-history --limit 100 --timeout 15
```

本轮不重新跑全库检索，不触发模型重翻译，也没有推送GitHub或发布Pages；本地页面刷新即可读取新数据。有效性检查是有限来源证据检查，不保证发现所有出版社的撤回公告。403/429列为访问受限，404/超时/5xx列为暂时无法核验；除明确官方删除或撤回证据外，不清除论文。已经确认失效的状态不会仅因后续链接200或超时自动解除，需要明确的恢复证据。3条超时来源的真实状态仍待核验。
