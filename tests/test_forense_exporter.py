"""Tests for ForenseExporter — 12 canonical asserts."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH  = PROJECT_ROOT / "config" / "forense_exporter_config.json"
OUTPUT_PATH  = PROJECT_ROOT / "data" / "dashboard" / "acto_4_forense.json"
SCHEMA_PATH  = PROJECT_ROOT / "schema" / "acto_4_forense.schema.json"


@pytest.fixture(scope="session")
def payload() -> dict:
    """Run the exporter once and cache the result for the whole test session."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.exporters.forense_exporter import ForenseExporter
    exp = ForenseExporter(CONFIG_PATH)
    return exp.run()


@pytest.fixture(scope="session")
def written_payload(payload) -> dict:
    """Also write the JSON so the schema-validation test can read it from disk."""
    from src.exporters.exporter_utils import write_json_validated
    write_json_validated(payload, SCHEMA_PATH, OUTPUT_PATH)
    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


# ── 1-3: canonical counts ─────────────────────────────────────────────────────

def test_ds3_cases(payload):
    cards = {c["id"]: c["value"] for c in payload["sub_acto_4_1"]["stat_cards"]}
    assert cards["ds3_cases"] == 18_661, f"DS3 count mismatch: {cards['ds3_cases']}"


def test_ds4_cases(payload):
    cards = {c["id"]: c["value"] for c in payload["sub_acto_4_1"]["stat_cards"]}
    assert cards["ds4_cases"] == 15_418, f"DS4 count mismatch: {cards['ds4_cases']}"


def test_total_cases(payload):
    cards = {c["id"]: c["value"] for c in payload["sub_acto_4_1"]["stat_cards"]}
    assert cards["total_cases"] == 34_079, f"Total count mismatch: {cards['total_cases']}"


# ── 4-5: intersectionality stats (female-weighted denominators) ───────────────
# Expected values locked from Phase 1 preflight 2026-07-03.
# DS3 n_base_f=16467, DS4 n_base_f=9637.

_CATEGORY_ORDER = ["SIN_PERTENENCIA_ETNICA", "AFRO_NARP", "NO_REGISTRADO", "INDIGENA", "GITANO"]

def test_ds3_n_base_f_range(payload):
    n = payload["sub_acto_4_5"]["ds3_stats"]["n_base_f"]
    assert 16_000 <= n <= 17_000, f"DS3 n_base_f={n}, expected 16000–17000"


def test_ds4_n_base_f_range(payload):
    n = payload["sub_acto_4_5"]["ds4_stats"]["n_base_f"]
    assert 9_000 <= n <= 10_500, f"DS4 n_base_f={n}, expected 9000–10500"


def test_ds3_pct_disability_f(payload):
    pct = payload["sub_acto_4_5"]["ds3_stats"]["pct_disability_f"]
    assert abs(pct - 1.24) <= 0.05, f"DS3 pct_disability_f={pct}, expected ≈1.24"


def test_ds4_pct_disability_f(payload):
    pct = payload["sub_acto_4_5"]["ds4_stats"]["pct_disability_f"]
    assert abs(pct - 0.58) <= 0.05, f"DS4 pct_disability_f={pct}, expected ≈0.58"


def test_ds3_pct_afro_narp_f(payload):
    pct = payload["sub_acto_4_5"]["ds3_stats"]["pct_afro_narp_f"]
    assert abs(pct - 16.22) <= 0.05, f"DS3 pct_afro_narp_f={pct}, expected ≈16.22"


def test_ds3_pct_indigena_f(payload):
    pct = payload["sub_acto_4_5"]["ds3_stats"]["pct_indigena_f"]
    assert abs(pct - 4.08) <= 0.05, f"DS3 pct_indigena_f={pct}, expected ≈4.08"


def test_ds3_pct_sin_pertenencia_f(payload):
    pct = payload["sub_acto_4_5"]["ds3_stats"]["pct_sin_pertenencia_f"]
    assert abs(pct - 75.2) <= 0.05, f"DS3 pct_sin_pertenencia_f={pct}, expected ≈75.20"


def test_ethnicity_marginals_ds3_sum(payload):
    rows = payload["sub_acto_4_5"]["ethnicity_marginals"]["ds3"]
    total = sum(r["pct_of_female_cases"] for r in rows)
    # round_pct uses 1 dp; 5 categories → max rounding artifact ≤ 0.15
    assert abs(total - 100.0) <= 0.15, f"DS3 marginals sum={total}, expected 100±0.15"


def test_ethnicity_marginals_ds4_sum(payload):
    rows = payload["sub_acto_4_5"]["ethnicity_marginals"]["ds4"]
    total = sum(r["pct_of_female_cases"] for r in rows)
    assert abs(total - 100.0) <= 0.15, f"DS4 marginals sum={total}, expected 100±0.15"


def test_ethnicity_marginals_ds3_ordering(payload):
    cats = [r["dimension_etnia"] for r in payload["sub_acto_4_5"]["ethnicity_marginals"]["ds3"]]
    assert cats == _CATEGORY_ORDER, f"DS3 category order: {cats}"


def test_ethnicity_marginals_ds4_ordering(payload):
    cats = [r["dimension_etnia"] for r in payload["sub_acto_4_5"]["ethnicity_marginals"]["ds4"]]
    assert cats == _CATEGORY_ORDER, f"DS4 category order: {cats}"


def test_gitano_low_n_flag_ds3(payload):
    row = next(r for r in payload["sub_acto_4_5"]["ethnicity_marginals"]["ds3"]
               if r["dimension_etnia"] == "GITANO")
    assert row["low_n_flag"] is True, f"DS3 GITANO low_n_flag={row['low_n_flag']}, expected True"


def test_gitano_low_n_flag_ds4(payload):
    row = next(r for r in payload["sub_acto_4_5"]["ethnicity_marginals"]["ds4"]
               if r["dimension_etnia"] == "GITANO")
    assert row["low_n_flag"] is True, f"DS4 GITANO low_n_flag={row['low_n_flag']}, expected True"


def test_afro_narp_not_low_n_ds3(payload):
    row = next(r for r in payload["sub_acto_4_5"]["ethnicity_marginals"]["ds3"]
               if r["dimension_etnia"] == "AFRO_NARP")
    assert row["low_n_flag"] is False, f"DS3 AFRO_NARP low_n_flag={row['low_n_flag']}, expected False"


def test_placeholders_resolved(payload):
    text = payload["sub_acto_4_5"]["anchor_text_es"]
    assert "{" not in text and "}" not in text, f"Unresolved placeholder in anchor_text_es: {text!r}"


def test_anchor_disability_placeholders_resolved(payload):
    text = payload["sub_acto_4_5"]["anchor_disability_es"]
    assert "{" not in text and "}" not in text, f"Unresolved placeholder in anchor_disability_es: {text!r}"


# ── 6: schema validation ──────────────────────────────────────────────────────

def test_schema_validation(written_payload):
    import jsonschema
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # raises if invalid
    jsonschema.validate(instance=written_payload, schema=schema)


# ── 7-8: escenario pct sums (new day×month + stacked-bar architecture) ────────

def test_escenario_sexual_regional_pct_sums_to_100(payload):
    entry = payload["sub_acto_4_2"]["escenario"]["by_department"]["regional"]
    total = sum(entry["sexual_pct"])
    assert abs(total - 100.0) <= 0.5, f"DS3 sexual_pct sum = {total}"


def test_escenario_vif_regional_pct_sums_to_100(payload):
    entry = payload["sub_acto_4_2"]["escenario"]["by_department"]["regional"]
    total = sum(entry["vif_pct"])
    assert abs(total - 100.0) <= 0.5, f"DS4 vif_pct sum = {total}"


# ── 9: sankey node integrity ──────────────────────────────────────────────────

def test_sankey_ds3_regional_no_missing_nodes(payload):
    scope  = payload["sub_acto_4_3"]["ds3"]["regional"]
    node_ids = {n["id"] for n in scope["nodes"]}
    for link in scope["links"]:
        assert link["source"] in node_ids, f"Missing source node: {link['source']}"
        assert link["target"] in node_ids, f"Missing target node: {link['target']}"


# ── 10: sankey ds4 regional covers top 80% ───────────────────────────────────

def test_sankey_ds4_regional_links_cover_top80(payload):
    scope   = payload["sub_acto_4_3"]["ds4"]["regional"]
    n_total = scope["n_total"]
    # col2→col3 links (source starts with "2__") represent the surviving flow assignments
    col23_sum = sum(
        lk["value"] for lk in scope["links"] if lk["source"].startswith("2__")
    )
    assert col23_sum >= 0.80 * n_total, (
        f"DS4 regional Sankey col2→col3 sum {col23_sum} < 80% of {n_total}"
    )


# ── 11: only Chocó DS4 has non-null caveat ───────────────────────────────────

def test_only_choco_ds4_has_caveat(payload):
    sankey = payload["sub_acto_4_3"]
    non_null = []
    for ds_key in ("ds3", "ds4"):
        for scope_key, scope in sankey[ds_key].items():
            if scope.get("caveat") is not None:
                non_null.append(f"{ds_key}.{scope_key}")

    assert non_null == ["ds4.CHOCO"], (
        f"Expected only ds4.CHOCO to have a caveat; got: {non_null}"
    )


# ── 12: factor consolidation ──────────────────────────────────────────────────

def test_factor_consolidation_alcohol(payload):
    regional = payload["sub_acto_4_4"]["ds4_factor"]["regional"]
    alc = next((r for r in regional if r["category"] == "ALCOHOL_SUSTANCIAS"), None)
    assert alc is not None, "ALCOHOL_SUSTANCIAS not found in ds4_factor.regional"
    expected = 1621 + 768  # sum of both raw alcohol categories
    assert alc["n"] == expected, (
        f"ALCOHOL_SUSTANCIAS n = {alc['n']}, expected {expected}"
    )


# ── 13: sankey column-2 node flow balance ─────────────────────────────────────

def test_sankey_col2_node_balance(payload):
    """For every col-2 node (dimension_agresor) in every scope of DS3 and DS4,
    sum(incoming link values) == sum(outgoing link values) ± 1.

    Incoming  = links whose target  starts with '2__'
    Outgoing  = links whose source  starts with '2__'
    """
    imbalances = []

    for ds_key in ("ds3", "ds4"):
        for scope_key, scope in payload["sub_acto_4_3"][ds_key].items():
            links = scope["links"]

            # bucket values by col-2 node id
            incoming: dict[str, int] = {}
            outgoing: dict[str, int] = {}

            for lk in links:
                if lk["target"].startswith("2__"):
                    incoming[lk["target"]] = incoming.get(lk["target"], 0) + lk["value"]
                if lk["source"].startswith("2__"):
                    outgoing[lk["source"]] = outgoing.get(lk["source"], 0) + lk["value"]

            all_col2 = set(incoming) | set(outgoing)
            for node_id in all_col2:
                a = incoming.get(node_id, 0)
                b = outgoing.get(node_id, 0)
                if abs(a - b) > 1:
                    imbalances.append({
                        "dataset": ds_key,
                        "scope":   scope_key,
                        "node":    node_id,
                        "incoming": a,
                        "outgoing": b,
                        "delta":   a - b,
                    })

    assert not imbalances, (
        "Sankey col-2 node imbalances detected:\n"
        + "\n".join(
            f"  [{i['dataset']}.{i['scope']}] {i['node']}: "
            f"in={i['incoming']} out={i['outgoing']} delta={i['delta']}"
            for i in imbalances
        )
    )
