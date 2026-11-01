/* Dashboard de minería informal: los filtros recalculan indicadores, mapa, gráficos y tabla desde web/data/datos.json */
(async function () {
  const [D, C] = await Promise.all(["data/datos.json", "data/capas.json"].map((u) => fetch(u).then((r) => r.json())));
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => Math.round(n).toLocaleString("en-US");
  const pct = (a, b) => (b ? (a / b) * 100 : 0);
  const pctT = (x) => (x < 10 && x > 0 ? x.toFixed(1) : Math.round(x)) + " %";
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const A = { sat: css("--sat"), prov: css("--prov"), oro: css("--oro"), rei: css("--reinfo"), sus: css("--sus"), anp: css("--anp") };
  const ANIOS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
  const anioDe = D.periodos.map((p) => (p[0] === "Q" ? 2000 + +p.slice(2) : +p));
  const provisional = D.periodos.map((p) => p[0] === "Q");
  const N = D.det.lon.length;
  const BIT = { anp: 1, amort: 2, corredor: 4, reserva: 8, tambopata: 16 };
  const iMDD = D.deps.indexOf("Madre de Dios");

  /* Tablas fijas por departamento */
  const orden = D.deps.slice().sort((a, b) => a.localeCompare(b, "es"));
  const estado = { dep: "", desde: 2018, hasta: 2026, zona: "todas", km: 5 };
  const params = new URLSearchParams(location.search);

  orden.forEach((d) => $("f-dep").add(new Option(d, d)));
  $("f-dep").insertBefore(new Option("Todo el Perú", ""), $("f-dep").firstChild);
  $("f-dep").value = "";
  ANIOS.forEach((a) => {
    $("f-desde").add(new Option(a, a));
    $("f-hasta").add(new Option(a, a));
  });
  $("f-desde").value = 2018;
  $("f-hasta").value = 2026;

  function pasa(i, usarZona = true, usarAnio = true) {
    const dep = estado.dep ? D.deps.indexOf(estado.dep) : -1;
    if (dep >= 0 && D.det.dep[i] !== dep) return false;
    const a = anioDe[D.det.per[i]];
    if (usarAnio && (a < estado.desde || a > estado.hasta)) return false;
    if (!usarZona) return true;
    const b = D.det.bits[i];
    switch (estado.zona) {
      case "anp": return !!(b & BIT.anp);
      case "amort": return !!(b & BIT.amort);
      case "fuera": return D.det.dep[i] === iMDD && !(b & BIT.corredor);
      case "dentro": return D.det.dep[i] === iMDD && !!(b & BIT.corredor);
      case "lejos": return D.det.km[i] > estado.km;
      default: return true;
    }
  }

  /* ---------- Mapa ---------- */
  const fondos = {
    claro: { tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"], attr: "Mapa base: Esri" },
    sat: { tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], attr: "Imagen: Esri, Maxar, Earthstar Geographics" },
  };
  const mapa = new maplibregl.Map({
    container: "mapa",
    style: { version: 8, sources: {
      claro: { type: "raster", tiles: fondos.claro.tiles, tileSize: 256, attribution: fondos.claro.attr },
      sat: { type: "raster", tiles: fondos.sat.tiles, tileSize: 256, attribution: fondos.sat.attr },
    }, layers: [
      { id: "claro", type: "raster", source: "claro" },
      { id: "sat", type: "raster", source: "sat", layout: { visibility: "none" } },
    ] },
    bounds: [[-81.5, -18.6], [-68.4, 0.2]], fitBoundsOptions: { padding: 12 }, attributionControl: { compact: true }, preserveDrawingBuffer: true,
  });
  window.__mapa = mapa;
  mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  mapa.scrollZoom.disable();
  mapa.on("click", () => mapa.scrollZoom.enable());
  let mapaListo = false;

  function geoDet() {
    const f = [];
    for (let i = 0; i < N; i++) {
      if (!pasa(i)) continue;
      f.push({ type: "Feature", geometry: { type: "Point", coordinates: [D.det.lon[i], D.det.lat[i]] }, properties: { i, r: anioDe[D.det.per[i]] >= 2024 ? 1 : 0 } });
    }
    return { type: "FeatureCollection", features: f };
  }
  function geoRej() {
    const f = [];
    D.rej.x.forEach((x, k) => {
      const t = D.rej.v[k] + D.rej.s[k];
      f.push({ type: "Feature", geometry: { type: "Point", coordinates: [x, D.rej.y[k]] }, properties: { t, v: D.rej.v[k], s: D.rej.s[k] } });
    });
    return { type: "FeatureCollection", features: f };
  }
  mapa.on("load", () => {
    mapa.addSource("amort", { type: "geojson", data: C.amort });
    mapa.addSource("anp", { type: "geojson", data: C.anp });
    mapa.addSource("corredor", { type: "geojson", data: C.corredor });
    mapa.addSource("deps", { type: "geojson", data: C.deps });
    mapa.addSource("rej", { type: "geojson", data: geoRej() });
    mapa.addSource("det", { type: "geojson", data: geoDet() });
    mapa.addLayer({ id: "deps-l", type: "line", source: "deps", paint: { "line-color": "#6b675e", "line-width": 0.6, "line-opacity": 0.6 } });
    mapa.addLayer({ id: "anp-f", type: "fill", source: "anp", paint: { "fill-color": A.anp, "fill-opacity": 0.14 } });
    mapa.addLayer({ id: "anp-l", type: "line", source: "anp", paint: { "line-color": A.anp, "line-width": 1.1 } });
    mapa.addLayer({ id: "amort-l", type: "line", source: "amort", paint: { "line-color": A.anp, "line-width": 1, "line-dasharray": [2, 2] } });
    mapa.addLayer({ id: "cor-l", type: "line", source: "corredor", paint: { "line-color": A.oro, "line-width": 1.8, "line-dasharray": [3, 2] } });
    mapa.addLayer({ id: "rej-c", type: "circle", source: "rej", layout: { visibility: "none" }, paint: {
      "circle-color": A.rei, "circle-opacity": 0.5, "circle-stroke-color": "#fff", "circle-stroke-width": 0.5,
      "circle-radius": ["interpolate", ["linear"], ["sqrt", ["get", "t"]], 1, 2, 10, 7, 30, 18] } });
    mapa.addLayer({ id: "det-c", type: "circle", source: "det", paint: {
      "circle-color": ["case", ["==", ["get", "r"], 1], A.sat, "#6d6459"],
      "circle-opacity": 0.85,
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 1.3, 8, 2.4, 12, 7] } });
    mapaListo = true;
    mapa.on("mousemove", "det-c", (e) => {
      mapa.getCanvas().style.cursor = "pointer";
      const i = e.features[0].properties.i;
      const p = D.periodos[D.det.per[i]];
      const b = D.det.bits[i];
      const z = [b & BIT.anp ? "área natural" : "", b & BIT.amort ? "amortiguamiento" : "", D.det.dep[i] === iMDD ? (b & BIT.corredor ? "dentro del corredor" : "fuera del corredor") : ""].filter(Boolean).join(" · ");
      muestraTip(`<strong>${D.provs[D.det.prov[i]]}, ${D.deps[D.det.dep[i]]}</strong><br>Periodo: ${etiquetaPeriodo(p)}<br>${D.det.km[i]} km al REINFO más cercano${z ? "<br>" + z : ""}`, e.originalEvent);
    });
    mapa.on("mouseleave", "det-c", () => { mapa.getCanvas().style.cursor = ""; ocultaTip(); });
    mapa.on("mousemove", "rej-c", (e) => {
      if (mapa.getLayoutProperty("det-c", "visibility") !== "none" && mapa.queryRenderedFeatures(e.point, { layers: ["det-c"] }).length) return;
      const q = e.features[0].properties;
      muestraTip(`<strong>REINFO en esta celda</strong><br>${fmt(q.t)} inscripciones<br>${fmt(q.v)} vigentes · ${fmt(q.s)} suspendidas`, e.originalEvent);
    });
    mapa.on("mouseleave", "rej-c", ocultaTip);
    aplicaCapas();
    pinta();
  });
  const etiquetaPeriodo = (p) => (p[0] === "Q" ? `${p[1]}.° trimestre de 20${p.slice(2)} (provisional)` : p === "2018" ? "hasta 2018" : p);
  function aplicaCapas() {
    if (!mapaListo) return;
    const vis = (id, v) => mapa.setLayoutProperty(id, "visibility", v ? "visible" : "none");
    vis("det-c", $("c-det").checked);
    vis("rej-c", $("c-rej").checked);
    ["anp-f", "anp-l", "amort-l"].forEach((l) => vis(l, $("c-anp").checked));
    vis("cor-l", $("c-cor").checked);
    vis("claro", $("c-fondo").value === "claro");
    vis("sat", $("c-fondo").value === "sat");
  }
  function encuadra() {
    if (!mapaListo) return;
    let x0 = 999, x1 = -999, y0 = 999, y1 = -999, n = 0;
    if (estado.dep) {
      const nom = estado.dep.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
      C.deps.features.filter((f) => f.properties.NM_DEPA === nom).forEach((f) => {
        const pasos = (c) => (typeof c[0] === "number" ? [c] : c.flatMap(pasos));
        pasos(f.geometry.coordinates).forEach(([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); n++; });
      });
    }
    if (n) mapa.fitBounds([[x0, y0], [x1, y1]], { padding: 24, duration: 500 });
    else mapa.fitBounds([[-81.5, -18.6], [-68.4, 0.2]], { padding: 12, duration: 500 });
  }

  /* ---------- Ayudas de SVG ---------- */
  const NS = "http://www.w3.org/2000/svg";
  function svg(w, h, etiqueta) {
    const s = document.createElementNS(NS, "svg");
    s.setAttribute("viewBox", `0 0 ${w} ${h}`);
    s.setAttribute("role", "img");
    s.setAttribute("aria-label", etiqueta);
    return s;
  }
  function el(p, tag, at = {}, texto) {
    const e = document.createElementNS(NS, tag);
    Object.entries(at).forEach(([k, v]) => e.setAttribute(k, v));
    if (texto !== undefined) e.textContent = texto;
    p.appendChild(e);
    return e;
  }
  const barraRedonda = (x, y, w, h, r = 3) => {
    if (h <= 0) return "";
    const q = Math.min(r, h, w / 2);
    return `M${x},${y + h}V${y + q}Q${x},${y} ${x + q},${y}H${x + w - q}Q${x + w},${y} ${x + w},${y + q}V${y + h}Z`;
  };
  function escalaBonita(max) {
    if (max <= 4) return { tope: 4, paso: 1 };
    const e = Math.pow(10, Math.floor(Math.log10(max)));
    const paso = [1, 2, 2.5, 5, 10].map((m) => m * e / 2).find((p) => max / p <= 5) || e;
    return { tope: Math.ceil(max / paso) * paso, paso };
  }
  function tip(obj, html) {
    obj.classList.add("obj");
    obj.addEventListener("mousemove", (ev) => muestraTip(html, ev));
    obj.addEventListener("mouseleave", ocultaTip);
    obj.addEventListener("touchstart", (ev) => { muestraTip(html, ev.touches[0]); }, { passive: true });
  }
  function muestraTip(html, ev) {
    const t = $("tip");
    t.innerHTML = html;
    t.hidden = false;
    const r = t.getBoundingClientRect();
    t.style.left = Math.min(ev.clientX + 14, innerWidth - r.width - 8) + "px";
    t.style.top = Math.max(8, ev.clientY - r.height - 10) + "px";
  }
  function ocultaTip() { $("tip").hidden = true; }
  const vacio = (nodo, msg) => { nodo.innerHTML = `<div class="vacio">${msg}</div>`; };

  function barrasAnio(nodo, datos, { alto = 240, ancho = 560, etiqueta, sufijo = "" } = {}) {
    nodo.innerHTML = "";
    const m = { t: 18, r: 8, b: 26, l: 42 };
    const s = svg(ancho, alto, etiqueta);
    const iw = ancho - m.l - m.r, ih = alto - m.t - m.b;
    const { tope, paso } = escalaBonita(Math.max(...datos.map((d) => d.v), 1));
    for (let y = 0; y <= tope + 1e-6; y += paso) {
      const py = m.t + ih - (y / tope) * ih;
      el(s, "line", { x1: m.l, x2: ancho - m.r, y1: py, y2: py, class: y ? "rj" : "eje" });
      el(s, "text", { x: m.l - 6, y: py + 4, "text-anchor": "end" }, fmt(y));
    }
    const bw = iw / datos.length;
    const gap = Math.min(10, bw * 0.28);
    datos.forEach((d, i) => {
      const h = (d.v / tope) * ih, x = m.l + i * bw + gap / 2, y = m.t + ih - h;
      const b = el(s, "path", { d: barraRedonda(x, y, bw - gap, h), fill: d.prov ? A.prov : A.sat, opacity: d.apag ? 0.25 : 1 });
      tip(b, `<strong>${d.t}</strong><br>${fmt(d.v)}${sufijo} ${d.prov ? "· provisional" : ""}`);
      if (datos.length <= 9 && d.v > 0) el(s, "text", { x: x + (bw - gap) / 2, y: y - 4, "text-anchor": "middle", class: "val", opacity: d.apag ? 0.4 : 1 }, fmt(d.v));
      el(s, "text", { x: x + (bw - gap) / 2, y: alto - 8, "text-anchor": "middle" }, d.c ?? d.t);
    });
    nodo.appendChild(s);
  }

  function pintaAnual() {
    const cu = {};
    ANIOS.forEach((a) => (cu[a] = 0));
    for (let i = 0; i < N; i++) if (pasa(i, true, false)) cu[anioDe[D.det.per[i]]]++;
    $("base18").textContent = fmt(cu[2018]);
    const datos = ANIOS.slice(1).map((a) => ({ t: a === 2026 ? "2026 (a setiembre)" : String(a), c: a === 2026 ? "2026*" : String(a), v: cu[a], prov: a >= 2025, apag: a < estado.desde || a > estado.hasta }));
    if (!datos.some((d) => d.v)) return vacio($("g-anual"), "No hay detecciones nuevas con estos filtros.");
    barrasAnio($("g-anual"), datos, { etiqueta: "Detecciones nuevas por año: " + datos.map((d) => `${d.t}: ${d.v}`).join(", ") });
  }

  function pintaProvincias(idx) {
    const nodo = $("g-prov");
    const c = new Map();
    idx.forEach((i) => c.set(D.det.prov[i], (c.get(D.det.prov[i]) || 0) + 1));
    const filas = [...c.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    if (!filas.length) return vacio(nodo, msgSinDatos());
    nodo.innerHTML = "";
    const fila = 30, ancho = 560, l = 140, r = 58;
    const s = svg(ancho, filas.length * fila + 6, "Provincias con más detecciones: " + filas.map(([p, v]) => `${D.provs[p]} ${v}`).join(", "));
    const max = filas[0][1];
    filas.forEach(([p, v], k) => {
      const y = k * fila + 3, w = Math.max(2, (v / max) * (ancho - l - r));
      el(s, "text", { x: l - 8, y: y + 16, "text-anchor": "end" }, D.provs[p]);
      const b = el(s, "path", { d: `M${l},${y + 3}H${l + w - 3}Q${l + w},${y + 3} ${l + w},${y + 6}V${y + 19}Q${l + w},${y + 22} ${l + w - 3},${y + 22}H${l}Z`, fill: A.sat });
      tip(b, `<strong>${D.provs[p]}</strong><br>${fmt(v)} detecciones`);
      el(s, "text", { x: l + w + 6, y: y + 17, class: "val" }, fmt(v));
    });
    nodo.appendChild(s);
  }

  function serieZona(cond) {
    const o = {};
    ANIOS.slice(1).forEach((a) => (o[a] = 0));
    for (let i = 0; i < N; i++) {
      const a = anioDe[D.det.per[i]];
      if (a > 2018 && pasa(i, false, false) && cond(i)) o[a]++;
    }
    return ANIOS.slice(1).map((a) => ({ t: a === 2026 ? "2026 (a setiembre)" : String(a), c: "’" + String(a).slice(2), v: o[a], prov: a >= 2025 }));
  }
  function pintaZonas() {
    const nodo = $("g-zonas");
    nodo.innerHTML = "";
    const defs = [
      ["Reserva Nacional Tambopata", (i) => D.det.bits[i] & BIT.tambopata],
      ["Zonas de amortiguamiento", (i) => D.det.bits[i] & BIT.amort],
    ];
    defs.forEach(([t, cond]) => {
      const c = document.createElement("div");
      c.innerHTML = `<h4>${t}</h4><div></div>`;
      nodo.appendChild(c);
      const datos = serieZona(cond);
      if (!datos.some((d) => d.v)) return vacio(c.lastChild, "Sin detecciones en esta selección.");
      barrasAnio(c.lastChild, datos, { alto: 220, ancho: 300, etiqueta: t + ": " + datos.map((d) => `${d.t} ${d.v}`).join(", ") });
    });
  }

  function linea(nodo, series, { etiqueta, sufijo = "", cats, alto = 240, min0 = true }) {
    nodo.innerHTML = "";
    const ancho = 560, m = { t: 14, r: 86, b: 26, l: 42 };
    const s = svg(ancho, alto, etiqueta);
    const iw = ancho - m.l - m.r, ih = alto - m.t - m.b;
    const todos = series.flatMap((q) => q.v.filter((x) => x != null));
    const { tope, paso } = escalaBonita(Math.max(...todos, 1));
    const X = (i) => m.l + (cats.length === 1 ? iw / 2 : (i / (cats.length - 1)) * iw);
    const Y = (v) => m.t + ih - (v / tope) * ih;
    for (let y = 0; y <= tope + 1e-6; y += paso) {
      el(s, "line", { x1: m.l, x2: m.l + iw, y1: Y(y), y2: Y(y), class: y ? "rj" : "eje" });
      el(s, "text", { x: m.l - 6, y: Y(y) + 4, "text-anchor": "end" }, fmt(y) + sufijo);
    }
    cats.forEach((c, i) => {
      if (cats.length > 9 && i % 2) return;
      el(s, "text", { x: X(i), y: alto - 8, "text-anchor": "middle" }, c);
    });
    series.forEach((q) => {
      const pts = q.v.map((v, i) => (v == null ? null : [X(i), Y(v)])).filter(Boolean);
      el(s, "path", { d: "M" + pts.map((p) => p.join(",")).join("L"), fill: "none", stroke: q.color, "stroke-width": 2.25, "stroke-linejoin": "round", "stroke-linecap": "round" });
      const u = q.v.length - 1;
      if (q.v[u] != null) {
        el(s, "circle", { cx: X(u), cy: Y(q.v[u]), r: 4, fill: q.color, stroke: "#fff", "stroke-width": 2 });
        el(s, "text", { x: X(u) + 8, y: Y(q.v[u]) + 4, class: "val" }, (q.fmt || fmt)(q.v[u]) + sufijo);
      }
    });
    const cruz = el(s, "line", { y1: m.t, y2: m.t + ih, stroke: "#6b675e", opacity: 0 });
    cats.forEach((c, i) => {
      const h = el(s, "rect", { x: X(i) - iw / cats.length / 2, y: m.t, width: iw / cats.length, height: ih, fill: "transparent" });
      h.addEventListener("mousemove", (ev) => {
        cruz.setAttribute("x1", X(i)); cruz.setAttribute("x2", X(i)); cruz.setAttribute("opacity", 0.5);
        muestraTip(`<strong>${c}</strong><br>` + series.map((q) => `${q.n}: ${q.v[i] == null ? "s/d" : (q.fmt || fmt)(q.v[i]) + sufijo}`).join("<br>"), ev);
      });
      h.addEventListener("mouseleave", () => { cruz.setAttribute("opacity", 0); ocultaTip(); });
    });
    nodo.appendChild(s);
  }

  function pintaCorredor() {
    const a = ANIOS.slice(1), tot = {}, fue = {};
    a.forEach((y) => { tot[y] = 0; fue[y] = 0; });
    for (let i = 0; i < N; i++) {
      const y = anioDe[D.det.per[i]];
      if (y > 2018 && D.det.dep[i] === iMDD) { tot[y]++; if (!(D.det.bits[i] & BIT.corredor)) fue[y]++; }
    }
    const v = a.map((y) => Math.round(pct(fue[y], tot[y]) * 10) / 10);
    linea($("g-corredor"), [{ n: "Fuera del corredor", v, color: A.sat, fmt: (x) => Math.round(x) }], { etiqueta: "Porcentaje de detecciones de Madre de Dios fuera del corredor: " + a.map((y, i) => `${y}: ${v[i]} %`).join(", "), sufijo: " %", cats: a.map((y) => (y === 2026 ? "2026*" : String(y))) });
  }

  function pintaOro() {
    const a = ANIOS.slice(1), c = {};
    a.forEach((y) => (c[y] = 0));
    for (let i = 0; i < N; i++) {
      const y = anioDe[D.det.per[i]];
      if (y > 2018 && pasa(i, true, false)) c[y]++;
    }
    if (!c[2019]) {
      linea($("g-oro"), [{ n: "Precio del oro", v: a.map((y) => Math.round((D.oro[y] / D.oro[2019]) * 100)), color: A.oro }], { etiqueta: "Índice del precio del oro con 2019 igual a 100", cats: a.map((y) => (y === 2026 ? "2026*" : String(y))) });
      return;
    }
    linea($("g-oro"), [
      { n: "Precio del oro", v: a.map((y) => Math.round((D.oro[y] / D.oro[2019]) * 100)), color: A.oro },
      { n: "Detecciones nuevas", v: a.map((y) => Math.round((c[y] / c[2019]) * 100)), color: A.sat },
    ], { etiqueta: "Índice con 2019 igual a 100 del precio del oro y las detecciones nuevas", cats: a.map((y) => (y === 2026 ? "2026*" : String(y))) });
  }

  function pintaPadron() {
    const nodo = $("g-padron");
    nodo.innerHTML = "";
    const t = D.reinfo;
    const v = Object.values(t).reduce((s, x) => s + x.v, 0), su = Object.values(t).reduce((s, x) => s + x.s, 0);
    const filas = [["Febrero de 2025", v, su], ["Noviembre de 2026", D.padron_hoy.VIGENTE, D.padron_hoy.SUSPENDIDO]];
    const ancho = 560, l = 130, r = 66, max = v + su, g = 2;
    const s = svg(ancho, 150, `Padrón REINFO. Febrero de 2025: ${v} vigentes y ${su} suspendidas. Noviembre de 2026: ${filas[1][1]} vigentes y ${filas[1][2]} suspendidas.`);
    filas.forEach(([n, a, b], k) => {
      const y = 24 + k * 62, esc = (ancho - l - r) / max, wa = a * esc, wb = b * esc;
      el(s, "text", { x: l - 8, y: y + 21, "text-anchor": "end" }, n);
      tip(el(s, "rect", { x: l, y, width: wa, height: 32, rx: 3, fill: A.rei }), `<strong>${n}</strong><br>${fmt(a)} vigentes`);
      tip(el(s, "rect", { x: l + wa + g, y, width: wb, height: 32, rx: 3, fill: A.sus }), `<strong>${n}</strong><br>${fmt(b)} suspendidas`);
      el(s, "text", { x: l + wa + wb + 8, y: y + 21, class: "val" }, fmt(a + b));
      el(s, "text", { x: l + 4, y: y + 49 }, `${fmt(a)} vigentes · ${fmt(b)} suspendidas`);
    });
    nodo.appendChild(s);
  }

  const msgSinDatos = () => estado.dep
    ? `El satélite no registra detecciones en ${estado.dep} con estos filtros. Eso no prueba que no haya minería: el modelo cubre la cuenca amazónica y no ve minería subterránea.`
    : "No hay detecciones con estos filtros.";

  /* ---------- KPI ---------- */
  function kpis(idx) {
    const n = idx.length;
    const sens = idx.filter((i) => D.det.bits[i] & (BIT.anp | BIT.amort)).length;
    const lejos = idx.filter((i) => D.det.km[i] > estado.km).length;
    const base = {};
    for (let i = 0; i < N; i++) {
      if (!pasa(i, true, false)) continue;
      const a = anioDe[D.det.per[i]];
      base[a] = (base[a] || 0) + 1;
    }
    const prom = [2019, 2020, 2021, 2022, 2023, 2024].reduce((s, a) => s + (base[a] || 0), 0) / 6;
    const var25 = prom ? pct((base[2025] || 0) - prom, prom) : null;
    const rt = estado.dep ? D.reinfo[estado.dep] : Object.values(D.reinfo).reduce((o, x) => ({ t: o.t + x.t, v: o.v + x.v, s: o.s + x.s }), { t: 0, v: 0, s: 0 });
    const conf = estado.dep ? D.conflictos[estado.dep] ?? 0 : Object.values(D.conflictos).reduce((a, b) => a + b, 0) + Object.values(D.conflictos_otros).reduce((a, b) => a + b, 0);
    const c = [
      ["Detecciones en la selección", fmt(n), `${estado.desde === 2018 ? "hasta 2018" : estado.desde} a ${estado.hasta === 2026 ? "set. 2026" : estado.hasta}`],
      ["2025 frente al promedio 2019-2024", var25 == null ? "s/d" : (var25 > 0 ? "+" : "") + Math.round(var25) + " %", `${fmt(base[2025] || 0)} frente a ${fmt(prom)}; provisional`],
      ["En área natural o amortiguamiento", n ? pctT(pct(sens, n)) : "s/d", `${fmt(sens)} detecciones`],
      [`A más de ${estado.km} km de un punto REINFO`, n ? pctT(pct(lejos, n)) : "s/d", `${fmt(lejos)} detecciones`],
      ["Inscripciones REINFO, feb. 2025", rt ? fmt(rt.t) : "0", rt && rt.t ? `${Math.round(pct(rt.s, rt.t))} % suspendidas` : "Sin inscripciones"],
      ["Conflictos sociales, jul. 2026", fmt(conf), estado.dep ? "Todos los tipos" : "Todos los tipos; incluye multirregionales"],
    ];
    $("kpis").innerHTML = c.map(([e, v, s]) => `<div class="kpi"><span class="e">${e}</span><span class="v">${v}</span><span class="s">${s}</span></div>`).join("");
  }

  /* ---------- Tabla ---------- */
  let ordenC = "d", ordenD = -1;
  const filasTabla = (() => {
    const det = {}, rec = {};
    D.deps.forEach((d) => { det[d] = 0; rec[d] = 0; });
    for (let i = 0; i < N; i++) {
      const d = D.deps[D.det.dep[i]];
      det[d]++;
      if (anioDe[D.det.per[i]] >= 2024) rec[d]++;
    }
    return D.deps.map((n) => {
      const r = D.reinfo[n] || { t: 0, s: 0 };
      return { n, t: r.t, ps: r.t ? pct(r.s, r.t) : 0, d: det[n], r: rec[n], c: D.conflictos[n] ?? 0 };
    });
  })();
  function pintaTabla() {
    const q = $("f-buscar").value.trim().toLocaleLowerCase("es").normalize("NFD").replace(/[̀-ͯ]/g, "");
    const fs = filasTabla.filter((f) => f.n.toLocaleLowerCase("es").normalize("NFD").replace(/[̀-ͯ]/g, "").includes(q))
      .sort((a, b) => (ordenC === "n" ? a.n.localeCompare(b.n, "es") : a[ordenC] - b[ordenC]) * ordenD || a.n.localeCompare(b.n, "es"));
    const cuerpo = document.querySelector("#tabla tbody");
    cuerpo.innerHTML = fs.map((f) => `<tr data-d="${f.n}" tabindex="0" class="${f.n === estado.dep ? "sel" : ""}"><td>${f.n}</td><td class="n">${fmt(f.t)}</td><td class="n">${f.t ? Math.round(f.ps) + " %" : "-"}</td><td class="n">${fmt(f.d)}</td><td class="n">${fmt(f.r)}</td><td class="n">${fmt(f.c)}</td></tr>`).join("") || `<tr><td colspan="6">Sin resultados.</td></tr>`;
    document.querySelectorAll("#tabla th button").forEach((b) => {
      const th = b.parentElement;
      th.setAttribute("aria-sort", b.dataset.c === ordenC ? (ordenD > 0 ? "ascending" : "descending") : "none");
      b.textContent = b.textContent.replace(/ [▲▼]$/, "") + (b.dataset.c === ordenC ? (ordenD > 0 ? " ▲" : " ▼") : "");
    });
  }

  /* ---------- Repintado ---------- */
  function pinta() {
    const idx = [];
    for (let i = 0; i < N; i++) if (pasa(i)) idx.push(i);
    $("s-km").textContent = estado.km + " km";
    const partes = [estado.dep || "Todo el Perú", `${estado.desde}-${estado.hasta}`, $("f-zona").selectedOptions[0].text];
    $("estado").textContent = `Mostrando ${fmt(idx.length)} detecciones · ${partes.join(" · ")}`;
    $("t-mapa").textContent = estado.dep ? `Mapa: ${estado.dep}` : "Mapa de detecciones y registros";
    kpis(idx);
    pintaAnual();
    pintaProvincias(idx);
    pintaZonas();
    pintaCorredor();
    pintaOro();
    pintaPadron();
    pintaTabla();
    if (mapaListo) mapa.getSource("det").setData(geoDet());
    window.__listo = true;
  }

  /* ---------- Eventos ---------- */
  function ponDep(d) {
    estado.dep = d;
    $("f-dep").value = d;
    pinta();
    encuadra();
  }
  $("f-dep").addEventListener("change", (e) => ponDep(e.target.value));
  $("f-desde").addEventListener("change", (e) => {
    estado.desde = +e.target.value;
    if (estado.desde > estado.hasta) { estado.hasta = estado.desde; $("f-hasta").value = estado.hasta; }
    pinta();
  });
  $("f-hasta").addEventListener("change", (e) => {
    estado.hasta = +e.target.value;
    if (estado.hasta < estado.desde) { estado.desde = estado.hasta; $("f-desde").value = estado.desde; }
    pinta();
  });
  $("f-zona").addEventListener("change", (e) => { estado.zona = e.target.value; pinta(); });
  $("f-km").addEventListener("input", (e) => { estado.km = +e.target.value; pinta(); });
  ["c-det", "c-rej", "c-anp", "c-cor", "c-fondo"].forEach((i) => $(i).addEventListener("change", aplicaCapas));
  $("b-limpiar").addEventListener("click", () => {
    Object.assign(estado, { dep: "", desde: 2018, hasta: 2026, zona: "todas", km: 5 });
    $("f-dep").value = ""; $("f-desde").value = 2018; $("f-hasta").value = 2026; $("f-zona").value = "todas"; $("f-km").value = 5; $("f-buscar").value = "";
    pinta();
    encuadra();
  });
  $("b-csv").addEventListener("click", () => {
    const filas = ["longitud,latitud,periodo,departamento,provincia,en_area_natural,en_amortiguamiento,en_corredor_mdd,km_reinfo"];
    for (let i = 0; i < N; i++) {
      if (!pasa(i)) continue;
      const b = D.det.bits[i];
      filas.push([D.det.lon[i], D.det.lat[i], D.periodos[D.det.per[i]], `"${D.deps[D.det.dep[i]]}"`, `"${D.provs[D.det.prov[i]]}"`, b & BIT.anp ? 1 : 0, b & BIT.amort ? 1 : 0, b & BIT.corredor ? 1 : 0, D.det.km[i]].join(","));
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["﻿" + filas.join("\n")], { type: "text/csv;charset=utf-8" }));
    a.download = "detecciones_mineria_filtradas.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  });
  $("f-buscar").addEventListener("input", pintaTabla);
  document.querySelector("#tabla thead").addEventListener("click", (e) => {
    const c = e.target.dataset && e.target.dataset.c;
    if (!c) return;
    if (ordenC === c) ordenD *= -1; else { ordenC = c; ordenD = c === "n" ? 1 : -1; }
    pintaTabla();
  });
  const elegirFila = (e) => {
    const tr = e.target.closest("tr[data-d]");
    if (!tr) return;
    ponDep(tr.dataset.d === estado.dep ? "" : tr.dataset.d);
    $("explorar").scrollIntoView();
  };
  document.querySelector("#tabla tbody").addEventListener("click", elegirFila);
  document.querySelector("#tabla tbody").addEventListener("keydown", (e) => { if (e.key === "Enter") elegirFila(e); });

  /* Permite abrir el tablero ya filtrado: ?dep=Apurímac&zona=fuera&fondo=sat */
  if (params.get("dep") && D.deps.includes(params.get("dep"))) { estado.dep = params.get("dep"); $("f-dep").value = estado.dep; mapa.once("load", encuadra); }
  if (params.get("zona")) { estado.zona = params.get("zona"); $("f-zona").value = estado.zona; }
  if (params.get("fondo")) { $("c-fondo").value = params.get("fondo"); }
  if (params.get("desde")) { estado.desde = +params.get("desde"); $("f-desde").value = estado.desde; }
  if (params.get("reinfo")) { $("c-rej").checked = true; }
  pinta();
})();
