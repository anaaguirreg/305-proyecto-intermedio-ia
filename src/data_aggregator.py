import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataAggregator:
    """
    Etapa 6: Construcción de Capas Analíticas (RAM-Only).
    - Responsabilidad Única: Filtrar por género/etario → agrupar cod_municipio+anio → sumar cantidad.
    - Cero escritura en disco. Cero esqueleto. Cero joins.
    - 100% JSON-driven, vectorial, validación metodológica integrada.
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
        self.agg_cfg = self.config.get('aggregation_config', {})
        self.cleaned_dir = (self.project_root / self.paths['cleaned_dir']).resolve()

    def _load_cleaned(self, dataset_name: str) -> pd.DataFrame:
        path = self.cleaned_dir / f"{dataset_name}_limpio.parquet"
        if not path.exists():
            raise FileNotFoundError(f"❌ Dataset limpio no encontrado: {path}")
        return pd.read_parquet(path)

    def _create_layer(self, layer_name: str, layer_cfg: Dict[str, Any]) -> pd.DataFrame:
        """Filtra y agrega una capa analítica. 100% vectorial, RAM-only."""
        df = self._load_cleaned(layer_cfg['source'])

        # Extraer año solo si no existe (fallback seguro desde fecha_hecho)
        if 'anio_hecho' not in df.columns:
            df['anio_hecho'] = df['fecha_hecho'].dt.year.astype('Int32')

        # Máscaras booleanas vectoriales sobre columnas ESTANDARIZADAS
        mask_genero = df['genero_victima'] == layer_cfg['genero_filter']
        mask_etario = df['grupo_etario'].isin(layer_cfg['etario_filter'])

        df_filtered = df[mask_genero & mask_etario].copy(deep=False)
        groupby_cols = self.agg_cfg['groupby_columns']

        # Agregación vectorial
        agg_df = (df_filtered
                  .groupby(groupby_cols, observed=True)[self.agg_cfg['sum_column']]
                  .sum()
                  .reset_index())

        # ✅ Validación metodológica estricta: max 1 fila por cod_municipio+anio_hecho
        max_group = agg_df.groupby(groupby_cols).size().max()
        if max_group > 1:
            raise ValueError(
                f"⚠️ {layer_name}: Agregación duplicada detectada (max={max_group}). Revisar filtros fuente.")

        return agg_df.astype({groupby_cols[0]: 'string', groupby_cols[1]: 'Int32'})

    def aggregate_all(self) -> Dict[str, pd.DataFrame]:
        """Orquestador batch. Retorna SOLO las 4 capas en RAM. Cero I/O."""
        logging.info(f"📐 Construyendo {len(self.agg_cfg['layers'])} capas analíticas en RAM...")

        layers = {}
        for name, cfg in self.agg_cfg['layers'].items():
            layers[name] = self._create_layer(name, cfg)
            logging.info(f"✅ {name}: {len(layers[name]):,} filas | columnas: {list(layers[name].columns)}")

        logging.info("🛡️ Validación: max(groupby.size()) <= 1 en todas las capas. Listo para MasterBuilder.")
        return layers