// ── Shared render helpers — loaded once, before js/acto_N.js ───────────────
// Consolidates the 13 inline renderAnchor() copies from the test_render_*.html
// prototypes into a single source, per the Phase 3 chart-mounting pass.

const getCssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/** Parses a "#rrggbb" token value into a [r,g,b] array for ramp interpolation. */
function hexToRgb(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec((hex || '').trim());
  if (!m) return [0, 0, 0];
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/**
 * Builds an anchor/copy element (PROVISIONAL prefix → amber box, else prose
 * paragraph). Returns null for empty/falsy text — callers must check before
 * inserting, so no leftover empty node is ever added to the DOM.
 */
function buildAnchorEl(text) {
  if (!text) return null;
  const PROV = 'PROVISIONAL: ';
  const isProv = text.startsWith(PROV);
  const el = document.createElement(isProv ? 'div' : 'p');
  el.className = isProv ? 'provisional-box' : 'prose';
  el.textContent = isProv ? text.slice(PROV.length) : text;
  return el;
}

/**
 * Renders anchor/intro copy into an explicit container (unlike the prototypes,
 * which hardcoded #anchor-wrapper — index.html mounts vary per chart).
 * Empty/falsy text renders nothing (no leftover empty node).
 */
function renderAnchor(container, text) {
  if (!container) return;
  const el = buildAnchorEl(text);
  if (el) container.appendChild(el);
}

/** Removes the pre-mount placeholder styling once a chart/card has rendered. */
function clearPlaceholder(el) {
  if (!el) return;
  el.classList.remove('viz-placeholder', 'viz-placeholder--map', 'viz-placeholder--full', 'viz-placeholder--aside', 'viz-placeholder--stats');
}

// ── Stat-card renderer (shared by acto_1.js, acto_2.js, acto_3.js, acto_4.js) ──
// Ported from test_render_phase_3a_stat_cards.html's renderStatCard(). Only the
// card grid is mounted into index.html — title/anchor/caveat already exist as
// static, approved copy in the page and are not duplicated here.

function formatStatValue(value, format) {
  if (value === null || value === undefined) return '—';
  if (format === 'text') return String(value);

  if (format === 'pct_split' && typeof value === 'object') {
    const nna = Number(value.nna_pct).toLocaleString('es', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const adu = Number(value.adultas_pct).toLocaleString('es', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    return `NNA ${nna} % · Adultas ${adu} %`;
  }

  const num = Number(value);
  const ES = 'es';

  switch (format) {
    case 'integer':
      return num.toLocaleString(ES, { useGrouping: false, maximumFractionDigits: 0 });
    case 'integer_thousands':
      return num.toLocaleString(ES, { useGrouping: true, maximumFractionDigits: 0 });
    case 'percent_1d':
      return num.toLocaleString(ES, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %';
    case 'decimal_2':
    case 'rate_100k':
    case 'decimal_2d':
      return num.toLocaleString(ES, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    case 'ratio_x_to_1':
      return num.toLocaleString(ES, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '×';
    default:
      return String(value);
  }
}

function renderStatCard(card) {
  const el = document.createElement('div');
  el.className = 'stat-card';

  if (card.badge) {
    const badge = document.createElement('span');
    badge.className = 'card-badge';
    badge.textContent = card.badge;
    el.appendChild(badge);
  }

  const isTextSized = card.display_format === 'text' || card.display_format === 'pct_split';
  const valEl = document.createElement('div');
  valEl.className = 'card-value' + (isTextSized ? ' card-value--text' : '');
  valEl.textContent = formatStatValue(card.value, card.display_format);
  el.appendChild(valEl);

  const labelEl = document.createElement('div');
  labelEl.className = 'card-label';
  labelEl.textContent = card.label_es;
  el.appendChild(labelEl);

  if (card.sub_value !== null && card.sub_value !== undefined) {
    const sv = card.sub_value;
    const svEl = document.createElement('div');
    svEl.className = 'card-subvalue';
    svEl.textContent = sv.value !== null
      ? formatStatValue(sv.value, 'percent_1d') + ' — ' + sv.label_es
      : sv.label_es;
    el.appendChild(svEl);
  }

  return el;
}

/**
 * Fetches `file`, reads `data[key]`, mounts anchor copy above the row (if
 * present), the stat_cards grid itself, and caveat copy below (if present).
 * Missing anchor_text_es/caveat_es simply render nothing (buildAnchorEl guard).
 */
async function mountStatRow(container, file, key) {
  if (!container) return;
  try {
    const res = await fetch(file);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const sub = data[key];
    if (!sub || !Array.isArray(sub.stat_cards)) throw new Error(`${key}: stat_cards missing`);

    const anchorEl = buildAnchorEl(sub.anchor_text_es);
    if (anchorEl) container.before(anchorEl);

    sub.stat_cards.forEach(card => container.appendChild(renderStatCard(card)));
    clearPlaceholder(container);

    // A 4th card wraps alone onto a new row under the auto-fit grid (3-up
    // fits, 4-up doesn't) — force a clean 2×2 instead of a 3+1 orphan.
    container.classList.toggle('stat-row--2col', sub.stat_cards.length === 4);

    const caveatEl = buildAnchorEl(sub.caveat_es);
    if (caveatEl) {
      caveatEl.classList.add('prose--muted-small');
      container.after(caveatEl);
    }
  } catch (err) {
    console.error(`mountStatRow(${key}) failed:`, err);
  }
}
