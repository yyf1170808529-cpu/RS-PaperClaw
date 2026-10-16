# V3.7.2 收藏、笔记与导出修复报告

日期：2026-10-16。仅修改收藏、笔记、导出及页面接线；不改检索、AI评价、翻译、来源资格和每日精选名单。

## 问题复现与原因

执行实际线上旧版本脚本及 FFBL-Coop 元数据，复现两条路径（不是只测试 Set）：

1. 日报允许旧 readings 中存在不完整阅读记录，并成功写入 favorites；完整库严格校验整个备份，某篇 reading 缺少 analysis 即放弃整份读取，导致收藏显示 0。错误提示又被更新状态覆盖。
2. 完整库选择日期后，收藏结果再次被该日期 recommendation_view 过滤，非当日精选的收藏消失。

离线复现日志位于本机 papers/maritime/private/v3_7_2_reproduction.log。并未读取用户手机私人存储，无法断言其具体触发了哪一条。

首轮修复上线后，用户手机反馈仍未联动；没有将首轮部署当作验收完成。随后继续修复第三个确定的加载顺序缺陷：完整库此前等整份 library.json 下载结束才绑定筛选事件，手机慢网络期间“我的收藏”无法响应。现在收藏先从本地快照渲染，不等待主库，网络失败也可查看、编辑和导出。HTML导航及脚本带版本参数，避免旧HTML/脚本组合继续被缓存。日报新增“查看我的收藏”直达入口。

## 修复与数据保护

- 共享模块 docs/maritime_favorites.js，日报和完整库使用同一收藏存储、ID规范化、别名映射及操作组件。
- 独立键 rs-paperclaw-maritime-favorites-v2，逐篇记录，保存标题、原文、阅读链接、时间和笔记快照；多个标签页修改不同论文不会互相覆盖。
- 独立迁移旧 readings-v1 的 favorites，不依赖旧阅读记录完整性；幂等迁移，不删除旧数据。异常原文保留在恢复备份中；修复导入前另存异常旧原文。
- 收藏不受日期、专题、方向、质量、AI分数及搜索限制；缺主库记录显示快照和明确数量。ID合并保留两个笔记版本。
- 点击收藏立即保存，笔记可为空；取消收藏保留笔记，再收藏可恢复。笔记以文本节点呈现，不执行HTML。
- 原完整论文分析及阅读状态继续使用原存储，未与收藏笔记混合。
- 支持全部收藏 Markdown 导出和 JSON 完整备份恢复。按照用户后续反馈，另加“复制全部收藏文本”和“导出 TXT”；复制区可长按全选，不必下载文件。所有导出包含全部收藏，不仅是当天或当前列表。
- 私有笔记、测试备份、截图均未提交到GitHub；论文主库和日报JSON未改变。

## 实际验证

- Python：python -m unittest discover -s tests，103项通过。
- Node：node --test tests/*.test.cjs，32项通过。
- git diff --check 通过。
- Node VM中运行两页实际脚本和事件，验证收藏空笔记、双页修改中文/Markdown笔记、重开页面、别名、未知论文快照、损坏旧阅读记录、迁移幂等、JSON恢复、多标签页及大库下载挂起/失败。
- 实际浏览器本地页面：收藏FFBL-Coop和SNAP，选择日期后进入“我的收藏”显示2篇；完整库修改SNAP笔记，返回日报仍一致。实际下载Markdown包含两篇完整标题、正确arXiv链接、空笔记占位和SNAP中文笔记；样例保存在本机 papers/maritime/private/v3_7_2_export_example.md。
- 后续修复实际浏览器：主库仍显示“正在加载”时已显示“本浏览器收藏2篇”和两篇快照；点击“复制全部收藏文本”，文本区含两篇标题、链接及完整库补记，无额外Markdown标题标记。
- 首轮线上浏览器确认已加载共享模块，旧FFBL-Coop收藏迁移后显示“已收藏”。实体手机首轮反馈仍失败，已据此追加加载顺序与缓存修复；不能将代理浏览器测试冒充用户手机验收。

## 发布

首轮提交：7d5cfb7，Pages运行38906649803成功。
后续修复提交：f3b3b9e，Pages运行38907848416，completed/success。通过HTTPS实际获取 maritime.html、maritime.js、maritime_favorites.js、maritime-daily.html，规范化换行后与本地逐字一致。

本次浏览器再开线上归档日报遇到工具导航超时；不将该次尝试描述为线上完整交互验收成功。最新交互在本地真实浏览器及双页脚本测试通过，线上文件版本和部署已确认，实体手机最终联动仍待用户反馈。

入口：
- 每日精选：https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html?v=3.7.2.1
- 我的收藏：https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime.html?view=favorites&v=3.7.2.1

## 修改文件

新增：docs/maritime_favorites.js、tests/helpers/maritime-ui.cjs、tests/favorites.test.cjs、tests/test_maritime_v3_7_2.py、本报告。
修改：docs/maritime.js、docs/maritime.html、services/mobile_digest.py（实际位于 skills/rs-paper-pipeline/scripts/services/）、tests/maritime.test.cjs、docs/maritime-daily.html及既存10月14/15/16日报HTML。重渲染既有JSON，不重新选论文。

## 仍需用户确认

最终部署后请在原来的同一手机浏览器，通过日报“查看我的收藏”进入，核验此前收藏是否出现。不同浏览器、应用内浏览器及不同设备不共享localStorage；跨环境需JSON导入。不建议清缓存或清站点数据，避免丢失私人收藏。尚未直接检查用户手机存储内容，不能声称所有手机场景已验收成功。
