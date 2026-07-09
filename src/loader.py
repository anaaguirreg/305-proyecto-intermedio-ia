import pandas as pd
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataLoader:
    """
    Ingesta pura. Configuración 100% externa.
    - Anclaje determinista al archivo de config (cero búsqueda, cero ambigüedad)
    - Convención: config/mapping_config.json está directamente bajo la raíz del proyecto
    - Mapeo de parámetros dinámico (sin condicionales hardcodeados)
    - Carga como strings para saltar inferencia de tipos (RAM/CPU optimizado)
    - Validación explícita con diagnóstico de columnas
    """

    def __init__(self, config_path: str, base_path_override: Optional[str] = None):
        cfg = Path(config_path).resolve()
        if not cfg.exists(): raise FileNotFoundError(f"❌ Config no encontrado: {cfg}")

        # 🔹 Carga en cascada
        base_path_file = cfg.parent / "base_config.json"
        base_cfg = {}
        if base_path_file.exists():
            with open(base_path_file, 'r', encoding='utf-8') as f: base_cfg = json.load(f)
        with open(cfg, 'r', encoding='utf-8') as f:
            spec_cfg = json.load(f)
        self.config = {**base_cfg, **spec_cfg}
        self.project_root = cfg.parent.parent

        self.paths = self.config.get('paths', {})
        self.file_loading = self.config.get('file_loading', {})
        self.datasets_config = self.config.get('datasets', {})

        self.base_path = Path(base_path_override).resolve() if base_path_override else (
                    self.project_root / self.paths.get('base_data_dir', 'data')).resolve()
        if not self.base_path.exists(): raise FileNotFoundError(f"❌ Ruta de datos no existe: {self.base_path}")

        logging.info(f"📁 DataLoader inicializado en: {self.base_path}")
        logging.info(f"🔍 Anclado a raíz de proyecto: {self.project_root}")

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_data(self, dataset_key: str) -> pd.DataFrame:
        ds_cfg = self.datasets_config[dataset_key]
        file_type = ds_cfg.get('type', 'csv').lower()
        file_path = self.base_path / self.paths.get('raw_dir', 'raw') / ds_cfg['filename']

        if not file_path.exists():
            raise FileNotFoundError(f"❌ Archivo no encontrado: {file_path}")

        load_params = self._merge_load_params(file_type, ds_cfg)

        try:
            if file_type == 'csv':
                df = pd.read_csv(file_path, **load_params)
            elif file_type in ['xls', 'xlsx', 'excel']:
                df = pd.read_excel(file_path, **load_params)

                # Aplanamiento vectorizado de MultiIndex (cero bucles)
                if isinstance(df.columns, pd.MultiIndex):
                    lvl0 = df.columns.get_level_values(0).astype(str)
                    lvl1 = df.columns.get_level_values(1).astype(str)
                    mask_na = pd.isna(df.columns.get_level_values(1)) | (lvl1 == '') | lvl1.str.contains(
                        'unnamed|level', case=False, na=True)
                    combined = np.where(mask_na, lvl0, (lvl0 + ' ' + lvl1).str.strip())
                    df.columns = pd.Index(combined)

            # Normalización vectorizada de nombres
            df.columns = (
                df.columns
                .str.strip()
                .str.replace(r'\s+', ' ', regex=True)
                .str.replace(r'(?i)unnamed.*', '', regex=True)
                .str.strip()
            )

            # Validación robusta con diagnóstico explícito
            required = ds_cfg.get('required_columns', [])
            cols_upper = {c.upper().strip(): c for c in df.columns}
            missing = [c for c in required if c.upper().strip() not in cols_upper]

            if missing:
                actual_first = df.columns[:12].tolist()
                raise ValueError(
                    f"❌ {dataset_key} falta columnas clave: {missing}. "
                    f"Columnas reales encontradas: {actual_first}"
                )

            logging.info(f"✅ {dataset_key} cargado: {df.shape[0]:,} filas, {df.shape[1]} cols")
            return df

        except Exception as e:
            logging.error(f"❌ Error cargando '{dataset_key}': {type(e).__name__} - {str(e)}")
            raise

    def _merge_load_params(self, file_type: str, ds_cfg: Dict) -> Dict:
        TRANSLATION_MAP = {
            'header_mode': 'header',
            'skip_rows': 'skiprows',
            'sheet_index': 'sheet_name',
            'dtypes': 'dtype',
            'usecols': 'usecols'
        }
        METADATA_KEYS = {'filename', 'type', 'required_columns', 'age_column_pattern', 'load_params'}

        merged = {}
        if file_type in self.file_loading:
            merged.update(self.file_loading[file_type])

        for k, v in ds_cfg.items():
            if k in METADATA_KEYS:
                continue
            if k == 'load_as_strings' and v is True:
                merged['dtype'] = str
                continue
            target_key = TRANSLATION_MAP.get(k, k)
            merged[target_key] = v

        return merged

    def load_all_datasets(self, dataset_keys: Optional[list] = None, skip_on_error: bool = True) -> Dict[
        str, pd.DataFrame]:
        keys = dataset_keys or list(self.datasets_config.keys())
        datasets = {}
        logging.info(f"🚀 Cargando {len(keys)} dataset(s)...")
        for key in keys:
            try:
                datasets[key] = self.load_data(key)
            except Exception as e:
                logging.warning(f"⚠️ Falló '{key}': {str(e)}")
                if not skip_on_error:
                    raise
        logging.info(f"✅ Carga completada: {len(datasets)}/{len(keys)} exitosos.")
        return datasets