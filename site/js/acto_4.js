// ── Acto 4 — La Anatomía Forense ────────────────────────────────────────────
// Ported from test_render_acto_4_{2,3,4,5}.html. Diagnóstico blocks and
// buildDiagnostico() are excluded. All charts mount inside the existing
// .viz-panel light cards already present in index.html around each mount —
// panel styling itself is untouched.

(function () {
  const FORENSE_URL = './data/acto_4_forense.json';
  const CFG_URL     = './config/forense_exporter_config.json';

  const CSS = {
    canvas:      getCssVar('--color-canvas'),
    ink:         getCssVar('--color-ink'),
    body:        getCssVar('--color-body'),
    muted:       getCssVar('--color-muted'),
    mutedSoft:   getCssVar('--color-muted-soft'),
    hairline:    getCssVar('--color-hairline'),
    primary:     getCssVar('--color-primary'),
    primaryMid:  getCssVar('--color-primary-mid'),
    error:       getCssVar('--color-error'),
    scale1:      getCssVar('--scale-1'),
    scale2:      getCssVar('--scale-2'),
    scale3:      getCssVar('--scale-3'),
    scale4:      getCssVar('--scale-4'),
    scaleNull:   getCssVar('--scale-null'),
  };

  const PROV_COLON  = 'PROVISIONAL: ';
  function stripProv(s) { return s && s.startsWith(PROV_COLON) ? s.slice(PROV_COLON.length) : (s || ''); }

  // ── sub_acto_4_3 — El agresor (Sankey DS3/DS4) ────────────────────────────
  function getNodeColor(node, dsColors) {
    const { column, label } = node;
    if (column === 1) return dsColors.col1[label] ?? CSS.hairline;
    if (column === 2) return dsColors.col2_overrides[label] ?? dsColors.col2_default;
    return label === 'NO_REGISTRADO' ? dsColors.col3_no_registrado : dsColors.col3_default;
  }

  function computeFlowSum(scope) {
    return scope.links.filter(lk => lk.source.startsWith('1__')).reduce((s, lk) => s + lk.value, 0);
  }

  function buildSankeyOption(scope, dsKey, viz) {
    const dsColors = viz[`${dsKey}_colors`];
    const nodeMap = new Map(scope.nodes.map(n => [n.id, n]));
    const linkPctMap = new Map(scope.links.map(lk => [`${lk.source}|${lk.target}`, lk.pct_within_ciclo]));
    const nodes = scope.nodes.map(n => ({ name: n.id, itemStyle: { color: getNodeColor(n, dsColors) } }));
    const links = scope.links.map(lk => ({ source: lk.source, target: lk.target, value: lk.value }));

    return {
      tooltip: {
        trigger: 'item', confine: true,
        formatter: params => {
          const d = params.data;
          if (!d) return '';
          if ('source' in d && 'target' in d) {
            const srcInfo = nodeMap.get(d.source);
            const tgtInfo = nodeMap.get(d.target);
            const srcLabel = srcInfo?.label ?? d.source.replace(/^\d+__/, '');
            const tgtLabel = tgtInfo?.label ?? d.target.replace(/^\d+__/, '');
            let html = `${srcLabel} → ${tgtLabel}<br>Casos: ${d.value.toLocaleString('es')}`;
            if (!d.source.startsWith('2__')) {
              const pct = linkPctMap.get(`${d.source}|${d.target}`) ?? 0;
              if (pct > 0) html += `<br>${pct.toFixed(1)}% de víctimas de este ciclo vital`;
            }
            return html;
          }
          const info = nodeMap.get(d.name);
          const label = info?.label ?? (d.name ?? '').replace(/^\d+__/, '');
          const n = info?.n_cases;
          return `<strong>${label}</strong><br>Casos: ${n != null ? n.toLocaleString('es') : '—'}`;
        },
      },
      series: [{
        type: 'sankey', animation: false, emphasis: { focus: 'adjacency' },
        nodeWidth: 16, nodeGap: 8, orient: 'horizontal',
        left: '1%', right: '22%', top: '2%', bottom: '2%',
        lineStyle: { color: 'source', opacity: viz.link_opacity },
        label: {
          fontSize: 10, color: CSS.ink,
          formatter: params => {
            const info = nodeMap.get(params.name);
            return info?.label ?? params.name.replace(/^\d+__/, '');
          },
        },
        data: nodes, links: links,
      }],
    };
  }

  async function mountSankey() {
    const container = document.getElementById('acto-4-sankey');
    if (!container) return;
    try {
      const acto4 = await fetch(FORENSE_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = acto4.sub_acto_4_3;
      const meta = acto4.metadata;
      const viz = sub.visualization;
      const DS_LABELS = { ds3: 'Violencia sexual', ds4: 'Violencia física intrafamiliar' };

      container.innerHTML = '';

      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(anchorP);

      if (meta.act_disclaimer_es) {
        const bar = document.createElement('p');
        bar.className = 'prose prose--muted-small';
        bar.textContent = meta.act_disclaimer_es;
        container.appendChild(bar);
      }

      const row = document.createElement('div');
      row.className = 'sankey-row';

      function buildCol(dsKey, badgeClass, badgeText) {
        const col = document.createElement('div');
        col.className = 'sankey-col';
        const header = document.createElement('div');
        header.className = 'ds-header';
        const name = document.createElement('span');
        name.className = 'ds-name';
        name.textContent = DS_LABELS[dsKey];
        const badge = document.createElement('span');
        badge.className = 'ds-badge ' + badgeClass;
        badge.textContent = badgeText;
        header.appendChild(name);
        header.appendChild(badge);

        const colLabels = document.createElement('div');
        colLabels.className = 'col-labels';
        const titles = viz.column_titles || {};
        ['col1', 'col2', 'col3'].forEach(key => {
          const span = document.createElement('span');
          span.textContent = titles[key] ?? '';
          colLabels.appendChild(span);
        });

        const chartDiv = document.createElement('div');
        chartDiv.className = 'sankey-chart';

        const metaP = document.createElement('div');
        metaP.className = 'sankey-meta';

        col.appendChild(header);
        col.appendChild(colLabels);
        col.appendChild(chartDiv);
        col.appendChild(metaP);
        return { col, chartDiv, metaP };
      }

      const ds3 = buildCol('ds3', 'badge-ds3', 'DS3 · seforense');
      const ds4 = buildCol('ds4', 'badge-ds4', 'DS4 · forense');
      row.appendChild(ds3.col);
      row.appendChild(ds4.col);
      container.appendChild(row);
      clearPlaceholder(container);

      const chartDs3 = echarts.init(ds3.chartDiv);
      const chartDs4 = echarts.init(ds4.chartDiv);
      chartDs3.setOption(buildSankeyOption(sub.ds3.regional, 'ds3', viz));
      chartDs4.setOption(buildSankeyOption(sub.ds4.regional, 'ds4', viz));

      const flow3 = computeFlowSum(sub.ds3.regional);
      const flow4 = computeFlowSum(sub.ds4.regional);
      const pct3 = (flow3 / sub.ds3.regional.n_total * 100).toFixed(1);
      const pct4 = (flow4 / sub.ds4.regional.n_total * 100).toFixed(1);
      ds3.metaP.textContent = `${flow3.toLocaleString('es')} casos renderizados (${pct3}% del universo con agresor registrado · n_filtrable=${sub.ds3.regional.n_total.toLocaleString('es')}).`;
      ds4.metaP.textContent = `${flow4.toLocaleString('es')} casos renderizados (${pct4}% del universo con agresor registrado · n_filtrable=${sub.ds4.regional.n_total.toLocaleString('es')}).`;

      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { chartDs3.resize(); chartDs4.resize(); });
      window.addEventListener('resize', () => { chartDs3.resize(); chartDs4.resize(); });
    } catch (err) {
      console.error('acto-4-sankey mount failed:', err);
    }
  }

  // ── sub_acto_4_2 — El hogar como escenario (heatmaps + selector) ─────────
  function flattenMatrix(matrix) {
    const cells = [];
    for (let d = 0; d < matrix.length; d++) {
      for (let m = 0; m < matrix[d].length; m++) cells.push([m, d, matrix[d][m]]);
    }
    return cells;
  }

  function buildHeatmapOption(heatmapBlock, deptKey) {
    const entry = heatmapBlock.by_department[deptKey];
    const cells = flattenMatrix(entry.matrix);
    const maxVal = Math.max(...cells.map(c => c[2]));
    return {
      backgroundColor: 'transparent',
      grid: { left: 82, right: 14, top: 54, bottom: 54 },
      tooltip: { trigger: 'item', formatter: p => `${heatmapBlock.axis_days[p.data[1]]} / ${heatmapBlock.axis_months[p.data[0]]}<br>${p.data[2]} casos` },
      xAxis: { type: 'category', data: heatmapBlock.axis_months, axisLabel: { rotate: 30, fontSize: 9 }, splitArea: { show: true } },
      yAxis: { type: 'category', data: heatmapBlock.axis_days, axisLabel: { fontSize: 10 }, splitArea: { show: true } },
      visualMap: {
        min: 0, max: maxVal || 1, calculable: true, orient: 'horizontal',
        left: 'center', top: 0, itemHeight: 80, textStyle: { fontSize: 10 },
        inRange: { color: [CSS.scale1, CSS.scale2, CSS.scale3, CSS.scale4, CSS.error] },
      },
      series: [{ type: 'heatmap', data: cells, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.3)' } } }],
    };
  }

  function buildEscenarioOption(escBlock, deptKey) {
    const entry = escBlock.by_department[deptKey];
    const cats = entry.categories.map(c => c.replace(/_/g, ' '));
    const vifPct = entry.vif_pct, sexPct = entry.sexual_pct;
    const totalVIF = entry.total_vif, totSex = entry.total_sexual;
    const COLOR_VIF = CSS.primary, COLOR_SEXUAL = CSS.primary;
    return {
      backgroundColor: 'transparent',
      grid: { left: 215, right: 80, top: 36, bottom: 44 },
      legend: { data: [`VIF (n=${totalVIF.toLocaleString('es')})`, `Sexual (n=${totSex.toLocaleString('es')})`], top: 5, textStyle: { fontSize: 10 } },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: params => `<strong>${cats[params[0].dataIndex]}</strong><br>` + params.map(p => `${p.seriesName}: ${(+p.value).toFixed(1)}%`).join('<br>'),
      },
      xAxis: { type: 'value', max: Math.ceil(Math.max(...vifPct, ...sexPct) / 10) * 10 + 5, axisLabel: { formatter: v => v + '%', fontSize: 9 }, splitLine: { lineStyle: { color: CSS.hairline } } },
      yAxis: { type: 'category', data: cats, inverse: true, axisLabel: { width: 202, overflow: 'truncate', fontSize: 10 } },
      series: [
        { name: `VIF (n=${totalVIF.toLocaleString('es')})`, type: 'bar', data: vifPct, itemStyle: { color: COLOR_VIF }, label: { show: true, position: 'right', fontSize: 9, color: CSS.body, formatter: p => (+p.value).toFixed(1) + '%' } },
        { name: `Sexual (n=${totSex.toLocaleString('es')})`, type: 'bar', data: sexPct, itemStyle: { color: COLOR_SEXUAL, opacity: 0.5 }, label: { show: true, position: 'right', fontSize: 9, color: CSS.body, formatter: p => (+p.value).toFixed(1) + '%' } },
      ],
    };
  }

  async function mountHeatmap() {
    const container = document.getElementById('acto-4-heatmap');
    if (!container) return;
    try {
      const [payload, fullCfg] = await Promise.all([
        fetch(FORENSE_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(CFG_URL).then(r => r.json()).catch(() => ({})),
      ]);
      const sub = payload.sub_acto_4_2;
      const copy = fullCfg?.copy_es?.sub_acto_4_2 ?? {};

      container.innerHTML = '';
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(anchorP);

      const selectorRow = document.createElement('div');
      selectorRow.className = 'selector-row';
      const selLabel = document.createElement('label');
      selLabel.className = 'selector-label';
      selLabel.textContent = copy.selector_labels_es?.label || 'Departamento';
      selLabel.htmlFor = 'acto4-dept-select';
      const select = document.createElement('select');
      select.className = 'dept-select';
      select.id = 'acto4-dept-select';
      select.name = 'acto4-dept-select';
      selectorRow.appendChild(selLabel);
      selectorRow.appendChild(select);
      container.appendChild(selectorRow);

      function buildPanel(defaultHeader) {
        const panel = document.createElement('div');
        panel.className = 'forense-chart-panel';
        const header = document.createElement('div');
        header.className = 'chart-header';
        header.textContent = defaultHeader;
        const metaEl = document.createElement('div');
        metaEl.className = 'chart-meta';
        const chartEl = document.createElement('div');
        chartEl.className = 'chart-el';
        chartEl.style.height = '260px';
        const caveatEl = document.createElement('p');
        caveatEl.className = 'caveat-note';
        caveatEl.hidden = true;
        panel.appendChild(header);
        panel.appendChild(metaEl);
        panel.appendChild(chartEl);
        panel.appendChild(caveatEl);
        return { panel, header, metaEl, chartEl, caveatEl };
      }

      const panelTitles = copy.panel_titles_es ?? {};
      const pVif = buildPanel(stripProv(panelTitles.heatmap_vif || 'VIF — día × mes'));
      const pSexual = buildPanel(stripProv(panelTitles.heatmap_sexual || 'Sexual — día × mes'));
      const pEscenario = buildPanel(stripProv(panelTitles.escenario || 'Escenario del hecho — VIF vs Sexual'));
      pEscenario.chartEl.style.height = '320px';

      container.appendChild(pVif.panel);
      container.appendChild(pSexual.panel);
      container.appendChild(pEscenario.panel);
      clearPlaceholder(container);

      const chartHeatmapVIF = echarts.init(pVif.chartEl);
      const chartHeatmapSexual = echarts.init(pSexual.chartEl);
      const chartEscenario = echarts.init(pEscenario.chartEl);

      const heatmapVIF = sub.heatmap_vif, heatmapSexual = sub.heatmap_sexual, escenario = sub.escenario;

      function updatePeak(metaEl, peak, totalCases) {
        metaEl.textContent = !peak
          ? `n = ${totalCases.toLocaleString('es')} casos`
          : `n = ${totalCases.toLocaleString('es')} casos — pico: ${peak.day} / ${peak.month} (${peak.value} casos)`;
      }
      function updateCaveat(caveatEl, caveatEs) {
        if (caveatEs) { caveatEl.textContent = stripProv(caveatEs); caveatEl.hidden = false; }
        else { caveatEl.hidden = true; caveatEl.textContent = ''; }
      }

      function updateAllCharts(deptKey) {
        chartHeatmapVIF.setOption(buildHeatmapOption(heatmapVIF, deptKey), true);
        chartHeatmapSexual.setOption(buildHeatmapOption(heatmapSexual, deptKey), true);
        chartEscenario.setOption(buildEscenarioOption(escenario, deptKey), true);

        const vifEntry = heatmapVIF.by_department[deptKey];
        const sexEntry = heatmapSexual.by_department[deptKey];
        const escEntry = escenario.by_department[deptKey];

        updatePeak(pVif.metaEl, vifEntry.peak, vifEntry.total_cases);
        updatePeak(pSexual.metaEl, sexEntry.peak, sexEntry.total_cases);
        updateCaveat(pVif.caveatEl, vifEntry.caveat_es);
        updateCaveat(pSexual.caveatEl, sexEntry.caveat_es);
        updateCaveat(pEscenario.caveatEl, escEntry.caveat_es);
      }

      const selLabels = copy.selector_labels_es ?? {};
      sub.departments_available.forEach(key => {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = selLabels[key] || (key === 'regional' ? 'Regional' : key);
        select.appendChild(opt);
      });
      select.value = sub.aggregation_default || 'regional';

      updateAllCharts(select.value);
      select.addEventListener('change', () => updateAllCharts(select.value));

      const allHeatmapCharts = [chartHeatmapVIF, chartHeatmapSexual, chartEscenario];
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => allHeatmapCharts.forEach(c => c.resize()));
      window.addEventListener('resize', () => allHeatmapCharts.forEach(c => c.resize()));
    } catch (err) {
      console.error('acto-4-heatmap mount failed:', err);
    }
  }

  // ── sub_acto_4_4 — El factor y la circunstancia (treemaps) ───────────────
  function buildTreemapOption(items, colorRange) {
    const data = items.map(d => ({
      name: d.category.replace(/_/g, ' '), value: d.n, _pct: d.pct,
      label: { show: true, formatter: p => `${p.name}\n${p.data._pct}%`, fontSize: 11, color: CSS.canvas, textShadowBlur: 3, textShadowColor: 'rgba(0,0,0,0.5)' },
    }));
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', formatter: p => `<strong>${p.name}</strong><br>${p.value.toLocaleString('es')} casos (${p.data._pct}%)` },
      series: [{
        type: 'treemap', data: data, width: '100%', height: '100%', top: 0, left: 0,
        squareRatio: 1, nodeClick: false, roam: false, breadcrumb: { show: false },
        label: { show: true, formatter: p => `${p.name}\n${p.data._pct}%`, fontSize: 11, color: CSS.canvas },
        upperLabel: { show: false },
        itemStyle: { gapWidth: 2, borderColor: CSS.canvas, borderWidth: 1 },
        levels: [{ colorSaturation: [0.35, 0.75], itemStyle: { gapWidth: 2, borderWidth: 1, borderColor: CSS.canvas }, color: colorRange, colorMappingBy: 'value' }],
        emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold' }, itemStyle: { borderColor: CSS.canvas, borderWidth: 2 } },
      }],
    };
  }

  async function mountTreemap() {
    const container = document.getElementById('acto-4-factor');
    if (!container) return;
    try {
      const [payload, fullCfg] = await Promise.all([
        fetch(FORENSE_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(CFG_URL).then(r => r.json()).catch(() => ({})),
      ]);
      const sub = payload.sub_acto_4_4;
      const copyCfg = fullCfg?.copy_es?.sub_acto_4_4 ?? {};

      container.innerHTML = '';
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(anchorP);

      const row = document.createElement('div');
      row.className = 'two-read';

      function buildTreemapCol() {
        const col = document.createElement('div');
        const title = document.createElement('div');
        title.className = 'chart-label';
        const chartEl = document.createElement('div');
        chartEl.style.cssText = 'width:100%;height:360px;';
        const metaEl = document.createElement('div');
        metaEl.className = 'chart-meta';
        col.appendChild(title);
        col.appendChild(chartEl);
        col.appendChild(metaEl);
        return { col, title, chartEl, metaEl };
      }

      const ds4Col = buildTreemapCol();
      const ds3Col = buildTreemapCol();
      row.appendChild(ds4Col.col);
      row.appendChild(ds3Col.col);
      container.appendChild(row);
      clearPlaceholder(container);

      const titlesData = sub.titles_es ?? {};
      const titlesConf = { ds4: copyCfg.ds4_title, ds3: copyCfg.ds3_title };
      ds4Col.title.textContent = titlesData.ds4 || titlesConf.ds4 || 'DS4 — Factor (VIF forense)';
      const ds3Title = titlesData.ds3 || titlesConf.ds3;
      if (ds3Title) { ds3Col.title.textContent = ds3Title; } else { ds3Col.title.remove(); }

      const ds4Items = sub.ds4_factor.regional;
      const ds3Items = sub.ds3_circumstance.regional;
      const ds4Total = ds4Items.reduce((s, d) => s + d.n, 0);
      const ds3Total = ds3Items.reduce((s, d) => s + d.n, 0);

      const rampDs4 = [getCssVar('--ramp-forense-ds4-start'), getCssVar('--ramp-forense-ds4-end')];
      const rampDs3 = [getCssVar('--ramp-forense-ds3-start'), getCssVar('--ramp-forense-ds3-end')];

      const chartDS4 = echarts.init(ds4Col.chartEl);
      chartDS4.setOption(buildTreemapOption(ds4Items, rampDs4));
      const chartDS3 = echarts.init(ds3Col.chartEl);
      chartDS3.setOption(buildTreemapOption(ds3Items, rampDs3));

      ds4Col.metaEl.textContent = `n = ${ds4Total.toLocaleString('es')} casos forenses DS4 — vista regional`;
      ds3Col.metaEl.textContent = `n = ${ds3Total.toLocaleString('es')} casos forenses DS3 — vista regional`;

      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { chartDS4.resize(); chartDS3.resize(); });
      window.addEventListener('resize', () => { chartDS4.resize(); chartDS3.resize(); });
    } catch (err) {
      console.error('acto-4-factor mount failed:', err);
    }
  }

  // ── sub_acto_4_5 — Interseccionalidad ─────────────────────────────────────
  const CAT_ORDER = ['SIN_PERTENENCIA_ETNICA', 'AFRO_NARP', 'NO_REGISTRADO', 'INDIGENA', 'GITANO'];
  const CAT_LABELS = {
    SIN_PERTENENCIA_ETNICA: 'Sin pertenencia declarada',
    AFRO_NARP: 'Afro-NARP',
    NO_REGISTRADO: 'No registrado',
    INDIGENA: 'Indígena',
    GITANO: 'Gitano/Rrom',
  };

  function renderIntersecCard(card, variant) {
    const el = document.createElement('div');
    el.className = variant === 'finding' ? 'stat-card stat-card--finding'
      : variant === 'ethnicity' ? 'stat-card stat-card--ethnicity'
      : 'stat-card';

    if (card.badge) {
      const badge = document.createElement('span');
      badge.className = 'card-badge';
      badge.textContent = card.badge;
      el.appendChild(badge);
    }
    const valEl = document.createElement('div');
    valEl.className = 'card-value';
    valEl.textContent = formatStatValue(card.value, card.display_format);
    el.appendChild(valEl);

    const labelEl = document.createElement('div');
    labelEl.className = 'card-label';
    labelEl.textContent = card.label_es;
    el.appendChild(labelEl);

    if (variant === 'finding' && card.n_base != null) {
      const nbEl = document.createElement('div');
      nbEl.className = 'card-n-base';
      nbEl.textContent = 'n = ' + card.n_base.toLocaleString('es') + ' casos peritados';
      el.appendChild(nbEl);
    }
    return el;
  }

  function buildEthnicityChartOption(marginalsDs3, marginalsDs4) {
    function byEtnia(rows) { const m = {}; rows.forEach(r => { m[r.dimension_etnia] = r; }); return m; }
    const mapDs3 = byEtnia(marginalsDs3);
    const mapDs4 = byEtnia(marginalsDs4);
    const lowN = new Set();
    [...marginalsDs3, ...marginalsDs4].forEach(r => { if (r.low_n_flag) lowN.add(r.dimension_etnia); });

    const ETH_COLORS = {
      SIN_PERTENENCIA_ETNICA: CSS.scaleNull,
      AFRO_NARP: CSS.primaryMid,
      NO_REGISTRADO: CSS.scale2,
      INDIGENA: CSS.scale3,
      GITANO: CSS.scale4,
    };

    const series = CAT_ORDER.map(cat => {
      const labelText = CAT_LABELS[cat] + (lowN.has(cat) ? ' *' : '');
      const ds3Row = mapDs3[cat] || { pct_of_female_cases: 0, n_cases_f: 0 };
      const ds4Row = mapDs4[cat] || { pct_of_female_cases: 0, n_cases_f: 0 };
      return {
        name: labelText, type: 'bar', stack: 'total', itemStyle: { color: ETH_COLORS[cat] },
        data: [
          { value: ds4Row.pct_of_female_cases, itemStyle: { color: ETH_COLORS[cat] }, nCasesF: ds4Row.n_cases_f },
          { value: ds3Row.pct_of_female_cases, itemStyle: { color: ETH_COLORS[cat] }, nCasesF: ds3Row.n_cases_f },
        ],
      };
    });

    return {
      animation: false,
      tooltip: {
        trigger: 'item',
        formatter: params => {
          const pct = params.value;
          const nCasesF = params.data && params.data.nCasesF != null ? params.data.nCasesF : null;
          const pctStr = pct != null ? pct.toLocaleString('es', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %' : '—';
          const nStr = nCasesF != null ? 'n = ' + nCasesF.toLocaleString('es') : '';
          return params.seriesName + '<br/>' + params.name + ': <b>' + pctStr + '</b>' + (nStr ? '<br/>' + nStr : '');
        },
      },
      legend: { top: 0, left: 'left', itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 11 } },
      grid: { top: 60, left: '14%', right: '4%', bottom: 10, containLabel: true },
      xAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%', fontSize: 11 } },
      yAxis: { type: 'category', data: ['VIF (DS4)', 'Delito sexual (DS3)'], axisLabel: { fontSize: 11 } },
      series,
    };
  }

  async function mountInterseccion() {
    const container = document.getElementById('acto-4-interseccion');
    if (!container) return;
    try {
      const payload = await fetch(FORENSE_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = payload.sub_acto_4_5;

      container.innerHTML = '';

      const titleEl = document.createElement('h4');
      titleEl.textContent = sub.title_es;
      container.appendChild(titleEl);
      const anchorEl = buildAnchorEl(sub.anchor_text_es);
      if (anchorEl) container.appendChild(anchorEl);

      const ethGrid = document.createElement('div');
      ethGrid.className = 'card-grid';
      [
        { badge: 'DS3 — Sexual', value: sub.ds3_stats.pct_afro_narp_f, display_format: 'percent_1d', label_es: 'Afro-NARP (víctimas femeninas, sexual forense)' },
        { badge: 'DS3 — Sexual', value: sub.ds3_stats.pct_indigena_f, display_format: 'percent_1d', label_es: 'Indígena (víctimas femeninas, sexual forense)' },
        { badge: 'DS3 — Sexual', value: sub.ds3_stats.pct_sin_pertenencia_f, display_format: 'percent_1d', label_es: 'Sin pertenencia étnica declarada (víctimas femeninas, sexual forense)' },
      ].forEach(card => ethGrid.appendChild(renderIntersecCard(card, 'ethnicity')));
      container.appendChild(ethGrid);

      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;height:220px;margin:20px 0;';
      container.appendChild(chartDiv);

      const lowNNote = document.createElement('p');
      lowNNote.className = 'low-n-note';
      if (sub.low_n_note_es) lowNNote.textContent = stripProv(sub.low_n_note_es);
      else lowNNote.hidden = true;
      container.appendChild(lowNNote);

      const anchorDisEl = buildAnchorEl(sub.anchor_disability_es);
      if (anchorDisEl) container.appendChild(anchorDisEl);

      const findGrid = document.createElement('div');
      findGrid.className = 'card-grid';
      findGrid.appendChild(renderIntersecCard({
        badge: 'DS4 — VIF', value: sub.ds4_stats.pct_disability_f, display_format: 'percent_1d',
        label_es: 'Con condición de discapacidad registrada (VIF forense)', n_base: sub.ds4_stats.n_base_f,
      }, 'finding'));
      findGrid.appendChild(renderIntersecCard({
        badge: 'DS3 — Sexual', value: sub.ds3_stats.pct_disability_f, display_format: 'percent_1d',
        label_es: 'Con condición de discapacidad registrada (sexual forense)', n_base: sub.ds3_stats.n_base_f,
      }, 'finding'));
      container.appendChild(findGrid);

      if (sub.caveat_es) {
        const caveatEl = document.createElement('p');
        caveatEl.className = 'shared-caveat';
        caveatEl.textContent = sub.caveat_es;
        container.appendChild(caveatEl);
      }

      clearPlaceholder(container);

      const chart = echarts.init(chartDiv);
      chart.setOption(buildEthnicityChartOption(sub.ethnicity_marginals.ds3, sub.ethnicity_marginals.ds4));
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-4-interseccion mount failed:', err);
    }
  }

  mountSankey();
  mountHeatmap();
  mountTreemap();
  mountInterseccion();
  mountStatRow(document.getElementById('acto-4-stat-cards'), './data/acto_4_forense.json', 'sub_acto_4_1');
})();
