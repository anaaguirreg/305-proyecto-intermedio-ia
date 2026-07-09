import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class LayerValidator:
    """Validación cruzada pre-JOIN. Fail-fast, vectorial, 100% JSON-driven."""

    def __init__(self, config_path: str):
        cfg = Path(config_path).resolve()
        if not cfg.exists(): raise FileNotFoundError(f"❌ Config no encontrado: {cfg}")

        # Carga en cascada idéntica al resto del pipeline
        base_path = cfg.parent / "base_config.json"
        base_cfg = {}
        if base_path.exists():
            with open(base_path, 'r', encoding='utf-8') as f: base_cfg = json.load(f)
        with open(cfg, 'r', encoding='utf-8') as f:
            spec_cfg = json.load(f)
        self.config = {**base_cfg, **spec_cfg}
        self.project_root = cfg.parent.parent

        self.rules = self.config.get('validation_rules', {})
        self.tolerance = self.rules.get('tolerance_pct', 0.0)
        self.expected_years = set(self.rules.get('expected_years', []))
        self.exclude_values = self.rules.get('exclude_gender_values', [])
        self.layer_groups = self.rules.get('layer_groups', {})
        self.clean_sources = self.rules.get('clean_sources', {})

        self.cleaned_dir = (
                    self.project_root / self.config.get('paths', {}).get('cleaned_dir', 'data/cleaned')).resolve()
        self.docs_dir = (self.project_root / self.config.get('paths', {}).get('docs_dir', 'docs')).resolve()
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.output_filename = self.config.get('output_config', {}).get('validation_report_filename',
                                                                        'validacion_capas_pre_join.csv')

    def validate(self, layers_dict: Dict[str, pd.DataFrame], cleaned_datasets: Dict[str, pd.DataFrame]) -> Dict[
        str, Any]:
        report = {'status': 'PASS', 'checks': [], 'errors': [], 'timestamp': pd.Timestamp.now().isoformat()}

        # 🔍 1. Validación de Sumas vs Datasets Limpios
        for group_key, layer_names in self.layer_groups.items():
            source_key = self.clean_sources.get(group_key)
            if not source_key or source_key not in cleaned_datasets:
                report['status'] = 'FAIL'
                report['errors'].append(f"❌ {group_key}: Fuente limpia '{source_key}' no encontrada.")
                continue

            clean_df = cleaned_datasets[source_key]
            layer_sum = sum(layers_dict[l]['cantidad'].sum() for l in layer_names if l in layers_dict)

            mask_exclude = clean_df['genero_victima'].isin(
                self.exclude_values) if 'genero_victima' in clean_df.columns else pd.Series([False] * len(clean_df))
            clean_sum = clean_df.loc[~mask_exclude, 'cantidad'].sum() if 'cantidad' in clean_df.columns else 0

            diff_pct = abs(layer_sum - clean_sum) / clean_sum if clean_sum > 0 else 0.0
            status = 'PASS' if diff_pct <= self.tolerance else 'FAIL'
            msg = f"Suma {group_key}: {layer_sum} vs {clean_sum} (diff: {diff_pct:.2%})"

            report['checks'].append(
                {'check': 'SUMA_TOTALES', 'group': group_key, 'expected': clean_sum, 'actual': layer_sum,
                 'diff_pct': diff_pct, 'status': status, 'msg': msg})
            if status == 'FAIL':
                report['status'] = 'FAIL'
                report['errors'].append(f"❌ {msg}")

        # 🔍 2. Unicidad & Cobertura Temporal (por capa)
        for l_name, df in layers_dict.items():
            # Unicidad
            grp_cols = [c for c in ['cod_municipio', 'anio_hecho'] if c in df.columns]
            if grp_cols:
                max_dup = df.groupby(grp_cols).size().max()
                status = 'PASS' if max_dup <= 1 else 'FAIL'
                msg = f"{l_name}: Unicidad garantizada" if status == 'PASS' else f"{l_name}: Duplicados detectados (max={max_dup})"
                report['checks'].append({'check': 'UNICIDAD', 'layer': l_name, 'status': status, 'msg': msg})
                if status == 'FAIL': report['errors'].append(f"❌ {msg}"); report['status'] = 'FAIL'

            # Cobertura Temporal
            if 'anio_hecho' in df.columns:
                years_present = set(df['anio_hecho'].dropna().astype(int))
                missing = self.expected_years - years_present
                status = 'PASS' if not missing else 'FAIL'
                msg = f"{l_name}: Cobertura completa (2018-2025)" if status == 'PASS' else f"{l_name}: Faltan años {sorted(missing)}"
                report['checks'].append({'check': 'COBERTURA_TEMPORAL', 'layer': l_name, 'status': status, 'msg': msg})
                if status == 'FAIL': report['errors'].append(f"❌ {msg}"); report['status'] = 'FAIL'

        # 📊 Exportar reporte trazable
        pd.DataFrame(report['checks']).to_csv(self.docs_dir / self.output_filename, index=False, encoding='utf-8')
        logging.info(f"📄 Reporte exportado: {self.docs_dir / self.output_filename}")

        # 🛑 Fail-FAST explícito
        if report['status'] == 'FAIL':
            for e in report['errors']: logging.error(e)
            raise ValueError("🛑 Validación cruzada de capas FALLIDA. Revise docs/ y corrija antes de continuar.")

        logging.info("✅ Validación cruzada de capas: PASS. Pipeline continuando...")
        return report