from __future__ import annotations

from lbo.adapters.base_adapter import AdapterMatch, BaseWorkbookAdapter


def detect_best_adapter(workbook, adapters: list[BaseWorkbookAdapter]) -> AdapterMatch:
    if not adapters:
        raise ValueError("No workbook adapters were provided")

    matches = [adapter.can_handle(workbook) for adapter in adapters]
    return max(matches, key=lambda match: match.confidence)

