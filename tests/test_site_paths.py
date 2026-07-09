"""
Regression guard: catches stale ../data/dashboard/ or ../config/ path
literals in site/**/*.html. These only break once the site is served from
site/ as its own root (e.g. GitHub Pages) — md5 sync tests check file
contents, not path literals, so this closes that gap.
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = PROJECT_ROOT / "site"

_STALE_PATTERNS = ["../data/dashboard/", "../config/"]


def _html_files() -> list[Path]:
    return sorted(SITE_DIR.rglob("*.html"))


@pytest.mark.parametrize("html_path", _html_files(), ids=lambda p: str(p.relative_to(SITE_DIR)))
def test_no_stale_relative_paths(html_path: Path) -> None:
    text = html_path.read_text(encoding="utf-8")
    hits = [pattern for pattern in _STALE_PATTERNS if pattern in text]
    assert not hits, (
        f"{html_path.relative_to(SITE_DIR)}: stale path literal(s) {hits} — "
        f"use ./data/ or ./config/ instead (site/ is served as its own root)"
    )
