// ── Acto 3 — Dos Violencias ──────────────────────────────────────────────────
// Ported from test_render_acto_3_{2,3,4,5}.html. Diagnóstico blocks and
// buildDiagnostico() are excluded. acto-3-taxonomia-tabs (sub_acto_3_1's
// tabbed chart) has no test_render source — stays a .viz-placeholder.

(function () {
  const TIPOLOGIA_URL = './data/acto_3_tipologia.json';

  const CSS = {
    canvas:    getCssVar('--color-canvas'),
    ink:       getCssVar('--color-ink'),
    body:      getCssVar('--color-body'),
    muted:     getCssVar('--color-muted'),
    hairline:  getCssVar('--color-hairline'),
    scaleNull: getCssVar('--scale-null'),
  };

  const CLUSTER_LABELS = { 0: 'Moderada / Baja', 1: 'Alta severidad', null: 'Sin modelo' };
  const QUADRANT_ORDER = ['coexistencia_alta', 'predomina_vif', 'predomina_sexual', 'bajo_perfil'];

  // ── sub_acto_3_2 — El contraste de tasas (VIF vs Sexual scatter) ──────────
  async function mountScatterContraste() {
    const container = document.getElementById('acto-3-scatter');
    if (!container) return;
    try {
      const tipologia = await fetch(TIPOLOGIA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = tipologia.sub_acto_3_2;
      const data = sub.data;
      const style = data.scatter_style;
      const colors = data.quadrant_colors;
      const arcCodes = new Set(data.archetypes.map(a => a.cod_municipio));

      const xs = data.points.map(p => p.vif_f_total_rate);
      const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
      const std = Math.sqrt(xs.map(x => (x - mean) ** 2).reduce((a, b) => a + b, 0) / xs.length);

      const seriesData = data.points.map(p => {
        const isArc = arcCodes.has(p.cod_municipio);
        const item = {
          name: p.municipality,
          value: [p.vif_f_total_rate, p.sexual_f_total_rate],
          symbolSize: isArc ? style.point_radius_archetype : style.point_radius_default,
          itemStyle: {
            color: colors[p.quadrant],
            opacity: isArc ? style.opacity_archetype : style.opacity_default,
            borderColor: isArc ? style.border_color_archetype : 'transparent',
            borderWidth: isArc ? style.border_width_archetype : 0,
          },
          _meta: p,
        };
        if (isArc) {
          item.label = { show: true, formatter: params => params.data._meta.municipality, position: 'right', distance: 8, fontSize: 11, fontWeight: 600, color: CSS.ink };
        }
        return item;
      });

      container.innerHTML = '';
      const titleEl = document.createElement('h4');
      titleEl.textContent = sub.title_es;
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(titleEl);
      container.appendChild(anchorP);

      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;height:400px;';
      container.appendChild(chartDiv);

      const legendDiv = document.createElement('div');
      legendDiv.style.cssText = 'display:flex;flex-wrap:wrap;gap:16px;margin-top:12px;font-size:0.82rem;color:var(--color-muted);';
      for (const key of QUADRANT_ORDER) {
        const q = data.quadrants[key];
        const color = data.quadrant_colors[key];
        const entry = document.createElement('span');
        entry.title = q.tooltip;
        entry.innerHTML = `<span class="legend-swatch" style="background:${color}"></span>${q.label} (n = ${q.n})`;
        legendDiv.appendChild(entry);
      }
      container.appendChild(legendDiv);
      clearPlaceholder(container);

      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: '12%', right: '4%', top: '5%', bottom: '14%', containLabel: true },
        tooltip: {
          trigger: 'item', confine: true,
          formatter: params => {
            if (!params.data || !params.data._meta) return '';
            const p = params.data._meta;
            const quad = data.quadrants[p.quadrant];
            const clusterLabel = CLUSTER_LABELS[p.cluster_id] ?? 'Sin modelo';
            let html = `<strong>${p.municipality}</strong> — ${p.department}<br>Código DANE: ${p.cod_municipio}<br>` +
              `Cuadrante: <strong>${quad.label}</strong><br>` +
              `<span style="font-size:0.87em;color:${CSS.muted};font-style:italic">${quad.tooltip}</span><br>` +
              `Tasa VIF: ${p.vif_f_total_rate.toFixed(1)} por 100k<br>Tasa Sexual: ${p.sexual_f_total_rate.toFixed(1)} por 100k<br>Tipología: ${clusterLabel}`;
            if (p.is_archetype) html += `<br><em>Municipio arquetipo de este cuadrante.</em>`;
            return html;
          },
        },
        xAxis: { type: 'log', logBase: 10, name: data.axis_labels_es.x_label, nameLocation: 'middle', nameGap: 35, nameTextStyle: { fontSize: 12, color: CSS.muted }, min: 10, axisLabel: { formatter: v => v.toLocaleString('es') } },
        yAxis: { type: 'value', name: data.axis_labels_es.y_label, nameLocation: 'middle', nameGap: 55, nameTextStyle: { fontSize: 12, color: CSS.muted } },
        series: [{
          type: 'scatter', animation: false, data: seriesData,
          markLine: {
            silent: true, symbol: ['none', 'none'],
            lineStyle: { type: 'dashed', color: CSS.muted, width: 1.5 }, label: { show: false },
            data: [{ yAxis: data.reference_lines.y_median }, { xAxis: data.reference_lines.x_median }],
          },
        }],
      });
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-3-scatter mount failed:', err);
    }
  }

  // ── sub_acto_3_3 — Dumbbell NNA vs Adultas (VIF y Sexual) ─────────────────
  async function mountDumbbell() {
    const container = document.getElementById('acto-3-tasas-nna-adultas');
    if (!container) return;
    try {
      const payload = await fetch(TIPOLOGIA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = payload.sub_acto_3_3;
      const data = sub.data;
      const lines = data.lines;
      const COLOR_NNA = getCssVar('--color-accent-teal');
      const COLOR_ADULTAS = getCssVar('--color-primary');

      const lineLabels = lines.map(l => l.label);
      const nnaPoints = lines.map((l, yi) => { const ep = l.endpoints.find(e => e.group === 'nna') || l.endpoints[0]; return { value: [ep.rate, yi], _ep: ep, _label: l.label }; });
      const adultasPoints = lines.map((l, yi) => { const ep = l.endpoints.find(e => e.group === 'adultas') || l.endpoints[1]; return { value: [ep.rate, yi], _ep: ep, _label: l.label }; });
      const markLineData = lines.map((l, yi) => {
        const nna = l.endpoints.find(e => e.group === 'nna') || l.endpoints[0];
        const adultas = l.endpoints.find(e => e.group === 'adultas') || l.endpoints[1];
        return [{ coord: [nna.rate, yi] }, { coord: [adultas.rate, yi] }];
      });

      container.innerHTML = '';
      const titleEl = document.createElement('h4');
      titleEl.textContent = sub.title_es;
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(titleEl);
      container.appendChild(anchorP);

      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;min-height:420px;';
      container.appendChild(chartDiv);
      clearPlaceholder(container);

      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 185, right: 80, top: 50, bottom: 60 },
        legend: { data: [{ name: 'NNA (0–17)', icon: 'circle' }, { name: 'Adultas (18+)', icon: 'circle' }], top: 5, textStyle: { fontSize: 11 } },
        xAxis: { type: 'value', name: 'Tasa por 100.000 habitantes', nameLocation: 'middle', nameGap: 36, nameTextStyle: { fontSize: 11, color: CSS.muted }, axisLabel: { fontSize: 11 }, splitLine: { lineStyle: { color: CSS.hairline } }, min: 0 },
        yAxis: { type: 'category', data: lineLabels, axisLabel: { fontSize: 12, width: 170, overflow: 'break' } },
        tooltip: {
          trigger: 'item',
          formatter: params => {
            const d = params.data;
            if (!d || !d._ep) return '';
            return `<strong>${d._label}</strong><br>${d._ep.label_display}<br>Tasa: ${d._ep.rate.toFixed(2)} / 100.000<br>Casos: ${d._ep.cases.toLocaleString('es')}`;
          },
        },
        series: [
          {
            name: 'NNA (0–17)', type: 'scatter', symbolSize: 16, itemStyle: { color: COLOR_NNA }, data: nnaPoints,
            label: { show: true, position: 'top', formatter: p => p.data._ep.rate.toFixed(1), fontSize: 10, color: COLOR_NNA },
            markLine: { silent: true, symbol: ['none', 'none'], lineStyle: { color: CSS.scaleNull, width: 2.5, type: 'solid' }, label: { show: false }, data: markLineData },
          },
          {
            name: 'Adultas (18+)', type: 'scatter', symbolSize: 16, itemStyle: { color: COLOR_ADULTAS }, data: adultasPoints,
            label: { show: true, position: 'top', formatter: p => p.data._ep.rate.toFixed(1), fontSize: 10, color: COLOR_ADULTAS },
          },
        ],
      });
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-3-tasas-nna-adultas mount failed:', err);
    }
  }

  // ── sub_acto_3_4 — Taxonomía del delito sexual (bar + markArea menores) ───
  function buildMarkAreaData(items) {
    const bands = [];
    let runStart = null;
    for (let i = 0; i <= items.length; i++) {
      const isMinor = i < items.length && items[i].is_minor;
      if (isMinor && runStart === null) runStart = i;
      else if (!isMinor && runStart !== null) {
        bands.push([{ yAxis: items[runStart].label }, { yAxis: items[i - 1].label }]);
        runStart = null;
      }
    }
    return bands;
  }

  async function mountTaxonomiaBar() {
    const container = document.querySelector('[data-subacto="sub_acto_3_4"]');
    if (!container) return;
    try {
      const payload = await fetch(TIPOLOGIA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = payload.sub_acto_3_4;
      const items = sub.data.global;
      const COLOR_MINOR = getCssVar('--color-primary-mid');
      const COLOR_BASE  = getCssVar('--color-accent-teal');
      const MARK_FILL   = 'rgba(123, 31, 75, 0.07)';

      const labels = items.map(d => d.label);
      const pcts = items.map(d => d.pct);
      const barColors = items.map(d => d.is_minor ? COLOR_MINOR : COLOR_BASE);
      const seriesData = pcts.map((v, i) => ({ value: v, itemStyle: { color: barColors[i] } }));
      const pctMinor = items.filter(d => d.is_minor).reduce((s, d) => s + d.pct, 0);
      const nMinor = items.filter(d => d.is_minor).reduce((s, d) => s + d.count, 0);
      const markAreaData = buildMarkAreaData(items);

      container.innerHTML = '';
      const titleEl = document.createElement('h4');
      titleEl.textContent = sub.title_es;
      container.appendChild(titleEl);

      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;height:400px;';
      const minorStat = document.createElement('p');
      minorStat.className = 'prose prose--muted-small';
      minorStat.textContent = `${pctMinor.toFixed(2)}% (${nMinor.toLocaleString('es')} casos) son delitos explícitamente contra menores de edad`;
      container.appendChild(chartDiv);
      container.appendChild(minorStat);
      clearPlaceholder(container);

      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 240, right: 70, top: 20, bottom: 44 },
        xAxis: { type: 'value', name: '% del total', nameLocation: 'middle', nameGap: 28, nameTextStyle: { fontSize: 11, color: CSS.muted }, axisLabel: { formatter: v => v + '%', fontSize: 10 }, splitLine: { lineStyle: { color: CSS.hairline } }, max: Math.ceil(Math.max(...pcts) / 5) * 5 + 2 },
        yAxis: { type: 'category', data: labels, inverse: true, axisLabel: { width: 228, overflow: 'truncate', fontSize: 11 } },
        tooltip: {
          trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: params => {
            const item = items[params[0].dataIndex];
            return `<strong>${item.label}</strong><br>${item.pct.toFixed(2)}% — ${item.count.toLocaleString('es')} casos` + (item.is_minor ? '<br><em>Delito contra menores</em>' : '');
          },
        },
        series: [{
          type: 'bar', data: seriesData,
          label: { show: true, position: 'right', formatter: p => p.value.toFixed(1) + '%', fontSize: 10, color: CSS.body },
          markArea: { silent: true, itemStyle: { color: MARK_FILL, borderColor: 'rgba(123,31,75,0.2)', borderWidth: 1 }, label: { show: false }, data: markAreaData },
        }],
      });
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-3-barras-linea (sub_acto_3_4) mount failed:', err);
    }
  }

  // ── sub_acto_3_5 — Evolución temporal violencia sexual NNA por depto ─────
  const DEPT_TOKEN = { 'CAUCA': '--dept-cauca', 'CHOCO': '--dept-choco', 'NARIÑO': '--dept-narino', 'VALLE DEL CAUCA': '--dept-valle' };

  async function mountEvolucionDepto() {
    const container = document.querySelector('[data-subacto="sub_acto_3_5"]');
    if (!container) return;
    try {
      const tipologia = await fetch(TIPOLOGIA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = tipologia.sub_acto_3_5;
      const data = sub.data;

      const colorMap = new Map();
      for (const s of data.series) {
        const varName = DEPT_TOKEN[s.department];
        colorMap.set(s.department, varName ? getCssVar(varName) : null);
      }

      const echartsSeriesData = data.series.map(s => {
        const color = colorMap.get(s.department) ?? undefined;
        return { type: 'line', name: s.department, data: s.data, smooth: false, symbol: 'circle', symbolSize: 5, lineStyle: { width: 2.5, color }, itemStyle: { color } };
      });

      container.innerHTML = '';
      const titleEl = document.createElement('h4');
      titleEl.textContent = sub.title_es;
      const subtitleP = document.createElement('p');
      subtitleP.className = 'prose';
      subtitleP.textContent = sub.anchor_text_es;
      container.appendChild(titleEl);
      container.appendChild(subtitleP);

      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;height:400px;';
      container.appendChild(chartDiv);
      clearPlaceholder(container);

      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: '8%', right: '4%', top: '14%', bottom: '12%', containLabel: true },
        legend: { data: data.series.map(s => s.department), top: '2%', textStyle: { fontSize: 11 } },
        tooltip: {
          trigger: 'axis',
          formatter: params => {
            let html = `<strong>${params[0].axisValue}</strong>`;
            for (const p of params) {
              const val = p.value != null ? p.value.toFixed(1) : 'sin dato';
              html += `<br><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};margin-right:4px"></span>${p.seriesName}: ${val}`;
            }
            return html;
          },
        },
        xAxis: { type: 'category', data: data.x_axis, axisLabel: { formatter: v => String(v) }, splitLine: { show: false } },
        yAxis: { type: 'value', name: data.metric_label, nameLocation: 'middle', nameGap: 55, nameTextStyle: { fontSize: 11, color: CSS.muted }, splitLine: { lineStyle: { color: CSS.hairline } } },
        series: echartsSeriesData,
      });
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-3-barras-linea (sub_acto_3_5) mount failed:', err);
    }
  }

  mountScatterContraste();
  mountDumbbell();
  mountTaxonomiaBar();
  mountEvolucionDepto();
  mountStatRow(document.getElementById('acto-3-stat-cards'), './data/acto_3_tipologia.json', 'sub_acto_3_1');
})();
