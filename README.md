[![Tests](https://img.shields.io/badge/tests-94%20passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Datos](https://img.shields.io/badge/datos-CC%20BY--SA%204.0-lightgrey)](https://creativecommons.org/licenses/by-sa/4.0/legalcode)
[![Sitio en vivo](https://img.shields.io/badge/demo-en%20vivo-success)](https://anaaguirreg.github.io/305-proyecto-intermedio-ia/)
[![Deploy](https://github.com/anaaguirreg/305-proyecto-intermedio-ia/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/anaaguirreg/305-proyecto-intermedio-ia/actions/workflows/deploy-pages.yml)

# Cicatrices Invisibles

### Índice de Cicatrices de Violencia de Género Femenino (ICV-GEN-F) en la Región Pacífico colombiana

**Concurso Datos al Ecosistema 2026 · Categoría Seguridad Ciudadana y Justicia**

Un proyecto de **Ana María Aguirre Guerrero** y **Jhonathan Rivera**.

> Hay historias que se transmiten de madres a hijas, y la violencia de género es una de ellas. Este proyecto conecta las cifras que el Estado colombiano mantiene por separado, para mostrar que cuidar a las niñas hoy es una forma de asegurar el bienestar de las mujeres del mañana.

**🔗 [Explorar el atlas en vivo](https://anaaguirreg.github.io/305-proyecto-intermedio-ia/)**

---

## Índice

1. [El problema](#el-problema)
2. [Justificación](#justificación)
3. [El índice ICV-GEN-F: qué mide y por qué](#el-índice-icv-gen-f-qué-mide-y-por-qué)
4. [Fuentes de datos](#fuentes-de-datos)
5. [Variables seleccionadas](#variables-seleccionadas)
6. [Tipo de análisis y modelo](#tipo-de-análisis-y-modelo)
7. [Resultados clave](#resultados-clave)
8. [Interpretación](#interpretación)
9. [Impacto potencial](#impacto-potencial)
10. [Solución en producción](#solución-en-producción-demo-en-vivo)
11. [Estructura del repositorio](#estructura-del-repositorio)
12. [Cómo reproducir el pipeline](#cómo-reproducir-el-pipeline)
13. [Documentación técnica](#documentación-técnica)
14. [Licencia](#licencia)
15. [Equipo](#equipo)
16. [Enlaces de acceso](#enlaces-de-acceso)

---

## El problema

En Chocó, Cauca, Nariño y Valle del Cauca la violencia intrafamiliar y sexual contra niñas y mujeres se documenta en registros institucionales separados (Policía Nacional y Medicina Legal) que nunca se cruzan entre sí. El resultado es que hoy **no existe un sistema que permita clasificar municipios por perfil de riesgo** ni priorizar territorios para intervención preventiva antes de que los casos escalen.

Además, la violencia contra niñas y la violencia contra mujeres adultas suelen analizarse como fenómenos separados, cuando en el territorio son parte de un mismo patrón: una niña agredida en su hogar es, con frecuencia, la mujer agredida mañana, muchas veces en el mismo municipio y por su propio entorno. A este patrón lo llamamos **continuo multigeneracional**, y es la hipótesis central que estructura el proyecto.

## Justificación

*Cicatrices Invisibles* responde a esta brecha integrando datos abiertos de violencia intrafamiliar, violencia sexual y caracterización forense, aplicando inteligencia artificial para clasificar los 179 municipios de la Región Pacífico por perfil de severidad, y produciendo un atlas interactivo orientado a tomadores de decisión en seguridad ciudadana y justicia.

**Beneficiarios directos:** Comisarías de Familia, ICBF Regional Pacífico, las Gobernaciones de Valle del Cauca, Cauca, Nariño y Chocó, y los equipos de política pública de género de las alcaldías.

**Beneficiarias indirectas:** las niñas, adolescentes y mujeres de los municipios críticos, cuyo riesgo hoy es invisible en los sistemas oficiales de información porque ningún sistema cruza estas fuentes.

## El índice ICV-GEN-F: qué mide y por qué

El **Índice Compuesto de Violencia de Género – Femenino (ICV-GEN-F)** es una medida que construimos específicamente para este proyecto. Resume en un solo número, entre 0 y 100, qué tan severa es la violencia contra niñas y mujeres en cada municipio de la Región Pacífico.

**¿Por qué hace falta un índice nuevo?** Porque la violencia de género no es un evento aislado. Es un patrón que se repite a lo largo de la vida de una mujer: empieza en la infancia y persiste en la adultez. Una niña agredida en su hogar hoy es, con frecuencia, la mujer agredida mañana — en el mismo municipio, a veces por el mismo entorno. Lo llamamos **continuo multigeneracional**.

**¿Qué mide exactamente?** El índice combina cuatro tasas — los cuatro rostros del continuo — calculadas por cada 100.000 habitantes femeninas:

* Violencia intrafamiliar contra niñas y adolescentes (peso 30%)
* Violencia sexual contra niñas y adolescentes (peso 30%)
* Violencia intrafamiliar contra mujeres adultas (peso 25%)
* Violencia sexual contra mujeres adultas (peso 15%)

El 60% del peso lo lleva la violencia contra niñas y adolescentes. Es una decisión metodológica: la violencia contra menores es la más invisibilizada, y la que marca el resto de la vida. Si el indicador no la jerarquiza, está midiendo otra cosa.

Detalle del cálculo (normalización, fórmula ponderada, tabla de clustering derivada) en [`docs/marco_metodologico.md`](docs/marco_metodologico.md).

## Fuentes de datos

**Datasets de datos.gov.co (4):**

| ID | Dataset | Fuente | Período | Enlace |
| :---- | :---- | :---- | :---- | :---- |
| DS1 | Violencia intrafamiliar | Policía Nacional | 2018–2025 | [datos.gov.co/d/vuyt-mqpw](https://www.datos.gov.co/d/vuyt-mqpw) |
| DS2 | Delitos sexuales | Policía Nacional | 2018–2025 | [datos.gov.co/d/fpe5-yrmw](https://www.datos.gov.co/d/fpe5-yrmw) |
| DS3 | Exámenes médico legales por presunto delito sexual | Instituto Nacional de Medicina Legal y Ciencias Forenses | 2018–2024 | [datos.gov.co/.../hyqu-diue](https://www.datos.gov.co/Justicia-y-Derecho/Ex-menes-m-dico-legales-por-presunto-delito-sexual/hyqu-diue/about_data) |
| DS4 | Violencia intrafamiliar, cifras definitivas | Instituto Nacional de Medicina Legal y Ciencias Forenses | 2018–2024 | [datos.gov.co/.../ers2-kerr](https://www.datos.gov.co/Justicia-y-Derecho/Violencia-intrafamiliar-Colombia-a-os-2015-a-2024-/ers2-kerr/about_data) |

**Dataset externo (1):**

| ID | Dataset | Fuente | Enlace |
| :---- | :---- | :---- | :---- |
| DANE | Serie municipal de población por área, sexo y edad 2018–2042 | DANE | [dane.gov.co — proyecciones de población](https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion) |

Detalle completo de cobertura, columnas y tratamiento de cada fuente en [`docs/fuentes_datos.md`](docs/fuentes_datos.md).

## Variables seleccionadas

El proyecto usa 5 datasets integrados en dos productos: la tabla maestra territorial (23 columnas, alimenta el índice y el modelo) y 12 tablas de caracterización forense (alimentan solo el dashboard, nunca el modelo). Variables principales:

| Categoría | Variable | Descripción |
| :---- | :---- | :---- |
| Territorial | `cod_municipio`, `municipio`, `departamento` | Llave de unión entre todas las fuentes |
| Temporal | `anio_hecho` | Período 2018–2025 (2018–2024 para las fuentes forenses) |
| Tasas (×100k mujeres) | `tasa_vif_nna_f`, `tasa_vif_adultas_f`, `tasa_sexual_nna_f`, `tasa_sexual_adultas_f` | Las 4 tasas femeninas que alimentan el índice |
| Brechas de género | `brecha_vif_nna`, `brecha_vif_adultas`, `brecha_sexual_nna`, `brecha_sexual_adultas` | Ratio tasa femenina / tasa masculina |
| Índice compuesto | `icv_gen_f` | Score 0–1 (0–100 en el dashboard), ponderado sobre las 4 tasas |
| Modelo | `cluster_kmeans` | Perfil de severidad asignado por K-Means (Alta / Moderada-baja) |
| Forense (Carril B) | `agresor`, `escenario`, `factor` / `circunstancia`, `etnia`, `discapacidad` | Caracterización cualitativa — nunca entran al índice ni al modelo |

**Total: 20 variables** — dentro del máximo permitido para el nivel Intermedio del concurso.

Diccionario completo de variables, tipos y reglas de derivación en [`docs/data_dictionary.md`](docs/data_dictionary.md).

## Tipo de análisis y modelo

**Tipo de análisis:** descriptivo (tasas, brechas de género, caracterización forense) + no supervisado (clustering) con un clasificador supervisado de apoyo para explicabilidad.

**Modelo utilizado:**

- **K-Means (k=2)** sobre las 4 tasas femeninas normalizadas (log1p + RobustScaler), para clasificar los 177 municipios de la Región Pacífico en dos perfiles de severidad. Se excluyen 2 municipios de Chocó (subregistro estructural) del universo de clustering.
- **Regresión Logística** como clasificador de explicabilidad sobre las etiquetas de cluster: se comparó contra varios algoritmos (incluido SVM con kernel RBF) mediante validación cruzada estratificada; ante un empate técnico de desempeño se eligió Regresión Logística por su interpretabilidad, parsimonia y coherencia con el índice lineal ICV-GEN-F.

Explicación completa de la metodología en [`docs/marco_metodologico.md`](docs/marco_metodologico.md).

## Resultados clave

- De los **177 municipios** evaluados por el modelo, **107 (~60%)** se clasifican en severidad **Alta** — la mayoría del territorio, no una minoría marginal.
- **Pasto (Nariño)** y **Popayán (Cauca)** — las dos capitales departamentales de la muestra — registran los ICV-GEN-F más altos de la región.
- **Cauca** presenta la brecha de género más amplia de la región: por cada hombre víctima de violencia, casi **5 mujeres** son víctimas.
- La brecha de género se ha reducido con los años, pero no porque la violencia contra las mujeres haya disminuido — es porque ha crecido el número de reportes de víctimas de sexo masculino (ver Interpretación).
- Cerca del **50%** de las víctimas de delito sexual son menores de 14 años.
- **Policarpa (Nariño)** presenta coexistencia alta de violencia intrafamiliar y sexual. En **Caloto (Cauca)** predomina la violencia intrafamiliar; en **Argelia (Cauca)**, la violencia sexual.
- Buena parte del Chocó profundo y las zonas costeras de Cauca y Nariño aparecen clasificadas como "Moderada/Baja" — no porque la violencia sea menor, sino por barreras geográficas, control territorial de grupos armados ilegales y desertificación institucional que inhiben la denuncia.
- El agresor cambia con la edad de la víctima: en la primera infancia es el cuidador; en la adolescencia, el padrastro; en la adultez, la pareja o expareja — evidencia del patrón de "antorcha" intergeneracional que motiva el enfoque del proyecto.
- La VIF ocurre con mayor frecuencia los domingos; la violencia sexual, los martes, con octubre como el mes de mayor incidencia.

## Interpretación

El ICV-GEN-F no es una predicción ni una sentencia sobre los municipios: es una fotografía comparativa que permite priorizar dónde el patrón de violencia contra niñas y mujeres es más severo. La clasificación "Moderada/Baja" de buena parte del Pacífico rural debe leerse con cautela: en varios casos refleja subregistro estructural (control armado, ausencia institucional), no ausencia real de violencia — esta limitación se documenta explícitamente en el dashboard y en `docs/conclusiones.md`.

La comparación entre fuentes policiales (más VIF) y forenses (más subregistro en violencia sexual de mujeres adultas) sugiere que la visibilidad de un tipo de violencia no equivale a su magnitud real: la revictimización institucional y el tabú social elevan la barrera de denuncia específicamente para la violencia sexual en mujeres adultas.

La tendencia decreciente de la brecha de género es un ejemplo del riesgo de leer los datos sin contexto: a simple vista podría interpretarse como una mejora en la situación de las mujeres, cuando en realidad refleja un aumento en el reporte de víctimas de sexo masculino, no una reducción de la violencia femenina. Que un municipio como Pasto o Popayán encabece el ranking del ICV-GEN-F tampoco es un dato menor: la mayor severidad no está confinada a la periferia rural, también aparece en las capitales con mayor capacidad institucional de registro.

## Impacto potencial

**¿A quién beneficia?**
Directamente: funcionarios de Comisarías de Familia, equipos del ICBF Regional Pacífico, Gobernaciones de Valle del Cauca, Cauca, Nariño y Chocó, y equipos de política pública de género de las alcaldías municipales. Indirectamente: niñas, adolescentes y mujeres de los municipios identificados como críticos, cuyas condiciones de riesgo hoy son invisibles en los sistemas de información oficiales.

**¿Qué problema ayuda a visibilizar?**
El proyecto visibiliza que la violencia intrafamiliar y sexual contra mujeres de todas las edades no es un problema urbano concentrado en las capitales — es un fenómeno que se repite con igual o mayor intensidad en municipios intermedios de la Región Pacífico que históricamente reciben menos recursos de intervención.

**¿Cómo puede apoyar la prevención?**
Al clasificar municipios por perfil de riesgo y caracterizar el tipo de agresor, el escenario y el factor desencadenante predominante, el proyecto permite diseñar intervenciones específicas en lugar de intervenciones uniformes. Un municipio donde el agresor predominante es el padre y los hechos ocurren en la vivienda requiere una estrategia diferente a uno donde el agresor es la pareja y los hechos ocurren en espacios públicos.

**¿Cómo puede orientar decisiones de política pública?**
El ICV-GEN-F y los clusters de K-Means producen un ranking de municipios que puede usarse directamente como criterio de focalización para programas como Familias en su Tierra, Rutas de Atención Integral a Víctimas de VBG, y despliegue de Comisarías Móviles en zonas sin sede permanente.

**¿Qué valor agrega frente a un análisis descriptivo tradicional?**
Un análisis descriptivo tradicional muestra cuántos casos hay. *Cicatrices Invisibles* muestra dónde están los municipios donde el riesgo es estructural y no coyuntural, qué tipo de violencia coexiste, quién la ejerce, y qué tan urgente es la intervención — todo en una sola herramienta, por primera vez en la región.

**¿Por qué es relevante para la Región Pacífico específicamente?**
La Región Pacífico concentra algunas de las brechas de seguridad más profundas de Colombia: Chocó y Cauca tienen presencia limitada de instituciones de protección, alta proporción de comunidades étnicas con vulnerabilidad interseccional, y contextos de conflicto armado que amplifican la violencia doméstica. Ningún análisis territorial con enfoque de género existe hoy para esta región como conjunto.

## Solución en producción (demo en vivo)

Para ver y probar la solución funcionando en tiempo real:

**Aplicación web:** [Visitar el atlas en vivo](https://anaaguirreg.github.io/305-proyecto-intermedio-ia/)

El sitio es 100% estático (HTML/CSS/JS + Leaflet + Apache ECharts), sin backend ni contenedor: no aplican Docker Hub ni documentación de API para este proyecto.

## Estructura del repositorio

```
305-proyecto-intermedio-ia/
│
├── RECURSOS/                                    # Material de presentación (pendiente — se agrega cuando esté lista)
│   ├── Presentacion.pptx
│   ├── presentacion.pdf
│   └── portada.png
│
├── README.md                                    # Este archivo
├── LICENSE                                      # MIT (código). Los 4 datasets fuente están bajo CC BY-SA 4.0
├── .gitignore                                   # Excluye data/raw/ (527MB), docs/_internal/, .venv/, .pytest_cache/, etc.
├── pyproject.toml                                # Dependencias y metadata del proyecto (Python)
│
├── .github/
│   └── workflows/
│       └── deploy-pages.yml                     # Despliega site/ a GitHub Pages en cada push a main; remueve test_render_*.html antes de publicar
│
├── docs/                                        # Documentación técnica de cara al jurado
│   ├── planteamiento_problema.md                # Definición del problema y preguntas analíticas
│   ├── marco_metodologico.md                    # Resumen ejecutivo de la metodología CRISP-ML(Q) + Scrum
│   ├── fuentes_datos.md                         # Las 5 fuentes con enlaces verificables
│   ├── data_dictionary.md                       # Diccionario completo de variables
│   ├── architecture.md                          # Diagrama de arquitectura de los dos carriles
│   ├── conclusiones.md                          # Hallazgos, limitaciones, próximos pasos
│   ├── validation_guide.md                      # Guía para que pares validen los resultados
│   ├── mapeo_estructural_raw.csv                # Fotografía estructural pre-transformación (MetadataMapper)
│   ├── auditoria_{dataset}.csv                  # Reportes de auditoría de calidad por dataset (DataAuditor)
│   ├── validacion_capas_pre_join.csv            # Validación cruzada de las 8 capas vs. totales limpios
│   ├── pre_registro_kmeans.md                   # Pre-registro del modelo, reconciliado con la corrida real
│   └── _internal/                               # Auditorías internas de fase — excluido del repo público
│
├── config/                                      # Toda regla de negocio vive aquí, no en el código
│   ├── mapping_config.json                      # Alias de columnas, taxonomías, tipos (etapas 1–6)
│   ├── base_config.json                         # Paths y display_config compartidos
│   ├── master_builder_config.json               # Pesos del ICV-GEN-F, reglas de agregación y validación (etapas 7–9)
│   ├── forense_analyzer_config.json             # Definición de las 12 tablas forenses (Carril B)
│   ├── ml_config.json                           # Hiperparámetros de K-Means y del clasificador (etapa 11)
│   ├── municipios_pacifico.json                 # Referencia geográfica DANE/DIVIPOLA — 179 municipios
│   ├── master_exporter_config.json              # Config de exportación .parquet → .json (tabla maestra)
│   └── forense_exporter_config.json             # Config de exportación .parquet → .json (tablas forenses)
│
├── data/                                        # data/raw/ excluido del repo vía .gitignore (527MB, supera límite de GitHub)
│   ├── raw/                                     # ds1_violencia.csv · ds2_sexuales.csv · dane_poblacion.xlsx · ds4_forense.csv · ds3_seforense.csv (no versionados)
│   ├── segmented/                               # Datasets filtrados a Región Pacífico 2018–2025 (.parquet)
│   ├── cleaned/                                 # violencia_limpio (68.052) · sexuales_limpio (34.592) · forense_limpio (15.418) · seforense_limpio (18.661) · poblacion_limpio (4.296)
│   ├── agregados_forense/                       # 6 tablas derivadas de DS4 (VIF forense)
│   ├── agregados_seforense/                     # 6 tablas derivadas de DS3 (sexual forense)
│   └── master/                                  # maestro_concurso.parquet (1.432×23) · tabla_clustering.parquet (179×16) · tabla_clustering_final.parquet
│
├── notebooks/                                   # Experimentación y pipeline documentado
│   ├── 00_ETL_pipeline.ipynb                    # Pipeline completo — etapas 1 a 9 en secuencia (pipeline "vivo")
│   ├── 01_diagnostico_estadistico.ipynb         # Diagnóstico estadístico post-ETL
│   ├── 02_sensibilidad_pesos_icv.ipynb          # Análisis de sensibilidad de los pesos del ICV-GEN-F
│   ├── 03_ml_entrenamiento.ipynb                # Etapa 11 — K-Means + benchmark de clasificadores + exportación de modelo
│   └── 04_Caracterizacion_forense.ipynb         # Etapa 10 — ForenseAnalyzer (DS3/DS4 → 12 tablas)
│
├── src/                                         # Pipeline modularizado — 100% config-driven, cero parámetros de negocio en Python
│   ├── DataLoader                               # Ingesta cruda, cero transformación
│   ├── MetadataMapper                           # Fotografía estructural pre-transformación
│   ├── DataStandardizer                         # Estandarización vectorial (renombrado, tipos, taxonomías, geo-validación)
│   ├── DataSegmenter                            # Filtro territorial (Región Pacífico) + temporal (2018–2025)
│   ├── DataAuditor                              # Auditoría de calidad — observa, nunca transforma
│   ├── DataCleaner                              # Deduplicación + imputación, 100% JSON-driven
│   ├── DataAggregator                           # Construcción de las 8 capas analíticas A–H
│   ├── LayerValidator                           # Validación cruzada de capas vs. totales limpios
│   ├── DataMasterBuilder                        # Esqueleto territorial + JOINs + tasas + ICV-GEN-F
│   ├── ForenseAnalyzer                          # 12 tablas de caracterización forense (Carril B)
│   ├── MasterExporter                           # .parquet → .json para el frontend (tabla maestra)
│   ├── ModelExporter                            # .parquet → .json (resultados de clustering/clasificador)
│   └── ForenseExporter                          # .parquet → .json (tablas forenses)
│
├── models/
│   ├── final_predictor.pkl                      # Clasificador de explicabilidad (Regresión Logística), entrenado sobre el 100% de los 177 municipios
│   └── predictor_metadata.json                  # Metadatos del modelo consumidos por el dashboard
│
├── schema/ y schemas/                           # Esquemas de validación — ambas vigentes, referenciadas por código distinto (actos 1–4 vs. acto 5)
│
├── scripts/
│   └── sync_to_site.sh                          # Sincroniza los JSON canónicos + configs hacia site/, con verificación md5
│
├── site/                                        # Artefacto estático autocontenible, desplegado en GitHub Pages
│   ├── index.html + assets/                     # Dashboard (Leaflet + Apache ECharts)
│   ├── data/ · config/                          # Copias sincronizadas — nunca editar directamente, se regeneran con sync_to_site.sh
│   └── test_render_*.html                       # Contratos de paridad visual — no se publican, se remueven en el deploy
│
└── tests/                                       # 94 tests en verde
    ├── test_site_data_sync.py                   # 12 tests — previenen drift entre las fuentes canónicas y site/
    └── ...                                       # 82 tests adicionales: limpieza, agregación, tabla maestra, modelo, exportadores
```

## Cómo reproducir el pipeline

```bash
# 1. Entorno
source .venv/bin/activate
pip install -e .   # necesario para que los notebooks importen desde src/

# 2. Ejecutar el pipeline en orden
#    notebooks/00_ETL_pipeline.ipynb        → etapas 1–9 (tabla maestra)
#    notebooks/04_Caracterizacion_forense.ipynb → etapa 10 (tablas forenses)
#    notebooks/03_ml_entrenamiento.ipynb    → etapa 11 (K-Means + clasificador)

# 3. Sincronizar salidas hacia el sitio estático
bash scripts/sync_to_site.sh
pytest tests/test_site_data_sync.py -v

# 4. Verificar el sitio localmente (no usar Live Server — genera falsos positivos de CSP)
python -m http.server 8000
```

## Documentación técnica

| Documento | Contenido |
| :---- | :---- |
| [`docs/planteamiento_problema.md`](docs/planteamiento_problema.md) | Problema, preguntas analíticas, evidencia exploratoria |
| [`docs/marco_metodologico.md`](docs/marco_metodologico.md) | Metodología CRISP-ML(Q) + Scrum completa |
| [`docs/fuentes_datos.md`](docs/fuentes_datos.md) | Detalle de las 5 fuentes de datos |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | Diccionario completo de variables |
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura de los dos carriles del pipeline |
| [`docs/conclusiones.md`](docs/conclusiones.md) | Hallazgos, limitaciones y próximos pasos |
| [`docs/validation_guide.md`](docs/validation_guide.md) | Guía para que pares validen los resultados |

## Licencia

- **Código:** [MIT](LICENSE).
- **Datasets fuente:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode) (datos.gov.co / DANE).

## Equipo

| | |
| :---- | :---- |
| **Ana María Aguirre Guerrero** — PhD en Ingeniería | Ingeniería de Datos BI, Developer · [LinkedIn](https://www.linkedin.com/in/ana-maria-aguirre-guerrero) |
| **Jhonathan Rivera** — PhD en Ingeniería | Data Scientist, Ingeniero de Datos · [LinkedIn](https://www.linkedin.com/in/jhonathan-fernando-rivera-ingenieria-de-materiales/) |

## Enlaces de acceso

Enlaces de acceso para GitHub:

* **Repositorio:** [github.com/anaaguirreg/305-proyecto-intermedio-ia](https://github.com/anaaguirreg/305-proyecto-intermedio-ia)
* **Sitio en vivo:** [anaaguirreg.github.io/305-proyecto-intermedio-ia](https://anaaguirreg.github.io/305-proyecto-intermedio-ia/)
* **Presentación (PPTX/PDF):** se agrega en `RECURSOS/` 
