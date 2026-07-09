"""ForenseExporter — produces acto_4_forense.json for the Cicatrices Invisibles dashboard.

Carril B: forensic analysis (DS3 seforense + DS4 forense).
All business rules are read from config/forense_exporter_config.json.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.exporters.exporter_utils import (
    normalize_dept_key,
    round_pct,
    to_int_safe,
    write_json_validated,
)


class ForenseExporter:
    """Builds and writes acto_4_forense.json from the 12 forensic parquet tables."""

    VERSION = "1.0.0"

    def __init__(self, config_path: Path) -> None:
        self._root = Path(config_path).resolve().parent.parent
        with open(config_path, encoding="utf-8") as fh:
            self._cfg = json.load(fh)

        self._paths = {k: self._root / v for k, v in self._cfg["paths"].items()}
        self._load_data()

    # ── data loading ──────────────────────────────────────────────────────────

    def _load_data(self) -> None:
        p = self._paths
        self._ds3_esc   = pd.read_parquet(p["ds3_escenario"])
        self._ds3_temp  = pd.read_parquet(p["ds3_temporalidad"])
        self._ds3_agr   = pd.read_parquet(p["ds3_agresor"])
        self._ds3_circ  = pd.read_parquet(p["ds3_circunstancia"])
        self._ds3_inter = pd.read_parquet(p["ds3_interseccional"])
        self._ds4_esc   = pd.read_parquet(p["ds4_escenario"])
        self._ds4_temp  = pd.read_parquet(p["ds4_temporalidad"])
        self._ds4_agr   = pd.read_parquet(p["ds4_agresor"])
        self._ds4_fac   = pd.read_parquet(p["ds4_factor"])
        self._ds4_inter = pd.read_parquet(p["ds4_interseccional"])
        # cleaned — used only for ciclo_vital aggregation and pct_nna
        self._ds3_clean = pd.read_parquet(p["seforense_limpio"],
                                          columns=["ciclo_vital", "departamento"])
        self._ds4_clean = pd.read_parquet(p["forense_limpio"],
                                          columns=["ciclo_vital", "departamento"])

    # ── orchestrator ──────────────────────────────────────────────────────────

    def run(self) -> dict:
        """Build and return the full acto_4_forense payload dict."""
        copy = self._cfg["copy_es"]
        return {
            "metadata":     self._build_metadata(),
            "sub_acto_4_1": self._build_sub_acto_4_1(),
            "sub_acto_4_2": self._build_sub_acto_4_2(),
            "sub_acto_4_3": self._build_sub_acto_4_3(),
            "sub_acto_4_4": self._build_sub_acto_4_4(),
            "sub_acto_4_5": self._build_sub_acto_4_5(),
        }

    def export(self, output_path: Path) -> None:
        """Write validated acto_4_forense.json to *output_path*."""
        payload = self.run()
        write_json_validated(payload, self._paths["schema"], output_path)
        print(f"✓  acto_4_forense.json  →  {output_path}  "
              f"({output_path.stat().st_size / 1024:.1f} KB)")

    # ── metadata ──────────────────────────────────────────────────────────────

    def _build_metadata(self) -> dict:
        n_ds3 = len(self._ds3_clean)
        n_ds4 = len(self._ds4_clean)
        return {
            "version":           self.VERSION,
            "generated_at":      datetime.now(timezone.utc).isoformat(),
            "year_range":        [2018, 2024],
            "n_total":           n_ds3 + n_ds4,
            "n_ds3":             n_ds3,
            "n_ds4":             n_ds4,
            "act_disclaimer_es": self._cfg["copy_es"]["act_disclaimer"],
        }

    # ── sub-acto 4.1 — universe ───────────────────────────────────────────────

    def _build_sub_acto_4_1(self) -> dict:
        n_ds3 = len(self._ds3_clean)
        n_ds4 = len(self._ds4_clean)
        n_total = n_ds3 + n_ds4

        nna_ciclos = set(self._cfg["nna_ciclos"])
        combined = pd.concat([self._ds3_clean[["ciclo_vital"]],
                               self._ds4_clean[["ciclo_vital"]]])
        pct_nna = round_pct(
            combined["ciclo_vital"].isin(nna_ciclos).sum() / n_total * 100
        )

        top_dept_ds3 = self._ds3_clean["departamento"].value_counts().index[0]
        pct_top3     = round_pct(
            (self._ds3_clean["departamento"] == top_dept_ds3).sum() / n_ds3 * 100
        )
        top_dept_ds4 = self._ds4_clean["departamento"].value_counts().index[0]
        pct_top4     = round_pct(
            (self._ds4_clean["departamento"] == top_dept_ds4).sum() / n_ds4 * 100
        )

        top_label_ds3 = f"{top_dept_ds3.title()} ({pct_top3}%)"
        top_label_ds4 = f"{top_dept_ds4.title()} ({pct_top4}%)"

        value_map = {
            "total_cases":   n_total,
            "ds3_cases":     n_ds3,
            "ds4_cases":     n_ds4,
            "pct_nna":       pct_nna,
            "top_dept_ds3":  top_label_ds3,
            "top_dept_ds4":  top_label_ds4,
        }

        cards = []
        for card_cfg in self._cfg["acto_4_kpis"]["sub_acto_4_1"]["stat_cards"]:
            cid = card_cfg["id"]
            cards.append({
                "id":             cid,
                "label_es":       card_cfg["label_es"],
                "value":          value_map[cid],
                "display_format": card_cfg["display_format"],
                "badge":          card_cfg["badge"],
                "sub_value":      card_cfg["sub_value"],
            })

        c = self._cfg["copy_es"]["sub_acto_4_1"]
        return {
            "title_es":       c["title"],
            "anchor_text_es": c["anchor"],
            "stat_cards":     cards,
        }

    # ── sub-acto 4.2 — scenario + temporality ─────────────────────────────────

    def _build_sub_acto_4_2(self) -> dict:
        c           = self._cfg["copy_es"]["sub_acto_4_2"]
        axis_days   = self._cfg["axis_days"]
        axis_months = self._cfg["axis_months"]
        depts_avail = ["regional", "CAUCA", "CHOCO", "NARIÑO", "VALLE DEL CAUCA"]

        return {
            "title_es":              c["title"],
            "anchor_text_es":        c["anchor"],
            "aggregation_default":   self._cfg.get("aggregation_default", "regional"),
            "departments_available": depts_avail,
            "heatmap_vif": self._build_heatmap_block(
                self._ds4_temp, axis_days, axis_months,
                dataset_id="ds4_vif",
                caveat_choco=c["caveat_choco_es"]["heatmap_vif"],
            ),
            "heatmap_sexual": self._build_heatmap_block(
                self._ds3_temp, axis_days, axis_months,
                dataset_id="ds3_sexual",
                caveat_choco=c["caveat_choco_es"]["heatmap_sexual"],
            ),
            "escenario": self._build_escenario_block(
                caveat_choco=c["caveat_choco_es"]["escenario"],
            ),
        }

    def _build_scenario(self, df: pd.DataFrame, cat_col: str) -> dict:
        """Build scenario dict keyed by normalised dept + 'regional'."""
        result: dict = {}
        depts = df["departamento"].unique()

        for dept in depts:
            key = normalize_dept_key(dept)
            sub  = df[df["departamento"] == dept]
            result[key] = self._agg_categorical(sub, cat_col)

        # regional = sum across all depts
        result["regional"] = self._agg_categorical(df, cat_col)
        return result

    def _agg_categorical(self, df: pd.DataFrame, cat_col: str) -> list[dict]:
        """Aggregate n_casos by cat_col, compute pct, return sorted list."""
        agg = (
            df.groupby(cat_col, as_index=False)["n_casos"]
            .sum()
            .rename(columns={"n_casos": "n"})
        )
        total = agg["n"].sum()
        agg["pct"] = (agg["n"] / total * 100).round(1)
        agg = agg.sort_values("n", ascending=False).reset_index(drop=True)
        return [
            {"category": row[cat_col], "n": to_int_safe(row["n"]), "pct": float(row["pct"])}
            for _, row in agg.iterrows()
        ]

    def _build_heatmap_block(
        self,
        df: pd.DataFrame,
        axis_days: list[str],
        axis_months: list[str],
        *,
        dataset_id: str,
        caveat_choco: str,
    ) -> dict:
        """Build heatmap block (day × month) with regional + per-department breakdown."""
        dept_names = ["CAUCA", "CHOCO", "NARIÑO", "VALLE DEL CAUCA"]
        by_dept: dict = {
            "regional": self._heatmap_dept_entry(df, axis_days, axis_months, caveat=None),
        }
        for dept in dept_names:
            sub    = df[df["departamento"] == dept].copy(deep=False)
            caveat = caveat_choco if dept == "CHOCO" else None
            by_dept[dept] = self._heatmap_dept_entry(sub, axis_days, axis_months, caveat=caveat)

        return {
            "dataset_id":    dataset_id,
            "axis_days":     axis_days,
            "axis_months":   axis_months,
            "by_department": by_dept,
        }

    def _heatmap_dept_entry(
        self,
        df: pd.DataFrame,
        axis_days: list[str],
        axis_months: list[str],
        *,
        caveat: str | None,
    ) -> dict:
        """Aggregate df to a 7×12 day×month matrix (hora_rango discarded by groupby)."""
        agg = df.groupby(["dia_hecho", "mes_hecho"], as_index=False)["n_casos"].sum()
        total_cases = to_int_safe(agg["n_casos"].sum())

        pivot = (
            agg.pivot_table(
                index="dia_hecho",
                columns="mes_hecho",
                values="n_casos",
                aggfunc="sum",
                fill_value=0,
            )
            .reindex(index=axis_days, columns=axis_months, fill_value=0)
        )
        matrix = [[int(v) for v in row] for row in pivot.values.tolist()]

        if len(agg) > 0:
            idx  = agg["n_casos"].idxmax()
            row  = agg.loc[idx]
            peak = {
                "day":   str(row["dia_hecho"]),
                "month": str(row["mes_hecho"]),
                "value": to_int_safe(row["n_casos"]),
            }
        else:
            peak = {"day": None, "month": None, "value": 0}

        return {"matrix": matrix, "total_cases": total_cases, "peak": peak, "caveat_es": caveat}

    def _build_escenario_block(self, *, caveat_choco: str) -> dict:
        """Build combined DS4+DS3 escenario with regional + per-department breakdown."""
        dept_names = ["CAUCA", "CHOCO", "NARIÑO", "VALLE DEL CAUCA"]
        by_dept: dict = {
            "regional": self._escenario_dept_entry(self._ds4_esc, self._ds3_esc, caveat=None),
        }
        for dept in dept_names:
            ds4_sub = self._ds4_esc[self._ds4_esc["departamento"] == dept].copy(deep=False)
            ds3_sub = self._ds3_esc[self._ds3_esc["departamento"] == dept].copy(deep=False)
            caveat  = caveat_choco if dept == "CHOCO" else None
            by_dept[dept] = self._escenario_dept_entry(ds4_sub, ds3_sub, caveat=caveat)

        return {
            "chart_type":     "stacked_bar_horizontal",
            "dataset_labels": {"vif": "VIF (DS4)", "sexual": "Sexual (DS3)"},
            "by_department":  by_dept,
        }

    def _escenario_dept_entry(
        self,
        ds4: pd.DataFrame,
        ds3: pd.DataFrame,
        *,
        caveat: str | None,
    ) -> dict:
        """Merge DS4+DS3 escenario for one scope; sort by combined count desc."""
        col = "dimension_escenario"

        ds4_agg = (
            ds4.groupby(col, as_index=False)["n_casos"].sum()
            .rename(columns={"n_casos": "vif_n"})
        )
        ds3_agg = (
            ds3.groupby(col, as_index=False)["n_casos"].sum()
            .rename(columns={"n_casos": "sexual_n"})
        )

        merged = ds4_agg.merge(ds3_agg, on=col, how="outer").fillna(0)
        merged["combined"] = merged["vif_n"] + merged["sexual_n"]
        merged = merged.sort_values("combined", ascending=False).reset_index(drop=True)

        total_vif    = to_int_safe(merged["vif_n"].sum())
        total_sexual = to_int_safe(merged["sexual_n"].sum())

        vif_pct = [
            round(float(v) / total_vif    * 100, 1) if total_vif    else 0.0
            for v in merged["vif_n"]
        ]
        sexual_pct = [
            round(float(v) / total_sexual * 100, 1) if total_sexual else 0.0
            for v in merged["sexual_n"]
        ]

        return {
            "categories":   merged[col].tolist(),
            "vif_pct":      vif_pct,
            "sexual_pct":   sexual_pct,
            "vif_n":        [to_int_safe(v) for v in merged["vif_n"]],
            "sexual_n":     [to_int_safe(v) for v in merged["sexual_n"]],
            "total_vif":    total_vif,
            "total_sexual": total_sexual,
            "caveat_es":    caveat,
        }

    # ── sub-acto 4.3 — sankey ─────────────────────────────────────────────────

    def _build_sub_acto_4_3(self) -> dict:
        thr = self._cfg["thresholds"]
        c   = self._cfg["copy_es"]["sub_acto_4_3"]
        return {
            "title_es":       c["title"],
            "anchor_text_es": c["anchor"],
            "thresholds": {
                "flow_top_pct":          thr["flow_top_pct"],
                "min_aggressor_cases":   thr["min_aggressor_cases"],
                "sankey_min_dept_cases": thr["sankey_min_dept_cases"],
            },
            "ds3":          self._build_sankey_dataset(self._ds3_agr, dataset="ds3"),
            "ds4":          self._build_sankey_dataset(self._ds4_agr, dataset="ds4"),
            "visualization": self._cfg["acto_4_visualization"]["sub_acto_4_3"],
        }

    def _build_sankey_dataset(self, df_agr: pd.DataFrame, dataset: str) -> dict:
        """Build Sankey payloads for regional + 4 depts."""
        result: dict = {}
        min_dept = self._cfg["thresholds"]["sankey_min_dept_cases"]

        # regional
        result["regional"] = self._build_sankey_scope(df_agr, scope_dept=None, dataset=dataset)

        for dept in df_agr["departamento"].unique():
            key    = normalize_dept_key(dept)
            sub    = df_agr[df_agr["departamento"] == dept].copy(deep=False)
            n_dept = int(sub["n_casos"].sum())
            caveat = None
            if n_dept < min_dept:
                caveat = f"Volumen bajo ({n_dept} casos) — interpretación limitada."
            scope = self._build_sankey_scope(sub, scope_dept=dept, dataset=dataset,
                                             caveat_override=caveat)
            result[key] = scope

        return result

    def _build_sankey_scope(
        self,
        df: pd.DataFrame,
        *,
        scope_dept: str | None,
        dataset: str,
        caveat_override: str | None = None,
    ) -> dict:
        """Build nodes + links for one dept scope (or regional if scope_dept is None)."""
        top_pct      = self._cfg["thresholds"]["flow_top_pct"] / 100
        min_cases    = self._cfg["thresholds"]["min_aggressor_cases"]
        others_rule  = self._cfg.get(f"aggressor_others_rule_{dataset}", {})

        # ── 1. aggregate flows across depts (regional) or keep as-is (dept) ──
        flows = (
            df.groupby(["ciclo_vital", "dimension_agresor", "agresor"], as_index=False)
            ["n_casos"].sum()
        )

        if len(flows) == 0:
            return {"n_total": 0, "caveat": caveat_override, "nodes": [], "links": []}

        n_total = int(flows["n_casos"].sum())

        # ── 2. identify named aggressors (total >= threshold) ─────────────────
        agresor_totals = flows.groupby("agresor")["n_casos"].sum()
        named_set      = set(agresor_totals[agresor_totals >= min_cases].index)

        # ── 3. build dim → catch-all mapping for unnamed aggressors ───────────
        dim_to_catchall: dict[str, str] = {}
        for catchall, dims in others_rule.items():
            for d in (dims if isinstance(dims, list) else [dims]):
                dim_to_catchall[d] = catchall

        # ── 4. rename aggressors (vectorised) ─────────────────────────────────
        named_mask       = flows["agresor"].isin(named_set)
        renamed_unnamed  = flows["dimension_agresor"].map(dim_to_catchall).fillna("OTROS")
        flows = flows.copy(deep=False)
        flows["agresor_renamed"] = flows["agresor"].where(named_mask, renamed_unnamed)

        # ── 5. re-aggregate with renamed aggressors ───────────────────────────
        flows_agg = (
            flows.groupby(["ciclo_vital", "dimension_agresor", "agresor_renamed"], as_index=False)
            ["n_casos"].sum()
            .sort_values("n_casos", ascending=False)
            .reset_index(drop=True)
        )

        # ── 6. top-80% filter ─────────────────────────────────────────────────
        cumsum  = flows_agg["n_casos"].cumsum()
        n_keep  = int((cumsum < n_total * top_pct).sum()) + 1
        surviving = flows_agg.iloc[:n_keep].copy()

        # ── 7. node n_cases totals ────────────────────────────────────────────
        col1_n = surviving.groupby("ciclo_vital")["n_casos"].sum().to_dict()
        col2_n = surviving.groupby("dimension_agresor")["n_casos"].sum().to_dict()
        col3_n = surviving.groupby("agresor_renamed")["n_casos"].sum().to_dict()

        nodes = (
            [{"id": f"1__{k}", "label": k, "column": 1, "n_cases": to_int_safe(v)}
             for k, v in sorted(col1_n.items())]
            + [{"id": f"2__{k}", "label": k, "column": 2, "n_cases": to_int_safe(v)}
               for k, v in sorted(col2_n.items())]
            + [{"id": f"3__{k}", "label": k, "column": 3, "n_cases": to_int_safe(v)}
               for k, v in sorted(col3_n.items())]
        )

        # ── 8. adjacency links: col1→col2 and col2→col3 ───────────────────────
        ciclo_totals = surviving.groupby("ciclo_vital")["n_casos"].sum()

        link12 = (
            surviving.groupby(["ciclo_vital", "dimension_agresor"], as_index=False)["n_casos"].sum()
        )
        link23 = (
            surviving.groupby(["dimension_agresor", "agresor_renamed"], as_index=False)["n_casos"].sum()
        )

        links = []

        for rec in link12.to_dict("records"):
            cv, da, n = rec["ciclo_vital"], rec["dimension_agresor"], rec["n_casos"]
            pct = round_pct(n / ciclo_totals[cv] * 100)
            links.append({
                "source":           f"1__{cv}",
                "target":           f"2__{da}",
                "value":            to_int_safe(n),
                "pct_within_ciclo": pct,
            })

        for rec in link23.to_dict("records"):
            da, ag, n = rec["dimension_agresor"], rec["agresor_renamed"], rec["n_casos"]
            links.append({
                "source":           f"2__{da}",
                "target":           f"3__{ag}",
                "value":            to_int_safe(n),
                "pct_within_ciclo": 0.0,
            })

        return {
            "n_total": n_total,
            "caveat":  caveat_override,
            "nodes":   nodes,
            "links":   links,
        }

    # ── sub-acto 4.4 — factor + circumstance ──────────────────────────────────

    def _build_sub_acto_4_4(self) -> dict:
        c = self._cfg["copy_es"]["sub_acto_4_4"]
        return {
            "anchor_text_es": c["anchor"],
            "titles_es":      {"ds4": c["ds4_title"], "ds3": c["ds3_title"]},
            "ds4_factor":       self._build_factor_ds4(),
            "ds3_circumstance": self._build_scenario(self._ds3_circ, "dimension_circunstancia"),
        }

    def _build_factor_ds4(self) -> dict:
        """Apply factor_consolidation_ds4 rule, then aggregate by dept."""
        consolidation: dict[str, list[str]] = self._cfg["factor_consolidation_ds4"]

        # Build raw→consolidated mapping (vectorised)
        raw_to_consolidated: dict[str, str] = {}
        for consolidated_name, raw_list in consolidation.items():
            for raw in raw_list:
                raw_to_consolidated[raw] = consolidated_name

        df = self._ds4_fac.copy(deep=False)
        df = df.copy()
        df["factor_consolidated"] = df["factor"].replace(raw_to_consolidated)

        result: dict = {}
        for dept in df["departamento"].unique():
            key = normalize_dept_key(dept)
            result[key] = self._agg_categorical(
                df[df["departamento"] == dept], "factor_consolidated"
            )
        result["regional"] = self._agg_categorical(df, "factor_consolidated")
        return result

    # ── sub-acto 4.5 — intersectionality ──────────────────────────────────────

    def _build_sub_acto_4_5(self) -> dict:
        c = self._cfg["copy_es"]["sub_acto_4_5"]

        ds3_stats = self._intersect_stats(self._ds3_inter)
        ds4_stats = self._intersect_stats(self._ds4_inter)

        anchor_text = c["anchor_text"].format(
            pct_afro=ds3_stats["pct_afro_narp_f"],
            pct_ind=ds3_stats["pct_indigena_f"],
            pct_sin=ds3_stats["pct_sin_pertenencia_f"],
        )
        anchor_disability = c["anchor_disability"].format(
            pct_disc_ds4=ds4_stats["pct_disability_f"],
            pct_disc_ds3=ds3_stats["pct_disability_f"],
        )

        return {
            "title_es":             c["title"],
            "anchor_text_es":       anchor_text,
            "anchor_disability_es": anchor_disability,
            "caveat_es":            c["caveat"],
            "low_n_note_es":        c["low_n_note"],
            "ds3_stats":            ds3_stats,
            "ds4_stats":            ds4_stats,
            "ethnicity_marginals": {
                "ds3": self._build_ethnicity_marginals(self._ds3_inter),
                "ds4": self._build_ethnicity_marginals(self._ds4_inter),
            },
        }

    def _intersect_stats(self, df: pd.DataFrame) -> dict:
        def _f(mask: pd.Series) -> int:
            return round((df.loc[mask, "n_casos"] * df.loc[mask, "pct_femenino"] / 100).sum())

        n_base_f = round((df["n_casos"] * df["pct_femenino"] / 100).sum())
        disc_f   = _f(df["dimension_discapacidad"] == "CON_CONDICION_DISCAPACIDAD")
        afro_f   = _f(df["dimension_etnia"] == "AFRO_NARP")
        ind_f    = _f(df["dimension_etnia"] == "INDIGENA")
        sin_f    = _f(df["dimension_etnia"] == "SIN_PERTENENCIA_ETNICA")
        noreg_f  = _f(df["dimension_etnia"] == "NO_REGISTRADO")
        git_f    = _f(df["dimension_etnia"] == "GITANO")

        return {
            "pct_disability_f":      round_pct(disc_f  / n_base_f * 100),
            "pct_afro_narp_f":       round_pct(afro_f  / n_base_f * 100),
            "pct_indigena_f":        round_pct(ind_f   / n_base_f * 100),
            "pct_sin_pertenencia_f": round_pct(sin_f   / n_base_f * 100),
            "pct_no_registrado_f":   round_pct(noreg_f / n_base_f * 100),
            "pct_gitano_f":          round_pct(git_f   / n_base_f * 100),
            "n_base_f":              n_base_f,
        }

    def _build_ethnicity_marginals(self, df: pd.DataFrame) -> list[dict]:
        category_order = [
            "SIN_PERTENENCIA_ETNICA", "AFRO_NARP", "NO_REGISTRADO", "INDIGENA", "GITANO",
        ]
        n_base_f = round((df["n_casos"] * df["pct_femenino"] / 100).sum())
        rows = []
        for eth in category_order:
            subset = df[df["dimension_etnia"] == eth]
            n_cases_f   = round((subset["n_casos"] * subset["pct_femenino"] / 100).sum())
            n_total_eth = subset["n_casos"].sum()
            pct_fem_weighted = (
                round_pct((subset["n_casos"] * subset["pct_femenino"]).sum() / n_total_eth)
                if n_total_eth > 0 else 0.0
            )
            rows.append({
                "dimension_etnia":       eth,
                "n_cases_f":             n_cases_f,
                "pct_of_female_cases":   round_pct(n_cases_f / n_base_f * 100),
                "pct_femenino_weighted": pct_fem_weighted,
                "low_n_flag":            n_cases_f < 30,
            })
        return rows


    # ── Top-level orchestrator ────────────────────────────────────────────────

    def build(self) -> None:
        """Run all export acts in sequence: 4, then 5."""
        out_path = self._root / "data" / "dashboard" / "acto_4_forense.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self.export(out_path)
        try:
            self.export_acto_5_ficha_forense_municipal()
            print("[ForenseExporter] acto_5_ficha_forense_municipal.json written")
        except Exception as exc:
            print(f"[ForenseExporter] acto_5_ficha_forense_municipal FAILED: {exc}")
            raise

    # ── Acto 5 — Ficha forense municipal ──────────────────────────────────────

    def _build_acto_5_ficha_forense_municipal(self) -> dict:
        """Return the full payload for acto_5_ficha_forense_municipal.json."""
        a5_cfg       = self._cfg["acto_5_ficha_forense_municipal"]
        min_casos    = self._cfg["forense_local"]["min_total_casos"]
        vs_card_cfgs = a5_cfg["violencia_sexual_stat_cards"]
        vif_card_cfgs = a5_cfg["violencia_intrafamiliar_stat_cards"]

        ds3 = pd.read_parquet(self._paths["ds3_municipio_resumen"])
        ds4 = pd.read_parquet(self._paths["ds4_municipio_resumen"])
        ds3["cod_municipio"] = ds3["cod_municipio"].astype(str)
        ds4["cod_municipio"] = ds4["cod_municipio"].astype(str)

        ds3_idx = ds3.set_index("cod_municipio")
        ds4_idx = ds4.set_index("cod_municipio")
        all_codes = sorted(set(ds3_idx.index) | set(ds4_idx.index))

        def _stat_cards(row, card_cfgs: list) -> list:
            cards = []
            for c in card_cfgs:
                if c["id"] == "distribucion_por_ciclo":
                    nna = row.get(c["source_field_nna"])
                    adu = row.get(c["source_field_adultas"])
                    value = {
                        "nna_pct":     round(float(nna), 1) if nna is not None and not pd.isna(nna) else None,
                        "adultas_pct": round(float(adu), 1) if adu is not None and not pd.isna(adu) else None,
                    }
                else:
                    raw = row.get(c["source_field"])
                    value = str(raw) if (raw is not None and not pd.isna(raw)) else None
                cards.append({
                    "id":             c["id"],
                    "label_es":       c["label_es"],
                    "value":          value,
                    "display_format": c["display_format"],
                    "badge":          None,
                    "sub_value":      None,
                })
            return cards

        def _build_perfil(df_idx, cod: str, card_cfgs: list):
            if cod not in df_idx.index:
                return None
            row = df_idx.loc[cod].to_dict()
            total = int(row["total_casos"])
            if total < min_casos:
                return None
            return {
                "total_casos": total,
                "stat_cards":  _stat_cards(row, card_cfgs),
                "caveat_es":   None,
            }

        municipios: dict = {}
        sin_cobertura: list = []
        n_con_vs  = 0
        n_con_vif = 0

        for cod in all_codes:
            vs_profile  = _build_perfil(ds3_idx, cod, vs_card_cfgs)
            vif_profile = _build_perfil(ds4_idx, cod, vif_card_cfgs)

            has_vs  = vs_profile is not None
            has_vif = vif_profile is not None

            if not has_vs and not has_vif:
                sin_cobertura.append(cod)
                continue

            nombre_es = (
                str(ds3_idx.loc[cod, "municipio"]) if cod in ds3_idx.index
                else str(ds4_idx.loc[cod, "municipio"])
            )
            if has_vs:
                n_con_vs += 1
            if has_vif:
                n_con_vif += 1

            municipios[cod] = {
                "cod_municipio":               cod,
                "nombre_es":                   nombre_es,
                "has_violencia_sexual_profile": has_vs,
                "has_vif_profile":             has_vif,
                "violencia_sexual":            vs_profile,
                "violencia_intrafamiliar":     vif_profile,
            }

        return {
            "metadata": {
                "generated_at":              datetime.now(timezone.utc).isoformat(),
                "source_tables":             [
                    "data/agregados_seforense/ds3_municipio_resumen.parquet",
                    "data/agregados_forense/ds4_municipio_resumen.parquet",
                ],
                "min_total_casos":           min_casos,
                "municipios_con_vs":         n_con_vs,
                "municipios_con_vif":        n_con_vif,
                "municipios_sin_cobertura":  sorted(sin_cobertura),
                "data_source_disclaimer_es": a5_cfg.get("data_source_disclaimer_es"),
            },
            "municipios": municipios,
        }

    def export_acto_5_ficha_forense_municipal(self) -> Path:
        """Validate _build_acto_5_ficha_forense_municipal() against schema and write."""
        payload     = self._build_acto_5_ficha_forense_municipal()
        schema_path = self._root / "schemas" / "acto_5_ficha_forense_municipal.schema.json"
        fname       = self._cfg["acto_5_ficha_forense_municipal"]["output_filename"]
        output_path = self._root / "data" / "dashboard" / fname
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_validated(payload=payload, schema_path=schema_path, output_path=output_path)
        size_kb = output_path.stat().st_size / 1024
        print(f"✓  {fname}  →  {output_path}  ({size_kb:.1f} KB)")
        return output_path


# ── CLI entry-point ───────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export acto_4_forense.json")
    p.add_argument("--config", required=True, type=Path,
                   help="Path to forense_exporter_config.json")
    p.add_argument("--output", required=True, type=Path,
                   help="Destination path for acto_4_forense.json")
    return p.parse_args()


if __name__ == "__main__":
    args   = _parse_args()
    t0     = time.perf_counter()
    exp    = ForenseExporter(args.config)
    exp.export(args.output)
    elapsed = time.perf_counter() - t0
    print(f"   elapsed: {elapsed:.2f}s")
