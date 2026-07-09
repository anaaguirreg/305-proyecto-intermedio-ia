"""
Regression guard: prevents site/ from serving stale JSONs.
If this test fails, run `bash scripts/sync_to_site.sh` and re-commit.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_JSON_FILES = [
    "acto_1_panorama.json",
    "acto_2_brechas.json",
    "acto_3_tipologia.json",
    "acto_4_forense.json",
    "acto_5_ficha_forense_municipal.json",
    "acto_5_municipios.json",
    "modelo_clasificador.json",
]

_CONFIG_FILES = [
    "pacifico_municipios.geojson",
    "municipios_pacifico.json",
    "master_exporter_config.json",
    "forense_exporter_config.json",
]


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("filename", _JSON_FILES)
def test_json_synced(filename: str) -> None:
    src  = PROJECT_ROOT / "data" / "dashboard" / filename
    dest = PROJECT_ROOT / "site" / "data" / filename
    assert src.exists(),  f"canonical source missing: {src}"
    assert dest.exists(), f"site copy missing — run bash scripts/sync_to_site.sh: {dest}"
    assert _md5(src) == _md5(dest), (
        f"{filename}: site copy is stale — run bash scripts/sync_to_site.sh\n"
        f"  src  md5={_md5(src)}\n"
        f"  dest md5={_md5(dest)}"
    )


@pytest.mark.parametrize("filename", _CONFIG_FILES)
def test_config_synced(filename: str) -> None:
    src  = PROJECT_ROOT / "config" / filename
    dest = PROJECT_ROOT / "site" / "config" / filename
    assert src.exists(),  f"canonical config missing: {src}"
    assert dest.exists(), f"site config copy missing — run bash scripts/sync_to_site.sh: {dest}"
    assert _md5(src) == _md5(dest), (
        f"{filename}: site/config copy is stale — run bash scripts/sync_to_site.sh\n"
        f"  src  md5={_md5(src)}\n"
        f"  dest md5={_md5(dest)}"
    )
