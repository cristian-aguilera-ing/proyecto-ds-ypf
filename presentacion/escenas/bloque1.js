// Bloque 1: el problema, el dataset, lo que encontramos y la limpieza.
import { CodigoVivo, enlazarPasos } from "../lib/codigo-vivo.js";
import { barras, Histograma, Lineas, contarHasta } from "../lib/graficos.js";
import { alEntrar, es, COLOR } from "../lib/util.js";

export function iniciar(d) {
  problema(d); dataset(d); hallazgos(d); gor(d); limpieza(d); variables(d);
}

function problema({ gancho: g }) {
  const sec = document.querySelector("#escena-problema");
  const xs = g.petroleo.map((_, i) => i + 1);
  const l = new Lineas(sec.querySelector("svg"), { xs, series: [{ datos: g.petroleo, color: COLOR.petroleo() }], alto: 640, ticksX: [1, 24, 48, 72],
                                                   etiquetaX: v => `Mes ${v}`, formatoY: v => es(v) });
  sec.querySelector(".lectura").textContent = `Un pozo real: ${g.sigla}, ${g.empresa}, en ${g.area}. Petróleo en m³ por mes.`;
  sec.querySelector(".dato .v").textContent = `−${es(g.caida_12m * 100, 1)} %`;
  alEntrar(sec, () => l.dibujar(0, 2.6));
}

function dataset({ crudo, anual }) {
  const sec = document.querySelector("#escena-dataset");
  const nombres = { NEUQUINA: "Neuquina", AUSTRAL: "Austral", "GOLFO SAN JORGE": "Golfo San Jorge", NOROESTE: "Noroeste" };
  const entrarBarras = barras(sec.querySelector(".barras"), crudo.cuencas.map(c => ({
    nombre: nombres[c.cuenca], valor: c.filas, texto: es(c.filas), destacada: c.cuenca === "NEUQUINA",
    color: c.cuenca === "NEUQUINA" ? "var(--acento)" : "var(--suave)" })));
  const l = new Lineas(sec.querySelector("svg"), { xs: anual.anio, series: [{ datos: anual.pet_millon_m3, color: COLOR.petroleo() }],
                                                   ancho: 840, alto: 620, ticksX: [2006, 2014, 2025], formatoY: v => es(v) });
  sec.querySelector(".lectura").textContent = `${es(crudo.filas)} filas y ${crudo.columnas} columnas: un registro por pozo y por mes, de 2006 a 2026.`;
  alEntrar(sec, () => { entrarBarras(); l.dibujar(0, 2.2); });
}

function hallazgos({ crudo }) {
  const sec = document.querySelector("#escena-hallazgos");
  const h = new Histograma(sec.querySelector("svg"), crudo.profundidad, {
    ancho: 900, alto: 660, marcas: [[10, "10 m"], [1000, "1.000 m"], [8000, "8.000"], [378939, "378.939 m"]],
    colorear: b => b >= 3.92 || b < 2.45 ? "var(--gas)" : "var(--acento)" });
  alEntrar(sec, () => h.entrar());
}

function gor({ gor: g }) {
  const sec = document.querySelector("#escena-gor");
  const izq = sec.querySelector(".lado-pet .v"), der = sec.querySelector(".lado-gas .v");
  let corte = 300;
  const h = new Histograma(sec.querySelector("svg"), g, {
    alto: 430, marcas: [[10, "10"], [100, "100"], [1000, "1.000"], [10000, "10.000"], [100000, "100.000 m³/m³"]],
    colorear: b => b < Math.log10(corte) ? COLOR.petroleo() : COLOR.gas() });
  const dibujar = e => {
    corte = e.GOR_CORTE_GAS; h.pintar();
    contarHasta(izq, g.petroleo[corte]); contarHasta(der, g.total - g.petroleo[corte]);
  };
  const inicial = { GOR_CORTE_GAS: 300 };
  const vivo = new CodigoVivo(sec.querySelector(".codigo"), { GOR_CORTE_GAS: { lista: g.cortes, actual: 300, formato: v => es(v).replace(".", "_") } }, dibujar);
  dibujar(inicial);
  enlazarPasos(sec, [{ GOR_CORTE_GAS: 30000 }, { GOR_CORTE_GAS: 3000 }], inicial, vivo);
  alEntrar(sec, () => h.entrar());
}

function limpieza({ crudo, panel }) {
  const sec = document.querySelector("#escena-limpieza");
  const neu = crudo.cuencas.find(c => c.cuenca === "NEUQUINA");
  const entrar = barras(sec.querySelector(".barras"), [
    { nombre: "CSV original", valor: crudo.filas, texto: `${es(crudo.filas)} filas`, color: "var(--suave)" },
    { nombre: "Solo Neuquina", valor: neu.filas, texto: `${es(neu.filas)} filas · ${es(neu.pozos)} pozos`, color: "var(--suave)" },
    { nombre: "Dataset limpio", valor: panel.filas, texto: `${es(panel.filas)} filas · ${es(panel.pozos)} pozos`, destacada: true },
  ]);
  alEntrar(sec, entrar);
}

// Grupos de columnas de src/ypf_ds/features/build.py: 53 en el modo A y 10 en el modo B
const GRUPOS = [["Historia de producción", 24, 0], ["Ciclo de vida del pozo", 9, 0], ["Estado operativo", 6, 0],
                ["Atributos del pozo", 7, 5], ["Ubicación y profundidad", 4, 4], ["Mes de vida y calendario", 3, 1]];

function variables({ nb }) {
  const sec = document.querySelector("#escena-variables"), cont = sec.querySelector(".barras");
  const entrar = barras(cont, GRUPOS.map(([n, a]) => ({ nombre: n, valor: a, texto: String(a) })), { max: 24 });
  const c4 = nb.limpieza.cap4_cobertura.dias_perf;
  const lectura = { A: "Modo A: todo lo que el pozo produjo hasta el mes t. Rezagos de 1 a 12 meses, medias móviles, pico y acumulada.",
                    B: `Modo B: solo lo que se sabe antes de perforar, 10 variables. El padrón Capítulo IV cubría el ${es(c4 * 100)} % de los pozos, pero no mejoró la validación.` };
  const pintar = e => {
    const i = e.modo === "A" ? 1 : 2;
    cont.querySelectorAll(".barra").forEach((b, j) => {
      gsap.to(b.querySelector("i"), { width: `${Math.max(GRUPOS[j][i] / 24 * 100, .4)}%`, duration: .9, ease: "power3.inOut" });
      b.querySelector(".b-texto").textContent = GRUPOS[j][i];
    });
    sec.querySelector(".lectura").textContent = lectura[e.modo];
  };
  const inicial = { modo: "A" };
  const vivo = new CodigoVivo(sec.querySelector(".codigo"), { modo: { lista: ["A", "B"], actual: "A", formato: v => `"${v}"` } }, pintar);
  sec.querySelector(".lectura").textContent = lectura.A;
  cont.classList.add("anchas");
  alEntrar(sec, () => vivo.estado.modo === "A" && entrar());
  enlazarPasos(sec, [{ modo: "B" }], inicial, vivo);
}
