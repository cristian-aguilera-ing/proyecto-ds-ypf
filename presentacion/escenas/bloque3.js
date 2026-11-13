// Bloque 3: tipos de pozo, explicación de cada predicción y paso a producto.
import { CodigoVivo, enlazarPasos } from "../lib/codigo-vivo.js";
import { barras, Lineas } from "../lib/graficos.js";
import { alEntrar, es, COLOR } from "../lib/util.js";

export function iniciar(d) { clusters(d); shap(d); producto(); }

function clusters({ metricas: { clustering: c }, nb: { clustering: t } }) {
  const sec = document.querySelector("#escena-clusters");
  const K = t.kmeans.map(f => f[0]), sil = t.kmeans.map(f => f[1]);
  const l = new Lineas(sec.querySelector("svg"), { xs: K, ancho: 840, alto: 400, yMin: .17, yMax: .25, formatoY: v => es(v, 2), series: [{ datos: sil, color: COLOR.acento() }] });
  const punto = l.s.append("circle").attr("r", 13).attr("fill", COLOR.acento());
  const grupos = sec.querySelector(".grupos"), nota = sec.querySelector("#c-nota");
  grupos.innerHTML = c.perfiles.map(p => `<div class="kpi"><div class="v" style="color:${p.fluido === "Gas" ? "var(--gas)" : "var(--petroleo)"}">${es(p.pozos)}</div>
    <div class="l">${p.nombre}<br>conserva ${es(p.retencion_mes12 * 100)} % al mes 12</div></div>`).join("");
  const NOTAS = { 2: "k = 2 tiene la silhouette más alta, pero dos grupos no alcanzan para describir tipos de pozo.",
                  [c.k]: `k = ${c.k}: la mejor silhouette entre 3 y 10 grupos y el mejor Davies-Bouldin hasta k = 5. Igual es débil: ${es(t.silhouette_negativa, 1)} % de los pozos queda con silhouette negativa.` };
  const pintar = e => {
    const f = t.kmeans[K.indexOf(e.k)];
    gsap.to(punto.node(), { attr: { cx: l.x(e.k), cy: l.y(f[1]) }, duration: .8, ease: "power3.inOut" });
    sec.querySelector("#c-sil").textContent = es(f[1], 3); sec.querySelector("#c-db").textContent = es(f[2], 3);
    sec.querySelector("#c-ch").textContent = es(f[3]);
    nota.textContent = NOTAS[e.k] ?? `k = ${e.k}: más grupos no mejoran la separación.`;
    gsap.to(grupos, { opacity: e.k === c.k ? 1 : .15, duration: .5 });
  };
  const inicial = { k: 2 };
  punto.attr("cx", l.x(2)).attr("cy", l.y(sil[0]));
  const vivo = new CodigoVivo(sec.querySelector(".codigo"), { k: { lista: K, actual: 2 } }, pintar);
  pintar(inicial);
  enlazarPasos(sec, [{ k: 7 }, { k: c.k }], inicial, vivo);
}

function shap({ shap: s }) {
  const sec = document.querySelector("#escena-shap");
  const entrar = barras(sec.querySelector(".barras"), s.variables.map(v => ({
    nombre: v.descripcion, valor: v.impacto, texto: `${v.impacto > 0 ? "+" : "−"}${es(Math.abs(v.impacto), 3)}`,
    color: v.impacto > 0 ? "var(--petroleo)" : "var(--gas)" })));
  sec.querySelector(".lectura").textContent = `Pronóstico del pozo ${s.sigla}: qué empujó el resultado hacia arriba y qué hacia abajo.`;
  alEntrar(sec, entrar);
}

function producto() {
  const sec = document.querySelector("#escena-producto");
  const barra = sec.querySelector(".medidor i"), v = sec.querySelector(".dato .v");
  const RAM = { 2: 921, 1: 336 };
  const pintar = e => {
    gsap.to(barra, { width: `${RAM[e.workers] / 1024 * 100}%`, duration: 1, ease: "power3.inOut" });
    v.textContent = `${RAM[e.workers]} MB`;
  };
  const inicial = { workers: 2 };
  const vivo = new CodigoVivo(sec.querySelector(".codigo"), { workers: { lista: [2, 1], actual: 2 } }, pintar);
  pintar(inicial);
  enlazarPasos(sec, [{ workers: 1 }], inicial, vivo);
}
