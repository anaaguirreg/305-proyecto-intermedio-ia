**CICATRICES INVISIBLES**
*Índice de Cicatrices de Violencia de Género Femenino (ICV-GEN-F)*

**Documento Metodológico Integral**

Versión 3.3 — Arquitectura CRISP-ML(Q) + Scrum + GitHub Pages

Categoría: Seguridad Ciudadana y Justicia

Región: Pacífico Colombiano (Valle del Cauca, Cauca, Nariño, Chocó)

Período de análisis: 2018 – 2025

**Concurso: Datos al Ecosistema 2026**

# 1. Marco Metodológico: CRISP-ML(Q) + Scrum

## 1.1. Justificación del framework dual

El concurso Datos al Ecosistema 2026 exige documentar la metodología, preferiblemente bajo lineamientos CRISP-ML. El proyecto adopta CRISP-ML(Q) como marco técnico para gestionar el ciclo de vida del modelo de IA, complementado con Scrum como marco ágil para organizar la ejecución en sprints semanales. Son complementarios: CRISP-ML define el qué (fases técnicas), Scrum el cómo (cadencia de entrega iterativa).

## 1.2. Mapeo CRISP-ML(Q) al proyecto

| Fase CRISP-ML | Alcance en el proyecto | Estado | Sprints |
| :---- | :---- | :---- | :---- |
| 1. Comprensión del Negocio y Datos | Definición del problema, inventario de fuentes, criterios de éxito, KPIs, diccionario de variables | ✅ Completada | S1 |
| 2. Ingeniería de Datos | Pipeline ETL completo: carga, estandarización, segmentación, auditoría, limpieza, capas analíticas, tabla maestra, carriles paralelos DS3/DS4 | ✅ Completada | S2–S6 |
| 3. Ingeniería de Modelos de ML | K-Means (método del codo + Silhouette), benchmark de clasificadores supervisados para explicabilidad y selección de Logistic Regression | ✅ Completada | S7 |
| 4. Evaluación del Modelo | Validación de clusters (Silhouette, Bootstrap ARI), análisis de sensibilidad del ICV-GEN-F, validación cruzada geográfica | ✅ Completada | S7 |
| 5. Despliegue | MasterExporter/ModelExporter/ForenseExporter (.parquet → .json), sitio estático GitHub Pages con Leaflet + Apache ECharts, en producción | ✅ Completada | S8–S9 |
| 6. Monitoreo y Mantenimiento | Documentación de reentrenamiento, estrategia de actualización, observabilidad Prefect (diseño) | Fuera del alcance del concurso | — |

## 1.3. Estructura Scrum y avance del proyecto

**Duración del sprint:** 1 semana. **Período total:** 1 de mayo – 13 de julio de 2026 (11 sprints). **Equipo:** 2 personas.

| Sprint | Fechas | Entregable / Incremento | Estado |
| :---- | :---- | :---- | :---- |
| S1 | 01–04 may | Definición del proyecto, inventario de fuentes, descarga de 5 datasets, diccionario de variables inicial | ✅ |
| S2 | 05–11 may | DataLoader + MetadataMapper + DataStandardizer operativos. Configuración externa en mapping\_config.json | ✅ |
| S3 | 12–18 may | DataSegmenter (filtro territorial/temporal) + DataAuditor. Parquet segmentados y reporte de auditoría | ✅ |
| S4 | 19–25 may | DataCleaner JSON-driven operativo. 5 datasets limpios en data/cleaned/ | ✅ |
| S5 | 26 may–01 jun | DataAggregator: 8 capas analíticas (A–H) en RAM. Validación de conteos por capa | ✅ |
| S6 | 02–08 jun | Validación cruzada A–H. DataMasterBuilder: esqueleto + LEFT JOINs + tasas + brechas + ICV-GEN-F. Carriles DS3/DS4 completos | ✅ |
| S7 | 09–15 jun | K-Means + codo + Silhouette + benchmark de clasificadores (Logistic Regression). Análisis de sensibilidad. Modelo validado y pre-registro reconciliado con la corrida | ✅ |
| S8 | 16–22 jun | MasterExporter/ForenseExporter (.parquet → .json) completos. Estructura HTML/CSS/JS y módulos 1–3 (mapa coroplético Leaflet + gráficos ECharts) implementados | ✅ |
| S9 | 23–29 jun | Módulos 4–5 (caracterización forense + fichas municipales). Deploy GitHub Pages. Recomendaciones de prevención | ✅ |
| S10 | 30 jun–06 jul | Repositorio público en GitHub y despliegue automatizado (GitHub Actions) completos. Extensión interseccional étnica del sub-acto 4.5. Documentación CRISP-ML y README completos | ✅ |
| S11 | 07–13 jul | Revisión final contra criterios del concurso. Presentación. Entrega oficial | ✅ |

## 1.4. Roles del equipo

| Rol Concurso | Rol CRISP-ML / Scrum | Responsabilidades clave |
| :---- | :---- | :---- |
| Líder de datos y modelo Jhonathan Rivera | Data Scientist + Ingeniero de Datos / Product Owner – Scrum Master | ETL, tabla maestra, modelo K-Means, repositorio GitHub |
| Análisis y comunicación Ana Maria Aguirre G | Ingeniero de Datos BI / Developer | Pipeline DS3/DS4, visualizaciones Leaflet/ECharts, sitio GitHub Pages, documentación |

# 2. Inventario de Fuentes de Datos

El proyecto integra 5 datasets de 3 fuentes institucionales con roles diferenciados. Las fuentes policiales (DS1, DS2) alimentan el modelo cuantitativo; las fuentes forenses (DS3, DS4) alimentan la caracterización cualitativa del dashboard.

| ID | Dataset | Fuente | Filas limpias | Columnas | Carril |
| :---- | :---- | :---- | :---- | :---- | :---- |
| DS1 | Violencia intrafamiliar | Policía Nacional | 68.052 | 10 | Principal → Tabla maestra |
| DS2 | Delitos sexuales | Policía Nacional | 34.592 | 11 | Principal → Tabla maestra |
| DANE | Proyecciones población | DANE | 4.296 | 10 | Principal → Denominadores |
| DS4 | Forense VIF | Medicina Legal | 15.418 | 21 | Paralelo → Dashboard |
| DS3 | Forense delito sexual | Medicina Legal | 18.661 | 21 | Paralelo → Dashboard |

**Regla metodológica:** DS3 y DS4 nunca entran a la tabla maestra ni al modelo de IA. Su función exclusiva es alimentar las fichas municipales y la narrativa de caracterización. Esto protege la integridad del ICV-GEN-F, cuyas tasas dependen solo de conteos policiales normalizados por población DANE.

**Limitación documentada:** DS3 y DS4 (Medicina Legal) cubren hasta 2024; DS1 y DS2 (Policía Nacional) hasta 2025. Las fichas alimentadas por datos forenses tendrán un año menos de cobertura. La asimetría responde a los ciclos de publicación institucionales y no afecta la tabla maestra ni el modelo.

# 3. Arquitectura General del Pipeline

## 3.1. Dos carriles, dos productos

**Producto 1 — Tabla maestra territorial (master\_table.parquet):** tabla a nivel municipio × año que integra DS1 + DS2 + DANE con tasas normalizadas, brechas de género y el índice compuesto ICV-GEN-F (1.432 filas × 23 columnas). De ella se deriva tabla\_clustering.parquet (179 filas × 16 columnas), insumo directo del K-Means.

**Producto 2 — Tablas de caracterización forense (12 tablas .parquet):** 6 derivadas de DS4 (VIF forense) + 6 derivadas de DS3 (sexual forense). Caracterizan perfil del agresor, escenario, factores/circunstancias, temporalidad e interseccionalidad. Alimentan las fichas municipales del dashboard.

Ambos productos convergen, ya exportados a JSON, en `site/`: un artefacto estático autocontenible que se sirve directamente desde GitHub Pages (ver §7.3).

## 3.2. Flujo del Carril Principal

* **Paso 0 →** mapping\_config.json (configuración externa)

* **Paso 1 →** DataLoader (ingesta cruda, cero transformación)

* **Paso 2 →** MetadataMapper (fotografía estructural)

* **Paso 3 →** DataStandardizer (estandarización vectorial)

* **Paso 4 →** DataSegmenter (filtro territorial + temporal)

* **Paso 5 →** DataAuditor (auditoría integral de calidad)

* **Paso 6 →** DataCleaner (deduplicación + imputación)

* **Paso 7 →** DataAggregator (8 capas analíticas A–H)

* **Paso 8 →** Validación cruzada (sumas de capas vs. totales limpios)

* **Paso 9 →** DataMasterBuilder (esqueleto + JOINs + tasas + ICV-GEN-F)

* **Paso 10 →** MasterExporter (.parquet → .json optimizados para frontend)

**Modelado (Fase 3, aguas abajo del Paso 9):** tabla\_clustering.parquet → K-Means (k=2, log1p + RobustScaler, N=177) → clasificador supervisado (Logistic Regression) → etiquetas de cluster y artefactos de modelo (ModelExporter).

## 3.3. Flujo de los Carriles Paralelos (DS3, DS4)

Raw → DataLoader → DataStandardizer → DataSegmenter → DataAuditor → DataCleaner → ForenseAnalyzer → 6 tablas .parquet por dataset → ForenseExporter → .json para frontend. Los carriles paralelos comparten los módulos del pipeline principal (Pasos 1–6) pero generan productos independientes; nunca cruzan datos con el carril principal ni entre sí.

## 3.4. Principio de configuración externa

Todas las reglas de negocio viven en archivos JSON de configuración. El código Python no contiene parámetros de negocio hardcodeados: cambiar la región, el período, los pesos del ICV-GEN-F o las taxonomías requiere editar el JSON, no el código. Un auditor puede revisar las reglas sin leer Python.

# 4. Metodología Ejecutada — Pasos 0 a 7

## 4.1. Paso 0 — Configuración externa (mapping\_config.json)

Centraliza todas las reglas de negocio, alias de columnas, valores válidos, taxonomías, pesos del índice y rutas en archivos JSON. Criterio de diseño: cero parámetros de negocio en Python; todo cambio metodológico se documenta como cambio en el JSON.

## 4.2. Paso 1 — Ingesta pura (DataLoader)

Carga los 5 archivos fuente en memoria tal como vienen, sin transformación, para preservar la trazabilidad del dato crudo. Los CSV se leen con dtype string para evitar inferencia automática; el DANE (.xlsx) se lee manejando el MultiIndex de las 300+ columnas de edad. DataLoader no renombra, no filtra y no castea.

## 4.3. Paso 2 — Fotografía estructural (MetadataMapper)

Genera una radiografía del dato antes de cualquier transformación: dimensiones, tipos, distribución de nulos, valores únicos y memoria estimada. Sirve como línea base para comparar el antes y el después del pipeline.

## 4.4. Paso 3 — Estandarización vectorial (DataStandardizer)

Transforma los 5 DataFrames crudos en una estructura canónica uniforme. Subprocesos en orden:

* Renombrado de columnas vía column\_aliases (cada variante cruda → forma canónica snake\_case).

* Composición de fecha\_hecho para DS3/DS4 (se sintetiza como {año}-01-01 para compatibilidad con las máscaras de segmentación temporal).

* Casteo de tipos según type\_rules (category, Int32, string, datetime64).

* Normalización de valores: mayúsculas, eliminación de acentos y limpieza de caracteres especiales por regex.

* Validación geográfica: cruce de cod\_municipio contra la referencia DANE/DIVIPOLA; etiquetado de códigos sin match como CODIGO\_MAL\_REGISTRADO.

* Aplicación de taxonomías dinámicas (dimension\_delito, dimension\_agresor, dimension\_escenario, dimension\_circunstancia, etc.).

* Derivación temporal (anio\_hecho, mes\_hecho, dia\_hecho) para DS1 y DS2.

* Agregación de bandas etarias DANE: colapso de 300+ columnas en pob\_f\_0\_17, pob\_f\_18\_mas, pob\_h\_0\_17, pob\_h\_18\_mas y totales por sexo.

## 4.5. Paso 4 — Segmentación territorial y temporal (DataSegmenter)

Filtra los 5 datasets a la Región Pacífico (Valle del Cauca, Cauca, Nariño, Chocó) en 2018–2025 mediante filtro AND estricto (departamento ∈ objetivo Y año ∈ rango). Los DataFrames segmentados se persisten en .parquet (Snappy): primer checkpoint persistente del pipeline.

## 4.6. Paso 5 — Auditoría integral de calidad (DataAuditor)

Diagnostica el estado de calidad de cada dataset segmentado sin modificar los datos. Dimensiones auditadas: nulos (conteo y %), duplicados exactos y parciales, dominio de valores categóricos, consistencia temporal y estadísticas numéricas básicas. Principio no negociable: el auditor observa, nunca transforma; las decisiones de resolución pertenecen al DataCleaner.

## 4.7. Paso 6 — Limpieza (DataCleaner)

La implementación usa una clase única DataCleaner 100% JSON-driven que procesa los 5 datasets sin lógica condicional por dataset: todo el comportamiento diferenciado se parametriza en cleaning\_config, column\_selection e imputation\_rules. Operaciones, en orden:

* **Deduplicación (primero):** máscara vectorial de duplicados exactos (keep='first') sobre todas las columnas originales; las filas eliminadas se exportan a cuarentena para trazabilidad total; activable/desactivable desde el JSON.

* **Selección de columnas (después):** se conservan solo las columnas declaradas en column\_selection; las ausentes se omiten con WARNING. Optimiza el consumo de RAM.

* **Imputación vectorial (al final):** según imputation\_rules, con soporte seguro para dtype=category (add\_categories antes de fillna) y regla opcional negative\_to\_zero.

Resultados post-cleaner por dataset:

| Dataset | Fuente | Filas salida | Columnas | Años cubiertos |
| :---- | :---- | :---- | :---- | :---- |
| DS1 — Violencia | Policía Nacional | 68.052 | 10 | 2018–2025 (8) |
| DS2 — Sexuales | Policía Nacional | 34.592 | 11 | 2018–2025 (8) |
| DANE — Población | DANE | 4.296 | 10 | 2018–2025 (8) |
| DS4 — Forense VIF | Medicina Legal | 15.418 | 21 | 2018–2024 (7) |
| DS3 — Forense Sexual | Medicina Legal | 18.661 | 21 | 2018–2024 (7) |

**Principio arquitectónico:** el DataCleaner NO genera dimensiones analíticas (eso es del DataStandardizer), NO filtra por región (eso lo hizo el DataSegmenter) y NO calcula tasas (eso lo hará el DataMasterBuilder). Su responsabilidad única: recibir un DataFrame segmentado y devolverlo limpio, deduplicado e imputado.

## 4.8. Paso 7 — Construcción de capas analíticas (DataAggregator)

Crea 8 DataFrames agregados en RAM con los conteos de casos por municipio × año, segmentados por sexo de la víctima y grupo etario. Cada capa filtra por género + grupo etario sobre el dataset limpio, agrupa por cod\_municipio + anio\_hecho y suma la columna cantidad.

| Capa | Fuente | Género | Grupo etario | Variable resultado |
| :---- | :---- | :---- | :---- | :---- |
| A | DS1 Violencia | FEMENINO | MENORES + ADOLESCENTES | casos\_vif\_nna\_f |
| B | DS1 Violencia | FEMENINO | ADULTOS | casos\_vif\_adultas\_f |
| C | DS2 Sexuales | FEMENINO | MENORES + ADOLESCENTES | casos\_sexual\_nna\_f |
| D | DS2 Sexuales | FEMENINO | ADULTOS | casos\_sexual\_adultas\_f |
| E | DS1 Violencia | MASCULINO | MENORES + ADOLESCENTES | casos\_vif\_nna\_m |
| F | DS1 Violencia | MASCULINO | ADULTOS | casos\_vif\_adultos\_m |
| G | DS2 Sexuales | MASCULINO | MENORES + ADOLESCENTES | casos\_sexual\_nna\_m |
| H | DS2 Sexuales | MASCULINO | ADULTOS | casos\_sexual\_adultos\_m |

Las capas E–H (masculinas) son necesarias exclusivamente para calcular la brecha de género (denominador del ratio). Por eso los registros masculinos se preservan a lo largo del pipeline; el filtro femenino se aplica solo en las capas A–D.

# 5. Tabla Maestra

## 5.1. Paso 8 — Validación cruzada de capas (control de calidad pre-JOIN)

Verifica que la suma de las 8 capas sea coherente con los totales de DS1 y DS2 limpios antes de construir la tabla maestra; es el riesgo silencioso más alto del pipeline. Validaciones obligatorias:

* Suma de A + B + E + F igual al total de DS1 limpio (menos registros con genero\_victima = NO\_REGISTRADO).

* Suma de C + D + G + H igual al total de DS2 limpio (misma exclusión).

* Unicidad: cada capa, a lo sumo una fila por combinación cod\_municipio × anio\_hecho.

* Cobertura temporal: cada capa con datos para los 8 años (2018–2025).

**Acción si falla:** detener el pipeline; no proceder al Paso 9 hasta que la validación sea exitosa, documentando y rastreando la discrepancia hasta el paso que la genera.

## 5.2. Paso 9 — Construcción de la tabla maestra (DataMasterBuilder)

Integra las 8 capas + datos poblacionales DANE en una única tabla territorial municipio × año, con tasas normalizadas, brechas de género e ICV-GEN-F.

### 5.2.1. Esqueleto territorial

Se construye una tabla base con todas las combinaciones municipio × año de la Región Pacífico: 179 municipios × 8 años = 1.432 filas. El esqueleto garantiza que ningún municipio desaparezca aunque no tenga casos en algún año (un municipio con 0 casos también es información).

**Decisión arquitectónica (granularidad-primero):** la construcción usa un esqueleto territorial 179 × 8 con LEFT JOINs, filtrando el DANE por area\_geo = 'Total' antes del merge. Esto evita la triplicación de filas que provendría de los tres valores de area\_geo del DANE; drop\_duplicates no es la solución correcta, sino el filtrado de granularidad previo al JOIN.

### 5.2.2. LEFT JOINs secuenciales

Se unen las 8 capas + DANE al esqueleto, siempre con LEFT JOIN desde el esqueleto como tabla izquierda y llave compuesta cod\_municipio + anio\_hecho. Tratamiento de NaN post-JOIN:

* **Columnas de casos (A–H):** NaN → 0 (significa 0 casos reportados, no ausencia de información).

* **Columnas de población (DANE):** NaN se conserva (no hay denominador disponible; no se puede imputar población). Estos municipios quedan con tasa = NaN, no con tasa = 0.

**Distinción crítica:** NaN en casos y NaN en población tienen significados opuestos; tratarlos igual contamina las tasas.

### 5.2.3. Tasas por 100.000 habitantes

Fórmula general: Tasa = (Número de casos / Población del grupo) × 100.000. Manejo de división por cero: si el denominador poblacional es 0, la tasa se asigna como NaN (no 0) y se documenta el caso.

### 5.2.4. Brechas de género

brecha = tasa\_femenina / tasa\_masculina. Un valor > 1 indica que la violencia afecta proporcionalmente más a las mujeres/niñas. Se calculan las brechas VIF NNA, VIF adultas, sexual NNA y sexual adultas. Si la tasa masculina es 0, la brecha se asigna como NaN y se documenta.

### 5.2.5. Normalización y cálculo del ICV-GEN-F

Las 4 tasas femeninas se normalizan a escala 0–1 con MinMaxScaler por columna sobre el dataset completo y se aplica la fórmula ponderada:

***ICV-GEN-F = 0,30·(VIF NNA) + 0,30·(Sexual NNA) + 0,25·(VIF adultas) + 0,15·(Sexual adultas)***

**Justificación de pesos:** las niñas reciben el mayor peso combinado (0,60) porque el proyecto prioriza la detección temprana de la violencia en la infancia como fenómeno estructural que precede a la violencia adulta. Los pesos alimentan únicamente el índice continuo; la topología de clusters es invariante a su reponderación por diseño.

### 5.2.6. Tabla de clustering

Se genera una tabla derivada promediando las tasas y el ICV-GEN-F por municipio (colapsando los 8 años): una fila por municipio, insumo directo del K-Means.

**Salidas:** master\_table.parquet (1.432 filas × 23 columnas) + tabla\_clustering.parquet (179 filas × 16 columnas).

# 6. Arquitectura del Carril Paralelo — DS3 y DS4

## 6.1. Principio de separación

DS3 (delito sexual forense) y DS4 (VIF forense) miden fenómenos distintos desde la misma institución con variables diferenciadas. DS4 registra solo agresores intrafamiliares y usa la variable factor; DS3 registra agresores familiares y no familiares y usa la variable circunstancia. La recomendación metodológica es tablas separadas con estructura paralela: no unificar DS3 y DS4, preservando la riqueza analítica de cada fuente y demostrando escalabilidad del pipeline.

## 6.2. Tablas derivadas de DS4 (VIF forense)

| Tabla | Propósito | Granularidad |
| :---- | :---- | :---- |
| ds4\_municipio\_resumen | Resumen de VIF forense por municipio | 1 fila × municipio |
| ds4\_agresor | Perfil del agresor intrafamiliar | departamento + agresor + ciclo\_vital |
| ds4\_escenario | Distribución de escenarios de la VIF | departamento + escenario |
| ds4\_temporalidad | Heatmap de estacionalidad de la VIF | departamento + mes + dia + hora\_rango |
| ds4\_interseccional | Vulnerabilidad múltiple en VIF, sobre denominador femenino ponderado (ver §6.5) | ciclo\_vital + etnia + discapacidad |
| ds4\_factor | Clasificación de factores del hecho | departamento + factor |

## 6.3. Tablas derivadas de DS3 (delito sexual forense)

| Tabla | Propósito | Granularidad |
| :---- | :---- | :---- |
| ds3\_municipio\_resumen | Resumen de delito sexual forense por municipio | 1 fila × municipio |
| ds3\_agresor | Perfil del agresor sexual (incl. no familiares) | departamento + agresor + ciclo\_vital |
| ds3\_escenario | Distribución de escenarios de violencia sexual | departamento + escenario |
| ds3\_circunstancia | Clasificación de circunstancias del hecho | departamento + circunstancia |
| ds3\_temporalidad | Heatmap de estacionalidad sexual | mes + dia + hora\_rango |
| ds3\_interseccional | Vulnerabilidad múltiple en violencia sexual, sobre denominador femenino ponderado (ver §6.5) | departamento + ciclo\_vital + etnia + discapacidad |

**Total de tablas forenses: 12 (6 DS4 + 6 DS3).** DS3 incluye ds3\_circunstancia; DS4 su análoga ds4\_factor. La variable ciclo\_vital no se colapsa a un grupo\_edad binario en las tablas forenses: el continuo multigeneracional y la mutación del agresor a lo largo de las etapas de vida es una tesis central, no una característica opcional.

## 6.4. Diferencias estructurales clave entre DS3 y DS4

| Dimensión | DS4 — VIF forense | DS3 — Delito sexual forense |
| :---- | :---- | :---- |
| Variable específica | factor (9 categorías) | circunstancia (49 categorías) |
| Dimensión derivada | — (factor no se dimensiona) | dimension\_circunstancia (8 categorías) |
| Tipos de agresor | Solo intrafamiliares (18 categorías) | Familiares + no familiares (58 categorías) |
| Cobertura temporal | 2018–2024 (7 años) | 2018–2024 (7 años) |
| dias\_incapacidad | Presente (4 rangos) | Ausente |
| Filas limpias | 15.418 | 18.661 |

## 6.5. Extensión interseccional — migración a denominador femenino (julio 2026)

Las tablas `ds3_interseccional` y `ds4_interseccional` originalmente calculaban los porcentajes de discapacidad y etnia sobre el total de casos (femeninos + masculinos). Dado que el ICV-GEN-F y toda la narrativa del proyecto tienen un enfoque explícitamente femenino, ese denominador mixto era inconsistente con el resto de la metodología: mezclaba la señal de vulnerabilidad femenina con casos masculinos, que no son el objeto del análisis.

**Cambio metodológico:** el denominador se migró a un conteo femenino ponderado — Σ(n\_casos × pct\_femenino / 100) — calculado por categoría. Los campos derivados de este nuevo denominador se renombraron con sufijo `_f` (p. ej. `n_base_f`, `pct_disability_f`) para distinguirlos explícitamente de cualquier cifra calculada sobre el total mixto, siguiendo la misma lógica de trazabilidad de variables descrita en §8.

**Extensión étnica (solo DS3):** se agregaron variables étnicas explícitas — `pct_afro_narp_f`, `pct_indigena_f`, `pct_sin_pertenencia_f` — y una comparación DS3 vs. DS4 a cinco categorías étnicas en orden fijo (Sin pertenencia étnica, Afro-NARP, No registrado, Indígena, Gitano).

**Regla de bajo-N:** cualquier categoría étnica con menos de 30 casos femeninos se marca en el dashboard con un flag de advertencia (`low_n_flag`), para que el jurado y cualquier usuario final no sobre-interpreten porcentajes calculados sobre muestras pequeñas. La categoría Gitano es el caso ilustrativo de esta regla en los datos actuales.

**Código muerto retirado:** el bloque de cruce `_ethnicity_table`, que contenía un error en el cálculo de la media ponderada, se eliminó del backend en esta misma extensión.

**Alcance del cambio:** exclusivo del Carril B (ForenseExporter/dashboard). No modifica el ICV-GEN-F, el K-Means ni ninguna estructura del Carril A — se preserva íntegramente la regla de oro de §2: DS3 y DS4 nunca entran a la tabla maestra ni al modelo de IA.

# 7. Fases CRISP-ML — Modelado, Evaluación y Despliegue

## 7.1. Fase 3 — Ingeniería de Modelos de ML

**Input:** tabla\_clustering.parquet (promedios por municipio). **Modelo principal:** K-Means no supervisado para estratificar los municipios de la Región Pacífico en perfiles de severidad de violencia de género.

Pasos metodológicos ejecutados:

* **Selección de features:** las 4 tasas femeninas, con exclusión explícita de variables identificadoras (cod\_municipio, municipio, departamento).

* **Preprocesamiento:** transformación log1p para reducir la asimetría y RobustScaler (mediana + IQR) en lugar de StandardScaler, elegido específicamente porque Cali (código 76001) domina el volumen regional y contamina la media; RobustScaler resiste ese outlier.

* **Número de clusters:** exploración del rango k = 2 a k = 6 con método del codo y Silhouette Score, aplicando parsimonia cuando las diferencias de Silhouette son marginales; se seleccionó k = 2.

* **Exclusión de municipios:** se excluyen dos municipios de Chocó (códigos 27150 y 27493) por subregistro estructural — ocho años de conteos absolutos casi nulos — que crearían un cluster artificial de baja severidad y distorsionarían la geometría. Universo efectivo de clustering: N = 177 municipios.

* **Posicionamiento del modelo:** instrumento de discretización de severidad (no de clustering tipológico). El ICV-GEN-F continuo y los tramos de cluster funcionan como instrumentos de validación convergente.

### 7.1.1. Clasificador supervisado para explicabilidad y selección de Logistic Regression

Para añadir explicabilidad al modelo no supervisado se entrena un clasificador supervisado sobre las etiquetas de cluster asignadas. En lugar de fijar de antemano un único algoritmo, la metodología consistió en probar varios clasificadores y elegir el mejor de forma fundamentada:

* **Protocolo de comparación:** benchmark de varios algoritmos supervisados (entre ellos SVM con kernel RBF) validados con StratifiedKFold(5) sobre F1-Macro y class\_weight='balanced' para manejar el desbalance entre tramos.

* **Resultado de la comparación:** Logistic Regression empató en desempeño con el mejor alternativo (SVM\_rbf) dentro del margen de ruido; la diferencia de F1-Macro fue despreciable.

**Criterio de decisión (por qué Logistic Regression):** ante un empate técnico de desempeño, se prioriza el modelo más conveniente para el proyecto. Logistic Regression se seleccionó por cuatro razones:

* **Separabilidad lineal:** hay evidencia de que los clusters son linealmente separables, por lo que un modelo lineal es suficiente y apropiado.

* **Interpretabilidad:** sus coeficientes lineales son directamente legibles para audiencias de política pública, a diferencia de modelos de caja negra.

* **Parsimonia:** a igualdad de desempeño, el modelo más simple reduce el riesgo de sobreajuste y facilita el mantenimiento.

* **Coherencia arquitectónica:** es consistente con el ICV-GEN-F, que es un índice lineal ponderado; el clasificador y el índice comparten la misma lógica lineal.

El modelo final se entrenó sobre el 100% de los 177 municipios y se exportó junto con sus metadatos para el dashboard.

## 7.2. Fase 4 — Evaluación del Modelo

La evaluación combina validación estadística interna y de sentido territorial:

* **Estabilidad de clusters:** verificación de que los clusters no cambian sustancialmente ante pequeñas perturbaciones de los datos (Bootstrap ARI sobre submuestras).

* **Calidad de la partición:** Silhouette Score como criterio de cohesión/separación.

* **Sensibilidad del ICV-GEN-F:** análisis de cómo cambia el ranking de municipios al variar los pesos. La metodología concluye que el esquema es robusto a reponderaciones razonables (alta correlación de rangos y alto solape de clusters) pero frágil ante el colapso dimensional, por lo que la estructura de cuatro dimensiones es analíticamente esencial.

* **Validación cruzada geográfica:** verificación de que los clusters tienen sentido territorial (municipios del mismo cluster comparten características observables).

* **Reconciliación del pre-registro:** se alineó pre\_registro\_kmeans.md con la corrida real del notebook (sin re-ejecutar el modelo) para garantizar integridad metodológica: la documentación coincide con la corrida.

## 7.3. Fase 5 — Despliegue (sitio estático GitHub Pages)

El proyecto adopta un sitio estático en GitHub Pages, con Leaflet para mapas coropléticos y Apache ECharts para gráficos interactivos. Fundamentos: (1) rendimiento (carga instantánea desde CDN, sin cold starts); (2) estética profesional y control total del diseño; (3) separación de capas (pipeline Python desacoplado del frontend HTML/JS), que demuestra diseño de software maduro.

**Estado: completado y en producción.** El paso final del pipeline Python (MasterExporter/ModelExporter/ForenseExporter) lee los .parquet (tabla maestra, 12 tablas forenses y resultados del modelo) y los exporta como .json autosuficientes, ya pre-agregados. El JavaScript del frontend solo renderiza; toda la lógica de negocio vive en Python. Este es el único punto de contacto entre la capa de datos y la de presentación.

`site/` es un artefacto autocontenible y desplegable: 8 JSON canónicos + 4 configuraciones sincronizados vía `scripts/sync_to_site.sh` con verificación md5, y los 18 `test_render_*.html` (+ `test_load.html`) migrados a rutas relativas `./data/` y `./config/`. Un test de sincronización dedicado (`tests/test_site_data_sync.py`, 12 casos parametrizados) previene drift entre las fuentes canónicas y `site/`. El despliegue a GitHub Pages es automático vía GitHub Actions (`.github/workflows/deploy-pages.yml`): en cada push a `main` copia `site/` a un directorio limpio y remueve los `test_render_*.html` antes de publicar, de modo que el jurado solo ve el dashboard final.

Los 5 módulos del dashboard:

| # | Módulo | Contenido |
| :---- | :---- | :---- |
| 1 | Panorama regional | Mapa coroplético ICV-GEN-F, ranking de municipios por cluster, tendencia temporal agregada (Leaflet + ECharts) |
| 2 | Análisis por tipo de violencia | Scatter de tasas VIF vs. sexuales, comparación NNA vs. adultas, evolución por departamento (ECharts) |
| 3 | Brechas de género | Gráficos divergentes de ratios de brecha por municipio y año (ECharts) |
| 4 | Caracterización forense | Perfil del agresor, escenarios, factores/circunstancias, estacionalidad e interseccionalidad (treemap, heatmap, sunburst, pie); incluye la extensión étnica del sub-acto 4.5 (§6.5) |
| 5 | Ficha municipal | Selector de municipio con narrativa automatizada (datos cuantitativos + cualitativos DS3/DS4) y mini-gráficos |

## 7.4. Fase 6 — Monitoreo y Mantenimiento

**Fuera del alcance del concurso.** CRISP-ML(Q) contempla 6 fases por definición del framework; esta última se documenta aquí como parte del ciclo de vida metodológico completo, pero **no es un compromiso de desarrollo dentro de este proyecto**. Ningún entregable del concurso depende de esta fase — queda registrada como diseño conceptual para una eventual continuidad posterior.

* Documentación de la estrategia de reentrenamiento: cuándo y cómo actualizar el modelo cuando se publiquen datos nuevos.

* Diseño de observabilidad con Prefect (flows, tasks y artefactos); implementación conceptual post-concurso.

# 8. Trazabilidad de Variables

Cada variable que transita por el pipeline tiene tres niveles documentados:

* **Variable original:** nombre exacto en el archivo crudo (p. ej. 'CODIGO DANE'). Preservada en MetadataMapper.

* **Variable estandarizada:** nombre canónico tras el DataStandardizer (p. ej. cod\_municipio). Definida en column\_aliases.

* **Variable derivada:** calculada durante el pipeline (p. ej. anio\_hecho, dimension\_delito, tasa\_vif\_nna\_f, icv\_gen\_f). El sufijo `_f` introducido en la extensión interseccional de julio 2026 (§6.5) sigue esta misma lógica: identifica explícitamente que la variable se calculó sobre el denominador femenino ponderado, no sobre el total mixto F+M.

El diccionario de variables es la fuente de verdad: cualquier variable que aparezca en el código y no en el diccionario es una variable no documentada y representa un riesgo metodológico.

# 9. Lista de Chequeo Pre-Tabla Maestra

## 9.1. Sobre los datos

* Los 5 archivos \_limpio.parquet están en data/cleaned/ y se leen sin errores.

* Los conteos post-cleaner coinciden: DS1 = 68.052 | DS2 = 34.592 | DANE = 4.296 | DS4 = 15.418 | DS3 = 18.661.

* DS2 incluye la columna dimension\_delito.

* genero\_victima en DS1 y DS2 incluye FEMENINO, MASCULINO y NO\_REGISTRADO.

* grupo\_etario en DS1 y DS2 incluye MENORES, ADOLESCENTES, ADULTOS y NO\_REGISTRADO.

* cod\_municipio tiene formato string de 5 dígitos consistente entre DS1, DS2 y DANE.

## 9.2. Sobre la metodología

* La validación cruzada de capas A–H contra totales limpios está ejecutada y aprobada.

* Llave compuesta del esqueleto definida: cod\_municipio + anio\_hecho.

* Todos los JOINs son LEFT JOIN desde el esqueleto; DANE filtrado por area\_geo = 'Total' antes del merge.

* Tratamiento diferenciado de NaN: casos → 0, población → conservar NaN.

* DS3 y DS4 nunca entran al ICV-GEN-F ni al K-Means.

* Poblaciones masculinas disponibles en DANE para calcular brechas de género.

## 9.3. Sobre las salidas

* La estructura de carpetas data/master/ existe antes de ejecutar.

* master\_table.parquet con 1.432 filas (179 municipios × 8 años) y 23 columnas; tabla\_clustering.parquet con 179 filas × 16 columnas.

* La fórmula del ICV-GEN-F y sus pesos están documentados en la configuración del master.
