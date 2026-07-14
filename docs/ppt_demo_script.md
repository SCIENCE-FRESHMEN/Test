# A 赛道 10 分钟 PPT 演示脚本

## PPT 结构：10 页

1. 项目标题：NEURONCLAW A 赛道 Paper-to-ARM 科研资产生成系统。
2. 问题定义：PDF 论文难以被 Agent 稳定检查、复用、回放。
3. 文献调研结论：ChemCrow、AI Scientist、BioDiscoveryAgent、RO-Crate、FAIR 对系统设计的启发。
4. 系统架构：原工具层 `tools.py` + P0 插件层 `p0_tools` + ARM Schema + Trace。
5. ARM 九模块：metadata / claims / evidence / protocol / runbook / eval_plan / provenance / limitations / artifacts。
6. ECS 专项：ECS 标签、图表 caption、医学边界、动物到人体不可直接迁移。
7. 成功案例演示：上传 ECS 论文，生成 ARM，查看 claims/evidence、图表证据和引用校验。
8. 失败案例演示：残缺输入、图表缺失、冲突候选、引用无 DOI、dry-run 缺参。
9. 测试与复现：`python -m pytest`、CLI、Web、JSON/YAML 导出、trace 回放。
10. 局限与下一步：图像 OCR、LangGraph 状态持久、多子 Agent、跨赛道知识图谱。

## 10 分钟讲稿

### 0:00-0:50 项目定位

本项目选择 A 赛道 Paper-to-ARM。输入是 1-5 篇脑科学或神经科学 PDF/TXT 论文，输出是标准 ARM 九模块结构化科研资产。系统只做科研文献结构化整理，不输出诊断、处方、预后或治疗建议。

### 0:50-1:40 问题定义

传统论文适合人读，但不适合 Agent 复用。结论、证据、图表、方法、引用和局限分散在 PDF 里；如果直接让大模型总结，很容易把模型推断混成论文原文。因此本系统的核心约束是：每条 claim 必须绑定原文摘抄、source_location 和 evidence_id；模型归纳只能标记为 `model_infer`。

### 1:40-2:50 文献调研

调研覆盖 PubMed、arXiv、Web of Science，时间范围 2020-2026。ChemCrow 和 BioDiscoveryAgent 说明科学任务需要 LLM 调度专用工具；AI Scientist 说明科研流程可以被拆成假设、实验、评估和写作阶段；RO-Crate 和 FAIR 说明科研资产需要机器可读元数据和 provenance。因此本系统采用分层流水线和结构化 Schema，而不是单轮摘要。

### 2:50-4:00 架构说明

原有 `arm_agent/tools.py` 保留两个核心工具：`literature_extract` 和 `reference_validator`。新增 P0 插件层统一放在 `arm_agent/p0_tools`，包括 `figure_extract`、`conflict_detector`、`arm_validator`。这样不会触发 `tools.py` 与 `tools/` 包导入冲突，也不破坏 `main.py` 和 `web_app.py`。

### 4:00-5:30 成功分支演示

打开 Web：`uvicorn web_app:app --host 127.0.0.1 --port 8000`。上传 `brain_ECS_review.txt` 或 `fixtures/full_papers` 中最多 5 篇 PDF。演示顺序：

1. 总览页：处理状态、ARM ID、ECS 标签、claim 数、evidence 数。
2. 评审门禁：ARM 九模块、5 条 claim、证据绑定、dry-run、trace、医学边界。
3. Claims & Evidence：展示 `raw_text` 与 `support_evidence_snippet` 对齐。
4. 图表证据：展示 Figure/Table caption 来源。
5. 引用校验：展示 DOI/PMID 和 `reference_requires_review`。

### 5:30-7:00 失败分支演示

上传 `fixtures/incomplete_paper.txt`。系统输出 `processing_status=failed` 和 blocked failure_report，不生成科学 claims。然后讲 5 类失败场景：输入残缺、图表缺失、图表正文冲突、无 DOI 引用、dry-run 参数缺失。强调失败分支是得分点：系统在信息不足时不编造 ARM。

### 7:00-8:00 ECS 专项

ECS 相关内容会写入 `metadata.ecs_related`、`metadata.ecs_keywords`、`claims.ecs_related` 和 ECS limitations。图表 caption 只解析文本，不夸大为图像像素识别。动物实验、细胞实验和影像结果不能直接迁移到人体临床建议。

### 8:00-9:00 测试与指标

展示终端：

```powershell
python -m pytest
```

当前测试覆盖成功 ARM、失败阻断、5 篇批量、图表 caption、ARM 校验、冲突检测、引用失效、dry-run 失败和 Web 接口。量化指标展示：

- ARM 九模块完整率：由 `arm_validator` 自动检查。
- claim 溯源率：`raw_text == support_evidence_snippet[0]`。
- dry-run 评分：写入 `provenance.evaluation_result.summary.score`。
- 失败阻断率：失败输入 `no_success_arm_generated=true`。

### 9:00-10:00 总结

本项目的工程创新点是：严格 quote-only claim、P0 插件式工具、ARM 九模块、失败阻断、dry-run 评估、trace 回放和 Web 可视化。下一步可接入 LangGraph 状态持久、OCR 图像理解、跨赛道知识图谱和更严格的安全 Guardrails。

## 5 分钟答辩问答预案

### Q1：为什么不直接让 DeepSeek 生成 ARM？

A：A 赛道核心是证据可追溯。单轮生成无法稳定保证每条 claim 对应原文段落、图表或表格。系统把模型推断与论文原文分离，claim 必须来自原文摘抄，流程文本才允许 `model_infer`。

### Q2：图表 OCR 做到什么程度？

A：当前只解析 PDF/TXT 可抽取文本中的 Figure/Table/Supplementary caption，不解释图像像素、显微图片、曲线数值或表格单元。该边界写入 docs 和代码注释，避免夸大能力。

### Q3：dry-run 是真实实验复现吗？

A：不是。dry-run 只验证 ARM 资产生成流程，包括输入文件、九模块、claim/evidence 绑定和预期输出。真实实验室复现需要原始数据、仪器、试剂和人工审批，不在本系统声明范围内。

### Q4：引用没有 DOI 为什么不一定阻断？

A：无 DOI/PMID 是复核风险，不一定说明文献不存在。系统标记 `reference_invalid` 和 `reference_requires_review`，写入 provenance，交给人工复核。

### Q5：跨论文冲突如何处理？

A：系统只输出冲突候选，不自动裁决科学正确性。冲突可能来自动物模型、样本、测量方法或疾病阶段差异，必须人工复核。

### Q6：如何证明没有伪造 Git 历史？

A：项目不伪造提交记录。开发过程写入 `docs/day_shturl`，按 Day1-Day6 记录完成模块、测试情况和答辩材料，用文档替代伪造历史。
