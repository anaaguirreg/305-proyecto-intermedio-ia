# Conclusiones

## Hallazgos principales

**Severidad territorial.** De los 177 municipios evaluados por el modelo, 107 (~60%) se clasifican en severidad Alta — la mayoría del territorio, no una minoría marginal. Pasto (Nariño) y Popayán (Cauca), las dos capitales departamentales de la muestra, registran los ICV-GEN-F más altos de la región: la mayor severidad no está confinada a la periferia rural, también aparece donde la capacidad institucional de registro es mayor.

**Brechas de género.** Cauca presenta la brecha de género más amplia de la región: por cada hombre víctima de violencia, casi 5 mujeres son víctimas. La brecha decrece con los años, pero no porque la violencia contra las mujeres disminuya — es porque ha crecido el número de reportes de víctimas de sexo masculino. Leer esa tendencia sin este contexto lleva a una conclusión equivocada.

**Patrón del agresor (continuo multigeneracional).** El agresor cambia con la edad de la víctima: cuidador en la primera infancia, padrastro en la adolescencia, pareja o expareja en la adultez. Cerca del 50% de las víctimas de delito sexual registradas son menores de 14 años. Este patrón es la evidencia empírica central que sostiene la hipótesis de partida del proyecto.

**Tipología territorial.** Policarpa (Nariño) presenta coexistencia alta de violencia intrafamiliar y sexual; en Caloto (Cauca) predomina la VIF, en Argelia (Cauca) la violencia sexual — confirmando que el patrón no es uniforme y que la intervención no puede serlo tampoco.

**La paradoja del subregistro.** Buena parte del Chocó profundo y las zonas costeras de Cauca y Nariño aparecen clasificadas como "Moderada/Baja" — no porque la violencia sea menor, sino por barreras geográficas, control territorial de grupos armados ilegales y ausencia institucional que inhiben la denuncia. El ICV-GEN-F mide lo que se reporta, no necesariamente lo que ocurre; esta distinción se documenta en el dashboard y debe acompañar cualquier lectura del índice.

## Limitaciones

- **Asimetría de cobertura temporal:** DS1/DS2 (Policía Nacional) cubren hasta 2025; DS3/DS4 (Medicina Legal) cubren hasta 2024. Las fichas alimentadas por datos forenses tienen un año menos de cobertura, por ciclos de publicación institucional.
- **Exclusión de 2 municipios del clustering:** 27150 y 27493 (Chocó) quedan fuera del K-Means por subregistro estructural (conteos casi nulos durante 8 años). El ICV-GEN-F continuo sí se calcula para ellos, pero no tienen `cluster_kmeans` asignado — es una decisión documentada en `docs/pre_registro_kmeans.md`, no un vacío accidental.
- **DS3/DS4 son complementarios, no exhaustivos:** por diseño, nunca entran al índice ni al modelo (ver regla de oro en [`fuentes_datos.md`](fuentes_datos.md)). La ficha forense municipal solo se activa si el municipio tiene ≥30 casos forenses — municipios con menor cobertura no tienen ficha forense, aunque sí tienen ICV-GEN-F.
- **Categorías étnicas de bajo-N:** en la extensión interseccional del sub-acto 4.5, categorías con menos de 30 casos femeninos (p. ej. Gitano) llevan flag de advertencia en el dashboard — los porcentajes sobre muestras tan pequeñas no deben leerse como tendencias estables.
- **Los pesos del ICV-GEN-F son una decisión metodológica, no un óptimo estadístico:** el 60% de peso combinado en violencia contra niñas responde a una priorización explícita (detección temprana), no a una calibración empírica. El análisis de sensibilidad confirmó que el ranking de municipios es robusto a reponderaciones razonables, pero la estructura de 4 dimensiones es esencial — colapsarla sí distorsiona los resultados.
- **Deduplicación exacta, no difusa:** el DataCleaner remueve duplicados exactos (`keep='first'`) sobre todas las columnas originales. Posibles duplicados "casi idénticos" con variaciones menores de captura no se abordan en esta versión.

## Impacto social, económico y ambiental

**Impacto social**
El detalle completo de beneficiarios, problema visibilizado y orientación a política pública está en la sección "Impacto potencial" del [`README.md`](../README.md). En síntesis: el proyecto beneficia directamente a Comisarías de Familia, ICBF Regional Pacífico, Gobernaciones y equipos de política pública de género municipales, y permite diseñar intervenciones diferenciadas por perfil de municipio en lugar de intervenciones uniformes y facilitar procesos de prevención.

**Impacto económico**
- **Costo de datos: cero.** Los 5 datasets fuente (DS1–DS4 + DANE) son de acceso abierto en datos.gov.co y dane.gov.co — no hay licenciamiento ni suscripción que replicar.
- **Costo de despliegue: cero.** El sitio estático se sirve gratis desde GitHub Pages, sin servidor, base de datos ni infraestructura cloud que mantener o escalar.
- **Eficiencia en la asignación de recursos públicos:** focalizar la intervención según el perfil de riesgo de cada municipio (cluster + ICV-GEN-F) reduce el costo de intervenciones uniformes mal dirigidas.
- **Replicabilidad sin costo marginal significativo:** el pipeline es 100% config-driven — extenderlo a otro departamento o a nivel nacional no requiere reescribir código, solo ajustar configuración (ver "Ideas de escalabilidad" más abajo).

**Impacto ambiental**
El proyecto no se planteó inicialmente con un objetivo ambiental explícito, pero varias decisiones de arquitectura, ya documentadas en otras secciones de este proyecto, reducen su huella computacional de forma medible:
- **Sin servidor ni cómputo en tiempo real:** el despliegue es 100% estático en GitHub Pages (ver [`architecture.md`](architecture.md)); todo el cálculo pesado ocurre una sola vez en el pipeline de exportación (.parquet → .json), no en cada visita al dashboard.
- **Selección de modelo por parsimonia:** ante un empate técnico entre Regresión Logística y SVM_rbf, se eligió el modelo lineal — de menor costo computacional en entrenamiento e inferencia — por ser suficiente para la separabilidad observada en los datos.
- **Configuración externa:** los cambios metodológicos se hacen editando archivos JSON, no reescribiendo ni re-ejecutando el pipeline completo.
- **Sustitución de procesos en papel:** el dashboard centraliza información que hoy se cruza manualmente entre Comisarías de Familia, ICBF, Fiscalía y Medicina Legal.

La misma arquitectura sin servidor y config-driven es la base común de la sostenibilidad y la escalabilidad.

## Próximos pasos

### Fase 6 CRISP-ML — Monitoreo y mantenimiento

La Fase 6 — monitoreo y reentrenamiento — queda como diseño conceptual para una eventual continuidad del proyecto.

### Ideas de escalabilidad

- Explorar una integración conceptual con sistemas de alerta temprana existentes (p. ej. SIVIGILA) como caso de uso de referencia para Comisarías de Familia y Gobernaciones.
- El pipeline está parametrizado por diseño (ver [`architecture.md § Configuración externa`](architecture.md)): extenderlo a otras regiones de Colombia no requeriría cambios de código, solo de configuración — esa es una prueba de escalabilidad que vale la pena documentar con un ejemplo concreto en el futuro.

No se identificaron ajustes estructurales que requieran tocar el schema de los JSON del dashboard: la arquitectura de datos se mantiene estable de cara al concurso.
