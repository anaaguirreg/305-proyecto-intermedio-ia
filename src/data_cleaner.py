import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataCleaner:
    """
    Limpieza quirúrgica 100% JSON-driven.
    - Selección de columnas por JSON (optimización RAM)
    - Deduplicación espejo con cuarentena trazable
    - Imputación vectorial con soporte seguro para dtype=category
    - Cero hardcoding, copy(deep=False), patrón idéntico a etapas previas
    """

    def __init__(self, config_path: str):
        cfg = Path(config_path).resolve()
        if not cfg.exists(): raise FileNotFoundError(f"❌ Config no encontrado: {cfg}")
        base_path_file = cfg.parent / "base_config.json"
        base_cfg = {}
        if base_path_file.exists():
            with open(base_path_file, 'r', encoding='utf-8') as f: base_cfg = json.load(f)
        with open(cfg, 'r', encoding='utf-8') as f:
            spec_cfg = json.load(f)
        self.config = {**base_cfg, **spec_cfg}
        self.project_root = cfg.parent.parent

        self.paths = self.config.get('paths', {})
        self.cleaning_cfg = self.config.get('cleaning_config', {})
        self.imputation_rules = self.cleaning_cfg.get('imputation_rules', {})
        self.dedup_rules = self.cleaning_cfg.get('deduplication_rules', {})
        self.docs_dir = (self.project_root / self.paths['docs_dir']).resolve()
        self.output_dir = (self.project_root / self.paths['cleaned_dir']).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _select_columns(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        """Filtra columnas por lista JSON. Vectorial, inmutable, seguro ante columnas faltantes."""
        keep_list = self.config.get("column_selection", {}).get(dataset_name)
        if not keep_list:
            return df.copy(deep=False)  # ✅ Default seguro: conserva todo si no hay config

        # ✅ Validación vectorial: solo toma columnas que realmente existen
        valid_cols = [c for c in keep_list if c in df.columns]
        missing = [c for c in keep_list if c not in df.columns]

        if missing:
            logging.warning(f"⚠️ {dataset_name}: Columnas no encontradas y omitidas: {missing}")

        return df[valid_cols].copy(deep=False)  # ✅ Indexado vectorial + copia superficial

    def _deduplicate(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        """Elimina duplicados espejo exactos y guarda cuarentena trazable."""
        if not self.dedup_rules.get('drop_exact_mirror_duplicates', False):
            return df.copy(deep=False)

        # Máscara vectorial: marca solo el exceso (keep='first')
        mask_dupes = df.duplicated(keep='first')
        count = int(mask_dupes.sum())

        if count > 0:
            q_file = self.dedup_rules['quarantine_filename_pattern'].format(dataset=dataset_name)
            q_path = self.docs_dir / q_file
            df[mask_dupes].copy(deep=False).to_csv(q_path, index=False, encoding='utf-8')
            logging.info(f"🚫 {count} duplicados espejo → cuarentena: {q_path.name}")

        # Retorna solo filas únicas (copia superficial para eficiencia RAM)
        return df[~mask_dupes].copy(deep=False)

    def _impute_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Imputación vectorial con soporte seguro para dtype=category."""
        # ✅ FIX: Garantizar inmutabilidad. Nunca modificamos el DataFrame entrante.
        df = df.copy(deep=False)

        for col, rules in self.imputation_rules.items():
            if col not in df.columns:
                continue

            fill_value = rules.get('null_value')
            if pd.isnull(fill_value):
                continue

            # Si es category y el valor no está en categorías, lo agrega primero
            if pd.api.types.is_categorical_dtype(df[col]):
                if fill_value not in df[col].cat.categories:
                    df[col] = df[col].cat.add_categories([fill_value])

            # Imputación vectorial (ejecución en C)
            df[col] = df[col].fillna(fill_value)

            # Limpieza de negativos para columnas numéricas
            if rules.get('negative_to_zero') and pd.api.types.is_numeric_dtype(df[col]):
                df.loc[df[col] < 0, col] = 0

        return df

    def clean(self, df: pd.DataFrame, dataset_name: str) -> Dict[str, Any]:
        """Orquestador de limpieza para un dataset."""
        logging.info(f"🧼 Limpiando: {dataset_name} ({len(df):,} filas)")

        # ✅ ORDEN CORRECTO PARA INTEGRIDAD ESTADÍSTICA:
        # 1. Deduplicación PRIMERO (sobre TODAS las columnas originales)
        df_before = len(df)
        df_clean = self._deduplicate(df, dataset_name)
        deduped_count = df_before - len(df_clean)

        # 2. Selección de columnas DESPUÉS (evita duplicados artificiales por reducción dimensional)
        df_clean = self._select_columns(df_clean, dataset_name)

        # 3. Imputación (sobre DataFrame ya filtrado)
        nulls_before = df_clean.isna().sum().sum()
        df_clean = self._impute_nulls(df_clean)
        nulls_imputed = int(nulls_before - df_clean.isna().sum().sum())

        # 4. Guardado
        out_path = self.output_dir / f"{dataset_name}_limpio.parquet"
        df_clean.to_parquet(out_path, compression='snappy', index=False)

        return {
            'dataset': dataset_name,
            'filas_entrada': df_before,
            'filas_salida': len(df_clean),
            'duplicados_eliminados': deduped_count,
            'nulos_imputados': nulls_imputed,
            'ruta_limpio': str(out_path)
        }

    def clean_all(self, datasets_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Orquestador batch. Retorna métricas consolidadas."""
        logging.info(f"🚀 Iniciando limpieza de {len(datasets_dict)} dataset(s)...")
        results = [self.clean(df, name) for name, df in datasets_dict.items()]
        return pd.DataFrame(results)