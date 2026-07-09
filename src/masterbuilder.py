import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataMasterBuilder:
    """Esqueleto DANE + LEFT JOINs + Tasas + Brechas + ICV-GEN-F + Tabla Clustering.
    Metodología Paso 9. 100% JSON-driven, vectorial, fail-safe."""

    def __init__(self, config_path: str):
        cfg = Path(config_path).resolve()
        if not cfg.exists(): raise FileNotFoundError(f"❌ Config no encontrado: {cfg}")

        # Carga en cascada
        base_path = cfg.parent / "base_config.json"
        base_cfg = {}
        if base_path.exists():
            with open(base_path, 'r', encoding='utf-8') as f: base_cfg = json.load(f)
        with open(cfg, 'r', encoding='utf-8') as f:
            spec_cfg = json.load(f)
        self.config = {**base_cfg, **spec_cfg}
        self.project_root = cfg.parent.parent

        self.paths = self.config.get('paths', {})
        self.mtb_cfg = self.config.get('master_table_config', {})
        self.output_cfg = self.config.get('output_config', {})
        self.year_range = self.config.get('year_range', [])

        self.rate_multiplier = self.mtb_cfg.get('rate_multiplier', 100000)
        self.pop_mapping = self.mtb_cfg.get('population_mapping', {})
        self.weights = self.mtb_cfg.get('icv_gen_f_weights', {})
        self.gap_pairs = self.mtb_cfg.get('gap_pairs', {})

        # Geo ref para nombres municipales
        geo_path = self.project_root / "config" / "municipios_pacifico.json"
        self.geo_ref = {}
        if geo_path.exists():
            with open(geo_path, 'r', encoding='utf-8') as f:
                self.geo_ref = json.load(f).get("municipios", {})

        self.master_dir = (self.project_root / self.paths.get(self.output_cfg.get('master_dir_key', 'master_dir'),
                                                              'data/master')).resolve()
        self.master_dir.mkdir(parents=True, exist_ok=True)

    def _build_skeleton(self, dane_df: pd.DataFrame) -> pd.DataFrame:
        """9.1: Esqueleto desde cod_municipio únicos de DANE × años."""
        years = list(range(self.year_range[0], self.year_range[1] + 1))
        mun_codes = sorted(dane_df['cod_municipio'].dropna().astype('string').unique().tolist())

        idx = pd.MultiIndex.from_product([mun_codes, years], names=['cod_municipio', 'anio_hecho'])
        skeleton = pd.DataFrame(index=idx).reset_index()
        skeleton['cod_municipio'] = skeleton['cod_municipio'].astype('string')

        name_map = {k: v.get('nombre', '') for k, v in self.geo_ref.items()}
        skeleton['municipio'] = skeleton['cod_municipio'].map(name_map)

        # Extraer departamento si existe en DANE
        if 'departamento' in dane_df.columns:
            dept_map = dane_df.drop_duplicates('cod_municipio').set_index('cod_municipio')['departamento']
            skeleton['departamento'] = skeleton['cod_municipio'].map(dept_map)
        else:
            skeleton['departamento'] = skeleton['cod_municipio'].str[:2]

        # ============================================================
        # 🔧 FIX: FILTRO PRE-MERGE para evitar triplicación por área
        # Causa raíz: dane_df (poblacion_limpio.parquet) trae 3 filas
        # por (municipio, año): Total, Cabecera, Resto.
        # Solución: conservar solo area_geo='Total' antes del LEFT JOIN.
        # ============================================================
        if 'area_geo' in dane_df.columns:
            n_antes = len(dane_df)
            dane_df = dane_df[
                dane_df['area_geo'].astype(str).str.strip().str.upper() == 'TOTAL'
            ].copy()
            logging.info(
                f"🔍 Población filtrada por area_geo='Total': "
                f"{n_antes:,} → {len(dane_df):,} filas "
                f"(factor {n_antes / max(len(dane_df), 1):.1f}x)"
            )
        else:
            logging.warning(
                f"⚠️ Columna 'area_geo' no encontrada en dane_df. "
                f"Columnas disponibles: {list(dane_df.columns)}. "
                "Verificar para evitar duplicación."
            )
        # ============================================================

        # LEFT JOIN con población DANE (conserva NaN si no hay denominador)
        pop_cols = ['cod_municipio', 'anio_hecho', 'pob_f_0_17', 'pob_f_18_mas', 'pob_h_0_17', 'pob_h_18_mas',
                    'total_f', 'total_h']
        available_pop = [c for c in pop_cols if c in dane_df.columns]
        skeleton = pd.merge(skeleton, dane_df[available_pop], on=['cod_municipio', 'anio_hecho'], how='left')
        return skeleton.sort_values(['cod_municipio', 'anio_hecho']).reset_index(drop=True)

    def _join_layers(self, skeleton: pd.DataFrame, layers_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """9.2: LEFT JOINs secuenciales. NaN en casos → 0. NaN en población → preservado."""
        df = skeleton.copy()
        merge_cols = ['cod_municipio', 'anio_hecho']
        layer_order = ['casos_vif_nna_f', 'casos_vif_adultas_f', 'casos_sexual_nna_f', 'casos_sexual_adultas_f',
                       'casos_vif_nna_m', 'casos_vif_adultos_m', 'casos_sexual_nna_m', 'casos_sexual_adultos_m']

        for layer_name in layer_order:
            if layer_name in layers_dict:
                subset = layers_dict[layer_name][merge_cols + ['cantidad']].rename(columns={'cantidad': layer_name})
                df = pd.merge(df, subset, on=merge_cols, how='left')
                df[layer_name] = df[layer_name].fillna(0).astype('Int32')
        return df

    def _calculate_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """9.3: Tasas ×100k. NaN en población → tasa = NaN."""
        df_rates = df.copy()
        for rate_col, mapping in self.pop_mapping.items():
            cases_col, pop_col = mapping['cases'], mapping['denominator']
            if cases_col not in df_rates.columns or pop_col not in df_rates.columns: continue

            cases = df_rates[cases_col].astype('Float64')
            pop = df_rates[pop_col].astype('Float64')
            mask_valid = (pop > 0) & pop.notna()
            rates = pd.Series(np.nan, index=df_rates.index, dtype='Float64')

            if mask_valid.any():
                rates.loc[mask_valid] = (cases.loc[mask_valid] / pop.loc[mask_valid]) * self.rate_multiplier
            df_rates[rate_col] = rates
        return df_rates

    def _calculate_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """9.4: Brechas f/m. Si tasa_m == 0 o NaN → brecha = NaN."""
        df_gaps = df.copy()
        for gap_col, pair in self.gap_pairs.items():
            f_col, m_col = pair['f'], pair['m']
            if f_col not in df_gaps.columns or m_col not in df_gaps.columns: continue

            f_tasa = df_gaps[f_col].astype('Float64')
            m_tasa = df_gaps[m_col].astype('Float64')
            mask_valid = (m_tasa > 0) & m_tasa.notna() & f_tasa.notna()
            gaps = pd.Series(np.nan, index=df_gaps.index, dtype='Float64')

            if mask_valid.any():
                gaps.loc[mask_valid] = f_tasa.loc[mask_valid] / m_tasa.loc[mask_valid]
            df_gaps[gap_col] = gaps
        return df_gaps

    def _calculate_icv_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """9.5: MinMax 0-1 + suma ponderada."""
        df_idx = df.copy()
        rate_cols = [c for c in self.weights.keys() if c in df_idx.columns]
        if not rate_cols: return df_idx

        df_norm = df_idx[rate_cols].copy()
        mins, maxs = df_norm.min(), df_norm.max()
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0  # Evita división por cero en columnas constantes

        df_norm = (df_norm - mins) / ranges
        weight_series = pd.Series(self.weights).reindex(df_norm.columns, fill_value=0)
        df_idx['icv_gen_f_score'] = (df_norm * weight_series).sum(axis=1) * 100
        return df_idx

    def _build_clustering_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """9.6: Colapsa años por municipio. Input directo para K-Means."""
        cols_to_avg = [c for c in df.columns if c.startswith(('tasa_', 'brecha_', 'icv_', 'casos_'))]
        agg_dict = {col: 'mean' for col in cols_to_avg if col in df.columns}
        agg_dict['municipio'] = 'first'
        agg_dict['departamento'] = 'first'

        clustering_df = df.groupby('cod_municipio').agg(agg_dict).reset_index()
        return clustering_df.sort_values('cod_municipio').reset_index(drop=True)

    def build(self, layers_dict: Dict[str, pd.DataFrame], dane_df: pd.DataFrame) -> pd.DataFrame:
        logging.info("🏗️ Construyendo Tabla Maestra (Esqueleto + JOINs + Tasas + Brechas + ICV)...")
        skeleton = self._build_skeleton(dane_df)
        master = self._join_layers(skeleton, layers_dict)
        master = self._calculate_rates(master)
        master = self._calculate_gaps(master)
        master = self._calculate_icv_index(master)

        # Guardar maestro anual
        master_file = self.output_cfg.get('master_filename', 'maestro_concurso.parquet')
        out_path_master = self.master_dir / master_file
        master.to_parquet(out_path_master, compression='snappy', index=False)
        logging.info(f"💾 Maestro anual exportado: {out_path_master} ({len(master):,} filas)")

        # Generar y guardar tabla de clustering
        clustering_df = self._build_clustering_table(master)
        cluster_file = self.output_cfg.get('clustering_filename', 'tabla_clustering.parquet')
        out_path_cluster = self.master_dir / cluster_file
        clustering_df.to_parquet(out_path_cluster, compression='snappy', index=False)
        logging.info(f"💾 Tabla Clustering exportada: {out_path_cluster} ({len(clustering_df):,} filas)")

        return master