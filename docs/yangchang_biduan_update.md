# 扬长避短增量改造说明

## 保留优势

- 原 ARM 九模块 Schema、claim/evidence 绑定、model_infer 隔离机制不变。
- 原 CLI `main.py run/demo`、Web `web_app.py`、成功/失败双案例、trace、reference_validator 不变。
- 原医学安全边界、ECS 标签、JSON/YAML 导出和批量 5 篇论文能力保留。

## 新增短板修复

1. PDF 原生解析：`tools/pdf_parser_tools/`，支持 pdfplumber/PyPDF2/pypdf，OCR 以 review_required stub 安全降级。
2. LangGraph 增强编排：`arm_agent/langgraph_orchestrator/`，支持 checkpoint、resume、人工审批记录、单篇失败隔离。
3. 本地脑科学 RAG：`arm_agent/rag/`，轻量 TF 相似度检索，辅助证据上下文召回。
4. 量化评测：`arm_agent/evaluation_engine/`，precision/recall/F1、幻觉检测、引用内容一致性。
5. C 赛道 KG 导出：`arm_agent/kg_export/`，输出 nodes/edges 图谱结构。
6. Web 增强：`web/demo_mode.html`、`web/audit_panel.html`，不替换原工作台。
7. 本地 LLM 兜底：`arm_agent/local_llm/`，规则式输出且强制 model_infer。
8. 多文献融合：`tools/multi_literature_fusion/`，合并、去重、冲突检测、可信度加权。

## 验证

```powershell
python -m pytest tests --basetemp=C:\tmp\pytest_tmp -q
```

当前结果：`51 passed, 1 warning`。

## Web 图表证据原图展示增量说明

本次迭代仅调整 Web 展示层和新增独立图像提取接口，不改动 ARM 主解析、reference_validator、Dry-run、Trace 回放和 JSON/YAML 导出逻辑。

- 顶部 Tab 永久移除“提交材料”，保留：总览、评审门禁、Claims & Evidence、图表证据、Dry-run、引用校验、Trace 回放、JSON。
- 图表证据页新增 PDF 原图预览：后端调用 PyMuPDF 提取 PDF embedded images，前端在对应 caption 上方展示图片。
- 若图片提取失败，页面显示友好提示，图注文本照常展示，不阻塞其他模块。
- 多论文场景支持左侧搜索与单篇筛选，仅展示当前选中论文的图表证据。
- 新增红点角标、全局待复核提示条、冲突状态预警卡片、图注折叠展开、引用编号高亮。
- 新增证据汇总 CSV 与图表摘要 PDF 下载入口，保留原“下载 ARM JSON”按钮位置。
