from __future__ import annotations

from pathlib import Path

from lbo.io.config import CONFIG_DIR, load_yaml
from lbo.schemas.models import EngineAssumptions, ScenarioName


def load_scenario_defaults(
    scenario: ScenarioName = "Base",
    path: str | Path | None = None,
) -> EngineAssumptions:
    config = load_yaml(path or CONFIG_DIR / "scenarios.yaml")
    scenarios = config.get("scenarios", {})
    if scenario not in scenarios:
        raise ValueError(f"Scenario '{scenario}' is not defined in scenarios config")
    return EngineAssumptions(scenario=scenario, **scenarios[scenario])

