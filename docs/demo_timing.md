# 10 分钟演示时序控制文档

| 时间 | 内容 | 操作 |
|---:|---|---|
| 0:00-1:00 | 项目定位 | 展示 A 赛道 Paper-to-ARM、ARM 九模块、安全边界 |
| 1:00-2:00 | 架构说明 | 展示原 pipeline + p0_tools + extensions 插件层 |
| 2:00-3:00 | 在线检索 | 运行 `python scripts\full_score_demo.py`，展示 PubMed/arXiv 模拟检索元数据 |
| 3:00-4:30 | 成功流程 | Web 上传 `brain_ECS_review.txt`，展示 claims/evidence |
| 4:30-5:30 | 图表证据 | 展示图表 caption、多 panel、table rows 的结构化结果 |
| 5:30-6:30 | 冲突与可信度 | 展示 conflict candidate、trust_level、conflict_score |
| 6:30-7:30 | 失败与安全 | 展示残缺论文阻断、prompt injection/临床指令拦截 |
| 7:30-8:30 | 增量 ARM | 展示 `schemas/arm_increment.py` 合并记录和 provenance patch |
| 8:30-9:20 | 测试复现 | 展示 `41 passed` 和 `tests/report/quantitative_report.md` |
| 9:20-10:00 | 总结 | 对照评分矩阵说明六项闭环 |

## 快捷入口

- 原 Web 工作台：`http://127.0.0.1:8000`
- 答辩快捷页：`http://127.0.0.1:8000/static/demo_mode.html`
