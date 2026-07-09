"""Shared helpers for dashboard exporters."""
from __future__ import annotations

import json
import math
from pathlib import Path

import jsonschema


def write_json_validated(payload: dict, schema_path: Path, output_path: Path) -> None:
    """Validate *payload* against JSON Schema at *schema_path*, then write to *output_path*.

    Raises ValueError if schema validation fails.
    """
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"Schema validation failed: {exc.message}  path={list(exc.absolute_path)}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def round_pct(value: float, decimals: int = 1) -> float:
    """Round a percentage value to *decimals* places, returning a plain float."""
    return round(float(value), decimals)


def to_int_safe(value) -> int | None:
    """Convert numpy/pandas scalar to Python int; return None for NaN/Inf/None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return int(f)


def normalize_dept_key(s: str) -> str:
    """'VALLE DEL CAUCA' → 'VALLE_DEL_CAUCA'.  Preserves accented characters."""
    return s.strip().upper().replace(" ", "_")
