# NEURONCLAW A Track: Paper-to-ARM Orchestrator

This project is a runnable Paper-to-ARM prototype for the A track. It turns one to five neuroscience paper text files into a structured `full_arm` package plus a replayable `trace_record`.

## What It Implements

- ARM nine modules: `metadata`, `claims`, `evidence`, `protocol`, `runbook`, `eval_plan`, `provenance`, `limitations`, `artifacts`
- Original scientific extraction tools remain `literature_extract` and `reference_validator`; P0 review plugins are separated under `arm_agent/p0_tools`
- Success branch: extracts at least five source-located claims from `brain_ECS_review.txt`
- Failure branch: blocks incomplete input and exports a failure report instead of a partial scientific ARM
- ECS tagging in metadata, claims, and limitations
- Dry-run capable runbook step with explicit inputs, tools, outputs, and manual review flags
- P0 review plugins under `arm_agent/p0_tools`: caption-only figure/table extraction, conflict candidate detection, and ARM validation
- Dry-run and evaluator results embedded into `provenance` and displayed in the Web UI
- API rate-limit settings are centralized in `arm_agent/config/settings.py`
- JSON/YAML export and full trace replay log
- Web review gate aligned to A-track requirements
- Submission materials: literature review, flowchart, success/failure cases, reproducibility notes, known limitations, PPT script, checklist, scoring matrix

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DEEPSEEK_API_KEY="sk-..."
```

### Recommended integrations (developed and maintained by our team)

<div align="center">

| **<div align="center">[napari plugin](https://github.com/MIC-DKFZ/napari-nninteractive)</div>** | **<div align="center">[MITK integration](https://www.mitk.org/)</div>** |
|-------------------|----------------------|
| [<img src="imgs/Logos/napari.jpg" height="200">](https://github.com/MIC-DKFZ/napari-nninteractive) | [<img src="imgs/Logos/mitk.jpg" height="200">](https://www.mitk.org/) |

</div>

### Community-driven integrations

Huge thanks to the community for contributing these integrations!

<div align="center">

| **<div align="center">[3D Slicer extension](https://github.com/coendevente/SlicerNNInteractive)</div>** | **<div align="center">[ITK-SNAP extension](https://itksnap-dls.readthedocs.io/en/latest/quick_start.html)</div>** | **<div align="center">[OHIF integration](https://github.com/CCI-Bonn/OHIF-AI)</div>** |
|-------------------------|-------------------------|-------------------------|
| [<img src="imgs/Logos/3DSlicer.png" height="200">](https://github.com/coendevente/SlicerNNInteractive) | [<img src="imgs/Logos/snaplogo_sq.png" height="200">](https://itksnap-dls.readthedocs.io/en/latest/quick_start.html) | [<img src="imgs/Logos/ohif.png" height="200">](https://github.com/CCI-Bonn/OHIF-AI) |

</div>



## What is nnInteractive?

> Isensee, F.*, Rokuss, M.*, Krämer, L.*, Dinkelacker, S., Ravindran, A., Stritzke, F., Hamm, B., Wald, T., Langenberg, M., Ulrich, C., Deissler, J., Floca, R., & Maier-Hein, K. (2025). nnInteractive: Redefining 3D Promptable Segmentation. https://arxiv.org/abs/2503.08373 \
> *: equal contribution

Link: [![arXiv](https://img.shields.io/badge/arXiv-2503.08373-b31b1b.svg)](https://arxiv.org/abs/2503.08373)


##### Abstract:

Accurate and efficient 3D segmentation is essential for both clinical and research applications. While foundation 
models like SAM have revolutionized interactive segmentation, their 2D design and domain shift limitations make them 
ill-suited for 3D medical images. Current adaptations address some of these challenges but remain limited, either 
lacking volumetric awareness, offering restricted interactivity, or supporting only a small set of structures and 
modalities. Usability also remains a challenge, as current tools are rarely integrated into established imaging 
platforms and often rely on cumbersome web-based interfaces with restricted functionality. We introduce nnInteractive, 
the first comprehensive 3D interactive open-set segmentation method. It supports diverse prompts—including points, 
scribbles, boxes, and a novel lasso prompt—while leveraging intuitive 2D interactions to generate full 3D 
segmentations. Trained on 120+ diverse volumetric 3D datasets (CT, MRI, PET, 3D Microscopy, etc.), nnInteractive 
sets a new state-of-the-art in accuracy, adaptability, and usability. Crucially, it is the first method integrated 
into widely used image viewers (e.g., Napari, MITK), ensuring broad accessibility for real-world clinical and research 
applications. Extensive benchmarking demonstrates that nnInteractive far surpasses existing methods, setting a new 
standard for AI-driven interactive 3D segmentation.

<img src="imgs/figure1_method.png" width="1200">


## Installation

nnInteractive ships as **two pip packages — install only what you need:**

- **`nninteractive-client`** — lightweight remote client that drives a remote
  `nninteractive-server` (via `nnInteractiveRemoteInferenceSession`). **No PyTorch, no GPU** —
  only `numpy` / `httpx` / `blosc2`. Ideal for a GUI or thin client.
- **`nnInteractive`** — the full stack: the local inference engine *and* the official
  server. Needs **PyTorch and an NVIDIA GPU** (10 GB VRAM recommended; small objects work with
  <6 GB). It depends on `nninteractive-client`, so it includes the remote client too.

Both expose the same `nnInteractive` import namespace, so client code is identical either way.

##### 1. Create a virtual environment

nnInteractive supports Python 3.10+ and works with Conda, pip, or any other virtual environment. Here’s an example using Conda:

```
conda create -n nnInteractive python=3.12
conda activate nnInteractive
```

```

The current demo is deterministic and local for reproducibility. The DeepSeek key is read from `DEEPSEEK_API_KEY` when model-backed extensions are added; do not hard-code it in source files.

DeepSeek's official quick start documents an OpenAI-compatible `base_url` of `https://api.deepseek.com`. This project defaults to `deepseek-v4-pro` in `.env.example`.

Note: installing `openai-agents` may upgrade `websockets`. On this machine pip reported a version conflict with `cozepy`; the Paper-to-ARM tests still pass.

## Run

Success case:

```powershell
python main.py run --input .\brain_ECS_review.txt --output-dir outputs --format json
```

Failure case:

```powershell
python main.py run --input .\fixtures\incomplete_paper.txt --output-dir outputs --format json
```

Both cases:

```powershell
python main.py demo --output-dir outputs
```

Web UI:

```powershell
uvicorn web_app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser. The page is an upload-first ARM workbench: upload 1-5 PDF/TXT files, generate ARM, inspect review-gate checks, view claims/evidence, reference validation, trace replay, raw JSON, and download the JSON export.
The "提交材料" tab links all review documents under `docs/`.

Five-paper batch case:

```powershell
$files = Get-ChildItem .\fixtures\full_papers -Filter *.pdf | Sort-Object Name | ForEach-Object { $_.FullName }
python main.py run --input @files --output-dir outputs\full_papers --format json
```

## Test

```powershell
python -m pytest
```

Expected current result:

```text
16 passed
```

## Submission Documents

- `docs/literature_review_A_track.md`
- `docs/flowchart_A_track.md`
- `docs/success_case.md`
- `docs/failure_case.md`
- `docs/reproducibility_and_tests.md`
- `docs/known_limitations.md`
- `docs/ppt_demo_script.md`
- `docs/submission_checklist.md`
- `docs/scoring_matrix.md`
- `docs/day_shturl`
- `docs/development_plan.md`

## Design Notes

The system uses a conservative controller: all claims must be backed by exact source-text quotes and locators. Pipeline-generated protocol, runbook, eval, and limitation text is marked as `model_infer` in provenance fields so it cannot be mistaken for paper evidence.

The built-in claim extractor follows a strict quote-only policy. Each extracted claim includes `raw_text`, `claim_category`, `source_location`, `support_evidence_snippet`, `conflict_evidence_snippet`, `source_attribution`, `ecs_related`, and `evidence_incomplete`. `raw_text` is copied directly from the source text and must match the supporting evidence snippet.

The reference validator records identifier, completeness, domain-fit, and duplicate/conflict checks for each extracted reference. References without DOI/PMID are marked `reference_requires_review`, and the aggregate status becomes `reference_invalid`; this is preserved in `provenance.reference_validation` and trace rather than silently discarded.

As part of the `nnInteractive` framework, we provide a dedicated module for **supervoxel generation** based on [SAM](https://github.com/facebookresearch/segment-anything) and [SAM2](https://github.com/facebookresearch/sam2). This replaces traditional superpixel methods (e.g., SLIC) with **foundation model–powered 3D pseudo-labels**.

🔗 **Module:** [`nnInteractive/supervoxel/`](nnInteractive/supervoxel)

The SuperVoxel module allows you to:

- Automatically generate high-quality 3D supervoxels via axial sampling + SAM segmentation and SAM2 mask propagation.
- Use the generated supervoxels as **pseudo-ground-truth labels** to train promptable 3D segmentation models like `nnInteractive`.
- Export `nnUNet`-compatible `.pkl` foreground prompts for downstream use.

For detailed installation, configuration, and usage instructions, check the [SuperVoxel README](nnInteractive/supervoxel/README.md).


Medical boundary: outputs are research-structuring artifacts only. They do not provide diagnosis, prognosis, prescriptions, or treatment recommendations. Limitations always include animal-to-human and clinical-use warnings.

## Citation

If you utilize this framework in your academic work, please cite our repository and the original nnUNet paper.

## License

MIT License


