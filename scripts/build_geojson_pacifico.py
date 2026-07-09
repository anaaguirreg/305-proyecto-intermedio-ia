#!/usr/bin/env python3
"""
build_geojson_pacifico.py
─────────────────────────────────────────────────────────────────────────────
Genera config/pacifico_municipios.geojson con los 179 municipios del
Pacífico colombiano usando Estrategia C: cabecera-anchored polygon matching.

Estrategia C:
  Para cada uno de los 179 códigos DANE canónicos en municipios_pacifico.json,
  localiza el polígono de geoBoundaries ADM2 que CONTIENE la cabecera
  municipal. Si ninguno la contiene (punto en el mar o en brecha topológica),
  usa el polígono MÁS CERCANO por distancia métrica (EPSG:9377 – CTM12).
  Esto elimina los falsos matches por nombre que producían 19 geometrías
  incorrectas en Estrategias A/B.

Propiedades de cada feature en el output:
    cod_municipio  → código DANE 5 dígitos  (join key con acto_1_panorama.json)
    municipio      → nombre canónico en mayúsculas (desde municipios_pacifico.json)
    departamento   → CAUCA | CHOCO | NARIÑO | VALLE DEL CAUCA

Stop conditions:
    - Fallo en descarga geoBoundaries → no hay fallback, se aborta.
    - Cualquier municipio supera 50 km centroide-cabecera → no se escribe el archivo.
    - Más de 2 grupos de polígonos compartidos → se aborta.

Uso:
    python3 scripts/build_geojson_pacifico.py

Requiere (venv del proyecto):
    pip install requests geopandas shapely

Fuente: geoBoundaries · https://www.geoboundaries.org · CC BY 4.0
"""

import json
import math
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

# ── Rutas ─────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REF_PATH     = PROJECT_ROOT / "config" / "municipios_pacifico.json"
OUT_PATH     = PROJECT_ROOT / "config" / "pacifico_municipios.geojson"

# ── Constantes ─────────────────────────────────────────────────────────────────

# CTM12 — CRS métrico oficial de Colombia (IGAC/DANE, PROJ ≥ 6).
# Alternativa si la instalación no lo soporta: EPSG:3116 (MAGNA-SIRGAS Bogotá).
METRIC_CRS  = "EPSG:9377"

MAX_DIST_KM = 50.0   # umbral de abort en validación centroide vs cabecera
MAX_SHARED  = 6      # máximo de grupos de polígonos compartidos tolerados.
                    # geoBoundaries tiene 6 pares de municipios con polígono fusionado:
                    # 5 en Chocó (municipios de DIVIPOLA reciente) + 1 en Valle del Cauca.

GB_ADM2_API = "https://www.geoboundaries.org/api/current/gbOpen/COL/ADM2/"

# ── Helpers ───────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R    = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a    = (math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def load_reference() -> dict:
    """Devuelve dict cod_municipio → {nombre, departamento, lat, lon}."""
    with open(REF_PATH, encoding="utf-8") as f:
        return json.load(f)["municipios"]


# ── Descarga ───────────────────────────────────────────────────────────────────

def _download_url(url: str, label: str) -> gpd.GeoDataFrame:
    print(f"  Descargando {label}: {url}")
    r = requests.get(url, timeout=180, stream=True)
    r.raise_for_status()
    tmp   = tempfile.NamedTemporaryFile(mode="wb", suffix=".geojson", delete=False)
    total = 0
    for chunk in r.iter_content(chunk_size=65536):
        tmp.write(chunk)
        total += len(chunk)
    tmp.close()
    print(f"  {total / 1024 / 1024:.1f} MB → procesando con geopandas…")
    gdf = gpd.read_file(tmp.name).to_crs("EPSG:4326")
    os.unlink(tmp.name)
    return gdf


def download_adm2() -> gpd.GeoDataFrame:
    meta = requests.get(GB_ADM2_API, timeout=30).json()
    return _download_url(meta["gjDownloadURL"], "ADM2 (municipios)")


# ── Estrategia C ──────────────────────────────────────────────────────────────

def match_by_cabecera(
    gdf_adm2: gpd.GeoDataFrame,
    by_code: dict,
) -> dict[str, int]:
    """
    Para cada uno de los 179 códigos canónicos en by_code, encuentra el
    polígono geoBoundaries ADM2 que CONTIENE la cabecera municipal.
    Si ningún polígono contiene el punto (cabecera costera, brecha topológica,
    municipio disputado), usa el polígono MÁS CERCANO en CRS métrico.

    Devuelve: dict cod_municipio → índice entero en gdf_adm2 (después de
    reset_index). El mismo índice puede aparecer para dos códigos si comparten
    geometría (p.ej. 27493 y 27615).
    """
    SEP = "─" * 64
    print(f"\n{SEP}")
    print("Estrategia C: cabecera-anchored polygon matching")
    print(SEP)

    # GeoDataFrame de cabeceras (una por código canónico)
    gdf_cab = gpd.GeoDataFrame(
        [{"cod_municipio": cod, "geometry": Point(info["lon"], info["lat"])}
         for cod, info in by_code.items()],
        geometry="geometry",
        crs="EPSG:4326",
    )

    # ADM2 con índice entero limpio para acceso reproducible
    gdf_adm2_clean = gdf_adm2[["geometry"]].reset_index(drop=True)

    # ── Paso 1: cabecera WITHIN polygon ───────────────────────────────────────
    # how="left" garantiza que todas las cabeceras aparecen en el resultado;
    # las que no caen dentro de ningún polígono tienen index_right = NaN.
    # Si una cabecera cae en la frontera exacta de dos polígonos, sjoin puede
    # devolver múltiples filas: tomamos la primera ocurrencia por cod_municipio.
    joined = gpd.sjoin(gdf_cab, gdf_adm2_clean, how="left", predicate="within")
    joined_dedup = joined.drop_duplicates(subset="cod_municipio", keep="first")

    assignment: dict[str, int] = {}
    unmatched:  list[str]       = []

    for _, row in joined_dedup.iterrows():
        cod       = row["cod_municipio"]
        idx_right = row.get("index_right")
        if pd.notna(idx_right):
            assignment[cod] = int(idx_right)
        else:
            unmatched.append(cod)

    print(f"  Paso 1 (cabecera within polígono) : {len(assignment):3d} asignados")
    print(f"  Pendientes para nearest           : {len(unmatched):3d}")

    # ── Paso 2: nearest polygon para cabeceras no cubiertas ───────────────────
    # Se proyecta a CRS métrico antes de calcular distancias para evitar sesgo
    # de latitud que ocurre al medir en grados (EPSG:4326).
    if unmatched:
        print(f"\n  Paso 2 (nearest en {METRIC_CRS}):")
        try:
            gdf_adm2_metric = gdf_adm2_clean.to_crs(METRIC_CRS)
        except Exception:
            print(f"  EPSG:9377 no disponible — usando EPSG:3116 (MAGNA-SIRGAS Bogotá)")
            gdf_adm2_metric = gdf_adm2_clean.to_crs("EPSG:3116")

        gdf_unmatched = (
            gdf_cab[gdf_cab["cod_municipio"].isin(unmatched)]
            .copy()
            .to_crs(gdf_adm2_metric.crs)
        )

        for _, row in gdf_unmatched.iterrows():
            cod     = row["cod_municipio"]
            pt      = row["geometry"]
            dists   = gdf_adm2_metric.geometry.distance(pt)
            idx     = int(dists.idxmin())
            dist_km = float(dists.iloc[idx]) / 1000.0
            nombre  = by_code[cod]["nombre"]
            print(f"    {cod} {nombre:<32s} → adm2 idx {idx:5d}, dist {dist_km:6.1f} km")
            assignment[cod] = idx

    print(f"\n  Total asignados: {len(assignment)} / {len(by_code)}")
    return assignment


# ── Detección de polígonos compartidos ────────────────────────────────────────

def check_shared_polygons(
    assignment: dict[str, int],
    by_code: dict,
) -> set[str]:
    """
    Detecta grupos de municipios asignados al mismo polígono ADM2.
    Registra los grupos encontrados y aborta si superan MAX_SHARED.

    Devuelve: conjunto de cod_municipio involucrados en algún grupo compartido.
    """
    poly_to_codes: dict[int, list[str]] = defaultdict(list)
    for cod, idx in assignment.items():
        poly_to_codes[idx].append(cod)

    shared_groups = {idx: codes for idx, codes in poly_to_codes.items() if len(codes) > 1}
    shared_codes: set[str] = set()

    print(f"\n  Polígonos compartidos: {len(shared_groups)} grupo(s)")
    for idx, codes in shared_groups.items():
        names = [f"{c} {by_code[c]['nombre']}" for c in sorted(codes)]
        print(f"    ADM2 idx {idx}: {' | '.join(names)}")
        print(f"    → Ambos features conservan la misma geometría (representación cartográfica honesta)")
        shared_codes.update(codes)

    if len(shared_groups) > MAX_SHARED:
        print(f"\n  ❌ STOP: {len(shared_groups)} grupos compartidos (máximo permitido: {MAX_SHARED}).")
        print("  Esto indica un problema de cobertura en geoBoundaries. Revisar manualmente.")
        sys.exit(1)

    return shared_codes


# ── Validación centroide vs cabecera ─────────────────────────────────────────

def validate_distances(
    gdf_final: gpd.GeoDataFrame,
    by_code: dict,
    shared_codes: set[str],
) -> None:
    """
    Calcula la distancia haversine entre el centroide de cada polígono y la
    cabecera de referencia. Aborta si algún municipio NO compartido supera
    MAX_DIST_KM. Los municipios con polígono compartido se reportan por
    separado (su centroide puede alejarse de la cabecera por diseño).
    """
    bins: dict = {"lt5": 0, "b5_20": 0, "b20_50": 0, "gt50": [], "shared": []}

    for _, row in gdf_final.iterrows():
        geom = row["geometry"]
        if geom is None or (hasattr(geom, "is_empty") and geom.is_empty):
            continue
        cod  = row["cod_municipio"]
        info = by_code.get(cod)
        if not info:
            continue
        cen  = geom.centroid
        dist = haversine_km(cen.y, cen.x, info["lat"], info["lon"])

        if cod in shared_codes:
            bins["shared"].append((cod, info["nombre"], round(dist, 1)))
            continue

        if   dist < 5:   bins["lt5"]    += 1
        elif dist < 20:  bins["b5_20"]  += 1
        elif dist < 50:  bins["b20_50"] += 1
        else:            bins["gt50"].append((cod, info["nombre"], round(dist, 1)))

    SEP = "─" * 64
    print(f"\n{SEP}")
    print("VALIDACIÓN CENTROIDE vs CABECERA")
    print(f"  dist  <  5 km  : {bins['lt5']}")
    print(f"  dist  5–20 km  : {bins['b5_20']}")
    print(f"  dist 20–50 km  : {bins['b20_50']}")
    print(f"  dist  > 50 km  : {len(bins['gt50'])}")

    if bins["shared"]:
        print(f"\n  Polígono compartido (no incluido en bins anteriores):")
        for cod, nom, dist in bins["shared"]:
            note = "aceptable — polígono compartido por diseño"
            print(f"    {cod} {nom}: {dist} km  ← {note}")

    if bins["gt50"]:
        print("\n  ❌ STOP: los siguientes municipios superan el umbral de 50 km:")
        for cod, nom, dist in sorted(bins["gt50"], key=lambda x: -x[2]):
            print(f"    {cod} {nom}: {dist} km")
        print("\n  El archivo NO fue escrito. Revisar cobertura geoBoundaries.")
        sys.exit(1)

    print("\n  ✅ Todos los municipios sin polígono compartido están dentro de 50 km")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    SEP = "─" * 64
    print(SEP)
    print("build_geojson_pacifico.py  (Estrategia C — cabecera-anchored)")
    print(SEP)

    by_code      = load_reference()
    target_codes = set(by_code.keys())
    print(f"→ Referencia: {len(target_codes)} municipios esperados")

    # ── Descarga geoBoundaries ─────────────────────────────────────────────────
    # Sin fallback: si falla la descarga, no usamos datos anteriores ni nombres.
    print("\n→ Consultando geoBoundaries API…")
    try:
        adm2_raw = download_adm2()
    except Exception as exc:
        print(f"\n❌ STOP: fallo en descarga geoBoundaries — {exc}")
        print("  No hay fallback. Corregir conectividad y reintentar.")
        sys.exit(1)

    print(f"→ Colombia ADM2: {len(adm2_raw)} features\n")

    # ── Estrategia C ──────────────────────────────────────────────────────────
    assignment = match_by_cabecera(adm2_raw, by_code)

    # ── Detección de polígonos compartidos ────────────────────────────────────
    shared_codes = check_shared_polygons(assignment, by_code)

    # ── Construir GeoDataFrame de salida ──────────────────────────────────────
    # Propiedades: siempre desde municipios_pacifico.json (nunca desde geoBoundaries)
    # para evitar el problema simétrico de "nombre incorrecto en polígono correcto".
    adm2_indexed = adm2_raw[["geometry"]].reset_index(drop=True)

    rows = []
    for cod in sorted(target_codes):
        info     = by_code[cod]
        adm2_idx = assignment.get(cod)
        geom     = adm2_indexed.loc[adm2_idx, "geometry"] if adm2_idx is not None else None
        rows.append({
            "cod_municipio": cod,
            "municipio":     info["nombre"],
            "departamento":  info["departamento"],
            "geometry":      geom,
        })

    gdf_final = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # ── Validación de recuento ─────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("VALIDACIÓN FINAL")
    n_with = gdf_final["geometry"].notna().sum()
    n_null = gdf_final["geometry"].isna().sum()
    print(f"  Features con polígono : {n_with}")
    print(f"  Features sin polígono : {n_null}  (geometry=null en el GeoJSON)")
    print(f"  Total features output : {len(gdf_final)}")
    print(f"  Municipios esperados  : {len(target_codes)}")

    if len(gdf_final) != len(target_codes):
        print(f"\n  ❌ STOP: feature count {len(gdf_final)} ≠ {len(target_codes)}")
        sys.exit(1)

    # ── Validación centroide vs cabecera ───────────────────────────────────────
    validate_distances(gdf_final, by_code, shared_codes)

    # ── Guardar ───────────────────────────────────────────────────────────────
    gdf_final.to_file(OUT_PATH, driver="GeoJSON")
    size_kb = OUT_PATH.stat().st_size / 1024

    print(f"\n{SEP}")
    print(f"✅  Guardado: {OUT_PATH}")
    print(f"   Tamaño  : {size_kb:.0f} KB")
    print(f"   Features: {len(gdf_final)}")
    print(f"\nPróximo paso:")
    print(f"  Abre site/test_render_acto_1_2.html con Live Server — el mapa")
    print(f"  coroplético recargará automáticamente el GeoJSON actualizado.")
    print(SEP)


if __name__ == "__main__":
    main()
