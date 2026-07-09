import pandas as pd
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MetadataMapper:
    """
    Reconocimiento estructural de datasets crudos.
    - SOLO registra: dimensiones, dtypes, memoria RAM/disco, schema, muestra, columnas pesadas
    - CERO métricas de calidad, CERO transformación, CERO hardcoding
    - Rutas ancladas a project_root (cero dependencia de cwd)
    - Validación explícita de directorios (cero mkdir automático)
    - Output estandarizado vía display_config del JSON
    - Vectorización pura: operaciones nativas pandas/numpy, sin loops sobre datos
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
        docs_key = self.paths.get('docs_dir')
        if not docs_key: raise ValueError("❌ 'docs_dir' no definido")

        self.docs_dir = (self.project_root / docs_key).resolve()
        if not self.docs_dir.exists(): raise FileNotFoundError(f"❌ Carpeta docs no existe: {self.docs_dir}")

        logging.info(f"📂 Ruta de docs validada: {self.docs_dir}")

    def _get_disk_size_mb(self, file_path: Optional[Path]) -> float:
        """Obtiene peso en disco a nivel OS (O(1))."""
        if file_path and file_path.exists():
            return round(file_path.stat().st_size / (1024 ** 2), 2)
        return 0.0

    def _get_memory_profile(self, df: pd.DataFrame) -> Dict:
        """Calcula RAM total y top 5 columnas 'object' por consumo (blindado contra IndexingError)."""
        mem_bytes = df.memory_usage(deep=True)
        total_mb = round(mem_bytes.sum() / (1024 ** 2), 2)

        # 🔧 FIX: Evitar indexado booleano directo que causa IndexingError en pandas
        obj_cols = [col for col in df.columns if df.dtypes[col] == 'object']

        if obj_cols:
            heavy_objs = mem_bytes[obj_cols].sort_values(ascending=False).head(5)
            heavy_objs_mb = {col: round(val / (1024 ** 2), 2) for col, val in heavy_objs.items()}
        else:
            heavy_objs_mb = {}

        return {"total_ram_mb": total_mb, "heavy_object_cols_mb": heavy_objs_mb}

    def _snapshot_structure(self, df: pd.DataFrame, name: str, file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Toma la 'foto anatómica' del DataFrame crudo. ESQUEMA SIEMPRE CONSISTENTE."""
        base_schema = {
            "dataset": name,
            "filas": 0,
            "columnas": 0,
            "tipos_datos": {},
            "memoria_ram_mb": 0.0,
            "peso_disco_mb": self._get_disk_size_mb(file_path),
            "schema": [],
            "muestra_estructural": [],
            "columnas_objeto_pesadas_mb": {}
        }

        if df.empty:
            base_schema["error"] = "DataFrame vacío o sin datos tras carga"
            logging.warning(f"⚠️ {name}: {base_schema['error']}")
            return base_schema

        # Cálculo vectorizado sobre datos reales
        base_schema.update({
            "filas": len(df),
            "columnas": len(df.columns),
            "tipos_datos": {str(k): str(v) for k, v in df.dtypes.to_dict().items()},
            "memoria_ram_mb": self._get_memory_profile(df)["total_ram_mb"],
            "schema": df.columns.tolist(),
            "muestra_estructural": df.head(2).to_dict(orient='records'),
            "columnas_objeto_pesadas_mb": self._get_memory_profile(df)["heavy_object_cols_mb"]
        })

        return base_schema

    def run(self, df: pd.DataFrame, name: str, file_path: Optional[Path] = None) -> Dict[str, Any]:
        """Ejecuta mapeo estructural en un dataset. NO modifica el DataFrame."""
        logging.info(f"📸 Mapeando estructura: {name}")
        return self._snapshot_structure(df, name, file_path)

    def map_all(self, datasets_dict: Dict[str, pd.DataFrame],
                raw_paths: Optional[Dict[str, Path]] = None) -> pd.DataFrame:
        """Consolida mapeos estructurales en un DataFrame exportable."""
        logging.info(f"🚀 Mapeando {len(datasets_dict)} dataset(s)...")
        raw_paths = raw_paths or {}

        results = [
            self.run(df, name, raw_paths.get(name))
            for name, df in datasets_dict.items()
        ]
        report_df = pd.DataFrame(results)

        # ✅ Exportar usando ruta anclada + validada en __init__
        if self.docs_dir.exists():
            out_path = self.docs_dir / "mapeo_estructural_raw.csv"

            # Serialización segura para CSV
            report_flat = report_df.copy()
            for col in ['tipos_datos', 'schema', 'muestra_estructural', 'columnas_objeto_pesadas_mb']:
                if col in report_flat.columns:
                    report_flat[col] = report_flat[col].apply(
                        lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x)
                    )
            report_flat.to_csv(out_path, index=False, encoding='utf-8')
            logging.info(f"📄 Reporte exportado: {out_path}")

        return report_df

    def print_tablero(self, report_df: pd.DataFrame) -> None:
        """Imprime resumen estructural usando display_config del JSON."""
        # ✅ Output estandarizado desde JSON
        disp = self.config.get('display_config', {})
        sep_char = disp.get('separator_char', '=')
        sep_len = disp.get('separator_length', 90)
        indent = disp.get('indent', '   ')
        prefix = disp.get('prefix_dataset', '🔹 ')

        SEP = sep_char * sep_len

        print(f"\n{SEP}")
        print("📊 TABLERO DE RECONOCIMIENTO ESTRUCTURAL")
        print(SEP)
        for _, row in report_df.iterrows():
            print(f"\n{prefix}{row.get('dataset', 'DESCONOCIDO').upper()}")
            print(f"{indent}📐 Estructura: {row.get('filas', 0):,} filas × {row.get('columnas', 0)} columnas")
            print(
                f"{indent}💾 Memoria RAM: {row.get('memoria_ram_mb', 0.0)} MB | Disco: {row.get('peso_disco_mb', 0.0)} MB")
            print(f"{indent}🧬 Tipos: {row.get('tipos_datos', {})}")
            if row.get('columnas_objeto_pesadas_mb'):
                print(f"{indent}⚖️ Columnas object pesadas: {row['columnas_objeto_pesadas_mb']}")
            print(f"{indent}📋 Schema: {row.get('schema', [])[:5]}{'...' if len(row.get('schema', [])) > 5 else ''}")
            if row.get('error'):
                print(f"{indent}🚨 Estado: {row['error']}")
        print(f"\n{SEP}")