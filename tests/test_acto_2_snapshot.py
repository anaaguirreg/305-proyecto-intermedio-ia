"""
Snapshot test — acto_2_brechas.json (Phase 3.2 / 3.2.1)

Compares data values between the pre-refactor legacy snapshot and the new
schema-compliant output.  Structural changes (sub_acto_N_M keys, English
structural keys, embedded copy) are expected; data values must be identical
within floating-point tolerance.

Phase 3.2.1 note:
  6 gap-related fields are semantically null (municipalities with zero male
  victims yield an undefined gap ratio).  The schema was amended to allow
  ["number", "null"] for these fields.  All comparisons use null-aware logic:
  null == null passes; null != number fails.
  Affected cells:
    scatter gap_average: 27150, 27493, 27600, 52390
    top10 gap_vif_nna: 19050
    top10 gap_sexual_nna: 19743

Run:
    pytest tests/test_acto_2_snapshot.py -v
"""

import json
from pathlib import Path

import pytest

ROOT   = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "data/dashboard/_legacy/acto_2_brechas.legacy.json"
NEW    = ROOT / "data/dashboard/acto_2_brechas.json"

TOL = 1e-4  # absolute tolerance for float comparisons

def _cmp_nullable(lv, nv, label: str, mismatches: list) -> None:
    """Null-aware numeric comparison. null==null passes; null!=number fails."""
    if lv is None or nv is None:
        if lv is not None or nv is not None:
            mismatches.append(f"{label}: null mismatch legacy={lv} new={nv}")
    elif abs(lv - nv) >= TOL:
        mismatches.append(f"{label}: legacy={lv} new={nv} Δ={abs(lv - nv):.6f}")


@pytest.fixture(scope="module")
def legacy():
    return json.loads(LEGACY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def new():
    return json.loads(NEW.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# S1 — sub_acto_2_1: canonical stat_cards array at root; no data wrapper.
#      4 cards (sexual_adults, vif_adults, sexual_nna, vif_nna) in order.
#      cases_f_total / cases_m_total intentionally absent from JSON output.
# ---------------------------------------------------------------------------

def test_s1_kpi_regional_cases(legacy, new):
    sub = new["sub_acto_2_1"]
    assert "stat_cards" in sub, "sub_acto_2_1 missing stat_cards"
    assert "data" not in sub,   "sub_acto_2_1 must not have data wrapper"
    cards = {c["id"]: c for c in sub["stat_cards"]}
    assert len(sub["stat_cards"]) == 4, f"Expected 4 stat_cards, got {len(sub['stat_cards'])}"

    key_map = {
        "sexual_adultas": "sexual_adults",
        "vif_adultas":    "vif_adults",
        "sexual_nna":     "sexual_nna",
        "vif_nna":        "vif_nna",
    }
    mismatches = []
    for old_key, new_key in key_map.items():
        lo = legacy["kpi_regional"][old_key]
        card = cards[new_key]
        assert "cases_f_total" not in card, f"{new_key}: cases_f_total must not appear in JSON"
        assert "cases_m_total" not in card, f"{new_key}: cases_m_total must not appear in JSON"
        legacy_ratio = lo["ratio_agregado"]
        new_ratio    = card["value"]
        if (legacy_ratio is None) != (new_ratio is None):
            mismatches.append(f"{old_key}: ratio nullness differs legacy={legacy_ratio} new={new_ratio}")
        elif legacy_ratio is not None and abs(legacy_ratio - new_ratio) >= TOL:
            mismatches.append(f"{old_key}: ratio legacy={legacy_ratio} new={new_ratio}")

    assert not mismatches, "KPI regional ratio mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S2 — butterfly_vif: 8 items; year + nna/adults rate_f/rate_m identical
# ---------------------------------------------------------------------------

def test_s2_butterfly_vif(legacy, new):
    legacy_items = legacy["butterfly_vif"]
    new_items    = new["sub_acto_2_2"]["data"]["vif"]
    assert len(legacy_items) == len(new_items) == 8, (
        f"butterfly_vif length: legacy={len(legacy_items)} new={len(new_items)}"
    )
    mismatches = []
    for li, ni in zip(legacy_items, new_items):
        if li["anio"] != ni["year"]:
            mismatches.append(f"anio mismatch: legacy={li['anio']} new={ni['year']}")
        for stage, new_stage in [("nna", "nna"), ("adultas", "adults")]:
            for lk, nk in [("tasa_f", "rate_f"), ("tasa_m", "rate_m"),
                           ("casos_f", "cases_f"), ("casos_m", "cases_m")]:
                lv = li[stage][lk]
                nv = ni[new_stage][nk]
                if isinstance(lv, float) and isinstance(nv, float):
                    if abs(lv - nv) >= TOL:
                        mismatches.append(f"year={li['anio']} [{stage}] {lk}: legacy={lv} new={nv}")
                elif lv != nv:
                    mismatches.append(f"year={li['anio']} [{stage}] {lk}: legacy={lv} new={nv}")
    assert not mismatches, "Butterfly VIF mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S3 — butterfly_sexual: same structure check as VIF
# ---------------------------------------------------------------------------

def test_s3_butterfly_sexual(legacy, new):
    legacy_items = legacy["butterfly_sexual"]
    new_items    = new["sub_acto_2_2"]["data"]["sexual"]
    assert len(legacy_items) == len(new_items) == 8, (
        f"butterfly_sexual length: legacy={len(legacy_items)} new={len(new_items)}"
    )
    mismatches = []
    for li, ni in zip(legacy_items, new_items):
        if li["anio"] != ni["year"]:
            mismatches.append(f"anio mismatch: legacy={li['anio']} new={ni['year']}")
        for stage, new_stage in [("nna", "nna"), ("adultas", "adults")]:
            for lk, nk in [("tasa_f", "rate_f"), ("tasa_m", "rate_m"),
                           ("casos_f", "cases_f"), ("casos_m", "cases_m")]:
                lv = li[stage][lk]
                nv = ni[new_stage][nk]
                if isinstance(lv, float) and isinstance(nv, float):
                    if abs(lv - nv) >= TOL:
                        mismatches.append(f"year={li['anio']} [{stage}] {lk}: legacy={lv} new={nv}")
                elif lv != nv:
                    mismatches.append(f"year={li['anio']} [{stage}] {lk}: legacy={lv} new={nv}")
    assert not mismatches, "Butterfly Sexual mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S4 — top10_brechas: 10 items; cod_municipio order identical
# ---------------------------------------------------------------------------

def test_s4_top10_count_and_order(legacy, new):
    legacy_items = legacy["top10_brechas"]["items"]
    new_items    = new["sub_acto_2_3"]["data"]["items"]
    assert len(legacy_items) == len(new_items) == 10, (
        f"top10 length: legacy={len(legacy_items)} new={len(new_items)}"
    )
    for i, (li, ni) in enumerate(zip(legacy_items, new_items)):
        assert li["cod_municipio"] == ni["cod_municipio"], (
            f"rank {i+1}: cod_municipio legacy={li['cod_municipio']} new={ni['cod_municipio']}"
        )
        assert li["rank"] == ni["rank"], (
            f"rank field mismatch at position {i+1}: legacy={li['rank']} new={ni['rank']}"
        )


# ---------------------------------------------------------------------------
# S5 — top10_brechas: per item, gap values identical (with null-fill delta noted)
# ---------------------------------------------------------------------------

def test_s5_top10_gap_values(legacy, new):
    legacy_items = legacy["top10_brechas"]["items"]
    new_items    = new["sub_acto_2_3"]["data"]["items"]
    gap_map = {
        "brecha_vif_nna":      "gap_vif_nna",
        "brecha_vif_adultas":  "gap_vif_adults",
        "brecha_sexual_nna":   "gap_sexual_nna",
        "brecha_sexual_adultas": "gap_sexual_adults",
        "brecha_promedio":     "gap_average",
    }
    mismatches = []
    for li, ni in zip(legacy_items, new_items):
        cod = li["cod_municipio"]
        for lk, nk in gap_map.items():
            _cmp_nullable(li[lk], ni[nk], f"{cod} {nk}", mismatches)
    assert not mismatches, "Top-10 gap value mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S6 — mapa_brechas: 4 departments; highlighted_department == CAUCA
# ---------------------------------------------------------------------------

def test_s6_mapa_departments(legacy, new):
    legacy_depts = {d["departamento"]: d for d in legacy["mapa_brechas"]["departments"]}
    new_depts    = {d["department"]:   d for d in new["sub_acto_2_4"]["data"]["departments"]}
    assert set(legacy_depts) == set(new_depts), (
        f"Department sets differ: {set(legacy_depts) ^ set(new_depts)}"
    )
    assert new["sub_acto_2_4"]["data"]["highlighted_department"] == "CAUCA"
    mismatches = []
    for dept in legacy_depts:
        ld = legacy_depts[dept]
        nd = new_depts[dept]
        for lk, nk in [
            ("brecha_promedio_dept", "gap_average"),
            ("n_municipios",         "n_municipalities"),
            ("n_en_top10",           "n_in_top10"),
        ]:
            lv = ld[lk]
            nv = nd[nk]
            if isinstance(lv, float) and isinstance(nv, float):
                if abs(lv - nv) >= TOL:
                    mismatches.append(f"{dept} {nk}: legacy={lv} new={nv}")
            elif lv != nv:
                mismatches.append(f"{dept} {nk}: legacy={lv} new={nv}")
    assert not mismatches, "Mapa department mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S7 — mapa_brechas: geojson has 4 FeatureCollection features
# ---------------------------------------------------------------------------

def test_s7_mapa_geojson(legacy, new):
    legacy_feats = legacy["mapa_brechas"]["geojson"]["features"]
    new_feats    = new["sub_acto_2_4"]["data"]["geojson"]["features"]
    assert len(legacy_feats) == len(new_feats), (
        f"GeoJSON feature count: legacy={len(legacy_feats)} new={len(new_feats)}"
    )
    # properties key renamed: departamento → department
    new_props = {f["properties"]["department"] for f in new_feats}
    legacy_props = {f["properties"]["departamento"] for f in legacy_feats}
    assert legacy_props == new_props, (
        f"GeoJSON department property sets differ: {legacy_props ^ new_props}"
    )


# ---------------------------------------------------------------------------
# S8 — scatter_icv_brecha: 177 points post-D7; cod_municipio set is legacy
#      minus the two structurally excluded municipalities.
#      Sub_acto_2_5 excludes cod_municipio 27150 and 27493 per Phase 3.B
#      Step 3 Decision D7 (structural exclusion: no calculable gender gap).
# ---------------------------------------------------------------------------

EXCLUDED_FROM_SCATTER_2_5 = {"27150", "27493"}


def test_s8_scatter_count_and_codes(legacy, new):
    legacy_pts = legacy["scatter_icv_brecha"]["points"]
    new_pts    = new["sub_acto_2_5"]["data"]["points"]

    assert len(legacy_pts) == 179  # unchanged legacy baseline
    assert len(new_pts) == 177, f"Expected 177 points post-D7, got {len(new_pts)}"

    legacy_codes = {p["cod_municipio"] for p in legacy_pts}
    new_codes    = {p["cod_municipio"] for p in new_pts}
    assert new_codes == legacy_codes - EXCLUDED_FROM_SCATTER_2_5, (
        "New scatter code set must equal legacy set minus the two "
        "structurally excluded municipalities (D7)."
    )
    assert EXCLUDED_FROM_SCATTER_2_5.isdisjoint(new_codes), (
        f"Excluded codes must be absent from new scatter: "
        f"{EXCLUDED_FROM_SCATTER_2_5 & new_codes}"
    )


# ---------------------------------------------------------------------------
# S9 — scatter_icv_brecha: per point icv_average and gap_average identical
#      (null-fill delta documented for 4 municipalities).
#      Iterates over the new 177-code set (not legacy 179) to avoid KeyError
#      on the two D7-excluded codes. Legacy is a superset so lookup succeeds.
# ---------------------------------------------------------------------------

def test_s9_scatter_values(legacy, new):
    legacy_idx = {p["cod_municipio"]: p for p in legacy["scatter_icv_brecha"]["points"]}
    new_idx    = {p["cod_municipio"]: p for p in new["sub_acto_2_5"]["data"]["points"]}

    # Explicit absence check for D7-excluded codes
    for code in EXCLUDED_FROM_SCATTER_2_5:
        assert code not in new_idx, (
            f"Code {code} must be absent from new scatter per D7"
        )

    mismatches = []
    for cod in sorted(new_idx):
        lp  = legacy_idx[cod]   # legacy is superset — lookup always succeeds
        np_ = new_idx[cod]
        # icv_average is never null in legacy or new
        if abs(lp["icv_promedio"] - np_["icv_average"]) >= TOL:
            mismatches.append(f"{cod}: icv legacy={lp['icv_promedio']} new={np_['icv_average']}")
        # gap_average is semantically null for municipalities with zero male victims
        _cmp_nullable(lp["brecha_promedio"], np_["gap_average"], f"{cod} gap_average", mismatches)
    assert not mismatches, "Scatter value mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S10 — scatter: correlations; spearman_rho and p_value identical
# ---------------------------------------------------------------------------

def test_s10_scatter_correlations(legacy, new):
    legacy_corr = legacy["scatter_icv_brecha"]["correlaciones"]
    new_corr    = new["sub_acto_2_5"]["data"]["correlations"]
    key_map = {
        "brecha_vif_nna":      "gap_vif_nna",
        "brecha_vif_adultas":  "gap_vif_adults",
        "brecha_sexual_nna":   "gap_sexual_nna",
        "brecha_sexual_adultas": "gap_sexual_adults",
    }
    mismatches = []
    for lk, nk in key_map.items():
        lc = legacy_corr[lk]
        nc = new_corr[nk]
        if abs(lc["spearman_rho"] - nc["spearman_rho"]) >= TOL:
            mismatches.append(f"{nk}: rho legacy={lc['spearman_rho']} new={nc['spearman_rho']}")
        lp, np__ = lc["p_value"], nc["p_value"]
        if lp != np__:
            mismatches.append(f"{nk}: p_value legacy={lp} new={np__}")
        if lc["significativa"] != nc["is_significant"]:
            mismatches.append(f"{nk}: is_significant legacy={lc['significativa']} new={nc['is_significant']}")
    assert not mismatches, "Correlation mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S11 — tendencias_temporales: 8 annual rows; year + gap/rate values identical
# ---------------------------------------------------------------------------

def test_s11_annual_data(legacy, new):
    legacy_rows = legacy["tendencias_temporales"]["datos_anuales"]
    new_rows    = new["sub_acto_2_6"]["data"]["annual_data"]
    assert len(legacy_rows) == len(new_rows) == 8, (
        f"annual_data length: legacy={len(legacy_rows)} new={len(new_rows)}"
    )
    col_map = {
        "anio":                    "year",
        "brecha_vif_nna":          "gap_vif_nna",
        "brecha_vif_adultas":      "gap_vif_adults",
        "brecha_sexual_nna":       "gap_sexual_nna",
        "brecha_sexual_adultas":   "gap_sexual_adults",
        "tasa_vif_nna_f":          "rate_vif_nna_f",
        "tasa_vif_adultas_f":      "rate_vif_adults_f",
        "tasa_sexual_nna_f":       "rate_sexual_nna_f",
        "tasa_sexual_adultas_f":   "rate_sexual_adults_f",
        "tasa_vif_nna_m":          "rate_vif_nna_m",
        "tasa_vif_adultos_m":      "rate_vif_adults_m",
        "tasa_sexual_nna_m":       "rate_sexual_nna_m",
        "tasa_sexual_adultos_m":   "rate_sexual_adults_m",
    }
    mismatches = []
    for lr, nr in zip(legacy_rows, new_rows):
        for lk, nk in col_map.items():
            lv = lr[lk]
            nv = nr[nk]
            if isinstance(lv, float) and isinstance(nv, float):
                if abs(lv - nv) >= TOL:
                    mismatches.append(f"year={lr['anio']} {nk}: legacy={lv} new={nv}")
            elif lv != nv:
                mismatches.append(f"year={lr['anio']} {nk}: legacy={lv} new={nv}")
    assert not mismatches, "Annual data mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S12 — tendencias: gap_trends + male_rate_trends slope/r2 identical
# ---------------------------------------------------------------------------

def test_s12_trend_slopes(legacy, new):
    legacy_bt = legacy["tendencias_temporales"]["tendencias_brecha"]
    legacy_tm = legacy["tendencias_temporales"]["tendencias_tasas_masculinas"]
    new_gt    = new["sub_acto_2_6"]["data"]["gap_trends"]
    new_mrt   = new["sub_acto_2_6"]["data"]["male_rate_trends"]

    bt_map = {
        "brecha_vif_nna":      "gap_vif_nna",
        "brecha_vif_adultas":  "gap_vif_adults",
        "brecha_sexual_nna":   "gap_sexual_nna",
        "brecha_sexual_adultas": "gap_sexual_adults",
    }
    tm_map = {
        "tasa_vif_nna_m":      "rate_vif_nna_m",
        "tasa_vif_adultos_m":  "rate_vif_adults_m",
        "tasa_sexual_nna_m":   "rate_sexual_nna_m",
        "tasa_sexual_adultos_m": "rate_sexual_adults_m",
    }

    mismatches = []
    for (legacy_dict, new_dict, mapping) in [
        (legacy_bt, new_gt,  bt_map),
        (legacy_tm, new_mrt, tm_map),
    ]:
        for lk, nk in mapping.items():
            ld = legacy_dict[lk]
            nd = new_dict[nk]
            if ld["pendiente"] is None:
                assert nd["slope"] is None, f"{nk}: slope expected None got {nd['slope']}"
                continue
            if abs(ld["pendiente"] - nd["slope"]) >= TOL:
                mismatches.append(f"{nk}: slope legacy={ld['pendiente']} new={nd['slope']}")
            if ld.get("r2") is not None and abs(ld["r2"] - nd["r2"]) >= TOL:
                mismatches.append(f"{nk}: r2 legacy={ld['r2']} new={nd['r2']}")
            if ld["significativa"] != nd["is_significant"]:
                mismatches.append(f"{nk}: is_significant legacy={ld['significativa']} new={nd['is_significant']}")

    assert not mismatches, "Trend slope mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# S13 — beat4_diagnostic: series rows, focal keys, narrative_conclusion identical
# ---------------------------------------------------------------------------

def test_s13_beat4_diagnostic(legacy, new):
    lb4 = legacy["beat4_diagnostico"]
    nb4 = new["sub_acto_2_6"]["data"]["beat4_diagnostic"]

    assert lb4["focal_gap_visual"] == "sexual_adultas"
    assert nb4["focal_gap_visual"] == "sexual_adults"
    assert lb4["focal_artefacto"] == "vif_adultas"
    assert nb4["focal_artifact"] == "vif_adults"
    assert lb4["conclusion_narrativa"] == nb4["narrative_conclusion"]

    focal_map = [("sexual_adultas", "sexual_adults"), ("vif_adultas", "vif_adults")]
    mismatches = []
    for lk, nk in focal_map:
        ls = lb4[lk]["series"]
        ns = nb4[nk]["series"]
        assert len(ls) == len(ns) == 8, (
            f"{nk}: series length legacy={len(ls)} new={len(ns)}"
        )
        for lr, nr in zip(ls, ns):
            if lr["anio"] != nr["year"]:
                mismatches.append(f"{nk}: anio/year legacy={lr['anio']} new={nr['year']}")
            for lf, nf in [("brecha", "gap"), ("tasa_f", "rate_f"), ("tasa_m", "rate_m")]:
                lv, nv = lr[lf], nr[nf]
                if isinstance(lv, float) and isinstance(nv, float):
                    if abs(lv - nv) >= TOL:
                        mismatches.append(
                            f"{nk} year={lr['anio']} {nf}: legacy={lv} new={nv}"
                        )
                elif lv != nv:
                    mismatches.append(f"{nk} year={lr['anio']} {nf}: legacy={lv} new={nv}")

        # gap_trend slopes
        lg = lb4[lk]["tendencia_brecha"]
        ng = nb4[nk]["gap_trend"]
        if abs(lg["pendiente"] - ng["slope"]) >= TOL:
            mismatches.append(f"{nk} gap_trend slope: legacy={lg['pendiente']} new={ng['slope']}")
        if lg["significativa"] != ng["is_significant"]:
            mismatches.append(f"{nk} gap_trend is_significant: legacy={lg['significativa']} new={ng['is_significant']}")

    assert not mismatches, "Beat4 diagnostic mismatches:\n" + "\n".join(mismatches)
