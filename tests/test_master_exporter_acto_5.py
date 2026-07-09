"""9 tests for MasterExporter._build_acto_5_municipios / export_acto_5_municipios."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.exporters.master_exporter import MasterExporter

CONFIG_PATH  = str(PROJECT_ROOT / "config" / "master_exporter_config.json")
OUTPUT_PATH  = PROJECT_ROOT / "data" / "dashboard" / "acto_5_municipios.json"
SNAPSHOT_DIR = PROJECT_ROOT / "tests" / "snapshots"
SNAPSHOT_FILE = SNAPSHOT_DIR / "acto_5_municipios_canaries.json"
EXCLUDED     = {"27150", "27493"}


@pytest.fixture(scope="module")
def built_output() -> dict:
    exp = MasterExporter(config_path=CONFIG_PATH)
    exp.export_acto_5_municipios()
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Schema validation (passes if export_acto_5_municipios does not raise)
# ---------------------------------------------------------------------------

def test_schema_validation(built_output: dict) -> None:
    assert "municipios" in built_output
    assert "metadata" in built_output
    assert "departamentos_disponibles" in built_output


# ---------------------------------------------------------------------------
# 2. Total municipality count
# ---------------------------------------------------------------------------

def test_total_municipios_count(built_output: dict) -> None:
    assert len(built_output["municipios"]) == 179
    assert built_output["metadata"]["total_municipios"] == 179


# ---------------------------------------------------------------------------
# 3. Excluded municipalities are present but flagged
# ---------------------------------------------------------------------------

def test_excluded_municipalities_flagged(built_output: dict) -> None:
    for cod in EXCLUDED:
        assert cod in built_output["municipios"], f"Excluded code {cod} missing from output"
        mun = built_output["municipios"][cod]
        assert mun["excluido_del_modelo"] is True
        assert mun["cluster_id"] is None
        assert mun["coefficient_contributions"] is None
        assert mun["icv_ranking"] is None


# ---------------------------------------------------------------------------
# 4. Included municipalities have 4 contribution items (Cali as canary)
# ---------------------------------------------------------------------------

def test_included_municipalities_have_contributions(built_output: dict) -> None:
    mun = built_output["municipios"]["76001"]
    assert mun["excluido_del_modelo"] is False
    contribs = mun["coefficient_contributions"]
    assert contribs is not None
    assert len(contribs) == 4
    for c in contribs:
        assert "feature_id" in c
        assert "feature_label_es" in c
        assert isinstance(c["coefficient"], (int, float))
        assert isinstance(c["contribution"], (int, float))


# ---------------------------------------------------------------------------
# 5. departamentos_disponibles covers all 4 Pacific departments
# ---------------------------------------------------------------------------

def test_departamentos_disponibles_covers_4_pacific(built_output: dict) -> None:
    dept_codes = {d["codigo_dane_dept"] for d in built_output["departamentos_disponibles"]}
    assert dept_codes == {"76", "19", "52", "27"}
    for dept in built_output["departamentos_disponibles"]:
        assert len(dept["municipios_codigos"]) > 0


# ---------------------------------------------------------------------------
# 6. All narrative_values_es dicts have 6 non-empty string values
# ---------------------------------------------------------------------------

def test_narrative_placeholders_resolved(built_output: dict) -> None:
    keys = [
        "municipio_placeholder", "cluster_placeholder", "icv_placeholder",
        "ranking_placeholder", "tipo_placeholder", "tasa_placeholder",
    ]
    for cod, mun in built_output["municipios"].items():
        nv = mun["narrative_values_es"]
        for key in keys:
            assert isinstance(nv[key], str) and len(nv[key]) > 0, (
                f"Empty narrative placeholder '{key}' for {cod}"
            )


# ---------------------------------------------------------------------------
# 7. Sparkline years are monotonically increasing
# ---------------------------------------------------------------------------

def test_sparkline_years_monotonic(built_output: dict) -> None:
    for cod, mun in built_output["municipios"].items():
        years = mun["sparkline_icv"]["years"]
        assert len(years) >= 1, f"Empty sparkline for {cod}"
        assert years == sorted(years), f"Non-monotonic sparkline for {cod}"
        values = mun["sparkline_icv"]["values"]
        assert len(values) == len(years)
        for v in values:
            assert isinstance(v, (int, float)), f"Non-numeric sparkline value for {cod}: {v!r}"


# ---------------------------------------------------------------------------
# 8. Stratified canary snapshot (6 canaries; created on first run, locked after)
# ---------------------------------------------------------------------------

def test_stratified_canary_snapshot(built_output: dict) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    municipios = built_output["municipios"]

    canary_cods: list[str] = list(EXCLUDED)  # 27150, 27493 — always included
    cali = "76001"
    if cali in municipios:
        canary_cods.append(cali)

    # One Alta severidad, one Moderada-Baja
    for cod, mun in municipios.items():
        if cod in EXCLUDED or cod in canary_cods:
            continue
        if mun["cluster_id"] == 1 and sum(1 for c in canary_cods if c not in EXCLUDED) == 1:
            canary_cods.append(cod)
        elif mun["cluster_id"] == 0 and sum(1 for c in canary_cods if c not in EXCLUDED) == 2:
            canary_cods.append(cod)
        if len(canary_cods) >= 5:
            break

    # One Chocó non-excluded
    for cod, mun in municipios.items():
        if cod.startswith("27") and cod not in EXCLUDED and cod not in canary_cods:
            canary_cods.append(cod)
            break

    canaries = {cod: municipios[cod] for cod in canary_cods if cod in municipios}
    snapshot = json.dumps(canaries, indent=2, sort_keys=True, ensure_ascii=False)

    if not SNAPSHOT_FILE.exists():
        SNAPSHOT_FILE.write_text(snapshot, encoding="utf-8")
        pytest.skip(f"Snapshot created: {SNAPSHOT_FILE}")

    assert SNAPSHOT_FILE.read_text(encoding="utf-8") == snapshot


# ---------------------------------------------------------------------------
# 9. Dominant violence type is one of the 3 valid labels for included municipalities
# ---------------------------------------------------------------------------

def test_dominant_violence_type_consistency(built_output: dict) -> None:
    valid = {"Violencia Intrafamiliar", "Violencia Sexual", "Ambas Violencias"}
    for cod, mun in built_output["municipios"].items():
        if cod in EXCLUDED:
            assert mun["dominant_violence_type_es"] is None
            assert mun["dominant_violence_rate"] is None
            continue
        dvt = mun["dominant_violence_type_es"]
        assert dvt in valid, f"Unknown dominant type '{dvt}' for {cod}"
        dvr = mun["dominant_violence_rate"]
        assert dvr is not None and isinstance(dvr, (int, float)), (
            f"Missing dominant rate for {cod}"
        )
