# 个人科研论文库：实际交付报告

日期：2026-10-12（北京时间）。工作目录：`D:\desktop\code\paper\RS-PaperClaw`。

**最新验证状态（同日后续修复）：专题 A 的最近 7 天检索已真实成功，63 篇候选、41 篇规则入选、9 篇高度相关，已生成论文库、日报与网页数据。按主专题分类 A=21、B=0、C=1、D=19；这是通过 A 检索召回的论文再按四专题评分，不是已完成全部四专题检索。下文“初始空库/未成功”描述首次开发验收状态。完整四专题在线执行仍由用户运行。**

## 完成情况与验收边界

已在原仓库源码上完成独立无 API 最小版本，离线回归与本地页面加载成功。**真实在线检索未成功，因此“看到真实最新论文列表”的最终在线验收尚未完成。** 没有放入测试论文、伪造示例或把网络失败写成空日报。当前发布用库文件是初始空库，没有成功日期记录。

原项目来自用户指定的 [thinson/RS-PaperClaw](https://github.com/thinson/RS-PaperClaw)，基线 commit `7a89e96cefa59f5a6b0abea4adba7b18228f7af4`。使用浅克隆与稀疏检出，跳过大型 `papers/previews`。已阅读 README、CUSTOMIZATION_GUIDE、PROJECT_OVERVIEW、CLI、配置、arXiv 客户端、关键词/LLM 筛选、单篇与日报 LLM 调用、原前端数据源及两个实际存在的旧工作流。基线实际定时文件名是 `rs-pipeline-schedule-reset.yml`，不是文档中的 `rs-pipeline-schedule.yml`。

## 新增与修改文件

修改仅四个原文件：

- `README.md`：添加独立模式链接。
- `skills/rs-paper-pipeline/scripts/cli.py`：在旧依赖导入前分派 `maritime`，旧帮助增加入口提示。
- `skills/rs-paper-pipeline/scripts/clients/arxiv_client.py`：添加通用日期/专题检索和完整 ID 规范化，调用原传输、重试、备用端点与 curl；旧遥感检索函数保持。
- `skills/rs-paper-pipeline/scripts/services/filter_assets.py`：加载独立四专题资产，旧配置不改。

新增：

- `MARITIME_MIGRATION_PLAN.md`、`MARITIME_README.md`、本报告。
- `skills/rs-paper-pipeline/scripts/services/maritime.py`：检索编排、规则评分、库合并、日报/网页导出、CLI 阅读成果导入导出、错误日志。
- `skills/rs-paper-pipeline/scripts/config/maritime/{A,B,C,D,rules}.json`：各专题独立检索组合、概念组、权重、阈值、场景和排除规则。
- `skills/rs-paper-pipeline/scripts/prompts/maritime_analysis.md`：13 项分析模板，强调全文证据、模块和公式，摘要不足时禁止虚构。
- `docs/maritime.html`、`docs/maritime.js`、`docs/maritime-data/library.json`：独立静态页面与数据。
- `papers/maritime/library.json`：本地唯一身份库（初始为空）。成功检索后生成 `daily_reports/maritime/YYYYMM/YYYYMMDD.md` 和 `docs/maritime-data/reports/`；当前没有制造空成功日报。
- `.github/workflows/maritime-no-api.yml`：独立手动/每日工作流。
- `tests/test_maritime.py`、`tests/maritime.test.cjs`：新增回归。

在线错误实际写在 `papers/maritime/logs/errors.jsonl`。日志目录按原 `.gitignore` 忽略；Actions 将其作为 artifact 保存。

原 `daily_arxiv_cross_filter.py`、`filter_keywords.json`、遥感 HTML 和两个旧 workflow 保留。独立存储不读写遥感 Issues/日报；无 API 模式仅需标准库，不调用付费 API，不下载 PDF，不自动控制 DeepSeek，不推送上游。

## 功能清单

- 最近 N 天、单日补跑、指定专题或全部四专题检索；原官方 API 传输与请求级重试复用，分页间至少 3 秒。扫描超限明确失败，不默默截断。
- A/B/C/D 多标签、主专题、独立应用场景标签；标题/摘要证据、概念组封顶、共同概念加分与排除条件。D 必须有方法及潜在视觉/感知联系，海事词不是入选前提。
- 四档相关性和命中解释、配置指纹。仅启发式排序，不评创新性。
- arXiv ID 去版本去重，原始标题/摘要/作者/日期/版本/链接、首次和最近检索时间与检索范围保留。日期补跑合并历史；旧版本不覆盖更新的元信息，人工分析保留。
- JSON 候选库和结构化 Markdown 日报，主专题数量、高度相关数量、原始英文摘要、可展开中文阅读提示；日报最多 25 篇，其余可在网页候选库查看。
- 静态阅读页按日期/专题/等级筛选、分数/发布日期排序、搜索标题/摘要/作者/命中词、原文与 PDF 链接。
- 自动填入论文 Prompt；剪贴板失败时手动复制。DeepSeek 由用户操作，需上传 PDF，不假设能从链接读取全文。
- Markdown 粘贴、本浏览器保存、五档状态、单篇 Markdown 导出、JSON 全量备份和合并恢复；CLI 导入后静态页面读取仓库分析。所有分析作为安全文本呈现。
- 无 Token 环境检查、仅重新评分、重建全部日报和网站、阅读备份导入导出。初始空库明确提示尚未成功检索。
- 独立 GitHub Actions：UTC 01:20 / 北京时间 09:20，每次回看 7 天；手动日期补跑；显式 contents: write，用内置 Token 更新当前 Fork；推送失败 job 明确失败，失败日志保留 14 天。

按用户详细研究兴趣定义实现四专题；任务后文“三专题”视为旧版本描述，A/B/C 重点、D 前沿拓展。

## 实际执行与测试结果

开发运行环境：Windows PowerShell、Python 3.13.5、Node 24.15.0。以下命令真实执行：

| 验证 | 结果 |
|---|---|
| `python skills/rs-paper-pipeline/scripts/cli.py maritime --action doctor` | 成功，无 Key 必要条件 |
| `python -S .../cli.py maritime --action doctor`（测试内，环境 Key 置空） | 成功，连 site-packages/旧 PyGithub 依赖均不需要 |
| `python .../cli.py maritime --action site` | 成功，生成初始空静态库 |
| `python -m unittest discover -s tests -p test_maritime.py` | 14/14 通过 |
| `node --test tests/maritime.test.cjs` | 6/6 通过 |
| `python -m unittest discover -s skills/rs-paper-pipeline/tests` | 原流水线 49/49 通过 |
| 原根目录 `test_report_site.py` | 2/2 通过（与新测试合并 discover 中运行） |
| `node --test tests/report-loading.test.cjs` | 原网页 8/8 通过 |
| `git diff --check` | 通过 |
| 本地 HTTP + 实际浏览器访问 `maritime.html` | 页面、四专题下拉框、排序/搜索、备份按钮、初始空库布局正常加载 |

共 79 项测试通过（14 新 Python + 6 新 JS + 49 原流水线 + 2 原网站 + 8 原前端）。新增测试覆盖四专题、无 maritime 的通用方法、泛词排除与概念组封顶、ID 版本与旧式 ID、分页/元信息、错误 feed/扫描上限、重复检索/补跑/旧版本、失败不发布空日报、成功空日报、无 LLM/GitHub Token、Markdown/JSON 导入导出、网页日期/专题/等级/作者搜索/排序、精确 Prompt、事件触发保存状态与分析、备份恢复、损坏备份保护和安全文本显示。模拟论文只在测试和临时目录中，未进入实际库。

实际浏览器检查的是初始空库页面；有论文的完整交互通过 Node DOM 适配器测试，**不是使用真实论文完成的浏览器端到端验收**。没有调用 DeepSeek 或验证其输出，没有在 GitHub 执行新 workflow 或部署 Pages。

## 一次实际检索

真实尝试的短时有界命令：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --days 7 --page-size 2000 --max-pages 1 --retries 1 --timeout 8
```

检索范围：2026-10-06 至 2026-10-12，全部 A/B/C/D。官方 export.arxiv.org 及 arxiv.org 端点 urllib 超时，curl 备用传输同样超时（其中一次收到 301 后未取得响应体），最终退出码 1，错误日志已保存。

**候选数量：未知；各专题入选数：未知；真实入选示例：无可验证结果。** 当前存储记录数 0 仅表示尚未获取数据，不代表这些日期没有相关论文。没有将网络限制导致的失败归类为模拟成功或真实在线成功，也没有用其他网站论文替代官方查询结果。

## 用户运行与部署

正常检索包含原客户端较长重试，遵照用户习惯不代为启动。工作目录 `D:\desktop\code\paper\RS-PaperClaw`：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --days 7
python -m http.server 8000 --directory docs --bind 127.0.0.1
```

打开 `http://127.0.0.1:8000/maritime.html`。数据输出、专题配置、补跑/评分/日报/分析导入、代理说明、Fork 和 Pages 的具体步骤详见 `MARITIME_README.md`。

在自己的 Fork 提交本次文件 → 允许 Actions 读写权限 → 手动运行 Personal Papers (No LLM API) → 核查日志与提交 → Pages 选择默认分支 `/docs` → 访问 `https://用户名.github.io/仓库名/maritime.html`。原两个调度不自动禁用，可由用户在 Fork 上关闭。没有创建 Fork、提交 git commit、push、PR 或修改上游。

## 限制与后续

1. 在线网络限制仍待在用户可访问 arXiv 的网络或 GitHub runner 上验证；当前不能确认候选量、检索召回率和评分实用性。首次真实检索后应人工检查入选与不相关候选，再调关键词/权重。
2. 规则会误检/漏检，不具备阅读全文、可靠质量评价或创新性判断；排除规则较保守，需定期维护。广义同义词仍受配置召回边界约束。
3. 提交日期与公告日期不同；有公告延迟或修订，7 天重叠回看降低遗漏但不保证无遗漏。按原始发布日期归档；更新日期另行保存。
4. 同步为手动 JSON 导入/CLI/仓库提交；localStorage 不跨设备同步。站点公开部署意味着提交进 docs 的人工分析也公开，个人阅读资料可仅留本地。
5. JSON 与静态页一次加载全库，适用于个人规模；没有数据库、分页后端、账户或并发写锁，避免同时运行两个本地写入进程。单文件原子写入，不提供跨多个输出文件的事务。
6. 分析展示 Markdown 原文，不渲染数学公式或 HTML；阅读长报告可导出给 Markdown 编辑器。重新评分会更新历史规则评价，不保存每次规则运行的完整快照。
7. 新 Actions/YAML 已实现但未在 GitHub runner 实跑；真实 push 权限、Pages 刷新和定时可靠性需 Fork 手动触发确认。工作流更新静态数据不会替用户部署其他托管服务。

后续无需为了基本检索和整理接入 LLM API。若以后希望自动全文阅读、中文摘要或更细语义筛选，可以沿稳定论文 ID/原文元信息/reading 字段添加可选层，不需重抓整个库；本次不实现 API 接入。

## 2026-10-12 HTTP 500 排查更新

用户实际运行默认命令收到连续 HTTP 500，说明当时请求获得了错误响应，不能简单归因于完全无法访问 arXiv。另做一次短时简单查询 `all:electron`、`max_results=1`，官方 API 成功返回 Atom XML；原四专题合并日期查询 URL 长 1512 字符，在 8 秒有界请求中超时。这些证据尚不足以证明 HTTP 500 是由检索复杂度引起。

已将 maritime 检索改成按专题串行发起较小查询，并保持至少 3 秒间隔；全部请求完成后才合并归档，部分成功不会生成完整成功日报。新模式默认重试从 6 降为 3。共享客户端增加可选 500/502/504 备用端点处理，仅新专题模式开启，旧模式行为保持；429/503 不扩散至其他传输。错误信息增加响应正文。

新增三项回归（分专题请求、后续专题失败时不发布部分库、可选 500 fallback），17 项 maritime Python 测试和 8 项原 arXiv 客户端测试通过。简单查询成功不代表最新论文专题检索已成功；此时实际归档仍为空。另新增 `start-maritime.cmd` 与 `preview_maritime.py` 供用户自行启动持续网页服务，文件和端口的短时 `--check` 验证通过。

随后专题 A 拆分查询（URL 长 449 字符）在一次最多 12 秒的请求中成功返回 Atom XML，证明该次官方专题 API 访问成功，仍不据此断言合并查询失败的唯一原因。

实际归档验证命令 `python skills/rs-paper-pipeline/scripts/cli.py maritime --days 7 --topic A --retries 1 --timeout 12 --max-pages 1` 随后成功（exit 0）。第一个端点读取超时，备用官方端点返回完整 63 篇候选，均已保存。日期范围 2026-10-06 至 2026-10-12，各日候选数 11/20/23/9/0/0/0，各日入选 8/16/10/7/0/0/0；后三天是在本次 A 查询成功返回范围内无候选，不能据此概括全部四专题。真实结果已进入 `papers/maritime/library.json`、`daily_reports/maritime/202610/` 和 `docs/maritime-data/`，用户启动阅读服务后刷新即可浏览。

实际入选示例（标题保持接口原文）：

- [2610.11113](https://arxiv.org/abs/2610.11113)：DiscoVL: Unveiling Disentangled C ross-Modal Representation Learning via Orthogonal Adversarial Regularization for V ision-Language Models。
- [2610.13056](https://arxiv.org/abs/2610.13056)：A4-MR: Abnormality-aware Anatomical Alignment for MR（医学场景，需人工判断迁移价值，规则分数不代表直接海事相关）。
- [2610.09700](https://arxiv.org/abs/2610.09700)：What Makes Synthetic Hard Negatives Work in Vision-Language Pretraining?
