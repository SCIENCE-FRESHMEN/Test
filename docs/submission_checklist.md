# A 赛道最终提交检查清单

## 统一产出

- [x] 可运行原型：FastAPI Web UI + CLI。
- [x] 文献调研报告：`docs/literature_review_A_track.md`。
- [x] 代码与测试：`tests/`，执行 `python -m pytest`。
- [x] README：`README.md`。
- [x] 流程图：`docs/flowchart_A_track.md`。
- [x] 成功案例：`docs/success_case.md`。
- [x] 失败案例：`docs/failure_case.md`，覆盖 5 类失败场景。
- [x] 已知限制：`docs/known_limitations.md`。
- [x] PPT 与演示脚本：`docs/ppt_demo_script.md`。
- [x] 评分矩阵：`docs/scoring_matrix.md`。
- [x] 七日开发日志：`docs/day_shturl`。

## A 赛道硬性要求

- [x] 支持 1-5 篇 PDF/TXT 输入。
- [x] ARM 包含 metadata / claims / evidence / protocol / runbook / eval_plan / provenance / limitations / artifacts。
- [x] 成功分支提取不少于 5 条可追溯 claim。
- [x] 每条 claim 绑定原文摘抄、source_location 和 evidence_id。
- [x] 模型推断与论文原文区分，`model_infer` 不冒充 paper evidence。
- [x] 至少一个 runbook 步骤 `can_dry_run=True`。
- [x] dry-run 输出结果与 evaluator 评分写入 provenance。
- [x] 提供 JSON/YAML 导出。
- [x] 提供 trace_record 回放。
- [x] 提供失败阻断案例，不生成残缺 ARM。
- [x] limitations 包含医学边界、动物到人体不可直接迁移、ECS 研究空白。
- [x] ECS 专项标签写入 metadata、claims、limitations。

## P0 模块检查

- [x] 新增工具统一放在 `arm_agent/p0_tools`。
- [x] 原 `arm_agent/tools.py` 保留，不删除原业务逻辑。
- [x] `figure_extract.py` 仅解析 caption 文本，不夸大 OCR/图像理解。
- [x] `conflict_detector.py` 输出冲突候选与 review_required。
- [x] `arm_validator.py` 检查九模块、quote-only、evidence 绑定、医学边界。
- [x] `dry_run.py` 处理 artifacts 尚未生成时的正常前置状态。
- [x] `evaluator.py` 输出 dry-run score。
- [x] `trace/recorder.py` 记录 claim/evidence 细粒度 trace。
- [x] settings 增加限流参数：请求间隔、最大并发、重试次数、退避、超时。

## Web UI 检查点

- [x] 上传 1-5 篇 PDF/TXT。
- [x] 总览页。
- [x] 评审门禁页。
- [x] Claims & Evidence 页。
- [x] 图表证据页。
- [x] Dry-run 页。
- [x] 引用校验页。
- [x] Trace 回放页。
- [x] JSON 原文页。
- [x] JSON 下载。
- [x] 提交材料页。

## 复现命令

```powershell
python -m pytest
python main.py run --input .\brain_ECS_review.txt --output-dir outputs --format json
python main.py run --input .\fixtures\incomplete_paper.txt --output-dir outputs --format json
uvicorn web_app:app --host 127.0.0.1 --port 8000
```
