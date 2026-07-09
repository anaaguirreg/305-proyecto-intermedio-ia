import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataAuditor:
    """
    Auditoría integral 100% JSON-driven. Escanea CADA columna y CADA fila.
    - Rutas ancladas a project_root (cero dependencia de cwd)
    - Validación explícita de directorios existentes (cero mkdir automático)
    - Dominio por columna + safe .astype('string') para dtype=category
    - 100% vectorial, cero hardcoding, patrón idéntico a módulos previos.
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
        self.auditor_cfg = self.config.get('auditor_config', {})
        self.output_cfg = self.auditor_cfg.get('output', {})
        self.year_range = self.config.get('year_range', [])
        self.type_rules = self.config.get('type_rules', {})
        self.priority_cols = self.auditor_cfg.get('priority_alert_columns', [])
        self.numeric_rules = self.auditor_cfg.get('numeric_rules', {})
        self.domain_rules = self.auditor_cfg.get('domain_rules', {})
        if not self.domain_rules: raise ValueError("❌ 'domain_rules' no definido")

        self.output_dir = (self.project_root / self.paths[self.output_cfg.get('report_dir_key')]).resolve()
        if not self.output_dir.exists(): raise FileNotFoundError(f"❌ Carpeta docs no existe: {self.output_dir}")

        logging.info(f"📂 Ruta de reporte validada: {self.output_dir}")

    def _audit_nulls(self, df: pd.DataFrame) -> Dict[str, Any]:
        null_counts = df.isna().sum()
        null_pct = (df.isna().mean() * 100).round(2)
        all_issues = {col: {'count': int(null_counts[col]), 'pct': float(null_pct[col])} for col in df.columns if
                      null_counts[col] > 0}
        priority_issues = {col: all_issues[col] for col in self.priority_cols if col in all_issues}
        return {'total_columns_with_nulls': len(all_issues), 'all_null_issues': all_issues,
                'priority_alert_issues': priority_issues}

    def _audit_duplicates(self, df: pd.DataFrame) -> Dict[str, Any]:
        mask_excess = df.duplicated(keep='first')
        count = int(mask_excess.sum())
        sample = []
        if count > 0:
            sample = df.loc[mask_excess].head(3).copy(deep=False).to_dict(orient='records')
        return {'exact_mirror_duplicates': count, 'duplicate_sample': sample}

    def _audit_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        expected = set(self.type_rules.keys())
        actual = set(df.columns)
        mismatches = []
        for col in actual & expected:
            exp_dtype = self.type_rules[col]
            act_dtype = str(df[col].dtype)
            if 'datetime' in exp_dtype and 'datetime' not in act_dtype:
                mismatches.append({'col': col, 'expected': exp_dtype, 'actual': act_dtype})
            elif exp_dtype in ('Int32', 'Float64') and not pd.api.types.is_numeric_dtype(df[col]):
                mismatches.append({'col': col, 'expected': exp_dtype, 'actual': act_dtype})
        return {'missing_from_type_rules': sorted(expected - actual),
                'extra_columns_not_in_rules': sorted(actual - expected), 'type_mismatches': mismatches}

    def _audit_domain(self, df: pd.DataFrame) -> Dict[str, Any]:
        issues = {}
        for col, allowed_values in self.domain_rules.items():
            if col not in df.columns: continue
            # ✅ Safe para dtype=category: cast a string antes de .isin()
            series_str = df[col].astype('string')
            invalid_mask = ~series_str.isin(allowed_values) & series_str.notna()
            if invalid_mask.any():
                issues[col] = {
                    'invalid_count': int(invalid_mask.sum()),
                    'invalid_pct': round(invalid_mask.sum() / len(df) * 100, 2),
                    'top_invalid_values': df.loc[invalid_mask, col].value_counts().head(5).to_dict()
                }
        return {'domain_violations': issues}

    def _audit_temporal(self, df: pd.DataFrame) -> Dict[str, Any]:
        if 'fecha_hecho' not in df.columns:
            return {'temporal_issues': {}}
        issues = {}
        years = df['fecha_hecho'].dt.year
        mask_range = years.between(self.year_range[0], self.year_range[1])
        out_of_range = int((~mask_range & df['fecha_hecho'].notna()).sum())
        if out_of_range > 0: issues['out_of_year_range'] = {'count': out_of_range}

        now_naive = pd.Timestamp('now')
        future_mask = df['fecha_hecho'] > now_naive
        if future_mask.any(): issues['future_dates'] = {'count': int(future_mask.sum())}

        nat_count = int(df['fecha_hecho'].isna().sum())
        if nat_count > 0: issues['null_dates'] = {'count': nat_count}
        return {'temporal_issues': issues}

    def _audit_numeric_sanity(self, df: pd.DataFrame) -> Dict[str, Any]:
        issues = {}
        num_cols = df.select_dtypes(include=['number', 'Int32', 'Float64']).columns
        min_val = self.numeric_rules.get('min_value', 0)
        iqr_mult = self.numeric_rules.get('outlier_iqr_multiplier', 3.0)
        for col in num_cols:
            s = df[col].dropna()
            if len(s) == 0: continue
            below_min = int((s < min_val).sum())
            if below_min > 0: issues[f'{col}_below_min'] = {'count': below_min, 'min_threshold': min_val}
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower, upper = q1 - iqr_mult * iqr, q3 + iqr_mult * iqr
                outliers = int(((s < lower) | (s > upper)).sum())
                if outliers > 0: issues[f'{col}_outliers'] = {'count': outliers,
                                                              'bounds': [round(lower, 2), round(upper, 2)]}
        return {'numeric_sanity_issues': issues}

    def _export_report(self, report: Dict[str, Any], dataset_name: str) -> Path:
        filename = self.output_cfg.get('report_filename', 'auditoria_{dataset}.csv').format(dataset=dataset_name)
        out_path = self.output_dir / filename
        flat = []
        for section, content in report.items():
            if section in ('dataset', 'total_rows', 'total_columns', 'timestamp', 'report_path'): continue
            if isinstance(content, dict):
                for k, v in content.items():
                    flat.append({'section': section, 'metric': k, 'value': str(v)})
            elif isinstance(content, (int, float, str)):
                flat.append({'section': 'meta', 'metric': section, 'value': str(content)})
        pd.DataFrame(flat).to_csv(out_path, index=False, encoding='utf-8')
        return out_path

    def audit(self, df: pd.DataFrame, dataset_name: str) -> Dict[str, Any]:
        logging.info(f"🔍 Auditando: {dataset_name} ({len(df):,} filas)")
        report = {'dataset': dataset_name, 'total_rows': len(df), 'total_columns': len(df.columns),
                  'timestamp': pd.Timestamp.now().isoformat()}
        report['nulls'] = self._audit_nulls(df)
        report['duplicates'] = self._audit_duplicates(df)
        report['schema'] = self._audit_schema(df)
        report['domain'] = self._audit_domain(df)
        report['temporal'] = self._audit_temporal(df)
        report['numeric'] = self._audit_numeric_sanity(df)
        report['report_path'] = str(self._export_report(report, dataset_name))
        return report

    def audit_all(self, datasets_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        logging.info(f"🚀 Auditando {len(datasets_dict)} dataset(s) de forma integral...")
        results = [self.audit(df, name) for name, df in datasets_dict.items()]
        summary = [{
            'dataset': r['dataset'], 'rows': r['total_rows'],
            'cols_with_nulls': r['nulls']['total_columns_with_nulls'],
            'mirror_duplicates': r['duplicates']['exact_mirror_duplicates'],
            'schema_issues': len(r['schema']['type_mismatches']),
            'domain_violations': len(r['domain']['domain_violations']),
            'temporal_issues': len(r['temporal']['temporal_issues']),
            'numeric_issues': len(r['numeric']['numeric_sanity_issues']),
            'report_path': r['report_path']
        } for r in results]
        return pd.DataFrame(summary)