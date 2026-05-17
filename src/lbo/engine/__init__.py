from __future__ import annotations

from lbo.engine.adjustment_engine import AdjustmentInputs, build_default_adjustments, run_adjusted_return_model
from lbo.engine.sensitivity_engine import run_standardized_sensitivity
from lbo.engine.sop_engine import generate_sop_analysis

__all__ = [
    "build_snapshot",
    "AdjustmentInputs",
    "build_default_adjustments",
    "generate_sop_analysis",
    "load_scenario_defaults",
    "run_adjusted_return_model",
    "run_python_engine",
    "run_standardized_sensitivity",
]


def __getattr__(name: str):
    if name == "build_snapshot":
        from lbo.engine.snapshot import build_snapshot

        return build_snapshot
    if name == "load_scenario_defaults":
        from lbo.engine.assumptions import load_scenario_defaults

        return load_scenario_defaults
    if name == "run_python_engine":
        from lbo.engine.python_engine import run_python_engine

        return run_python_engine
    raise AttributeError(f"module 'lbo.engine' has no attribute {name!r}")
