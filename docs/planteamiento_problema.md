# Planteamiento del Problema

## Problema central

En la Región Pacífico colombiana — Valle del Cauca, Cauca, Nariño y Chocó — la violencia intrafamiliar y la violencia sexual contra niñas, adolescentes y mujeres adultas constituyen una crisis de seguridad ciudadana que opera en silencio institucional. Esta región concentra algunos de los municipios con mayor vulnerabilidad estructural del país: presencia de grupos armados, alta proporción de población étnica, déficit histórico de presencia estatal y condiciones de pobreza que amplifican los factores de riesgo para la violencia de género.

El Estado colombiano registra estos hechos a través de múltiples sistemas administrativos, pero esa información permanece fragmentada entre entidades que nunca la cruzan: el ICBF gestiona la protección de niñas, la Fiscalía investiga los delitos, las Comisarías de Familia atienden la violencia doméstica y Medicina Legal documenta las lesiones. Ninguna herramienta pública integra estas fuentes para responder una pregunta fundamental de política pública:

> **¿En qué municipios de la Región Pacífico la violencia intrafamiliar y sexual contra niñas y mujeres es un patrón estructural que atraviesa generaciones, y cómo puede anticiparse para orientar estrategias de prevención?**

La brecha que *Cicatrices Invisibles* busca resolver tiene tres dimensiones:

- **Brecha territorial:** no existe una herramienta que compare sistemáticamente los municipios de la Región Pacífico según su nivel de riesgo de violencia intrafamiliar y sexual con enfoque de género, a partir de datos abiertos normalizados por población.
- **Brecha generacional:** la violencia contra niñas y la violencia contra mujeres adultas se analizan por separado, cuando la evidencia sugiere que coexisten en los mismos territorios como expresiones de un mismo patrón cultural — el **continuo multigeneracional** (ver [`README.md § El índice ICV-GEN-F`](../README.md#el-índice-icv-gen-f-qué-mide-y-por-qué)). Esa coexistencia no tiene indicador oficial en Colombia.
- **Brecha predictiva:** las intervenciones de seguridad y justicia en la región son reactivas. No existe un sistema que clasifique municipios por perfil de riesgo ni que permita priorizar territorios para intervención preventiva antes de que los casos escalen.

## Evidencia que sustenta el problema

El análisis exploratorio del dataset de Delitos Sexuales (DS2) confirma que el género femenino concentra entre el 80% y el 85% de los casos reportados en todos los grupos etarios — menores, adolescentes y adultos — de manera consistente. La tendencia temporal muestra crecimiento sostenido hasta 2019, una caída en 2020 atribuible al subregistro por confinamiento durante la pandemia, y una estabilización posterior que no indica resolución del problema sino normalización del mismo.

Los datasets forenses de Medicina Legal (DS3, DS4) revelan adicionalmente que los principales agresores de niñas en contexto intrafamiliar son figuras de autoridad dentro del hogar — padre, madre, abuelos, otros familiares —, y que el factor desencadenante predominante en VIF es la intolerancia y el machismo. Ambos hallazgos, ya confirmados en la corrida final del pipeline (ver [`README.md § Resultados clave`](../README.md#resultados-clave)), sostienen que la violencia contra niñas no es un evento accidental sino un patrón cultural reproducible territorialmente.

## Preguntas analíticas

**Pregunta principal:**

> ¿Qué municipios de la Región Pacífico colombiana presentan patrones críticos de coexistencia de violencia intrafamiliar y sexual contra niñas, adolescentes y mujeres adultas, y cómo ha evolucionado ese patrón entre 2018 y 2025?

**Preguntas secundarias:**

| # | Pregunta | Dataset que la responde |
| :---- | :---- | :---- |
| P1 | ¿Cuáles son los municipios con mayor tasa de VIF contra niñas y adolescentes? | DS1 filtrado MENORES + ADOLESCENTES + FEMENINO |
| P2 | ¿Cuáles son los municipios con mayor tasa de delitos sexuales contra niñas, adolescentes y mujeres? | DS2 filtrado MENORES + ADOLESCENTES + FEMENINO |
| P3 | ¿En qué municipios coexisten alta violencia intrafamiliar contra mujeres adultas y alta violencia sexual contra niñas simultáneamente? | DS1 + DS2 cruzados por municipio |
| P4 | ¿Cómo ha evolucionado la violencia contra niñas y mujeres entre 2018 y 2025 en la región? | Serie histórica DS1 + DS2 |
| P5 | ¿Qué perfiles de municipio emergen al clasificar el riesgo con inteligencia artificial? | K-Means sobre la tabla maestra |
| P6 | ¿Quién agrede a las niñas y mujeres, dónde ocurre la violencia y qué factores la desencadenan? | DS3, DS4 — caracterización forense |
| P7 | ¿Existen grupos con vulnerabilidad adicional por discapacidad o pertenencia étnica en los municipios más críticos? | DS3, DS4 — análisis interseccional |
| P8 | ¿Qué municipios deberían priorizarse para intervención preventiva según el índice de riesgo construido? | ICV-GEN-F + clusters |

## Objetivos

**Objetivo general:** construir un sistema analítico interactivo con enfoque de género y territorio que identifique, clasifique y caracterice los patrones de violencia intrafamiliar y sexual contra niñas, adolescentes y mujeres adultas en los municipios de la Región Pacífico colombiana, integrando inteligencia artificial para perfilar territorios y orientar estrategias diferenciadas de prevención en seguridad ciudadana y justicia.

**Objetivos específicos:**

| # | Objetivo | Entregable |
| :---- | :---- | :---- |
| OE1 | Integrar, limpiar y normalizar DS1 + DS2 + DANE en una tabla maestra territorial con tasas por 100.000 mujeres | Pipeline ETL documentado + `maestro_concurso.parquet` con las 4 tasas femeninas |
| OE2 | Construir el ICV-GEN-F como índice compuesto del continuo multigeneracional | Variable `icv_gen_f` calculada |
| OE3 | Clasificar los municipios por perfil de severidad mediante K-Means, validado estadísticamente (método del codo + Silhouette Score) | Modelo entrenado + `cluster_kmeans` asignado |
| OE4 | Caracterizar el perfil del agresor, el escenario y la vulnerabilidad interseccional (discapacidad, etnia) a partir de DS3 y DS4 | 12 tablas de caracterización forense + extensión interseccional (sub-acto 4.5) |
| OE5 | Desplegar un atlas interactivo con narrativa automatizada y recomendaciones diferenciadas por municipio | Sitio estático público en GitHub Pages con ficha municipal (Acto 5) |

## Alcance final vs. planteamiento inicial

Como es esperable en un ciclo CRISP-ML(Q) iterativo, algunos parámetros técnicos se precisaron durante la ejecución respecto al planteamiento inicial de esta fase:

| Parámetro | Planteamiento inicial | Alcance final ejecutado |
| :---- | :---- | :---- |
| Universo territorial | Estimado ~250 municipios | **179 municipios** confirmados (177 efectivos en el clustering) |
| Número de clusters | Rango exploratorio de perfiles de riesgo | **k = 2** (validado por método del codo + Silhouette Score) |
| Tecnología del dashboard | Streamlit | **Sitio estático en GitHub Pages** (Leaflet + Apache ECharts) — ver [`architecture.md`](architecture.md) |
| Variables del proyecto | 17 variables propuestas | **20 variables** finales — ver [`data_dictionary.md`](data_dictionary.md) |

Ninguno de estos ajustes altera la pregunta de investigación ni los objetivos: son refinamientos metodológicos documentados a medida que el pipeline y el modelo se validaron contra los datos reales.
