// ── Acto 2 — La Fractura de Género ──────────────────────────────────────────
// Ported from test_render_acto_2_{2,3,4,5,6}.html. Diagnóstico blocks,
// buildDiagnostico(), and the supplementary HTML table in _2_3 (no mount
// exists for it in index.html) are excluded.

(function () {
  const BRECHAS_URL = './data/acto_2_brechas.json';
  const CFG_URL     = './config/master_exporter_config.json';

  const CSS = {
    canvas:      getCssVar('--color-canvas'),
    ink:         getCssVar('--color-ink'),
    body:        getCssVar('--color-body'),
    muted:       getCssVar('--color-muted'),
    hairline:    getCssVar('--color-hairline'),
    primary:     getCssVar('--color-primary'),
    primaryMid:  getCssVar('--color-primary-mid'),
    primaryDeep: getCssVar('--color-primary-deep'),
    scaleNull:   getCssVar('--scale-null'),
  };

  // sub_acto_2_2's --color-female/--color-male and sub_acto_2_6's --color-gap
  // both resolve (in the prototypes' own local :root overrides) to existing
  // shared tokens — resolved directly here rather than inventing new ones.
  const COLOR_F   = CSS.primary;
  const COLOR_M   = CSS.primary;
  const COLOR_GAP = CSS.muted;

  // ── sub_acto_2_2 — Anatomía de la brecha (butterfly, tabbed NNA/adultas) ──
  function buildButterflyOption(yearData, tab, cfg) {
    const sorted = [...yearData].sort((a, b) => b.year - a.year);
    const years  = sorted.map(d => String(d.year));
    const ratesF = sorted.map(d => +(d[tab].rate_f.toFixed(1)));
    const ratesM = sorted.map(d => -(+d[tab].rate_m.toFixed(1)));
    const axisMax = Math.ceil(Math.max(...ratesF, ...ratesF.map(v => Math.abs(v))) / 50) * 50;
    const axisLabel = cfg?.axis_labels_es ?? {};
    const legendLabel = cfg?.legend_labels_es ?? {};

    return {
      backgroundColor: 'transparent',
      grid: { left: 56, right: 70, top: 50, bottom: 48 },
      legend: { data: [legendLabel.female || 'Femenino', legendLabel.male || 'Masculino'], top: 5, textStyle: { fontSize: 11 } },
      xAxis: {
        type: 'value', min: -axisMax, max: axisMax,
        axisLabel: { formatter: v => Math.abs(v), fontSize: 10 },
        name: axisLabel.x || 'Tasa por 100.000 hab.', nameLocation: 'middle', nameGap: 30,
        nameTextStyle: { fontSize: 10, color: CSS.muted },
        splitLine: { lineStyle: { color: CSS.hairline } },
      },
      yAxis: { type: 'category', data: years, axisLabel: { fontSize: 11 } },
      series: [
        {
          name: legendLabel.female || 'Femenino', type: 'bar', stack: 'total', data: ratesF,
          itemStyle: { color: COLOR_F },
          label: { show: true, position: 'right', formatter: p => p.value > 0 ? p.value.toFixed(1) : '', fontSize: 9, color: CSS.body },
        },
        {
          name: legendLabel.male || 'Masculino', type: 'bar', stack: 'total', data: ratesM,
          itemStyle: { color: COLOR_M, opacity: 0.5 },
          label: { show: true, position: 'left', formatter: p => p.value < 0 ? Math.abs(p.value).toFixed(1) : '', fontSize: 9, color: CSS.body },
        },
      ],
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: params => {
          const year = params[0].name;
          const yearRow = yearData.find(d => String(d.year) === year);
          if (!yearRow) return year;
          const grp = yearRow[tab];
          return `<strong>${year}</strong><br>Femenino: ${grp.rate_f.toFixed(1)}<br>Masculino: ${grp.rate_m.toFixed(1)}<br>Razón F/M: ${grp.ratio.toFixed(2)}×`;
        },
      },
    };
  }

  async function mountButterfly() {
    const container = document.getElementById('acto-2-butterfly');
    if (!container) return;
    try {
      const [brechasPayload, fullCfg] = await Promise.all([
        fetch(BRECHAS_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(CFG_URL).then(r => r.json()).catch(() => ({})),
      ]);
      const sub = brechasPayload.sub_acto_2_2;
      const data = sub.data;
      const dispCfg = fullCfg?.acto_2_visualization?.sub_acto_2_2 ?? {};
      const chartTitles = dispCfg.chart_titles ?? {};
      const tabLabels = dispCfg.tab_labels ?? {};

      container.innerHTML = '';
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(anchorP);

      const tabRow = document.createElement('div');
      tabRow.className = 'tab-row';
      const btnNna = document.createElement('button');
      btnNna.className = 'tab-btn active';
      btnNna.dataset.tab = 'nna';
      btnNna.textContent = tabLabels.nna || 'NNA (0–17)';
      const btnAdults = document.createElement('button');
      btnAdults.className = 'tab-btn';
      btnAdults.dataset.tab = 'adults';
      btnAdults.textContent = tabLabels.adults || 'Mujeres adultas (18+)';
      tabRow.appendChild(btnNna);
      tabRow.appendChild(btnAdults);
      container.appendChild(tabRow);

      const row = document.createElement('div');
      row.className = 'two-read';
      const colVif = document.createElement('div');
      const titleVif = document.createElement('div');
      titleVif.className = 'chart-label';
      titleVif.textContent = chartTitles.vif || 'Violencia intrafamiliar (VIF)';
      const chartVifDiv = document.createElement('div');
      chartVifDiv.style.cssText = 'width:100%;min-height:420px;';
      colVif.appendChild(titleVif);
      colVif.appendChild(chartVifDiv);

      const colSexual = document.createElement('div');
      const titleSexual = document.createElement('div');
      titleSexual.className = 'chart-label';
      titleSexual.textContent = chartTitles.sexual || 'Violencia sexual';
      const chartSexualDiv = document.createElement('div');
      chartSexualDiv.style.cssText = 'width:100%;min-height:420px;';
      colSexual.appendChild(titleSexual);
      colSexual.appendChild(chartSexualDiv);

      row.appendChild(colVif);
      row.appendChild(colSexual);
      container.appendChild(row);
      clearPlaceholder(container);

      const chartVif = echarts.init(chartVifDiv);
      const chartSexual = echarts.init(chartSexualDiv);
      let activeTab = 'nna';
      function refresh() {
        chartVif.setOption(buildButterflyOption(data.vif, activeTab, dispCfg), true);
        chartSexual.setOption(buildButterflyOption(data.sexual, activeTab, dispCfg), true);
      }
      refresh();
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => { chartVif.resize(); chartSexual.resize(); });
      }
      window.addEventListener('resize', () => { chartVif.resize(); chartSexual.resize(); });

      tabRow.addEventListener('click', e => {
        const btn = e.target.closest('.tab-btn');
        if (!btn) return;
        activeTab = btn.dataset.tab;
        tabRow.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
        refresh();
      });
    } catch (err) {
      console.error('acto-2-butterfly mount failed:', err);
    }
  }

  // ── sub_acto_2_3 — Top 10 brecha de género (bar ranking) ──────────────────
  const fmtGap = v => (v == null ? 'no calculable' : v.toFixed(2) + '×');

  async function mountTop10Gap() {
    const container = document.getElementById('acto-2-top10');
    if (!container) return;
    try {
      const payload = await fetch(BRECHAS_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = payload.sub_acto_2_3;
      const { echarts_series, items } = sub.data;
      const BAR_COLOR = CSS.primaryMid;
      const HIGHLIGHT_BORDER = CSS.primaryDeep;

      const seriesData = echarts_series.values.map((v, i) => {
        if (v == null) return { value: 0, itemStyle: { color: CSS.scaleNull }, label: { show: true, formatter: () => 'no calculable', color: CSS.muted } };
        if (i === 0) return { value: v, itemStyle: { color: BAR_COLOR, borderColor: HIGHLIGHT_BORDER, borderWidth: 2 } };
        return v;
      });

      container.innerHTML = '';
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(anchorP);

      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;min-height:480px;';
      container.appendChild(chartDiv);
      clearPlaceholder(container);

      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 230, right: 130, top: 16, bottom: 50 },
        xAxis: {
          type: 'value', name: 'Brecha promedio (f/m)', nameLocation: 'middle', nameGap: 32,
          axisLabel: { formatter: v => v.toFixed(1) + '×', fontSize: 12, interval: 'auto' },
          splitLine: { lineStyle: { color: CSS.hairline } },
        },
        yAxis: { type: 'category', data: echarts_series.categories, inverse: true, axisLabel: { width: 215, overflow: 'truncate', fontSize: 12 } },
        series: [{
          type: 'bar', data: seriesData, color: BAR_COLOR,
          label: { show: true, position: 'right', formatter: p => fmtGap(p.value), fontSize: 11, color: CSS.body },
        }],
        tooltip: {
          trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: params => {
            const it = items[params[0].dataIndex];
            return [
              `<strong>${it.municipality}</strong> — ${it.department}`,
              `Código DANE ${it.cod_municipio} · Rango ${it.rank}`,
              `Brecha promedio: ${fmtGap(it.gap_average)}`,
              `<em>Desglose por dimensión</em>`,
              `VIF NNA: ${fmtGap(it.gap_vif_nna)}`,
              `VIF Adultas: ${fmtGap(it.gap_vif_adults)}`,
              `Sexual NNA: ${fmtGap(it.gap_sexual_nna)}`,
              `Sexual Adultas: ${fmtGap(it.gap_sexual_adults)}`,
            ].join('<br>');
          },
        },
      });
      // Layout just changed from a shared row to a full-width row — force a
      // resize once the final width settles (rAF) in addition to font-load.
      requestAnimationFrame(() => chart.resize());
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-2-top10 mount failed:', err);
    }
  }

  // ── sub_acto_2_4 — Mapa departamental de brecha de género ─────────────────
  const COLOR_LO = hexToRgb(getCssVar('--ramp-brecha-start'));
  const COLOR_HI = hexToRgb(getCssVar('--ramp-brecha-end'));
  function gapColor(gap, min, max) {
    const t = max > min ? Math.max(0, Math.min(1, (gap - min) / (max - min))) : 0.5;
    const r = Math.round(COLOR_LO[0] + t * (COLOR_HI[0] - COLOR_LO[0]));
    const g = Math.round(COLOR_LO[1] + t * (COLOR_HI[1] - COLOR_LO[1]));
    const b = Math.round(COLOR_LO[2] + t * (COLOR_HI[2] - COLOR_LO[2]));
    return `rgb(${r},${g},${b})`;
  }

  async function mountDeptMap() {
    const container = document.getElementById('acto-2-map');
    if (!container) return;
    try {
      const payload = await fetch(BRECHAS_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = payload.sub_acto_2_4;
      const data = sub.data;
      const deptMap = new Map(data.departments.map(d => [d.department, d]));
      const { min, max } = data.gap_range;

      container.innerHTML = '';
      const titleEl = document.createElement('h4');
      titleEl.textContent = sub.title_es;
      container.appendChild(titleEl);

      const mapDiv = document.createElement('div');
      mapDiv.style.cssText = 'width:100%;min-height:420px;';
      container.appendChild(mapDiv);

      if (sub.caveat_es) {
        const caveatP = document.createElement('p');
        caveatP.className = 'prose prose--muted-small';
        caveatP.textContent = sub.caveat_es;
        container.appendChild(caveatP);
      }
      clearPlaceholder(container);

      const leafletMap = L.map(mapDiv).setView([3.8, -76.8], 6);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(leafletMap);

      L.geoJSON(data.geojson, {
        style: feature => {
          const deptName = feature.properties.department;
          const row = deptMap.get(deptName);
          const isHighlight = deptName === data.highlighted_department;
          return {
            fillColor: row ? gapColor(row.gap_average, min, max) : CSS.scaleNull,
            fillOpacity: 0.82, color: CSS.ink,
            weight: isHighlight ? 3 : 0.8, opacity: isHighlight ? 1 : 0.35,
          };
        },
        onEachFeature: (feature, layer) => {
          const deptName = feature.properties.department;
          const row = deptMap.get(deptName);
          if (row) {
            layer.bindPopup(
              `<strong>${deptName}</strong><br>Brecha promedio: <strong>${row.gap_average.toFixed(2)}×</strong> (F/M)<br>` +
              `Rango regional: ${min.toFixed(2)}× – ${max.toFixed(2)}×<br>Municipios: ${row.n_municipalities} · En Top 10: ${row.n_in_top10}` +
              (row.is_highlighted ? '<br><em>Departamento destacado</em>' : '')
            );
          }
          layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.95 }));
          layer.on('mouseout',  () => layer.setStyle({ fillOpacity: 0.82 }));
        },
      }).addTo(leafletMap);

      const legendCtrl = L.control({ position: 'bottomright' });
      legendCtrl.onAdd = () => {
        const div = L.DomUtil.create('div', 'dept-legend');
        const sorted = [...data.departments].sort((a, b) => b.gap_average - a.gap_average);
        let html = '<strong>Brecha F/M promedio</strong>';
        for (const d of sorted) {
          const color = gapColor(d.gap_average, min, max);
          const swatchClass = d.department === data.highlighted_department ? 'swatch swatch-highlight' : 'swatch';
          html += `<br><span class="${swatchClass}" style="background:${color}"></span>${d.department}: ${d.gap_average.toFixed(2)}×`;
        }
        div.innerHTML = html;
        return div;
      };
      legendCtrl.addTo(leafletMap);
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => leafletMap.invalidateSize());
      window.addEventListener('resize', () => leafletMap.invalidateSize());
    } catch (err) {
      console.error('acto-2-map mount failed:', err);
    }
  }

  // ── sub_acto_2_5 — Correlación ICV-GEN-F ↔ brecha (scatter) ───────────────
  async function mountScatter() {
    const container = document.getElementById('acto-2-scatter');
    if (!container) return;
    try {
      const payload = await fetch(BRECHAS_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = payload.sub_acto_2_5;
      const data = sub.data;
      const POINT_COLOR = getCssVar('--color-accent-teal');
      const NULL_GAP_COLOR = CSS.scaleNull;

      container.innerHTML = '';
      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;height:360px;';
      container.appendChild(chartDiv);
      clearPlaceholder(container);

      const seriesData = data.points.map(p => ({
        name: p.municipality,
        value: [p.icv_average, p.gap_average],
        itemStyle: { color: p.gap_average != null ? POINT_COLOR : NULL_GAP_COLOR, opacity: p.gap_average != null ? 0.75 : 0.5 },
        _meta: p,
      }));

      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: '10%', right: '4%', top: '5%', bottom: '14%', containLabel: true },
        tooltip: {
          trigger: 'item', confine: true,
          formatter: params => {
            if (!params.data || !params.data._meta) return '';
            const p = params.data._meta;
            const gap = p.gap_average != null ? `${p.gap_average.toFixed(2)}× (F/M)` : 'no calculable (sin víctimas masculinas)';
            return `<strong>${p.municipality}</strong> — ${p.department}<br>Código DANE: ${p.cod_municipio}<br>ICV-GEN-F promedio: ${p.icv_average.toFixed(2)}<br>Brecha promedio: ${gap}`;
          },
        },
        xAxis: {
          type: 'value', name: (data.axis_labels_es.x_label || '').replace(/^PROVISIONAL: /, ''),
          nameLocation: 'middle', nameGap: 35, nameTextStyle: { fontSize: 12, color: CSS.muted },
          splitLine: { lineStyle: { color: CSS.hairline } },
        },
        yAxis: {
          type: 'value', name: (data.axis_labels_es.y_label || '').replace(/^PROVISIONAL: /, ''),
          nameLocation: 'middle', nameGap: 55, nameTextStyle: { fontSize: 12, color: CSS.muted },
          splitLine: { lineStyle: { color: CSS.hairline } },
        },
        series: [{
          type: 'scatter', animation: false, symbolSize: 7, data: seriesData,
          markLine: {
            silent: true, symbol: ['none', 'none'],
            lineStyle: { type: 'dashed', color: CSS.muted, width: 1.5 }, label: { show: false },
            data: [{ yAxis: data.reference_lines.y_median }, { xAxis: data.reference_lines.x_median }],
          },
        }],
      });
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());

      // Anchor copy for this sub-act into the dedicated text mount (only case
      // in Acto 2 where index.html left an explicit empty text slot for it).
      const textMount = document.querySelector('[data-mount="acto-2-scatter-text"]');
      renderAnchor(textMount, sub.anchor_text_es);
    } catch (err) {
      console.error('acto-2-scatter mount failed:', err);
    }
  }

  // ── sub_acto_2_6 — El giro analítico (acto-2-lines: dual gap/rates panels) ─
  function buildGapOption(series, cfg) {
    const years = series.map(d => String(d.year));
    const gaps = series.map(d => +(d.gap.toFixed(2)));
    const lbl = cfg?.legend_labels_es?.gap || 'Razón F/M';
    const yLbl = cfg?.axis_labels_es?.y_gap || 'Razón F/M';
    const xLbl = cfg?.axis_labels_es?.x || 'Año';
    return {
      backgroundColor: 'transparent',
      grid: { left: 52, right: 14, top: 38, bottom: 44 },
      legend: { data: [{ name: lbl, icon: 'circle' }], top: 5, textStyle: { fontSize: 10 } },
      xAxis: { type: 'category', data: years, axisLabel: { fontSize: 10 }, name: xLbl, nameLocation: 'middle', nameGap: 28, nameTextStyle: { fontSize: 10, color: CSS.muted } },
      yAxis: { type: 'value', name: yLbl, nameLocation: 'middle', nameGap: 36, nameTextStyle: { fontSize: 10, color: CSS.muted }, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: CSS.hairline } }, min: v => Math.floor(v.min * 0.85) },
      tooltip: { trigger: 'axis', formatter: p => `<strong>${p[0].name}</strong><br>${lbl}: ${p[0].value.toFixed(2)}×` },
      series: [{
        name: lbl, type: 'line', data: gaps, symbol: 'circle', symbolSize: 6,
        lineStyle: { color: COLOR_GAP, width: 2 }, itemStyle: { color: COLOR_GAP },
        label: { show: true, position: 'top', fontSize: 9, color: COLOR_GAP, formatter: p => p.value.toFixed(2) },
      }],
    };
  }

  function buildRatesOption(series, cfg) {
    const years = series.map(d => String(d.year));
    const ratesF = series.map(d => +(d.rate_f.toFixed(1)));
    const ratesM = series.map(d => +(d.rate_m.toFixed(1)));
    const lblF = cfg?.legend_labels_es?.rate_f || 'Tasa femenina';
    const lblM = cfg?.legend_labels_es?.rate_m || 'Tasa masculina';
    const yLbl = cfg?.axis_labels_es?.y_rate || 'Tasa por 100.000 hab.';
    const xLbl = cfg?.axis_labels_es?.x || 'Año';
    return {
      backgroundColor: 'transparent',
      grid: { left: 60, right: 14, top: 38, bottom: 44 },
      legend: { data: [{ name: lblF, icon: 'circle' }, { name: lblM, icon: 'circle' }], top: 5, textStyle: { fontSize: 10 } },
      xAxis: { type: 'category', data: years, axisLabel: { fontSize: 10 }, name: xLbl, nameLocation: 'middle', nameGap: 28, nameTextStyle: { fontSize: 10, color: CSS.muted } },
      yAxis: { type: 'value', name: yLbl, nameLocation: 'middle', nameGap: 44, nameTextStyle: { fontSize: 10, color: CSS.muted }, axisLabel: { fontSize: 10 }, splitLine: { lineStyle: { color: CSS.hairline } }, min: 0 },
      tooltip: { trigger: 'axis', formatter: params => `<strong>${params[0].name}</strong><br>` + params.map(p => `${p.seriesName}: ${(+p.value).toFixed(1)}`).join('<br>') },
      series: [
        { name: lblF, type: 'line', data: ratesF, symbol: 'circle', symbolSize: 4, lineStyle: { color: COLOR_F, width: 2 }, itemStyle: { color: COLOR_F }, areaStyle: { color: COLOR_F, opacity: 0.12 } },
        { name: lblM, type: 'line', data: ratesM, symbol: 'circle', symbolSize: 4, lineStyle: { color: COLOR_M, width: 2, opacity: 0.5 }, itemStyle: { color: COLOR_M, opacity: 0.5 }, areaStyle: { color: COLOR_M, opacity: 0.15 } },
      ],
    };
  }

  function buildGiroPanel(titleText, gapDivHeight, ratesDivHeight) {
    const col = document.createElement('div');
    const h4 = document.createElement('h4');
    h4.textContent = titleText;
    const gapDiv = document.createElement('div');
    gapDiv.style.cssText = `width:100%;height:${gapDivHeight}px;`;
    const ratesDiv = document.createElement('div');
    ratesDiv.style.cssText = `width:100%;height:${ratesDivHeight}px;`;
    col.appendChild(h4);
    col.appendChild(gapDiv);
    col.appendChild(ratesDiv);
    return { col, gapDiv, ratesDiv };
  }

  async function mountGiroAnalitico() {
    const container = document.getElementById('acto-2-lines');
    if (!container) return;
    try {
      const [payload, fullCfg] = await Promise.all([
        fetch(BRECHAS_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(CFG_URL).then(r => r.json()).catch(() => ({})),
      ]);
      const sub = payload.sub_acto_2_6;
      const data = sub.data;
      const bd = data.beat4_diagnostic;
      const dispCfg = fullCfg?.acto_2_visualization?.sub_acto_2_6 ?? {};
      const panelLabels = dispCfg.panel_labels_es ?? {};

      const focalKey = bd.focal_gap_visual;
      const focalData = bd[focalKey];
      const artifactKey = bd.focal_artifact;
      const artifactData = bd[artifactKey];

      container.innerHTML = '';
      const row = document.createElement('div');
      row.className = 'two-read';

      const panel1 = buildGiroPanel(panelLabels.focal_gap_visual || `${focalKey} — brecha y tasas`, 180, 220);
      const panel2 = buildGiroPanel(panelLabels.focal_artifact || `${artifactKey} — brecha y tasas (artefacto)`, 180, 220);
      row.appendChild(panel1.col);
      row.appendChild(panel2.col);
      container.appendChild(row);

      if (bd.narrative_conclusion) {
        const pq = document.createElement('p');
        pq.className = 'prose';
        pq.textContent = bd.narrative_conclusion;
        container.appendChild(pq);
      }
      clearPlaceholder(container);

      const chartGap1 = echarts.init(panel1.gapDiv);
      const chartRates1 = echarts.init(panel1.ratesDiv);
      chartGap1.setOption(buildGapOption(focalData.series, dispCfg));
      chartRates1.setOption(buildRatesOption(focalData.series, dispCfg));

      const chartGap2 = echarts.init(panel2.gapDiv);
      const chartRates2 = echarts.init(panel2.ratesDiv);
      chartGap2.setOption(buildGapOption(artifactData.series, dispCfg));
      chartRates2.setOption(buildRatesOption(artifactData.series, dispCfg));

      const allGiroCharts = [chartGap1, chartRates1, chartGap2, chartRates2];
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => allGiroCharts.forEach(c => c.resize()));
      }
      window.addEventListener('resize', () => allGiroCharts.forEach(c => c.resize()));
    } catch (err) {
      console.error('acto-2-lines mount failed:', err);
    }
  }

  mountButterfly();
  mountTop10Gap();
  mountDeptMap();
  mountScatter();
  mountGiroAnalitico();
  mountStatRow(document.getElementById('acto-2-stat-cards'), './data/acto_2_brechas.json', 'sub_acto_2_1');
})();
