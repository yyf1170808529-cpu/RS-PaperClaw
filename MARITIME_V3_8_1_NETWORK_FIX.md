# V3.8.1 桌面断线恢复与网页诊断

日期：2026-10-20。

## 故障定位

原 `cloud_update.py` 的 GitHub API、任务轮询和 github.io 检查直接调用 `urlopen`，没有重试。仅在 `wait_for_run()` 返回之后写 `latest-cloud.json`，所以触发已被接受、但查询遇到 SSL EOF 时，桌面既退出又没有可恢复的触发凭据。下次双击无条件重新 dispatch，有重复付费任务风险。原桌面入口还把本地异常统称为“云端更新未完成”。

用户提供的历史异常是 `SSL: UNEXPECTED_EOF_WHILE_READING`；本轮未获得当时完整网络抓包或异常堆栈，不能断言由 GitHub、代理或运营商中的哪一方断开。当前真实直连测试 GitHub API 和 Pages HTML 都返回 HTTP 200；通过现有本机代理也成功。未重现当时真实服务端 SSL 故障，故障恢复通过明确标注的本地异常注入验证。

## 修改

- `skills/rs-paper-pipeline/scripts/services/cloud_update.py`：共用 HTTPS 读取函数，单次超时25秒；GET 最多尝试3次，指数退避2、4秒。SSL EOF、连接/读取失败及408/5xx临时错误可重试；429和带限流头的403单独识别，尊重较长冷却时间，不无限等待或无限重试。401/权限403不反复重试。保留 TLS 证书验证。
- workflow_dispatch POST 不自动重试。发送之前将 request_id 和提交时间写入被 Git 忽略的 `papers/maritime/private/cloud-request.json`；响应不明确时保存 `dispatch_unknown`，仅查询同一个身份。明确被拒绝的请求单独记录。
- 找到实际 run_id 后立即原子保存。重启按该 ID 查询；未找到时按精确 request_id 分页查找，首次发现等待最多45秒。首次升级也会接续最近一次已有桌面任务，避免旧版漏存回执后再次触发。状态文件损坏不自动删除或重建付费任务。
- API连接、认证、限流、任务未确认、云端失败、Pages部署失败及网页访问受阻分别输出；保留任务链接和备用日报源文件链接，不打印 Token 或响应中的敏感正文。
- Pages 核验同时检查部署提交里的 `update-result.json.github_run_id`，不再仅凭时间选取不相关部署。已经部署成功但 github.io 连接失败时，明确输出“Pages发布成功，当前网络无法验证网页访问”，保存 `awaiting_web` 供下次续查。
- 桌面离线期间如果后续任务已发布，核实原任务部署及当前网页与仓库最新数据的一致性，报告已被后续任务更新，不一直等待旧任务重新出现在首页。
- `skills/rs-paper-pipeline/scripts/update_maritime.py`：复用现有操作系统文件锁，避免两个桌面窗口同时触发；本地异常不再等同于云端失败。
- `tests/test_maritime_network.py`：新增15项针对网络恢复、身份持久化、防重复触发和Pages状态的测试。

未修改检索、DeepSeek评审、Argos翻译、五篇质量门槛、收藏、定时或写入端。未关闭证书验证、修改域名、清理浏览器数据或上传私人笔记。

## 真实云端与网页结果

1. 早上的定时任务 [39355765993](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39355765993) success；[Pages 39357123398](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39357123398) success。初次核验日期2026-10-20，5篇论文、5篇中文摘要。
2. 开始检查时，用户此前触发的桌面任务 [39376344799](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39376344799) 仍在运行。本轮没有重新触发它。它随后提交 `32f3f5e`，[Pages 39377548686](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/runs/39377548686) completed/success。
3. 上述桌面任务本身最终 failure，失败步骤为 `Report incomplete source update`。保存结果显示 Argos 失败2篇，具体为 `2609.38116`、`2609.24152` 的 `numeric_mismatch: numbers or percentages changed`；不是SSL或Pages部署失败。本轮不修改翻译逻辑或放松数值校验。
4. 最后真实 HTTPS 读取的日报日期仍为2026-10-20，5篇论文、3篇中文摘要，HTML含全部5篇标题；JSON与对应仓库提交完全一致。不能继续把早上“5篇中文”的状态当作最后一次检查结果。
5. 使用修复后的 `public_result(..., wait=False)` 分别核验最新桌面任务及被替代的早上任务，均完成网页核验，旧任务正确识别当前线上来自 `39376344799`。
6. 一次本地注入的 SSL EOF 后，程序退避2秒，第二次真实 GET 成功读取 GitHub API。此次两次请求均为 GET；这是“注入故障后恢复真实访问”，不是声称 GitHub 当时真实发生SSL错误。

本轮新 workflow_dispatch 数：**0**；DeepSeek请求数及新增API费用：**0**。真实任务中的模型费用属于此前已运行任务，不算作本轮验证费用。未为验收重跑多来源检索或付费审核。

## 测试与使用

- `python -m unittest discover -s tests`：132项通过。
- `node --test tests/*.test.cjs`：33项通过。
- `git diff --check`：通过。
- 覆盖连接前EOF、响应读取EOF、成功dispatch后的查询断线、多次轮询断线、429/502/503、长限流冷却、401/403、POST不重试、进程重启按run_id恢复、首次升级接管旧任务、双窗口锁、原任务被新日报替代、部署成功但github.io不可达及真实部署失败。

日常继续双击原“论文更新”。中断后再次双击会优先恢复未核验任务；已核验完成后再双击才进入正常的新更新。首次升级会先接续旧桌面任务。查询失败会显示原任务链接，不能据此判断云端已经停止。

如果触发响应丢失且始终找不到对应任务，客户端保留身份、不擅自重发。必须先核实 Actions 是否真的没有接收；客户端不能凭一次连接失败保证服务端没有执行。

日报：[每日精选](https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html)。
备用：[Actions](https://github.com/yyf1170808529-cpu/RS-PaperClaw/actions/workflows/maritime-no-api.yml)、[最新日报源文件](https://github.com/yyf1170808529-cpu/RS-PaperClaw/blob/main/docs/maritime-data/mobile/latest.json)。

未代替用户实体手机测试，也不能保证其当前网络始终能访问 github.io。网络恢复记录、测试输出和诊断证据仅保存在被忽略的本地private/logs目录。此次修复不涉及网页资源修改，无需为了桌面网络修复再启动一次Pages或付费论文更新。
