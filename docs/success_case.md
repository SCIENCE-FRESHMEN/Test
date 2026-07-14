# 成功案例说明

## 输入

成功案例使用 `fixtures/full_papers` 下 5 篇真实 PDF 中的前 5 篇，系统上限为 5 篇。

也可使用单篇 `brain_ECS_review.txt` 作为快速演示。

## 运行方式

Web UI：

1. 打开 `http://127.0.0.1:8000`。
2. 点击“选择 PDF/TXT 文件”。
3. 选择 1-5 篇论文。
4. 点击“生成 ARM 资产”。
5. 查看“总览”“评审门禁”“Claims & Evidence”“引用校验”“Trace 回放”。
6. 点击“下载 ARM JSON”导出资产包。

命令行：

```powershell
$files = Get-ChildItem .\fixtures\full_papers -Filter *.pdf | Sort-Object Name | Select-Object -First 5 | ForEach-Object { $_.FullName }
python main.py run --input @files --output-dir outputs\full_papers --format json
```

## 预期结果

- `metadata.processing_status = success`
- claims 数量不少于 5
- 每条 claim 含 `raw_text`、`source_location`、`support_evidence_snippet`
- `raw_text == support_evidence_snippet[0]`
- evidence 与 claim 通过 evidence_ids 绑定
- provenance 包含 reference_validation
- trace_record 包含每次工具调用
- runbook 至少一个步骤 `can_dry_run = true`
- artifacts 包含 JSON 导出路径

## 展示重点

- 评审门禁页展示 A 赛道核心要求是否通过。
- Claims 页面展示原文摘抄，不是模型概括。
- 引用校验页面展示 DOI/PMID、完整性、领域匹配、重复风险。
- Trace 页面展示 `literature_extract` 与 `reference_validator` 调用顺序。

