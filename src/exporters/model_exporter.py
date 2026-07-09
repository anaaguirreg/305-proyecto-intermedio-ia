from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler


class ModelExporter:

    def __init__(self, config_path: Path, output_dir: Path) -> None:
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        self.project_root = self.config_path.resolve().parent.parent

        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        act5 = cfg.get("acto_5_municipios", {})
        self._cluster_normalization: dict = act5.get("cluster_label_normalization", {})
        self._features_labels_es: dict = act5.get("coefficient_features_labels_es", {})

    def _load_model(self) -> LogisticRegression:
        model_path = self.project_root / "models" / "final_predictor.pkl"
        model = joblib.load(str(model_path))
        assert isinstance(model, LogisticRegression), (
            f"Expected LogisticRegression, got {type(model).__name__}"
        )
        assert model.coef_.shape == (1, 4), (
            f"Expected coef_ shape (1, 4), got {model.coef_.shape}"
        )
        assert list(model.classes_) == [0, 1], (
            f"Expected classes_ [0, 1], got {list(model.classes_)}"
        )
        return model

    def _load_metadata(self) -> float | None:
        meta_path = self.project_root / "models" / "predictor_metadata.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("cv_f1_macro")

    def _reconstruct_scaler(self, features: list[str]) -> RobustScaler:
        clustering_path = (
            self.project_root / "data" / "master" / "tabla_clustering.parquet"
        )
        df = pd.read_parquet(clustering_path, columns=features)
        assert len(df) == 179, f"Expected 179 rows for scaler fit, got {len(df)}"
        X = np.log1p(df[features].values.astype(float))
        scaler = RobustScaler()
        scaler.fit(X)
        return scaler

    def _load_clustering_final(self) -> pd.DataFrame:
        path = (
            self.project_root / "data" / "master" / "tabla_clustering_final.parquet"
        )
        df = pd.read_parquet(path)
        assert len(df) == 177, f"Expected 177 rows, got {len(df)}"
        return df.set_index("cod_municipio")

    def _normalize_cluster_label(self, raw_label: str) -> dict:
        mapping = self._cluster_normalization.get(raw_label)
        if mapping is None:
            raise ValueError(f"Unknown cluster label: {raw_label!r}")
        return mapping

    def _compute_contributions(
        self,
        model: LogisticRegression,
        scaler: RobustScaler,
        clustering_final_df: pd.DataFrame,
    ) -> pd.DataFrame:
        features = list(model.feature_names_in_)
        coef = model.coef_[0]

        raw = clustering_final_df[features].values.astype(float)
        log_raw = np.log1p(raw)
        standardized = (log_raw - scaler.center_) / scaler.scale_
        contributions = standardized * coef

        records = []
        for i, cod in enumerate(clustering_final_df.index):
            for j, feat in enumerate(features):
                records.append(
                    {
                        "cod_municipio": str(cod),
                        "feature_id": feat,
                        "coefficient": float(coef[j]),
                        "standardized_value": float(standardized[i, j]),
                        "contribution": float(contributions[i, j]),
                    }
                )
        return pd.DataFrame(records)

    def _write_modelo_clasificador_json(
        self, scaler: RobustScaler, model: LogisticRegression, cv_f1_macro: float | None
    ) -> Path:
        features = list(model.feature_names_in_)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_type": "LogisticRegression",
            "features": features,
            "features_labels_es": {
                f: self._features_labels_es.get(f, f) for f in features
            },
            "preprocessing": {
                "log1p": True,
                "robust_scaler": {
                    "center": [float(v) for v in scaler.center_],
                    "scale": [float(v) for v in scaler.scale_],
                },
            },
            "coefficients": [float(v) for v in model.coef_[0]],
            "intercept": float(model.intercept_[0]),
            "decision_threshold": 0.5,
            "classes": {
                "0": "Moderada-Baja severidad",
                "1": "Alta severidad",
            },
            "validation_metrics": {
                "cv_f1_macro": cv_f1_macro,
            },
        }
        out_path = self.output_dir / "modelo_clasificador.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return out_path

    def _write_contribuciones_municipales_json(
        self, contributions_df: pd.DataFrame
    ) -> Path:
        municipios: dict = {}
        for cod, group in contributions_df.groupby("cod_municipio"):
            contribs = group[
                ["feature_id", "coefficient", "standardized_value", "contribution"]
            ].to_dict("records")
            municipios[cod] = {"contributions": contribs}

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "municipios": municipios,
        }
        out_path = self.output_dir / "contribuciones_municipales.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return out_path

    def build(self) -> None:
        t0 = datetime.now(timezone.utc)

        model = self._load_model()
        cv_f1_macro = self._load_metadata()
        features = list(model.feature_names_in_)
        scaler = self._reconstruct_scaler(features)
        clustering_final = self._load_clustering_final()
        contributions_df = self._compute_contributions(model, scaler, clustering_final)

        path1 = self._write_modelo_clasificador_json(scaler, model, cv_f1_macro)
        path2 = self._write_contribuciones_municipales_json(contributions_df)

        elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
        print(f"ModelExporter done in {elapsed:.2f}s")
        print(f"  {path1}")
        print(f"  {path2}")
