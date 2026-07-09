"""4 tests for ForenseExporter._build_acto_5_ficha_forense_municipal / export_..."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.exporters.forense_exporter import ForenseExporter

CONFIG_PATH   = PROJECT_ROOT / "config" / "forense_exporter_config.json"
OUTPUT_PATH   = PROJECT_ROOT / "data" / "dashboard" / "acto_5_ficha_forense_municipal.json"
SNAPSHOT_DIR  = PROJECT_ROOT / "tests" / "snapshots"
SNAPSHOT_FILE = SNAPSHOT_DIR / "acto_5_ficha_forense_municipal.json"


@pytest.fixture(scope="module")
def built_output() -> dict:
    exp = ForenseExporter(CONFIG_PATH)
    exp.export_acto_5_ficha_forense_municipal()
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Schema validation (passes if export does not raise)
# ---------------------------------------------------------------------------

def test_schema_validation(built_output: dict) -> None:
    meta = built_output["metadata"]
    assert "generated_at"             in meta
    assert "source_tables"            in meta
    assert "min_total_casos"          in meta
    assert "municipios_con_vs"        in meta
    assert "municipios_con_vif"       in meta
    assert "municipios_sin_cobertura" in meta
    assert meta["min_total_casos"] == 30
    assert isinstance(built_output["municipios"], dict)
    # Spot-check a random municipality structure
    first_cod = next(iter(built_output["municipios"]))
    mun = built_output["municipios"][first_cod]
    for key in ["cod_municipio", "nombre_es",
                "has_violencia_sexual_profile", "has_vif_profile",
                "violencia_sexual", "violencia_intrafamiliar"]:
        assert key in mun, f"Missing key '{key}' in municipality {first_cod}"


# ---------------------------------------------------------------------------
# 2. Canonical snapshot (created on first run, locked after)
# ---------------------------------------------------------------------------

def _strip_timestamps(payload: dict) -> dict:
    """Return a copy of payload with generated_at replaced by a stable sentinel."""
    import copy
    p = copy.deepcopy(payload)
    if "metadata" in p:
        p["metadata"]["generated_at"] = "__TIMESTAMP__"
    return p


def test_canonical_snapshot(built_output: dict) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stable = _strip_timestamps(built_output)
    snapshot = json.dumps(stable, indent=2, sort_keys=True, ensure_ascii=False)

    if not SNAPSHOT_FILE.exists():
        SNAPSHOT_FILE.write_text(snapshot, encoding="utf-8")
        pytest.skip(f"Snapshot created: {SNAPSHOT_FILE}")

    assert SNAPSHOT_FILE.read_text(encoding="utf-8") == snapshot


# ---------------------------------------------------------------------------
# 3. Asymmetric threshold behavior: at least one municipality has exactly one
#    profile (VS but not VIF, or VIF but not VS)
# ---------------------------------------------------------------------------

def test_threshold_asymmetric_behavior(built_output: dict) -> None:
    municipios = built_output["municipios"]
    has_asymmetric = False

    for mun in municipios.values():
        has_vs  = mun["has_violencia_sexual_profile"]
        has_vif = mun["has_vif_profile"]
        if has_vs != has_vif:
            has_asymmetric = True
            if has_vs:
                assert mun["violencia_sexual"] is not None
                assert mun["violencia_intrafamiliar"] is None
            else:
                assert mun["violencia_sexual"] is None
                assert mun["violencia_intrafamiliar"] is not None

    assert has_asymmetric, (
        "Expected at least one municipality with asymmetric VS/VIF profiles"
    )


# ---------------------------------------------------------------------------
# 4. Municipalities below threshold for BOTH types are excluded from 'municipios'
#    and listed in metadata.municipios_sin_cobertura
# ---------------------------------------------------------------------------

def test_below_threshold_both_types_excluded_from_municipios(built_output: dict) -> None:
    sin_cobertura = set(built_output["metadata"]["municipios_sin_cobertura"])
    municipios_keys = set(built_output["municipios"].keys())

    overlap = sin_cobertura & municipios_keys
    assert len(overlap) == 0, (
        f"sin_cobertura municipalities found in municipios dict: {overlap}"
    )
