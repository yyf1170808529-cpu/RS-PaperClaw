# V2 操作指南

**日常使用先看 [简明操作指南](./简明操作指南.md)**：双击打开、看论文、复制Prompt、保存分析、更新和备份。下文是进阶配置，不需要先读完才能使用。

工作目录：`D:\desktop\code\paper\RS-PaperClaw`。继续用原 Python CLI 和 `start-maritime.cmd`。没有重建 Dashboard、数据库或 LLM 服务，也没有部署 V2 长期调度。

## 先看已经入库的真实论文

双击根目录 `start-maritime.cmd`，保持窗口打开。阅读地址 `http://127.0.0.1:8000/maritime.html`。默认显示全部已收录的入选论文；“最近7天重点推荐”是可选的精选范围，不用一般候选补数量。

选择“阅读范围 → 全部已收录论文”，“期刊门槛 → JCR JIF Q1”，可以查看已通过 Crossref/OpenAlex 获取的 TIM 海事船舶检测论文，第一作者 Jian Fu，单位 Beihang University。CAS 分区显示待核验，JCR 2025 两个学科 Q1。它是历史验证样例，不冒充最近7天新论文。英文摘要完整保存；中文需要安装翻译工具并执行翻译。

“全部高水平期刊（OR）”取 CAS 和 JIF 条件并集；“同时一区”才是两条件交集。JCR多学科只需最新核实年份中一个有效学科 Q1。旧年份信息保留用于追溯，判定不回退使用已有更高年份记录之前的 Q1。JCI/SJR 字段不进入该判断。

默认四专题分类保留。推荐组为海事正式重点、跨领域正式方法、前沿预印本、一般候选；医学/EEG/纯轨迹预测保留在一般候选，不参与重点推荐。机构不参与分数。当前正式来源较少，推荐比率不达70–80%时减少数量，不补无关论文。

## 取新论文及回溯（长命令由你执行）

```powershell
cd D:\desktop\code\paper\RS-PaperClaw
# 原arXiv流程保持
python skills/rs-paper-pipeline/scripts/cli.py maritime --days 7
# 各来源独立执行，成功数据即保存；任何失败/扫描截断整体返回非零
python skills/rs-paper-pipeline/scripts/cli.py maritime --action fetch-all --days 14
# 正式期刊：所有启用候选池，或指定期刊id
python skills/rs-paper-pipeline/scripts/cli.py maritime --action fetch-journals --days 180 --journal tim --journal ocean-engineering --query 'ship detection'
python skills/rs-paper-pipeline/scripts/cli.py maritime --action fetch-journals --days 366 --journal joes --query 'maritime perception'
# OpenAlex可发现候选池之外的期刊/会议，其分区仍需另行核验
python skills/rs-paper-pipeline/scripts/cli.py maritime --action fetch-openalex --days 180 --query 'maritime multimodal perception'
# 精确DOI检索不受--days范围限制，用于补元信息和历史验证
python skills/rs-paper-pipeline/scripts/cli.py maritime --action fetch-all --source crossref --source openalex --doi '10.1109/TIM.2025.3559575'
```

默认每页100、最多30页；正式来源达上限会保存已获取结果并标记 incomplete，绝不称全量成功。按来源/期刊写入 `papers/maritime/library.json` 的 source_runs，网站显示最近一次来源任务的成功/失败。24小时元数据缓存位于私有目录；不缓存失败。关键词查询只是召回，正式期刊身份通过 ISSN 与 Crossref journal title 核验。

免费 OpenAlex key 是可选项，基础请求不强制 Key；若匿名配额不足，可在环境变量 `OPENALEX_API_KEY` 设置自己的免费 Key，不写入代码或备份。它不是 LLM API。Crossref 可选 `CROSSREF_MAILTO`，原 `RS_PROXY_URL` 仍有效。不得绕过任何付费或账号限制。

## 维护期刊池与分区证据

文件：`skills/rs-paper-pipeline/scripts/config/maritime/venues.json`。当前19本候选包含 Ocean Engineering、JOE、TIV、TITS、TIM。候选身份种子不能代替分区；运行检索时另行核对 ISSN/name。TIM已记录JIF2025证据，其余分区大部分待核验，仍允许获取一般候选。

CAS记录必须是官方表、major大类、默认2025年；publisher或学校引用官方表可作为证据，但只有笼统“一区”且未说明大类的信息不能填入已核实记录。修改 recommendation.json 的 cas_year 可调整明确指定的版本。

将核验资料整理成 JSON 后导入（这会更换对应期刊的该套记录，注意保留历史记录）：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --action import-venues --file .\my-verified-venues.json
python skills/rs-paper-pipeline/scripts/cli.py maritime --action venue-audit
```

JSON 格式示例仅示范结构，**不能把示例 URL 作为核验依据**：

```json
{
  "journals": [{
    "id": "tim", "issn": ["0018-9456"],
    "cas_records": [],
    "jcr_records": [{
      "scheme": "JCR", "metric": "JIF Quartile", "year": 2025,
      "category": "明确的真实JCR学科名", "quartile": "Q1", "verified": true,
      "evidence": {"kind": "institution", "url": "实际核验来源地址", "checked_at": "2026-10-12"}
    }]
  }]
}
```

CAS额外字段 `scheme: CAS`, `scope: major`, `official_table: true`, `partition: 1`。未核验条目用 `verified: false`。证据可用 URL 或本地证明文件字段 `local_file`，不要把付费报告全文发布在 GitHub。新增期刊直接编辑候选池；不要复制其他期刊分区。

会议采用独立 conference_records：用 DOI 或稳定 paper_id 精确绑定论文，scheme为 official_proceedings，提供真实 venue、year 和已核验的官方论文集 evidence。官方论文集有明确证据但没有DOI也可登记；论文标题中自称CVPR/NeurIPS不能作为录用依据。Workshop不默认等同主会。

## 可选离线中文摘要

最简单的操作：双击根目录 `install-translation.cmd` 安装，再双击 `translate-maritime.cmd` 翻译摘要，完成后刷新页面。安装脚本优先使用已安装的 Python 3.11，否则使用当前 Python；安装失败会停止并保留错误供排查。模型下载和翻译由你启动，本轮未运行。下面是等价的手动命令：

```powershell
python -m venv .venv-maritime
.\.venv-maritime\Scripts\python.exe -m pip install -r skills/rs-paper-pipeline/requirements-translation.txt
.\.venv-maritime\Scripts\python.exe skills/rs-paper-pipeline/scripts/cli.py maritime --action install-model
.\.venv-maritime\Scripts\python.exe skills/rs-paper-pipeline/scripts/cli.py maritime --action translate --limit 5
```

模型安装后无需网络翻译。以后使用**这个虚拟环境的 Python**检索，新入选论文可自动翻译；普通环境未安装Argos时只做检索。已有译文按英文摘要hash复用，机器结果明确标识。翻译失败不阻塞检索/归档，页面保留英文。AIS/Radar/LiDAR/DETR及公式使用轻量占位保护；若模型破坏占位符则拒绝缓存为成功，需要人工修订。

离线模型及Argos质量尚待实际验证，不能认为已得到高质量科研翻译。网页可切换中文/英文/中英对照、复制摘要。中文不存在时明确提示；数学公式按原文文本保存。

人工修订：把完整中文摘要放到UTF-8文本文件，例如 `abstract-zh.txt`：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --action revise-translation --id 'doi:10.1109/tim.2025.3559575' --file .\abstract-zh.txt
```

人工译文不会被再次机器翻译覆盖。

## ChatGPT / DeepSeek 网页精读

点击“原始论文”优先打开已知 PDF；没有 PDF 时打开论文页面。复制分析 Prompt，打开 ChatGPT 或 DeepSeek 并粘贴。Prompt 包含 PDF 链接，请网页端先尝试读取；无法读取时，再手动上传 PDF。把分析复制回来保存即可，日常不需要本地 PDF 命令。

下面的 CLI 保留为可选工具，不再出现在阅读页。已验证的样例：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --action prepare-pdf --id 'doi:10.1007/978-3-031-20047-2_1' --extract-text
```

ByteTrack来自ECCV官方开放论文集。本地 `papers/maritime/private/reading/0e875c78bf9f135e/` 已有 paper.pdf、paper.txt、prompt.md和manifest.json。该私有目录被Git忽略，不打包进静态页面。上传 PDF 和 Prompt 到 DeepSeek 网页需你手动操作。

无可信开放PDF时，先依法获得PDF，再指定本地文件：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --action prepare-pdf --id 'doi:10.1109/tim.2025.3559575' --file 'C:\Users\yyf\Downloads\paper.pdf' --extract-text
```

不爬付费全文，不把登录页当PDF，不自动上传DeepSeek。文本提取复用原项目pdftotext思路；无该工具时PDF/Prompt仍可准备，明确标记文本不可用。扫描PDF不提供OCR，全文提取/标题匹配失败时需人工核对。

分析粘贴、五档阅读状态、Markdown导出、JSON备份、CLI导入保持原操作。新论文用 DOI/OpenAlex身份，旧arXiv身份保持；别名合并记录保留。自动合并只用 DOI/arXiv显式关系，标题相似不合并。两个已有人工分析冲突会保留到 merge_conflicts，不悄悄丢弃。

## 重新评分、日报与审查

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --action rescore
python skills/rs-paper-pipeline/scripts/cli.py maritime --action site
python skills/rs-paper-pipeline/scripts/cli.py maritime --action review-audit --limit 25 --file .\my-review-audit.json
```

每日归档分组显示，不再简单取关键词前25。没有准确日的期刊论文只显示年份/年月，进入历史库，不凭空补1月1日用于每日推荐。查询原来源日期保留在metadata_records中。Crossref/OpenAlex对日期可能不一致，需以出版社进一步核对。

已做一次25篇真实候选的摘要层适配审查，见 `MARITIME_V2_RECOMMENDATION_AUDIT.md`。这是研究兴趣检查，不是创新性评审。当前样本不足以证实海事推荐70–80%目标或前10篇8篇标准。

详细实际测试和未解决事项见 `MARITIME_V2_FINAL_REPORT.md`。暂不启用新的V2长期Actions/Pages部署；原V1独立工作流仍在文件中，未自动修改你的GitHub设置。
