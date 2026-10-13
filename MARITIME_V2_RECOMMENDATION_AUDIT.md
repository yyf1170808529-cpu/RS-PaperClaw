# V2 真实候选推荐适配审查

日期：2026-10-12。抽样为当前真实库按原关键词分数最高的25篇（均来自原arXiv库）。人工式适配检查依据标题与已查看的摘要片段，不审查全文创新性、实验准确性或论文质量；下表意见由代理根据阅读兴趣给出，不是用户本人评价。没有将机器规则统计冒充语义创新性判断。

|论文ID与标题|旧分数|V2组|摘要层检查意见|
|---|---:|---|---|
|2610.09174 · Context-aware Attention-based Gaussian Mixture Models for Vehicular Trajectory Prediction|29|candidate|车辆轨迹预测为主；候选保留，移出重点推荐合适。|
|2610.11113 · DiscoVL: Unveiling Disentangled C ross-Modal Representation Learning via Orthogonal Adversarial Regularization for V ision-Language Models|27|preprints|跨模态表征/适配与通用方法联系明确；可少量保留预印本，真实迁移价值待全文。|
|2610.10238 · Geometry-Supervised Visual Representation Learning for Multi-Phenotype Lesion Interpretation in Medical VLMs|27|candidate|医学病灶解释；通用表征词不能把它提升成海事重点，候选保留。|
|2610.07954 · Revisiting Numerical Forecasting Models for Language-Based Trajectory Prediction|25|candidate|语言化轨迹预测；与视觉感知任务较间接，降低首页优先级。|
|2610.13056 · A4-MR: Abnormality-aware Anatomical Alignment for MR|24|candidate|MR解剖配准；只作跨域备选，不因为对齐/基础模型词多高推荐。|
|2610.09700 · What Makes Synthetic Hard Negatives Work in Vision-Language Pretraining?|24|preprints|视觉语言预训练中的负样本方法；有方法借鉴联系，可少量拓展。|
|2610.10286 · $Δ$Representation: Geometry Supervised Representation Learning of Phenotypes via Counterfactual Reasoning for Medical VLMs|24|candidate|医学VLM病变表征；候选保留，重点降级。|
|2610.09287 · Scaling subjects in cross-modal alignment: video decoding with EEG foundation model|23|candidate|EEG视觉解码，传感器语义与海事感知不同；候选保留。|
|2610.12747 · Trajectory Prediction for Autonomous Driving in Road Construction Zones Using Human-in-the-Loop Driving Data|23|candidate|施工区自车轨迹预测；交通相关但不是当前视觉/目标关联主线。|
|2610.11580 · Uncertainty-Aware Optimization for Physics-Aware Highway Trajectory Prediction|23|candidate|公路轨迹预测与不确定性；一般候选，不能据不确定性词升级。|
|2610.11826 · From Suppression to Repair: Mitigating Object Hallucination in Large Vision-Language Models via Localized Distribution Alignment|23|candidate|VLM生成内容的物体幻觉；任务联系较间接，候选适当。|
|2610.09863 · Global Average Precision for Representation Learning|22|preprints|表征学习评价指标；可借鉴，但是否值得首页应看与感知实验的联系，当前预印本定位偏宽。|
|2610.08573 · Sparse2comm: Towards Robust Cooperative 3D Object Detection|22|preprints|协同3D目标检测、带宽与不可靠通信；感知联系强，适合前沿拓展。|
|2610.08192 · MacJEPA: Missingness-Robust Audio-Visual Recognition from Untrimmed Egocentric Videos|22|candidate|缺失模态的音视频行为识别；有融合借鉴价值，当前候选定位较保守，可人工关注。|
|2610.07928 · Dynamic Alignment and Calibration for Multimodal Learning|22|preprints|动态跨模态对齐和校准；与融合方法联系明确，少量预印本合适。|
|2610.12936 · Evo-World: A Lightweight Vision-Language-Action Model with Future Motion Prediction via Optical-Flow Supervision|22|candidate|VLA机器人控制和未来运动；视觉线索可借鉴，但不宜按主线感知强推。|
|2610.11342 · Point-Focused Attention Meets Context-Scan State Space: Robust Biological Visual Perception for Point Cloud Representation|22|preprints|点云局部/全局表征；通用3D感知联系明确，预印本候选可保留。|
|2610.07946 · Adapting Vision-Language-Action Models to Unknown Visual Disruptions During Execution|22|candidate|执行中VLA适配视觉干扰；鲁棒方法可借鉴，动作策略背景下保守推荐合理。|
|2610.13915 · Where to Look Matters: Rethinking Sub-Volume Sampling in 3D Medical Self-supervised Learning|21|candidate|3D医学自监督裁剪；方法可备选，移出重点。|
|2610.11918 · From Surface to Depth: Towards Cognitive Appraisal Reasoning in Multimodal Emotion Understanding|21|candidate|多模态情绪理解；与当前目标感知联系弱，候选。|
|2610.11553 · EVIE: Evidence-Vector-Informed Embeddings for Visual Document Retrieval|21|candidate|视觉文档检索；不等于目标关联，候选。|
|2610.11329 · PathLang: A Language-Centered Benchmark for Vision-Language Models in Computational Pathology|20|candidate|计算病理VLM基准；医学领域，移出重点。|
|2610.10391 · MOTIP2: Spatial Priors for End-to-End Multi-Object Tracking|20|preprints|端到端多目标跟踪与空间身份约束；主线联系强，预印本合适。|
|2610.12421 · Beyond Spatio-Temporal Priors: A Generalizable Approach for Dense Correspondence Matching|20|candidate|稠密对应匹配；有迁移潜力，但编辑/生成场景联系需全文核查，候选不删除。|
|2610.09355 · Multimodal LLMs Can Learn to Read Brain Signals: A Vision--Language Model for Unified Multi-Task EEG Decoding|19|candidate|EEG跨任务解码；候选，不因多模态词高分强推。|

发现：旧前列的医学、EEG及纯轨迹工作现在退到一般候选；协同检测、跨模态对齐、MOT等方法仍在库内。有些缺失模态方法被压得较保守，而通用表征指标仍可能进入预印本组，规则不能替代人工判断。

额外正式样例：TIM海事红外船舶检测（10.1109/TIM.2025.3559575）符合JIF OR门槛且与海事感知直接相关；ByteTrack（10.1007/978-3-031-20047-2_1）有ECCV官方论文集证据，作为历史关联方法样例保留。两者不冒充最近7天论文。

当前只有少量重点推荐，不能证明“重点前10篇至少8篇相关”或海事70–80%比例目标已达到。建议用户在6–12个月正式来源回溯完成后再做一次20–30篇抽查。
