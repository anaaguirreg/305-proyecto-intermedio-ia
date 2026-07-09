// ── Acto 1 — El Territorio ──────────────────────────────────────────────────
// Ported from test_render_acto_1_2.html (map), _1_3.html (top10), _1_4.html
// (evolución). Diagnóstico blocks, buildDiagnostico(), and the supplementary
// HTML table in _1_3 (no mount exists for it in index.html) are excluded.

(function () {
  const PANORAMA_URL = './data/acto_1_panorama.json';

  const CSS = {
    canvas:      getCssVar('--color-canvas'),
    ink:         getCssVar('--color-ink'),
    body:        getCssVar('--color-body'),
    muted:       getCssVar('--color-muted'),
    hairline:    getCssVar('--color-hairline'),
    primaryMid:  getCssVar('--color-primary-mid'),
    scale1:      getCssVar('--scale-1'),
    scale2:      getCssVar('--scale-2'),
    scale3:      getCssVar('--scale-3'),
    scale4:      getCssVar('--scale-4'),
    scale5:      getCssVar('--scale-5'),
    scaleNull:   getCssVar('--scale-null'),
  };

  // ── sub_acto_1_2 — choropleth map (ICV continuo / tipología cluster) ──────
  const PALETTE = [CSS.scale1, CSS.scale2, CSS.scale3, CSS.scale4, CSS.scale5];
  const N_BINS  = 5;

  function computeBreaks(sorted) {
    const breaks = [];
    for (let i = 1; i < N_BINS; i++) breaks.push(sorted[Math.floor((i / N_BINS) * sorted.length)]);
    return breaks;
  }

  function getColor(icv, breaks) {
    for (let i = 0; i < breaks.length; i++) if (icv <= breaks[i]) return PALETTE[i];
    return PALETTE[N_BINS - 1];
  }

  function makeStyle(rec, breaks) {
    if (!rec) return { fillColor: CSS.scaleNull, fillOpacity: 0.45, color: CSS.canvas, weight: 0.5 };
    const style = {
      fillColor: getColor(rec.icv_average, breaks), fillOpacity: 0.82,
      color: CSS.ink, weight: 0.8, opacity: 0.35, dashArray: null,
    };
    if (rec.excluded_from_model) { style.color = CSS.body; style.weight = 2; style.dashArray = '4,4'; }
    return style;
  }

  function makeClusterStyle(rec, clusterStyle) {
    const entry = clusterStyle.get(rec ? rec.cluster_id : null);
    const style = {
      fillColor: entry ? entry.color : CSS.scaleNull, fillOpacity: 0.82,
      color: CSS.canvas, weight: 0.5, dashArray: null,
    };
    if (rec && rec.excluded_from_model) { style.color = CSS.body; style.weight = 2; style.dashArray = '4,4'; }
    return style;
  }

  function setLegendContent(div, mode, breaks, clusterStyle) {
    if (mode === 'icv') {
      const lo = [0, ...breaks];
      const hi = [...breaks, 52.18];
      div.innerHTML = '<strong>ICV-GEN-F</strong>';
      for (let i = 0; i < N_BINS; i++) {
        div.innerHTML += `<br><span class="swatch" style="background:${PALETTE[i]}"></span>${lo[i].toFixed(2)} – ${hi[i].toFixed(2)}`;
      }
      div.innerHTML += `<br><span class="swatch" style="background:${CSS.scaleNull}"></span>Sin datos`
        + `<br><span class="swatch-excluded"></span>Excluido del modelo`
        + `<br><span class="swatch-circle"></span>Sin límite administrativo separado`;
    } else {
      const alta = clusterStyle.get(1), modBaja = clusterStyle.get(0), excl = clusterStyle.get(null);
      div.innerHTML = '<strong>Tipología K-Means</strong>'
        + `<br><span class="swatch" style="background:${alta.color}"></span>${alta.label}`
        + `<br><span class="swatch" style="background:${modBaja.color}"></span>${modBaja.label}`
        + `<br><span class="swatch" style="background:${excl.color}"></span>${excl.label}`
        + `<br><span class="swatch-excluded"></span>Excluido del modelo`
        + `<br><span class="swatch-circle"></span>Sin límite administrativo separado`;
    }
  }

  function makePopup(geoProp, rec, clusterStyle) {
    const nombre = rec ? rec.municipality : geoProp.municipio;
    const depto  = rec ? rec.department : geoProp.departamento;
    const icv    = rec ? rec.icv_average.toFixed(2) : 'Sin datos';
    let html = `<strong>${nombre}</strong><br>${depto}<br>Código: ${geoProp.cod_municipio}<br>ICV-GEN-F: ${icv}`;
    if (rec && rec.excluded_from_model) html += `<br><em>Excluido del modelo K-Means</em>`;
    if (clusterStyle && rec) {
      const entry = clusterStyle.get(rec.cluster_id);
      html += `<br>Tipología: ${entry ? entry.label : '—'}`;
    }
    return html;
  }

  function detectTwins(features) {
    const keyToFeats = new Map();
    for (const feat of features) {
      const key = JSON.stringify(feat.geometry.coordinates);
      if (!keyToFeats.has(key)) keyToFeats.set(key, []);
      keyToFeats.get(key).push(feat);
    }
    const TWIN_CODES = new Set();
    for (const [, feats] of keyToFeats) {
      if (feats.length < 2) continue;
      const sorted = feats.slice().sort((a, b) => a.properties.cod_municipio.localeCompare(b.properties.cod_municipio));
      for (const f of sorted.slice(1)) TWIN_CODES.add(f.properties.cod_municipio);
    }
    return TWIN_CODES;
  }

  async function mountMap() {
    const container = document.getElementById('acto-1-map');
    if (!container) return;
    try {
      const [geoData, panorama, cabeceraData, cfg] = await Promise.all([
        fetch('./config/pacifico_municipios.geojson').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch(PANORAMA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch('./config/municipios_pacifico.json').then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }),
        fetch('./config/master_exporter_config.json').then(r => r.ok ? r.json() : null).catch(() => null),
      ]);

      const sub = panorama.sub_acto_1_2;
      const dataMap = new Map(sub.data.features.map(f => [f.cod_municipio, f]));
      const sorted = sub.data.features.map(f => f.icv_average).sort((a, b) => a - b);
      const breaks = computeBreaks(sorted);
      const cabecera = cabeceraData.municipios;

      let CLUSTER_STYLE = null;
      const cl = cfg && cfg.cluster_legend;
      if (cl && cl.alta_severidad && cl.moderada_baja && cl.excluded) {
        CLUSTER_STYLE = new Map([
          [1,    { color: cl.alta_severidad.color, label: cl.alta_severidad.label }],
          [0,    { color: cl.moderada_baja.color,  label: cl.moderada_baja.label  }],
          [null, { color: cl.excluded.color,       label: cl.excluded.label       }],
        ]);
      }

      const TWIN_CODES = detectTwins(geoData.features);

      // Build DOM only once data is ready
      container.innerHTML = '';
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(anchorP);

      const toggleBar = document.createElement('div');
      toggleBar.style.cssText = 'max-width:100%;margin-bottom:8px;display:flex;gap:0;';
      const btnIcv = document.createElement('button');
      btnIcv.className = 'toggle-btn active';
      btnIcv.textContent = 'ICV continuo';
      const btnCluster = document.createElement('button');
      btnCluster.className = 'toggle-btn';
      btnCluster.textContent = 'Tipología (clusters)';
      if (!CLUSTER_STYLE) btnCluster.disabled = true;
      toggleBar.appendChild(btnIcv);
      toggleBar.appendChild(btnCluster);

      const mapDiv = document.createElement('div');
      mapDiv.style.cssText = 'width:100%;height:520px;border:1px solid var(--color-hairline);';

      container.appendChild(toggleBar);
      container.appendChild(mapDiv);
      clearPlaceholder(container);

      const leafletMap = L.map(mapDiv).setView([3.5, -76.5], 7);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(leafletMap);

      const polygonLayers = [];
      const filteredGeo = { type: 'FeatureCollection', features: geoData.features.filter(f => !TWIN_CODES.has(f.properties.cod_municipio)) };
      L.geoJSON(filteredGeo, {
        style: feature => makeStyle(dataMap.get(feature.properties.cod_municipio), breaks),
        onEachFeature: (feature, layer) => {
          const rec = dataMap.get(feature.properties.cod_municipio);
          polygonLayers.push({ layer, rec });
          layer.bindPopup(makePopup(feature.properties, rec, CLUSTER_STYLE));
        },
      }).addTo(leafletMap);

      const twinMarkers = [];
      for (const feat of geoData.features.filter(f => TWIN_CODES.has(f.properties.cod_municipio))) {
        const cod = feat.properties.cod_municipio;
        const rec = dataMap.get(cod);
        const cab = cabecera[cod];
        if (!cab) continue;
        const fillColor = rec ? getColor(rec.icv_average, breaks) : CSS.scaleNull;
        const markerOptions = { radius: 6, fillColor, fillOpacity: 0.95, color: CSS.ink, weight: 1.5 };
        if (rec && rec.excluded_from_model) markerOptions.dashArray = '4,4';
        const marker = L.circleMarker([cab.lat, cab.lon], markerOptions);
        let popupHtml = makePopup(feat.properties, rec, CLUSTER_STYLE);
        popupHtml += `<br><em>Sin límite administrativo separado en geoBoundaries — se muestra en su cabecera municipal.</em>`;
        marker.bindPopup(popupHtml);
        marker.addTo(leafletMap);
        twinMarkers.push({ marker, rec });
      }

      let legendDiv;
      const legendCtrl = L.control({ position: 'bottomright' });
      legendCtrl.onAdd = () => {
        legendDiv = L.DomUtil.create('div', 'icv-legend');
        setLegendContent(legendDiv, 'icv', breaks, CLUSTER_STYLE);
        return legendDiv;
      };
      legendCtrl.addTo(leafletMap);

      let currentMode = 'icv';
      function applyMode(mode) {
        if (mode === currentMode) return;
        currentMode = mode;
        for (const { layer, rec } of polygonLayers) {
          layer.setStyle(mode === 'icv' ? makeStyle(rec, breaks) : makeClusterStyle(rec, CLUSTER_STYLE));
        }
        for (const { marker, rec } of twinMarkers) {
          const fillColor = mode === 'icv'
            ? (rec ? getColor(rec.icv_average, breaks) : CSS.scaleNull)
            : (CLUSTER_STYLE.get(rec ? rec.cluster_id : null)?.color ?? CSS.scaleNull);
          marker.setStyle({ fillColor });
        }
        setLegendContent(legendDiv, mode, breaks, CLUSTER_STYLE);
        btnIcv.classList.toggle('active', mode === 'icv');
        btnCluster.classList.toggle('active', mode === 'cluster');
      }
      btnIcv.addEventListener('click', () => applyMode('icv'));
      if (CLUSTER_STYLE) btnCluster.addEventListener('click', () => applyMode('cluster'));

      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => leafletMap.invalidateSize());
      window.addEventListener('resize', () => leafletMap.invalidateSize());
    } catch (err) {
      console.error('acto-1-map mount failed:', err);
    }
  }

  // ── sub_acto_1_3 — Top 10 municipios (bar ranking) ────────────────────────
  const BAR_COLOR = '#3d8a7a';

  function tooltipFormatterTop10(items) {
    return params => {
      const it = items[params[0].dataIndex];
      const clusterLabel = it.cluster_name ? it.cluster_name.replace(/^\p{Emoji}\s*/u, '') : '—';
      return [
        `<strong>${it.municipality}</strong> — ${it.department}`,
        `Código DANE ${it.cod_municipio} · Rango ${it.rank}`,
        `ICV-GEN-F promedio: ${it.icv_average.toFixed(2)}`,
        `Tipología: ${clusterLabel}`,
      ].join('<br>');
    };
  }

  function buildSeriesDataTop10(values, highlightFlags, highlightColor) {
    return values.map((v, i) => {
      if (v == null) return { value: 0, itemStyle: { color: CSS.scaleNull }, label: { show: true, formatter: () => 'sin dato', color: CSS.muted } };
      if (highlightFlags && highlightFlags[i]) return { value: v, itemStyle: { color: highlightColor } };
      return v;
    });
  }

  function buildRankTable(items, highlightMatch) {
    const wrap = document.createElement('div');
    wrap.className = 'tabla-wrap';
    const table = document.createElement('table');
    table.innerHTML = '<thead><tr><th>Rango</th><th>Municipio</th><th>Departamento</th><th>ICV-GEN-F promedio</th><th>Tipología</th></tr></thead>';
    const tbody = document.createElement('tbody');
    items.forEach((it, i) => {
      const tr = document.createElement('tr');
      if (highlightMatch(it)) tr.className = 'highlighted';
      else if (i % 2 === 1) tr.className = 'alt';
      const clusterLabel = it.cluster_name ? it.cluster_name.replace(/^\p{Emoji}\s*/u, '') : '—';
      tr.innerHTML = `<td>${it.rank}</td><td>${it.municipality}</td><td>${it.department}</td><td>${it.icv_average.toFixed(2)}</td><td>${clusterLabel}</td>`;
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    return wrap;
  }

  async function mountTop10() {
    const container = document.getElementById('acto-1-top10');
    if (!container) return;
    try {
      const panorama = await fetch(PANORAMA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const sub = panorama.sub_acto_1_3;
      const { echarts_series, items } = sub.data;
      const highlightColor = CSS.primaryMid;

      container.innerHTML = '';
      const titleEl = document.createElement('h4');
      titleEl.textContent = sub.title_es;
      const anchorP = document.createElement('p');
      anchorP.className = 'prose';
      anchorP.textContent = sub.anchor_text_es;
      container.appendChild(titleEl);
      container.appendChild(anchorP);

      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;height:440px;';
      container.appendChild(chartDiv);
      container.appendChild(buildRankTable(items, it => it.highlight));
      clearPlaceholder(container);

      const seriesData = buildSeriesDataTop10(echarts_series.values, echarts_series.highlight_flags, highlightColor);
      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 230, right: 95, top: 16, bottom: 50 },
        xAxis: {
          type: 'value', name: 'ICV-GEN-F promedio', nameLocation: 'middle', nameGap: 32,
          axisLabel: { formatter: v => v.toFixed(1) },
          splitLine: { lineStyle: { color: CSS.hairline } },
        },
        yAxis: {
          type: 'category', data: echarts_series.categories, inverse: true,
          axisLabel: { width: 215, overflow: 'truncate', fontSize: 12 },
        },
        series: [{
          type: 'bar', data: seriesData, color: BAR_COLOR,
          label: { show: true, position: 'right', formatter: p => (p.value != null ? p.value.toFixed(2) : '—'), fontSize: 11, color: CSS.body },
        }],
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: tooltipFormatterTop10(items) },
      });
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-1-top10 mount failed:', err);
    }
  }

  // ── sub_acto_1_4 — Evolución temporal ICV-GEN-F regional ──────────────────
  async function mountEvolucion() {
    const container = document.getElementById('acto-1-evolucion');
    if (!container) return;
    try {
      const panorama = await fetch(PANORAMA_URL).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
      const data = panorama.sub_acto_1_4.data;
      const serie = data.series[0];

      container.innerHTML = '';
      const chartDiv = document.createElement('div');
      chartDiv.style.cssText = 'width:100%;height:360px;';
      container.appendChild(chartDiv);
      clearPlaceholder(container);

      const chart = echarts.init(chartDiv);
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: '8%', right: '4%', top: '10%', bottom: '12%', containLabel: true },
        tooltip: { trigger: 'axis', formatter: params => `<strong>${params[0].axisValue}</strong><br>${serie.name}: ${params[0].value.toFixed(2)}` },
        xAxis: { type: 'category', data: data.x_axis, axisLabel: { formatter: v => String(v) }, splitLine: { show: false } },
        yAxis: { type: 'value', name: serie.name, nameLocation: 'middle', nameGap: 50, nameTextStyle: { fontSize: 11, color: CSS.muted }, splitLine: { lineStyle: { color: CSS.hairline } } },
        series: [{ type: 'line', name: serie.name, data: serie.data, smooth: false, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2.5 } }],
      });
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => chart.resize());
      window.addEventListener('resize', () => chart.resize());
    } catch (err) {
      console.error('acto-1-evolucion mount failed:', err);
    }
  }

  mountMap();
  mountTop10();
  mountEvolucion();
  mountStatRow(document.getElementById('acto-1-stat-cards'), './data/acto_1_panorama.json', 'sub_acto_1_1');
})();
