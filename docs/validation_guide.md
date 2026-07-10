# Guía de Validación

Esta guía permite a un par evaluador verificar de forma independiente las afirmaciones metodológicas y los resultados de *Cicatrices Invisibles*, sin depender de la palabra del equipo. Está organizada en cuatro niveles, de menor a mayor esfuerzo.

## Nivel 1 — Verificación sin ejecutar código (~5 minutos)

| # | Verificación | Cómo | Resultado esperado |
| :---- | :---- | :---- | :---- |
| 1 | El sitio está en producción | Visitar [anaaguirreg.github.io/305-proyecto-intermedio-ia](https://anaaguirreg.github.io/305-proyecto-intermedio-ia/) | El dashboard carga y los 5 módulos son navegables |
| 2 | El repositorio es público | Visitar [github.com/anaaguirreg/305-proyecto-intermedio-ia](https://github.com/anaaguirreg/305-proyecto-intermedio-ia) | Accesible sin necesidad de inicio de sesión |
| 3 | Las 4 fuentes de datos.gov.co existen | Abrir los 4 enlaces listados en [`fuentes_datos.md`](fuentes_datos.md) | Cada enlace resuelve a un dataset activo en el portal |
| 4 | La fuente DANE existe | Abrir el enlace de DANE en [`fuentes_datos.md`](fuentes_datos.md) | Resuelve a la página oficial de proyecciones de población |
| 5 | Licencia declarada | Ver `LICENSE` en la raíz del repositorio | MIT (código) |
| 6 | Cero parámetros de negocio hardcodeados | Buscar los pesos del ICV-GEN-F (`0.30`, `0.25`, `0.15`) en el código Python de `src/` | No deberían aparecer en `.py` — solo en `config/master_builder_config.json` |

## Nivel 2 — Verificación ejecutando el pipeline (~30–60 minutos)

Requiere clonar el repositorio y seguir los pasos de [`README.md § Cómo reproducir el pipeline`](../README.md#cómo-reproducir-el-pipeline).

| # | Paso | Cómo | Resultado esperado |
| :---- | :---- | :---- | :---- |
| 1 | Entorno instalado | `source .venv/bin/activate && pip install -e .` | Sin errores |
| 2 | Tests de sincronización del sitio | `pytest tests/test_site_data_sync.py -v` | 12 tests en verde |
| 3 | Conteos post-limpieza | Revisar `data/cleaned/*.parquet` (o correr `notebooks/00_ETL_pipeline.ipynb`) | DS1 = 68.052 · DS2 = 34.592 · DANE = 4.296 · DS4 = 15.418 · DS3 = 18.661 |
| 4 | Tabla maestra | `data/master/maestro_concurso.parquet` | 1.432 filas (179 municipios × 8 años) × 23 columnas |
| 5 | Tabla de clustering | `data/master/tabla_clustering.parquet` | 179 filas |
| 6 | Exclusión documentada del K-Means | `data/master/tabla_clustering_final.parquet` | 177 filas — no incluye los códigos 27150 ni 27493 |
| 7 | Sitio local (sin falsos positivos de CSP) | `python -m http.server 8000` desde la raíz — **no usar Live Server** | El dashboard renderiza igual que en producción |

## Nivel 3 — Verificación de la metodología (lectura dirigida)

| Afirmación a verificar | Dónde está documentada |
| :---- | :---- |
| Fórmula y pesos del ICV-GEN-F | [`README.md § El índice ICV-GEN-F`](../README.md#el-índice-icv-gen-f-qué-mide-y-por-qué) + [`marco_metodologico.md § 5.2.5`](marco_metodologico.md) |
| Por qué se excluyen los municipios 27150 y 27493 | [`marco_metodologico.md § 7.1`](marco_metodologico.md) + `docs/pre_registro_kmeans.md` |
| Por qué Regresión Logística y no otro clasificador | [`marco_metodologico.md § 7.1.1`](marco_metodologico.md) — benchmark contra SVM RBF, empate técnico |
| Por qué DS3/DS4 nunca entran a la tabla maestra ni al modelo | [`fuentes_datos.md`](fuentes_datos.md) — regla de oro |
| Extensión interseccional de julio 2026 (sub-acto 4.5) | [`marco_metodologico.md § 6.5`](marco_metodologico.md) |
| Las 20 variables del proyecto y su derivación | [`data_dictionary.md`](data_dictionary.md) |

## Nivel 4 — Verificación de cifras del dashboard

Las cifras citadas en [`README.md § Resultados clave`](../README.md#resultados-clave) son directamente observables en el sitio en vivo, sin necesidad de ejecutar código:

| Cifra | Dónde verificarla en el dashboard |
| :---- | :---- |
| 107 de 177 municipios en severidad Alta | Acto 1 — Panorama territorial, stat cards regionales + choropleth |
| Pasto y Popayán con el ICV-GEN-F más alto | Acto 1 — ranking top-10 por ICV |
| Brecha de género de Cauca (~5:1) | Acto 2 — Brechas de género, mapa departamental |
| ~50% de víctimas de delito sexual menores de 14 años | Acto 3 — Tipología del delito |
| Patrón del agresor por ciclo de vida | Acto 4 — Anatomía forense, Sankey del agresor |

## Si encuentras una discrepancia

Esta guía asume que la validación puede revelar diferencias entre lo documentado y lo observado — es su propósito. Cualquier discrepancia entre estas tablas y el estado real del repositorio o del sitio en vivo puede reportarse abriendo un *Issue* en el repositorio de GitHub, indicando el número de verificación (Nivel–#) que falló.
