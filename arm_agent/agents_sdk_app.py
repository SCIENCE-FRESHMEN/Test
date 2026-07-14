from __future__ import annotations

from typing import Any

from .config import get_settings
from .pipeline import PaperToARMOrchestrator
from .tools import literature_extract, reference_validator


ORCHESTRATOR_INSTRUCTIONS = """
You are the NEURONCLAW A-track Paper-to-ARM controller.
You may use only two domain tools: literature_extract and reference_validator.
Every scientific claim must keep a source locator and exact quote. If validation fails,
return the blocked failure report and do not invent missing paper content.
"""


def build_deepseek_agents_model(api_key: str, base_url: str = "https://api.deepseek.com", model: str = "deepseek-v4-pro") -> Any:
    """Create an Agents SDK chat-completions model backed by DeepSeek's OpenAI-compatible API."""
    try:
        from agents import OpenAIChatCompletionsModel
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional environment package.
        raise RuntimeError("Install optional dependencies with: pip install openai-agents openai") from exc
    settings = get_settings()
    return OpenAIChatCompletionsModel(
        model=model,
        openai_client=AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=settings.api_retry_attempts,
            timeout=settings.api_timeout_seconds,
        ),
    )


def build_agents_sdk_orchestrator(model: str | Any = "deepseek-v4-pro") -> Any:
    """Build an OpenAI Agents SDK Agent when the optional SDK is installed.

    The deterministic CLI pipeline remains the reference implementation for tests and demos.
    This wrapper exists so the same two tools can be exposed through the Agents SDK runtime
    during live presentations.
    """
    try:
        from agents import Agent, function_tool
    except ImportError as exc:  # pragma: no cover - depends on optional environment package.
        raise RuntimeError("Install optional dependency with: pip install openai-agents") from exc

    lit_tool = function_tool(literature_extract, strict_mode=False)
    ref_tool = function_tool(reference_validator, strict_mode=False)
    return Agent(
        name="NEURONCLAW Paper-to-ARM Orchestrator",
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        model=model,
        tools=[lit_tool, ref_tool],
    )


def run_deterministic_orchestrator(paper_files: list[str], output_dir: str = "outputs") -> dict[str, Any]:
    """Run the reproducible controller used by the command-line demo."""
    result = PaperToARMOrchestrator(output_dir=output_dir).run(paper_files)
    return result.model_dump()
