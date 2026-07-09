#!/usr/bin/env bash
# sync_to_site.sh
# Sync canonical dashboard JSONs and config files from repo to site/.
# Run AFTER regenerating any exporter output, BEFORE git commit.
#
# Usage: bash scripts/sync_to_site.sh [--help]

set -euo pipefail

if [[ "${1-}" == "--help" ]]; then
  echo "Sync canonical dashboard JSONs and config files from repo to site/."
  echo "Run AFTER regenerating any exporter output, BEFORE git commit."
  exit 0
fi

# ── Detect md5 command (macOS: md5, Linux: md5sum) ───────────────────────────
if command -v md5sum &>/dev/null; then
  md5_file() { md5sum "$1" | awk '{print $1}'; }
elif command -v md5 &>/dev/null; then
  md5_file() { md5 -q "$1"; }
else
  echo "ERROR: neither md5sum nor md5 found — cannot verify copies." >&2
  exit 1
fi

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_JSON="$REPO_ROOT/data/dashboard"
DEST_JSON="$REPO_ROOT/site/data"
SRC_CFG="$REPO_ROOT/config"
DEST_CFG="$REPO_ROOT/site/config"

mkdir -p "$DEST_JSON"
mkdir -p "$DEST_CFG"

# ── File lists ────────────────────────────────────────────────────────────────
JSON_FILES=(
  acto_1_panorama.json
  acto_2_brechas.json
  acto_3_tipologia.json
  acto_4_forense.json
  acto_5_ficha_forense_municipal.json
  acto_5_municipios.json
  modelo_clasificador.json
)

CONFIG_FILES=(
  pacifico_municipios.geojson
  municipios_pacifico.json
  master_exporter_config.json
  forense_exporter_config.json
)

# ── Copy + verify helper ──────────────────────────────────────────────────────
PASS_COUNT=0
FAIL_COUNT=0

copy_and_verify() {
  local src="$1"
  local dest="$2"
  local fname
  fname="$(basename "$src")"

  if [[ ! -f "$src" ]]; then
    echo "ERROR: source missing: $src" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf "  %-50s  %10s  %10s  %s\n" "$fname" "MISSING" "—" "FAIL"
    return 1
  fi

  cp "$src" "$dest"

  local src_md5 dest_md5 src_size dest_size
  src_md5="$(md5_file "$src")"
  dest_md5="$(md5_file "$dest")"
  src_size="$(wc -c < "$src" | tr -d ' ')"
  dest_size="$(wc -c < "$dest" | tr -d ' ')"

  if [[ "$src_md5" == "$dest_md5" ]]; then
    PASS_COUNT=$((PASS_COUNT + 1))
    printf "  %-50s  %10s  %10s  %s\n" "$fname" "$src_size" "$dest_size" "OK"
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf "  %-50s  %10s  %10s  %s\n" "$fname" "$src_size" "$dest_size" "MD5 MISMATCH" >&2
    return 1
  fi
}

# ── Print header ──────────────────────────────────────────────────────────────
printf "\n%-52s  %10s  %10s  %s\n" "File" "Src bytes" "Dest bytes" "Status"
printf "%s\n" "$(printf '─%.0s' {1..80})"

# ── Sync JSON files ───────────────────────────────────────────────────────────
for fname in "${JSON_FILES[@]}"; do
  copy_and_verify "$SRC_JSON/$fname" "$DEST_JSON/$fname"
done

# ── Sync config files ─────────────────────────────────────────────────────────
for fname in "${CONFIG_FILES[@]}"; do
  copy_and_verify "$SRC_CFG/$fname" "$DEST_CFG/$fname"
done

# ── Summary ───────────────────────────────────────────────────────────────────
printf "%s\n" "$(printf '─%.0s' {1..80})"
TOTAL=$((PASS_COUNT + FAIL_COUNT))
echo ""
echo "Result: $PASS_COUNT/$TOTAL files synced and md5-verified."

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  echo "SYNC FAILED: $FAIL_COUNT file(s) had errors." >&2
  exit 1
fi

echo "All files OK — site/ is up to date."
