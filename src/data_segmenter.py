import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataSegmenter:
    """
    Segmentación vectorial estricta (lógica AND).
    - Requisito: Departamento EN lista Y Año EN rango [2018, 2025]
    - 100% máscaras booleanas vectoriales. Cero if/for sobre datos.
    - Rutas 100% dinámicas: se resuelven exclusivamente desde claves del JSON.
    - Cero hardcoding. Validación explícita de configuración.
    - Copia superficial (deep=False) para eficiencia RAM.
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
        self.seg_cfg = self.config.get('segmentation_config', {})
        self.output_cfg = self.seg_cfg.get('output', {})
        self.target_departments = self.config.get('target_departments', [])
        self.year_range = self.config.get('year_range', [])
        if not self.target_departments or len(self.year_range) != 2:
            raise ValueError("❌ Faltan target_departments o year_range")
        self.year_start, self.year_end = int(self.year_range[0]), int(self.year_range[1])

        self.output_dir = (self.project_root / self.paths[self.output_cfg.get('dir_key')]).resolve()
        if not self.output_dir.exists():
            logging.warning(f"⚠️ Ruta '{self.output_dir}' no existe. Se creará para guardar .parquet.")
            self.output_dir.mkdir(parents=True, exist_ok=True)
        else:
            logging.info(f"📂 Usando carpeta configurada: {self.output_dir}")

    def segment(self, df: pd.DataFrame, dataset_name: str) -> Dict[str, Any]:
        # 🔹 MÁSCARAS VECTORIZADAS PURAS (ejecución en C, cero bucles Python)
        mask_dept = df['departamento'].isin(self.target_departments)
        mask_year = df['fecha_hecho'].dt.year.between(self.year_start, self.year_end)

        # 🔹 LÓGICA AND EXPLÍCITA (Departamento Y Año)
        mask_final = mask_dept & mask_year
        df_segmented = df[mask_final].copy(deep=False)

        # 📊 Métricas derivadas directamente de la máscara (vectorial)
        count_original = len(df)
        count_kept = int(mask_final.sum())
        count_excluded = count_original - count_kept

        # 💾 Guardado Parquet con validación explícita de patrón
        pattern = self.output_cfg.get('filename_pattern')
        if not pattern:
            raise ValueError("❌ 'filename_pattern' no definido en 'output' del JSON")

        # ✅ Validación: el patrón debe contener los placeholders requeridos
        required_placeholders = ['{dataset}', '{year_start}', '{year_end}']
        missing = [p for p in required_placeholders if p not in pattern]
        if missing:
            raise ValueError(f"❌ 'filename_pattern' debe incluir {missing}. Actual: '{pattern}'")

        # ✅ Nombres de argumentos idénticos a placeholders del JSON (1:1 trazabilidad)
        filename = pattern.format(
            dataset=dataset_name,
            year_start=self.year_start,
            year_end=self.year_end
        )
        parquet_path = self.output_dir / filename

        df_segmented.to_parquet(
            parquet_path,
            compression=self.output_cfg.get('compression', 'snappy'),
            index=self.output_cfg.get('index', False)
        )

        return {
            'dataset': dataset_name,
            'filas_originales': count_original,
            'filas_cumplen_ambos': count_kept,
            'excluidas_no_cumplen': count_excluded,
            'columnas_preservadas': len(df_segmented.columns),
            'ruta_parquet': str(parquet_path)
        }

    def segment_all(self, datasets_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Orquestador batch. Retorna métricas consolidadas."""
        logging.info(f"✂️ Segmentando (AND Vectorial): Depto + Año {self.year_start}-{self.year_end}")
        results = [self.segment(df, name) for name, df in datasets_dict.items()]
        return pd.DataFrame(results)