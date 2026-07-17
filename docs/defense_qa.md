# 答辩问答库

## 架构设计

Q: 为什么不直接重构成多 Agent 大系统？
A: 赛题要求端到端可运行和可复现。当前保留稳定主流程，用 `arm_agent/extensions` 和 `p0_tools` 作为插件层扩展，既不破坏旧命令，又能展示 handoff、调度、在线检索和安全护栏。

Q: 新增 `tools/literature_search_online.py` 为什么不放在 `arm_agent/tools/`？
A: 原仓库已有 `arm_agent/tools.py` 单文件模块，新增同名目录会造成 Python import 冲突。因此在线检索放在根级 `tools/` 包，保持兼容。

## 证据溯源

Q: 如何防止模型内容冒充论文证据？
A: 科学 claim 必须来自原文 `raw_text`，并绑定 `support_evidence_snippet`、`source_location` 和 evidence_id。流程、局限、冲突分析、可信度评分等模型归纳统一标记 `model_infer` 或写入 extension provenance。

Q: 图表解析做到什么程度？
A: 当前解析可抽取文本中的 Figure/Table/Supplementary caption，并拆分多 panel 和简单 caption 表格，不声明图像像素识别。

## 安全约束

Q: 如果用户要求诊断或处方怎么办？
A: `security_guardrails` 会识别 prompt injection 和临床指令，输出 `security_blocked` 失败报告，不生成成功 ARM。

Q: 动物实验能否推导人体治疗？
A: 不可以。limitations 固定声明动物实验不可直接迁移人体，系统只做科研文献结构化整理。

## 测试指标

Q: 如何证明新增功能可复现？
A: 执行 `python -m pytest --basetemp=outputs\pytest_tmp -q`，当前结果 41 passed。`scripts/full_score_demo.py` 会生成 `tests/report/quantitative_report.md` 和扩展 demo JSON。

Q: 为什么使用模拟在线检索？
A: 答辩环境和沙箱可能无网络，模拟 PubMed/arXiv 接口保证可复现，同时完整记录平台、关键词、年份、筛选条件和 DOI/PMID 字段。

## 不足与优化

Q: 当前最大短板是什么？
A: 图表解析仍是文本 caption 层级；未来可接入真实 PubMed API、arXiv API、OCR、表格结构识别和 LangGraph 状态持久。
