<div align="center">
  <img src="./docs/logo-220.png" alt="RS-PaperClaw Logo" width="120" />

# RS-PaperClaw🦞

### 遥感论文自动追踪与分析流水线

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![Status](https://img.shields.io/badge/Status-Active-2EA043)](#)
[![Workflow](https://img.shields.io/badge/Workflow-arXiv%20%E2%86%92%20Issue%20%E2%86%92%20Digest-8A2BE2)](#)
[![Pages](https://img.shields.io/badge/GitHub%20Pages-Live-b55f34)](https://thinson.github.io/RS-PaperClaw/)

**arXiv → 单篇报告 Issue → 每日汇总日报 → 可视化阅读页面**

English version: **[README_EN.md](./README_EN.md)**

新增个人科研论文库：**[简明操作指南](./简明操作指南.md)** · **[无 LLM API 模式使用说明](./MARITIME_README.md)** · **[独立阅读页](./docs/maritime.html)**。支持 A/B/C/D 多专题规则排序、本地日报、ChatGPT / DeepSeek 网页分析 Prompt、分析/阅读状态备份与 CLI 导入；原遥感流程保留。

V2：**[正式来源、双分区筛选与PDF精读操作指南](./MARITIME_V2_README.md)**。期刊门槛为 CAS 2025官方大类一区或已核实 JCR JIF Q1；离线翻译为可选模块。

</div>

---

## 🌐 在线阅读入口

- 项目主页（GitHub Pages）：**https://thinson.github.io/RS-PaperClaw/**
- CVPR 2026 GeoAI 合集：**https://thinson.github.io/RS-PaperClaw/cvpr2026_geoai.html**
- 日报归档目录：**[daily_reports/](./daily_reports/README.md)**

## 🖼️ 界面预览

| 电脑端 UI | 移动端 UI |
|---|---|
| <img src="./docs/screenshots/ui-desktop.jpg" alt="RS-PaperClaw Desktop UI" height="260" /> | <img src="./docs/screenshots/ui-mobile.jpg" alt="RS-PaperClaw Mobile UI" height="260" /> |

---

## 📰 News

- `2026-09-29`: 优化网页 UI、日报加载和阅读体验，更新桌面端与移动端预览。
- `2026-05-27`: 默认 LLM 已切换为 `deepseek-v4-flash`；同时支持其他 OpenAI-like Chat Completions 兼容模型，可通过 `LLM_MODEL` 与 `LLM_API_URL` 自定义。
- `2026-04-24`: 新增 CVPR 2026 GeoAI 论文合集页面，收录 139 篇论文（9 Oral + 20 Highlight + 110 Poster），按主题标签分类浏览。
- `2026-04-20`: README 补充项目进展时间线，便于快速了解当前维护状态。
- `2026-04-19`: GitHub Pages 前端完成一轮集中修复，包括历史日报分页加载、日期深链跳转、`More` 交互合并，以及 Papers 表格显示问题修复。
- `2026-04-17`: 单篇报告与日报已增加“单位”信息；作者展示规则同步更新，不再使用 `et al.`。
- `2026-03-05`: 当前仓库内可追溯的最早日报归档日期为 `20260305`，标志着日报归档链路已开始持续积累。

---

## ✨ 项目做什么

RS-PaperClaw 每天自动完成：

- 🔎 拉取 arXiv 候选论文（遥感相关）
- 🧠 关键词 + LLM 二级筛选
- 📝 生成 / 更新单篇阅读报告（GitHub Issue）
- 🗞️ 生成当天日报（GitHub Issue）
- 🗂️ 同步日报到 `daily_reports/YYYYMM/YYYYMMDD.md`
- 📮 推送摘要到钉钉/飞书

---

## 🎯 为什么以 Issue 为核心

- 🧭 **可追踪**：单论文单 Issue，历史与改动可回溯
- 🤝 **易协作**：评论即讨论，补充即沉淀
- ⚙️ **自动化友好**：增量流程可稳定更新同一条记录
- 🗂️ **归档闭环**：Issue 动态协作 + Markdown 静态留档

---

## 🧩 核心能力

| 模块 | 输出 |
|---|---|
| 单篇报告 | 基础信息、TL;DR、中文摘要、标签、前三页预览图、10问分析 |
| 日报生成 | 今日概况（含数量统计）、亮点、文章列表、观察 |
| 质量控制 | 过滤占位内容，保障结构完整与可读性 |
| 结果归档 | Issue + Markdown 双轨同步，便于追踪与回溯 |
| 可视化页面 | 最近日报浏览、移动端卡片视图、Issue 深读弹层 |

---

## 🗺️ 目录结构（main）

```text
RS-PaperClaw/
├── .github/workflows/                 # GitHub Actions（定时主跑 + 手动运维）
├── docs/                             # GitHub Pages 静态页面
│   ├── index.html
│   └── logo-220.png
├── daily_reports/                    # 日报归档（按年月）
│   ├── README.md
│   └── YYYYMM/YYYYMMDD.md
├── papers/previews/                  # 论文预览图（用于 Issue 展示）
├── skills/rs-paper-pipeline/         # 技能与脚本
│   ├── README.md
│   ├── SKILL.md
│   ├── .env.example
│   ├── RUNBOOK_RS_PIPELINE.md
│   ├── AGENT_GUIDE_RS_PIPELINE.md
│   └── scripts/
│       ├── cli.py
│       ├── clients/
│       ├── services/
│       ├── config/filter_keywords.json
│       └── prompts/filter_cross_prompt.md
└── README_EN.md
```

---

## 🚀 快速开始

### 0) 克隆仓库

仓库包含大量论文预览图（400MB+），如需跳过可使用轻量克隆：

```bash
# 轻量克隆（跳过 papers/previews/ 图片，约 1MB）
git clone --filter=blob:none --sparse https://github.com/thinson/RS-PaperClaw.git
cd RS-PaperClaw
git sparse-checkout set --no-cone '/*' '!papers/previews'

# 完整克隆（含全部预览图，约 400MB）
git clone https://github.com/thinson/RS-PaperClaw.git
```

### 1) 初始化

```bash
cd skills/rs-paper-pipeline
./bootstrap.sh
```

### 2) 配置 `.env`

至少填写：

- `GITHUB_TOKEN`
- `LLM_API_KEY`

可选：

- `LLM_MODEL`（默认：`deepseek-v4-flash`）
- `LLM_API_URL`（默认：`https://api.deepseek.com/chat/completions`；支持其他 OpenAI-like Chat Completions 兼容接口）
- `DINGTALK_WEBHOOK`
- `FEISHU_TARGET`
- `RS_GITHUB_REPO`

### 3) 运行当天流程

```bash
cd skills/rs-paper-pipeline
python3 scripts/cli.py run
```

### 4) 常用命令

```bash
cd skills/rs-paper-pipeline
python3 scripts/cli.py doctor
python3 scripts/cli.py filter --dry-run --date 20260317
python3 scripts/cli.py run --date 20260317 --no-notify
python3 scripts/cli.py reconcile --date 20260317 --dry-run
```

### 5) 想定制成你自己的论文系统

可以直接看：

- `skills/rs-paper-pipeline/CUSTOMIZATION_GUIDE.md`

这份文档专门说明：

- 如何改关键词和 regex
- 如何改筛选 prompt
- 如何改 `.env` 配置项
- 如何把目标仓库切到你自己的 repo
- 如何用最小风险验证改动

---

## ⏰ 定时任务（示例）

```cron
推荐直接使用仓库内工作流：

- `.github/workflows/rs-pipeline-schedule.yml`
- `.github/workflows/rs-pipeline-manual.yml`

它们会调用 `skills/rs-paper-pipeline/scripts/cli.py`，并使用仓库内的筛选配置文件。
```

---

## 📎 备注

- 默认文档语言为中文；英文请见 [README_EN.md](./README_EN.md)
- 页面部署方式：`main` 分支 + `/docs`
- 文章 list 筛选规则来自：
  - `skills/rs-paper-pipeline/scripts/config/filter_keywords.json`
  - `skills/rs-paper-pipeline/scripts/prompts/filter_cross_prompt.md`

---

## ✅ TODO
- 增加期刊来源：RSE（Remote Sensing of Environment）、ISPRS JPRS、IEEE 旗下相关期刊

---

## 🔗 Related Projects

- **papers.cool**: https://papers.cool/

---

## ⭐ Star History

<a href="https://www.star-history.com/?type=date&repos=thinson%2FRS-PaperClaw">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=thinson/RS-PaperClaw&type=date&theme=dark&legend=top-left&sealed_token=0MxBU6_td-V1EzNAbnCRYKVXLAqwKtr5RKH-HgXo8QT7XJDEMeAc-yb7ISDKomfsK5rPEYmPuDywBcC-02-GKFvrThXHHdsXhPEmrVhNkpYX5fFLAwHt7HdecdjruzRiKUL6uxUeds8qm09ZJHCCO3m30-7zp7YBPnTTM0BzAvZwHG1tnFaXxtF3L5ns" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=thinson/RS-PaperClaw&type=date&legend=top-left&sealed_token=0MxBU6_td-V1EzNAbnCRYKVXLAqwKtr5RKH-HgXo8QT7XJDEMeAc-yb7ISDKomfsK5rPEYmPuDywBcC-02-GKFvrThXHHdsXhPEmrVhNkpYX5fFLAwHt7HdecdjruzRiKUL6uxUeds8qm09ZJHCCO3m30-7zp7YBPnTTM0BzAvZwHG1tnFaXxtF3L5ns" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=thinson/RS-PaperClaw&type=date&legend=top-left&sealed_token=0MxBU6_td-V1EzNAbnCRYKVXLAqwKtr5RKH-HgXo8QT7XJDEMeAc-yb7ISDKomfsK5rPEYmPuDywBcC-02-GKFvrThXHHdsXhPEmrVhNkpYX5fFLAwHt7HdecdjruzRiKUL6uxUeds8qm09ZJHCCO3m30-7zp7YBPnTTM0BzAvZwHG1tnFaXxtF3L5ns" />
 </picture>
</a>


### 个人阅读模式：V3.1 元数据修复

日常双击桌面“论文更新”；只打开页面用 `start-maritime.cmd`。详见[简明操作指南](简明操作指南.md)。更新显示四阶段与最终退出状态，使用本地锁防止重复启动；单来源任务默认180秒上限、翻译阶段默认180秒，每次最多处理5篇新译文，成功缓存和人工修订不重翻。可用 `--task-timeout`、`--translation-timeout`、`--limit` 调整。

历史库可单独执行 `maritime --action dedup` 去重，或 `maritime --action enrich --limit 5 --timeout 15 --retries 1` 补齐缺失英文摘要。不会重新全量检索，不生成替代摘要。正式发表信息优先，旧ID别名、分析冲突和翻译缓存保留。期刊指标按ISSN/eISSN或完全匹配的核验名称统一复用；网页只显示期刊名、一区标记与实际IF。

真实修复与验证结果见 [MARITIME_V3_1_REPAIR_REPORT.md](MARITIME_V3_1_REPAIR_REPORT.md)。


### V3.2 摘要覆盖与增量维护

历史中文入口：双击 `补齐中文摘要.cmd`，或运行 `maritime --action translate-history --translation-limit 25 --batches 3 --translation-timeout 180`（使用 `.venv-maritime` 的Python）。逐篇保存，重复执行自动跳过成功缓存；`--retry-failed` 可重新尝试失败记录。日常更新优先新入选重点论文；最大篇数及时间预算可通过 `config/maritime/translation.json` 或CLI配置，不改变论文推荐配额。

`enrich` 按本地历史/缓存→已关联arXiv→Crossref→OpenAlex→有限官方出版社页面补齐。OpenAlex免费Key读取环境变量 `OPENALEX_API_KEY`，Windows也读取用户环境变量；匿名额度耗尽后暂停到服务端重置时间，缓存仍可用，不无限重试。出版社内容必须核对DOI与完整标题，只把明确可再发布的CC BY/CC0摘要写入公开库；其他可读取摘要仅存于忽略提交的私有目录，禁止绕过登录、验证码和付费墙。

顶部只显示简短更新状态，来源汇总默认折叠；检索截断、限流与失败的原始记录仍在日志。正常个人模式检索只保存元数据；PDF准备仍为用户主动操作。磁盘与真实验收见 [MARITIME_V3_2_FINAL_REPORT.md](MARITIME_V3_2_FINAL_REPORT.md)。
