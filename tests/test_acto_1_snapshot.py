"""
Snapshot test — acto_1_panorama.json (Phase 3.1)

Compares data values between the pre-refactor legacy snapshot and the new
schema-compliant output.  Structural changes (sub_acto_N_M keys, English
structural keys, embedded copy fields) are expected; data values must be
identical within floating-point tolerance.

Run:
    pytest tests/test_acto_1_snapshot.py -v
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "data/dashboard/_legacy/acto_1_panorama.legacy.json"
NEW = ROOT / "data/dashboard/acto_1_panorama.json"

TOL = 1e-4  # absolute tolerance for float comparisons


@pytest.fixture(scope="module")
def legacy():
    return json.loads(LEGACY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def new():
    return json.loads(NEW.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# S1 — choropleth: 179 features in both; cod_municipio sets identical
# ---------------------------------------------------------------------------

def test_s1_choropleth_count_and_codes(legacy, new):
    legacy_features = legacy["choropleth"]["features"]
    new_features    = new["sub_acto_1_2"]["data"]["features"]

    assert len(legacy_features) == 179, f"legacy: expected 179 features, got {len(legacy_features)}"
    assert len(new_features)    == 179, f"new: expected 179 features, got {len(new_features)}"

    legacy_codes = {f["cod_municipio"] for f in legacy_features}
    new_codes    = {f["cod_municipio"] for f in new_features}
    assert legacy_codes == new_codes, f"cod_municipio sets differ: {legacy_codes ^ new_codes}"


# ---------------------------------------------------------------------------
# S2 — choropleth: per municipality, icv_average / cluster_id / excluded match
# ---------------------------------------------------------------------------

def test_s2_choropleth_values(legacy, new):
    legacy_idx = {f["cod_municipio"]: f for f in legacy["choropleth"]["features"]}
    new_idx    = {f["cod_municipio"]: f for f in new["sub_acto_1_2"]["data"]["features"]}

    mismatches = []
    for cod in sorted(legacy_idx):
        lf = legacy_idx[cod]
        nf = new_idx[cod]

        # icv_promedio (legacy) == icv_average (new)
        if abs(lf["icv_promedio"] - nf["icv_average"]) >= TOL:
            mismatches.append(
                f"{cod}: icv legacy={lf['icv_promedio']} new={nf['icv_average']}"
            )

        # cluster_id
        if lf["cluster_id"] != nf["cluster_id"]:
            mismatches.append(
                f"{cod}: cluster_id legacy={lf['cluster_id']} new={nf['cluster_id']}"
            )

        # excluded_from_model
        if lf["excluded_from_model"] != nf["excluded_from_model"]:
            mismatches.append(
                f"{cod}: excluded legacy={lf['excluded_from_model']} new={nf['excluded_from_model']}"
            )

    assert not mismatches, "Choropleth value mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S3 — top10_ranking: 10 items in both; cod_municipio in same rank order
# ---------------------------------------------------------------------------

def test_s3_top10_count_and_order(legacy, new):
    legacy_items = legacy["top10_ranking"]["items"]
    new_items    = new["sub_acto_1_3"]["data"]["items"]

    assert len(legacy_items) == 10, f"legacy: expected 10 items, got {len(legacy_items)}"
    assert len(new_items)    == 10, f"new: expected 10 items, got {len(new_items)}"

    for i, (li, ni) in enumerate(zip(legacy_items, new_items), start=1):
        assert li["cod_municipio"] == ni["cod_municipio"], (
            f"rank {i}: cod_municipio differs — legacy={li['cod_municipio']} new={ni['cod_municipio']}"
        )
        assert li["rank"] == ni["rank"], (
            f"rank field differs at position {i}: legacy={li['rank']} new={ni['rank']}"
        )


# ---------------------------------------------------------------------------
# S4 — top10_ranking: per rank, icv_promedio == icv_average
# ---------------------------------------------------------------------------

def test_s4_top10_icv_values(legacy, new):
    legacy_items = legacy["top10_ranking"]["items"]
    new_items    = new["sub_acto_1_3"]["data"]["items"]

    mismatches = []
    for li, ni in zip(legacy_items, new_items):
        delta = abs(li["icv_promedio"] - ni["icv_average"])
        if delta >= TOL:
            mismatches.append(
                f"rank {li['rank']} ({li['cod_municipio']}): "
                f"icv legacy={li['icv_promedio']} new={ni['icv_average']} Δ={delta:.6f}"
            )

    assert not mismatches, "Top-10 ICV mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S5 — top10_ranking: highlighted set = {52001, 19001} in both
# ---------------------------------------------------------------------------

def test_s5_highlighted_municipalities(legacy, new):
    # Legacy uses municipality names; extract codes from items where highlight=True
    legacy_highlighted_codes = {
        item["cod_municipio"]
        for item in legacy["top10_ranking"]["items"]
        if item["highlight"]
    }
    # New uses cod_municipio codes in highlighted_municipalities array
    new_highlighted_array = set(new["sub_acto_1_3"]["data"]["highlighted_municipalities"])
    new_highlighted_codes = {
        item["cod_municipio"]
        for item in new["sub_acto_1_3"]["data"]["items"]
        if item["highlight"]
    }

    expected = {"52001", "19001"}

    assert legacy_highlighted_codes == expected, (
        f"Legacy highlight codes: {legacy_highlighted_codes} — expected {expected}"
    )
    assert new_highlighted_array == expected, (
        f"New highlighted_municipalities array: {new_highlighted_array} — expected {expected}"
    )
    assert new_highlighted_codes == expected, (
        f"New items highlight flags: {new_highlighted_codes} — expected {expected}"
    )


# ---------------------------------------------------------------------------
# S6 — timeline: x_axis years identical [2018..2025]
# ---------------------------------------------------------------------------

def test_s6_timeline_x_axis(legacy, new):
    legacy_years = legacy["timeline"]["x_axis"]
    new_years    = new["sub_acto_1_4"]["data"]["x_axis"]

    assert legacy_years == new_years, (
        f"x_axis differs — legacy={legacy_years} new={new_years}"
    )
    assert legacy_years == list(range(2018, 2026)), (
        f"Expected 2018-2025, got {legacy_years}"
    )


# ---------------------------------------------------------------------------
# S7 — timeline: series[0].data element-wise equal
# ---------------------------------------------------------------------------

def test_s7_timeline_series_values(legacy, new):
    legacy_data = legacy["timeline"]["series"][0]["data"]
    new_data    = new["sub_acto_1_4"]["data"]["series"][0]["data"]

    assert len(legacy_data) == len(new_data) == 8, (
        f"Series data length mismatch: legacy={len(legacy_data)} new={len(new_data)}"
    )

    mismatches = []
    for i, (lv, nv) in enumerate(zip(legacy_data, new_data)):
        if lv is None and nv is None:
            continue
        if lv is None or nv is None:
            mismatches.append(f"year index {i}: legacy={lv} new={nv}")
            continue
        if abs(lv - nv) >= TOL:
            mismatches.append(
                f"year index {i}: legacy={lv} new={nv} Δ={abs(lv - nv):.6f}"
            )

    assert not mismatches, "Timeline series mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S8 — sub_acto_1_1: canonical stat_cards array at root; caveat_es present.
#      Deliberate value changes from legacy:
#        n_municipios value: 179 → 177 (n_clustered, not n_total)
#        n_alta_severidad sub_value: pct:60 → sub_value.value:60.5 (1 decimal)
#      icv_promedio_regional (14.34) must be byte-identical to legacy.
# ---------------------------------------------------------------------------

def test_s8_stat_cards_values(legacy, new):
    sub = new["sub_acto_1_1"]
    assert "stat_cards" in sub,  "sub_acto_1_1 missing stat_cards at root"
    assert "data" not in sub,    "sub_acto_1_1 must not have data wrapper"
    assert "caveat_es" in sub,   "sub_acto_1_1 missing caveat_es"
    assert "Carmen del Darién" in sub["caveat_es"], "caveat_es must name Carmen del Darién"
    assert "Nuevo Belén de Bajirá" in sub["caveat_es"], "caveat_es must name Nuevo Belén de Bajirá"

    cards = {c["id"]: c for c in sub["stat_cards"]}
    assert len(sub["stat_cards"]) == 3, f"Expected 3 stat_cards, got {len(sub['stat_cards'])}"
    expected_ids = {"n_municipios", "n_alta_severidad", "icv_promedio_regional"}
    assert set(cards) == expected_ids, f"Card ids: {set(cards)}"

    # Card 1 — deliberate correction: 179 → 177 (n_clustered)
    assert cards["n_municipios"]["value"] == 177, (
        f"n_municipios expected 177 (n_clustered), got {cards['n_municipios']['value']}"
    )
    assert "pct" not in cards["n_municipios"], "n_municipios must not have orphan pct field"

    # Card 2 — value unchanged (107); pct promoted to sub_value with 1-decimal precision
    assert cards["n_alta_severidad"]["value"] == 107, (
        f"n_alta_severidad expected 107, got {cards['n_alta_severidad']['value']}"
    )
    sv = cards["n_alta_severidad"]["sub_value"]
    assert sv is not None, "n_alta_severidad sub_value must not be null"
    assert abs(sv["value"] - 60.5) < TOL, (
        f"n_alta_severidad sub_value.value expected 60.5, got {sv['value']}"
    )
    assert "pct" not in cards["n_alta_severidad"], "n_alta_severidad must not have orphan pct field"

    # Card 3 — byte-identical to legacy
    legacy_icv = legacy["stat_cards"][2]["value"]   # icv_promedio_regional is index 2
    new_icv    = cards["icv_promedio_regional"]["value"]
    assert abs(new_icv - legacy_icv) < TOL, (
        f"icv_promedio_regional legacy={legacy_icv} new={new_icv} — must be byte-identical"
    )
