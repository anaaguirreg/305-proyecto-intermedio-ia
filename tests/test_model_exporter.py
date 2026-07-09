"""Tests for ModelExporter — 7 canonical asserts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.exporters.model_exporter import ModelExporter

CONFIG_PATH = PROJECT_ROOT / "config" / "master_exporter_config.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "dashboard"
EXCLUDED_CODES = {"27150", "27493"}


@pytest.fixture(scope="module")
def built_exporter() -> ModelExporter:
    exp = ModelExporter(CONFIG_PATH, OUTPUT_DIR)
    exp.build()
    return exp


# ---------------------------------------------------------------------------
# 1. Model shape
# ---------------------------------------------------------------------------

def test_load_model_shape() -> None:
    exp = ModelExporter(CONFIG_PATH, OUTPUT_DIR)
    model = exp._load_model()
    assert model.coef_.shape == (1, 4)
    assert list(model.classes_) == [0, 1]


# ---------------------------------------------------------------------------
# 2. Scaler input row count
# ---------------------------------------------------------------------------

def test_scaler_reconstruction_uses_179_rows() -> None:
    import pandas as pd

    df = pd.read_parquet(PROJECT_ROOT / "data" / "master" / "tabla_clustering.parquet")
    assert len(df) == 179


# ---------------------------------------------------------------------------
# 3. Scaler output dimensions
# ---------------------------------------------------------------------------

def test_scaler_center_and_scale_are_length_4() -> None:
    exp = ModelExporter(CONFIG_PATH, OUTPUT_DIR)
    model = exp._load_model()
    features = list(model.feature_names_in_)
    scaler = exp._reconstruct_scaler(features)
    assert len(scaler.center_) == 4
    assert len(scaler.scale_) == 4
    assert scaler.center_.dtype.kind == "f"
    assert scaler.scale_.dtype.kind == "f"


# ---------------------------------------------------------------------------
# 4. Contribution math
# ---------------------------------------------------------------------------

def test_contributions_math() -> None:
    exp = ModelExporter(CONFIG_PATH, OUTPUT_DIR)
    model = exp._load_model()
    features = list(model.feature_names_in_)
    scaler = exp._reconstruct_scaler(features)
    clustering_final = exp._load_clustering_final()
    contributions_df = exp._compute_contributions(model, scaler, clustering_final)

    first_cod = clustering_final.index[0]
    raw_vals = clustering_final.loc[first_cod, features].values.astype(float)
    log_vals = np.log1p(raw_vals)
    standardized_expected = (log_vals - scaler.center_) / scaler.scale_
    contributions_expected = model.coef_[0] * standardized_expected

    for j, feat in enumerate(features):
        mask = (contributions_df["cod_municipio"] == str(first_cod)) & (
            contributions_df["feature_id"] == feat
        )
        actual_row = contributions_df[mask]
        assert len(actual_row) == 1, f"Expected 1 row for {feat}, got {len(actual_row)}"
        assert abs(actual_row["contribution"].iloc[0] - contributions_expected[j]) < 1e-6
        assert (
            abs(actual_row["standardized_value"].iloc[0] - standardized_expected[j]) < 1e-6
        )


# ---------------------------------------------------------------------------
# 5. modelo_clasificador.json structure
# ---------------------------------------------------------------------------

def test_modelo_clasificador_json_structure(built_exporter: ModelExporter) -> None:
    out_file = OUTPUT_DIR / "modelo_clasificador.json"
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "generated_at" in data
    assert data["model_type"] == "LogisticRegression"
    assert "features" in data and len(data["features"]) == 4
    assert isinstance(data["coefficients"], list) and len(data["coefficients"]) == 4
    assert data["decision_threshold"] == 0.5
    assert abs(data["validation_metrics"]["cv_f1_macro"] - 0.9769) < 1e-4
    assert data["preprocessing"]["log1p"] is True
    assert len(data["preprocessing"]["robust_scaler"]["center"]) == 4
    assert len(data["preprocessing"]["robust_scaler"]["scale"]) == 4
    for label in data["classes"].values():
        assert "\U0001f534" not in label  # 🔴
        assert "\U0001f7e0" not in label  # 🟠


# ---------------------------------------------------------------------------
# 6. contribuciones_municipales.json — 177 keys, no excluded codes
# ---------------------------------------------------------------------------

def test_contribuciones_municipales_json_has_177_keys(
    built_exporter: ModelExporter,
) -> None:
    out_file = OUTPUT_DIR / "contribuciones_municipales.json"
    assert out_file.exists()

    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    municipios = data["municipios"]
    assert len(municipios) == 177
    for code in EXCLUDED_CODES:
        assert code not in municipios, f"Excluded code {code} found in output"


# ---------------------------------------------------------------------------
# 7. Cluster label normalization strips emojis
# ---------------------------------------------------------------------------

def test_cluster_label_normalization_strips_emojis() -> None:
    exp = ModelExporter(CONFIG_PATH, OUTPUT_DIR)

    result_alta = exp._normalize_cluster_label("\U0001f534 Alta severidad")
    assert result_alta["label_es"] == "Alta severidad"
    assert "\U0001f534" not in result_alta["label_es"]
    assert result_alta["emoji"] == "\U0001f534"
    assert result_alta["color_token"] == "cluster_alta"

    result_mod = exp._normalize_cluster_label("\U0001f7e0 Moderada/Baja")
    assert result_mod["label_es"] == "Moderada-Baja severidad"
    assert "\U0001f7e0" not in result_mod["label_es"]
    assert result_mod["emoji"] == "\U0001f7e0"
    assert result_mod["color_token"] == "cluster_moderada"
