# A 赛道评分矩阵对照

## 端到端完成度（30 分）

| 要求 | 对应实现 | 演示位置 |
|---|---|---|
| 输入 1-5 篇论文 | `main.py run --input`、Web 上传 | Web 输入面板 |
| ARM 九模块 | `arm_agent/schema.py`、`arm_agent/pipeline.py` | JSON 原文页 |
| 成功分支 ≥5 claims | `tests/test_pipeline.py` | Claims & Evidence |
| 失败阻断分支 | `fixtures/incomplete_paper.txt` | 总览 / 评审门禁 |
| JSON/YAML 导出 | `main.py`、artifacts | 下载按钮 |
| dry-run | `arm_agent/eval/dry_run.py` | Dry-run 面板 |

## 方案设计（20 分）

| 要求 | 对应实现 | 演示位置 |
|---|---|---|
| 总控调度 | `PaperToARMOrchestrator` | 流程图 |
| 原工具兼容 | `arm_agent/tools.py` | 代码说明 |
| P0 插件层 | `arm_agent/p0_tools` | 图表/冲突/校验面板 |
| 配置中心 | `arm_agent/config/settings.py` | `.env.example` |
| 限流参数 | `api_request_interval_seconds`、`api_max_concurrency`、`api_retry_attempts`、`api_retry_backoff_seconds`、`api_timeout_seconds` | 配置说明 |
| Guardrails 预留 | 输入校验、工具分层、输出校验 | 答辩问答 |

## 证据可追溯（15 分）

| 要求 | 对应实现 | 演示位置 |
|---|---|---|
| claim 原文摘抄 | `raw_text`、`support_evidence_snippet` | Claims & Evidence |
| locator 定位 | `source_location`、`evidence.locator` | Claims & Evidence |
| 图表 caption | `p0_tools.figure_extract` | 图表证据 |
| 引用校验 | `reference_validator` | 引用校验 |
| 冲突候选 | `p0_tools.conflict_detector` | 冲突告警 |
| 模型推断区分 | `source_attribution`、`model_infer_policy` | JSON provenance |

## 文献调研落地（15 分）

| 要求 | 对应实现 | 演示位置 |
|---|---|---|
| 4-6 页报告 | `docs/literature_review_A_track.md` | 提交材料 |
| ≥10 篇参考文献 | 报告参考文献 12 条 | 文献调研页 |
| 方法对比表 | 报告第 3 节 | PPT 第 3 页 |
| 3 条落地链路 | 报告第 4 节 | PPT 第 3-4 页 |
| ECS 专项 | 报告第 6 节 | ECS 专项页 |

## 代码测试复现（10 分）

| 要求 | 对应实现 | 演示位置 |
|---|---|---|
| 自动化测试 | `tests/` | 终端 |
| P0 模块测试 | `test_p0_*.py` | 终端 |
| Web 接口测试 | `tests/test_web_app.py` | 终端 |
| 当前结果 | `16 passed` | PPT 第 9 页 |

## 汇报演示（10 分）

| 要求 | 对应实现 | 演示位置 |
|---|---|---|
| 成功案例 | `brain_ECS_review.txt` | Web 上传 |
| 失败案例 | `docs/failure_case.md` | Web 上传 |
| 5 类失败样例 | 输入残缺、图表缺失、图表正文冲突、无 DOI、dry-run 缺参 | PPT 第 8 页 |
| 提交材料导航 | `/api/project-materials` | 提交材料页 |
| 七日开发说明 | `docs/day_shturl` | 提交材料页 |
