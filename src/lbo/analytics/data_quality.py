from __future__ import annotations

from lbo.schemas.standard_model import StandardModel


def summarize_data_quality(model: StandardModel) -> dict[str, int | float]:
    return {
        "coverage": model.extraction_coverage,
        "missing_fields": len(model.missing_fields),
        "warnings": len(model.metadata.warnings),
        "excel_errors": len(model.metadata.excel_errors),
        "sensitivities": len(model.sensitivities),
    }
