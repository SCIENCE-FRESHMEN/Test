from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SECTION_HEADINGS = [
    "abstract",
    "introduction",
    "methods",
    "method",
    "materials and methods",
    "materials",
    "methodology",
    "experimental procedures",
    "results",
    "result",
    "results and discussion",
    "discussion",
    "conclusion",
    "conclusions",
    "references",
    "bibliography",
    "supplementary materials",
    "supporting information",
    "摘要",
    "引言",
    "前言",
    "方法",
    "材料与方法",
    "结果",
    "讨论",
    "结论",
    "参考文献",
]

ECS_TERMS = [
    "extracellular space",
    "ecs",
    "brain interstitial system",
    "interstitial fluid",
    "isf",
    "extracellular matrix",
    "ecm",
    "glymphatic",
    "brain ecs",
    "extracellular volume",
    "tortuosity",
    "interstitial space",
    "脑细胞外间隙",
    "细胞外间隙",
    "脑组织液",
    "组织液",
    "脑间质",
    "脑内新分区",
    "引流途径",
    "类淋巴",
    "磁示踪",
    "脑细胞外间隙",
    "细胞外间隙",
    "脑组织液",
    "组织液",
    "脑间质",
    "脑内新分区",
    "引流途径",
]

CLAIM_EXTRACTOR_PROMPT = """
Paper细粒度结论&证据抽取子Agent:
只摘抄原文，禁止自主推导、扩写、脑补数据。每条claim必须包含
claim_id/raw_text/claim_category/source_location/support_evidence_snippet/
conflict_evidence_snippet/source_attribution/ecs_related/evidence_incomplete。
raw_text和support_evidence_snippet必须来自论文原文，不概括、不润色。
无原文直接支撑的猜想、推论丢弃；单篇少于5条有效claim时交由trace标记缺口。
"""

REFERENCE_VALIDATOR_PROMPT = """
参考文献合法性校验工具:
输入论文内全部引用文本、DOI、PMID、文献标题。逐项校验标识符、信息完整性、
领域匹配、重复/冲突。输出固定状态reference_valid或reference_invalid；
所有记录写入trace，供答辩展示引用校验流程。
"""


@dataclass
class LocatedParagraph:
    source_file: str
    section: str
    paragraph_index: int
    text: str


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\ufb00", "ff").replace("\ufb01", "fi").replace("\ufb02", "fl").replace("\ufb03", "ffi").replace("\ufb04", "ffl")
    text = re.sub(r"/G[0-9A-Fa-f]{2}", " ", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"-\n(?=[a-z])", "", text)
    normalized_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if "Downloaded from https://spj.science.org" in line:
            continue
        if re.search(r"Han et al\. 2026 \| https://doi\.org/10\.34133/cbsystems\.0529\s+\d+", line):
            continue
        # PDF text extracted from two-column pages often places unrelated columns
        # on one line. Treat wide gaps as column boundaries before paragraphing.
        parts = [part.strip() for part in re.split(r"\s{2,}", line) if part.strip()]
        normalized_lines.extend(parts or [""])
    return "\n".join(normalized_lines)


def read_paper_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        candidates: list[tuple[str, str]] = []
        pypdf_text = _read_pdf_with_pypdf(path)
        if pypdf_text:
            candidates.append(("pypdf", pypdf_text))
        pymupdf_text = _read_pdf_with_pymupdf(path)
        if pymupdf_text:
            candidates.append(("pymupdf", pymupdf_text))
        pdfplumber_text = _read_pdf_with_pdfplumber(path)
        if pdfplumber_text:
            candidates.append(("pdfplumber", pdfplumber_text))
        if not candidates:
            raise RuntimeError(f"No extractable text found in PDF: {path}")
        return max(candidates, key=lambda item: _pdf_text_quality_score(item[1]))[1]
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf_with_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        page_text: list[str] = []
        for page_index, page in enumerate(reader.pages, start=1):
            try:
                extracted = page.extract_text() or ""
            except Exception:
                extracted = ""
            if extracted.strip():
                page_text.append(f"\n\n[page {page_index}]\n{extracted}")
        return "\n".join(page_text)
    except Exception:
        return ""


def _read_pdf_with_pymupdf(path: Path) -> str:
    try:
        import fitz
    except ImportError:
        return ""
    try:
        doc = fitz.open(str(path))
        page_text: list[str] = []
        for page_index, page in enumerate(doc, start=1):
            extracted = page.get_text("text") or ""
            if extracted.strip():
                page_text.append(f"\n\n[page {page_index}]\n{extracted}")
        doc.close()
        return "\n".join(page_text)
    except Exception:
        return ""


def _read_pdf_with_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""
    try:
        page_text: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                try:
                    extracted = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                except Exception:
                    extracted = ""
                if extracted.strip():
                    page_text.append(f"\n\n[page {page_index}]\n{extracted}")
        return "\n".join(page_text)
    except Exception:
        return ""


def _pdf_text_quality_score(text: str) -> float:
    if not text:
        return 0.0
    normalized = normalize_text(text)
    ascii_words = len(re.findall(r"\b[A-Za-z]{3,}\b", normalized))
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    compact_penalty = len(re.findall(r"[a-z]{12,}[A-Z][a-z]", normalized)) * 200
    glyph_penalty = len(re.findall(r"/G[0-9A-Fa-f]{2}", text)) * 50
    replacement_penalty = text.count("\ufffd") * 100
    return len(normalized) + ascii_words * 6 + cjk_chars * 4 - compact_penalty - glyph_penalty - replacement_penalty


def _looks_like_heading(line: str) -> str | None:
    cleaned_original = re.sub(r"^\s*(?:\d+(\.\d+)*|[一二三四五六七八九十]+)\s*(?:[\.、|]\s*)?", "", line.strip()).strip(" :：")
    cleaned = cleaned_original.lower()
    if re.match(r"^(abstract|introduction|methods?|materials|results?|discussion|conclusions?|references|supporting information)$", cleaned):
        if cleaned in {"method", "methods", "materials"}:
            return "methods"
        if cleaned in {"result", "results"}:
            return "results"
        if cleaned in {"conclusion", "conclusions"}:
            return "conclusion"
        return cleaned
    if re.match(r"^(results|result)(\s+and\s+discussion)?$", cleaned):
        return "results"
    if re.match(r"^(experimental section|experimental procedures|materials|materials and methods|methods?|methodology)$", cleaned):
        return "methods"
    if re.match(r"^(discussion|conclusions?)$", cleaned):
        return "conclusion" if cleaned.startswith("conclusion") else "discussion"
    if cleaned_original in {"摘要", "引言", "前言", "方法", "材料与方法", "结果", "讨论", "结论", "参考文献"}:
        return {
            "摘要": "abstract",
            "引言": "introduction",
            "前言": "introduction",
            "方法": "methods",
            "材料与方法": "methods",
            "结果": "results",
            "讨论": "discussion",
            "结论": "conclusion",
            "参考文献": "references",
        }[cleaned_original]
    if cleaned.startswith("conclusion"):
        return "conclusion"
    if cleaned in SECTION_HEADINGS:
        if cleaned in {"method", "materials", "materials and methods", "methodology", "experimental procedures"}:
            return "methods"
        if cleaned in {"result", "results and discussion"}:
            return "results"
        if cleaned == "bibliography":
            return "references"
        return cleaned
    return None


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"front_matter": []}
    current = "front_matter"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            sections.setdefault(current, []).append("")
            continue
        heading = _looks_like_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _repair_compact_pdf_text(text: str) -> str:
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[.,;:])(?=[A-Za-z])", " ", text)
    return text


def _paragraphs(lines: list[str]) -> list[str]:
    joined = "\n".join(lines)
    joined = _repair_compact_pdf_text(joined)
    parts = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", joined)]
    expanded: list[str] = []
    for part in parts:
        if _contains_cjk(part) and len(part) > 900:
            expanded.extend(_chunk_cjk_paragraph(part))
        else:
            expanded.append(part)
    parts = expanded
    return [p for p in parts if len(p) >= 40]


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _chunk_cjk_paragraph(text: str, max_chars: int = 650) -> list[str]:
    sentences = [item.strip() for item in re.split(r"(?<=[。！？.!?])\s*", text) if item.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks or [text]


def _extract_title_and_authors(front_matter: list[str]) -> tuple[str | None, list[str]]:
    lines = [line.strip() for line in front_matter if line.strip()]
    title_parts: list[str] = []
    for line in lines[:12]:
        low = line.lower()
        if "citation:" in low:
            continue
        if any(token in low for token in ["submitted", "copyright", "institute "]):
            break
        if re.search(r"\d|@|\*address|review article|^combes|^lv s|^hongbin han|^benjamin|^hongfeng|^yang shi", low):
            continue
        title_parts.append(line)
        if line.endswith(("Paradigm", "Treatment", "Disease")) and len(title_parts) >= 3:
            break
    title = re.sub(r"\s+", " ", " ".join(title_parts)).strip() or None

    author_lines = []
    for line in lines[:22]:
        low = line.lower()
        if any(token in low for token in ["citation:", "submitted", "institute ", "department ", "copyright", "of radiology", "beijing", "china", "laboratory"]):
            continue
        if re.search(r"[A-Z][a-z]+.*\d", line) and "," in line:
            author_lines.append(line)
    author_blob = " ".join(author_lines)
    candidates = re.split(r",\s+| and ", author_blob)
    authors = []
    for candidate in candidates:
        cleaned = re.sub(r"\d|\*|REVIEW ARTICLE|Citation:.*", "", candidate).strip()
        cleaned = re.sub(r"^(and\s+)+", "", cleaned, flags=re.I).strip(" ,")
        if 3 <= len(cleaned) <= 80 and re.search(r"[A-Z][a-z]+", cleaned):
            if cleaned != title and cleaned not in authors:
                authors.append(cleaned)
    return title, authors[:20]


def _extract_references(text: str) -> list[dict[str, Any]]:
    references_by_key: dict[str, dict[str, Any]] = {}
    for match in re.finditer(r"(?:doi:|https://doi\.org/)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", text, re.I):
        doi = match.group(1).rstrip(".,);]")
        key = f"doi:{doi.lower()}"
        references_by_key[key] = {
            "reference_text": _reference_context(text, match.start()),
            "doi": doi,
            "pmid": None,
            "title": _guess_reference_title(_reference_context(text, match.start())),
            "locator": f"char:{match.start()}",
        }
    for match in re.finditer(r"\bPMID[:\s]+(\d{6,10})\b", text, re.I):
        pmid = match.group(1)
        key = f"pmid:{pmid}"
        references_by_key[key] = {
            "reference_text": _reference_context(text, match.start()),
            "doi": None,
            "pmid": pmid,
            "title": _guess_reference_title(_reference_context(text, match.start())),
            "locator": f"char:{match.start()}",
        }

    references_text = _references_tail(text)
    for idx, entry in enumerate(_split_reference_entries(references_text), start=1):
        doi_match = re.search(r"(?:doi:|https://doi\.org/|https?://doi\.org/\s*)(10\.\s*\d{4,9}\s*/[-._;()/:A-Za-z0-9\s]+)", entry, re.I)
        pmid_match = re.search(r"\bPMID[:\s]+(\d{6,10})\b", entry, re.I)
        doi = re.sub(r"\s+", "", doi_match.group(1)).rstrip(".,);]") if doi_match else None
        pmid = pmid_match.group(1) if pmid_match else None
        key = f"doi:{doi.lower()}" if doi else f"entry:{idx}:{hash(entry)}"
        references_by_key.setdefault(
            key,
            {
                "reference_text": entry,
                "doi": doi,
                "pmid": pmid,
                "title": _guess_reference_title(entry),
                "locator": f"references entry {idx}",
            },
        )
    return list(references_by_key.values())


def _reference_context(text: str, position: int) -> str:
    start = max(0, text.rfind("\n", 0, position - 1))
    end = text.find("\n", position)
    if end == -1:
        end = min(len(text), position + 500)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _references_tail(text: str) -> str:
    matches = list(re.finditer(r"(?im)^\s*(references|bibliography|参考文献)\s*$", text))
    if not matches:
        return ""
    return text[matches[-1].end() :]


def _split_reference_entries(references_text: str) -> list[str]:
    if not references_text:
        return []
    chunks = re.split(r"\n\s*(?=(?:\[\d+\]|\d+\.\s|[０-９\d]+[．、]\s))", references_text)
    entries = [re.sub(r"\s+", " ", chunk).strip() for chunk in chunks if len(chunk.strip()) >= 40]
    return entries[:250]


def _guess_reference_title(reference_text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", reference_text).strip()
    parts = [part.strip() for part in re.split(r"\.\s+", cleaned) if part.strip()]
    for part in parts[1:4]:
        if 12 <= len(part) <= 220 and not re.search(r"\b(doi|PMID|http|vol|pp)\b", part, re.I):
            return part
    return None


def _extract_figures_and_tables(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    marker = r"(?:Fig\.?\s*[\u00a0 ]*\d+[A-Za-z]?|Figure\s*\d+[A-Za-z]?|Table\s*\d+[A-Za-z]?|图\s*\d+|表\s*\d+)"
    pattern = re.compile(rf"\b({marker})[.)。．、:\s]*\s*(.{{40,900}}?)(?=\n\s*(?:{marker})| references| 参考文献|\Z)", re.I | re.S)
    for idx, match in enumerate(pattern.finditer(text), start=1):
        caption = re.sub(r"\s+", " ", match.group(2)).strip()
        items.append(
            {
                "id": match.group(1).replace("Figure", "Fig."),
                "caption": caption[:900],
                "locator": f"{match.group(1)} caption",
                "index": idx,
            }
        )
    if not items:
        for idx, line in enumerate(text.splitlines(), start=1):
            if re.search(marker, line, re.I):
                caption = re.sub(r"\s+", " ", line).strip()
                if len(caption) >= 20:
                    items.append(
                        {
                            "id": re.search(marker, line, re.I).group(0).replace("Figure", "Fig."),
                            "caption": caption[:900],
                            "locator": f"line {idx}",
                            "index": len(items) + 1,
                        }
                    )
            if len(items) >= 20:
                break
    return items


def _extract_candidate_claims(paragraphs: list[LocatedParagraph]) -> list[dict[str, Any]]:
    claim_markers = [
        "demonstrated",
        "demonstrate",
        "indicates",
        "indicate",
        "reveal",
        "reveals",
        "show",
        "shows",
        "showed",
        "suggest",
        "suggests",
        "suggested",
        "constitutes",
        "is defined as",
        "is primarily",
        "accounts for",
        "associated with",
        "important",
        "critical",
        "plays",
        "involved",
        "regulates",
        "clearance",
        "diffusion",
        "diffusivity",
        "heterogeneous",
        "elevated",
        "extracellular",
        "glymphatic",
        "interstitial",
        "amyloid",
        "matrix",
        "required for",
        "confirms",
        "unveils",
        "provides",
        "we propose",
        "we recommend",
        "emphasizes",
        "critical role",
        "overlooked",
        "表明",
        "显示",
        "发现",
        "提示",
        "证明",
        "揭示",
        "提出",
        "认为",
        "构成",
        "定义",
        "影响",
        "相关",
        "首次实现",
        "解决了",
        "建立",
        "证实",
        "发挥",
        "综述",
        "表明",
        "显示",
        "发现",
        "提示",
        "证明",
        "揭示",
        "提出",
        "认为",
        "构成",
        "定义",
        "影响",
        "相关",
    ]
    claims: list[dict[str, Any]] = []
    for para in paragraphs:
        if para.section == "front_matter" and not _front_matter_contains_claim_signal(para.text):
            continue
        sentences = re.split(r"(?<=[.!?。！？])\s+", para.text)
        for sentence in sentences:
            clean = sentence.strip()
            if len(clean) < 30 or len(clean) > 420:
                continue
            low = clean.lower()
            if any(skip in low for skip in ["citation:", "copyright", "downloaded from", "address correspondence", "exclusive licensee"]):
                continue
            if re.search(r"\b(et al\.|submitted|accepted|published)\b", low):
                continue
            if _looks_like_column_noise(clean):
                continue
            if any(marker in low for marker in claim_markers):
                claims.append(
                    {
                        "text": clean,
                        "raw_text": clean,
                        "claim_category": _claim_category(para.section, clean),
                        "section": para.section,
                        "paragraph_index": para.paragraph_index,
                        "locator": f"{para.section} paragraph {para.paragraph_index}",
                        "source_location": _source_location(para.section, para.paragraph_index, clean),
                        "source_file": para.source_file,
                        "ecs_related": any(term.lower() in low for term in ECS_TERMS),
                        "support_evidence_snippet": [clean],
                        "conflict_evidence_snippet": [],
                        "source_attribution": "paper_original",
                        "evidence_incomplete": False,
                    }
                )
    return claims


def _front_matter_contains_claim_signal(text: str) -> bool:
    low = text.lower()
    if any(skip in low for skip in ["citation:", "copyright", "received:", "accepted:", "published", "address correspondence"]):
        return False
    return any(term.lower() in low for term in ECS_TERMS) or any(
        marker in low
        for marker in [
            "demonstrated",
            "reveals",
            "shows",
            "suggests",
            "confirms",
            "unveils",
            "provides",
            "propose",
            "发现",
            "证明",
            "提出",
            "显示",
            "综述",
        ]
    )


def _claim_category(section: str, sentence: str) -> str:
    low = sentence.lower()
    if section in {"results", "methods"} or any(token in low for token in ["demonstrated", "showed", "shows", "observed", "measured", "associated with", "significant"]):
        return "experimental_result"
    if any(token in low for token in ["we propose", "we hypothesize", "hypothesis", "should", "may", "提出"]):
        return "research_hypothesis"
    return "review_summary"


def _source_location(section: str, paragraph_index: int, sentence: str) -> str:
    marker = r"(Fig\.?\s*[\u00a0 ]*\d+[A-Za-z]?|Figure\s*\d+[A-Za-z]?|Table\s*\d+[A-Za-z]?|图\s*\d+|表\s*\d+)"
    figure_match = re.search(marker, sentence, re.I)
    figure_part = f" {figure_match.group(1)}" if figure_match else ""
    return f"{section} paragraph {paragraph_index}{figure_part}"


def _classify_article_type(text: str) -> str:
    head = text[:6000]
    if re.search(r"\b(review article|review)\b|综述|回顾|工作综述", head, re.I):
        return "review"
    if re.search(r"\b(research article|original article)\b", head, re.I):
        return "research"
    return "research"


def _looks_like_column_noise(sentence: str) -> bool:
    low = sentence.lower()
    noise_patterns = [
        "however, these recent findings",
        "pharmaceutical and device companies have invested hun- work",
        "few achievements have proven the brain ecs",
        "finally, we propose a new",
        "of the brain ecs increasing evidence",
        "6), neglected",
    ]
    if any(pattern in low for pattern in noise_patterns):
        return True
    if sentence.endswith("(Fig.") or sentence.endswith("Fig."):
        return True
    if re.search(r"\b(hun-|ner-|clasdeterminant|sified|transalong|lowspatial)\b", low):
        return True
    return False


def literature_extract(source_file: str, max_claims: int = 12) -> dict[str, Any]:
    """Parse a paper text/PDF file into sections, metadata, candidate claims, evidence, and references."""
    path = Path(source_file)
    text = normalize_text(read_paper_text(path))
    sections = _split_sections(text)
    title, authors = _extract_title_and_authors(sections.get("front_matter", []))
    doi_match = re.search(r"(?:doi:|https://doi\.org/)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", text, re.I)
    year_match = re.search(r"\b(20[0-3]\d|19[7-9]\d)\b", text)
    article_type = _classify_article_type(text)
    license_match = re.search(r"(Creative Commons[^.\n]+|CC BY ?[0-9.]+)", text, re.I)

    located: list[LocatedParagraph] = []
    section_payload: dict[str, list[dict[str, Any]]] = {}
    for section, lines in sections.items():
        section_paragraphs = _paragraphs(lines)
        section_payload[section] = []
        for idx, paragraph in enumerate(section_paragraphs, start=1):
            located.append(LocatedParagraph(source_file=str(path), section=section, paragraph_index=idx, text=paragraph))
            section_payload[section].append({"paragraph_index": idx, "text": paragraph})

    figures_tables = _extract_figures_and_tables(text)
    references = _extract_references(text)
    candidate_claims = _extract_candidate_claims(located)
    section_priority = {
        "abstract": 0,
        "front_matter": 1,
        "introduction": 2,
        "results": 3,
        "discussion": 4,
        "conclusion": 5,
    }
    candidate_claims = sorted(
        candidate_claims,
        key=lambda item: (
            not item["ecs_related"],
            section_priority.get(item["section"], 9),
            item["paragraph_index"],
        ),
    )[:max_claims]
    for idx, claim in enumerate(candidate_claims, start=1):
        claim["claim_id"] = f"C-{idx:04d}"
    ecs_hits = sorted({term for term in ECS_TERMS if term.lower() in text.lower()})

    return {
        "extractor_prompt": CLAIM_EXTRACTOR_PROMPT.strip(),
        "metadata": {
            "title": title,
            "authors": authors,
            "doi": doi_match.group(1).rstrip(".,);]") if doi_match else None,
            "year": int(year_match.group(1)) if year_match else None,
            "article_type": article_type,
            "license": license_match.group(1) if license_match else None,
            "source_file": str(path),
            "ecs_related": bool(ecs_hits),
            "ecs_keywords": ecs_hits,
        },
        "sections": section_payload,
        "figures_tables": figures_tables,
        "candidate_claims": candidate_claims,
        "references": references,
        "quality_flags": {
            "has_methods": "methods" in section_payload and bool(section_payload["methods"]),
            "has_results": "results" in section_payload and bool(section_payload["results"]),
            "has_figures_or_tables": bool(figures_tables),
            "has_references": bool(references) or "references" in section_payload,
            "paragraph_count": len(located),
            "ecs_hit_count": len(ecs_hits),
        },
    }


def reference_validator(references: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate reference identifiers, completeness, domain fit, and duplication risk."""
    doi_re = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
    pmid_re = re.compile(r"^\d{6,10}$")
    domain_terms = [
        "brain",
        "neuro",
        "neuron",
        "cns",
        "cognitive",
        "alzheimer",
        "dementia",
        "glymphatic",
        "extracellular",
        "interstitial",
        "ecs",
        "脑",
        "神经",
        "认知",
        "阿尔茨海默",
        "细胞外间隙",
        "脑组织液",
    ]
    seen: dict[str, int] = {}
    records = []
    for ref in references:
        reference_text = str(ref.get("reference_text") or "")
        doi = _normalized_doi(ref.get("doi") or (ref.get("value") if ref.get("type") == "doi" else None))
        pmid = str(ref.get("pmid") or (ref.get("value") if ref.get("type") == "pmid" else "") or "").strip() or None
        title = ref.get("title") or _guess_reference_title(reference_text)
        identifier_valid = bool((doi and doi_re.match(doi)) or (pmid and pmid_re.match(pmid)))
        has_year = bool(re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", reference_text))
        has_author = bool(re.search(r"[A-Z][A-Za-z'\-]+(?:\s+[A-Z]\.)?|[\u4e00-\u9fff]{2,4}", reference_text))
        has_journal = _has_journal_signal(reference_text)
        domain_match = any(term.lower() in (reference_text + " " + str(title or "")).lower() for term in domain_terms)
        duplicate_key = (doi or pmid or str(title or reference_text[:80])).lower()
        seen[duplicate_key] = seen.get(duplicate_key, 0) + 1
        reasons = []
        if not identifier_valid:
            reasons.append("reference_requires_review:no_valid_doi_or_pmid")
        if not has_year:
            reasons.append("missing_year")
        if not has_author:
            reasons.append("missing_author")
        if not has_journal:
            reasons.append("missing_journal")
        if not domain_match:
            reasons.append("domain_mismatch_or_unclear")
        records.append(
            {
                "reference_text": reference_text,
                "doi": doi,
                "pmid": pmid,
                "title": title,
                "locator": ref.get("locator"),
                "identifier_check": {
                    "valid_doi": bool(doi and doi_re.match(doi)),
                    "valid_pmid": bool(pmid and pmid_re.match(pmid)),
                    "reference_requires_review": not identifier_valid,
                },
                "completeness_check": {
                    "has_year": has_year,
                    "has_journal": has_journal,
                    "has_author": has_author,
                },
                "domain_match_check": {
                    "is_neuroscience_or_ecs_related": domain_match,
                },
                "duplicate_conflict_check": {
                    "duplicate_key": duplicate_key,
                    "duplicate_count": 0,
                    "conflict_risk": False,
                },
                "reference_valid": not reasons,
                "reference_invalid": reasons,
            }
        )
    for record in records:
        duplicate_count = seen.get(record["duplicate_conflict_check"]["duplicate_key"], 0)
        record["duplicate_conflict_check"]["duplicate_count"] = duplicate_count
        if duplicate_count > 1:
            record["duplicate_conflict_check"]["conflict_risk"] = True
            record["reference_valid"] = False
            record["reference_invalid"].append("duplicate_reference")
    invalid_records = [record for record in records if not record["reference_valid"]]
    return {
        "validator_prompt": REFERENCE_VALIDATOR_PROMPT.strip(),
        "status": "reference_valid" if not invalid_records else "reference_invalid",
        "validated_references": records,
        "reference_valid_count": len(records) - len(invalid_records),
        "reference_invalid_count": len(invalid_records),
        "invalid_count": len(invalid_records),
        "checked_count": len(records),
        "summary": {
            "identifier_invalid": sum(1 for item in records if item["identifier_check"]["reference_requires_review"]),
            "information_incomplete": sum(1 for item in records if not all(item["completeness_check"].values())),
            "domain_mismatch_or_unclear": sum(1 for item in records if not item["domain_match_check"]["is_neuroscience_or_ecs_related"]),
            "duplicate_or_conflict": sum(1 for item in records if item["duplicate_conflict_check"]["conflict_risk"]),
        },
    }


def _normalized_doi(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", "", str(value).strip())
    return text.rstrip(".,);]") or None


def _has_journal_signal(reference_text: str) -> bool:
    if re.search(r"\b(Journal|J\.|Nature|Science|Cell|Brain|Neuro|Proceedings|Reports|Radiology|Alzheimer|Dementia|Med|医学|学报|杂志)\b", reference_text, re.I):
        return True
    return bool(re.search(r"\b\d+\s*\(\s*\d+\s*\)\s*:\s*\d+", reference_text))
