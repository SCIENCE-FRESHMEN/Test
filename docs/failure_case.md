# A 赛道失败案例说明

本项目失败分支的原则是：当输入缺失关键证据、图表、引用、ECS 信息或 dry-run 依赖时，系统输出 blocked failure report，不生成残缺科学 ARM。所有失败风险写入 `trace_record.failure_risks` 或 `provenance` 的 review 字段，供答辩现场回放。

## 失败场景 1：输入残缺

### 输入文件

`fixtures/incomplete_paper.txt`

该文件故意缺少完整正文、Methods、Results、图表 caption、参考文献和 ECS 关键信息。

### CLI 命令

```powershell
python main.py run --input .\fixtures\incomplete_paper.txt --output-dir outputs\failure_incomplete --format json
```

### 阻断输出样例

```json
{
  "metadata": {"processing_status": "failed"},
  "claims": [],
  "evidence": [],
  "failure_report": {
    "status": "blocked",
    "reason": "validation_failed",
    "no_success_arm_generated": true
  }
}
```

典型风险码：`insufficient_claims`、`ecs_information_missing`、`missing_figures_tables`、`missing_reference_records`、`paper_text_too_short`。

### Web 展示效果

Web 总览页显示 `processing_status=failed`；评审门禁中“失败阻断可展示”为 PASS；Claims & Evidence 为空，说明系统没有编造论文结论。

## 失败场景 2：图表 caption 缺失

### 输入文件

任意删除 Figure/Table caption 的论文文本，例如 `fixtures/incomplete_paper.txt` 或手工构造 `fixtures/broken_papers/no_figures.txt`。

### CLI 命令

```powershell
python main.py run --input .\fixtures\incomplete_paper.txt --output-dir outputs\failure_no_figures --format json
```

### 阻断或复核输出样例

```json
{
  "code": "missing_figures_tables",
  "message": "No figure or table captions were detected.",
  "severity": "high"
}
```

如果正文足够完整但 caption 不足，`provenance.figure_extraction` 会记录：

```json
{
  "status": "figure_extract_review_required",
  "risks": [{"code": "figure_caption_missing", "review_required": true}]
}
```

### Web 展示效果

“图表证据”页显示“未抽取到图表 caption”；评审门禁中“图表 caption 追踪”为 PASS 或 CHECK，具体取决于是否成功写入 provenance。

## 失败场景 3：图表正文冲突

### 输入构造

批量输入两篇论文时，若一篇 claim 表述 “extracellular brain clearance shows increased amyloid clearance”，另一篇表述 “does not show amyloid clearance”，系统不会自动判定科学结论谁对谁错，只输出冲突候选。

### CLI 命令

```powershell
python main.py run --input .\fixtures\full_papers\paper_a.pdf .\fixtures\full_papers\paper_b.pdf --output-dir outputs\failure_conflict --format json
```

### 复核输出样例

```json
{
  "conflict_detection": {
    "status": "conflict_review_required",
    "conflict_pairs": [
      {
        "conflict_id": "CON-001",
        "risk_level": "high",
        "review_required": true,
        "reason": "Opposite lexical polarity detected on shared neuroscience/ECS terms; manual review required."
      }
    ]
  }
}
```

### Web 展示效果

“图表证据”页下方“冲突告警”显示冲突对、共享术语和 review_required。答辩说明：这是人工复核门禁，不是系统自行下科学裁决。

## 失败场景 4：无 DOI/PMID 引用

### 输入构造

参考文献只包含作者、题名、期刊和年份，但无 DOI/PMID。

### CLI 命令

```powershell
python main.py run --input .\brain_ECS_review.txt --output-dir outputs\reference_review --format json
```

### 复核输出样例

```json
{
  "reference_validation": {
    "status": "reference_invalid",
    "summary": {
      "identifier_invalid": 1,
      "information_incomplete": 0
    }
  }
}
```

### Web 展示效果

“引用校验”页显示 `reference_invalid`，无 DOI/PMID 的条目标记 `reference_requires_review:no_valid_doi_or_pmid`。该风险不必然阻断 ARM，但必须进入 provenance 供人工复核。

## 失败场景 5：dry-run 参数缺失

### 输入构造

ARM runbook 中 `input_files` 指向不存在文件，或生成后移动原始输入文件。

### 测试入口

```powershell
python -m pytest tests\test_p0_dry_run_evaluator.py
```

### 输出样例

```json
{
  "status": "dry_run_failed",
  "steps": [
    {
      "step_id": "R-001",
      "status": "failed",
      "errors": ["missing_input_file:outputs/missing.txt"],
      "review_required": true
    }
  ]
}
```

### Web 展示效果

“Dry-run”页显示 `dry_run_failed`、失败步骤、缺失文件和评估指标。答辩说明：dry-run 只验证 ARM 资产生成流程，不声称真实实验室实验复现。

## 失败案例验收标准

- 失败输入不生成成功 ARM。
- `claims` 和 `evidence` 不被系统补造。
- 阻断原因可在 `trace_record.failure_risks` 或 `provenance` 中回放。
- Web 可展示失败风险、引用复核、图表缺失、冲突候选和 dry-run 失败。
