# RS-PaperClaw V3.8 最终报告

日期：2026-10-19。

## 当前结论

- 原桌面“论文更新”已修正路径，默认只触发云端同一个工作流，不再先本地检索、付费、推送。
- 新增74篇全部保留：此前远端已有9篇，实际补入65篇；随后云端新增2篇，当前主库3683条。74个原ID均能在最终主库或别名中解析，未重复插入。
- 一次完整云端更新、一次修复后的恢复更新均真实成功，GitHub及Pages均核验；中间一次恢复测试失败如实保留并修复。
- 当前日报2026-10-19，5篇均有有效AI审核及Argos中文摘要；可用AI后备10篇，已达到10—20储备范围，目标仍为15篇。
- 本次两轮付费审核按API usage计价合计约¥0.8179956，254418 tokens；摘要翻译API调用0次。

入口：https://yyf1170808529-cpu.github.io/RS-PaperClaw/maritime-daily.html?v=3.8.1

## 数据备份及74篇核验

本地最新日志确认3607→3681，新增74篇；不是根据用户估计直接写74。修复前已保存本地主库、网页主库、AI缓存、译文、完整/待发布日报、HEAD、远端HEAD、Git状态及binary patch，位于Git忽略的 papers/maritime/private/v3_8_backup；另保留可恢复stash。旧快捷方式也备份到此处。

远端初始3616条，74个ID中已有9个、缺65个。以远端较新数据为基底，经既有merge_records按稳定ID补入65个，合并来源历史、别名、时间戳及有效译文/评价；未用较旧远端覆盖本地。未发现代码冲突，数据文件冲突经备份逐记录解决。没有reset --hard、force push、删除历史、清localStorage或上传私人模型/PDF/笔记。

恢复提交ad83243中的主库在GitHub API读取到的blob SHA与本地完全相同（当时39534549字节）。云端完整任务后主库3683条，恢复任务新增0条；最终再次验证原74个ID全部存在。公开清单 docs/maritime-data/recovery-v3-8.json 可核对，初始恢复库数量3681与最终3683含义不同。

## 原因与单一写入端

旧流程本地先检索，付费前要求本地HEAD等于远端HEAD，结束后又要求远端不变才能同步。云端正常提交即可让本地按钮跳过AI并停止推送；最新本地日志确实显示 cached81、processed0、Remote/local commits differ。

默认更新论文.cmd现调用services/cloud_update.py：使用环境凭据、已授权gh（若存在）或OS Git Credential Manager，不存储/打印Token；API触发maritime-no-api.yml，以唯一request_id定位本次任务，自动等待，核对本次run_id的update-result.json、最近完整日报JSON及HTML论文标题，再报告Pages成功。日志只在本机保存详细结果，控制台显示新增、AI、Argos、日期、储备和两种发布状态。

本机没有gh，但现有OS凭据已真实授权成功并完成dispatch。首次没有凭据时仅需一次 git credential-manager github login 浏览器授权，无需把密钥发到聊天里。

原D:/desktop/论文更新.lnk实际指向不存在的C:/Users/yyf/Desktop旧目录；先备份，再修正同一快捷方式为D:/desktop/code/paper/RS-PaperClaw/更新论文.cmd，目标存在，工作目录正确。没有新增第二个按钮。

云端完成后，工作区干净则自动fetch/merge --ff-only公共副本；存在开发修改或不能快进则保留本地，不阻断云端。--local仅用于本地维护，默认--no-ai且不自动推送；--sync-only限定Actions使用。手动Git开发仍可进行，不通过盲目覆盖消除代码分歧。

## 无人值守与恢复

同一工作流北京时间09:20完整检索、15:20恢复；第二次RS_RESUME_ONLY=1跳过来源检索。串行concurrency，普通按钮和schedule共用run_update、daily_evaluate、select_daily、Argos及发布保护，没有第二套推荐策略。

检索部分失败但五篇及翻译完整时，保留来源警告，不再人为把整个工作流置为failure。AI校验失败结果不入选；翻译环境错误与单篇验证错误分开记录。模型环境故障时不以五篇新英文覆盖完整日报；单篇不可翻译保留可核验原因与英文。同步失败保留生成归档，后续通过官方download-artifact恢复并按ID合并主库、来源、日期、别名、有效缓存和待发布快照，不下载旧代码覆盖当前实现。若归档含私人reading数据则拒绝自动公开。

本轮实际成功下载并合并了上一轮失败任务的公共归档；该归档来自测试阶段失败，未包含新的付费成果。恢复分支的新增记录幂等、人工译文保护另有回归测试；未故意制造线上推送断网故障。

## 持久化审核储备及成本

ai-reserve.json保存规范化paper_id、当前fingerprint、review_version=2、qualified、pushed_dates及冷却可用状态；选择前仍重核当前干净摘要/偏好指纹、可信来源、有效性和AI证据。不会把旧队列标志当作永久合格证明。新论文优先，已有合格缓存及近期/历史后备补足五篇，七天冷却，50/30/20仍为软比例。

原“达到五篇立刻停止”已改为继续积累目标15篇后备；每轮最多120篇，批次4篇，保持DeepSeek Flash、非思考和原每日2元项目预算。semantic-attempts.json记录当日已尝试的指纹；成功缓存复用，失败/超时指纹当天不反复付费，避免永远重新处理同一批。没有提高AI分数或降低来源/证据门槛。

第一轮储备从0增至5；恢复后增至10。现有目标15尚未完全达到，后续定时任务继续补库；不声称已经有15篇。日预算是本项目账本限制，不能代表整个DeepSeek账户在其他软件中的全局消费上限。上述费用是usage结合现有时段价格的计价，未冒充账户最终结算账单。

## Argos真实异常与修复

实测运行时：Argos1.11.0、Stanza1.10.1、CTranslate2 4.8.3。使用已下载translate-en_zh.argosmodel中的原始resources.json复现完整堆栈：

```
stanza/pipeline/core.py:242 → maintain_processor_list
stanza/resources/common.py:217 → add_mwt
stanza/resources/common.py:193 → resources[lang][PACKAGES]
KeyError: 'packages'
```

旧资源仅有default_processors等字段、缺packages。进一步指定旧tokenizer还出现旧权重缺feat_dropout；简单补JSON并不能解决。私有original-packages-trace.log保存真实堆栈。

没有删除或重装整个模型。原Argos解码器和英译中权重继续使用；旧Stanza资源/权重不兼容时仅替换为无需模型的英文句界分段。新资源路径用download_method=None离线Stanza，兼容不完整tokenizer缓存；不隐藏缺失翻译解码模型的错误。XDG目录、Stanza资源路径及CPU设置继续统一到私有translation目录，spawn继承环境。固定已验收依赖版本，Actions复用旧模型缓存，install-model之后必须真实推理冒烟，不能把安装成功当作可推理。

用原始报错资源真实推理：We propose a robust object tracking method. → 我们提出一个强大的物体跟踪方法。正式translate_one也输出中文并通过检查。Ubuntu完整任务及恢复任务的Prepare translation model冒烟步骤均真实success。

精选翻译不再被assessment excluded等历史规则拦截：人工优先、有效摘要哈希缓存其次，其余由Argos处理；五篇独立优先队列。worker超时不覆盖已成功译文。补充稠密对应、度量深度、点云、异常检测等术语；数字、URL、关键符号、明显错误术语是硬检查，一般表达/长度疑点仅作quality_warnings，避免隐藏全部可阅读中文。

原来的2610.16749、2609.29235、2610.14513、2610.12871、2610.14598五篇在本机全部实际完成翻译，首批5成功0失败；术语更新后二次新译2、缓存3。原译文记录仍保留。随后云端根据有效AI结果调整当日身份，并把更换入选的论文新译，最终五篇均有中文：

|paper_id|标题|来源|中文|
|---|---|---|---|
|2610.16749|The Midas Touch for Metric Depth: Interpretable Metricization for Generalizable Depth Perception|arXiv|Argos，有效摘要哈希|
|2609.29235|SARFusion: Scene-Aware Routing Fusion for Robust Camera-LiDAR 3D Object Detection|arXiv|Argos，有效摘要哈希|
|2610.13788|When LiDAR Fades, Radar Takes Over: LiDAR Reliability-Aware Adaptive Localization Under Airborne Obscurants|arXiv|Argos，有效摘要哈希|
|2609.36844|GlassFormer: Learning Real-time Glass Segmentation using Radar-Depth Fusion|arXiv|Argos，有效摘要哈希|
|2609.16535|Multimodal Emergency Vehicle Classification via Audio-Visual Transformers and Knowledge Distillation|arXiv|Argos，有效摘要哈希|

Argos为机器译文，部分句式仍生硬；结构/数字检查不等于语义完美，不以付费翻译API补救。

## 真实云端与Pages验收

|任务|结果|检索/新增|AI新增/缓存/拒收|Argos新译/缓存/失败|计价|
|---|---|---|---|---|---|
|39226498086 完整更新|success|42项：39成功、3个OpenAlex401警告；新增2|57/113/3|2/3/0|¥0.2715972|
|39228826171 首次恢复|failure|未执行业务阶段|0/0/0|未执行|0|
|39229273200 修复后恢复|success|明确not_run_resume，新增0|110/170/10|2/3/0|¥0.5463984|

中间失败的完整日志已读取：RS_RESUME_ONLY=1泄漏到测试，模拟完整检索的测试进入恢复分支。已将测试步骤环境设为0，实际恢复步骤仍为1；重新运行成功，未掩盖失败。恢复任务跳过当天已失败3个指纹，没有重复支付它们。当前仍有10份新输出校验失败被拒收，未来按预算处理，未为凑数放行。

完整更新Pages39228442727、恢复Pages39230160822均success，真实读取update-result.json的github_run_id与对应任务一致。最终静态保护/版本检查发布验收见下节。

本次手动dispatch已在云端无人值守跑通；未来schedule尚未到触发时刻，不将手动实跑冒充已观察到未来定时执行。无需电脑开机是GitHub托管工作流的执行方式。

## 页面、收藏及回归

收藏存储键、规范化ID和备份格式不变；没有清浏览器数据、上传私人笔记或更改导出。每五分钟只读取轻量publication-status.json，新日期或同日新修订只出现用户可点击的更新链接，不自动刷新，保留未保存笔记。正常页面无版本/已就绪调试文本，保留静态文件缓存参数。

Python115项、Node33项通过；YAML解析及git diff --check通过。新增覆盖默认云端入口、本地维护不付费/不推送、后备失效与冷却、同日失败不重复付费、旧资源不初始化不兼容Stanza、失败归档幂等及人工译文保护、翻译环境失败保留旧完整日报、同日版本检查保留未保存收藏笔记。真实Argos及两轮云端/Pages并非模拟返回。

未读取用户实体手机的私人存储，不把代理或Node测试冒充实体手机操作；线上内容检查以真实HTTPS页面和JSON为准。

## 文件与使用

新增services/cloud_update.py、services/cloud_recovery.py、tests/test_maritime_v3_8.py、公开ai-reserve.json/semantic-attempts.json/update-result.json/recovery-v3-8.json及本报告。上述services实际位于skills/rs-paper-pipeline/scripts/services。

修改update_maritime.py、maritime_update.py、semantic_evaluation.py、mobile_digest.py、selected_translation.py、maritime_reading.py、semantic/translation_terms配置、requirements-translation.txt、工作流、README、收藏共享脚本/页面及相关测试；重建公开日报HTML/JSON并恢复既有未同步记录。

日常只需双击原“论文更新”；等待结果后阅读手机日报。--resume为故障恢复/本次验收使用，下午定时任务会自动执行，不要求用户日常另跑命令。--local仅维护本地无付费副本，不自动发布。

## 最终静态发布

待本次最后一次无付费静态发布完成后补入精确commit/Pages证据。目标日期2026-10-19，五篇中文，储备10；没有发起第四次付费任务。
