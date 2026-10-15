# V3.7.1 本地摘要翻译修复

日期：2026-10-15。已恢复 **DeepSeek 只做筛选和推荐理由，摘要使用 Argos 本地离线翻译**。没有重新检索或重做 AI 筛选，没有下载新模型。

## 修复与真实翻译

V3.7 的 `chosen_zh(daily=True)` 隐藏了已有 Argos 译文，并让付费翻译成为精选译文来源。本轮移除该限制及 DeepSeek 翻译请求代码。两页统一按“人工修订 → 哈希匹配并通过检查的 Argos 缓存 → 本地 Argos 补全 → 失败时保留英文和具体原因”处理；旧 DeepSeek 译文保留在历史字段中。

使用原 `.venv-maritime`、原 `translate-en_zh-1_9` 模型和 CPU。五篇都实际进入过本地模型翻译，最终全部成功：

| 论文 ID | 最终来源 | 译文字符数 | 检查 |
|---|---|---:|---|
| `2610.01750` FFBL-Coop | Argos 本地 | 447 | 通过 |
| `2609.37162` RGB-T Tracking | Argos 本地 | 587 | 通过 |
| `2609.37243` Codebook Distillation | Argos 本地 | 336 | 通过 |
| `2610.09700` SNAP | Argos 本地 | 362 | 通过 |
| `2610.07928` Dynamic Alignment | Argos 本地 | 460 | 通过 |

修复了旧译文中的 fuse→“保险丝”、困难负样本等术语问题；扩展 `translation_terms.json`，保护模型名、数据集、公式、数字、百分比与缩写。增加数值、模型名、空片段及连续重复文本检查，复用现有 Argos 解码器的备选结果，未引入新模型。真实执行中还修正了英文 five→5 的误判、短指标 AP 的保护和代码 URL 中模型名的重复计数。早期失败结果保留在翻译历史及本地日志，最终无失败论文。

最后一次实译补齐 2 篇、复用 3 篇；随后单独验证为 **缓存命中 5、重译 0、失败 0**。手机日报五篇的中文内容与完整库 `display_abstract_zh` 逐字一致，英文摘要与 AI 评价未变。保护字段前后比较通过；收藏与笔记存储键、备份格式不变。

**本轮 DeepSeek 翻译请求新增 0 次，翻译费用 ¥0。** 每次真实翻译前后的原 DeepSeek 费用账本哈希一致；测试还禁止翻译阶段调用其 API 客户端。模型离线执行，未刷新或下载资源。首次沙箱读取模型文件受限，使用正常权限访问现有模型后解决，没有修改模型权限或重装模型。

## 日常与云端

`translate_selected()` 只把当天五篇送入原本地翻译 worker，不受历史队列篇数抢占；成功缓存直接复用，人工译文不覆盖。失败会保存论文 ID、错误类型和具体原因，日报与完整库保留英文并显示原因，不再只写“中文译文暂未完成”。普通历史翻译入口保留。

GitHub Actions 原本已安装 CPU 翻译依赖、缓存 `papers/maritime/private/translation` 并运行 `install-model`：缓存存在时复用同一英译中模型，独立环境缺失时准备原模型。本轮为准备步骤增加失败提示与 `argos-setup.log` 归档；运行阶段逐篇记录结果，不将失败统计为完成。云端与 Windows 使用同一套本地翻译代码，翻译模块已不包含 DeepSeek 请求。本轮未触发完整云端检索任务，以遵守“不重新检索/筛选”；未声称实测了全新 Ubuntu 环境安装。

## 验收与发布

Python **101 项通过**，Node **25 项通过**。覆盖缓存复用、daily 不隐藏 Argos、人工优先、五篇优先队列、零翻译 API、数值/术语/模型名/重复检查、失败原因展示和完整库中文显示。

代码提交 `bc6afd9`、`b78d2e0`；公开数据通过原白名单同步，提交 `6016dc57bca34cc3c172fa2859bb946f934a1032`，未使用 force push。历史 Markdown 日报未覆盖，私有模型、PDF、日志、分析未提交。

[Pages 运行 38740589900](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/38740589900) 实际完成，结论为 success。[手机日报](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html)、日报 JSON 和完整库 JSON 均实测 HTTP 200。线上逐篇比较五条中文摘要均完全一致，来源均为 argos、错误字段为空；日报 HTML 有五个论文区块，没有“本地中文翻译未完成”提示。本次为真实公开 URL 验收，未代替用户实体手机操作。

主要修改：`selected_translation.py`、`maritime_reading.py`、`maritime_update.py`、`mobile_digest.py`、`maritime.py`、`translation_terms.json`、`docs/maritime.js`、原 Actions 工作流和相关测试；更新五篇翻译及静态数据。Argos 仍可能出现生硬语序和语义误译，结构检查不能保证学术翻译完全准确，页面保留英文供对照。
