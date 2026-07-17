# 运行与编译说明

## 1. Python 复现

建议使用 Python 3.10--3.12，并在本目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python code\pinn_ecs.py
python code\ecs_net.py
```

脚本会在 `code/results/` 写入 `pinn_tracer_profiles.png` 与 `ecs_net_segmentation.png`。两者均由脚本内部生成的合成数据得到；日志中的参数为无量纲教学演示，不是ECS实测数据。GPU不是必需条件；CPU运行时可将 `epochs` 参数调小进行快速检查。

依赖用途：PyTorch负责网络训练；NumPy和Matplotlib负责数值与绘图；OpenCV生成合成显微图像；SimpleITK为后续接入NIfTI/DICOM的预留依赖。若只运行当前示例，SimpleITK安装失败不影响脚本，可暂时从 `requirements.txt` 删除该行。

## 2. TeX Live 编译

安装 TeX Live，并确保包含 `ctex`、`biblatex`、`biber` 与 `gb7714-2015`。进入 `latex/` 后按顺序执行：

```powershell
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

生成文件为 `latex/main.pdf`。采用 XeLaTeX，是为了可靠处理中文字体。运行代码后图片会从 `../code/results/` 自动被找到；本稿正文未强制插图，因此即使首次尚无结果图也可编译。

## 3. Overleaf 编译

上传整个 `ecs_course_report` 文件夹内容，将主文件设为 `latex/main.tex`，编译器选择 XeLaTeX，文献工具选择 Biber。若Overleaf无法跨目录读取图，请将 `code/results/` 下的 PNG 复制到 `latex/figures/`，保持文件名不变。

## 4. 常见问题

- `biber` 未找到：在TeX Live Manager安装Biber，或确认编辑器的文献后端为Biber而不是BibTeX。
- 中文乱码：切换至XeLaTeX；不要以pdfLaTeX编译该文件。
- `gb7714-2015` 缺失：通过TeX Live Manager安装 `biblatex-gb7714-2015` 宏包。
- PyTorch安装失败：按本机CUDA/CPU环境从 PyTorch 官方安装页选择命令，然后重跑其余依赖安装。
- 模型输出波动：该PINN逆问题受随机初始化与优化影响；固定随机种子、增加迭代次数并不等同于获得真实生物学结论。

## 5. 提交前检查

- 确认黄色“待与老师/助教确认”标记已保留或获得明确答复。
- 不将合成图、演示参数或仿真比较写为动物/临床实验结果。
- 检查 `main.pdf` 中引用、页眉、公式和参考文献是否完整。
