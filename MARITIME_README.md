# 个人科研论文追踪：无 LLM API 模式

保留 RS-PaperClaw 原遥感模式，新增独立模式。Python 3.10+、标准库即可；不需安装原 requirements、OpenClaw、GPU、Docker、数据库或任何 API Key。不会调用 LLM、不下载 PDF、不创建 Issue、不推送上游。

## Windows 快速开始

**先打开页面：双击仓库根目录的 `start-maritime.cmd`。** 它会启动本地服务并打开默认浏览器。请保持弹出的命令行窗口打开；关闭窗口或按 Ctrl+C 后，网页地址会显示“拒绝建立连接”。这个本地地址仅在你的电脑上、服务运行期间可用，尚未部署成公开网站。

若双击后提示 Python 不存在，请在 PowerShell 运行 `python --version` 检查 Python 安装。若提示端口占用，可执行：

```powershell
cd D:\desktop\code\paper\RS-PaperClaw
.\start-maritime.cmd --port 8001
```

此时浏览器地址为 `http://127.0.0.1:8001/maritime.html`。首次尚未检索成功时页面显示空库，是正常状态；页面启动和获取论文是两个步骤。

**再获取论文：保持网页服务窗口打开，另开一个 PowerShell 窗口执行下方检索命令。** 等命令结束并确认成功，再刷新阅读页。开发环境最初曾超时，后续拆分查询并切换备用端点后，专题 A 已获取 63 篇真实候选、41 篇规则入选；完整四专题仍需运行下方命令。出现 `ERROR` 时不要把旧数据或空库理解为当天没有论文。错误日志位于 `papers/maritime/logs/errors.jsonl`。

在 PowerShell 中进入仓库根目录（本次路径 `D:\desktop\code\paper\RS-PaperClaw`）：

```powershell
cd D:\desktop\code\paper\RS-PaperClaw
python skills/rs-paper-pipeline/scripts/cli.py maritime --action doctor
python skills/rs-paper-pipeline/scripts/cli.py maritime --days 7
```

第二条是正常在线检索命令，可能因 arXiv 限流和原客户端重试耗时较长，请自行运行。输出位于 `papers/maritime/library.json`、`daily_reports/maritime/YYYYMM/YYYYMMDD.md`、`docs/maritime-data/`。失败退出码为 1，错误位于 `papers/maritime/logs/errors.jsonl`，不会把失败写成无论文日报。正常命令每页 100、最多 30 页；到达上限且仍有候选时明确失败，可以缩短日期或增加 `--max-pages`。通过 `RS_PROXY_URL` 配置可用代理，或原 `ARXIV_API_URL` 配置官方接口地址；新模式始终使用 query API，不受旧模式 `ARXIV_SOURCE=oai` 影响。

若能访问 arXiv 网页但出现 HTTP 500：网页与 query API 是不同入口，不能据此判断全部网络不可用。现版本已将四专题拆成四次较小的检索，默认每请求重试 3 次；500/502/504 耗尽后尝试备用官方端点，429/503 仍保留原限流处理。错误会记录服务器响应正文。可以先用单专题试运行，成功后再执行全部专题：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --days 7 --topic A --retries 1 --timeout 20
```

这条命令可能仍有分页与端点切换，请等待最终结果。拆分请求不保证上游服务器恢复；任一请求失败时，整次检索不会发布部分成功日报。

```powershell
# 指定日期补跑；日期是原始提交日期，不是网页公告批次
python skills/rs-paper-pipeline/scripts/cli.py maritime --date 20261010
# 按专题检索，可重复传入（A/B/C/D）
python skills/rs-paper-pipeline/scripts/cli.py maritime --days 7 --topic A --topic C
# 仅重算本地评分，不访问网络；同时重建日报与网页
python skills/rs-paper-pipeline/scripts/cli.py maritime --action rescore
# 重新生成全部历史日报和网站数据，不访问网络
python skills/rs-paper-pipeline/scripts/cli.py maritime --action digest
python skills/rs-paper-pipeline/scripts/cli.py maritime --action site
```

不在指定日期返回论文是一次成功的空检索，和网络失败不同。重叠检索用于补充公告延迟。按论文原始发布日期归入日报；同一天按专题补跑合并候选和已检索范围，不删旧记录。无新结果也不会抹掉历史记录。arXiv 版本 ID 去掉 `v数字` 后唯一存储；原始版本号、首次/最近检索时间、检索范围保留。重算评分会更新所有历史日报的规则评价，原论文、日期身份与人工分析保持。

## 阅读页

启动本地服务（这是持续运行程序，请自行启动，Ctrl+C 结束）：

```powershell
python -m http.server 8000 --directory docs --bind 127.0.0.1
```

打开 [个人阅读页](http://127.0.0.1:8000/maritime.html)。请使用 HTTP/HTTPS，直接双击 HTML 的 `file://` 模式不能可靠获取 JSON 或使用剪贴板。原 `index.html` 保留。

全部日期是本地候选库中的入选论文，可按日期、多个标签之一、相关性等级和作者/标题/摘要搜索。默认按规则分数排序；可改为发布日期排序。不相关候选默认隐藏，可选“不相关候选”审查排除规则。每个日报最多推荐 25 篇，网页库保留全部候选；日期栏显示候选、入选、各主专题和高度相关统计，并链接 Markdown 日报。

阅读流程：复制某篇论文 Prompt → 打开 [DeepSeek 网页](https://chat.deepseek.com/) → 粘贴 Prompt 并上传 PDF → 将输出 Markdown 粘回论文的分析区 → 保存分析。剪贴板不可用时可展开 Prompt 手动复制。模板位于 `skills/rs-paper-pipeline/scripts/prompts/maritime_analysis.md`，同时打包进静态 JSON，无额外网页依赖。

分析以安全的 Markdown 原文展示，保留公式、文本和链接原文；不执行 HTML、脚本或外部 Markdown 渲染库。支持五种阅读状态。浏览器 localStorage 仅属于当前站点和当前浏览器；更换端口、浏览器、设备或清理数据均不会自动同步。请定期“导出 JSON 备份”，可以在另一浏览器导入。导入按 ID 合并，冲突以导入内容为准。网页支持保留未知 ID 的阅读记录，CLI 为避免错配会拒绝未知论文，并在报错前不写入任何记录。

将阅读成果保存到仓库并用于其他设备的静态页面：

```powershell
# 网页导出的 JSON：同时导入分析和阅读状态
python skills/rs-paper-pipeline/scripts/cli.py maritime --action import --file C:\Users\yyf\Downloads\maritime-readings.json
# 单篇 Markdown（ID 替换为库中真实论文 ID）；保留已存状态
python skills/rs-paper-pipeline/scripts/cli.py maritime --action import --id 2610.12345 --file .\analysis.md
# 导出仓库中的分析/状态备份
python skills/rs-paper-pipeline/scripts/cli.py maritime --action export --file .\readings-backup.json
```

导入后自动更新网页。仓库 `reading` 是基础记录，浏览器的本地记录优先，若想恢复到最新仓库记录，可以先备份，再将 CLI 导出的 JSON 导入网页。同一论文本地状态与分析组合保存。Markdown 单篇导出导出当前输入框内容，即使尚未保存。

## 配置与评分

`skills/rs-paper-pipeline/scripts/config/maritime/` 中 `A.json/B.json/C.json/D.json` 独立维护名字、具体任务检索组合、概念组、所需证据组；`rules.json` 配置标题权重 5、摘要权重 2、概念组封顶 7、共同概念加分 3、排除短语、场景标签、场景优先加分、等级阈值和日报数量上限。

- A：多模态感知与信息融合，至少两个概念组。
- B：计算机视觉与图像智能处理，需明确视觉任务，可保留较弱任务证据。
- C：目标关联与时空动态理解，需关联任务/动态证据并有另一概念组。
- D：通用深度学习与多模态基础方法，必须同时具备方法和视觉/感知/匹配等迁移联系。

应用标签独立于研究专题，海事/交通只提高排序，不是入选条件。一个关键词只计算标题或摘要较高的权重，同组命中封顶；主专题为证据分数最高的专题，其他匹配专题全部保留。等级阈值：高度相关 ≥20、方法可借鉴 ≥12、一般相关 ≥5；存在排除短语或无必要证据则不相关。分数不是论文质量、创新性、实验强度或真实可迁移性评价。规则存在漏检和误检，应人工复核并调整配置。

任务描述后半部多处“三专题”与第二部分详细的 A/B/C/D 定义不一致；本实现按完整的四专题定义，D 为前沿方法拓展。原 `filter_keywords.json` 和 `daily_arxiv_cross_filter.py` 不替换，避免破坏遥感行为。

## 个人 Fork 与 Actions

1. 在 GitHub 创建你自己的 Fork，把本次改动提交至该 Fork 的默认分支。不要将提交推往 `thinson/RS-PaperClaw`。
2. Fork 的 Actions 页面允许工作流运行。在 Settings → Actions → General 中允许仓库读写权限（组织策略禁止时需管理员开启）。新工作流明确 `contents: write`，仅用 checkout 的内置 `GITHUB_TOKEN` 推送当前 Fork；无 LLM secrets，无自定义 GitHub Token。
3. 手动运行 **Personal Papers (No LLM API)**，可选日期或最近天数。定时每天 UTC 01:20（北京时间 09:20），默认回看 7 天。Actions 的定时可能延迟，不承诺精确时刻。原遥感工作流原样保留；不使用原模式时，可在 Fork Actions 页面自行禁用两个旧工作流。
4. 检查成功日志、提交和 `docs/maritime-data/library.json`。请求级重试沿用原客户端；上游失败本次 job 失败并保存日志，下一次重叠日期检索会补充。不会在失败后提交空日报。Push 无写权限或发生冲突会明确失败；未加无限 push 重试。
5. Settings → Pages → Deploy from a branch → 默认分支 `/docs`。入口为 `https://你的用户名.github.io/仓库名/maritime.html`。本次没有部署、推送或自动创建 Fork。

Actions 日志 artifact 保留 14 天，库文件长期保留。原部署方式是分支 `/docs`；若 fork 使用其他部署配置，请让其发布整个 docs 目录。持续变更静态数据的提交是否立即触发 Pages，由仓库现有 Pages 配置决定，可在 Pages 部署列表核查。

## 验证

```powershell
python -m unittest discover -s tests -p test_maritime.py
node --test tests/maritime.test.cjs
python -m unittest discover -s skills/rs-paper-pipeline/tests
node --test tests/report-loading.test.cjs
```

Node 仅用于前端开发测试，运行系统无需 Node。测试论文仅在临时目录中使用。当前真实在线检索情况详见 `MARITIME_FINAL_REPORT.md`；未获取真实论文时页面为空，不放入模拟论文。
