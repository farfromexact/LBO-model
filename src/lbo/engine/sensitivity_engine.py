from __future__ import annotations

from pydantic import BaseModel, Field

from lbo.schemas.standard_model import StandardModel


class SensitivityCase(BaseModel):
    case_name: str
    exit_multiple: float
    ebitda_cagr: float
    implied_exit_ev: float | None
    implied_moic: float | None
    warning: str | None = None


class SensitivityResult(BaseModel):
    cases: list[SensitivityCase] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def run_standardized_sensitivity(model: StandardModel) -> SensitivityResult:
    ebitda = model.metrics.get("ebitda")
    entry_ev = model.valuation.entry_ev
    sponsor_equity = model.returns.sponsor_equity_invested
    if not ebitda or not ebitda.value or not entry_ev.value or not sponsor_equity.value:
        return SensitivityResult(warnings=["Missing EBITDA, Entry EV, or Sponsor Equity; sensitivity not calculated."])

    entry_multiple = entry_ev.value / ebitda.value if ebitda.value else None
    if entry_multiple is None:
        return SensitivityResult(warnings=["Could not infer entry multiple; sensitivity not calculated."])

    cases: list[SensitivityCase] = []
    for exit_multiple_delta in [-1.0, 0.0, 1.0]:
        for cagr in [-0.05, 0.0, 0.05]:
            exit_multiple = max(entry_multiple + exit_multiple_delta, 0)
            implied_ebitda = ebitda.value * ((1 + cagr) ** 5)
            implied_exit_ev = implied_ebitda * exit_multiple
            implied_moic = implied_exit_ev / abs(sponsor_equity.value) if sponsor_equity.value else None
            cases.append(
                SensitivityCase(
                    case_name=f"{exit_multiple:.1f}x / {cagr:.0%} EBITDA CAGR",
                    exit_multiple=exit_multiple,
                    ebitda_cagr=cagr,
                    implied_exit_ev=implied_exit_ev,
                    implied_moic=implied_moic,
                )
            )
    return SensitivityResult(cases=cases)

