import json
import logging
from pathlib import Path
from typing import Dict, Literal

import pandas as pd

logger = logging.getLogger(__name__)

DatasetKey = Literal["ds3", "ds4"]


class ForenseAnalyzer:
    """
    Genera 12 tablas de caracterización forense para el dashboard 

    Lee DS3 (seforense_limpio.parquet) y DS4 (forense_limpio.parquet) desde
    data/cleaned/. Carril paralelo — nunca alimenta la tabla maestra ni el
    modelo ICV. Configuración 100% JSON-driven desde
    config/forense_analyzer_config.json.
    """

    def __init__(self, config_path: str) -> None:
        cfg = Path(config_path).resolve()
        if not cfg.exists():
            raise FileNotFoundError(f"Config not found: {cfg}")

        with open(cfg, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.project_root = cfg.parent.parent

        paths = self.config["paths"]
        self.cleaned_dir = (self.project_root / paths["cleaned_dir"]).resolve()
        self.ds4_output_dir = (self.project_root / paths["ds4_output_dir"]).resolve()
        self.ds3_output_dir = (self.project_root / paths["ds3_output_dir"]).resolve()

        self.ds4_config = self.config["ds4_config"]
        self.ds3_config = self.config["ds3_config"]
        self.null_label: str = self.config.get("output_config", {}).get("null_label", "SIN_DATO")

        logger.info(f"ForenseAnalyzer initialized | config: {config_path}")

    def _load_and_validate(self, dataset_key: DatasetKey) -> pd.DataFrame:
        """
        Carga y valida un dataset limpio desde data/cleaned/.

        Raises FileNotFoundError si el archivo fuente no existe.
        Raises KeyError si faltan columnas declaradas en columns_available.
        Row-count mismatch emite WARNING pero no detiene la ejecución.
        """
        source_filename = self.config["source_files"][dataset_key]
        path = self.cleaned_dir / source_filename

        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")

        df = pd.read_parquet(path)

        expected_count: int = self.config["expected_counts"][dataset_key]
        actual_count = len(df)
        if actual_count != expected_count:
            logger.warning(
                f"{dataset_key.upper()} row count: {actual_count}"
                f" (expected {expected_count})"
                f" — verify upstream pipeline if mismatch is significant"
            )

        dataset_cfg_key = f"{dataset_key}_config"
        expected_cols = set(self.config[dataset_cfg_key]["columns_available"])
        actual_cols = set(df.columns)
        missing = expected_cols - actual_cols
        if missing:
            raise KeyError(f"Missing columns in {dataset_key}: {sorted(missing)}")

        logger.info(f"Loaded {dataset_key}: {len(df)} rows × {len(df.columns)} columns")
        return df

    def _build_table(self, df: pd.DataFrame, table_name: str, table_config: dict) -> pd.DataFrame:
        """Generic aggregation engine — 100% JSON-driven, no hardcoded table logic."""
        null_label = self.null_label
        pre_filter: dict = table_config.get("pre_filter", {})
        if pre_filter:
            mask = pd.Series(True, index=df.index)
            for col, val in pre_filter.items():
                mask = mask & (df[col] == val)
            df = df.loc[mask].copy(deep=False)

        groupby_keys: list = table_config["groupby"]
        agg_specs: dict = table_config["aggregations"]
        attribute_columns: dict = table_config.get("attribute_columns", {})

        result: pd.DataFrame = None  # type: ignore[assignment]
        pct_of_group_deferred: dict = {}

        for agg_name, spec in agg_specs.items():
            method: str = spec["method"]

            if method == "pct_of_group":
                pct_of_group_deferred[agg_name] = spec
                continue

            grouped = df.groupby(groupby_keys, observed=True)

            if method == "size":
                part = grouped.size().reset_index(name=agg_name)

            elif method in ("min", "max"):
                col = spec["column"]
                part = getattr(grouped[col], method)().reset_index(name=agg_name)

            elif method == "value_counts_pct":
                col = spec["column"]
                value = spec["value"]
                indicator = (df[col] == value).astype("float64")
                part = (
                    df.assign(_ind=indicator)
                    .groupby(groupby_keys, observed=True)["_ind"]
                    .mean()
                    .mul(100)
                    .reset_index(name=agg_name)
                )

            elif method == "mode":
                col = spec["column"]
                part = (
                    grouped[col]
                    .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else null_label)
                    .reset_index(name=agg_name)
                )

            elif method == "conditional_pct":
                conditions: dict = spec["conditions"]
                mask = pd.Series(True, index=df.index)
                for cond_col, cond_val in conditions.items():
                    mask = mask & (df[cond_col] == cond_val)
                part = (
                    df.assign(_cond=mask.astype("float64"))
                    .groupby(groupby_keys, observed=True)["_cond"]
                    .mean()
                    .mul(100)
                    .reset_index(name=agg_name)
                )

            elif method == "filtered_mode":
                col = spec["column"]
                filters: dict = spec["filters"]
                fmask = pd.Series(True, index=df.index)
                for fcol, fval in filters.items():
                    fmask = fmask & (df[fcol] == fval)
                filtered_df = df[fmask]
                part = (
                    filtered_df.groupby(groupby_keys, observed=True)[col]
                    .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else null_label)
                    .reset_index(name=agg_name)
                )

            else:
                raise ValueError(f"Unknown method '{method}' in table '{table_name}'")

            result = part if result is None else result.merge(part, on=groupby_keys, how="left")
            if method == "filtered_mode":
                result[agg_name] = result[agg_name].fillna(null_label)

        # pct_of_group is deferred: it depends on the size column already being in result
        for agg_name, spec in pct_of_group_deferred.items():
            group_level: str = spec["group_level"]
            size_col = next(name for name, s in agg_specs.items() if s["method"] == "size")
            group_totals = result.groupby(group_level, observed=True)[size_col].transform("sum")
            result[agg_name] = (result[size_col] / group_totals) * 100

        # attribute_columns: lookup first value of attr_col per join_col value (1:1 functional dependency)
        for attr_col, join_col in attribute_columns.items():
            lookup = (
                df.groupby(join_col, observed=True)[attr_col]
                .first()
                .rename(attr_col)
            )
            result = result.merge(lookup, on=join_col, how="left")

        return result

    def analyze(self, dataset_key: DatasetKey) -> Dict[str, pd.DataFrame]:
        """
        Genera todas las tablas de caracterización para un dataset.

        Carga el dataset, aplica _build_table para cada tabla declarada en el
        config, persiste cada resultado en parquet, y retorna el dict completo.
        """
        df = self._load_and_validate(dataset_key)

        dataset_cfg = self.ds4_config if dataset_key == "ds4" else self.ds3_config
        output_dir_key = "ds4_output_dir" if dataset_key == "ds4" else "ds3_output_dir"
        output_dir = (self.project_root / self.config["paths"][output_dir_key]).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        out_cfg = self.config["output_config"]
        tables_out: Dict[str, pd.DataFrame] = {}

        for table_name, table_config in dataset_cfg["tables"].items():
            table_df = self._build_table(df, table_name, table_config)

            output_path = output_dir / table_config["output_filename"]
            table_df.to_parquet(output_path, compression=out_cfg["compression"], index=out_cfg["index"])
            logger.info(f"Saved {table_name}: {len(table_df)} rows → {output_path}")

            tables_out[table_name] = table_df

        total_rows = sum(len(t) for t in tables_out.values())
        logger.info(
            f"ForenseAnalyzer complete for {dataset_key}: "
            f"{len(tables_out)} tables generated, {total_rows} total rows"
        )
        return tables_out

    def analyze_all(self) -> Dict[str, pd.DataFrame]:
        """Top-level entry point: genera las 12 tablas de DS4 y DS3."""
        return {**self.analyze("ds4"), **self.analyze("ds3")}
