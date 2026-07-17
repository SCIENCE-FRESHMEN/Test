from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from arm_agent.tools import normalize_text, read_paper_text


class RAGDocument(BaseModel):
    doc_id: str
    source_file: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LocalRAGIndex(BaseModel):
    index_id: str
    documents: list[RAGDocument]
    vocabulary: list[str]
    model_infer: bool = True

    def query(self, query_text: str, top_k: int = 3) -> dict[str, Any]:
        query_vec = _tf(query_text, self.vocabulary)
        scored = []
        for doc in self.documents:
            score = _cosine(query_vec, _tf(doc.text, self.vocabulary))
            scored.append({"doc_id": doc.doc_id, "source_file": doc.source_file, "score": round(score, 4), "text": doc.text[:800], "metadata": doc.metadata})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return {"query": query_text, "top_k": top_k, "matches": scored[:top_k], "trace": [{"stage": "local_rag_query", "documents": len(self.documents)}]}


def build_rag_index_from_files(source_files: list[str], chunk_size: int = 900) -> LocalRAGIndex:
    docs: list[RAGDocument] = []
    for source_file in source_files:
        text = normalize_text(read_paper_text(Path(source_file)))
        chunks = _chunk_text(text, chunk_size)
        for index, chunk in enumerate(chunks, start=1):
            docs.append(RAGDocument(doc_id=f"{Path(source_file).stem}-{index:03d}", source_file=source_file, text=chunk, metadata={"chunk_index": index}))
    vocabulary = sorted({token for doc in docs for token in _tokens(doc.text) if len(token) > 2})[:5000]
    return LocalRAGIndex(index_id="local-brain-rag", documents=docs, vocabulary=vocabulary)


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) > chunk_size and buffer:
            chunks.append(buffer.strip())
            buffer = paragraph
        else:
            buffer = f"{buffer}\n{paragraph}" if buffer else paragraph
    if buffer:
        chunks.append(buffer.strip())
    return chunks or [text[:chunk_size]]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", text.lower())


def _tf(text: str, vocab: list[str]) -> list[float]:
    counts = Counter(_tokens(text))
    total = sum(counts.values()) or 1
    return [counts[token] / total for token in vocab]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
