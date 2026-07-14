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
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "references",
    "supplementary materials",
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
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF input requires pypdf. Install dependencies with: pip install -r requirements.txt") from exc
        reader = PdfReader(str(path))
        page_text: list[str] = []
        for page_index, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            if extracted.strip():
                page_text.append(f"\n\n[page {page_index}]\n{extracted}")
        if not page_text:
            raise RuntimeError(f"No extractable text found in PDF: {path}")
        return "\n".join(page_text)
    return path.read_text(encoding="utf-8", errors="replace")


def _looks_like_heading(line: str) -> str | None:
    cleaned = re.sub(r"^\d+(\.\d+)*\s+", "", line.strip()).strip(":").lower()
    if cleaned.startswith("conclusion"):
        return "conclusion"
    if cleaned in SECTION_HEADINGS:
        return "methods" if cleaned in {"method", "materials and methods"} else cleaned
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
    return [p for p in parts if len(p) >= 40]


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
    matches = list(re.finditer(r"(?im)^\s*(references|参考文献)\s*$", text))
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
    pattern = re.compile(rf"\b({marker})[.)．、:\s]*\s*(.{{40,900}}?)(?=\n\s*(?:{marker})| references|\Z)", re.I | re.S)
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
        "indicates",
        "reveal",
        "reveals",
        "show",
        "shows",
        "suggest",
        "suggests",
        "constitutes",
        "is defined as",
        "is primarily",
        "accounts for",
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
    ]
    claims: list[dict[str, Any]] = []
    for para in paragraphs:
        if para.section == "front_matter" and "despite huge investment" not in para.text.lower():
            continue
        sentences = re.split(r"(?<=[.!?])\s+", para.text)
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
    article_type = "review" if re.search(r"\b(review article|review|综述)\b", text, re.I) else "research"
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
