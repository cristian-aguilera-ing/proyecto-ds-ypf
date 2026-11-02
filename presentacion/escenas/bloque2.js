// Bloque 2: por qué dos modos, cómo se validó, qué modelo y qué problemas aparecieron.
import { CodigoVivo, enlazarPasos } from "../lib/codigo-vivo.js";
import { barras, Lineas, CurvaBanda } from "../lib/graficos.js";
import { alEntrar, es, COLOR } from "../lib/util.js";

// Métricas del notebook 03 (datos/notebooks.json): se miden sobre una muestra y no están en metadata.json
const METRICAS = { r2: ["R²", 3, "max"], mae: ["MAE", 1, "min"], rmse: ["RMSE", 1, "min"], wape: ["WAPE", 3, "min"], seg: ["Tiempo (s)", 1, "min"] };

export function iniciar(d) {
  dosModos(d); algoritmos(d); target(d); horizonte(d); arps(d); incertidumbre(d);
}

function dosModos({ gancho: g, pozo_nuevo: n }) {
  const sec = document.querySelector("#escena-modos");
  const corte = 40, xs = g.petroleo.slice(0, corte + 12).map((_, i) => i + 1);
  const a = new Lineas(sec.querySelector("#modo-a"), { xs, ancho: 840, alto: 500, ticksX: [1, 20, 40], etiquetaX: v => `Mes ${v}`, formatoY: v => es(v), series: [
    { datos: xs.map((_, i) => i <= corte ? g.petroleo[i] : null), color: COLOR.petroleo() },
    { datos: xs.map((_, i) => i >= corte ? g.petroleo[i] : null), color: COLOR.petroleo(), punteada: true }] });
  const c = n.curvas["6000_2024"];
  const b = new CurvaBanda(sec.querySelector("#modo-b"), { ancho: 840, alto: 500, yMax: Math.max(...c.p90) });
  b.pintar(c);
  alEntrar(sec, () => a.dibujar(0, 1.6));
}

function algoritmos({ nb: { algoritmos: t } }) {
  const sec = document.querySelector("#escena-algoritmos"), cont = sec.querySelector(".barras"), sel = sec.querySelector(".selector");
  const filas = t.filas.map(f => Object.fromEntries([["nombre", f[0]], ...t.columnas.map((c, i) => [c, f[i + 1]])]));
  let actual = "r2";
  // Ordena con el mejor arriba y anima el cambio de posición (FLIP) y de largo de cada barra
  const pintar = (m, animar = true) => {
    const [, dec, mejor] = METRICAS[m], max = Math.max(...filas.map(f => f[m]));
    const orden = [...filas].sort((x, y) => mejor === "max" ? y[m] - x[m] : x[m] - y[m]);
    const antes = new Map([...cont.children].map(el => [el.dataset.nombre, el.getBoundingClientRect().top]));
    const entrar = barras(cont, orden.map(f => ({ nombre: f.nombre, valor: f[m], texto: es(f[m], dec), destacada: f.nombre === "LightGBM",
      color: f.nombre === "LightGBM" ? "var(--acento)" : f.nombre === "Persistencia" ? "var(--gas)" : "var(--suave)" })), { max });
    [...cont.children].forEach((el, i) => { el.dataset.nombre = orden[i].nombre; });
    if (!animar || !antes.size) return entrar;
    const escala = cont.getBoundingClientRect().height / cont.offsetHeight || 1;
    [...cont.children].forEach(el => {
      const d = (antes.get(el.dataset.nombre) - el.getBoundingClientRect().top) / escala;
      gsap.from(el, { y: d, duration: .8, ease: "power3.inOut" });
    });
    cont.querySelectorAll("i").forEach(i => gsap.fromTo(i, { width: "0%" }, { width: `${i.dataset.ancho}%`, duration: .9, ease: "power3.out" }));
  };
  const elegir = m => { actual = m; sel.querySelectorAll("button").forEach(b => b.classList.toggle("activo", b.dataset.m === m)); pintar(m); };
  sel.innerHTML = Object.entries(METRICAS).map(([k, [n]]) => `<button data-m="${k}" class="${k === "r2" ? "activo" : ""}">${n}</button>`).join("");
  sel.addEventListener("click", e => { const b = e.target.closest("button"); if (b) elegir(b.dataset.m); });
  const entrar = pintar("r2", false);
  alEntrar(sec, () => { if (actual === "r2") entrar(); });
  Reveal.on("fragmentshown", e => { if (sec.contains(e.fragment)) elegir("seg"); });
  Reveal.on("fragmenthidden", e => { if (sec.contains(e.fragment)) elegir("r2"); });
}

function target({ nb }) {
  const sec = document.querySelector("#escena-target");
  const barra = sec.querySelector(".medidor i"), val = sec.querySelector(".dato .v"), r2 = sec.querySelector("#t-r2"), wape = sec.querySelector("#t-wape");
  const pintar = e => {
    const t = nb.target[e.target];
    gsap.to(barra, { width: `${t.sesgo * 100 / 1.2}%`, duration: 1, ease: "power3.inOut" });
    val.textContent = es(t.sesgo, 3); r2.textContent = es(t.r2, 3); wape.textContent = es(t.wape, 3);
  };
  const inicial = { target: "log1p" };
  const vivo = new CodigoVivo(sec.querySelector(".codigo"), { target: { lista: ["log1p", "ratio_ponderado"], actual: "log1p", formato: v => `"${v}"` } }, pintar);
  pintar(inicial);
  enlazarPasos(sec, [{ target: "ratio_ponderado" }], inicial, vivo);
}

function horizonte({ metricas: m }) {
  const sec = document.querySelector("#escena-horizonte");
  const l = new Lineas(sec.querySelector("svg"), { xs: m.horizontes, yMin: -1, yMax: 1, alto: 460, formatoY: v => es(v, 1), etiquetaX: v => `${v}`, series: [
    { datos: m.r2.petroleo, color: COLOR.petroleo() }, { datos: m.r2.petroleo_pers, color: COLOR.suave(), punteada: true, grosor: 4 }] });
  const mod = sec.querySelector("#h-modelo"), per = sec.querySelector("#h-pers");
  const pintar = e => {
    const i = e.horizonte - 1; l.hasta(i);
    mod.textContent = es(m.r2.petroleo[i], 2); per.textContent = es(m.r2.petroleo_pers[i], 2);
  };
  const inicial = { horizonte: 1 };
  const vivo = new CodigoVivo(sec.querySelector(".codigo"), { horizonte: { lista: m.horizontes, actual: 1 } }, pintar);
  pintar(inicial);
  enlazarPasos(sec, [{ horizonte: 3 }, { horizonte: 6 }, { horizonte: 12 }], inicial, vivo);
}

function arps({ gancho: g, metricas: m }) {
  const sec = document.querySelector("#escena-arps");
  const real = g.petroleo.slice(g.pico_mes), xs = real.map((_, i) => i);
  const curva = (b, di) => xs.map(t => g.arps.qi / Math.pow(1 + b * di * t, 1 / b));
  const inicial = { b: .5, Di: .05 };
  const l = new Lineas(sec.querySelector("svg"), { xs, alto: 430, ticksX: [0, 20, 40, 60, 80], etiquetaX: v => `Mes ${v}`, formatoY: v => es(v), series: [
    { datos: real, color: COLOR.suave(), grosor: 3 }, { datos: curva(inicial.b, inicial.Di), color: COLOR.gas() }] });
  const vivo = new CodigoVivo(sec.querySelector(".codigo"), {
    b: { lista: [.5, 1, g.arps.b], actual: .5 }, Di: { lista: [.05, .1, g.arps.di], actual: .05 } }, e => l.mover(1, curva(e.b, e.Di)));
  enlazarPasos(sec, [{ b: 1, Di: .05 }, { b: g.arps.b, Di: g.arps.di }], inicial, vivo);
  const bt = m.backtest.petroleo;
  sec.querySelector("#a-modelo").textContent = es(bt.modelo.wape * 100, 1) + " %";
  sec.querySelector("#a-arps").textContent = es(bt.arps.wape * 100, 1) + " %";
}

function incertidumbre({ nb: { cobertura: c } }) {
  const sec = document.querySelector("#escena-incertidumbre"), cont = sec.querySelector(".coberturas");
  cont.innerHTML = c.modelos.map(([n, v]) => `<div class="cobertura"><span>${n}</span>
    <div class="medidor"><i style="background:${v >= c.esperada - .02 ? "var(--petroleo)" : "var(--gas)"}" data-v="${v}"></i>
      <div class="ideal" style="left:${c.esperada * 100}%">${n === c.modelos[0][0] ? "<span>80 % esperado</span>" : ""}</div></div>
    <b>${es(v * 100, 1)} %</b></div>`).join("");
  alEntrar(sec, () => gsap.fromTo(cont.querySelectorAll(".medidor i"), { width: "0%" },
    { width: (_, el) => `${el.dataset.v * 100}%`, duration: 1.1, ease: "power3.out", stagger: .15 }));
}
