# V3.4 DeepSeek API论文筛选试验报告

日期：2026-10-14。基于V3.3现有规则，只添加独立试验层；主库、来源资格、手机正式日报均未修改。

## 实际调用与结论

官方鉴权、模型列表和生成请求均实际成功，模型deepseek-flash，显式thinking=disabled。50篇全为真实库记录，全部取得有效JSON及可在干净摘要中定位的证据。累计13次生成请求，含证据拒收后的复核；不是模拟验收。

**暂不建议全面启用AI日报排序。** 语义筛选能识别部分宽泛关键词误检，但重点推荐阈值表现过严；尚无用户人工标签，无法证明Precision提升。正式手机日报继续采用原规则。

## 用量、计价与预算

- 实际输入tokens：57479（缓存命中3840，未命中53639）。
- 实际输出tokens：21279；合计78758。
- 按各请求created时间、实际用量与官方峰谷价计算：**人民币0.1388318元**。本次均在2026-10-14 13:00—13:10北京时间空闲时段。
- 按高峰价格保守记账：0.2776636元，低于2元上限；剩余未决费用预留0。费用包含失败校验及复核，不只统计最终成功结果。
- 各轮余额接口观察差额为0，最终核验仍为0。因此上面的费用是实际tokens对应的官方计价额，**不是已经从账户账单核验的扣款**；不能将余额暂未变化解释为永久免费。账单实际扣款仍需平台对账。
- 官方依据：[模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)、[非思考与JSON参数](https://api-docs.deepseek.com/api/create-chat-completion/)、[余额接口](https://api-docs.deepseek.com/api/get-user-balance/)。
- 原始usage、请求ID、创建时间和价格上界写入私有账本；5篇共用一次请求，无法精确把费用拆为每篇，未虚构单篇tokens。公开results.json保留用量证据，不含密钥和账户余额。

预算在发送前按UTF-8输入上界及max_tokens输出上界预留；POST不自动重试。超时可能已计费，保留预留额度并停止。预算按北京时间每日记账，第二阶段共用账本。缓存指纹包括题名、干净摘要、偏好、模型、规则及已核验来源信息；成功结果复用，本次最终续跑49篇直接命中缓存。

预算约束是本机/该Actions运行环境的账本，不是DeepSeek账户级服务端封顶；本机与Actions缓存不共享，不应同时运行两边并把它理解为全账户2元。价格配置已于本轮核对；后续官方改价需同步更新。

## 样本与比较口径

样本为直接场景12、方法迁移12、低相关12、易误判12、补充2，共50。使用既有资源/失效硬规则筛出研究论文，排除数据集、软件、确认失效与没有可用英文摘要的记录。样本含不满足正式推荐质量要求的诊断对照：AI相关不等于能够发布。

没有英文摘要的记录不送API；先使用已有enrich流程补全再参与试验。本次50篇已有可用干净摘要，未额外联网批量补摘要或下载PDF。

下表“原规则”是现有rank_key在**同一50篇抽样库**中的探索排序，包含普通候选，不是现有手机实际发布榜。前5即前5行，前10为完整表。两栏均受同一抽样范围限制，不代表全库召回率。

|位次|原规则排序|AI语义排序（未应用正式发布门槛）|
|---:|---|---|
|1|Examining Racial and Gender Bias in CLIP via Explainability-Based Visual Attention Analysis · 规则12|MarShip-DET: A Frequency-Aware Multi-Scale Fusion Algorithm for Ship Detection in Maritime Remote Sensing Imagery · 重点推荐，直接4/5、迁移3/5|
|2|CmIVTP: Cross-Modal Interaction-Based Vessel Trajectory Prediction for Maritime Intelligence · 规则26|When LiDAR Fades, Radar Takes Over: LiDAR Reliability-Aware Adaptive Localization Under Airborne Obscurants · 候选，直接3/5、迁移5/5|
|3|Maritime Infrared Ship Detection in AAV Imagery Based on Two-Stage Region-Segmentation-Guided Learning Network · 规则18|Toward Novel-Class Generalization for SAR Few-Shot Object Detection via Self-Supervised Learning · 候选，直接3/5、迁移4/5|
|4|Onboard Marine Anomaly Detection on $Φ$sat-2: From Simulation-Based Development to In-Orbit Demonstration · 规则0|A Multi-Modal Framework for Detecting Physical–Digital Container Identity Drift in Global Logistics · 候选，直接3/5、迁移4/5|
|5|IRSTD-Agent: Agentic Infrared Small Target Detection via Zoom-Guided Interaction Learning · 规则16|ROSETTA: Rotation Subspace Estimation for Training-free Transmodal Alignment · 候选，直接3/5、迁移4/5|
|6|Toward Novel-Class Generalization for SAR Few-Shot Object Detection via Self-Supervised Learning · 规则28|Maritime Infrared Ship Detection in AAV Imagery Based on Two-Stage Region-Segmentation-Guided Learning Network · 候选，直接3/5、迁移3/5|
|7|ConPro: Contrast Projection Pretraining for Label-Efficient Vessel Segmentation in DSA Sequences · 规则12|Semantic-Guided Diffusion for UAV Maritime Target Detection: Fusing RGB -Thermal Registration with Contextual Feature Modulation · 候选，直接3/5、迁移3/5|
|8|CONFIDENCE-WEIGHTED MID-LEVEL LIDAR–STEREO FUSION WITH HYBRID PCA-K-MEANS CLUSTERING FOR MARITIME 3D OBJECT DETECTION · 规则20|CmIVTP: Cross-Modal Interaction-Based Vessel Trajectory Prediction for Maritime Intelligence · 候选，直接3/5、迁移3/5|
|9|Bridging Modalities and Tasks: A Unified Hierarchical ViT for SAR-to-Optical Translation and Semantic Segmentation · 规则17|Structure-Aware Matching for Robust UAV Thermal-to-Satellite Geo-Localization · 候选，直接2/5、迁移4/5|
|10|Semantic-Guided Diffusion for UAV Maritime Target Detection: Fusing RGB -Thermal Registration with Contextual Feature Modulation · 规则16|Acoustics-YOLO: A Multiscale Feature Fusion-Based Method for Small-Target Sonar Image Detection in Shallow-Water Environments · 候选，直接2/5、迁移4/5|

前5重合0篇，前10重合4篇；换位本身不证明质量提升。样本中原硬规则正式推荐资格通过5篇；AI判断重点推荐1、候选27、不推荐22。将AI重点与硬规则取交集后，本样本可发布重点为**0篇**。不能用AI唯一重点推荐绕过未核验期刊门槛。

## 具体差异与需人工复核的案例

- ConPro: Contrast Projection Pretraining for Label-Efficient Vessel Segmentation in DSA Sequences（2609.30043）：vessel实际是医学血管。AI判不推荐，直接0、迁移2。这是候选库误检识别例，不是旧手机日报已经发布了它。
- CLIP种族/性别偏差解释分析（10.1609/aies.v9i2.43211）：规则探索排序靠前，AI判不推荐，因任务偏差分析而非船舶检测/跨传感器关联。
- CmIVTP（2605.26524）：原规则26分、水路正式资格通过；AI识别AIS-CCTV关系，但因任务重心是轨迹预测降为候选。与本轮“降低纯轨迹预测”偏好一致，同时也可能丢失其中关联模块，需用户确认。
- Maritime Infrared Ship Detection（10.1109/tim.2025.3559575）：船舶视觉检测属用户明确关注项，AI却因不是AIS关联给候选。**疑似过度偏重AIS导致错误降级**，不能据此认定模型更优。
- MarShip-DET（10.3390/s26165295）：AI唯一重点推荐，题目和摘要的船舶检测方法证据具体，但原质量资格未通过；正式重点榜仍不采用，不让模型猜期刊分区。
- 医学细胞/细胞核分割能耗指标（2610.10324）：几次返回的证据未通过逐字引用校验，均未缓存为成功；最终真实重试返回可校验证据，判不推荐。必须继续保持严格证据校验，不能因为JSON合法就信任模型。

这些是摘要层面的观察及待确认错降级例；没有人工真值，无法给真实误推荐/误排除率，也没有把模型判断当真值。

## 50篇完整结果与证据

每篇的完整任务、limitations、confidence和逐字证据在 [results.json](evaluations/maritime-v3-4/results.json)。inference=true的解释是迁移推断，不是论文事实。下表为全部结果索引。

|ID|题名|分层|规则分|直接/迁移|AI决定|中文理由|
|---|---|---|---:|---|---|---|
|doi:10.1109/tim.2025.3559575|Maritime Infrared Ship Detection in AAV Imagery Based on Two-Stage Region-Segmentation-Guided Learning Network|direct|18|3/5 · 3/5|候选|海上红外船舶检测，有分割、特征编码和注意力机制，可迁移至视觉船舶感知，但无AIS或跨模态关联，直接相关中等。|
|2610.11735|Onboard Marine Anomaly Detection on $Φ$sat-2: From Simulation-Based Development to In-Orbit Demonstration|direct|0|2/5 · 2/5|候选|海事遥感异常检测，含自监督特征编码，但任务偏在轨异常检测，与AIS关联和船舶视觉检测核心方向距离较远。|
|2610.05342|IRSTD-Agent: Agentic Infrared Small Target Detection via Zoom-Guided Interaction Learning|direct|16|2/5 · 3/5|候选|红外小目标检测智能体，含多模态大模型和视觉工具搜索，间接可迁移至跨模态目标定位，但无AIS关联，直接相关较低。|
|doi:10.3837/tiis.2026.09.009|Toward Novel-Class Generalization for SAR Few-Shot Object Detection via Self-Supervised Learning|direct|28|3/5 · 4/5|候选|SAR少样本目标检测，自监督和特征交互方法对跨模态表征、缺失模态和鲁棒感知有借鉴价值，但未涉及AIS关联，直接相关中等。|
|2609.30043|ConPro: Contrast Projection Pretraining for Label-Efficient Vessel Segmentation in DSA Sequences|direct|12|0/5 · 2/5|不推荐|医学血管分割自监督预训练，属于明确降级的不相关医学研究，仅时序自监督目标有微弱迁移价值，直接相关不足。|
|doi:10.35631/jistm.1144016|CONFIDENCE-WEIGHTED MID-LEVEL LIDAR–STEREO FUSION WITH HYBRID PCA-K-MEANS CLUSTERING FOR MARITIME 3D OBJECT DETECTION|direct|20|2/5 · 3/5|候选|海事多传感器中层融合，涉及跨模态特征交互与不确定性，与多传感器融合偏好相关，但非AIS关联或轨迹匹配，迁移价值中等。|
|2609.04726|Bridging Modalities and Tasks: A Unified Hierarchical ViT for SAR-to-Optical Translation and Semantic Segmentation|direct|17|2/5 · 3/5|候选|跨模态表征与分割学习，涉及条件注入与不确定性加权，可迁移至跨模态对齐，但非直接AIS关联，海事属性有限。|
|doi:10.32894/kujss.2026.172069.1330|Semantic-Guided Diffusion for UAV Maritime Target Detection: Fusing RGB -Thermal Registration with Contextual Feature Modulation|direct|16|3/5 · 3/5|候选|海事RGB-热红外配准与融合，涉及跨模态对齐和语义调制，与跨模态匹配偏好相关，但非AIS关联，迁移价值中等。|
|doi:10.22266/ijies2026.0930.71|GA-SAR-Det: A Multi-scale YOLOv11 Architecture for Small and Densely Distributed SAR Ship Target Detection|direct|17|1/5 · 2/5|不推荐|SAR船舶检测架构改进，与AIS关联、跨模态对齐或轨迹匹配无关，与用户优先主题直接相关度低。|
|doi:10.7716/aem.v15i3.4232|DE-MFM-YOLO: A YOLO-Based Network with Detail-Enhanced Convolution and Modulated Feature Fusion for Multi-Scale Ship Detection in SAR Images|direct|18|1/5 · 2/5|不推荐|SAR船舶检测的YOLO改进，与AIS关联、跨模态对齐或轨迹匹配无直接关系，不符合优先主题。|
|doi:10.3390/s26165295|MarShip-DET: A Frequency-Aware Multi-Scale Fusion Algorithm for Ship Detection in Maritime Remote Sensing Imagery|direct|17|4/5 · 3/5|重点推荐|直接面向船舶视觉检测，方法含多尺度融合、边缘感知与注意力机制，与船舶视觉检测方向高度相关，具备迁移价值。|
|doi:10.48084/etasr.19710|A Multi-Modal Framework for Detecting Physical–Digital Container Identity Drift in Global Logistics|direct|10|3/5 · 4/5|候选|涉及AIS、视觉交叉模态一致性匹配，与视觉-AIS关联和跨模态对齐方向相关，但任务偏向物流身份验证，迁移价值中等。|
|doi:10.1609/aies.v9i2.43211|Examining Racial and Gender Bias in CLIP via Explainability-Based Visual Attention Analysis|transfer|12|0/5 · 2/5|不推荐|主题为CLIP偏见与可解释性分析，与船舶视觉、AIS关联、多传感器融合等优先方向无直接关系，迁移价值低。|
|doi:10.56201/ijcsmt.vol.11.no9.2025.pg22.38|A Survey of Object Detection and Classification in Video Using Deep Learning Approaches|transfer|19|2/5 · 3/5|候选|视频目标检测综述，覆盖YOLO、Transformer、多模态视频理解等方向，对船舶视觉检测有背景参考价值，但无具体技术贡献。|
|2610.13259|Beyond a Single Crop: Contextualized Embeddings for Player Re-Identification|transfer|18|1/5 · 3/5|候选|方法涉及上下文嵌入、跨帧关联和视觉语言模型，可迁移到船舶多目标关联与跨模态表征，但领域偏离较大。|
|doi:10.1038/s41598-026-74573-6|Efficient dual-attention fusion with gated feed-forward learning for image restoration under compound degradations|transfer|17|1/5 · 3/5|不推荐|图像恢复任务，无海事情境，与AIS关联等优先方向无直接证据，仅注意力融合可轻度借鉴，不重点推荐。|
|2610.12901|JMT-YOLO: Multi-task Domain Adaptation via Segmentation-Guided Consistency Learning|transfer|14|1/5 · 4/5|候选|域自适应目标检测，方法（辅助分割、掩码一致性、多尺度上下文）可迁移至船舶视觉检测与跨模态对齐，但无直接海事证据。|
|2610.12835|Structure-Aware Matching for Robust UAV Thermal-to-Satellite Geo-Localization|transfer|12|2/5 · 4/5|候选|跨模态匹配框架，结构增强与模态感知仿射重映射可迁移至视觉-AIS关联与跨模态对齐，但非直接海事任务。|
|2610.13547|MOSAIC: Multi-Scale Object-Centric Slot Adaptation with Image-Guided Prototype Conditioning for Remote Sensing Image Super-Resolution|transfer|12|1/5 · 3/5|不推荐|遥感图像超分辨率，无直接海事证据，方法（槽注意力、原型记忆）仅间接可借鉴，不重点推荐。|
|doi:10.1088/1361-6501/aeb27f|Acoustics-YOLO: A Multiscale Feature Fusion-Based Method for Small-Target Sonar Image Detection in Shallow-Water Environments|transfer|12|2/5 · 4/5|候选|水下声纳小目标检测，属海事感知，多尺度融合与背景抑制可迁移至船舶视觉检测，但非直接关联任务。|
|2610.11113|DiscoVL: Unveiling Disentangled C ross-Modal Representation Learning via Orthogonal Adversarial Regularization for V ision-Language Models|transfer|27|2/5 · 3/5|候选|跨模态对齐与鲁棒表征方法与视觉-语言任务相关，可迁移到视觉-AIS跨模态表征，但摘要缺乏海事场景验证。|
|2610.11342|Point-Focused Attention Meets Context-Scan State Space: Robust Biological Visual Perception for Point Cloud Representation|transfer|22|2/5 · 3/5|候选|点云表征与注意力/状态空间方法可能迁移到雷达点云处理，但与AIS关联和船舶检测无直接证据。|
|2610.12393|HRIL: Learning Multimodal Synergy via Higher-Order Tensor Modeling|transfer|19|2/5 · 3/5|候选|多模态协同表征方法可能用于视觉-AIS跨模态对齐，但缺乏海事场景证据，迁移性需额外验证。|
|doi:10.1038/s41598-026-74070-w|SAR object detection via adaptive shift-wise downsampling and frequency-spatially modulated feature fusion|transfer|15|2/5 · 4/5|候选|SAR目标检测的特征融合与抗噪声方法可迁移到海上雷达/视觉检测，但与AIS关联无直接证据。|
|2610.12871|ROSETTA: Rotation Subspace Estimation for Training-free Transmodal Alignment|low|10|3/5 · 4/5|候选|跨模态对齐与传感器异构匹配方法可直接借鉴到雷达-AIS或视觉-AIS关联，但缺乏海事验证。|
|2610.12897|AD-SRF: Attack-Defense Semantic Reinforcement for Multi-Modal Image Fusion|low|10|2/5 · 3/5|候选|多模态融合与跨模态检索有方法迁移参考，但非海事/雷达-AIS场景，直接相关有限，仅作候选。|
|2610.13697|Improving Semantic Coverage in AI Test & Evaluation through Generative Augmentation|low|9|2/5 · 4/5|候选|跨模态零样本标注与扩散增强可启发缺失模态/鲁棒感知数据增强，但直接海事相关性低，列为候选。|
|2610.13788|When LiDAR Fades, Radar Takes Over: LiDAR Reliability-Aware Adaptive Localization Under Airborne Obscurants|low|9|3/5 · 5/5|候选|雷达-其他模态可靠性自适应切换与跨模态特征对多传感器融合有较高迁移价值，但直接海事相关中等。|
|2610.13687|X-AVDD: Cross-Attentive Audio-Visual Dataset Distillation|low|7|1/5 · 2/5|不推荐|音视频蒸馏与目标应用链较远，仅有弱跨模态对齐概念，直接海事相关极低，不建议优先。|
|2610.13072|AV-FlowEdit: Training-Free Prompt-Driven Audio-Visual Editing with Event-Aware Spectral Trajectory Preservation|low|7|1/5 · 2/5|不推荐|音视频编辑与雷达-AIS/船舶视觉任务无关，仅共享宽泛跨模态术语，不建议纳入优先筛选。|
|2610.11669|Perceptually Grounded and Semantics-Aware Evaluation for Holistic Co-Speech Gesture Generation|low|11|1/5 · 3/5|不推荐|主题为语音手势生成评估，仅含跨模态同步与语义保留等通用评估思路，无海事感知、AIS或视觉-AIS关联证据，与优先方向关联弱，降级处理。|
|2610.11672|CloudEar: Integrating Perceptual, Diagnostic, and Cross-Modal Evidence for Music Evaluation|low|10|1/5 · 2/5|不推荐|音乐评估框架，仅提及跨模态对齐但无视觉-AIS、雷达或船舶感知证据，与优先方向无实质关联，按低优先级处理。|
|2610.11526|MSGAT: Multi-Head Spiking Graph Attention with Similarity-Space Fusion for Image-Text Retrieval|low|9|2/5 · 3/5|候选|提出相似度空间融合对齐与多粒度匹配，思路可迁移至视觉-AIS跨模态对齐，但任务为图文检索且无海事证据，仅作候选参考。|
|2610.12458|OmniCapBench: A Deep-Structured Evaluation Framework for Fine-Grained Audio-Visual Captioning|low|7|1/5 · 3/5|不推荐|音视频字幕评估基准，虽涉及跨模态错位和细粒度评估，但无海事感知证据，与视觉-AIS关联仅属弱方法启发，降级处理。|
|2610.11685|HI3D 3.0 (Twinkle3D): Object-specific 3D Asset Generation with High Resolution|low|7|1/5 · 2/5|不推荐|图像到3D生成工作，仅含图像-3D跨模态交互，与船舶视觉、AIS关联或检测分割无实质关联，不属优先方向。|
|2610.11230|CORAL: Cross-modal Vector Retrieval via Incremental Graph Construction at Scale|low|0|1/5 · 3/5|候选|跨模态检索索引系统，含查询模态特征增量融入与动态更新，方法上对跨模态检索基础设施有潜在迁移价值，但无海事场景与感知任务证据，直接相关性低。|
|2605.26524|CmIVTP: Cross-Modal Interaction-Based Vessel Trajectory Prediction for Maritime Intelligence|tricky|26|3/5 · 3/5|候选|海事AIS-CCTV跨模态交互与数据集构建与视觉-AIS关联方向相关，但核心任务是轨迹预测，属低优先级，故降级为候选。|
|2610.09907|FedSSMCoOp: SSM Encoders for light-weight Federated Prompt Learning for Few-shot Classification|tricky|16|1/5 · 2/5|不推荐|属医学影像联邦分类，跨模态为视觉-语言提示学习，无海事感知证据，迁移与直接相关性均低。|
|2610.07694|Anchor-driven Multi-modal Multi-scale Expert Selection for Survival Prediction|tricky|9|0/5 · 2/5|不推荐|属不相关医学生存预测，虽含跨模态对齐结构，但模态与场景均无海事相关性，直接相关为0。|
|2610.05157|Cross-Modal Contrastive Learning for the Retrieval of Immunotherapy-Associated Molecular Signatures from Histopathology|tricky|20|0/5 · 2/5|不推荐|属不相关医学跨模态检索，跨模态对比对齐思路或有借鉴，但场景与模态完全无海事相关性。|
|2609.17068|Beyond In-Distribution Metrics: A Systematic Out-of-Distribution Evaluation of Congenital Heart Disease Segmentation|tricky|0|0/5 · 2/5|不推荐|医学图像分割OOD评估，与海事雷达/AIS、跨模态关联及船舶视觉检测无直接关系，仅自监督与域适配有弱迁移参考。|
|doi:10.1088/1361-6501/aeb1e7|BiMars: bilateral heterogeneous network with Cross-Branch Alignment for Martian terrain semantic segmentation|tricky|12|1/5 · 3/5|候选|火星语义分割，跨分支对齐与多策略融合对异质特征融合、光照鲁棒有参考价值；但与雷达/AIS、船舶视觉任务直接相关低。|
|doi:10.1038/s41598-026-74213-z|HEA-GAN for high-fidelity low-light image enhancement and degradation-aware image augmentation using a hybrid deep learning and GAN framework|tricky|15|2/5 · 3/5|候选|低光增强与可控数据增广方法可迁移至船舶视觉图像增强与鲁棒训练，但非海事任务且为概念框架，直接相关性有限。|
|2610.10324|Performance at What Cost? A Sustainability-Aware Performance Index for Cell and Nucleus Instance Segmentation|tricky|10|0/5 · 2/5|不推荐|生物医学细胞分割评测，与海事雷达/视觉-AIS关联、跨模态匹配及船舶感知无直接关系；仅能耗度量可泛泛迁移，无具体海事方法证据。|
|2610.06232|AUTOPILOT An Advanced Perception, Localization and Path Planning Techniques for Autonomous Vehicles Using YOLOv7 and MiDaS|tricky|9|2/5 · 2/5|候选|YOLO与MiDaS组合可用于船舶视觉检测和深度估计参考，但场景为陆上自动驾驶且含低优先级路径规划，直接相关性中等偏低。|
|2609.33948|TrackFlood: Relocating Latency Attacks from NMS-Free Detectors to Real-Time Trackers|tricky|14|1/5 · 2/5|不推荐|主题为NMS-free检测器延迟攻击与跟踪关联防御，属对抗鲁棒性，与Radar-AIS/视觉-AIS关联及跨模态匹配直接相关低，仅跟踪关联概念可弱迁移。|
|doi:10.1007/s44163-026-02133-y|Perception and decision optimization of basketball robot based on YOLOv5 and LiDAR fusion|tricky|19|1/5 · 2/5|不推荐|任务为篮球机器人视觉-激光雷达融合与轨迹预测决策，虽涉及多传感器融合但场景与AIS/海事无关，且含低优先轨迹预测，直接相关低。|
|doi:10.3389/frobt.2026.1859583|A review of full-stack autonomous obstacle avoidance for assistive robots for the disabled|tricky|9|1/5 · 1/5|不推荐|综述聚焦辅助机器人多传感器融合与避障规划，包含路径规划等低优先方向，且无海事/AIS内容，方法证据仅为综述性描述，直接相关与迁移价值均低。|
|2610.13783|UkrMeme: Multimodal Explainable Persuasion Detection in Ukrainian Memes|fill|12|0/5 · 1/5|不推荐|任务为乌克兰迷因说服检测，视觉-语言模型跨模态但面向社交媒体NLP，与Radar-AIS/视觉-AIS关联及海事感知无直接关系，迁移仅限泛化跨模态概念。|
|2610.13282|Frontend-Assisted Large Audio-Language Models for SLT2026 SmartGlasses Challenge|fill|0|0/5 · 0/5|不推荐|主题为智能眼镜挑战赛的语音识别系统，属纯语音/NLP，无视觉、雷达或AIS关联技术，直接相关与迁移价值均为零。|

## 人工评估及使用

人工表：[human-labels.csv](evaluations/maritime-v3-4/human-labels.csv)，50行。将human_relevant_0_or_1填1（按你的兴趣值得阅读全文）或0（不值得），human_notes记录误检/错误降级。模型结果不是人工真值，空白不会自动补为AI决定；续跑保留人工标签。

目前人工标签0行，Precision@5与Precision@10均为null，不能声称提高。填好表后运行：

```powershell
cd D:\desktop\code\paper\RS-PaperClaw
python skills/rs-paper-pipeline/scripts/cli.py maritime --action score-ai-labels
```

输出human-metrics.json；只在该榜前K篇人工标签齐全时计算Precision。建议特别检查CmIVTP、红外船舶检测和方法迁移候选，再决定是否提高AI决策阈值的容忍度。

再做同样50篇独立试验（成功缓存复用；偏好/摘要改变会使相关缓存失效）：

```powershell
python skills/rs-paper-pipeline/scripts/cli.py maritime --action evaluate-ai --sample-size 50 --ai-budget 2
```

偏好和预算：skills/rs-paper-pipeline/scripts/config/maritime/semantic.json。默认自动日更及手机AI排序关闭；evaluate-ai是明确手动发起的试验，不受关闭自动模式影响。stage_two.enabled默认false，只对前10复核，可配置官方模型，共用预算；本轮第二阶段未启用，未将模拟测试称为真实Pro验收。

本轮尚未连接AI到正式手机生成器或每天检索：enabled/mobile_ai_enabled保留关闭，**改开关本身不代表已完成上线**。待人工验证后再做单独的有限候选日更接入，不能贸然替换。

密钥已配置到Windows用户环境，程序从DEEPSEEK_API_KEY读取；不写入仓库、网页、缓存或日志。GitHub另有手动试验工作流，无schedule：仓库Settings → Secrets and variables → Actions → New repository secret，名称DEEPSEEK_API_KEY，再从Actions手动触发。GitHub Secret本轮未自动设置，云端API试验未执行。

## 验证与文件

Python主要回归78项通过、原技能49项通过、Node22项通过。单元测试中的模拟响应只测试预算与校验，真实验收来自官方13次请求。主库、网页library.json和手机HTML的git diff为空，原无API模式不要求Key，也没有替换正式日报。

新增clients/deepseek_client.py、services/semantic_evaluation.py、config/maritime/semantic.json、手动Actions工作流、test_maritime_v3_4.py及评估表。maritime.py只增加显式试验及人工打分入口；修正了V3.3日报测试中在“下一天空日报”之后才检查摘要元素的测试顺序。

私有缓存/账本/余额在papers/maritime/private/deepseek（Git忽略）；真实运行日志v34-real-api*.log（Git忽略）。公开评估结果不包含余额或密钥。

建议：先做人工标注与偏好校准，再考虑只对新入选候选调用Flash；暂不将本轮排名作为每日自动正式发布。真实创新性仍不能仅凭摘要可靠确认，API语义层评价的是任务相关性、证据和潜在迁移价值。
