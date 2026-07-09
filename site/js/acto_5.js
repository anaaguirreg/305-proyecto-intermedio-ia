// ── Acto 5 — Tu Municipio (Ficha + Clasificador IA) ─────────────────────────
// Ported from test_render_acto_5.html. Diagnóstico block excluded. C31 (the
// hardcoded <h1>Acto 5 — Ficha Municipal</h1>) and C32 (the literal
// "Pass 2.C: sparkline…" process text) are deliberately not reproduced —
// index.html already has its own real "Tu municipio" heading.
// Reuses the shared renderStatCard/formatStatValue/buildAnchorEl/clearPlaceholder
// from render_helpers.js rather than redeclaring local copies.

(function () {
  const MUNICIPIOS_URL = './data/acto_5_municipios.json';
  const FICHA_URL      = './data/acto_5_ficha_forense_municipal.json';
  const MODELO_URL     = './data/modelo_clasificador.json';
  const CONFIG_URL     = './config/master_exporter_config.json';

  const CSS = {
    canvas:      getCssVar('--color-canvas'),
    body:        getCssVar('--color-body'),
    muted:       getCssVar('--color-muted'),
    mutedSoft:   getCssVar('--color-muted-soft'),
    hairline:    getCssVar('--color-hairline'),
    primaryMid:  getCssVar('--color-primary-mid'),
  };

  const STATE = {
    municipios: null, ficha: null, modelo: null, config: null, selectedMun: null,
  };

  let SPARKLINE_CHART = null;
  let CONTRIBUTIONS_CHART = null;

  function resolveNarrative(template, narrativeValues) {
    return template.replace(/\{(\w+)\}/g, (match, key) => {
      const val = narrativeValues[key + '_placeholder'];
      return val !== undefined ? val : match;
    });
  }

  function getUrlParams() {
    const sp = new URLSearchParams(window.location.search);
    return { dep: sp.get('dep') || '', mun: sp.get('mun') || '' };
  }
  function setUrlParams(dep, mun) {
    const sp = new URLSearchParams();
    if (dep) sp.set('dep', dep);
    if (mun) sp.set('mun', mun);
    history.replaceState(null, '', '?' + sp.toString());
  }
  function deptKey(dept) { return dept.nombre_es.toUpperCase(); }

  // ── DOM skeleton (built once, before data arrives) ────────────────────────
  let els = {};
  function buildSkeleton(root) {
    root.innerHTML = '';

    const loading = document.createElement('div');
    loading.className = 'load-msg';
    loading.textContent = 'Cargando datos…';
    root.appendChild(loading);

    const errorBlock = document.createElement('div');
    errorBlock.className = 'load-error';
    errorBlock.hidden = true;
    root.appendChild(errorBlock);

    const app = document.createElement('div');
    app.hidden = true;

    const selectorBar = document.createElement('div');
    selectorBar.className = 'selector-bar';
    const labelDept = document.createElement('label');
    labelDept.textContent = 'Departamento';
    labelDept.htmlFor = 'acto5-dept-select';
    const selDept = document.createElement('select');
    selDept.id = 'acto5-dept-select';
    selDept.name = 'acto5-dept-select';
    const labelMun = document.createElement('label');
    labelMun.textContent = 'Municipio';
    labelMun.htmlFor = 'acto5-mun-select';
    const selMun = document.createElement('select');
    selMun.id = 'acto5-mun-select';
    selMun.name = 'acto5-mun-select';
    selectorBar.append(labelDept, selDept, labelMun, selMun);
    app.appendChild(selectorBar);

    const mainContent = document.createElement('div');

    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';
    emptyState.textContent = 'Selecciona un municipio para ver su ficha.';
    mainContent.appendChild(emptyState);

    const munPanel = document.createElement('div');
    munPanel.hidden = true;

    const munHeader = document.createElement('div');
    munHeader.className = 'mun-header';
    const excludedBanner = document.createElement('div');
    excludedBanner.className = 'excluded-banner';
    excludedBanner.hidden = true;
    const narrativeBanner = document.createElement('div');
    narrativeBanner.className = 'narrative-banner';
    narrativeBanner.hidden = true;
    const statCardsGrid = document.createElement('div');
    statCardsGrid.className = 'card-grid';
    munPanel.append(munHeader, excludedBanner, narrativeBanner, statCardsGrid);

    const chartsGrid = document.createElement('div');
    chartsGrid.className = 'charts-grid';

    const sparkPanel = document.createElement('div');
    sparkPanel.className = 'chart-panel';
    const sparkTitle = document.createElement('div');
    sparkTitle.className = 'chart-panel-title';
    sparkTitle.textContent = 'ICV-GEN-F histórico';
    const sparklineContainer = document.createElement('div');
    sparklineContainer.className = 'chart-container';
    sparkPanel.append(sparkTitle, sparklineContainer);

    const contribPanel = document.createElement('div');
    contribPanel.className = 'chart-panel';
    const contribTitle = document.createElement('div');
    contribTitle.className = 'chart-panel-title';
    contribTitle.textContent = 'Contribución al clasificador';
    const contributionsContainer = document.createElement('div');
    contributionsContainer.className = 'chart-container';
    const contributionsNa = document.createElement('div');
    contributionsNa.className = 'contributions-na';
    contributionsNa.style.display = 'none';
    contributionsNa.textContent = 'Este municipio no ingresa al modelo de clasificación por subregistro estructural en los datos policiales.';
    const contributionsCaption = document.createElement('small');
    contributionsCaption.className = 'contributions-caption';
    contributionsCaption.style.display = 'none';
    contributionsCaption.textContent = 'Este gráfico revela qué indicadores pesaron más en la clasificación del municipio. Los valores positivos empujan hacia alta severidad; los negativos hacia moderada-baja.';
    contribPanel.append(contribTitle, contributionsContainer, contributionsNa, contributionsCaption);

    chartsGrid.append(sparkPanel, contribPanel);
    munPanel.appendChild(chartsGrid);

    const forensicSection = document.createElement('div');
    forensicSection.className = 'forensic-section';
    const forensicTitle = document.createElement('div');
    forensicTitle.className = 'forensic-section-title';
    forensicTitle.textContent = 'Perfil forense local';
    const forensicDisclaimer = document.createElement('p');
    forensicDisclaimer.className = 'forensic-disclaimer';
    forensicDisclaimer.style.display = 'none';
    const forensicContent = document.createElement('div');
    forensicSection.append(forensicTitle, forensicDisclaimer, forensicContent);
    munPanel.appendChild(forensicSection);

    const widgetSection = document.createElement('div');
    widgetSection.className = 'widget-section';
    const widgetTitle = document.createElement('div');
    widgetTitle.className = 'widget-section-title';
    widgetTitle.textContent = 'Clasificador IA — Simula tu municipio';
    const sliderGrid = document.createElement('div');
    sliderGrid.className = 'slider-grid';
    const widgetPrediction = document.createElement('div');
    widgetPrediction.className = 'widget-prediction';
    const predLabel = document.createElement('span');
    predLabel.className = 'widget-pred-label';
    predLabel.textContent = 'Clasificación inferida:';
    const predResult = document.createElement('span');
    predResult.className = 'widget-pred-result';
    predResult.textContent = '—';
    const predProb = document.createElement('span');
    predProb.className = 'widget-pred-prob';
    widgetPrediction.append(predLabel, predResult, predProb);
    const widgetCaveat = document.createElement('p');
    widgetCaveat.className = 'widget-caveat';
    widgetCaveat.innerHTML = 'Ajusta los deslizadores para simular escenarios. El modelo usa log1p + RobustScaler + regresión logística (F1-Macro CV&nbsp;=&nbsp;0.9769).';
    widgetSection.append(widgetTitle, sliderGrid, widgetPrediction, widgetCaveat);
    munPanel.appendChild(widgetSection);

    const closingSection = document.createElement('div');
    closingSection.className = 'closing-section';
    const closingTeaser = document.createElement('div');
    closingTeaser.className = 'closing-teaser';
    const closingNotAvailable = document.createElement('p');
    closingNotAvailable.className = 'closing-not-available';
    closingNotAvailable.hidden = true;
    closingNotAvailable.textContent = 'Narrativa de cierre no disponible para municipios excluidos del modelo.';
    const closingToggle = document.createElement('button');
    closingToggle.className = 'closing-toggle';
    closingToggle.hidden = true;
    closingToggle.textContent = 'Ver modelo de prevención';
    const closingModelContent = document.createElement('div');
    closingModelContent.className = 'closing-model-content';
    closingModelContent.hidden = true;
    closingSection.append(closingTeaser, closingNotAvailable, closingToggle, closingModelContent);
    munPanel.appendChild(closingSection);

    mainContent.appendChild(munPanel);
    app.appendChild(mainContent);
    root.appendChild(app);

    els = {
      loading, errorBlock, app, selDept, selMun, emptyState, munPanel,
      munHeader, excludedBanner, narrativeBanner, statCardsGrid,
      sparklineContainer, contributionsContainer, contributionsNa, contributionsCaption,
      forensicDisclaimer, forensicContent,
      sliderGrid, predResult, predProb,
      closingTeaser, closingNotAvailable, closingToggle, closingModelContent,
    };
  }

  // ── selectors ──────────────────────────────────────────────────────────
  function buildDeptSelector(departamentos, defaultDep) {
    const sel = els.selDept;
    sel.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '— Selecciona departamento —';
    placeholder.disabled = true;
    sel.appendChild(placeholder);
    departamentos.forEach(dept => {
      const opt = document.createElement('option');
      opt.value = dept.nombre_es.toUpperCase();
      opt.textContent = dept.nombre_es;
      sel.appendChild(opt);
    });
    sel.value = defaultDep || '';
  }

  function buildMunSelector(deptValue, defaultMun) {
    const state = STATE.municipios;
    const munMap = state.municipios;
    const sel = els.selMun;
    sel.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = '— Selecciona tu municipio —';
    sel.appendChild(placeholder);
    if (!deptValue) return;
    const dept = state.departamentos_disponibles.find(d => deptKey(d) === deptValue);
    if (!dept) return;
    const entries = dept.municipios_codigos
      .filter(cod => munMap[cod])
      .map(cod => ({ cod, nombre: munMap[cod].nombre_es }))
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
    entries.forEach(({ cod, nombre }) => {
      const opt = document.createElement('option');
      opt.value = cod;
      opt.textContent = nombre;
      sel.appendChild(opt);
    });
    if (defaultMun && dept.municipios_codigos.includes(defaultMun)) sel.value = defaultMun;
  }

  // ── charts ────────────────────────────────────────────────────────────
  function ensureCharts() {
    if (!SPARKLINE_CHART) {
      SPARKLINE_CHART = echarts.init(els.sparklineContainer);
      window.addEventListener('resize', () => SPARKLINE_CHART.resize());
    }
    if (!CONTRIBUTIONS_CHART) {
      CONTRIBUTIONS_CHART = echarts.init(els.contributionsContainer);
      window.addEventListener('resize', () => CONTRIBUTIONS_CHART.resize());
    }
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => { SPARKLINE_CHART.resize(); CONTRIBUTIONS_CHART.resize(); });
    }
  }

  function updateSparkline(mun) {
    const spark = mun.sparkline_icv;
    if (!spark) return;
    SPARKLINE_CHART.setOption({
      backgroundColor: 'transparent',
      grid: { left: 10, right: 10, top: 16, bottom: 30, containLabel: true },
      tooltip: { trigger: 'axis', formatter: params => `<strong>${params[0].axisValue}</strong><br>ICV-GEN-F: ${Number(params[0].value).toFixed(2)}` },
      xAxis: { type: 'category', data: spark.years, axisLabel: { fontSize: 10, color: CSS.muted }, axisLine: { lineStyle: { color: CSS.hairline } }, splitLine: { show: false } },
      yAxis: { type: 'value', axisLabel: { fontSize: 10, color: CSS.muted, formatter: v => v.toFixed(0) }, splitLine: { lineStyle: { color: CSS.canvas } } },
      series: [{ type: 'line', data: spark.values, smooth: true, symbol: 'circle', symbolSize: 4, lineStyle: { width: 2, color: CSS.primaryMid }, itemStyle: { color: CSS.primaryMid }, areaStyle: { color: 'rgba(123, 31, 75, 0.08)' } }],
    });
  }

  function updateContributions(mun) {
    const contribsRaw = mun.coefficient_contributions;
    if (!contribsRaw) {
      els.contributionsContainer.style.display = 'none';
      els.contributionsNa.style.display = 'flex';
      els.contributionsCaption.style.display = 'none';
      CONTRIBUTIONS_CHART.clear();
      return;
    }
    els.contributionsContainer.style.display = '';
    els.contributionsNa.style.display = 'none';
    els.contributionsCaption.style.display = '';

    const contribs = [...contribsRaw].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
    const labels = contribs.map(c => c.feature_label_es);
    const values = contribs.map(c => c.contribution);
    const colors = values.map(v => (v >= 0 ? CSS.primaryMid : CSS.mutedSoft));
    const fmtN = v => v.toFixed(3);

    CONTRIBUTIONS_CHART.setOption({
      backgroundColor: 'transparent',
      grid: { left: 10, right: 55, top: 8, bottom: 8, containLabel: true },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: params => {
          const c = contribs[params[0].dataIndex];
          return [`<strong>${c.feature_label_es}</strong>`, `Coeficiente: ${fmtN(c.coefficient)}`, `Valor estandarizado: ${fmtN(c.standardized_value)}`, `Contribución: ${fmtN(c.contribution)}`].join('<br>');
        },
      },
      xAxis: { type: 'value', axisLabel: { fontSize: 10, color: CSS.muted, formatter: v => v.toFixed(1) }, splitLine: { lineStyle: { color: CSS.canvas } } },
      yAxis: { type: 'category', data: labels, inverse: true, axisLabel: { fontSize: 11, color: CSS.body, width: 120, overflow: 'truncate' } },
      series: [{ type: 'bar', data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i] } })), label: { show: true, position: 'right', formatter: p => fmtN(p.value), fontSize: 10, color: CSS.muted } }],
    });
  }

  // ── forensic profile ──────────────────────────────────────────────────
  function renderForensicProfile(cod) {
    const contentEl = els.forensicContent;
    const disclaimerEl = els.forensicDisclaimer;
    contentEl.innerHTML = '';
    disclaimerEl.style.display = 'none';

    const fichaEntry = STATE.ficha.municipios[cod];
    if (!fichaEntry) {
      const msg = document.createElement('p');
      msg.className = 'forensic-no-coverage';
      msg.textContent = 'Cobertura forense insuficiente para perfilamiento local (< 30 casos peritados)';
      contentEl.appendChild(msg);
      return;
    }

    const hasVS = fichaEntry.has_violencia_sexual_profile;
    const hasVIF = fichaEntry.has_vif_profile;

    if (hasVS || hasVIF) {
      const text = STATE.ficha.metadata.data_source_disclaimer_es;
      if (text) { disclaimerEl.textContent = text; disclaimerEl.style.display = ''; }
    }

    function renderDim(label, perfil) {
      const block = document.createElement('div');
      block.className = 'forensic-dim';
      const header = document.createElement('div');
      header.className = 'forensic-dim-header';
      const labelSpan = document.createElement('span');
      labelSpan.textContent = label;
      header.appendChild(labelSpan);
      if (perfil && perfil.total_casos != null) {
        const badge = document.createElement('span');
        badge.className = 'forensic-total-badge';
        badge.textContent = `${perfil.total_casos.toLocaleString('es')} casos`;
        header.appendChild(badge);
      }
      block.appendChild(header);
      if (!perfil) {
        const note = document.createElement('p');
        note.className = 'forensic-no-dim';
        note.textContent = 'Sin cobertura suficiente en esta dimensión (< 30 casos peritados).';
        block.appendChild(note);
        return block;
      }
      const grid = document.createElement('div');
      grid.className = 'forensic-card-grid';
      (perfil.stat_cards || []).forEach(card => grid.appendChild(renderStatCard(card)));
      block.appendChild(grid);
      return block;
    }

    contentEl.appendChild(renderDim('Violencia sexual', hasVS ? fichaEntry.violencia_sexual : null));
    const divider = document.createElement('hr');
    divider.className = 'forensic-dim-divider';
    contentEl.appendChild(divider);
    contentEl.appendChild(renderDim('Violencia intrafamiliar', hasVIF ? fichaEntry.violencia_intrafamiliar : null));
  }

  // ── classifier widget ──────────────────────────────────────────────────
  function getFeatureRange(featureId) {
    const munMap = STATE.municipios.municipios;
    const cardId = featureId.replace(/_f$/, '');
    const vals = Object.values(munMap)
      .map(m => {
        const card = m.stat_cards && m.stat_cards.find(c => c.id === cardId);
        return (card && card.value !== null) ? Number(card.value) : null;
      })
      .filter(v => v !== null && !isNaN(v))
      .sort((a, b) => a - b);
    if (!vals.length) return { min: 0, max: 1000 };
    const n = vals.length;
    const p1 = vals[Math.max(0, Math.floor(n * 0.01))];
    const p99 = vals[Math.min(n - 1, Math.floor(n * 0.99))];
    return { min: Math.max(0, Math.floor(p1)), max: Math.ceil(p99) };
  }

  function runClassifier(featureValues) {
    const m = STATE.modelo;
    const center = m.preprocessing.robust_scaler.center;
    const scale = m.preprocessing.robust_scaler.scale;
    const coef = m.coefficients;
    let z = m.intercept;
    for (let i = 0; i < 4; i++) {
      const xl = Math.log(1 + featureValues[i]);
      z += coef[i] * (xl - center[i]) / scale[i];
    }
    const p = 1 / (1 + Math.exp(-z));
    const cls = p >= m.decision_threshold ? 1 : 0;
    return { p, cls, label: m.classes[String(cls)] };
  }

  function updatePrediction() {
    const sliders = els.sliderGrid.querySelectorAll('input[type="range"]');
    if (!sliders.length) return;
    const vals = Array.from(sliders).map(s => Number(s.value));
    const { p, label } = runClassifier(vals);
    els.predResult.textContent = label;
    els.predProb.textContent = `(p = ${(p * 100).toFixed(1)} %)`;
  }

  function renderWidget(mun) {
    const modelo = STATE.modelo;
    const gridEl = els.sliderGrid;
    gridEl.innerHTML = '';
    const features = modelo.features;
    const labels = modelo.features_labels_es;

    features.forEach(fid => {
      const range = getFeatureRange(fid);
      const cardId = fid.replace(/_f$/, '');
      const card = mun.stat_cards && mun.stat_cards.find(c => c.id === cardId);
      const rawVal = (card && card.value !== null) ? Number(card.value) : null;
      const initVal = rawVal !== null
        ? Math.max(range.min, Math.min(range.max, Math.round(rawVal)))
        : Math.round((range.min + range.max) / 2);

      const row = document.createElement('div');
      row.className = 'slider-row';
      const header = document.createElement('div');
      header.className = 'slider-row-header';
      const sliderId = `acto5-slider-${fid}`;
      const lbl = document.createElement('label');
      lbl.className = 'slider-label';
      lbl.textContent = labels[fid] || fid;
      lbl.htmlFor = sliderId;
      const rangeLbl = document.createElement('span');
      rangeLbl.className = 'slider-range-label';
      rangeLbl.textContent = `p1: ${range.min} — p99: ${range.max}`;
      header.append(lbl, rangeLbl);
      row.appendChild(header);

      const input = document.createElement('input');
      input.type = 'range';
      input.id = sliderId;
      input.name = sliderId;
      input.min = range.min;
      input.max = range.max;
      input.step = 1;
      input.value = initVal;
      row.appendChild(input);

      const display = document.createElement('div');
      display.className = 'slider-value-display';
      display.textContent = initVal.toLocaleString('es', { maximumFractionDigits: 0 });
      row.appendChild(display);

      input.addEventListener('input', () => {
        display.textContent = Number(input.value).toLocaleString('es', { maximumFractionDigits: 0 });
        updatePrediction();
      });

      gridEl.appendChild(row);
    });

    updatePrediction();
  }

  // ── closing narrative ──────────────────────────────────────────────────
  function renderClosingNarrative(mun) {
    const { closingTeaser, closingToggle, closingModelContent, closingNotAvailable } = els;
    closingTeaser.textContent = '';
    closingModelContent.innerHTML = '';
    closingModelContent.hidden = true;
    closingToggle.hidden = true;
    closingToggle.textContent = 'Ver modelo de prevención';
    closingNotAvailable.hidden = true;

    const a5cfg = STATE.config ? STATE.config.acto_5_municipios : null;
    if (!a5cfg || mun.excluido_del_modelo || mun.cluster_id === null) {
      closingNotAvailable.hidden = false;
      return;
    }

    const clusterStr = String(mun.cluster_id);
    const hallazgoTmpl = (a5cfg.closing_hallazgo_by_cluster_es || {})[clusterStr] || '';
    const hallazgo = hallazgoTmpl.replace(/\{dominant_violence_type\}/g, mun.dominant_violence_type_es || 'N/D');
    const modeloPrevencion = ((a5cfg.closing_modelo_prevencion_by_cluster_es || {})[clusterStr]) || '';
    const teaserText = (a5cfg.closing_teaser_template_es || '')
      .replace(/\{municipio\}/g, mun.nombre_es)
      .replace(/\{hallazgo\}/g, hallazgo)
      .replace(/\{modelo_prevencion\}/g, modeloPrevencion);
    closingTeaser.textContent = teaserText;

    const modelHtml = mun.cluster_id === 1 ? a5cfg.prevention_model_alta_html_es : a5cfg.prevention_model_moderada_html_es;
    if (modelHtml) {
      closingModelContent.innerHTML = modelHtml;
      closingToggle.hidden = false;
      closingToggle.onclick = () => {
        const isOpen = !closingModelContent.hidden;
        closingModelContent.hidden = isOpen;
        closingToggle.textContent = isOpen ? 'Ver modelo de prevención' : 'Ocultar modelo de prevención';
      };
    }
  }

  // ── render selected municipality ───────────────────────────────────────
  function renderMunicipality(cod) {
    const state = STATE.municipios;
    const mun = state.municipios[cod];
    if (!mun) { showEmptyState(); return; }

    STATE.selectedMun = cod;

    els.munHeader.innerHTML = '';
    const h3 = document.createElement('h2');
    h3.textContent = mun.nombre_es;
    els.munHeader.appendChild(h3);
    const deptEl = document.createElement('div');
    deptEl.className = 'mun-dept';
    deptEl.textContent = mun.departamento_es;
    els.munHeader.appendChild(deptEl);

    if (mun.excluido_del_modelo) {
      els.excludedBanner.textContent = state.metadata.excluido_del_modelo_banner_es
        || 'Este municipio no se incluye en el modelo de clasificación por subregistro estructural.';
      els.excludedBanner.hidden = false;
    } else {
      els.excludedBanner.hidden = true;
    }

    const template = state.metadata.narrative_template_es || '';
    const isProvisional = template.startsWith('PROVISIONAL: ');
    const rawTemplate = isProvisional ? template.slice('PROVISIONAL: '.length) : template;
    const resolved = resolveNarrative(rawTemplate, mun.narrative_values_es || {});

    els.narrativeBanner.innerHTML = '';
    if (isProvisional) {
      const tag = document.createElement('span');
      tag.className = 'narrative-provisional';
      tag.textContent = 'PROVISIONAL';
      els.narrativeBanner.appendChild(tag);
    }
    const textEl = document.createElement('span');
    textEl.className = 'narrative-text';
    textEl.textContent = resolved;
    els.narrativeBanner.appendChild(textEl);
    els.narrativeBanner.hidden = false;

    els.statCardsGrid.innerHTML = '';
    (mun.stat_cards || []).forEach(card => els.statCardsGrid.appendChild(renderStatCard(card)));

    els.emptyState.hidden = true;
    els.munPanel.hidden = false;

    ensureCharts();
    updateSparkline(mun);
    updateContributions(mun);
    renderForensicProfile(cod);
    renderWidget(mun);
    renderClosingNarrative(mun);
  }

  function showEmptyState() {
    STATE.selectedMun = null;
    els.emptyState.hidden = false;
    els.munPanel.hidden = true;
  }

  function onDeptChange() {
    const deptVal = els.selDept.value;
    buildMunSelector(deptVal, '');
    showEmptyState();
    setUrlParams(deptVal, '');
  }
  function onMunChange() {
    const deptVal = els.selDept.value;
    const munVal = els.selMun.value;
    setUrlParams(deptVal, munVal);
    if (munVal) renderMunicipality(munVal); else showEmptyState();
  }

  // ── main ────────────────────────────────────────────────────────────────
  async function main() {
    const container = document.getElementById('acto-5-ficha-municipal');
    if (!container) return;

    buildSkeleton(container);

    let results;
    try {
      results = await Promise.all([
        fetch(MUNICIPIOS_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(FICHA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(MODELO_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(CONFIG_URL).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
    } catch (err) {
      els.loading.hidden = true;
      els.errorBlock.textContent = 'Error al cargar datos: ' + err.message;
      els.errorBlock.hidden = false;
      console.error('Acto 5 load error:', err);
      return;
    }

    const [municipiosData, fichaData, modeloData, configData] = results;
    STATE.municipios = municipiosData;
    STATE.ficha = fichaData;
    STATE.modelo = modeloData;
    STATE.config = configData;

    const { dep, mun } = getUrlParams();
    buildDeptSelector(municipiosData.departamentos_disponibles, dep);
    buildMunSelector(dep, mun);

    els.selDept.addEventListener('change', onDeptChange);
    els.selMun.addEventListener('change', onMunChange);

    els.loading.hidden = true;
    els.app.hidden = false;
    clearPlaceholder(container);

    if (mun && els.selMun.value === mun) {
      renderMunicipality(mun);
    } else {
      showEmptyState();
    }
  }

  main();
})();
