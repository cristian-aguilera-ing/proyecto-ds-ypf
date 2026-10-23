// Frontend del pronóstico: consume la API FastAPI (detrás de nginx en /api).
const API = location.protocol === "file:" || location.port === "5500" ? "http://localhost:8000" : "/api";
const COLORES = { petroleo: getComputedStyle(document.documentElement).getPropertyValue("--petroleo").trim(),
                  gas: getComputedStyle(document.documentElement).getPropertyValue("--gas").trim() };
const graficos = {};
let opciones = null;

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
document.querySelectorAll(".tab").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("activa", x === b));
  $("#panel-existente").classList.toggle("oculto", b.dataset.tab !== "existente");
  $("#panel-nuevo").classList.toggle("oculto", b.dataset.tab !== "nuevo");
}));

// ---------------------------------------------------------------- inicio
async function iniciar() {
  try {
    const h = await pedir("/health");
    $("#estado-api").textContent = `modelos ${h.version_modelos} · datos hasta ${h.datos_hasta}`;
    opciones = await pedir("/opciones");
    cargarOpciones();
  } catch (e) {
    $("#estado-api").textContent = "API no disponible";
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
  try { render(await llamada()); }
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
    art.querySelector("canvas").classList.add("oculto");
    return;
  }
  art.querySelector("canvas").classList.remove("oculto");
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
    options: { responsive: true, interaction: { mode: "index", intersect: false }, animation: false,
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
  $("#avisos").innerHTML = (avisos || []).map(a => `<div class="aviso">⚠ ${a}</div>`).join("");
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

iniciar();
