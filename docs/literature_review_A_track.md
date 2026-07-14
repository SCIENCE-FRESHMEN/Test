# NEURONCLAW A 赛道 Paper-to-ARM 文献调研报告

## 摘要

Paper-to-ARM 的目标不是生成普通论文摘要，而是把脑科学、神经科学、认知障碍与脑细胞外间隙（extracellular space, ECS）相关论文转换为可检查、可复用、可回放的结构化科研资产。传统 PDF 论文面向人工阅读，结论、证据、图表、实验流程、引用和局限分散在不同位置；如果直接交给单轮大模型处理，容易出现证据边界不清、原文定位缺失、模型归纳被误认为论文事实等问题。

本项目调研 2020-2026 年 AI Agent 科研自动化、结构化科研资产、证据溯源、生物医学 Agent 与 ECS 神经科学论文处理相关工作，形成三点工程结论：第一，LLM 适合作为调度与候选生成组件，但科学 claim 必须由原文摘抄和 locator 支撑；第二，科研 Agent 应采用“总控调度 + 专用工具 + Schema 校验 + Trace 回放”的流水线，而不是单轮自由文本生成；第三，ARM 资产应借鉴 FAIR 与 RO-Crate 思想，把论文事实、证据、运行步骤、局限和导出物统一封装为机器可读对象。基于上述结论，系统实现了 `literature_extract`、`reference_validator` 原始工具和 `p0_tools` 插件层，覆盖图表 caption 抽取、跨论文冲突检测、ARM 完整性校验、dry-run 评估和细粒度 trace。

ECS 论文具有特殊性：ECS 与脑内物质运输、药物递送、代谢废物清除、神经退行性疾病机制和认知障碍研究密切相关，但其测量方法、动物模型、影像证据和临床可迁移性存在明显边界。因此 Paper-to-ARM 系统必须在 `metadata`、`claims`、`limitations` 和 `provenance` 中显式保留 `ecs_related`、ECS 关键词、图表 caption 来源和人工复核标记，避免把 ECS 机制结论淹没在普通神经科学摘要中。

## 1. 检索方案

### 1.1 检索平台

本调研使用以下平台：

- PubMed：检索生物医学 AI Agent、神经科学、ECS、认知障碍和证据抽取相关论文。
- arXiv：检索 ChemCrow、AI Scientist、Agent Laboratory、BioDiscoveryAgent、RAG、ReAct 等快速发展的 Agent 和 LLM 方法。
- Web of Science / Crossref：核对 RO-Crate、FAIR、结构化科研资产、DOI 和期刊出版信息。
- 项目样例文献：`brain_ECS_review.txt`，用于验证 ECS 专项字段、caption 解析、claim/evidence 对齐和 limitations 表达。

### 1.2 时间范围

主要范围为 2020-2026 年。FAIR 原则为 2016 年基础文献，RO-Crate 为 2022 年结构化科研资产包装代表工作，虽然早于 2020 年或处于范围边界，但与 ARM 资产设计直接相关，因此纳入。

### 1.3 检索关键词

英文关键词：

`AI agent biomedical discovery`, `LLM scientific discovery`, `Paper to structured research asset`, `scientific asset packaging`, `RO-Crate`, `FAIR research data`, `evidence extraction biomedical literature`, `retrieval augmented generation evidence`, `ReAct language model`, `Agent Laboratory`, `AI Scientist`, `BioDiscoveryAgent`, `ChemCrow`, `brain extracellular space`, `ECS neuroscience`, `glymphatic clearance`, `Alzheimer extracellular space`, `knowledge graph biomedical literature`.

中文关键词：

`脑细胞外间隙`, `脑组织液`, `脑间质系统`, `脑病机制`, `科研智能体`, `文献证据溯源`, `结构化科研资产`, `知识图谱`, `可复现实验流程`, `引用校验`, `图表证据绑定`。

### 1.4 纳入与剔除标准

纳入标准：

- 与 AI Agent、科研自动化、文献结构化、证据溯源、科研资产打包或生物医学任务执行直接相关。
- 与神经科学、脑病、ECS、认知障碍文献处理直接相关。
- 具有 DOI、arXiv DOI、PMID 或可核对的正式出版信息。
- 能为本项目的 Agent 架构、ARM Schema、工具调用、trace、可复现验证或安全边界提供工程启发。

剔除规则：

- 仅讨论通用聊天机器人，不涉及工具调用、结构化输出或科研任务执行。
- 无法核对基本来源信息，且不属于赛题指定背景材料。
- 与脑科学、生物医学或科研资产复用无明显关系的纯工程案例。
- 只有观点性评论，缺少方法、系统或可复用框架的材料。

## 2. 主流方法综述

### 2.1 LLM 单轮抽取

LLM 单轮抽取通常把论文全文或片段输入模型，要求模型输出摘要、关键发现或方法步骤。这种方案实现成本低，适合快速生成初稿，但不适合作为最终 ARM 资产生成方式。原因是单轮输出容易混合原文事实、背景知识和模型归纳，无法稳定保证每条 claim 都有章节、段落、图表或表格定位。RAG 和 ReAct 类方法说明，复杂知识任务需要显式检索、工具调用和来源约束，而不应完全依赖模型参数记忆。

本系统对应策略：`claims.raw_text` 必须来自论文原文，`support_evidence_snippet[0]` 必须与 `raw_text` 对齐；模型生成内容只允许进入 `protocol`、`runbook`、`eval_plan`、`limitations` 等流程解释字段，并标记 `model_infer`。

### 2.2 多 Agent 科研流水线

ChemCrow 证明了 “LLM + 专用工具” 可用于复杂化学任务；BioDiscoveryAgent 展示了生物实验设计中闭环假设搜索和工具辅助推理；AI Scientist 和 Agent Laboratory 把科研流程扩展到假设生成、实验执行、代码生成、结果分析和论文撰写。这类工作共同说明：科研 Agent 不应是单个自由文本生成器，而应拆分为可审计阶段。

本系统在七日 Hackathon 约束下采用插件式分层：原有 `arm_agent/tools.py` 保留 `literature_extract` 与 `reference_validator`，新增 `arm_agent/p0_tools` 放置图表 caption 抽取、冲突检测和 ARM 校验，避免破坏现有入口。后续 P1 可进一步接入 LangGraph 状态持久和多子 Agent 编排。

### 2.3 结构化科研资产

FAIR 原则强调科研对象应可发现、可访问、可互操作、可复用；RO-Crate 使用 JSON-LD 和 schema.org 将数据、软件、人员、方法和元数据打包为研究对象。ARM 九模块与这些思想一致：`metadata` 记录来源，`claims` 与 `evidence` 保留事实和证据，`protocol` 与 `runbook` 描述过程，`eval_plan` 给出复现验证，`provenance` 记录来源和工具，`limitations` 表达边界，`artifacts` 支持导出。

本系统把 ARM 输出为 JSON/YAML，并在 `provenance` 中写入引用校验、图表 caption、冲突检测、dry-run 和细粒度 trace，方便前端渲染、答辩回放和后续知识图谱对接。

### 2.4 证据溯源与安全边界

生物医学文献处理的核心风险是模型幻觉和医学越界。对于 ECS 和认知障碍论文，动物实验、细胞实验、影像研究和临床观察的证据等级不同，不能直接输出临床诊断、预后或治疗建议。本系统把安全边界写入 `limitations`，失败分支对残缺输入直接阻断，不生成残缺 ARM。

## 3. 方法对比总表

| 方案名称 | 核心技术 | 优势 | 局限性 | 适配场景 |
|---|---|---|---|---|
| LLM 单轮抽取 | 直接 prompt 论文全文或片段 | 实现快，适合初稿 | 容易混合原文和模型归纳，证据定位不稳定 | 早期探索、人工辅助摘要 |
| RAG + 证据片段 | 检索段落后生成答案 | 可引用来源，降低幻觉 | 仍需 Schema 和输出校验 | 文献问答、局部证据定位 |
| ReAct / Tool-Use Agent | 推理与工具调用交替 | 可把检索、验证、解析拆成步骤 | Trace 与权限控制必须完善 | 科研流水线调度 |
| 多 Agent 科研系统 | 文档解析、实验设计、执行、评估分工 | 适合复杂科研任务 | 开发周期长，调试成本高 | P1/P2 架构升级 |
| ChemCrow 式工具增强 | LLM 调度领域工具 | 领域任务更可靠 | 依赖工具质量和权限边界 | 专用科学任务 |
| BioDiscoveryAgent 式闭环 | 假设-实验-结果迭代 | 支持生物实验设计 | 不等同文献资产封装 | 生物扰动实验设计 |
| RO-Crate/FAIR 资产 | 研究对象元数据打包 | 可复用、可交换、可归档 | 不负责 claim 抽取 | ARM 导出和跨赛道复用 |
| Paper-to-ARM 本系统 | 原文 claim、证据绑定、引用校验、caption、dry-run、trace | 对 A 赛道直接适配，成功/失败分支完整 | caption 仅解析文本，不做图像像素理解 | 神经科学/ECS 论文资产生成 |

## 4. 三条可落地设计结论

### 结论 1：工具增强 Agent 比单轮摘要更适合科学资产生成

调研发现：ChemCrow、ReAct 和 BioDiscoveryAgent 都说明，复杂科学任务需要工具调用、阶段化流程和可审计中间结果，而不是仅依赖 LLM 一次性输出 [1,3,4,8]。

架构/代码设计决策：保留 `literature_extract` 和 `reference_validator` 作为原始工具；新增 `p0_tools` 插件层，承载 `figure_extract`、`conflict_detector`、`arm_validator`。这样既兼容旧入口，又能向多 Agent 架构演进。

本系统落地实现：`arm_agent/pipeline.py` 中原逻辑仍 `from arm_agent.tools import literature_extract, reference_validator`，新增逻辑统一 `from arm_agent.p0_tools import ...`，避免 `tools.py` 与 `tools/` 包冲突。

### 结论 2：结构化科研资产必须把证据和流程一起封装

调研发现：FAIR 与 RO-Crate 强调研究对象需要元数据、文件、方法、关系和 provenance；AI Scientist 类系统进一步说明科研流程本身也需要被记录和评估 [2,6,7,10]。

架构/代码设计决策：ARM 不只保存 claims，还必须包含 runbook、eval_plan、provenance、limitations 和 artifacts；dry-run 只验证 ARM 生成流程，不夸大为真实实验室复现。

本系统落地实现：`arm_agent/eval/dry_run.py` 检查输入文件、九模块、claim/evidence 绑定；`arm_agent/eval/evaluator.py` 生成评估分；结果写入 `provenance.dry_run_result` 与 `provenance.evaluation_result`，前端 Dry-run 面板展示。

### 结论 3：ECS 论文需要专项打标和医学边界

调研发现：ECS 与脑内物质运输、间质液、glymphatic clearance、神经退行性疾病和认知障碍相关，但不同实验模型和测量方法的外推能力不同，动物实验不能直接迁移到人体临床判断 [11,12]。

架构/代码设计决策：在 `metadata`、`claims`、`limitations` 中增加 `ecs_related`；对图表 caption、证据不完整、引用缺 DOI/PMID 和跨论文冲突全部标记 `review_required`，而不是自动断言结论正确。

本系统落地实现：`literature_extract` 提取 `ecs_keywords`，`p0_tools.figure_extract` 只解析 caption 文本，`p0_tools.conflict_detector` 只输出冲突候选，`limitations` 固定包含医学边界和动物到人体不可直接迁移说明。

## 5. 领域痛点与系统解决方案

### 5.1 可自动 AI 提取内容

- 元数据初筛：标题、作者、DOI、年份、来源文件、ECS 关键词。
- 段落级 claim 候选：只从原文句子中截取，不做扩写。
- 文本证据和 locator：章节、段落、图表 caption 字符串。
- 引用风险：无 DOI/PMID、缺年份、缺期刊、领域不明、重复引用。
- ARM 九模块结构、runbook、eval_plan、trace、导出路径。

### 5.2 必须人工复核内容

- claim 是否真正代表论文核心结论。
- 图表 caption 是否与正文 claim 一致。
- 跨论文冲突是否属于真实科学矛盾，而非实验条件差异。
- 无 DOI/PMID 的引用是否仍可接受。
- 动物、细胞、影像或临床证据的等级解释。
- ECS 机制是否能被推广到人体疾病或治疗场景。

### 5.3 三大行业痛点

LLM 幻觉：系统通过 quote-only claim、`source_attribution=paper_original`、`model_infer` 标记和 ARM validator 限制模型自由发挥。

证据无法溯源：系统要求每条 claim 绑定 `source_location`、`support_evidence_snippet` 和 `evidence_ids`，图表 caption 也作为 evidence 写入。

实验步骤不可复现：系统提供 runbook 和 dry-run，但明确 dry-run 仅验证 ARM 生成流程，不声称复现实验室实验。

## 6. ECS 专项适配

基于 `brain_ECS_review.txt` 样例，系统针对 ECS 做了以下定制：

- `metadata.ecs_related` 和 `metadata.ecs_keywords` 记录 ECS、extracellular space、interstitial fluid、glymphatic 等关键词。
- `claims.ecs_related` 标记每条 ECS 相关结论。
- `limitations` 固定包含 ECS 研究空白、动物到人体不可直接迁移、医学诊疗禁止输出。
- `figure_extract` 解析 Figure/Table/Supplementary caption 作为图表证据来源，但不做图像像素识别。
- `conflict_detector` 对 ECS、glymphatic、interstitial、amyloid、clearance 等术语进行跨论文冲突候选检测。
- Web 端单独展示“图表证据”和“冲突告警”，答辩时可直观看到 ECS 专项溯源。

## 7. 项目局限

当前系统是七日 Hackathon 原型，优先满足 A 赛道端到端、结构化、可追溯、失败阻断和演示要求。局限包括：

- PDF 图表处理仅限可抽取文本 caption，不识别图像像素、显微图、曲线数值或复杂表格单元。
- 冲突检测是保守词汇级候选扫描，不能替代领域专家判断。
- 引用校验以 DOI/PMID 和文本完整性为主，未联网逐条校验参考文献页面。
- dry-run 验证 ARM 生成流程和文件依赖，不等同真实实验复现。
- LangGraph 状态持久、多子 Agent 并发调度、三层 Guardrails 深度实现属于 P1/P2 扩展。

## 8. 行业价值

ARM 结构化资产相较传统 PDF 具有三类复用价值：

- AI 科研智能体：Agent 可直接读取 `claims`、`evidence`、`runbook` 和 `provenance`，减少重复解析 PDF 的成本。
- 知识图谱：`metadata`、`claims`、ECS 标签、引用和 limitations 可映射为实体、关系和证据边。
- 机制挖掘：跨论文冲突检测、ECS 关键词聚合和证据等级标记可支持后续疾病机制比较。

## 参考文献

[1] Bran AM, Cox S, Schilter O, Baldassari C, White AD, Schwaller P. ChemCrow: augmenting large-language models with chemistry tools. Nature Machine Intelligence. 2024. DOI: 10.1038/s42256-024-00832-8.

[2] Lu C, Lu C, Lange RT, Foerster J, Clune J, Ha D. The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery. arXiv. 2024. DOI: 10.48550/arXiv.2408.06292.

[3] Roohani Y, Vora J, Huang Q, et al. BioDiscoveryAgent: An AI Agent for Designing Genetic Perturbation Experiments. arXiv. 2024. DOI: 10.48550/arXiv.2405.17631.

[4] Gao S, Fang J, Li Y, et al. Empowering biomedical discovery with AI agents. arXiv. 2024. DOI: 10.48550/arXiv.2404.02831.

[5] Schick T, Dwivedi-Yu J, Dessì R, et al. Toolformer: Language Models Can Teach Themselves to Use Tools. arXiv. 2023. DOI: 10.48550/arXiv.2302.04761.

[6] Yao S, Zhao J, Yu D, et al. ReAct: Synergizing Reasoning and Acting in Language Models. arXiv. 2022. DOI: 10.48550/arXiv.2210.03629.

[7] Schmidgall S, Ziaei R, Harris C, et al. Agent Laboratory: Using LLM Agents as Research Assistants. arXiv. 2025. DOI: 10.48550/arXiv.2501.04227.

[8] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. arXiv. 2020. DOI: 10.48550/arXiv.2005.11401.

[9] Sefton P, Soiland-Reyes S, Nesheim D, et al. Packaging research artefacts with RO-Crate. Data Science. 2022. DOI: 10.3233/DS-210053.

[10] Wilkinson MD, Dumontier M, Aalbersberg IJJ, et al. The FAIR Guiding Principles for scientific data management and stewardship. Scientific Data. 2016. DOI: 10.1038/sdata.2016.18.

[11] Han H, et al. Brain extracellular space and brain interstitial system review sample used in this project. Cell & Bioscience Systems. 2026. DOI: 10.34133/cbsystems.0529.

[12] Iliff JJ, Wang M, Liao Y, et al. A paravascular pathway facilitates CSF flow through the brain parenchyma and the clearance of interstitial solutes. Science Translational Medicine. 2012. DOI: 10.1126/scitranslmed.3003748.
