"""
Snapshot test — acto_3_tipologia.json (Phase 3.3)

Compares data values between the pre-refactor legacy snapshot and the new
schema-compliant output.  Structural changes (sub_acto_N_M keys, English
structural keys, embedded copy fields) are expected; data values must be
identical within floating-point tolerance.

Run:
    pytest tests/test_acto_3_snapshot.py -v
"""

import json
from pathlib import Path

import pytest

ROOT   = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "data/dashboard/_legacy/acto_3_tipologia.legacy.json"
NEW    = ROOT / "data/dashboard/acto_3_tipologia.json"

TOL = 1e-4  # absolute tolerance for float comparisons


@pytest.fixture(scope="module")
def legacy():
    return json.loads(LEGACY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def new():
    return json.loads(NEW.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# S1 — metadata: n_total=179, n_clustered=177, year_range=[2018,2025]
# ---------------------------------------------------------------------------

def test_s1_metadata_constants(new):
    m = new["metadata"]
    assert m["n_total"]    == 179,          f"n_total={m['n_total']}, expected 179"
    assert m["n_clustered"] == 177,         f"n_clustered={m['n_clustered']}, expected 177"
    assert m["year_range"]  == [2018, 2025], f"year_range={m['year_range']}"


# ---------------------------------------------------------------------------
# S2 — sub_acto_3_1: canonical stat_cards array at root; no data wrapper
#      Cards: pct_under_14, pct_all_minors, total_cases (in order)
# ---------------------------------------------------------------------------

def test_s2_kpi_keys(new):
    sub = new["sub_acto_3_1"]
    assert "stat_cards" in sub,  "sub_acto_3_1 missing stat_cards"
    assert "data" not in sub,    "sub_acto_3_1 must not have data wrapper"
    cards = sub["stat_cards"]
    assert len(cards) == 3, f"Expected 3 stat_cards, got {len(cards)}"
    ids = [c["id"] for c in cards]
    assert ids == ["pct_under_14", "pct_all_minors", "total_cases"], f"Card ids order: {ids}"
    required_card_keys = {"id", "label_es", "value", "display_format", "badge", "sub_value"}
    for c in cards:
        missing = required_card_keys - set(c.keys())
        assert not missing, f"Card {c['id']} missing keys: {missing}"


# ---------------------------------------------------------------------------
# S3 — KPI values match legacy kpi_tipologia
# ---------------------------------------------------------------------------

def test_s3_kpi_values(legacy, new):
    old = legacy["kpi_tipologia"]
    cards = {c["id"]: c for c in new["sub_acto_3_1"]["stat_cards"]}

    assert abs(cards["pct_under_14"]["value"]   - old["pct_menor_14"])  < TOL, (
        f"pct_under_14 legacy={old['pct_menor_14']} new={cards['pct_under_14']['value']}"
    )
    assert abs(cards["pct_all_minors"]["value"] - old["pct_all_minors"]) < TOL, (
        f"pct_all_minors legacy={old['pct_all_minors']} new={cards['pct_all_minors']['value']}"
    )
    assert cards["total_cases"]["value"] == old["total_casos"], (
        f"total_cases legacy={old['total_casos']} new={cards['total_cases']['value']}"
    )


# ---------------------------------------------------------------------------
# S4 — scatter: n_points=177; same cod_municipio set as legacy
# ---------------------------------------------------------------------------

def test_s4_scatter_count_and_codes(legacy, new):
    old_pts = legacy["capa3a_scatter"]["points"]
    new_pts = new["sub_acto_3_2"]["data"]["points"]

    assert new["sub_acto_3_2"]["data"]["n_points"] == 177
    assert len(new_pts) == 177, f"Expected 177 points, got {len(new_pts)}"
    assert len(old_pts) == 177, f"Legacy expected 177 points, got {len(old_pts)}"

    old_codes = {p["cod_municipio"] for p in old_pts}
    new_codes = {p["cod_municipio"] for p in new_pts}
    assert old_codes == new_codes, f"cod_municipio sets differ: {old_codes ^ new_codes}"


# ---------------------------------------------------------------------------
# S5 — scatter: per-municipality vif_f_total_rate and sexual_f_total_rate match
# ---------------------------------------------------------------------------

def test_s5_scatter_rates(legacy, new):
    old_idx = {p["cod_municipio"]: p for p in legacy["capa3a_scatter"]["points"]}
    new_idx = {p["cod_municipio"]: p for p in new["sub_acto_3_2"]["data"]["points"]}

    mismatches = []
    for cod in sorted(old_idx):
        op, np_ = old_idx[cod], new_idx[cod]
        for rate_col in ("vif_f_total_rate", "sexual_f_total_rate"):
            if abs(op[rate_col] - np_[rate_col]) >= TOL:
                mismatches.append(
                    f"{cod} {rate_col}: legacy={op[rate_col]} new={np_[rate_col]}"
                )

    assert not mismatches, "Scatter rate mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S6 — scatter: quadrant n counts match legacy
# ---------------------------------------------------------------------------

def test_s6_quadrant_counts(legacy, new):
    old_q = legacy["capa3a_scatter"]["quadrants"]
    new_q = new["sub_acto_3_2"]["data"]["quadrants"]

    for qid in ("coexistencia_alta", "predomina_vif", "predomina_sexual", "bajo_perfil"):
        old_n = old_q[qid]["n"]
        new_n = new_q[qid]["n"]
        assert old_n == new_n, f"quadrant {qid}: legacy n={old_n} new n={new_n}"


# ---------------------------------------------------------------------------
# S7 — archetypes: 3 items; same cod_municipio set as legacy
# ---------------------------------------------------------------------------

def test_s7_archetypes(legacy, new):
    old_arcs = legacy["capa3a_scatter"]["archetypes"]
    new_arcs = new["sub_acto_3_2"]["data"]["archetypes"]

    assert len(new_arcs) == 3, f"Expected 3 archetypes, got {len(new_arcs)}"
    old_codes = {a["cod_municipio"] for a in old_arcs}
    new_codes = {a["cod_municipio"] for a in new_arcs}
    assert old_codes == new_codes, f"Archetype codes differ: {old_codes ^ new_codes}"


# ---------------------------------------------------------------------------
# S8 — dumbbell denominators match legacy (values; keys renamed)
# ---------------------------------------------------------------------------

def test_s8_dumbbell_denominators(legacy, new):
    old_den = legacy["capa3a_dumbbell"]["denominators"]
    new_den = new["sub_acto_3_3"]["data"]["denominators"]

    assert new_den["pop_f_0_17_sum"]    == old_den["pob_f_0_17_sum"], (
        f"pop_f_0_17_sum: legacy={old_den['pob_f_0_17_sum']} new={new_den['pop_f_0_17_sum']}"
    )
    assert new_den["pop_f_18_plus_sum"] == old_den["pob_f_18_mas_sum"], (
        f"pop_f_18_plus_sum: legacy={old_den['pob_f_18_mas_sum']} new={new_den['pop_f_18_plus_sum']}"
    )


# ---------------------------------------------------------------------------
# S9 — dumbbell: per-line endpoint cases and rate match legacy
# ---------------------------------------------------------------------------

def test_s9_dumbbell_endpoint_values(legacy, new):
    old_lines = {ln["id"]: ln for ln in legacy["capa3a_dumbbell"]["lines"]}
    new_lines = {ln["id"]: ln for ln in new["sub_acto_3_3"]["data"]["lines"]}

    mismatches = []
    for line_id in ("vif", "sexual"):
        old_eps = {ep["grupo"]: ep for ep in old_lines[line_id]["endpoints"]}
        new_eps = {ep["group"]: ep for ep in new_lines[line_id]["endpoints"]}

        for grp in ("nna", "adultas"):
            oe, ne = old_eps[grp], new_eps[grp]
            if oe["cases"] != ne["cases"]:
                mismatches.append(f"{line_id}/{grp} cases: legacy={oe['cases']} new={ne['cases']}")
            if abs(oe["rate"] - ne["rate"]) >= TOL:
                mismatches.append(f"{line_id}/{grp} rate: legacy={oe['rate']} new={ne['rate']}")

    assert not mismatches, "Dumbbell endpoint mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S10 — sub_acto_3_4.data has no pct_under_14 / pct_menor_14 (dedup enforced)
# ---------------------------------------------------------------------------

def test_s10_no_kpi_duplication(new):
    data = new["sub_acto_3_4"]["data"]
    forbidden = {"pct_under_14", "pct_menor_14", "pct_all_minors"}
    found = forbidden & set(data.keys())
    assert not found, f"KPI fields must not appear in sub_acto_3_4.data: {found}"


# ---------------------------------------------------------------------------
# S11 — crime typology total_cases matches legacy total_casos
# ---------------------------------------------------------------------------

def test_s11_crime_typology_total(legacy, new):
    old_total = legacy["tipologia_delito"]["total_casos"]
    new_total = new["sub_acto_3_4"]["data"]["total_cases"]
    assert new_total == old_total, f"total_cases: legacy={old_total} new={new_total}"


# ---------------------------------------------------------------------------
# S12 — global crime rows: per crime_dimension, count and pct match legacy
# ---------------------------------------------------------------------------

def test_s12_global_crime_rows(legacy, new):
    old_rows = {r["dimension_delito"]: r for r in legacy["tipologia_delito"]["global"]}
    new_rows = {r["crime_dimension"]:  r for r in new["sub_acto_3_4"]["data"]["global"]}

    assert set(old_rows) == set(new_rows), (
        f"crime_dimension sets differ: {set(old_rows) ^ set(new_rows)}"
    )

    mismatches = []
    for dim in sorted(old_rows):
        or_, nr = old_rows[dim], new_rows[dim]
        if or_["cantidad"] != nr["count"]:
            mismatches.append(f"{dim} count: legacy={or_['cantidad']} new={nr['count']}")
        if abs(or_["pct"] - nr["pct"]) >= TOL:
            mismatches.append(f"{dim} pct: legacy={or_['pct']} new={nr['pct']}")

    assert not mismatches, "Global crime row mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S13 — by_department: all 4 depts; per-dept per-crime_dimension count matches
# ---------------------------------------------------------------------------

def test_s13_by_department_counts(legacy, new):
    old_by_dept = legacy["tipologia_delito"]["por_departamento"]
    new_by_dept = new["sub_acto_3_4"]["data"]["by_department"]

    assert set(old_by_dept.keys()) == set(new_by_dept.keys()), (
        f"Department keys differ: {set(old_by_dept.keys()) ^ set(new_by_dept.keys())}"
    )

    mismatches = []
    for dept in sorted(old_by_dept):
        old_rows = {r["dimension_delito"]: r for r in old_by_dept[dept]}
        new_rows = {r["crime_dimension"]:  r for r in new_by_dept[dept]}
        if set(old_rows) != set(new_rows):
            mismatches.append(f"{dept}: crime_dimension sets differ")
            continue
        for dim in sorted(old_rows):
            old_n = old_rows[dim]["cantidad"]
            new_n = new_rows[dim]["count"]
            if old_n != new_n:
                mismatches.append(f"{dept}/{dim} count: legacy={old_n} new={new_n}")

    assert not mismatches, "By-department count mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S14 — timeline: x_axis=[2018..2025]; 4 series; per-dept per-year data matches
# ---------------------------------------------------------------------------

def test_s14_timeline_values(legacy, new):
    old_tl = legacy["timeline_sexual_nna"]
    new_tl = new["sub_acto_3_5"]["data"]

    assert new_tl["x_axis"] == list(range(2018, 2026)), (
        f"x_axis={new_tl['x_axis']}, expected 2018-2025"
    )
    assert new_tl["x_axis"] == old_tl["x_axis"], (
        f"x_axis differs: legacy={old_tl['x_axis']} new={new_tl['x_axis']}"
    )
    assert len(new_tl["series"]) == 4, f"Expected 4 series, got {len(new_tl['series'])}"

    old_series = {s["departamento"]: s["data"] for s in old_tl["series"]}
    new_series = {s["department"]:   s["data"] for s in new_tl["series"]}

    assert set(old_series) == set(new_series), (
        f"Department sets differ: {set(old_series) ^ set(new_series)}"
    )

    mismatches = []
    for dept in sorted(old_series):
        for i, (ov, nv) in enumerate(zip(old_series[dept], new_series[dept])):
            if ov is None and nv is None:
                continue
            if ov is None or nv is None:
                mismatches.append(f"{dept}[{i}]: legacy={ov} new={nv}")
                continue
            if abs(ov - nv) >= TOL:
                mismatches.append(
                    f"{dept} year_index={i}: legacy={ov} new={nv} Δ={abs(ov-nv):.6f}"
                )

    assert not mismatches, "Timeline value mismatches:\n" + "\n".join(mismatches)
