"""
MasterExporter — Cicatrices Invisibles dashboard JSON exporter (Carril A).

Reads:
    data/master/master_table.parquet
    data/master/tabla_clustering_final.parquet
    (Acts 2, 3, 5 will also read data/cleaned/sexuales_limpio.parquet)

Writes (data/dashboard/):
    acto_1_panorama.json   — choropleth, top-10, regional timeline, stat cards
    acto_2_brechas.json    — [future]
    acto_3_tipologia.json  — [future]
    acto_5_municipios.json — [future]

Usage:
    python -m src.exporters.master_exporter               # uses config/master_exporter_config.json
    python -m src.exporters.master_exporter --config config/master_exporter_config.json
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.exporters.exporter_utils import write_json_validated


# ---------------------------------------------------------------------------
# Narrative / UI constants — Acto 2 and Acto 3 only.
# Acto 1 constants (_EXCLUDED_CODES, _HIGHLIGHTED_MUNICIPALITIES, _UI_TEXT,
# _CLUSTER_LEGEND) have been migrated to config/master_exporter_config.json
# and are now loaded in __init__ via self.config. Phase 3.2/3.3 will migrate
# the remaining constants below.
# ---------------------------------------------------------------------------

# _UI_TEXT_ACT2 migrated to config/master_exporter_config.json (Phase 3.2)

# _UI_TEXT_ACT3, _DISPLAY_LABELS, _MINOR_CATEGORIES, _ACT3_ARCHETYPES migrated
# to config/master_exporter_config.json (Phase 3.3)


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------

def _sanitize(obj):
    """
    Recursively convert every value in a nested dict/list to a JSON-safe Python
    native type.  Called once on the full payload before json.dump so that no
    numpy scalar, pandas NA, or IEEE-754 non-finite float reaches the encoder.

    Why not a custom JSONEncoder?  encoder.default() is only called for types
    the stdlib encoder cannot handle at all.  Python's float('nan') IS handled
    by the stdlib encoder — it emits the non-standard JSON literal NaN.  The
    sanitizer intercepts it first, converting it to None (→ JSON null).
    """
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    # Python float NaN / ±Inf — must be checked before numpy, as np.nan is also float
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return None if (math.isnan(float(obj)) or math.isinf(float(obj))) else float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [_sanitize(v) for v in obj.tolist()]
    # pandas NA, NaT, pd.NA — catch-all for any remaining NA sentinel
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj


# ---------------------------------------------------------------------------
# MasterExporter
# ---------------------------------------------------------------------------

class MasterExporter:
    """
    Produces optimized JSON payloads for the Cicatrices Invisibles frontend.

    Every section method returns a pure Python dict/list ready for json.dump.
    No business logic is hardcoded: output path is resolved from base_config.json
    (key: paths.dashboard_dir); if absent, falls back to data/dashboard/.

    Design constraints (mirrors the rest of the pipeline):
    - Column-selection at read time (only loads what each section needs).
    - All aggregations are vectorized pandas operations; no Python row loops.
    - deep=False copies wherever the source DataFrame is not mutated.
    - Output is compact JSON (no indent) to minimize frontend payload size.
    - NaN / pd.NA → JSON null via _sanitize(), called once before json.dump.
    - All floats rounded to 2 decimal places at the aggregation step.
    """

    _MASTER_COLS: list[str] = [
        "cod_municipio", "anio_hecho", "municipio", "departamento",
        "icv_gen_f_score",
    ]
    _MASTER_COLS_ACT2: list[str] = [
        "cod_municipio", "anio_hecho", "municipio", "departamento",
        "casos_vif_nna_f",    "casos_vif_adultas_f",
        "casos_sexual_nna_f", "casos_sexual_adultas_f",
        "casos_vif_nna_m",    "casos_vif_adultos_m",
        "casos_sexual_nna_m", "casos_sexual_adultos_m",
        "tasa_vif_nna_f",     "tasa_vif_adultas_f",
        "tasa_sexual_nna_f",  "tasa_sexual_adultas_f",
        "tasa_vif_nna_m",     "tasa_vif_adultos_m",
        "tasa_sexual_nna_m",  "tasa_sexual_adultos_m",
        "brecha_vif_nna",     "brecha_vif_adultas",
        "brecha_sexual_nna",  "brecha_sexual_adultas",
        "icv_gen_f_score",
    ]
    _CLUSTERING_COLS: list[str] = [
        "cod_municipio", "municipio", "departamento",
        "icv_gen_f_score", "cluster_id", "cluster_name",
    ]
    _MASTER_COLS_ACT3: list[str] = [
        "cod_municipio", "anio_hecho", "departamento",
        "tasa_sexual_nna_f",
        "pob_f_0_17", "pob_f_18_mas",
        "casos_vif_nna_f", "casos_vif_adultas_f",
        "casos_sexual_nna_f", "casos_sexual_adultas_f",
    ]
    _CLUSTERING_COLS_ACT3: list[str] = [
        "cod_municipio", "municipio", "departamento",
        "tasa_vif_nna_f", "tasa_vif_adultas_f",
        "tasa_sexual_nna_f", "tasa_sexual_adultas_f",
        "cluster_id", "cluster_name",
    ]
    _SEXUALES_COLS: list[str] = ["departamento", "dimension_delito", "cantidad", "genero_victima"]
    _MASTER_COLS_ACT5: list[str] = [
        "cod_municipio", "anio_hecho", "municipio", "departamento", "icv_gen_f_score",
        "tasa_vif_nna_f", "tasa_sexual_nna_f", "tasa_vif_adultas_f", "tasa_sexual_adultas_f",
    ]
    _CLUSTERING_COLS_ACT5: list[str] = [
        "cod_municipio", "municipio", "departamento",
        "icv_gen_f_score", "cluster_id", "cluster_name",
        "tasa_vif_nna_f", "tasa_sexual_nna_f", "tasa_vif_adultas_f", "tasa_sexual_adultas_f",
    ]

    def __init__(self, config_path: str) -> None:
        self._config_path = Path(config_path).resolve()
        self._project_root = self._config_path.parent.parent

        with open(self._config_path, encoding="utf-8") as fh:
            self.config = json.load(fh)

        paths = self.config.get("paths", {})
        # master_exporter_config.json supplies file paths; derive directories from them.
        # Falls back to base_config.json style (directory keys) for Act 2/3 compat.
        if "master_table" in paths:
            self._master_dir    = self._project_root / Path(paths["master_table"]).parent
            self._cleaned_dir   = self._project_root / Path(paths["sexuales_limpio"]).parent
            self._dashboard_dir = self._project_root / paths.get("output_dir", "data/dashboard")
            self._schema_dir    = self._project_root / paths.get("schema_dir", "schema")
        else:
            self._master_dir    = self._project_root / paths.get("master_dir", "data/master")
            self._cleaned_dir   = self._project_root / paths.get("cleaned_dir", "data/cleaned")
            self._dashboard_dir = self._project_root / paths.get("dashboard_dir", "data/dashboard")
            self._schema_dir    = self._project_root / "schema"

        # Acto 1 business rules — loaded from config, not module-level constants.
        br = self.config.get("business_rules", {})
        self._excluded_codes    = frozenset(br.get("excluded_codes", []))
        self._highlighted_codes = frozenset(br.get("highlighted_municipalities_codes", []))

    # ------------------------------------------------------------------
    # Public API — Acto 1  (Phase 3.1 — config-driven, schema-validated)
    # ------------------------------------------------------------------

    def build_acto_1(self) -> dict:
        """Return the full sanitized Acto 1 payload as a plain-Python dict (no I/O)."""
        master     = self._load_master_table()
        clustering = self._load_clustering_final()
        payload = {
            "metadata":      self._build_metadata_acto_1(),
            "sub_acto_1_1":  self._build_sub_acto_1_1(clustering),
            "sub_acto_1_2":  self._build_sub_acto_1_2(master, clustering),
            "sub_acto_1_3":  self._build_sub_acto_1_3(clustering),
            "sub_acto_1_4":  self._build_sub_acto_1_4(master),
        }
        return _sanitize(payload)

    def export_acto_1(self, output_path: Path | None = None) -> None:
        """Validate build_acto_1() against acto_1_panorama.schema.json and write."""
        if output_path is None:
            fname = self.config.get("output_filenames", {}).get("acto_1", "acto_1_panorama.json")
            output_path = self._dashboard_dir / fname
        schema_path = self._schema_dir / "acto_1_panorama.schema.json"
        write_json_validated(
            payload=self.build_acto_1(),
            schema_path=schema_path,
            output_path=output_path,
        )
        size_kb = output_path.stat().st_size / 1024
        print(f"✓  acto_1_panorama.json  →  {output_path}  ({size_kb:.1f} KB)")

    # ------------------------------------------------------------------
    # Public API — Acto 2  (Phase 3.2 — config-driven, schema-validated)
    # ------------------------------------------------------------------

    def build_acto_2(self) -> dict:
        """Return the full sanitized Acto 2 payload as a plain-Python dict (no I/O)."""
        master     = self._load_master_act2()
        top3_items = self._build_top10_brechas(master)["items"]
        payload = {
            "metadata":      self._build_metadata_acto_2(),
            "sub_acto_2_1":  self._build_sub_acto_2_1(master),
            "sub_acto_2_2":  self._build_sub_acto_2_2(master),
            "sub_acto_2_3":  self._build_sub_acto_2_3(master),
            "sub_acto_2_4":  self._build_sub_acto_2_4(master, top3_items),
            "sub_acto_2_5":  self._build_sub_acto_2_5(master),
            "sub_acto_2_6":  self._build_sub_acto_2_6(master),
        }
        return _sanitize(payload)

    def export_acto_2(self, output_path: Path | None = None) -> None:
        """Validate build_acto_2() against acto_2_brechas.schema.json and write."""
        if output_path is None:
            fname = self.config.get("output_filenames", {}).get("acto_2", "acto_2_brechas.json")
            output_path = self._dashboard_dir / fname
        schema_path = self._schema_dir / "acto_2_brechas.schema.json"
        write_json_validated(
            payload=self.build_acto_2(),
            schema_path=schema_path,
            output_path=output_path,
        )
        size_kb = output_path.stat().st_size / 1024
        print(f"✓  acto_2_brechas.json  →  {output_path}  ({size_kb:.1f} KB)")

    def build_acto_3(self) -> dict:
        """Return the full acto_3_tipologia payload (no I/O). All data is sanitized."""
        clustering = self._load_clustering_act3()
        master     = self._load_master_act3()
        sexuales   = self._load_sexuales()
        tipologia  = self._build_tipologia_delito(sexuales)

        payload = {
            "metadata":     self._build_metadata_acto_3(),
            "sub_acto_3_1": self._build_sub_acto_3_1(tipologia),
            "sub_acto_3_2": self._build_sub_acto_3_2(clustering),
            "sub_acto_3_3": self._build_sub_acto_3_3(master),
            "sub_acto_3_4": self._build_sub_acto_3_4(tipologia),
            "sub_acto_3_5": self._build_sub_acto_3_5(master),
        }
        return _sanitize(payload)

    def export_acto_3(self) -> None:
        """Write acto_3_tipologia.json, schema-validated."""
        fname       = self.config.get("output_filenames", {}).get("acto_3", "acto_3_tipologia.json")
        out_path    = self._dashboard_dir / fname
        schema_path = self._schema_dir / "acto_3_tipologia.schema.json"
        write_json_validated(
            payload=self.build_acto_3(),
            schema_path=schema_path,
            output_path=out_path,
        )
        size_kb = out_path.stat().st_size / 1024
        print(f"✓  {fname}  →  {out_path}  ({size_kb:.1f} KB)")

    # ------------------------------------------------------------------
    # Acto 3 — metadata & sub-act wrappers
    # ------------------------------------------------------------------

    def _build_metadata_acto_3(self) -> dict:
        br = self.config["business_rules"]
        return {
            "version":           "1.0.0",
            "generated_at":      datetime.now(timezone.utc).isoformat(),
            "year_range":        list(br["year_range"]),
            "n_total":           br["n_total_features"],
            "n_clustered":       br["n_clustered"],
            "act_disclaimer_es": self.config["copy_es"]["act_disclaimers"]["acto_3"],
            "source_files": {
                "tabla_clustering_final": self.config["paths"]["tabla_clustering"],
                "master_table":           self.config["paths"]["master_table"],
                "sexuales_limpio":        self.config["paths"]["sexuales_limpio"],
            },
        }

    def _build_sub_acto_3_1(self, tipologia: dict) -> dict:
        copy = self.config["copy_es"]["acto_3"]["sub_acto_3_1"]
        card_templates = self.config["acto_3_kpis"]["sub_acto_3_1"]["stat_cards"]
        stat_cards = [
            {**tmpl, "value": tipologia[tmpl["id"]]}
            for tmpl in card_templates
        ]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "stat_cards":     stat_cards,
        }

    def _build_sub_acto_3_2(self, clustering: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_3"]["sub_acto_3_2"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": self._build_capa3a_scatter(clustering),
        }

    def _build_sub_acto_3_3(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_3"]["sub_acto_3_3"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "subtitle_es":    copy["subtitle_es"],
            "caveat_es":      copy.get("caveat_es"),
            "data": self._build_capa3a_dumbbell(master),
        }

    def _build_sub_acto_3_4(self, tipologia: dict) -> dict:
        copy = self.config["copy_es"]["acto_3"]["sub_acto_3_4"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": {
                "total_cases":   tipologia["total_cases"],
                "global":        tipologia["global"],
                "by_department": tipologia["by_department"],
            },
        }

    def _build_sub_acto_3_5(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_3"]["sub_acto_3_5"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": self._build_timeline_sexual_nna(master),
        }

    # ------------------------------------------------------------------
    # Loaders — minimal column selection at read time
    # ------------------------------------------------------------------

    def _load_master_table(self) -> pd.DataFrame:
        path = self._master_dir / "master_table.parquet"
        df = pd.read_parquet(path, columns=self._MASTER_COLS)
        df["cod_municipio"] = df["cod_municipio"].astype(str)
        return df

    def _load_clustering_final(self) -> pd.DataFrame:
        path = self._master_dir / "tabla_clustering_final.parquet"
        df = pd.read_parquet(path, columns=self._CLUSTERING_COLS)
        df["cod_municipio"] = df["cod_municipio"].astype(str)
        return df

    def _load_master_act2(self) -> pd.DataFrame:
        path = self._master_dir / "master_table.parquet"
        df = pd.read_parquet(path, columns=self._MASTER_COLS_ACT2)
        df["cod_municipio"] = df["cod_municipio"].astype(str)
        return df

    def _load_master_act3(self) -> pd.DataFrame:
        path = self._master_dir / "master_table.parquet"
        df = pd.read_parquet(path, columns=self._MASTER_COLS_ACT3)
        df["cod_municipio"] = df["cod_municipio"].astype(str)
        return df

    def _load_clustering_act3(self) -> pd.DataFrame:
        path = self._master_dir / "tabla_clustering_final.parquet"
        df = pd.read_parquet(path, columns=self._CLUSTERING_COLS_ACT3)
        df["cod_municipio"] = df["cod_municipio"].astype(str)
        return df

    def _load_sexuales(self) -> pd.DataFrame:
        path = self._cleaned_dir / "sexuales_limpio.parquet"
        df = pd.read_parquet(path, columns=self._SEXUALES_COLS)
        # Carril A scope: female victims only. See Phase 0 audit 2026-07-03.
        df = df[df["genero_victima"] == "FEMENINO"].copy(deep=False)
        return df.drop(columns=["genero_victima"])

    def _load_master_act5(self) -> pd.DataFrame:
        path = self._master_dir / "master_table.parquet"
        df = pd.read_parquet(path, columns=self._MASTER_COLS_ACT5)
        df["cod_municipio"] = df["cod_municipio"].astype(str)
        return df

    def _load_clustering_act5(self) -> pd.DataFrame:
        path = self._master_dir / "tabla_clustering_final.parquet"
        df = pd.read_parquet(path, columns=self._CLUSTERING_COLS_ACT5)
        df["cod_municipio"] = df["cod_municipio"].astype(str)
        return df

    # ------------------------------------------------------------------
    # Section: metadata (Acto 1)
    # ------------------------------------------------------------------

    def _build_metadata_acto_1(self) -> dict:
        br   = self.config["business_rules"]
        cfg_paths = self.config["paths"]
        return {
            "version":           "1.0.0",
            "generated_at":      datetime.now(timezone.utc).isoformat(),
            "year_range":        list(br["year_range"]),
            "n_total":           br["n_total_features"],
            "n_clustered":       br["n_clustered"],
            "act_disclaimer_es": self.config["copy_es"]["act_disclaimers"]["acto_1"],
            "source_files": {
                "master_table":          cfg_paths["master_table"],
                "tabla_clustering_final": cfg_paths["tabla_clustering"],
            },
        }

    # ------------------------------------------------------------------
    # Sub-act wrappers — Acto 1 (Phase 3.1)
    # ------------------------------------------------------------------

    def _build_sub_acto_1_1(self, clustering: pd.DataFrame) -> dict:
        copy     = self.config["copy_es"]["acto_1"]["sub_acto_1_1"]
        kpi_cfg  = self.config["acto_1_kpis"]["sub_acto_1_1"]
        tmpls    = kpi_cfg["stat_cards"]

        n_clustered = len(clustering)
        n_alta      = int((clustering["cluster_id"] == 1).sum())
        pct_alta    = round(n_alta / n_clustered * 100, 1)
        icv_avg     = round(float(clustering["icv_gen_f_score"].mean()), 2)

        computed = {
            "n_municipios":          {"value": n_clustered, "sub_value_val": None},
            "n_alta_severidad":      {"value": n_alta,      "sub_value_val": pct_alta},
            "icv_promedio_regional": {"value": icv_avg,     "sub_value_val": None},
        }
        stat_cards = []
        for tmpl in tmpls:
            c = {**tmpl, "value": computed[tmpl["id"]]["value"]}
            if tmpl["sub_value"] is not None:
                c["sub_value"] = {**tmpl["sub_value"], "value": computed[tmpl["id"]]["sub_value_val"]}
            stat_cards.append(c)

        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "caveat_es":      kpi_cfg["caveat_es"],
            "stat_cards":     stat_cards,
        }

    def _build_sub_acto_1_2(self, master: pd.DataFrame, clustering: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_1"]["sub_acto_1_2"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "caveat_es":      copy["caveat_es"],
            "data": self._build_choropleth(master, clustering),
        }

    def _build_sub_acto_1_3(self, clustering: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_1"]["sub_acto_1_3"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": self._build_top10_ranking(clustering),
        }

    def _build_sub_acto_1_4(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_1"]["sub_acto_1_4"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": self._build_timeline(master),
        }

    # ------------------------------------------------------------------
    # Section: stat_cards
    # ------------------------------------------------------------------

    def _build_stat_cards(self, clustering: pd.DataFrame) -> list[dict]:
        """
        Card 1 — 179: canonical DANE municipality count for the 4 departments.
                       Includes the 2 excluded municipalities (explained by the
                       Chocó disclaimer in caveat_es).

        Card 2 — 107 / 60%: from tabla_clustering_final (177 clustered municipalities).
                             The pct denominator is 177, matching the model's scope.

        Card 3 — ICV avg: mean of per-municipality average ICV across the 177
                          clustered municipalities. The 2 excluded ones are omitted
                          because their near-zero ICV reflects structural underreporting,
                          not genuine low violence — including them would depress the
                          regional average in a misleading way.
        """
        n_total = self.config["business_rules"]["n_total_features"]
        n_alta = int((clustering["cluster_id"] == 1).sum())
        pct_alta = round(n_alta / len(clustering) * 100)
        icv_avg = round(float(clustering["icv_gen_f_score"].mean()), 2)

        return [
            {
                "id": "n_municipios",
                "value": n_total,
                "label": "municipios analizados",
            },
            {
                "id": "n_alta_severidad",
                "value": n_alta,
                "pct": pct_alta,
                "label": "en alta severidad",
            },
            {
                "id": "icv_promedio_regional",
                "value": icv_avg,
                "label": "ICV-GEN-F promedio regional",
            },
        ]

    # ------------------------------------------------------------------
    # Section: choropleth
    # ------------------------------------------------------------------

    def _load_coords(self) -> dict[str, dict]:
        """Return {cod_municipio: {lat, lon}} from municipios_pacifico.json."""
        ref_path = self._project_root / self.config["paths"]["municipios_coords"]
        with open(ref_path, encoding="utf-8") as fh:
            ref = json.load(fh)
        return {
            code: {"lat": info.get("lat"), "lon": info.get("lon")}
            for code, info in ref["municipios"].items()
        }

    def _build_choropleth(
        self, master: pd.DataFrame, clustering: pd.DataFrame
    ) -> dict:
        """
        179 features — one per municipality, sorted by icv_promedio descending so
        the frontend can iterate in display-priority order.

        icv_promedio: mean of icv_gen_f_score across 8 years from master_table.
        cluster_id / cluster_name: null for codes 27150 and 27493 (excluded pair).
        excluded_from_model: boolean flag for the frontend to apply grey styling.
        lat / lon: polygon centroid from config/municipios_pacifico.json for
                   the circle-marker dot map (null for 27493 which has no polygon).

        The geo_join_key ('cod_municipio') matches the key schema in
        municipios_pacifico.json and the properties of the frontend GeoJSON.
        """
        # Per-municipality ICV average — all 179 municipalities
        icv_by_mun = (
            master.groupby("cod_municipio")
            .agg(
                municipio=("municipio", "first"),
                departamento=("departamento", "first"),
                icv_promedio=("icv_gen_f_score", "mean"),
            )
            .reset_index()
        )
        # Round before joining to avoid float precision drift in downstream math
        icv_by_mun["icv_promedio"] = icv_by_mun["icv_promedio"].round(2).astype(float)

        # Left join: preserves all 179; NA fills cluster cols for excluded pair
        cluster_cols = clustering[["cod_municipio", "cluster_id", "cluster_name"]].copy(deep=False)
        merged = icv_by_mun.merge(cluster_cols, on="cod_municipio", how="left")

        # Compute n_clustered while cluster_id is still float64 (NaN = excluded)
        n_clustered = int(merged["cluster_id"].notna().sum())

        # pandas left-join converts int32 cluster_id → float64 (NaN for the 2 excluded rows).
        # Cast back to nullable Int32: non-null values → Python int in to_dict();
        # null values → pd.NA, handled as null by _JsonEncoder.
        merged["cluster_id"] = merged["cluster_id"].astype("Int32")

        # cluster_name: string-backed column; left-join fills excluded rows with float NaN.
        # .where()/.loc on pandas string dtypes can silently preserve NaN on assignment.
        # np.where() creates a fresh object array, guaranteeing Python None for those cells.
        merged["cluster_name"] = np.where(
            merged["cluster_name"].isna(), None, merged["cluster_name"]
        )

        merged["excluded_from_model"] = merged["cod_municipio"].isin(self._excluded_codes)

        # Inject centroid coordinates for the circle-marker dot map
        coords = self._load_coords()
        merged["lat"] = merged["cod_municipio"].map(lambda c: coords.get(c, {}).get("lat"))
        merged["lon"] = merged["cod_municipio"].map(lambda c: coords.get(c, {}).get("lon"))

        merged = merged.sort_values("icv_promedio", ascending=False).reset_index(drop=True)

        icv_min = round(float(merged["icv_promedio"].min()), 2)
        icv_max = round(float(merged["icv_promedio"].max()), 2)

        # Rename Spanish parquet column names to schema English keys before serialization
        merged = merged.rename(columns={
            "municipio":    "municipality",
            "departamento": "department",
            "icv_promedio": "icv_average",
        })

        return {
            "geo_join_key": "cod_municipio",
            "n_features":   len(merged),
            "n_clustered":  n_clustered,
            "icv_range":    {"min": icv_min, "max": icv_max},
            "cluster_legend": self.config["cluster_legend"],
            "features":     merged.to_dict(orient="records"),
        }

    # ------------------------------------------------------------------
    # Section: top10_ranking
    # ------------------------------------------------------------------

    def _build_top10_ranking(self, clustering: pd.DataFrame) -> dict:
        """
        Top 10 municipalities ranked by pre-averaged icv_gen_f_score
        (tabla_clustering_final — no re-computation from master_table).

        echarts_series is shaped for a horizontal ECharts bar chart:
        - categories: ascending ICV order so rank 1 renders at the chart top
          (ECharts renders category[0] at the bottom of the y-axis).
        - highlight_flags: parallel bool array; true for Pasto and Popayán —
          the frontend applies a border style, NOT a different color.

        items: descending (rank 1 first) for synchronized-hover tooltip lookup
        and for any companion table rendered alongside the chart.
        """
        top10_desc = (
            clustering.nlargest(10, "icv_gen_f_score")
            .reset_index(drop=True)
            .copy(deep=False)
        )

        # ECharts-ready arrays — ascending so highest ICV appears at chart top
        top10_asc = top10_desc.sort_values("icv_gen_f_score", ascending=True)
        categories: list[str] = top10_asc["municipio"].tolist()
        values: list[float] = top10_asc["icv_gen_f_score"].round(2).tolist()
        # Highlight matched by cod_municipio code (from config), not municipality name
        highlight_flags: list[bool] = (
            top10_asc["cod_municipio"].isin(self._highlighted_codes).tolist()
        )

        # Items table — vectorized construction, descending order
        top10_desc["rank"]        = range(1, 11)
        top10_desc["highlight"]   = top10_desc["cod_municipio"].isin(self._highlighted_codes)
        top10_desc["icv_average"] = top10_desc["icv_gen_f_score"].round(2)

        items: list[dict] = (
            top10_desc[
                ["rank", "cod_municipio", "municipio", "departamento",
                 "icv_average", "cluster_id", "cluster_name", "highlight"]
            ]
            .rename(columns={"municipio": "municipality", "departamento": "department"})
            .to_dict(orient="records")
        )

        return {
            "echarts_series": {
                "type": "bar",
                "categories": categories,
                "values": values,
                "highlight_flags": highlight_flags,
            },
            "highlighted_municipalities": sorted(self._highlighted_codes),
            "items": items,
        }

    # ------------------------------------------------------------------
    # Section: timeline
    # ------------------------------------------------------------------

    def _build_timeline(self, master: pd.DataFrame) -> dict:
        """
        Regional ICV-GEN-F average per year, all 179 municipalities included.

        ECharts line chart shape:
        - x_axis: list[int] — calendar years 2018–2025
        - series[0].data: list[float | None] — avg ICV per year (null if missing)
        """
        agg = (
            master.groupby("anio_hecho")["icv_gen_f_score"]
            .mean()
            .round(2)
            .sort_index()
        )

        years: list[int] = [int(y) for y in agg.index.tolist()]
        values: list[float | None] = [
            None if pd.isna(v) else round(float(v), 2)
            for v in agg.tolist()
        ]

        return {
            "chart_type": "line",
            "x_axis": years,
            "series": [
                {
                    "name": "ICV-GEN-F promedio regional",
                    "data": values,
                }
            ],
        }

    # ==================================================================
    # Act 2 — La fractura de género
    # ==================================================================

    def _build_metadata_acto_2(self) -> dict:
        br = self.config["business_rules"]
        return {
            "version":           "1.0.0",
            "generated_at":      datetime.now(timezone.utc).isoformat(),
            "year_range":        list(br["year_range"]),
            "n_total":           br["n_total_features"],
            "act_disclaimer_es": self.config["copy_es"]["act_disclaimers"]["acto_2"],
            "source_files": {
                "master_table": self.config["paths"]["master_table"],
            },
            "methodology": {
                "kpi_ratio":         "sum(casos_f) / sum(casos_m) — todos los años y municipios agregados",
                "butterfly_tasas":   "media de tasas por 100k entre municipios, por año",
                "butterfly_ratio":   "sum(casos_f) / sum(casos_m) por año — sin sesgo de selección",
                "top10_metrica":     "mediana de las 4 brechas promedio por municipio (skipna=True)",
                "gap_cols_excluded": "NaN excluidos — solo años con registros en ambos géneros",
            },
        }

    # ------------------------------------------------------------------
    # Sub-act wrappers — Acto 2 (Phase 3.2)
    # ------------------------------------------------------------------

    def _build_sub_acto_2_1(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_2"]["sub_acto_2_1"]
        card_templates = self.config["acto_2_kpis"]["sub_acto_2_1"]["stat_cards"]
        kpi = self._build_kpi_regional(master)
        stat_cards = [
            {**tmpl, "value": kpi[tmpl["id"]]["aggregate_ratio"]}
            for tmpl in card_templates
        ]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "stat_cards":     stat_cards,
        }

    def _build_sub_acto_2_2(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_2"]["sub_acto_2_2"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": {
                "vif":    self._build_butterfly(master, "vif"),
                "sexual": self._build_butterfly(master, "sexual"),
            },
        }

    def _build_sub_acto_2_3(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_2"]["sub_acto_2_3"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": self._build_top10_brechas(master),
        }

    def _build_sub_acto_2_4(self, master: pd.DataFrame, top10_items: list[dict]) -> dict:
        copy = self.config["copy_es"]["acto_2"]["sub_acto_2_4"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "caveat_es":      copy["caveat_es"],
            "data": self._build_mapa_brechas(master, top10_items),
        }

    def _build_sub_acto_2_5(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_2"]["sub_acto_2_5"]
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "caveat_es":      copy["caveat_es"],
            "data": self._build_scatter_icv_brecha(master),
        }

    def _build_sub_acto_2_6(self, master: pd.DataFrame) -> dict:
        copy = self.config["copy_es"]["acto_2"]["sub_acto_2_6"]
        trends = self._build_tendencias_temporales(master)
        beat4  = self._build_beat4_diagnostico(master)
        return {
            "title_es":       copy["title_es"],
            "anchor_text_es": copy["anchor_text_es"],
            "data": {**trends, "beat4_diagnostic": beat4},
        }

    # ------------------------------------------------------------------
    # Section: regional_kpi (Beat 1 — Big Numbers)
    # ------------------------------------------------------------------

    def _build_kpi_regional(self, df: pd.DataFrame) -> dict:
        """
        Two hierarchical Big Numbers built as sum/sum regional aggregates (all
        8 years × 179 municipalities).  The sum/sum method is required by the
        guide to avoid the selection-bias introduced by mean(brecha_municipal)
        when municipalities with near-zero male counts inflate the ratio.

        Primary  — violencia sexual adulta  (~6:1): narrative hook
        Secondary — VIF adulta              (~4:1): transversal corroboration
        """
        def _agg(f_col: str, m_col: str, label: str) -> dict:
            total_f = int(df[f_col].sum())
            total_m = int(df[m_col].sum())
            ratio   = round(total_f / total_m, 2) if total_m > 0 else None
            return {
                "label":           label,
                "cases_f_total":   total_f,
                "cases_m_total":   total_m,
                "aggregate_ratio": ratio,
            }

        return {
            "sexual_adults": _agg(
                "casos_sexual_adultas_f", "casos_sexual_adultos_m",
                "Violencia sexual contra mujeres adultas",
            ),
            "vif_adults": _agg(
                "casos_vif_adultas_f", "casos_vif_adultos_m",
                "Violencia intrafamiliar contra mujeres adultas",
            ),
            "sexual_nna": _agg(
                "casos_sexual_nna_f", "casos_sexual_nna_m",
                "Violencia sexual contra niñas y adolescentes",
            ),
            "vif_nna": _agg(
                "casos_vif_nna_f", "casos_vif_nna_m",
                "Violencia intrafamiliar contra niñas y adolescentes",
            ),
        }

    # ------------------------------------------------------------------
    # Section: butterfly_vif / butterfly_sexual (Beat 2)
    # ------------------------------------------------------------------

    def _build_butterfly(self, df: pd.DataFrame, violencia: str) -> list[dict]:
        """
        Returns 8 year-entries each containing two lifecycle tabs (nna, adultas).

        tasa_f / tasa_m — regional mean of per-municipality rates (×100k),
            already a comparable unit across municipalities.
        ratio — sum(casos_f) / sum(casos_m) per year: unbiased aggregate ratio
            (avoids inflating the ratio via municipalities with near-zero male counts).
        casos_f / casos_m — regional sums for context tooltips.

        ECharts butterfly:  series [tasa_f (positive), -tasa_m (negative)]
                            yAxis.type='category' with years as categories.
        """
        if violencia == "vif":
            tf_nna,  tm_nna  = "tasa_vif_nna_f",     "tasa_vif_nna_m"
            tf_adu,  tm_adu  = "tasa_vif_adultas_f",  "tasa_vif_adultos_m"
            cf_nna,  cm_nna  = "casos_vif_nna_f",     "casos_vif_nna_m"
            cf_adu,  cm_adu  = "casos_vif_adultas_f", "casos_vif_adultos_m"
        else:
            tf_nna,  tm_nna  = "tasa_sexual_nna_f",     "tasa_sexual_nna_m"
            tf_adu,  tm_adu  = "tasa_sexual_adultas_f",  "tasa_sexual_adultos_m"
            cf_nna,  cm_nna  = "casos_sexual_nna_f",     "casos_sexual_nna_m"
            cf_adu,  cm_adu  = "casos_sexual_adultas_f", "casos_sexual_adultos_m"

        agg = (
            df.groupby("anio_hecho")
            .agg(
                tasa_f_nna=(tf_nna,  "mean"),
                tasa_m_nna=(tm_nna,  "mean"),
                casos_f_nna=(cf_nna, "sum"),
                casos_m_nna=(cm_nna, "sum"),
                tasa_f_adu=(tf_adu,  "mean"),
                tasa_m_adu=(tm_adu,  "mean"),
                casos_f_adu=(cf_adu, "sum"),
                casos_m_adu=(cm_adu, "sum"),
            )
            .reset_index()
            .sort_values("anio_hecho")
        )

        def _ratio(f: int, m: int) -> float | None:
            return round(f / m, 2) if m > 0 else None

        return [
            {
                "year": int(r["anio_hecho"]),
                "nna": {
                    "rate_f":   round(float(r["tasa_f_nna"]), 2),
                    "rate_m":   round(float(r["tasa_m_nna"]), 2),
                    "ratio":    _ratio(int(r["casos_f_nna"]), int(r["casos_m_nna"])),
                    "cases_f":  int(r["casos_f_nna"]),
                    "cases_m":  int(r["casos_m_nna"]),
                },
                "adults": {
                    "rate_f":   round(float(r["tasa_f_adu"]), 2),
                    "rate_m":   round(float(r["tasa_m_adu"]), 2),
                    "ratio":    _ratio(int(r["casos_f_adu"]), int(r["casos_m_adu"])),
                    "cases_f":  int(r["casos_f_adu"]),
                    "cases_m":  int(r["casos_m_adu"]),
                },
            }
            for _, r in agg.iterrows()
        ]

    # ------------------------------------------------------------------
    # Section: top10_brechas (Beat 3 — territorial ranking)
    # ------------------------------------------------------------------

    def _build_top10_brechas(self, df: pd.DataFrame) -> dict:
        """
        Top 10 municipalities by gender gap, following the notebook methodology:
          1. Per-municipality mean of each gap column across 8 years (NaN excluded).
          2. Per-municipality MEDIAN across the 4 averaged gap columns (skipna=True).
             Median is more robust than mean when up to 3 of the 4 columns are NaN.
          3. Top 10 by descending median gap.

        Returns a dict with echarts_series (for the bar chart) and items (full records).
        The guide (docs/analisis_brechas.json) validates this produces EL TAMBO first.
        """
        gap_cols = [
            "brecha_vif_nna", "brecha_vif_adultas",
            "brecha_sexual_nna", "brecha_sexual_adultas",
        ]
        per_mun = (
            df.groupby("cod_municipio")
            .agg(
                municipio=("municipio",                        "first"),
                departamento=("departamento",                  "first"),
                brecha_vif_nna=("brecha_vif_nna",             "mean"),
                brecha_vif_adultas=("brecha_vif_adultas",     "mean"),
                brecha_sexual_nna=("brecha_sexual_nna",       "mean"),
                brecha_sexual_adultas=("brecha_sexual_adultas","mean"),
            )
            .reset_index()
        )
        per_mun["brecha_promedio"] = per_mun[gap_cols].median(axis=1, skipna=True)

        top10 = (
            per_mun.nlargest(10, "brecha_promedio")
            .reset_index(drop=True)
            .copy(deep=False)
        )
        top10["rank"] = range(1, 11)
        for col in gap_cols + ["brecha_promedio"]:
            top10[col] = top10[col].round(2)

        items = (
            top10[
                ["rank", "cod_municipio", "municipio", "departamento",
                 "brecha_vif_nna", "brecha_vif_adultas",
                 "brecha_sexual_nna", "brecha_sexual_adultas", "brecha_promedio"]
            ]
            .rename(columns={
                "municipio":          "municipality",
                "departamento":       "department",
                "brecha_vif_nna":     "gap_vif_nna",
                "brecha_vif_adultas": "gap_vif_adults",
                "brecha_sexual_nna":  "gap_sexual_nna",
                "brecha_sexual_adultas": "gap_sexual_adults",
                "brecha_promedio":    "gap_average",
            })
            .to_dict(orient="records")
        )

        # echarts_series: categories rank-1-first so yAxis.inverse=true puts rank 1 at top
        return {
            "echarts_series": {
                "categories": [r["municipality"] for r in items],
                "values":     [r["gap_average"] for r in items],
            },
            "items": items,
        }

    # ------------------------------------------------------------------
    # Section: mapa_brechas — 4-department choropleth for Act 2
    # ------------------------------------------------------------------

    def _build_mapa_brechas(self, df: pd.DataFrame, top10_items: list[dict]) -> dict:
        """
        Department-level choropleth for the Pacific region (4 departments).

        Methodology for brecha_promedio_dept (consistent with Top 10 ranking):
          1. Same per-municipality brecha_promedio: median of 4 mean-gap columns.
          2. Department value = mean of per-municipality brecha_promedio values.
             This is the "former" option the user chose — avoids inflating departments
             with outlier municipalities dominating the simple column mean.

        Polygon geometry: dissolve pacifico_municipios.geojson by departamento,
        then simplify at 0.01° tolerance (~1 km) for a compact embedded payload.
        """
        import geopandas as gpd  # deferred — not needed by other methods

        gap_cols = [
            "brecha_vif_nna", "brecha_vif_adultas",
            "brecha_sexual_nna", "brecha_sexual_adultas",
        ]

        # Step 1 — per-municipality median gap (same computation as _build_top10_brechas)
        per_mun = (
            df.groupby("cod_municipio")
            .agg(
                departamento=("departamento",                  "first"),
                brecha_vif_nna=("brecha_vif_nna",             "mean"),
                brecha_vif_adultas=("brecha_vif_adultas",     "mean"),
                brecha_sexual_nna=("brecha_sexual_nna",       "mean"),
                brecha_sexual_adultas=("brecha_sexual_adultas","mean"),
            )
            .reset_index()
        )
        per_mun["brecha_promedio"] = per_mun[gap_cols].median(axis=1, skipna=True)

        # Step 2 — department aggregation: mean of per-municipality brecha_promedio
        dept_agg = (
            per_mun.groupby("departamento")
            .agg(
                brecha_promedio_dept=("brecha_promedio",       "mean"),
                brecha_vif_nna=("brecha_vif_nna",             "mean"),
                brecha_vif_adultas=("brecha_vif_adultas",     "mean"),
                brecha_sexual_nna=("brecha_sexual_nna",       "mean"),
                brecha_sexual_adultas=("brecha_sexual_adultas","mean"),
                n_municipios=("cod_municipio",                 "count"),
            )
            .reset_index()
        )

        # Step 3 — count how many Top-10 municipalities belong to each department
        # top10_items already have "department" key (renamed in _build_top10_brechas)
        top10_dept_counts: dict[str, int] = {}
        for item in top10_items:
            top10_dept_counts[item["department"]] = top10_dept_counts.get(item["department"], 0) + 1
        dept_agg["n_en_top10"]   = dept_agg["departamento"].map(lambda d: top10_dept_counts.get(d, 0))
        dept_agg["is_highlight"] = dept_agg["departamento"] == "CAUCA"

        dept_agg = dept_agg.sort_values("brecha_promedio_dept", ascending=False).reset_index(drop=True)
        for col in ["brecha_promedio_dept", "brecha_vif_nna", "brecha_vif_adultas",
                    "brecha_sexual_nna", "brecha_sexual_adultas"]:
            dept_agg[col] = dept_agg[col].round(2)

        brecha_min = round(float(dept_agg["brecha_promedio_dept"].min()), 2)
        brecha_max = round(float(dept_agg["brecha_promedio_dept"].max()), 2)

        # Step 4 — dissolve municipal polygons into 4 department features
        geojson_path = self._project_root / "config" / "pacifico_municipios.geojson"
        gdf = gpd.read_file(geojson_path)
        dept_gdf = (
            gdf[["departamento", "geometry"]]
            .dissolve(by="departamento")
            .reset_index()
        )
        dept_gdf["geometry"] = dept_gdf["geometry"].simplify(0.01, preserve_topology=True)
        dept_gdf = dept_gdf[["departamento", "geometry"]]
        geojson = json.loads(dept_gdf.to_json())
        for feat in geojson["features"]:
            feat["properties"] = {"department": feat["properties"]["departamento"]}

        departments = (
            dept_agg
            .rename(columns={
                "departamento":       "department",
                "brecha_promedio_dept": "gap_average",
                "brecha_vif_nna":     "gap_vif_nna",
                "brecha_vif_adultas": "gap_vif_adults",
                "brecha_sexual_nna":  "gap_sexual_nna",
                "brecha_sexual_adultas": "gap_sexual_adults",
                "n_municipios":       "n_municipalities",
                "n_en_top10":         "n_in_top10",
                "is_highlight":       "is_highlighted",
            })
            .to_dict(orient="records")
        )

        return {
            "highlighted_department": "CAUCA",
            "gap_range": {"min": brecha_min, "max": brecha_max},
            "departments": departments,
            "geojson": geojson,
        }

    # ------------------------------------------------------------------
    # Section: scatter_icv_brecha (Beat 5)
    # ------------------------------------------------------------------

    def _build_scatter_icv_brecha(self, df: pd.DataFrame) -> dict:
        """
        179 scatter points: x=ICV-GEN-F promedio, y=brecha_promedio (median of 4 gaps).
        Used for Beat 5 ICV-vs-Brecha cuadrant analysis.

        Spearman correlations from docs/analisis_brechas.json (pre-validated in notebook):
        ρ≈0.45–0.49 (p<0.001) for all 4 gap dimensions — moderate positive correlation.
        """
        gap_cols = [
            "brecha_vif_nna", "brecha_vif_adultas",
            "brecha_sexual_nna", "brecha_sexual_adultas",
        ]
        per_mun = (
            df.groupby("cod_municipio")
            .agg(
                municipio=("municipio",         "first"),
                departamento=("departamento",   "first"),
                icv_promedio=("icv_gen_f_score","mean"),
                brecha_vif_nna=("brecha_vif_nna",          "mean"),
                brecha_vif_adultas=("brecha_vif_adultas",  "mean"),
                brecha_sexual_nna=("brecha_sexual_nna",    "mean"),
                brecha_sexual_adultas=("brecha_sexual_adultas","mean"),
            )
            .reset_index()
        )
        per_mun["brecha_promedio"] = per_mun[gap_cols].median(axis=1, skipna=True)
        per_mun["icv_promedio"]    = per_mun["icv_promedio"].round(2)
        per_mun["brecha_promedio"] = per_mun["brecha_promedio"].round(2)

        # Drop the 2 Chocó municipalities excluded from the clustering universe (D7)
        per_mun = per_mun[~per_mun["cod_municipio"].isin(self._excluded_codes)].copy(deep=False)

        # Axis reference lines (medians) for the quadrant overlay
        icv_median    = round(float(per_mun["icv_promedio"].median()), 2)
        brecha_median = round(float(per_mun["brecha_promedio"].median(skipna=True)), 2)

        points = (
            per_mun[["cod_municipio", "municipio", "departamento", "icv_promedio", "brecha_promedio"]]
            .rename(columns={
                "municipio":      "municipality",
                "departamento":   "department",
                "icv_promedio":   "icv_average",
                "brecha_promedio": "gap_average",
            })
            .to_dict(orient="records")
        )

        viz_cfg = self.config["acto_2_visualization"]["sub_acto_2_5"]
        return {
            "n_points": len(points),
            "points": points,
            "reference_lines": {
                "x_median": icv_median,
                "y_median": brecha_median,
            },
            "axes":           viz_cfg["axes"],
            "axis_labels_es": viz_cfg["axis_labels_es"],
            "correlations": {
                "gap_vif_nna":     {"spearman_rho": 0.4513, "p_value": 0.0, "is_significant": True},
                "gap_vif_adults":  {"spearman_rho": 0.3895, "p_value": 0.0, "is_significant": True},
                "gap_sexual_nna":  {"spearman_rho": 0.4943, "p_value": 0.0, "is_significant": True},
                "gap_sexual_adults": {"spearman_rho": 0.481, "p_value": 0.0, "is_significant": True},
            },
        }

    # ------------------------------------------------------------------
    # Section: tendencias_temporales (Beat 4 — the diagnostic pivot)
    # ------------------------------------------------------------------

    def _build_tendencias_temporales(self, df: pd.DataFrame) -> dict:
        """
        Annual series for both gap metrics AND the raw F/M rates.

        The dual-series structure supports Beat 4's diagnostic argument:
        the brecha falls while male rates rise — it is a reporting artefact,
        not a genuine reduction in violence against women.

        Trend slopes (pendiente) are computed via numpy polyfit over the 8-year
        range.  R² is computed from residuals.  P-value is not available without
        scipy; significance is provided as pre-validated constants from the
        notebook (docs/analisis_brechas.json).
        """
        gap_cols  = ["brecha_vif_nna", "brecha_vif_adultas",
                     "brecha_sexual_nna", "brecha_sexual_adultas"]
        tasa_f_cols = ["tasa_vif_nna_f", "tasa_vif_adultas_f",
                       "tasa_sexual_nna_f", "tasa_sexual_adultas_f"]
        tasa_m_cols = ["tasa_vif_nna_m", "tasa_vif_adultos_m",
                       "tasa_sexual_nna_m", "tasa_sexual_adultos_m"]

        agg = (
            df.groupby("anio_hecho")
            .agg({**{c: "mean" for c in gap_cols + tasa_f_cols + tasa_m_cols}})
            .reset_index()
            .sort_values("anio_hecho")
        )

        # Annual data rows — rename all columns to schema keys before to_dict
        for col in gap_cols + tasa_f_cols + tasa_m_cols:
            agg[col] = agg[col].round(2)
        annual_data = (
            agg.rename(columns={
                "anio_hecho":           "year",
                "brecha_vif_nna":       "gap_vif_nna",
                "brecha_vif_adultas":   "gap_vif_adults",
                "brecha_sexual_nna":    "gap_sexual_nna",
                "brecha_sexual_adultas": "gap_sexual_adults",
                "tasa_vif_nna_f":       "rate_vif_nna_f",
                "tasa_vif_adultas_f":   "rate_vif_adults_f",
                "tasa_sexual_nna_f":    "rate_sexual_nna_f",
                "tasa_sexual_adultas_f": "rate_sexual_adults_f",
                "tasa_vif_nna_m":       "rate_vif_nna_m",
                "tasa_vif_adultos_m":   "rate_vif_adults_m",
                "tasa_sexual_nna_m":    "rate_sexual_nna_m",
                "tasa_sexual_adultos_m": "rate_sexual_adults_m",
            })
            .to_dict(orient="records")
        )

        # Trend computation via numpy polyfit (slope + R²)
        x = agg["anio_hecho"].to_numpy(dtype=float)

        def _trend(col: str) -> dict:
            y = agg[col].to_numpy(dtype=float)
            mask = ~np.isnan(y)
            if mask.sum() < 3:
                return {"pendiente": None, "r2": None, "tendencia": "Datos insuficientes"}
            coeffs  = np.polyfit(x[mask], y[mask], 1)
            y_pred  = np.polyval(coeffs, x[mask])
            ss_res  = float(np.sum((y[mask] - y_pred) ** 2))
            ss_tot  = float(np.sum((y[mask] - y[mask].mean()) ** 2))
            r2      = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 0.0
            slope   = round(float(coeffs[0]), 4)
            tendencia = "Aumentando" if slope > 0.005 else "Disminuyendo" if slope < -0.005 else "Estable"
            return {"pendiente": slope, "r2": r2, "tendencia": tendencia}

        tendencias_brecha  = {c: _trend(c) for c in gap_cols}
        tendencias_tasas_m = {c: _trend(c) for c in tasa_m_cols}

        # Pre-validated significance from notebook (scipy stats.linregress)
        _significativa = {
            "brecha_vif_nna": False, "brecha_vif_adultas": True,
            "brecha_sexual_nna": True, "brecha_sexual_adultas": False,
            "tasa_vif_nna_m": True, "tasa_vif_adultos_m": True,
            "tasa_sexual_nna_m": False, "tasa_sexual_adultos_m": False,
        }
        for col, meta in {**tendencias_brecha, **tendencias_tasas_m}.items():
            meta["significativa"] = _significativa.get(col, False)

        def _rename_trend(meta: dict) -> dict:
            return {
                "slope":        meta["pendiente"],
                "r2":           meta["r2"],
                "direction":    meta["tendencia"],
                "is_significant": meta["significativa"],
            }

        vif_adults_m_slope = float(_trend("tasa_vif_adultos_m")["pendiente"])

        return {
            "annual_data": annual_data,
            "gap_trends": {
                "gap_vif_nna":      _rename_trend(tendencias_brecha["brecha_vif_nna"]),
                "gap_vif_adults":   _rename_trend(tendencias_brecha["brecha_vif_adultas"]),
                "gap_sexual_nna":   _rename_trend(tendencias_brecha["brecha_sexual_nna"]),
                "gap_sexual_adults": _rename_trend(tendencias_brecha["brecha_sexual_adultas"]),
            },
            "male_rate_trends": {
                "rate_vif_nna_m":      _rename_trend(tendencias_tasas_m["tasa_vif_nna_m"]),
                "rate_vif_adults_m":   _rename_trend(tendencias_tasas_m["tasa_vif_adultos_m"]),
                "rate_sexual_nna_m":   _rename_trend(tendencias_tasas_m["tasa_sexual_nna_m"]),
                "rate_sexual_adults_m": _rename_trend(tendencias_tasas_m["tasa_sexual_adultos_m"]),
            },
            "artifact_diagnostic": {
                "conclusion": (
                    "La caída de brechas de VIF adulta es parcialmente artefacto: "
                    "las tasas masculinas aumentan significativamente "
                    "(+4.2 puntos/año, p=0.014), mientras las femeninas permanecen estables. "
                    "En violencia sexual, las tasas masculinas son estables — "
                    "la caída de brecha refleja leve descenso real en reportes femeninos."
                ),
                "vif_adults_m_slope":        vif_adults_m_slope,
                "vif_adults_m_is_significant": True,
            },
        }

    # ------------------------------------------------------------------
    # Section: beat4_diagnostico — sparkline + stacked area data
    # ------------------------------------------------------------------

    def _build_beat4_diagnostico(self, df: pd.DataFrame) -> dict:
        """
        Pre-structured data for the Beat 4 sparkline + stacked area chart.

        Rationale for two separate focal series:
          - sexual_adultas: the HEADLINE visual (gap 7.19→4.65, dramatic decline).
            Female rates fell; male rates stable.  The gap shrinks for a mixed reason.
          - vif_adultas: the ANALYTICAL PROOF of the artefact.  Female rates grow
            (+2.9/yr); male rates grow FASTER (+4.2/yr, p=0.014 significant).
            The gap closes not because violence against women decreases, but because
            men are being reported more frequently.

        Each focal series is structured as [{anio, brecha, tasa_f, tasa_m}] × 8 years
        — ready to feed ECharts directly:
            sparkline → [{value: brecha}] per anio
            stacked area → [{tasa_f}, {tasa_m}] per anio  (M rendered negative)

        P-values are pre-validated from docs/analisis_brechas.json (scipy linregress).
        """
        agg = (
            df.groupby("anio_hecho")
            .agg(
                brecha_vif_adultas=("brecha_vif_adultas",       "mean"),
                brecha_sexual_adultas=("brecha_sexual_adultas", "mean"),
                tasa_vif_adultas_f=("tasa_vif_adultas_f",       "mean"),
                tasa_vif_adultos_m=("tasa_vif_adultos_m",       "mean"),
                tasa_sexual_adultas_f=("tasa_sexual_adultas_f", "mean"),
                tasa_sexual_adultos_m=("tasa_sexual_adultos_m", "mean"),
            )
            .reset_index()
            .sort_values("anio_hecho")
        )

        def _rows(brecha_col: str, tf_col: str, tm_col: str) -> list[dict]:
            return [
                {
                    "year":   int(r["anio_hecho"]),
                    "gap":    round(float(r[brecha_col]), 2),
                    "rate_f": round(float(r[tf_col]),     2),
                    "rate_m": round(float(r[tm_col]),     2),
                }
                for _, r in agg.iterrows()
            ]

        # Trend slopes for UI annotations (slope from polyfit, p from docs)
        x = agg["anio_hecho"].to_numpy(dtype=float)

        def _slope(col: str) -> float:
            y = agg[col].to_numpy(dtype=float)
            return round(float(np.polyfit(x, y, 1)[0]), 4)

        return {
            "focal_gap_visual": "sexual_adults",
            "focal_artifact":   "vif_adults",
            "sexual_adults": {
                "series": _rows("brecha_sexual_adultas", "tasa_sexual_adultas_f", "tasa_sexual_adultos_m"),
                "gap_trend": {
                    "slope":         _slope("brecha_sexual_adultas"),
                    "p_value":       0.0982,
                    "is_significant": False,
                    "interpretation": "Descenso de brecha no significativo estadísticamente",
                },
                "female_rate_trend": {
                    "slope":          _slope("tasa_sexual_adultas_f"),
                    "interpretation": "Tasas femeninas descienden moderadamente",
                },
                "male_rate_trend": {
                    "slope":         _slope("tasa_sexual_adultos_m"),
                    "p_value":       None,
                    "is_significant": False,
                    "interpretation": "Tasas masculinas estables",
                },
            },
            "vif_adults": {
                "series": _rows("brecha_vif_adultas", "tasa_vif_adultas_f", "tasa_vif_adultos_m"),
                "gap_trend": {
                    "slope":         _slope("brecha_vif_adultas"),
                    "p_value":       0.0121,
                    "is_significant": True,
                    "interpretation": "Descenso de brecha significativo — pero es un artefacto",
                },
                "female_rate_trend": {
                    "slope":          _slope("tasa_vif_adultas_f"),
                    "interpretation": "Tasas femeninas crecen gradualmente",
                },
                "male_rate_trend": {
                    "slope":         _slope("tasa_vif_adultos_m"),
                    "p_value":       0.0140,
                    "is_significant": True,
                    "interpretation": "Tasas masculinas crecen significativamente (+4.2/año): artefacto de subregistro corregido",
                },
            },
            "narrative_conclusion": (
                "La brecha de violencia sexual adulta descendió de 7.2× a 4.7× entre 2018 y 2025. "
                "Podría leerse como avance. No lo es. En VIF adulta, la brecha cae porque los hombres "
                "se reportan más rápido: tasas masculinas +4.2 puntos/año (p=0.014), mientras las "
                "femeninas crecen sólo 2.9 puntos/año. La inequidad no disminuye — cambia cómo se mide."
            ),
        }

    # ==================================================================
    # Act 3 — Dos violencias, y la mitad ocurre en la infancia
    # ==================================================================

    def _build_capa3a_scatter(self, clustering: pd.DataFrame) -> dict:
        """
        177 scatter points for the Capa 3a quadrant scatter (Beat 2 geography).

        Axes: composite female rates per 100k (VIF NNA+Adultas on X; Sexual NNA+Adultas on Y).
        Quadrant assignment: median-based on the 177-municipality distribution.
        Archetypes: 3 municipalities (one per labeled quadrant; bajo_perfil is unlabeled).
        All non-archetype points rendered at low opacity by the frontend (fixed size).
        """
        cl = clustering.copy(deep=False)
        cl["vif_f_total_rate"]    = (cl["tasa_vif_nna_f"] + cl["tasa_vif_adultas_f"]).round(2)
        cl["sexual_f_total_rate"] = (cl["tasa_sexual_nna_f"] + cl["tasa_sexual_adultas_f"]).round(2)

        med_vif    = float(cl["vif_f_total_rate"].median())
        med_sexual = float(cl["sexual_f_total_rate"].median())

        def _quadrant(row) -> str:
            hi_v = row["vif_f_total_rate"] > med_vif
            hi_s = row["sexual_f_total_rate"] > med_sexual
            if hi_v and hi_s:     return "coexistencia_alta"
            if hi_v and not hi_s: return "predomina_vif"
            if not hi_v and hi_s: return "predomina_sexual"
            return "bajo_perfil"

        cl["quadrant"]     = cl.apply(_quadrant, axis=1)
        archetype_codes    = frozenset(self.config["business_rules"]["archetype_codes"].keys())
        cl["is_archetype"] = cl["cod_municipio"].isin(archetype_codes)

        # Descending-rank for each axis (rank 1 = highest rate)
        cl["rank_vif"]    = cl["vif_f_total_rate"].rank(method="min", ascending=False).astype(int)
        cl["rank_sexual"] = cl["sexual_f_total_rate"].rank(method="min", ascending=False).astype(int)

        quadrant_counts = cl["quadrant"].value_counts().to_dict()

        cols = [
            "cod_municipio", "municipio", "departamento",
            "vif_f_total_rate", "sexual_f_total_rate",
            "quadrant", "is_archetype", "rank_vif", "rank_sexual",
            "cluster_id", "cluster_name",
        ]
        points = (
            cl[cols]
            .sort_values("vif_f_total_rate", ascending=False)
            .reset_index(drop=True)
            .rename(columns={"municipio": "municipality", "departamento": "department"})
        )

        return {
            "n_points":           len(points),
            "aggregation_method": "per_municipality_averages_tabla_clustering_final",
            "axes": {
                "x": "vif_f_total_rate = tasa_vif_nna_f + tasa_vif_adultas_f (por 100k femenino)",
                "y": "sexual_f_total_rate = tasa_sexual_nna_f + tasa_sexual_adultas_f (por 100k femenino)",
            },
            "reference_lines": {
                "x_median": round(med_vif, 2),
                "y_median": round(med_sexual, 2),
            },
            "quadrants": {
                "coexistencia_alta": {
                    "label":   "Coexistencia alta",
                    "n":       quadrant_counts.get("coexistencia_alta", 0),
                    "tooltip": "Alta VIF y alta violencia sexual. Municipio con doble carga de violencia de género.",
                },
                "predomina_vif": {
                    "label":   "Predomina VIF",
                    "n":       quadrant_counts.get("predomina_vif", 0),
                    "tooltip": "Alta violencia intrafamiliar, baja violencia sexual. El hogar es el escenario predominante.",
                },
                "predomina_sexual": {
                    "label":   "Predomina Sexual",
                    "n":       quadrant_counts.get("predomina_sexual", 0),
                    "tooltip": "Alta violencia sexual, baja VIF. El espacio comunitario concentra el riesgo.",
                },
                "bajo_perfil": {
                    "label":      "Bajo perfil declarado",
                    "n":          quadrant_counts.get("bajo_perfil", 0),
                    "tooltip":    "Baja VIF y baja violencia sexual en registros. Puede reflejar subregistro estructural, no ausencia real de violencia.",
                    "disclaimer": "Baja VIF y baja violencia sexual en registros puede reflejar subregistro estructural, no ausencia real de violencia.",
                },
            },
            "archetypes": points[points["is_archetype"]].to_dict(orient="records"),
            "points":     points.to_dict(orient="records"),
            "quadrant_colors": self.config["acto_3_visualization"]["sub_acto_3_2"]["quadrant_colors"],
            "scatter_style":   self.config["acto_3_visualization"]["sub_acto_3_2"]["scatter_style"],
            "axis_labels_es":  self.config["acto_3_visualization"]["sub_acto_3_2"]["axis_labels_es"],
        }

    def _build_capa3a_dumbbell(self, master: pd.DataFrame) -> dict:
        """
        Regional sum/sum rates for the dumbbell chart (Capa 3a, 40% width).

        Methodology: sum(casos) / sum(population) × 100000 across all 179
        municipalities × 8 years — identical to Act 2 kpi_regional.
        NOT a mean of per-municipality rates (those are biased by small-population outliers).

        Denominators: pob_f_0_17 for NNA rates; pob_f_18_mas for adult rates.
        """
        s = master.agg({
            "casos_vif_nna_f":       "sum",
            "casos_vif_adultas_f":   "sum",
            "casos_sexual_nna_f":    "sum",
            "casos_sexual_adultas_f": "sum",
            "pob_f_0_17":            "sum",
            "pob_f_18_mas":          "sum",
        })

        pob_nna = float(s["pob_f_0_17"])
        pob_adu = float(s["pob_f_18_mas"])

        def _rate(casos: float, pob: float) -> float:
            return round(casos / pob * 100_000, 2) if pob > 0 else None

        return {
            "aggregation_method": "sum_sum_regional",
            "note": (
                "Tasas regionales = sum(casos) / sum(población) × 100000, "
                "179 municipios × 8 años. No es la media de tasas municipales."
            ),
            "denominators": {
                "pop_f_0_17_sum":    int(pob_nna),
                "pop_f_18_plus_sum": int(pob_adu),
            },
            "lines": [
                {
                    "id":    "vif",
                    "label": "Violencia intrafamiliar",
                    "color": "#4575b4",
                    "endpoints": [
                        {
                            "group":         "nna",
                            "label_display": "NNA (0–17)",
                            "cases":         int(s["casos_vif_nna_f"]),
                            "rate":          _rate(s["casos_vif_nna_f"], pob_nna),
                        },
                        {
                            "group":         "adultas",
                            "label_display": "Adultas (18+)",
                            "cases":         int(s["casos_vif_adultas_f"]),
                            "rate":          _rate(s["casos_vif_adultas_f"], pob_adu),
                        },
                    ],
                },
                {
                    "id":    "sexual",
                    "label": "Violencia sexual",
                    "color": "#d73027",
                    "endpoints": [
                        {
                            "group":         "nna",
                            "label_display": "NNA (0–17)",
                            "cases":         int(s["casos_sexual_nna_f"]),
                            "rate":          _rate(s["casos_sexual_nna_f"], pob_nna),
                        },
                        {
                            "group":         "adultas",
                            "label_display": "Adultas (18+)",
                            "cases":         int(s["casos_sexual_adultas_f"]),
                            "rate":          _rate(s["casos_sexual_adultas_f"], pob_adu),
                        },
                    ],
                },
            ],
        }

    def _build_tipologia_delito(self, sexuales: pd.DataFrame) -> dict:
        """
        Weighted percentages of dimension_delito by cantidad column.

        Q10 rule: pct = sum(cantidad per category) / sum(total cantidad) × 100
        Q11 rule: OTROS is excluded if its pct rounds to exactly 0.00%.
        Q12 double-cut: global percentages + per-department breakdown.
        """
        # Global aggregation
        global_agg = (
            sexuales.groupby("dimension_delito")["cantidad"]
            .sum()
            .reset_index()
        )
        total_all = int(global_agg["cantidad"].sum())
        global_agg["pct"] = (global_agg["cantidad"] / total_all * 100).round(2)

        # Exclude OTROS if pct rounds to exactly 0.00
        otros_exclude = (global_agg["dimension_delito"] == "OTROS") & (global_agg["pct"] == 0.00)
        global_agg = global_agg[~otros_exclude].copy(deep=False)

        total_used = int(global_agg["cantidad"].sum())
        global_agg["pct"] = (global_agg["cantidad"] / total_used * 100).round(2)
        minor_cats = frozenset(self.config["minor_categories"])
        display_labels = self.config["display_labels"]
        global_agg["is_minor"] = global_agg["dimension_delito"].isin(minor_cats)
        global_agg["label"] = (
            global_agg["dimension_delito"].map(display_labels).fillna(global_agg["dimension_delito"])
        )
        global_agg = global_agg.sort_values("pct", ascending=False).reset_index(drop=True)

        menor_14_rows = global_agg.loc[global_agg["dimension_delito"] == "ABUSO_SEXUAL_MENOR_14", "pct"]
        pct_menor_14  = round(float(menor_14_rows.iloc[0]) if len(menor_14_rows) else 0.0, 2)
        pct_all_minors = round(float(global_agg.loc[global_agg["is_minor"], "pct"].sum()), 2)

        # Per-department breakdown
        dept_agg = (
            sexuales.groupby(["departamento", "dimension_delito"])["cantidad"]
            .sum()
            .reset_index()
        )
        dept_totals = dept_agg.groupby("departamento")["cantidad"].transform("sum")
        dept_agg["pct"] = (dept_agg["cantidad"] / dept_totals * 100).round(2)

        otros_dept = (dept_agg["dimension_delito"] == "OTROS") & (dept_agg["pct"] == 0.00)
        dept_agg = dept_agg[~otros_dept].copy(deep=False)
        dept_agg["is_minor"] = dept_agg["dimension_delito"].isin(minor_cats)
        dept_agg["label"] = (
            dept_agg["dimension_delito"].map(display_labels).fillna(dept_agg["dimension_delito"])
        )
        dept_agg = (
            dept_agg
            .sort_values(["departamento", "pct"], ascending=[True, False])
            .reset_index(drop=True)
        )

        by_department = {
            dept: (
                group[["dimension_delito", "label", "cantidad", "pct", "is_minor"]]
                .rename(columns={"dimension_delito": "crime_dimension", "cantidad": "count"})
                .to_dict(orient="records")
            )
            for dept, group in dept_agg.groupby("departamento")
        }

        return {
            "total_cases":    total_used,
            "pct_under_14":   pct_menor_14,
            "pct_all_minors": pct_all_minors,
            "global": (
                global_agg[["dimension_delito", "label", "cantidad", "pct", "is_minor"]]
                .rename(columns={"dimension_delito": "crime_dimension", "cantidad": "count"})
                .to_dict(orient="records")
            ),
            "by_department": by_department,
        }

    def _build_timeline_sexual_nna(self, master: pd.DataFrame) -> dict:
        """
        Average tasa_sexual_nna_f per department × year (2018–2025).
        One ECharts line series per department.
        """
        agg = (
            master.groupby(["departamento", "anio_hecho"])["tasa_sexual_nna_f"]
            .mean()
            .round(2)
            .reset_index()
        )

        years: list[int] = sorted(agg["anio_hecho"].unique().tolist())
        depts: list[str] = sorted(agg["departamento"].unique().tolist())

        series = []
        for dept in depts:
            dept_df = agg[agg["departamento"] == dept].set_index("anio_hecho")["tasa_sexual_nna_f"]
            data = [
                None if pd.isna(dept_df.get(yr)) else round(float(dept_df.get(yr)), 2)
                for yr in years
            ]
            series.append({"department": dept, "data": data})

        return {
            "chart_type": "line",
            "metric": "tasa_sexual_nna_f",
            "metric_label": "Tasa violencia sexual NNA femenino (por 100k)",
            "x_axis": [int(y) for y in years],
            "series": series,
        }

    # ------------------------------------------------------------------
    # Top-level orchestrator
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Run all export acts in sequence: 1, 2, 3, then 5."""
        self.export_acto_1()
        self.export_acto_2()
        self.export_acto_3()
        try:
            self.export_acto_5_municipios()
            print("[MasterExporter] acto_5_municipios.json written")
        except Exception as exc:
            print(f"[MasterExporter] acto_5_municipios FAILED: {exc}")
            raise

    # ==================================================================
    # Act 5 — Ficha municipal
    # ==================================================================

    def _build_acto_5_municipios(self) -> dict:
        """Return the full sanitized Acto 5 payload for all 179 municipalities."""
        act5_cfg    = self.config["acto_5_municipios"]
        stat_cfgs   = act5_cfg["stat_cards"]
        cluster_norm = act5_cfg["cluster_label_normalization"]
        dvt_labels  = act5_cfg["dominant_violence_type_labels_es"]
        feat_labels = act5_cfg["coefficient_features_labels_es"]
        spark_axis  = act5_cfg["sparkline_axis_labels_es"]

        master      = self._load_master_act5()
        clustering  = self._load_clustering_act5()

        # Vectorized computations on the 177 clustered municipalities
        cl = clustering.copy()
        vif_arr = (
            cl["tasa_vif_nna_f"].to_numpy(dtype=float, na_value=0.0)
            + cl["tasa_vif_adultas_f"].to_numpy(dtype=float, na_value=0.0)
        )
        sex_arr = (
            cl["tasa_sexual_nna_f"].to_numpy(dtype=float, na_value=0.0)
            + cl["tasa_sexual_adultas_f"].to_numpy(dtype=float, na_value=0.0)
        )
        max_arr      = np.maximum(vif_arr, sex_arr)
        max_safe     = np.where(max_arr == 0, np.nan, max_arr)
        ratio_diff   = np.abs(vif_arr - sex_arr) / max_safe
        dom_type_arr = np.where(
            np.isnan(ratio_diff) | (ratio_diff <= 0.05), "ambas",
            np.where(vif_arr > sex_arr, "vif", "sexual"),
        )
        dom_rate_arr = np.where(
            dom_type_arr == "ambas", max_arr,
            np.where(dom_type_arr == "vif", vif_arr, sex_arr),
        ).round(2)
        cl["dominant_type"] = dom_type_arr
        cl["dominant_rate"] = dom_rate_arr
        cl["icv_ranking"]   = (
            cl["icv_gen_f_score"]
            .astype("float64")
            .rank(method="min", ascending=False)
            .astype(int)
        )
        cl_idx = cl.set_index("cod_municipio")

        # Load coefficient contributions produced by ModelExporter
        contribs_path = self._dashboard_dir / "contribuciones_municipales.json"
        with open(contribs_path, encoding="utf-8") as fh:
            contribs_lookup: dict = json.load(fh)["municipios"]

        # Sparklines — one per municipality from master_table (all 179)
        sparklines: dict = {}
        for cod, grp in master.groupby("cod_municipio"):
            grp_s  = grp.sort_values("anio_hecho")
            values = [
                0.0 if pd.isna(v) else round(float(v), 2)
                for v in grp_s["icv_gen_f_score"].tolist()
            ]
            sparklines[cod] = {
                "years":          [int(y) for y in grp_s["anio_hecho"].tolist()],
                "values":         values,
                "axis_labels_es": spark_axis,
            }

        # Municipality name/dept lookup from master_table
        mun_info = (
            master.groupby("cod_municipio", as_index=True)
            .agg(nombre_es=("municipio", "first"), departamento_es=("departamento", "first"))
        )

        # departamentos_disponibles (4 Pacific departments)
        dept_map: dict = act5_cfg["departamentos_pacifico"]
        dept_mun: dict = {}
        for cod in mun_info.index:
            dept_mun.setdefault(cod[:2], []).append(cod)
        departamentos_disponibles = [
            {
                "codigo_dane_dept": code,
                "nombre_es":        nombre,
                "municipios_codigos": sorted(dept_mun.get(code, [])),
            }
            for code, nombre in dept_map.items()
        ]

        # Per-municipality records
        municipios: dict = {}
        for cod in sorted(mun_info.index):
            is_excluded = cod in self._excluded_codes
            nombre_es   = str(mun_info.at[cod, "nombre_es"])
            dept_es     = str(mun_info.at[cod, "departamento_es"])
            codigo_dane_dept = cod[:2]

            if cod in cl_idx.index:
                cl_row       = cl_idx.loc[cod]
                icv_score    = round(float(cl_row["icv_gen_f_score"]), 2)
                cluster_id   = int(cl_row["cluster_id"])
                raw_cname    = str(cl_row["cluster_name"])
                norm         = cluster_norm.get(raw_cname, {})
                cluster_label_es    = norm.get("label_es")
                cluster_emoji       = norm.get("emoji")
                cluster_color_token = norm.get("color_token")
                icv_ranking  = int(cl_row["icv_ranking"])
                dom_type_es  = dvt_labels.get(str(cl_row["dominant_type"]))
                dom_rate     = float(cl_row["dominant_rate"])

                tasa_vals = {
                    "icv_gen_f_score":    icv_score,
                    "cluster_label_es":   cluster_label_es,
                    "tasa_vif_nna_f":     round(float(cl_row["tasa_vif_nna_f"]), 2),
                    "tasa_sexual_nna_f":  round(float(cl_row["tasa_sexual_nna_f"]), 2),
                    "tasa_vif_adultas_f": round(float(cl_row["tasa_vif_adultas_f"]), 2),
                    "tasa_sexual_adultas_f": round(float(cl_row["tasa_sexual_adultas_f"]), 2),
                }
                raw_contribs = contribs_lookup.get(cod, {}).get("contributions")
                coeff_contribs = None if raw_contribs is None else [
                    {
                        "feature_id":       c["feature_id"],
                        "feature_label_es": feat_labels.get(c["feature_id"], c["feature_id"]),
                        "coefficient":      c["coefficient"],
                        "standardized_value": c["standardized_value"],
                        "contribution":     c["contribution"],
                    }
                    for c in raw_contribs
                ]
            else:
                # Excluded municipality
                icv_score    = None
                cluster_id   = None
                cluster_label_es = cluster_emoji = cluster_color_token = None
                icv_ranking  = None
                dom_type_es  = None
                dom_rate     = None
                tasa_vals    = {
                    "icv_gen_f_score":       None,
                    "cluster_label_es":      None,
                    "tasa_vif_nna_f":        None,
                    "tasa_sexual_nna_f":     None,
                    "tasa_vif_adultas_f":    None,
                    "tasa_sexual_adultas_f": None,
                }
                coeff_contribs = None

            stat_cards = [
                {
                    "id":             c["id"],
                    "label_es":       c["label_es"],
                    "value":          tasa_vals.get(c["source_field"]),
                    "display_format": c["display_format"],
                    "badge":          None,
                    "sub_value":      None,
                }
                for c in stat_cfgs
            ]

            narrative_values_es = {
                "municipio_placeholder": nombre_es,
                "cluster_placeholder":   cluster_label_es or act5_cfg["excluido_del_modelo_banner_es"][:30],
                "icv_placeholder":       str(round(icv_score, 2)) if icv_score is not None else "N/D",
                "ranking_placeholder":   str(icv_ranking) if icv_ranking is not None else "N/D",
                "tipo_placeholder":      dom_type_es or "N/D",
                "tasa_placeholder":      str(round(dom_rate, 2)) if dom_rate is not None else "N/D",
            }

            municipios[cod] = {
                "cod_municipio":           cod,
                "nombre_es":               nombre_es,
                "departamento_es":         dept_es,
                "codigo_dane_dept":        codigo_dane_dept,
                "excluido_del_modelo":     is_excluded,
                "stat_cards":              stat_cards,
                "sparkline_icv":           sparklines.get(cod, {"years": [], "values": [], "axis_labels_es": spark_axis}),
                "cluster_id":              cluster_id,
                "cluster_label_es":        cluster_label_es,
                "cluster_emoji":           cluster_emoji,
                "cluster_color_token":     cluster_color_token,
                "icv_ranking":             icv_ranking,
                "dominant_violence_type_es": dom_type_es,
                "dominant_violence_rate":  dom_rate,
                "coefficient_contributions": coeff_contribs,
                "narrative_values_es":     narrative_values_es,
            }

        payload = {
            "metadata": {
                "generated_at":                    datetime.now(timezone.utc).isoformat(),
                "source_tables":                   [
                    self.config["paths"]["master_table"],
                    self.config["paths"]["tabla_clustering"],
                    "data/dashboard/contribuciones_municipales.json",
                ],
                "total_municipios":                len(municipios),
                "municipios_excluidos_del_modelo": sorted(self._excluded_codes),
                "narrative_template_es":           act5_cfg["narrative_template_es"],
                "narrative_template_cierre_es":    act5_cfg["narrative_template_cierre_es"],
            },
            "departamentos_disponibles": departamentos_disponibles,
            "municipios":                municipios,
        }
        return _sanitize(payload)

    def export_acto_5_municipios(self) -> Path:
        """Validate _build_acto_5_municipios() against schema and write to data/dashboard/."""
        payload     = self._build_acto_5_municipios()
        schema_path = self._project_root / "schemas" / "acto_5_municipios.schema.json"
        fname       = self.config["acto_5_municipios"]["output_filename"]
        output_path = self._dashboard_dir / fname
        write_json_validated(payload=payload, schema_path=schema_path, output_path=output_path)
        size_kb = output_path.stat().st_size / 1024
        print(f"✓  {fname}  →  {output_path}  ({size_kb:.1f} KB)")
        return output_path

    # ------------------------------------------------------------------
    # Writer
    # ------------------------------------------------------------------

    def _write_json(self, payload: dict, filename: str) -> Path:
        self._dashboard_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._dashboard_dir / filename
        # _sanitize() converts all numpy/pandas types and NaN/Inf to JSON-native
        # Python types before the stdlib encoder sees them — avoids the NaN literal.
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(_sanitize(payload), fh, ensure_ascii=False, indent=None)
        size_kb = out_path.stat().st_size / 1024
        print(f"✓  {filename}  →  {out_path}  ({size_kb:.1f} KB)")
        return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="MasterExporter — Cicatrices Invisibles")
    ap.add_argument("--config", default="config/master_exporter_config.json",
                    help="Path to master_exporter_config.json")
    ap.add_argument("--act", type=int, choices=[1, 2, 3],
                    help="Run only this act (default: all)")
    # keep positional for backward compat: python -m src.exporters.master_exporter base_config.json
    ap.add_argument("config_pos", nargs="?", help=argparse.SUPPRESS)
    args = ap.parse_args()

    config_path = args.config_pos or args.config
    exporter = MasterExporter(config_path=config_path)

    if args.act in (None, 1):
        exporter.export_acto_1()
    if args.act in (None, 2):
        exporter.export_acto_2()
    if args.act in (None, 3):
        exporter.export_acto_3()
