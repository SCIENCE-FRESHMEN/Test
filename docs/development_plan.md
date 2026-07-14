# P0-P1-P2 分阶段开发计划表

| 阶段 | 开发内容 | 预估耗时 | 验收标准 | 对应评分项 | 答辩演示价值 |
|---|---|---:|---|---|---|
| P0 | 修复 `tools.py` 与新增工具包冲突，新增 `arm_agent/p0_tools` | 0.5 天 | 所有新增工具从 `arm_agent.p0_tools` 导入，`python -m pytest` 通过 | 代码复现、方案设计 | 说明不破坏原入口，插件式演进 |
| P0 | 图表 caption 抽取 `figure_extract.py` | 0.5 天 | Figure/Table/Supplementary caption 写入 provenance；缺失时 review_required | 证据可追溯、失败案例 | Web 图表证据面板 |
| P0 | dry-run 与 evaluator | 0.5 天 | 空 artifacts 不误判；缺文件时报 dry_run_failed；输出 score | 端到端、测试复现 | Web Dry-run 面板 |
| P0 | ARM 完整性校验 `arm_validator.py` | 0.5 天 | 九模块、claim/evidence、quote-only、医学边界自动检查 | 证据可追溯、医学安全 | 评审门禁 PASS/CHECK |
| P0 | 冲突检测 `conflict_detector.py` | 0.5 天 | 批量论文冲突候选进入 provenance，人工复核标记 | 失败/冲突案例 | 冲突告警演示 |
| P0 | Trace 与 Web P0 面板 | 0.5 天 | 图表、冲突、dry-run、评分可视化 | 汇报演示 | 一页展示新增能力 |
| P0 | 自动化测试扩充 | 0.5 天 | 覆盖成功、异常、冲突、引用失效、dry-run 报错 | 代码测试复现 | 终端展示 16 passed |
| P0 | 三份核心 docs + 评分矩阵 | 0.5 天 | 调研报告、失败案例、PPT 脚本、day_shturl 完整 | 文献调研、答辩 | 直接作为提交材料 |
| P1 | LangGraph 状态持久与多子 Agent | 1-2 天 | 支持断点续跑、批量任务状态恢复 | 方案设计 | 展示架构升级路线 |
| P1 | 三层 Guardrails 深化 | 1 天 | 输入注入、文件大小/隐私、工具权限、输出水印 | 医学安全、工程规范 | 回答安全追问 |
| P1 | ECS 术语本体与证据等级 | 1 天 | ECS 术语映射，细胞/动物/临床证据分层 | ECS 专项、证据质量 | 展示领域深度 |
| P2 | OCR/版面解析增强 | 2-3 天 | 可解析更复杂 caption 和表格文本；仍不夸大图像理解 | 加分项 | 展示多模态路线 |
| P2 | 跨赛道知识图谱导出 | 1-2 天 | ARM claims/evidence 可导出 KG 边表 | 跨赛道复用 | B/C 赛道连接 |
| P2 | 量化评分仪表盘 | 1 天 | 自动输出自评分和缺口建议 | 汇报演示 | 对标评分表 |
