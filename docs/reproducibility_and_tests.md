# 复现与测试说明

## 环境

- Python 3.13
- Windows PowerShell
- 依赖文件：`requirements.txt`

## 安装

```powershell
pip install -r requirements.txt
```

## 启动 Web UI

```powershell
uvicorn web_app:app --host 127.0.0.1 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## 端到端测试

```powershell
python -m pytest
```

当前测试覆盖：

1. 单篇 ECS 综述成功生成 ARM。
2. 残缺论文触发失败阻断。
3. 5 篇 PDF 批量生成 ARM。

## 手工复现命令

单篇成功：

```powershell
python main.py run --input .\brain_ECS_review.txt --output-dir outputs --format json
```

失败阻断：

```powershell
python main.py run --input .\fixtures\incomplete_paper.txt --output-dir outputs --format json
```

五篇批量：

```powershell
$files = Get-ChildItem .\fixtures\full_papers -Filter *.pdf | Sort-Object Name | Select-Object -First 5 | ForEach-Object { $_.FullName }
python main.py run --input @files --output-dir outputs\full_papers --format json
```

## 可检查输出

- `full_arm`: ARM 九模块资产包。
- `trace_record`: 输入、工具调用、抽取记录、校验结果、失败风险。
- Web UI: 总览、评审门禁、Claims & Evidence、引用校验、Trace、JSON。

