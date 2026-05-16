from __future__ import annotations

from lbo.schemas.models import CoreSheets


def detect_core_sheets(sheet_names: list[str], aliases_config: dict) -> CoreSheets:
    roles = aliases_config.get("roles", {})
    detected: dict[str, str | None] = {}
    missing: list[str] = []

    for role, role_config in roles.items():
        match = _match_sheet(sheet_names, role_config.get("aliases", []))
        detected[role] = match
        if role_config.get("required", False) and match is None:
            missing.append(role)

    return CoreSheets(**detected, missing_roles=missing)


def _match_sheet(sheet_names: list[str], aliases: list[str]) -> str | None:
    normalized = {sheet: _normalize(sheet) for sheet in sheet_names}
    normalized_aliases = [_normalize(alias) for alias in aliases]

    for alias in normalized_aliases:
        for sheet, normalized_sheet in normalized.items():
            if normalized_sheet == alias:
                return sheet

    for alias in normalized_aliases:
        for sheet, normalized_sheet in normalized.items():
            if alias and alias in normalized_sheet:
                return sheet

    return None


def _normalize(value: str) -> str:
    return value.casefold().replace(" ", "").replace("_", "").replace("-", "")

