# Diccionario de Variables

Documenta las **20 variables** listadas en la sección "Variables seleccionadas" del [`README.md`](../README.md) — el máximo permitido para el nivel Intermedio del concurso. Las 4 tasas femeninas y el ICV-GEN-F son las únicas variables que alimentan el modelo K-Means; las variables forenses (filas 15–20) caracterizan el dashboard pero **nunca entran al índice ni al modelo** (ver regla de oro en [`fuentes_datos.md`](fuentes_datos.md)).

## Territoriales y temporal

| # | Variable | Tipo | Dominio | Fuente | Derivación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | `cod_municipio` | string (5 dígitos) | Código DANE/DIVIPOLA | DS1, DS2, DS3, DS4, DANE | Validado contra `config/municipios_pacifico.json`; sin match → `CODIGO_MAL_REGISTRADO` |
| 2 | `municipio` | category | Nombre oficial del municipio | DANE (recuperado por cruce si falta en la fuente) | — |
| 3 | `departamento` | category | Valle del Cauca \| Cauca \| Nariño \| Chocó | DS1, DS2, DS3, DS4, DANE | Filtro de segmentación territorial |
| 4 | `anio_hecho` | Int32 | 2018–2025 (2018–2024 en DS3/DS4) | Derivada de `fecha_hecho` | `anio_hecho = year(fecha_hecho)`. En DS3/DS4, `fecha_hecho` se sintetiza como `{año}-01-01` |

`cod_municipio` + `anio_hecho` es la llave compuesta del esqueleto territorial (179 municipios × 8 años).

## Tasas (por 100.000 mujeres)

| # | Variable | Tipo | Dominio | Fuente | Derivación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 5 | `tasa_vif_nna_f` | float | ≥ 0 (NaN si población = 0) | DS1 + DANE | (casos VIF niñas/adolescentes FEMENINO / población femenina 0–17) × 100.000 |
| 6 | `tasa_vif_adultas_f` | float | ≥ 0 (NaN si población = 0) | DS1 + DANE | (casos VIF adultas FEMENINO / población femenina 18+) × 100.000 |
| 7 | `tasa_sexual_nna_f` | float | ≥ 0 (NaN si población = 0) | DS2 + DANE | (casos sexuales niñas/adolescentes FEMENINO / población femenina 0–17) × 100.000 |
| 8 | `tasa_sexual_adultas_f` | float | ≥ 0 (NaN si población = 0) | DS2 + DANE | (casos sexuales adultas FEMENINO / población femenina 18+) × 100.000 |

Estas son las **4 tasas que alimentan el ICV-GEN-F y el K-Means** — ver fórmula y pesos en [`marco_metodologico.md § El índice`](marco_metodologico.md).

## Brechas de género

| # | Variable | Tipo | Dominio | Fuente | Derivación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 9 | `brecha_vif_nna` | float | > 0 (NaN si tasa masculina = 0); > 1 = más mujeres afectadas | DS1 | tasa femenina / tasa masculina, VIF niñas/adolescentes |
| 10 | `brecha_vif_adultas` | float | > 0 (NaN si tasa masculina = 0) | DS1 | tasa femenina / tasa masculina, VIF adultas |
| 11 | `brecha_sexual_nna` | float | > 0 (NaN si tasa masculina = 0) | DS2 | tasa femenina / tasa masculina, sexual niñas/adolescentes |
| 12 | `brecha_sexual_adultas` | float | > 0 (NaN si tasa masculina = 0) | DS2 | tasa femenina / tasa masculina, sexual adultas |

Las brechas enriquecen la narrativa del dashboard (Acto 3); no son insumo del ICV-GEN-F ni del modelo.

## Índice compuesto y modelo

| # | Variable | Tipo | Dominio | Fuente | Derivación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 13 | `icv_gen_f` | float | 0–1 (0–100 en el dashboard) | Calculada | `0,30·tasa_vif_nna_f + 0,30·tasa_sexual_nna_f + 0,25·tasa_vif_adultas_f + 0,15·tasa_sexual_adultas_f`, sobre las 4 tasas normalizadas 0–1 con MinMaxScaler |
| 14 | `cluster_kmeans` | category | Alta \| Moderada/Baja | K-Means (k=2) | Sobre `tabla_clustering.parquet` (promedio municipal de las 4 tasas, transformación `log1p` + `RobustScaler`), N=177 (excluye 2 municipios de Chocó por subregistro estructural) |

## Forense — caracterización (Carril B, solo dashboard)

| # | Variable | Tipo | Dominio | Fuente | Nota |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 15 | `agresor` | category | DS4: 18 categorías (solo intrafamiliares) · DS3: 58 categorías (familiares + no familiares) | DS3, DS4 | Perfil del presunto agresor |
| 16 | `escenario` | category | Vivienda, vía pública, etc. | DS3, DS4 | Lugar del hecho |
| 17 | `factor` | category | 9 categorías | DS4 | Factor desencadenante del hecho (exclusivo VIF forense) |
| 18 | `circunstancia` | category | 49 categorías (colapsadas en `dimension_circunstancia`, 8 categorías) | DS3 | Análoga a `factor`, exclusiva de delito sexual forense |
| 19 | `etnia` | category | Sin pertenencia étnica, Afro-NARP, Indígena, Gitano, No registrado | DS3, DS4 | Desde jul-2026, los porcentajes reportados en el dashboard usan denominador femenino ponderado (sufijo `_f`) — ver `marco_metodologico.md § 6.5` |
| 20 | `discapacidad` | category/boolean | Tipo de discapacidad reportada | DS3, DS4 | Misma nota de denominador femenino ponderado que `etnia` |

**Regla de oro:** ninguna de las variables 15–20 se une a la tabla maestra ni se usa como *feature* del K-Means. Su único destino es enriquecer las tablas de caracterización forense y las fichas municipales del dashboard.
