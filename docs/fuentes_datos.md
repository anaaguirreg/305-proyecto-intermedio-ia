# Fuentes de Datos

*Cicatrices Invisibles* integra 5 datasets de 3 fuentes institucionales, con roles diferenciados dentro del pipeline (ver [`marco_metodologico.md`](marco_metodologico.md) para el detalle arquitectónico completo).

**Regla de oro:** DS1 y DS2 (Policía Nacional) alimentan el índice ICV-GEN-F y el modelo K-Means (Carril A). DS3 y DS4 (Medicina Legal) nunca entran a la tabla maestra ni al modelo — alimentan exclusivamente la caracterización forense y las fichas municipales del dashboard (Carril B).

## Resumen

| ID | Dataset | Fuente | Portal | Filas limpias | Carril |
| :---- | :---- | :---- | :---- | :---- | :---- |
| DS1 | Violencia intrafamiliar | Policía Nacional | datos.gov.co | 68.052 | A — Tabla maestra |
| DS2 | Delitos sexuales | Policía Nacional | datos.gov.co | 34.592 | A — Tabla maestra |
| DS3 | Exámenes médico legales por presunto delito sexual | Medicina Legal | datos.gov.co | 18.661 | B — Dashboard |
| DS4 | Violencia intrafamiliar, cifras definitivas | Medicina Legal | datos.gov.co | 15.418 | B — Dashboard |
| DANE | Proyecciones de población municipal | DANE | dane.gov.co | 4.296 | A — Denominadores |

---

## DS1 — Violencia intrafamiliar

- **Fuente:** Policía Nacional de Colombia
- **Portal:** [datos.gov.co](https://www.datos.gov.co/d/vuyt-mqpw)
- **Licencia:** CC BY-SA 4.0
- **Columnas clave:** departamento, municipio, cod_municipio, fecha_hecho, genero_victima, grupo_etario, cantidad
- **Cobertura usada en el proyecto:** Región Pacífico (Valle del Cauca, Cauca, Nariño, Chocó), 2018–2025
- **Filas tras limpieza:** 68.052
- **Rol en el proyecto:** alimenta las capas A, B, E y F del DataAggregator → tasas femeninas y masculinas de VIF → ICV-GEN-F y K-Means.
- **Nota de calidad:** 0% de duplicados — la fuente más confiable del pipeline.

## DS2 — Delitos sexuales

- **Fuente:** Policía Nacional de Colombia
- **Portal:** [datos.gov.co](https://www.datos.gov.co/d/fpe5-yrmw)
- **Licencia:** CC BY-SA 4.0
- **Columnas clave:** iguales a DS1 + `dimension_delito`
- **Cobertura usada en el proyecto:** Región Pacífico, 2018–2025
- **Filas tras limpieza:** 34.592
- **Rol en el proyecto:** alimenta las capas C, D, G y H → tasas femeninas y masculinas de delitos sexuales → ICV-GEN-F y K-Means.
- **Nota de calidad:** ~3.210 filas duplicadas identificadas y puestas en cuarentena por el DataCleaner (deduplicación vectorial `keep='first'`) antes de la agregación.

## DS3 — Exámenes médico legales por presunto delito sexual

- **Fuente:** Instituto Nacional de Medicina Legal y Ciencias Forenses
- **Portal:** [datos.gov.co](https://www.datos.gov.co/Justicia-y-Derecho/Ex-menes-m-dico-legales-por-presunto-delito-sexual/hyqu-diue/about_data)
- **Licencia:** CC BY-SA 4.0
- **Columnas clave:** ciclo_vital, agresor, escenario, circunstancia, discapacidad, etnia, hora_rango, mes_hecho
- **Cobertura usada en el proyecto:** Región Pacífico, 2018–2024 (un año menos que las fuentes policiales — ver limitación abajo)
- **Filas tras limpieza:** 18.661
- **Rol en el proyecto:** Carril B (Producto 2) — alimenta 6 de las 12 tablas de caracterización forense (perfil del agresor, escenario, circunstancia, estacionalidad e interseccionalidad). **Nunca entra al ICV-GEN-F ni al K-Means.**

## DS4 — Violencia intrafamiliar, cifras definitivas

- **Fuente:** Instituto Nacional de Medicina Legal y Ciencias Forenses
- **Portal:** [datos.gov.co](https://www.datos.gov.co/Justicia-y-Derecho/Violencia-intrafamiliar-Colombia-a-os-2015-a-2024-/ers2-kerr/about_data)
- **Licencia:** CC BY-SA 4.0
- **Columnas clave:** ciclo_vital, agresor, escenario, factor, discapacidad, etnia, dias_incapacidad, hora_rango, mes_hecho
- **Cobertura usada en el proyecto:** Región Pacífico, 2018–2024
- **Filas tras limpieza:** 15.418
- **Rol en el proyecto:** Carril B (Producto 2) — alimenta las otras 6 tablas de caracterización forense. **Nunca entra al ICV-GEN-F ni al K-Means.**

## DANE — Proyecciones de población municipal

- **Fuente:** Departamento Administrativo Nacional de Estadística (DANE)
- **Portal:** [dane.gov.co](https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion) — serie municipal de población por área, sexo y edad 2018–2042
- **Fecha de descarga:** 8 de agosto de 2025
- **Formato original:** .xlsx con encabezado MultiIndex (300+ columnas de edad), colapsado por el pipeline en 4 columnas: `pob_f_0_17`, `pob_f_18_mas`, `pob_h_0_17`, `pob_h_18_mas`
- **Cobertura usada en el proyecto:** Región Pacífico, 2018–2025
- **Filas tras limpieza:** 4.296
- **Rol en el proyecto:** único dataset externo del proyecto (no proviene del portal datos.gov.co, sino directamente del sitio oficial de DANE); provee los denominadores poblacionales para calcular las 4 tasas por 100.000 habitantes y las brechas de género.

> **Nota:** a diferencia de DS1–DS4, no aplica una licencia CC BY-SA explícita para esta fuente — es información pública oficial de DANE, sin términos de uso publicados en la página de descarga.

---

## Limitación documentada

DS3 y DS4 (Medicina Legal) cubren hasta 2024; DS1 y DS2 (Policía Nacional) cubren hasta 2025. Las fichas municipales alimentadas por datos forenses tienen, por lo tanto, un año menos de cobertura que las tasas territoriales. La asimetría responde a los ciclos de publicación de cada institución y no afecta la tabla maestra ni el modelo, que dependen exclusivamente de DS1, DS2 y DANE.
