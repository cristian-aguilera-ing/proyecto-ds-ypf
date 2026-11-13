// Apéndice: panel de métricas de los notebooks para responder preguntas. Pestañas y vistas con clic.
import { barras } from "../lib/graficos.js";
import { es } from "../lib/util.js";

const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
const tabla = (cab, filas, destacar = () => false) => `<table class="tabla"><tr>${cab.map(c => `<th>${c}</th>`).join("")}</tr>
  ${filas.map(f => `<tr class="${destacar(f) ? "destacada" : ""}">${f.map(v => `<td>${v}</td>`).join("")}</tr>`).join("")}</table>`;
const pct = (v, d = 1) => `${es(v * 100, d)} %`;

// Cada pestaña es una lista de vistas [título, html, alMostrar?]; con una sola vista no hay subselector
function vistas(nb) {
  const { eda, limpieza: li, cv_temporal: cv, optuna: op, diagnostico: dg, categorias: ca, formaciones: fo, modo_b: mb, clustering: cl, shap: sh, cobertura: co } = nb;
  const reporte = f => tabla(["Categoría", "Precisión", "Recall", "F1"], ca[f].clases.map(c => [c[0], ...c.slice(1).map(v => es(v, 3))]));
  const formacion = orden => {
    const filas = [...fo.filas].sort((a, b) => orden === "wape" ? a[2] - b[2] : orden === "filas" ? b[1] - a[1] : b[3] - a[3]);
    return filas.map(f => ({ nombre: f[0], valor: orden === "filas" ? f[1] : orden === "wape" ? f[2] : f[3],
      texto: orden === "filas" ? es(f[1]) : es(orden === "wape" ? f[2] : f[3], 3), destacada: f[0] === "Vaca Muerta" }));
  };
  return {
    "01 EDA": [["", `<div class="cuadricula">
      ${kpi(`${es(eda.filas)} × ${eda.columnas}`, "filas × columnas del CSV crudo")}
      ${kpi(es(eda.neuquina_filas), `filas de Neuquina, ${es(eda.neuquina_pozos)} pozos`)}
      ${kpi(`${es(eda.profundidad_max)} m`, "profundidad máxima: error de carga")}
      ${kpi(es(eda.profundidad_ceros), "filas con profundidad 0")}
      ${kpi(es(eda.tef_mayor_dias), "filas con más días de producción que el mes")}
      ${kpi(es(eda.negativos_gas), "filas con gas negativo")}
      ${kpi(es(eda.coord_invertidas_filas), "filas con latitud y longitud invertidas")}
      ${kpi(es(eda.pozos_meses_faltantes), "pozos con meses sin registro")}</div>
      <p class="lectura">Outliers de profundidad por IQR: límites ${es(eda.iqr_limites[0])} a ${es(eda.iqr_limites[1])} m, ${es(eda.outliers_iqr)} filas (0,3 %).</p>`]],
    "02 Limpieza": [["", `<div class="cuadricula">
      ${kpi(es(li.filas), `filas del panel limpio, ${es(li.pozos)} pozos`)}
      ${kpi(es(li.meses_reconstruidos), "meses reconstruidos por la grilla")}
      ${kpi(es(li.censurados), "pozos censurados: ya producían en 2006")}
      ${kpi(es(li.horizontales), "pozos horizontales")}</div>
      <div class="columnas"><div><p class="subt">Padrón Capítulo IV: cobertura sobre los pozos</p><div class="barras" data-barras="c4"></div></div>
        <div><p class="subt">Correlación con la acumulada de 12 meses</p><div class="barras" data-barras="corr"></div>
        <p class="lectura" style="margin-top:20px">En naranja, las del Capítulo IV: correlacionan, pero no mejoraron la validación del modo B y no se usan.</p></div></div>`,
      raiz => {
        barras(raiz.querySelector('[data-barras="c4"]'), Object.entries(li.cap4_cobertura).map(([k, v]) => ({ nombre: k, valor: v, texto: pct(v) })), { max: 1 })();
        barras(raiz.querySelector('[data-barras="corr"]'), Object.entries(li.cap4_correlacion_acum12).map(([k, v]) => ({
          nombre: k, valor: v, texto: es(v, 3), color: k.startsWith("dias") || k === "cota" ? "var(--gas)" : "var(--acento)" })), { max: 1 })();
      }]],
    "03 Modelado": [
      ["CV temporal", `<p class="lectura">5 folds con ventana que crece: siempre se valida después de lo entrenado. R² ${es(cv.r2_medio, 3)} ± ${es(cv.r2_desvio, 3)}, WAPE ${es(cv.wape_medio, 3)} ± ${es(cv.wape_desvio, 3)}.</p>
        ${tabla(["Fold", "Valida desde", "Hasta", "Filas de train", "R²", "WAPE"], cv.folds.map((f, i) => [i + 1, f.desde, f.hasta, es(f.train), es(f.r2, 3), es(f.wape, 3)]))}`],
      ["Optuna vs Grid", `<div class="cuadricula" style="grid-template-columns:1fr 1fr">
        ${kpi(es(op.grid.rmse, 4), `GridSearch · RMSE de validación (log) · ${es(op.grid.seg)} s · ${op.grid.params}`)}
        ${kpi(es(op.optuna.rmse, 4), `Optuna (TPE) · RMSE de validación (log) · ${es(op.optuna.seg)} s · ${op.optuna.params}`)}</div>
        <p class="lectura">Optuna encontró un error apenas menor en menos tiempo, y explora rangos continuos en vez de una grilla fija.</p>`],
      ["Diagnóstico", `${tabla(["Test 2024–2025", "MAE", "RMSE", "R²", "WAPE"], dg.filas.map(f => [f[0], ...f.slice(1).map((v, i) => es(v, i < 2 ? 1 : 3))]), f => !f[0].includes("persistencia"))}
        <p class="lectura">Residuo medio ${es(dg.residuo_medio, 1)} m³ y mediana ${es(dg.residuo_mediana, 1)} m³: sin sesgo sistemático.</p>`],
      ["Por formación", `<div class="selector" data-orden><button data-o="r2" class="activo">R²</button><button data-o="wape">WAPE</button><button data-o="filas">Filas</button></div><div class="barras" data-barras="fo"></div>`,
        raiz => {
          const cont = raiz.querySelector('[data-barras="fo"]'), sel = raiz.querySelector("[data-orden]");
          const pintar = o => { const f = formacion(o); barras(cont, f, { max: Math.max(...f.map(x => x.valor)) })(); };
          sel.onclick = e => {
            const b = e.target.closest("button"); if (!b) return;
            sel.querySelectorAll("button").forEach(x => x.classList.toggle("activo", x === b)); pintar(b.dataset.o);
          };
          pintar(sel.querySelector(".activo").dataset.o);
        }],
      ["Categorías", `<p class="lectura">Producción en tres categorías por terciles: ¿el pronóstico cae en la categoría correcta?</p>
        <div class="columnas"><div><p class="subt">Petróleo · accuracy ${es(ca.petroleo.accuracy, 3)}</p>${reporte("petroleo")}</div>
        <div><p class="subt">Gas · accuracy ${es(ca.gas.accuracy, 3)}</p>${reporte("gas")}</div></div>`],
      ["Modo B", `${tabla(["Acumulada 12 meses", "MAE (m³)", "R²", "WAPE"], ["petroleo", "gas"].flatMap(f => [
          [`${f === "gas" ? "Gas" : "Petróleo"} · LightGBM`, es(mb[f].modelo.mae), es(mb[f].modelo.r2, 3), es(mb[f].modelo.wape, 3)],
          [`${f === "gas" ? "Gas" : "Petróleo"} · curva mediana`, es(mb[f].mediana.mae), es(mb[f].mediana.r2, 3), es(mb[f].mediana.wape, 3)]]), f => f[0].includes("LightGBM"))}
        <p class="lectura">${mb.pozos_test} pozos de test nunca vistos. El fluido dominante se acierta en el ${pct(mb.fluido_accuracy)} de los casos.</p>`],
      ["Cobertura", tabla(["Banda P10–P90", "Cobertura en test", "Esperada"], co.modelos.map(([n, v]) => [n, pct(v), pct(co.esperada, 0)]), f => !f[0].includes("nuevo"))]],
    "04 Clustering": [["", `<div class="cuadricula">${kpi(cl.svd_componentes, "componentes SVD")}${kpi(pct(cl.svd_varianza), "varianza explicada")}
        ${kpi("k = 4", "K-Means elegido")}${kpi(`${es(cl.silhouette_negativa, 1)} %`, "pozos con silhouette negativa")}</div>
      <div class="columnas"><div>${tabla(["k", "Silhouette", "Davies-Bouldin", "Calinski-H."], cl.kmeans.map(f => [f[0], es(f[1], 3), es(f[2], 3), es(f[3])]), f => f[0] === 4)}</div>
        <div><p class="subt">DBSCAN: con cualquier eps deja muchos pozos como ruido</p>
        ${tabla(["eps", "Clusters", "% ruido", "Silhouette"], cl.dbscan.map(f => [es(f[0], 1), f[1], `${es(f[2], 1)} %`, es(f[3], 3)]))}</div></div>`]],
    "05 SHAP": [["", `<p class="lectura">Ejemplo del notebook: pozo ${sh.idpozo}.</p>
      <div class="cuadricula">${kpi(`${es(sh.ultimo_mes)} m³`, "producción del último mes")}${kpi(es(sh.ratio, 3), "ratio predicho")}
        ${kpi(`${es(sh.predicho)} m³`, "pronóstico a 12 meses")}${kpi(`${es(sh.real_12m)} m³`, "valor real a 12 meses")}</div>
      <p class="lectura">El pronóstico es el último mes por el ratio. SHAP descompone ese ratio en el aporte de cada variable, como en la escena del pozo YPF.Nq.LLL-1577(h).</p>`]]
  };
}

export function iniciar({ nb }) {
  const pestanas = document.querySelector("#ap-pestanas"), paneles = document.querySelector("#ap-paneles");
  const todo = Object.values(vistas(nb)), nombres = Object.keys(vistas(nb));
  pestanas.innerHTML = nombres.map((n, i) => `<button data-p="${i}" class="${i ? "" : "activo"}">${n}</button>`).join("");
  paneles.innerHTML = todo.map((vs, i) => `<div class="panel ${i ? "" : "activo"}" data-p="${i}">
    ${vs.length > 1 ? `<div class="selector" data-sub>${vs.map((v, j) => `<button data-v="${j}" class="${j ? "" : "activo"}">${v[0]}</button>`).join("")}</div>` : ""}
    ${vs.map((v, j) => `<div class="vista" data-v="${j}" style="display:${j ? "none" : "flex"};flex-direction:column;gap:22px">${v[1]}</div>`).join("")}</div>`).join("");
  const vista = (p, v) => paneles.querySelector(`.panel[data-p="${p}"] .vista[data-v="${v}"]`);
  const alMostrar = (p, v) => todo[p][v][2]?.(vista(p, v));

  pestanas.onclick = e => {
    const b = e.target.closest("button"); if (!b) return;
    pestanas.querySelectorAll("button").forEach(x => x.classList.toggle("activo", x === b));
    paneles.querySelectorAll(".panel").forEach(x => x.classList.toggle("activo", x.dataset.p === b.dataset.p));
    const sub = paneles.querySelector(`.panel[data-p="${b.dataset.p}"] [data-sub] .activo`);
    alMostrar(Number(b.dataset.p), sub ? Number(sub.dataset.v) : 0);
  };
  paneles.onclick = e => {
    const b = e.target.closest("[data-sub] button"); if (!b) return;
    const panel = b.closest(".panel");
    b.parentElement.querySelectorAll("button").forEach(x => x.classList.toggle("activo", x === b));
    panel.querySelectorAll(".vista").forEach(x => { x.style.display = x.dataset.v === b.dataset.v ? "flex" : "none"; });
    alMostrar(Number(panel.dataset.p), Number(b.dataset.v));
  };
}
