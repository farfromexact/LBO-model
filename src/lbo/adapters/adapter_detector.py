from __future__ import annotations

from lbo.adapters.base_adapter import AdapterMatch, BaseWorkbookAdapter
from lbo.adapters.generic_lbo_adapter import GenericLBOAdapter


def detect_best_adapter(workbook, adapters: list[BaseWorkbookAdapter]) -> AdapterMatch:
    candidates: list[BaseWorkbookAdapter] = adapters or []
    generic = next((adapter for adapter in candidates if isinstance(adapter, GenericLBOAdapter)), None)
    if generic is None:
        generic = GenericLBOAdapter()
        candidates.append(generic)

    matches = [adapter.can_handle(workbook) for adapter in candidates]
    best = max(matches, key=lambda match: match.confidence_score)
    if best.confidence_score >= 0.60 and best.template_id != "generic_lbo":
        return best

    generic_match = generic.can_handle(workbook)
    return generic_match.model_copy(
        update={
            "confidence_score": min(generic_match.confidence_score, 0.59),
            "warnings": generic_match.warnings + ["No specific adapter reached 60% confidence; using generic fallback."],
        }
    )
