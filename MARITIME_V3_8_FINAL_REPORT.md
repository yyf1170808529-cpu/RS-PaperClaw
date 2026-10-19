# V3.8 一键云端更新、后备池与Argos修复

2026-10-19。

## 数据恢复

本地更新从3607增到3681，74个新增稳定ID已完整备份。远端3616条中已包含9篇，缺65篇；已按现有稳定ID合并入口补入65篇，主库3681，74篇全部可解析且无重复ID。来源历史、有效译文、有效AI缓存保留；本地HEAD、远端HEAD、patch、主库、缓存、日志及日报位于被Git忽略的 papers/maritime/private/v3_8_backup，另有可恢复stash。没有reset --hard或force push。未发现代码冲突，产生的数据冲突通过远端基底与本地备份按记录合并，未以旧库覆盖。公开核验清单：docs/maritime-data/recovery-v3-8.json。远端最终核验待发布后补充。

## 单一写入端

原按钮先本地抓取及付费，然后要求HEAD与远端完全相等才审核及推送，云端自动提交即导致本地停止。现在默认按钮调用cloud_update，同一系统GitHub凭据通过API触发maritime-no-api.yml，使用request_id定位任务；等待结束后检查Pages和同run_id的公开update-result.json，分别显示来源、AI、翻译、同步、发布日期与Pages。无需Git版本一致，不把Token保存到代码或日志。

本机没有gh，但Git Credential Manager现有凭据已真实通过API授权检查。默认不再进行本地检索、付费或写入正式库；--local保留维护入口，--resume恢复云端阶段。没有工作区修改时才允许自行pull --ff-only，不自动覆盖用户开发文件。

云端仍使用同一run_update，09:20北京时间检索、15:20恢复阶段；串行concurrency，第二次跳过检索。来源部分失败但完整五篇和翻译成功，不再人为exit1；翻译失败与日报不足仍明确报错，Pages另行核验。

## 持久化后备池

新增ai-reserve.json，按稳定ID保存fingerprint、review_version=2、合格状态、推送日期及冷却可用状态。所有选择仍重新核验当前摘要/偏好指纹和发表硬条件。目标15篇后备，日常补审不再选到五篇立刻停止，而是继续在每日60篇及2元预算内积累；来源门槛、模型和预算不变。semantic-attempts.json保存当日已付费尝试的指纹，失败/不兼容结果也不在同日重复付费。成功缓存继续复用。

当前修复前后备为0，云端实跑后的数量待追加，不声称已积累15篇。

## Argos真实根因及修复

实际运行环境Argos1.11.0、Stanza1.10.1、CTranslate2 4.8.3。使用已下载translate-en_zh.argosmodel中原始resources.json复现：stanza.pipeline.core.Pipeline第242行→maintain_processor_list→stanza.resources.common.add_mwt第193行 resources[lang][PACKAGES] → KeyError: packages。旧资源无packages；进一步指定旧tokenizer时发现旧权重缺feat_dropout，单纯补JSON字段仍无法推理。完整堆栈保存在私有 original-packages-trace.log。

未删除/重装模型。旧资源路径只改用不需模型的英文边界分句，仍由原Argos解码器、原英译中权重完成翻译；新资源继续使用离线Stanza，不联网刷新资源。明确固定已验收运行依赖版本，云端复用旧模型缓存并增加真实英译中冒烟测试。XDG及Stanza目录继续在私有translation中，spawn子进程继承环境。

原始资源兼容路径真实推理：“We propose a robust object tracking method.” → “我们提出一个强大的物体跟踪方法。”；正式translate_one也产生中文并通过校验。

精选翻译与历史规则筛选分开：selected=True不再因旧assessment excluded而跳过已AI合格精选；人工与有效哈希缓存优先，worker超时不覆盖已成功译文。加入稠密对应、度量深度、点云、异常检测等术语。DeepSeek摘要翻译API调用0次。

## 今日五篇真实翻译

2610.16749、2609.29235、2610.14513、2610.12871、2610.14598均实际执行Argos，5成功0失败；术语补充后按有效缓存/重译规则再次通过。当前手机日报2026-10-19，五篇均有中文和英文，原JSON中五篇english_only已修复。Argos为机器译文，不将形式校验通过冒充语义完美；部分句式仍生硬，可人工对照原文。

## 页面与测试

保留收藏/笔记/导出和全部存储键，无正常就绪或版本调试文字。每五分钟仅检查轻量publication-status.json，有新日期时出现用户可点击的更新链接，不自动刷新，不丢未保存笔记。

Python110项、Node32项通过，YAML可解析，git diff --check通过。新增回归覆盖默认桌面调用只触发云端、同一工作流输入、后备指纹及推送冷却、同日失败指纹不重复付费。真实Windows Argos冒烟及今日五篇已验证。

## 云端真实验收

新版完整工作流及Pages执行证据待本次真实运行后追加，当前不能用本地测试代替Ubuntu验收。
