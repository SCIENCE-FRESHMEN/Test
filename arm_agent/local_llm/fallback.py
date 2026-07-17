from __future__ import annotations

from pydantic import BaseModel


class LocalFallbackLLM(BaseModel):
    model_name: str = "local-rule-fallback"
    model_infer: bool = True

    def generate(self, prompt: str, max_sentences: int = 3) -> dict:
        sentences = [part.strip() for part in prompt.replace("\n", " ").split(".") if len(part.strip()) > 20]
        summary = ". ".join(sentences[:max_sentences])
        if summary:
            summary += "."
        return {"text": summary, "model": self.model_name, "model_infer": True, "trace": [{"stage": "local_fallback_generate", "sentences": len(sentences)}]}


def local_generate_summary(text: str, max_sentences: int = 3) -> dict:
    return LocalFallbackLLM().generate(text, max_sentences=max_sentences)
