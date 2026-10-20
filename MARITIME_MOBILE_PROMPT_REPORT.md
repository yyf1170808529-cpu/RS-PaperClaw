# 手机每日精选 Prompt 功能交付

日期：2026-10-20。

## 实现

- 每篇每日精选在“原文”“阅读与笔记”旁增加小型 `Prompt` 按钮。点击直接调用浏览器剪贴板并显示“已复制”；权限拒绝或不支持时展开只读文本框，可长按全选复制。默认不展开Prompt。
- 将桌面现有 `makePrompt()` 原样移到 `docs/maritime_prompt.js`，桌面和每日精选调用同一个函数。继续读取 `skills/rs-paper-pipeline/scripts/prompts/maritime_analysis.md`，未修改模板及13项精读要求。有可信PDF链接时保留全文精读结构；没有PDF时按原桌面逻辑截取全文限制说明，请用户提供全文，不凭摘要编造方法和实验。
- 新增 `docs/maritime_daily_prompt.js`。标题、作者、发布日期、arXiv、DOI、正式原文、来源、PDF及完整英文摘要均来自当前论文自己的元数据，缺失字段沿用“暂未获取”。日常页面内嵌所需的5篇元数据及原模板，无需下载整个论文库，也不调用模型API。
- 修改 `services/mobile_digest.py`（实际路径在 `skills/rs-paper-pipeline/scripts/` 下）：以后自动生成的日报JSON保留Prompt所需元数据，HTML自动加载共享函数和复制交互。历史档案通过稳定ID及别名从本地主库补齐缺失字段，不借用其他论文内容；重建HTML时保留归档中的标题及完整摘要。
- 已升级2026-10-14至2026-10-20的7个归档HTML和当前每日精选页，归档脚本相对路径正确。10月17日原归档只有2篇，仍保留2篇及2个按钮，不改变历史入选结果。论文主库、原有日报JSON及译文未因本次重建改变。
- 桌面页面加载共享模块后继续原有功能；收藏、笔记、导出、AI筛选及Argos翻译逻辑均未修改。新增/修改脚本带缓存版本参数，无需清除浏览器数据。

## 测试

- Python：`python -m unittest discover -s tests`，136项通过。
- Node：`node --test tests/*.test.cjs`，37项通过。
- 新增测试覆盖：按钮准确复制当前论文、有PDF时13项完整模板、无PDF时全文请求、剪贴板拒绝/缺失时只读文本框、原模板完全一致、身份/别名匹配、缺失元数据不串篇、将来生成日报的字段完整性、历史HTML重建不修改归档JSON及安全转义。
- 原有收藏、双页面笔记联动、JSON/Markdown/TXT导出、筛选和阅读功能回归通过。`git diff --check`通过。

## 真实部署与访问

功能提交：[37815f4](https://github.com/yyf1170808529-cpu/RS-PaperClaw/commit/37815f40db47d0ea02d56ff6b69fea75ae6f10be)。

实际Pages任务：[39390893973](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39390893973)，completed/success，部署SHA与功能提交一致。

部署后使用手机Safari User-Agent真实HTTPS读取当前日报、完整库入口、两个新增脚本、桌面脚本及7个历史日报HTML，均与提交内容一致。当前每日精选日期2026-10-20，5篇对应5个按钮，ID依次为：2610.26090、2609.38116、2609.25860、2610.09511、2609.24152。每篇内嵌作者、日期和完整摘要，模板与仓库原文件一致。归档页按钮数依次为5、5、5、2、5、5、5。

线上核验不是仅检查Actions状态；还实际比对了HTML、脚本和每篇Prompt元数据。复制及权限回退交互由Node执行DOM交互测试验证，未将其冒充用户实体手机的剪贴板权限验收。

页面：[每日精选](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html?v=3.8.2)。

刷新页面后点击任一论文的Prompt，粘贴到ChatGPT或DeepSeek网页版。如果无法自动复制，使用展开的只读文本框。浏览器无法读取PDF链接时，仍需自行提供全文。本次未重新检索、重新AI审核或重新翻译，新增付费API调用为0。
