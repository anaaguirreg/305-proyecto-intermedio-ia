import pandas as pd
import json
import re
import logging
import unicodedata
from pathlib import Path
from typing import Dict, Any, Optional, Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataStandardizer:
    """
    Estandarización vectorizada, 100% JSON-driven, cero hardcoding.
    Optimizada para microdatos masivos: copy-on-write, regex pre-compiladas, casting matricial.
    Preserva <NA>, datos valiosos y aplica tipado seguro.
    - FIX: cod_municipio estandarizado a 5 dígitos (DDMMM) de forma vectorial.
    - FIX: Clasificación taxonómica genérica integrada en etapa de estandarización.
    - FIX: Derivación temporal vectorial (anio/mes/dia desde fecha_hecho).
    - FIX: Validación geográfica externa para recuperar nombres y etiquetar códigos inválidos.
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
        self.type_rules = self.config.get('type_rules', {})
        self.age_config = self.config.get('age_aggregation', {})
        self.col_alias_map = {}
        for c, aliases in self.config.get('column_aliases', {}).items():
            for a in aliases: self.col_alias_map[self._normalize_text(a)] = self._normalize_text(c)
        self.month_mapping = {self._normalize_text(k): v for k, v in self.config.get('month_mapping', {}).items()}
        self.normalization_cfg = self.config.get('normalization_config', {})
        self.value_aliases = self.config.get('value_aliases', {})
        self.regex_patterns = {k: re.compile(v) for k, v in self.config.get('regex_patterns', {}).items()}

        geo_path = self.project_root / "config" / "municipios_pacifico.json"
        self.geo_ref = {}
        self.geo_fallback = "CODIGO_MAL_REGISTRADO"
        if geo_path.exists():
            with open(geo_path, 'r', encoding='utf-8') as f:
                g = json.load(f)
                self.geo_ref = g.get("municipios", {})
                self.geo_fallback = g.get("invalid_codes_fallback", self.geo_fallback)

    @staticmethod
    def _normalize_text(text: Union[str, pd.Series]) -> Union[str, pd.Series]:
        if isinstance(text, pd.Series):
            return (text.fillna("")
                    .str.lower().str.strip()
                    .str.normalize('NFD').str.encode('ascii', 'ignore').str.decode('ascii')
                    .str.replace(r'[^a-z0-9_]', '', regex=True)
                    .str.replace(' ', '_', regex=False)
                    .str.replace(r'_+', '_', regex=True)
                    .str.strip('_'))

        if pd.isna(text): return ""
        s = str(text).lower().strip()
        s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
        s = s.replace(' ', '_')
        s = re.sub(r'[^a-z0-9_]', '', s)
        while '__' in s: s = s.replace('__', '_')
        return s.strip('_')

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        raw_norm = {self._normalize_text(c): c for c in df.columns}
        rename_dict = {raw_norm[alias]: canon for alias, canon in self.col_alias_map.items() if alias in raw_norm}
        if rename_dict:
            df = df.rename(columns=rename_dict)
        return df

    def _compose_fecha_hecho(self, df: pd.DataFrame) -> pd.DataFrame:
        if not {'anio_hecho', 'mes_hecho', 'dia_hecho'}.issubset(df.columns):
            return df

        y = pd.to_numeric(df['anio_hecho'], errors='coerce').astype('Int32')
        m_clean = self._normalize_text(df['mes_hecho'])
        m_num = m_clean.map(self.month_mapping).astype('Int32')

        valid_mask = y.notna() & m_num.notna()
        df['fecha_hecho'] = pd.NaT

        if valid_mask.any():
            y_str = y[valid_mask].astype('string')
            m_str = m_num[valid_mask].astype('string').str.zfill(2)
            df.loc[valid_mask, 'fecha_hecho'] = pd.to_datetime(
                y_str + '-' + m_str + '-01', errors='coerce', format='%Y-%m-%d'
            )
        return df

    def _ensure_fecha_hecho_from_year(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'anio_hecho' in df.columns and 'fecha_hecho' not in df.columns:
            mask_year = df['anio_hecho'].notna()
            df['fecha_hecho'] = pd.NaT
            if mask_year.any():
                y_clean = pd.to_numeric(df.loc[mask_year, 'anio_hecho'], errors='coerce').astype('Int32').astype(
                    'string')
                df.loc[mask_year, 'fecha_hecho'] = pd.to_datetime(
                    y_clean + '-01-01', errors='coerce', dayfirst=False
                )
        return df

    def _cast_types(self, df: pd.DataFrame) -> pd.DataFrame:
        for col, dtype_str in self.type_rules.items():
            if col not in df.columns: continue
            try:
                if 'datetime' in dtype_str:
                    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                elif dtype_str == 'Int32':
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int32')
                elif dtype_str == 'string':
                    s = df[col].astype('string')
                    if col == 'cod_municipio':
                        s = s.str.replace(r'\D', '', regex=True)
                        s = s.str[:5].str.zfill(5)
                    else:
                        trailing_dot = self.regex_patterns.get('trailing_dot_zero')
                        if trailing_dot:
                            s = s.str.replace(trailing_dot, '', regex=True)
                    df[col] = s
                elif dtype_str == 'category':
                    df[col] = df[col].astype('category')
            except Exception as e:
                logging.warning(f"⚠️ Falló casteo de '{col}' a {dtype_str}: {e}")

        obj_cols = df.select_dtypes(include=['object']).columns
        if len(obj_cols) > 0:
            df = df.astype({col: 'string' for col in obj_cols})
        return df

    def _normalize_values(self, df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.normalization_cfg
        targets = cfg.get('targets', [])
        case_transform = cfg.get('case_transform', 'none').lower()
        remove_accents = cfg.get('remove_accents', False)
        allowed_pattern = self.regex_patterns.get(cfg.get('allowed_chars_key', 'allowed_chars_normalization'))

        # ✅ Pre-procesamiento de config (NO sobre datos): lookup invertido para .map() vectorial
        alias_map = {}
        for canon, aliases in self.value_aliases.items():
            for alias in aliases:
                norm = alias.lower().strip()
                if remove_accents:
                    norm = unicodedata.normalize('NFD', norm).encode('ascii', 'ignore').decode()
                alias_map[norm] = canon

        for col in targets:
            if col not in df.columns: continue

            # 🔄 Pipeline 100% vectorial sobre columnas completas
            s = df[col].astype('string').str.strip().str.lower()
            if remove_accents:
                s = s.str.normalize('NFD').str.encode('ascii', 'ignore').str.decode('ascii')
            if allowed_pattern:
                s = s.str.replace(allowed_pattern, '', regex=True).str.strip()

            # ✅ Lookup vectorial + preservación de no-mapeados
            mapped = s.map(alias_map)
            result = mapped.combine_first(s)

            if case_transform == 'upper':
                result = result.str.upper()
            elif case_transform == 'lower':
                result = result.str.lower()
            elif case_transform == 'title':
                result = result.str.title()
            df[col] = result
        return df

    def _validate_and_fill_municipios(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida y rellena municipios usando referencia geográfica JSON. Vectorial, inmutable."""
        if not self.geo_ref or "cod_municipio" not in df.columns:
            return df

        # Normalización vectorial de códigos DANE (5 dígitos)
        codes = df["cod_municipio"].astype(str).str.zfill(5)

        # Identifica filas donde municipio está vacío o es nulo
        mask_empty = df["municipio"].isna() | (df["municipio"].astype(str).str.strip() == "")

        # ✅ Extrae SOLO nombres válidos del JSON (ignora dicts vacíos o con null)
        valid_names = {
            k: v.get("nombre") for k, v in self.geo_ref.items()
            if isinstance(v, dict) and v.get("nombre")
        }

        # Mapeo vectorial de código → nombre válido
        name_map = codes.map(valid_names)

        # 1️⃣ Relleno: solo si hay un nombre canónico válido
        fill_mask = mask_empty & name_map.notna()
        if fill_mask.any():
            df.loc[fill_mask, "municipio"] = name_map[fill_mask]
            logging.info(f"🌍 Geo-Enriquecimiento: {fill_mask.sum()} municipios recuperados")

        # 2️⃣ Etiquetado: código presente pero sin nombre válido en referencia
        invalid_mask = mask_empty & codes.notna() & name_map.isna()
        if invalid_mask.any():
            df.loc[invalid_mask, "municipio"] = self.geo_fallback
            logging.info(f"🏷️ Geo-Integridad: {invalid_mask.sum()} códigos inválidos → '{self.geo_fallback}'")

        return df

    def _apply_dynamic_taxonomy(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        """Motor de taxonomía 100% JSON-driven. Cero hardcoding. Escala infinitamente."""
        taxonomy_rules = self.config.get("taxonomy_config", [])
        if not taxonomy_rules:
            return df

        for rule in taxonomy_rules:
            # Solo ejecuta si la regla corresponde al dataset actual Y la columna fuente existe
            if rule.get("dataset") != dataset_name:
                continue

            source = rule.get("source_col")
            target = rule.get("target_col")
            patterns = rule.get("patterns", {})

            if not source or not target or source not in df.columns or not patterns:
                continue

            # Vectorial, inmutable, seguro ante nulos
            s = df[source].astype("string").fillna("")
            df[target] = "NO_REGISTRADO"  # Default seguro

            # Orden JSON = prioridad. Ejecución en C.
            for category, regex in patterns.items():
                mask = s.str.contains(regex, case=False, na=False, regex=True)
                df.loc[mask, target] = category

        return df

    def _derive_temporal_features(self, df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
        """Deriva año/mes/día desde fecha_hecho. 100% JSON-driven, cero hardcoding."""
        rules = self.config.get("temporal_derivation", {}).get(dataset_name)
        if not rules or "fecha_hecho" not in df.columns:
            return df

        dt = pd.to_datetime(df["fecha_hecho"], errors="coerce")
        names_cfg = self.config.get("temporal_names_config", {})

        # ✅ Construye mapeos EXCLUSIVAMENTE desde JSON (cero diccionarios en Python)
        meses = names_cfg.get("meses", [])
        dias = names_cfg.get("dias_semana", [])
        month_map = {i + 1: m.upper() for i, m in enumerate(meses)}
        day_map = {i: d.upper() for i, d in enumerate(dias)}

        if "anio_hecho" in rules["fecha_hecho"]:
            df["anio_hecho"] = dt.dt.year.astype("Int32")

        if "mes_hecho" in rules["fecha_hecho"] and month_map:
            df["mes_hecho"] = dt.dt.month.map(month_map).astype("string")

        if "dia_hecho" in rules["fecha_hecho"] and day_map:
            df["dia_hecho"] = dt.dt.dayofweek.map(day_map).astype("string")

        return df

    def _aggregate_dane_age(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        pattern = self.age_config.get('regex_pattern', '')
        age_cols = df.filter(regex=pattern).columns
        if len(age_cols) == 0: return df

        idx = pd.Index(age_cols)
        genders = idx.str.extract(r'(MUJERES|HOMBRES)', expand=False).str.upper()
        ages = idx.str.extract(r'(\d+)', expand=False).astype(int)

        for target_col, cfg in self.age_config.get('target_columns', {}).items():
            mask = (genders == cfg['gender_keyword']) & (ages >= cfg['min_age']) & (ages <= cfg['max_age'])
            cols_to_sum = age_cols[mask]
            if len(cols_to_sum) > 0:
                num_subset = df[cols_to_sum].astype('Float64')
                df[target_col] = num_subset.sum(axis=1, min_count=1).astype('Int32')
            else:
                df[target_col] = pd.NA

        check = self.age_config.get('sanity_check', {})
        tol = check.get('tolerance_pct', 0.001)
        f_base = check.get('f_base_col')
        if 'pob_f_0_17' in df.columns and f_base and f_base in df.columns:
            sum_f = df['pob_f_0_17'].astype(float).fillna(0) + df['pob_f_18_mas'].astype(float).fillna(0)
            base_f = df[f_base].astype(float).fillna(0)
            valid = base_f > 0
            if valid.any():
                err = (sum_f[valid] - base_f[valid]).abs() / base_f[valid]
                if (err > tol).any():
                    logging.warning(f"⚠️ {name}: Discrepancia > {tol * 100}% en verificación femenina")

        df = df.drop(columns=age_cols, errors='ignore')
        return df

    # ✅ ÚNICO MÉTODO standardize() - EL CORREGIDO
    def standardize(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        logging.info(f"🔧 Estandarizando: {name} ({len(df):,} filas, {len(df.columns)} cols)")
        df_std = df.copy(deep=False)
        df_std.attrs['original_name'] = name

        df_std = self._rename_columns(df_std)
        df_std = self._compose_fecha_hecho(df_std)
        df_std = self._ensure_fecha_hecho_from_year(df_std)
        df_std = self._cast_types(df_std)
        df_std = self._normalize_values(df_std)
        df_std = self._validate_and_fill_municipios(df_std)  # ✅ VALIDACIÓN GEOGRÁFICA
        df_std = self._apply_dynamic_taxonomy(df_std, name)  # ✅ Taxonomía genérica
        df_std = self._derive_temporal_features(df_std, name)  # ✅ Derivación temporal
        df_std = self._aggregate_dane_age(df_std, name)

        logging.info(f"✅ {name} estandarizado. Columnas finales: {len(df_std.columns)}")
        return df_std

    def standardize_all(self, datasets_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        logging.info(f"🚀 Estandarizando {len(datasets_dict)} dataset(s)...")
        return {name: self.standardize(df, name) for name, df in datasets_dict.items()}