# ECS Course Report Delivery / ECS课程报告交付说明

This directory is a self-contained course-report source package. All numerical examples are synthetic and must not be interpreted as animal, clinical, or public-dataset results.

## Layout

- `latex/main.tex`: Chinese report source.
- `latex/references.bib`: cited bibliography.
- `code/pinn_ecs.py`: a lightweight 1-D ECS advection-diffusion PINN inverse-problem demonstration.
- `code/ecs_net.py`: a lightweight shape-aware dual-branch ECS segmentation demonstration using synthetic microscopy-like slices.
- `requirements.txt`: Python dependencies.
- `RUN_AND_COMPILE.md`: reproducible commands and troubleshooting.

Items highlighted in yellow in the PDF are unverified hypotheses, implementation boundaries, or questions for the instructor/TA.

## Quick start / 快速运行

```powershell
pip install -r requirements.txt
python code\dataset_generator.py
python code\pinn_ecs.py
python code\ecs_net.py
python code\visualization.py
```

All generated arrays and figures are synthetic. They are not animal, human, or public-image observations. For LaTeX compilation, run XeLaTeX, Biber, XeLaTeX, XeLaTeX inside `latex/`; see `RUN_AND_COMPILE.md` for details. Yellow boxes are questions requiring instructor/TA confirmation.

所有数组和图像均为程序生成的合成数据，不代表动物、人体或公开影像观察结果。进入 `latex/` 后按 XeLaTeX、Biber、XeLaTeX、XeLaTeX 顺序编译；详情见 `RUN_AND_COMPILE.md`。黄色标记为提交前应与老师/助教确认的科学或合规边界。
