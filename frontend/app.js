// Frontend del pronóstico: consume la API FastAPI (detrás de nginx en /api).
const API = location.protocol === "file:" || location.port === "5500" ? "http://localhost:8000" : "/api";
const COLORES = {};
const graficos = {};
let opciones = null;
let ultimoResultado = null;  // { r, render } para redibujar los gráficos al cambiar de tema
let metadatos = null;        // respuesta de /metadata para el dashboard (se pide una vez)

// ---------------------------------------------------------------- tema claro / oscuro
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
function leerColores() {
  COLORES.petroleo = css("--petroleo"); COLORES.gas = css("--gas");
  COLORES.acento = css("--acento"); COLORES.suave = css("--suave");
  Chart.defaults.color = css("--suave"); Chart.defaults.borderColor = css("--borde");
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  // Leyendas con la forma de cada serie (línea, punteada o barra) en lugar de cuadrados llenos
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxHeight = 8;
}
function actualizarBotonTema() {
  const claro = document.documentElement.dataset.theme === "light";
  const b = document.querySelector("#tema");
  b.querySelector(".tema-texto").textContent = claro ? "Oscuro" : "Claro";
  b.setAttribute("aria-label", claro ? "Cambiar a modo oscuro" : "Cambiar a modo claro");
}
document.querySelector("#tema").addEventListener("click", () => {
  const claro = document.documentElement.dataset.theme !== "light";
  if (claro) document.documentElement.dataset.theme = "light"; else delete document.documentElement.dataset.theme;
  try { localStorage.setItem("tema", claro ? "light" : "dark"); } catch (e) {}
  leerColores(); actualizarBotonTema();
  if (ultimoResultado && !document.querySelector("#resultado").classList.contains("oculto")) ultimoResultado.render(ultimoResultado.r);
  if (metadatos && !document.querySelector("#panel-metricas").classList.contains("oculto")) renderMetricas(metadatos);
});
leerColores(); actualizarBotonTema();

const $ = (s, r = document) => r.querySelector(s);
const fmt = (v, d = 1) => v == null ? "—" : Number(v).toLocaleString("es-AR", { maximumFractionDigits: d, minimumFractionDigits: 0 });
const escapar = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = v => v == null ? "—" : `${fmt(v * 100, 1)} %`;

async function pedir(ruta, cuerpo) {
  const r = await fetch(API + ruta, cuerpo ? { method: "POST", headers: { "Content-Type": "application/json" },
                                              body: JSON.stringify(cuerpo) } : {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || r.statusText));
  return j;
}

// ---------------------------------------------------------------- pestañas
// El indicador del segmentado se desliza hasta la pestaña activa
function moverIndicador() {
  const t = $(".tab.activa"), nav = $(".tabs");
  nav.style.setProperty("--x", `${t.offsetLeft}px`);
  nav.style.setProperty("--w", `${t.offsetWidth}px`);
  // La primera ubicación no se anima; desde ahí el indicador se desliza
  requestAnimationFrame(() => nav.classList.add("listo"));
}
document.querySelectorAll(".tab").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(x => {
    x.classList.toggle("activa", x === b); x.setAttribute("aria-selected", x === b);
  });
  $("#panel-existente").classList.toggle("oculto", b.dataset.tab !== "existente");
  $("#panel-nuevo").classList.toggle("oculto", b.dataset.tab !== "nuevo");
  $("#panel-metricas").classList.toggle("oculto", b.dataset.tab !== "metricas");
  // En Métricas se esconden el resultado y el error del pronóstico, sin perderlos (ver estilos.css)
  document.querySelector("main").dataset.vista = b.dataset.tab;
  if (b.dataset.tab === "metricas") cargarMetricas();
  moverIndicador();
}));
// Se recalcula si cambia el tamaño de las pestañas (carga de la tipografía, rotación, ancho de ventana)
new ResizeObserver(moverIndicador).observe($(".tabs"));

// ---------------------------------------------------------------- brillo del vidrio
// Cada superficie de vidrio refleja la posición del cursor (variables --mx/--my del CSS)
document.addEventListener("pointermove", e => {
  const v = e.target.closest?.(".vidrio"); if (!v) return;
  const r = v.getBoundingClientRect();
  v.style.setProperty("--mx", `${e.clientX - r.left}px`);
  v.style.setProperty("--my", `${e.clientY - r.top}px`);
}, { passive: true });

// ---------------------------------------------------------------- inicio
async function iniciar() {
  try {
    const h = await pedir("/health");
    $("#estado-api").textContent = `Modelos ${h.version_modelos}, datos hasta ${h.datos_hasta}`;
    $("#estado-api").classList.add("ok");
    opciones = await pedir("/opciones");
    cargarOpciones();
  } catch (e) {
    $("#estado-api").textContent = "API no disponible";
    $("#estado-api").classList.add("caido");
    mostrarError("No se pudo conectar con la API: " + e.message);
  }
}

function cargarOpciones() {
  const f = $("#form-nuevo");
  const llenar = (nombre, valores, etiqueta = v => v) =>
    f.elements[nombre].innerHTML = valores.map(v => `<option value="${v}">${etiqueta(v)}</option>`).join("");
  llenar("formacion", opciones.formacion);
  llenar("sub_tipo_recurso", opciones.sub_tipo_recurso);
  llenar("tipopozo", opciones.tipopozo);
  llenar("empresa", opciones.empresa);
  const areas = [...opciones.areas].sort((a, b) => b.n - a.n);
  f.elements.areayacimiento.innerHTML = areas.map(a =>
    `<option value="${a.areayacimiento}">${a.areayacimiento} (${a.n} pozos)</option>`).join("");
  f.elements.areayacimiento.addEventListener("change", completarArea);
  f.elements.anio_inicio.value = opciones.rangos.anio_inicio[1];
  $("#campos-c4").classList.toggle("oculto", !opciones.usa_capitulo_iv);
  if (opciones.tipopozo.includes("Petrolífero")) f.elements.tipopozo.value = "Petrolífero";
  completarArea();
}

// Al elegir un área se proponen lat/lon/profundidad típicas (medianas de los pozos del área)
function completarArea() {
  const f = $("#form-nuevo");
  const a = opciones.areas.find(x => x.areayacimiento === f.elements.areayacimiento.value);
  if (!a) return;
  f.elements.lat.value = a.lat.toFixed(4);
  f.elements.lon.value = a.lon.toFixed(4);
  f.elements.profundidad.value = Math.round(a.profundidad);
  f.elements.es_horizontal.value = a.horizontal == null ? "" : String(a.horizontal);
  f.elements.dias_perf.value = a.dias_perf == null ? "" : Math.round(a.dias_perf);
  f.elements.dias_term.value = a.dias_term == null ? "" : Math.round(a.dias_term);
}

// ---------------------------------------------------------------- búsqueda de pozos
let temporizador;
$("#buscar").addEventListener("input", e => {
  clearTimeout(temporizador);
  $("#idpozo").value = /^\d+$/.test(e.target.value.trim()) ? e.target.value.trim() : "";
  const q = e.target.value.trim();
  if (q.length < 2) { $("#sugerencias").innerHTML = ""; return; }
  temporizador = setTimeout(async () => {
    const res = await pedir(`/pozos?q=${encodeURIComponent(q)}`).catch(() => []);
    $("#sugerencias").innerHTML = res.length ? res.map(p =>
      `<li data-id="${p.idpozo}" data-sigla="${p.sigla}" class="${p.activo ? "" : "inactivo"}">
        <span class="estado ${p.activo ? "on" : "off"}">${p.activo ? "activo" : "sin producción" + (p.ultima_produccion ? " desde " + p.ultima_produccion : "")}</span>
        ${p.sigla} <small>· ${p.idpozo} · ${p.formacion} · ${p.areayacimiento} · ${p.empresa} · ${p.fluido}</small></li>`).join("")
      : `<li class="vacio">Sin resultados para "${escapar(q)}"</li>`;
  }, 250);
});
$("#sugerencias").addEventListener("click", e => {
  const li = e.target.closest("li"); if (!li || !li.dataset.id) return;
  $("#idpozo").value = li.dataset.id;
  $("#buscar").value = li.dataset.sigla;
  $("#sugerencias").innerHTML = "";
});

// Limpiar: borra la búsqueda, las sugerencias, el resultado y los mensajes de error
$("#limpiar").addEventListener("click", () => {
  clearTimeout(temporizador);
  $("#buscar").value = ""; $("#idpozo").value = ""; $("#horizonte").value = 12;
  $("#sugerencias").innerHTML = "";
  $("#error").classList.add("oculto");
  $("#resultado").classList.add("oculto");
  for (const k in graficos) { graficos[k].destroy(); delete graficos[k]; }
  $("#buscar").focus();
});

// ---------------------------------------------------------------- envíos
$("#form-existente").addEventListener("submit", async e => {
  e.preventDefault();
  const id = Number($("#idpozo").value);
  if (!id) return mostrarError("Elegí un pozo de la lista de sugerencias o ingresá un idpozo numérico.");
  await ejecutar(e.submitter, () => pedir("/predict/existente", { idpozo: id, horizonte: Number($("#horizonte").value) }),
                 renderExistente);
});

$("#form-nuevo").addEventListener("submit", async e => {
  e.preventDefault();
  const d = Object.fromEntries(new FormData(e.target));
  ["profundidad", "lat", "lon"].forEach(k => d[k] = Number(d[k]));
  d.anio_inicio = Number(d.anio_inicio);
  // Opcionales: vacío = el modelo usa el valor típico del área
  d.es_horizontal = d.es_horizontal === "" ? null : d.es_horizontal === "true";
  ["dias_perf", "dias_term"].forEach(k => d[k] = d[k] === "" ? null : Number(d[k]));
  if (!opciones.usa_capitulo_iv) ["es_horizontal", "dias_perf", "dias_term"].forEach(k => delete d[k]);
  await ejecutar(e.submitter, () => pedir("/predict/nuevo", d), renderNuevo);
});

async function ejecutar(boton, llamada, render) {
  boton.disabled = true; $("#error").classList.add("oculto");
  try {
    const r = await llamada(); ultimoResultado = { r, render }; render(r);
    // Solo un pronóstico nuevo dispara la entrada; redibujar por cambio de tema no
    const res = $("#resultado"); res.classList.remove("entrando"); void res.offsetWidth; res.classList.add("entrando");
  }
  catch (err) { mostrarError(err.message); }
  finally { boton.disabled = false; }
}

function mostrarError(m) { const el = $("#error"); el.textContent = m; el.classList.remove("oculto"); }

// ---------------------------------------------------------------- render
function renderExistente(r) {
  const p = r.pozo;
  $("#encabezado").innerHTML = `<h2>${p.sigla} <small>(idpozo ${p.idpozo})</small></h2>
    <p>${p.empresa} · ${p.formacion} (${p.sub_tipo_recurso}) · ${p.areayacimiento}, ${p.provincia} · fluido ${p.fluido}
    · pronóstico desde ${r.origen}</p>`;
  for (const fl of ["petroleo", "gas"]) {
    const c = r.pronostico[fl];
    const hist = { x: r.historia.fecha.map(f => f.slice(0, 7)), y: r.historia[fl] };
    renderFluido(fl, c, hist, c && [
      ["Último mes", fmt(c.ultimo_mes)], ["Acumulada pronosticada (P50)", fmt(c.acumulada_p50, 0)],
      ["Rango acumulada P10–P90", `${fmt(c.acumulada_p10, 0)} – ${fmt(c.acumulada_p90, 0)}`],
      ["Caudal diario mes 1", `${fmt(c.caudal_diario_inicial, 1)} /d`],
      ["Variación último mes → mes 12", c.declinacion_12m == null ? "—" : `${c.declinacion_12m > 0 ? "−" : "+"}${pct(Math.abs(c.declinacion_12m))}`],
      ["R² test · mes 1 / mes 12", `${fmt(c.metricas_modelo.r2_h1, 2)} / ${fmt(c.metricas_modelo.r2_h12, 2)}`],
    ]);
  }
  const i = r.indicadores_actuales;
  renderInfo(r.cluster, [
    ["GOR último mes", i.gor_m3_m3 == null ? "—" : `${fmt(i.gor_m3_m3, 0)} m³/m³`],
    ["Corte de agua", pct(i.corte_agua)], ["Días efectivos último mes", fmt(i.dias_efectivos, 1)],
    ["Meses en producción", i.meses_en_produccion],
    ["Acumulada histórica petróleo", `${fmt(i.acum_pet_m3, 0)} m³`],
    ["Acumulada histórica gas", `${fmt(i.acum_gas_Mm3, 0)} Mm³`],
    ["Profundidad", `${fmt(p.profundidad, 0)} m`],
  ], r.avisos);
  renderTabla(r.pronostico, r.pronostico.petroleo?.eje || r.pronostico.gas?.eje, "Mes");
}

function renderNuevo(r) {
  const e = r.entrada;
  $("#encabezado").innerHTML = `<h2>Curva tipo · pozo nuevo</h2>
    <p>${e.formacion} (${e.sub_tipo_recurso}) · ${e.areayacimiento} · ${e.tipopozo} · ${e.empresa} · ${fmt(e.profundidad, 0)} m · inicio ${e.anio_inicio}${
      e.es_horizontal == null || !opciones.usa_capitulo_iv ? "" : ` · ${e.es_horizontal ? "horizontal" : "vertical/dirigido"} · perforación ${fmt(e.dias_perf, 0)} d · terminación ${fmt(e.dias_term, 0)} d`}</p>`;
  for (const fl of ["petroleo", "gas"]) {
    const c = r.pronostico[fl];
    renderFluido(fl, c, null, [
      ["Acumulada 12 meses (P50)", fmt(c.acumulada_12m_p50, 0)],
      ["Acumulada 24 meses (P50)", fmt(c.acumulada_p50, 0)],
      ["Rango 24 m P10–P90", `${fmt(c.acumulada_p10, 0)} – ${fmt(c.acumulada_p90, 0)}`],
      ["Pico mensual (P50)", `${fmt(c.pico_p50)} · mes ${c.mes_pico}`],
      ["Caudal diario mes 1", `${fmt(c.caudal_diario_inicial, 1)} /d`],
      ["Declinación pico → mes 12", pct(c.declinacion_12m)],
    ]);
  }
  renderInfo(r.cluster, [
    ["GOR esperado 12 meses", r.indicadores.gor_12m_m3_m3 == null ? "—" : `${fmt(r.indicadores.gor_12m_m3_m3, 0)} m³/m³`],
    ["Fluido dominante", r.indicadores.fluido_dominante],
    ["WAPE acumulada 12 m petróleo (test)", pct(r.pronostico.petroleo.metricas_modelo.wape_acum12)],
    ["WAPE acumulada 12 m gas (test)", pct(r.pronostico.gas.metricas_modelo.wape_acum12)],
    ["R² acumulada 12 m petróleo (test)", fmt(r.pronostico.petroleo.metricas_modelo.r2_acum12, 3)],
    ["R² acumulada 12 m gas (test)", fmt(r.pronostico.gas.metricas_modelo.r2_acum12, 3)],
  ], r.avisos);
  renderTabla(r.pronostico, r.pronostico.petroleo.eje, "Mes de vida");
}

function renderFluido(fl, c, hist, kpis) {
  const art = $(`#res-${fl}`);
  graficos[fl]?.destroy();
  if (!c) {
    art.querySelector(".kpis").innerHTML = `<p class="sin-dato">Sin producción de este fluido en el último mes informado.</p>`;
    art.querySelector(".shap").innerHTML = "";
    art.querySelector(".grafico").classList.add("oculto");
    return;
  }
  art.querySelector(".grafico").classList.remove("oculto");
  art.querySelector(".kpis").innerHTML = kpis.map(([l, v]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  const ejeF = c.eje.map(x => typeof x === "string" ? x.slice(0, 7) : `M${x}`);
  const etiquetas = hist ? [...hist.x, ...ejeF] : ejeF;
  const nH = hist ? hist.x.length : 0;
  const relleno = arr => [...Array(nH).fill(null), ...arr];
  const color = COLORES[fl];
  const series = [
    { label: "P90", data: relleno(c.p90), borderWidth: 0, pointRadius: 0, backgroundColor: color + "33", fill: "+1" },
    { label: "P10", data: relleno(c.p10), borderWidth: 0, pointRadius: 0, fill: false },
    { label: "P50 (pronóstico)", data: relleno(c.p50), borderColor: color, borderDash: [6, 3], pointRadius: 2, fill: false },
  ];
  if (hist) {
    // La historia termina en el mes de origen; se une con el primer punto pronosticado
    series.push({ label: "Histórico", data: [...hist.y, ...Array(c.p50.length).fill(null)], borderColor: color,
                  pointRadius: 1.5, fill: false });
  }
  graficos[fl] = new Chart(art.querySelector("canvas"), {
    type: "line", data: { labels: etiquetas, datasets: series },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, animation: false,
               plugins: { legend: { labels: { filter: it => it.text !== "P10" } },
                          tooltip: { callbacks: { label: x => x.raw == null ? null : `${x.dataset.label}: ${fmt(x.raw)}` } } },
               scales: { y: { beginAtZero: true, title: { display: true, text: c.unidad + "/mes" } } } },
  });
  // La unidad del impacto depende del modelo (ver docs/guia_frontend.md, sección SHAP)
  const u = c.explicacion.unidad;
  const titulo = { ratio: "Impacto (ratio vs último mes)", volumen: `Impacto (${c.unidad}/mes)`, porcentaje: "Impacto (%)" }[u];
  const valor = x => u === "volumen" ? fmt(x, 0) : u === "porcentaje" ? `${fmt(x, 1)} %` : fmt(x, 3);
  art.querySelector(".shap").innerHTML = `<tr><th>Variable</th><th class="num">${titulo}</th></tr>` +
    c.explicacion.variables.map(x => `<tr><td>${x.descripcion}</td><td class="num">${x.impacto > 0 ? "+" : ""}${valor(x.impacto)}</td></tr>`).join("");
}

function renderInfo(cluster, filas, avisos) {
  $("#avisos").innerHTML = (avisos || []).map(a => `<div class="aviso">${a}</div>`).join("");
  $("#info-cluster").innerHTML = cluster ? `<h3>Tipo de pozo (clustering K-Means)</h3>
    <p><strong>${cluster.nombre}</strong></p>
    <table><tr><td>Pozos en el grupo</td><td class="num">${cluster.pozos}</td></tr>
    <tr><td>Pico mediano petróleo</td><td class="num">${fmt(cluster.pico_pet_mediano_m3)} m³</td></tr>
    <tr><td>Pico mediano gas</td><td class="num">${fmt(cluster.pico_gas_mediano_Mm3)} Mm³</td></tr>
    <tr><td>GOR mediano</td><td class="num">${cluster.gor_mediano == null ? "— (gas seco)" : fmt(cluster.gor_mediano, 0) + " m³/m³"}</td></tr>
    <tr><td>Producción mes 12 / pico</td><td class="num">${pct(cluster.retencion_mes12)}</td></tr></table>`
    : `<h3>Tipo de pozo</h3><p class="sin-dato">Sin cluster: el pozo tiene menos de 12 meses de historia o ya producía antes de 2006.</p>`;
  $("#info-tecnica").innerHTML = `<h3>Información técnica</h3><table>${filas.map(([l, v]) =>
    `<tr><td>${l}</td><td class="num">${v}</td></tr>`).join("")}</table>`;
  $("#resultado").classList.remove("oculto");
}

function renderTabla(pron, eje, titulo) {
  const pe = pron.petroleo, ga = pron.gas;
  if (!eje) { $("#tabla-mensual").innerHTML = `<p class="sin-dato">Sin pronóstico: el pozo no produjo en el último mes informado.</p>`; return; }
  const fila = (i) => `<tr><td>${typeof eje[i] === "string" ? eje[i].slice(0, 7) : eje[i]}</td>
    ${pe ? `<td class="num">${fmt(pe.p10[i])}</td><td class="num">${fmt(pe.p50[i])}</td><td class="num">${fmt(pe.p90[i])}</td>` : "<td></td><td></td><td></td>"}
    ${ga ? `<td class="num">${fmt(ga.p10[i])}</td><td class="num">${fmt(ga.p50[i])}</td><td class="num">${fmt(ga.p90[i])}</td>` : "<td></td><td></td><td></td>"}</tr>`;
  $("#tabla-mensual").innerHTML = `<table><tr><th>${titulo}</th><th class="num">Pet P10</th><th class="num">Pet P50</th><th class="num">Pet P90</th>
    <th class="num">Gas P10</th><th class="num">Gas P50</th><th class="num">Gas P90</th></tr>${eje.map((_, i) => fila(i)).join("")}</table>`;
}

// ---------------------------------------------------------------- dashboard de métricas
// Todas las métricas son de test (2024–2025) y vienen de models/metadata.json vía /metadata
const R2_VERSION_1 = 0.907;  // R² a 1 mes del proyecto anterior (solo petróleo), ver README

async function cargarMetricas() {
  if (metadatos) return renderMetricas(metadatos);
  try {
    metadatos = await pedir("/metadata");
    renderMetricas(metadatos);
    const p = $("#panel-metricas"); p.classList.remove("entrando"); void p.offsetWidth; p.classList.add("entrando");
  } catch (e) { mostrarError("No se pudieron cargar las métricas: " + e.message); }
}

// Dibuja una línea vertical de referencia en un valor del eje x (cobertura ideal 80 %)
const referencia = valor => ({
  id: "referencia",
  afterDatasetsDraw(ch) {
    const x = ch.scales.x.getPixelForValue(valor), { top, bottom } = ch.chartArea, c = ch.ctx;
    c.save(); c.strokeStyle = COLORES.acento; c.setLineDash([5, 4]); c.lineWidth = 1.5;
    c.beginPath(); c.moveTo(x, top); c.lineTo(x, bottom); c.stroke();
    c.fillStyle = COLORES.acento; c.font = `12px ${Chart.defaults.font.family}`; c.fillText("ideal 80 %", x + 6, top + 12);
    c.restore();
  },
});

function grafico(id, config, plugins = []) {
  graficos[id]?.destroy();
  graficos[id] = new Chart($(`#${id} canvas`), { ...config, plugins,
    options: { responsive: true, maintainAspectRatio: false, animation: false,
               interaction: { mode: "index", intersect: false }, ...config.options } });
}
const lectura = (id, texto) => $(`#${id} .lectura`).innerHTML = texto;
const num = (v, d = 2) => fmt(v, d);

function renderMetricas(m) {
  const pe = m.modelos.petroleo_existente.metricas_test, ge = m.modelos.gas_existente.metricas_test;
  const pn = m.modelos.petroleo_nuevo.metricas_test, gn = m.modelos.gas_nuevo.metricas_test;
  const H = Object.keys(pe.por_horizonte).sort((a, b) => a - b);
  const serie = (met, quien, campo) => H.map(h => met.por_horizonte[h][quien][campo]);
  const { petroleo: cP, gas: cG, suave: cS, acento: cA } = COLORES;
  const linea = (label, data, color, base) => ({ label, data, borderColor: base ? color + "99" : color,
    backgroundColor: color, borderWidth: base ? 1.5 : 2.5, borderDash: base ? [5, 4] : [], pointRadius: base ? 0 : 3, pointStyle: base ? "line" : "circle" });

  $("#m-kpis").innerHTML = [
    [`${num(pe.por_horizonte[1].modelo.r2)} / ${num(ge.por_horizonte[1].modelo.r2)}`, "R² a 1 mes · petróleo / gas"],
    [`${num(pe.por_horizonte[12].modelo.r2)} / ${num(ge.por_horizonte[12].modelo.r2)}`, "R² a 12 meses · petróleo / gas"],
    [`${pct(pn.acum_12m.modelo.wape)} / ${pct(gn.acum_12m.modelo.wape)}`, "Error acumulada 12 m, pozo nuevo (WAPE)"],
    [`${pct(pe.cobertura_p10_p90)} / ${pct(ge.cobertura_p10_p90)}`, "Meses reales dentro de la banda P10–P90"],
  ].map(([v, l]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");

  // 1 · R² por horizonte
  grafico("m1", { type: "line", data: { labels: H.map(h => `${h}`), datasets: [
      linea("Petróleo · modelo", serie(pe, "modelo", "r2"), cP), linea("Gas · modelo", serie(ge, "modelo", "r2"), cG),
      linea("Petróleo · persistencia", serie(pe, "persistencia", "r2"), cP, true),
      linea("Gas · persistencia", serie(ge, "persistencia", "r2"), cG, true)] },
    options: { scales: { x: { title: { display: true, text: "Meses adelante" } }, y: { title: { display: true, text: "R²" } } },
               plugins: { tooltip: { callbacks: { title: x => `${x[0].label} ${x[0].label === "1" ? "mes" : "meses"} adelante`,
                                                  label: x => `${x.dataset.label}: ${num(x.raw)}` } } } } });
  lectura("m1", `Petróleo: R² ${num(pe.por_horizonte[1].modelo.r2)} a 1 mes y ${num(pe.por_horizonte[12].modelo.r2)} a 12 meses; repetir el último mes cae a ${num(pe.por_horizonte[12].persistencia.r2)}.`);

  // 2 · WAPE por horizonte
  grafico("m2", { type: "line", data: { labels: H.map(h => `${h}`), datasets: [
      linea("Petróleo · modelo", serie(pe, "modelo", "wape"), cP), linea("Gas · modelo", serie(ge, "modelo", "wape"), cG),
      linea("Petróleo · persistencia", serie(pe, "persistencia", "wape"), cP, true),
      linea("Gas · persistencia", serie(ge, "persistencia", "wape"), cG, true)] },
    options: { scales: { x: { title: { display: true, text: "Meses adelante" } },
                         y: { title: { display: true, text: "WAPE (más bajo es mejor)" }, ticks: { callback: v => `${Math.round(v * 100)} %` } } },
               plugins: { tooltip: { callbacks: { label: x => `${x.dataset.label}: ${pct(x.raw)}` } } } } });
  lectura("m2", `A 12 meses el pronóstico de petróleo se desvía ${pct(pe.por_horizonte[12].modelo.wape)}; repetir el último mes, ${pct(pe.por_horizonte[12].persistencia.wape)}.`);

  // 3 · Backtest pozo existente: modelo, Arps y persistencia
  const bp = pe.backtest_origen_2023_12, bg = ge.backtest_origen_2023_12;
  const etiquetas4 = ["R² petróleo", "R² gas", "WAPE petróleo", "WAPE gas"];
  const valores4 = (a, b) => [a.r2, b.r2, a.wape, b.wape];
  grafico("m3", { type: "bar", data: { labels: etiquetas4, datasets: [
      { label: "Modelo", data: valores4(bp.modelo, bg.modelo), backgroundColor: cA, borderRadius: 6 },
      { label: "Arps", data: valores4(bp.arps, bg.arps), backgroundColor: cS + "99", borderRadius: 6 },
      { label: "Persistencia", data: valores4(bp.persistencia, bg.persistencia), backgroundColor: cS + "44", borderRadius: 6 }] },
    options: { plugins: { tooltip: { callbacks: { label: x => `${x.dataset.label}: ${x.dataIndex < 2 ? num(x.raw) : pct(x.raw)}` } } } } });
  lectura("m3", `Partiendo de dic-2023 (${fmt(bp.pozos, 0)} pozos), el modelo logra R² ${num(bp.modelo.r2)} en petróleo contra ${num(bp.arps.r2)} de Arps.`);

  // 4 · Pozo nuevo: modelo contra curva mediana (acumulada 12 meses)
  const ap = pn.acum_12m, ag = gn.acum_12m;
  grafico("m4", { type: "bar", data: { labels: etiquetas4, datasets: [
      { label: "Modelo", data: valores4(ap.modelo, ag.modelo), backgroundColor: cA, borderRadius: 6 },
      { label: "Curva mediana", data: valores4(ap.curva_mediana, ag.curva_mediana), backgroundColor: cS + "77", borderRadius: 6 }] },
    options: { plugins: { tooltip: { callbacks: { label: x => `${x.dataset.label}: ${x.dataIndex < 2 ? num(x.raw) : pct(x.raw)}` } } } } });
  lectura("m4", `En ${fmt(ap.pozos, 0)} pozos nuevos, el error de la acumulada a 12 meses de petróleo baja de ${pct(ap.curva_mediana.wape)} (curva mediana) a ${pct(ap.modelo.wape)}.`);

  // 5 · Cobertura de la banda P10–P90
  const cob = [["Petróleo · existente", pe, cP], ["Gas · existente", ge, cG], ["Petróleo · nuevo", pn, cP], ["Gas · nuevo", gn, cG]];
  grafico("m5", { type: "bar", data: { labels: cob.map(c => c[0]), datasets: [{ label: "Cobertura",
      data: cob.map(c => c[1].cobertura_p10_p90), backgroundColor: cob.map(c => c[2] + "cc"), borderRadius: 6 }] },
    options: { indexAxis: "y", plugins: { legend: { display: false }, tooltip: { callbacks: { label: x => `Dentro de la banda: ${pct(x.raw)}` } } },
               scales: { x: { min: 0.5, max: 1, ticks: { callback: v => `${Math.round(v * 100)} %` } } } } },
    [referencia(0.8)]);
  lectura("m5", `En pozos existentes la banda contiene ${pct(pe.cobertura_p10_p90)} de los meses (petróleo); en pozos nuevos, ${pct(pn.cobertura_p10_p90)}: algo más angosta de lo ideal.`);

  // 6 · Elección de k en el clustering
  const ev = m.clustering.evaluacion, K = Object.keys(ev).sort((a, b) => a - b), kSel = String(m.clustering.k);
  const marca = K.map(k => k === kSel ? 7 : 3);
  grafico("m6", { type: "line", data: { labels: K, datasets: [
      { label: "Silhouette (más alto mejor)", data: K.map(k => ev[k].silhouette), borderColor: cA, backgroundColor: cA, pointRadius: marca, yAxisID: "y" },
      { label: "Davies-Bouldin (más bajo mejor)", data: K.map(k => ev[k].davies_bouldin), borderColor: cS, backgroundColor: cS, borderDash: [5, 4], pointRadius: marca, yAxisID: "y1" }] },
    options: { scales: { x: { title: { display: true, text: "Cantidad de grupos (k)" } },
                         y: { position: "left", title: { display: true, text: "Silhouette" } },
                         y1: { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "Davies-Bouldin" } } },
               plugins: { tooltip: { callbacks: { title: x => `k = ${x[0].label}`, label: x => `${x.dataset.label.split(" (")[0]}: ${num(x.raw, 3)}` } } } } });
  lectura("m6", `Con k = ${kSel} la silhouette llega a su máximo (${num(ev[kSel].silhouette, 3)}) sobre ${fmt(m.clustering.pozos, 0)} pozos.`);

  // 7 · Perfiles de los clusters
  const per = m.clustering.perfiles;
  grafico("m7", { type: "bar", data: { labels: per.map(p => p.nombre), datasets: [
      { type: "bar", label: "Pozos", data: per.map(p => p.pozos), backgroundColor: per.map(p => (p.fluido === "Gas" ? cG : cP) + "aa"), borderRadius: 6, yAxisID: "y" },
      { type: "line", label: "Retención al mes 12", data: per.map(p => p.retencion_mes12), borderColor: cA, backgroundColor: cA, showLine: false, pointRadius: 6, yAxisID: "y1" }] },
    options: { scales: { x: { ticks: { maxRotation: 0, autoSkip: false, font: { size: 11 }, callback(v, i) {
                           const partes = per[i].nombre.split(" · ");
                           // En pantallas angostas solo el número; los nombres van en la lista debajo
                           return this.chart.width < 520 ? `${i + 1}` : partes; } } }, y: { title: { display: true, text: "Pozos" } },
                         y1: { position: "right", min: 0, max: 1, grid: { drawOnChartArea: false }, ticks: { callback: v => `${Math.round(v * 100)} %` },
                               title: { display: true, text: "Retención mes 12" } } },
               plugins: { tooltip: { callbacks: { title: x => per[x[0].dataIndex].nombre,
                                                  label: x => x.dataset.yAxisID === "y1" ? `Retención: ${pct(x.raw)}` : `Pozos: ${fmt(x.raw, 0)}` } } } } });
  $("#m7 .leyenda-grupos").innerHTML = per.map(p => `<li>${escapar(p.nombre)}</li>`).join("");
  const mayor = [...per].sort((a, b) => b.pozos - a.pozos)[0];
  lectura("m7", `El grupo más común es "${escapar(mayor.nombre)}" (${fmt(mayor.pozos, 0)} pozos), que conserva ${pct(mayor.retencion_mes12)} de su pico al mes 12.`);

  // 8 · Comparación con la versión 1
  const v2 = pe.alcance_proyecto_anterior.modelo.r2;
  $("#m8 .comparacion").innerHTML = [
    [num(R2_VERSION_1, 3), "Versión 1 · petróleo, 1 mes adelante"],
    [num(v2, 3), "Versión 2 · mismo alcance"],
    [num(pe.modelo.r2, 3), "Versión 2 · promedio de 1 a 12 meses"],
  ].map(([v, l]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  lectura("m8", `Con el mismo alcance que la versión 1, el R² es prácticamente igual (${num(v2, 3)} contra ${num(R2_VERSION_1, 3)}), y ahora además se pronostica gas y hasta 12 meses.`);

  const f = m.modelos.petroleo_existente.filas;
  $("#m-pie").textContent = `Entrenamiento: ${m.cortes.train}. Validación: ${m.cortes.valid}. Test: ${m.cortes.test}. ` +
    `Filas del modelo de petróleo existente: ${fmt(f.train, 0)} de entrenamiento, ${fmt(f.valid, 0)} de validación y ${fmt(f.test, 0)} de test. Modelos del ${m.version}.`;
}

iniciar();
