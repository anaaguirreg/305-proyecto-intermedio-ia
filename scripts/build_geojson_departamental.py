"""
build_geojson_departamental.py — dissolve municipal polygons into 4 departmental polygons.

Input:  config/pacifico_municipios.geojson  (179 municipal features, CRS84 / WGS84)
Output: config/pacifico_departamentos.json  (4 departmental features, same CRS)

Properties on each output feature:
  cod_departamento  — 2-digit DIVIPOLA string derived from cod_municipio[:2]
  departamento      — uppercase name matching MasterExporter convention

Safe to re-run: overwrites output file in place.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from shapely.ops import unary_union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH   = PROJECT_ROOT / "config" / "pacifico_municipios.geojson"
OUTPUT_PATH  = PROJECT_ROOT / "config" / "pacifico_departamentos.json"


def main() -> None:
    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    gdf = gpd.read_file(INPUT_PATH)
    print(f"Input: {len(gdf)} municipal features from {INPUT_PATH.name}")

    required_cols = {"cod_municipio", "departamento"}
    missing = required_cols - set(gdf.columns)
    if missing:
        raise ValueError(f"Missing expected columns in source GeoJSON: {missing}")

    # ------------------------------------------------------------------
    # Derive cod_departamento (first 2 digits of cod_municipio)
    # ------------------------------------------------------------------
    gdf["cod_departamento"] = gdf["cod_municipio"].str[:2]

    # ------------------------------------------------------------------
    # Dissolve: one polygon per department via unary_union of geometries
    # ------------------------------------------------------------------
    dept_groups = gdf.groupby("departamento")
    features: list[dict] = []

    for departamento, group in sorted(dept_groups):
        cod_dep = group["cod_departamento"].iloc[0]
        dissolved_geom = unary_union(group.geometry.values)

        feature = {
            "type": "Feature",
            "properties": {
                "cod_departamento": cod_dep,
                "departamento":     departamento,
            },
            "geometry": json.loads(gpd.GeoSeries([dissolved_geom]).to_json())
                            ["features"][0]["geometry"],
        }
        features.append(feature)

        # Sanity check: area in decimal degrees (rough plausibility only)
        area_dd = dissolved_geom.area
        print(f"  {cod_dep}  {departamento}: "
              f"{len(group)} municipalities dissolved → "
              f"area ≈ {area_dd:.4f} sq-deg")

    if len(features) != 4:
        raise ValueError(f"Expected 4 departmental features, got {len(features)}")

    # ------------------------------------------------------------------
    # Build FeatureCollection and write
    # ------------------------------------------------------------------
    feature_collection = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }

    OUTPUT_PATH.write_text(
        json.dumps(feature_collection, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"\nOutput: {len(features)} departmental features → {OUTPUT_PATH}")
    print("Sanity: output feature count == 4:", len(features) == 4)


if __name__ == "__main__":
    main()
