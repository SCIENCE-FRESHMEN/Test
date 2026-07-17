from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtensionSettings:
    online_search_enabled: bool = True
    online_search_default_platforms: tuple[str, ...] = ("PubMed", "arXiv")
    online_search_year_from: int = 2020
    online_search_year_to: int = 2026
    figure_parse_max_tables: int = 20
    increment_export_enabled: bool = True
    handoff_heavy_task_threshold: int = 5


def get_extension_settings() -> ExtensionSettings:
    return ExtensionSettings()
