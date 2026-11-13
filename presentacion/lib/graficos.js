// Curva con banda P10–P90 sobre SVG que se transforma interpolando los valores (no redibuja de golpe).
export class CurvaBanda {
  constructor(svg, { ancho = 1740, alto = 600, yMax, etiquetaMes = "Mes" }) {
    const m = { izq: 100, der: 20, sup: 30, inf: 64 };
    this.x = d3.scaleLinear().domain([1, 24]).range([m.izq, ancho - m.der]);
    this.y = d3.scaleLinear().domain([0, yMax]).nice().range([alto - m.inf, m.sup]);
    const s = this.s = d3.select(svg).attr("viewBox", `0 0 ${ancho} ${alto}`).attr("class", "grafico");
    const fmt = d3.format(",d");
    const rej = s.append("g").attr("class", "rejilla");
    this.y.ticks(5).forEach(t => {
      rej.append("line").attr("x1", m.izq).attr("x2", ancho - m.der).attr("y1", this.y(t)).attr("y2", this.y(t));
      s.append("text").attr("x", m.izq - 14).attr("y", this.y(t) + 8).attr("text-anchor", "end").text(fmt(t).replaceAll(",", "."));
    });
    [1, 6, 12, 18, 24].forEach(t => s.append("text").attr("x", this.x(t)).attr("y", alto - 26)
      .attr("text-anchor", t === 24 ? "end" : t === 1 ? "start" : "middle").text(`${etiquetaMes} ${t}`));
    this.banda = s.append("path").attr("class", "banda");
    this.fantasma = s.append("path").attr("class", "fantasma");
    this.p50 = s.append("path").attr("class", "p50");
    this.area = d3.area().x((_, i) => this.x(i + 1)).y0(d => this.y(d[0])).y1(d => this.y(d[1])).curve(d3.curveMonotoneX);
    this.linea = d3.line().x((_, i) => this.x(i + 1)).y(d => this.y(d)).curve(d3.curveMonotoneX);
  }
  pintar(c) {
    this.banda.attr("d", this.area(c.p10.map((v, i) => [v, c.p90[i]])));
    this.p50.attr("d", this.linea(c.p50));
  }
  // Pasa de la curva actual a la nueva; la anterior queda punteada para comparar
  mover(nueva, { duracion = 1 } = {}) {
    const ini = this.actual ?? nueva, t = { v: 0 };
    if (this.actual) this.fantasma.attr("d", this.linea(ini.p50));
    this.tween?.kill();
    this.tween = gsap.to(t, { v: 1, duration: duracion, ease: "power3.inOut", onUpdate: () => {
      this.pintar(Object.fromEntries(["p10", "p50", "p90"].map(k => [k, ini[k].map((a, i) => a + (nueva[k][i] - a) * t.v)])));
    } });
    this.actual = nueva;
  }
}

export function contarHasta(el, valor, formato = v => Math.round(v).toLocaleString("es-AR")) {
  const inicio = Number(el.dataset.valorActual ?? valor), t = { v: inicio };
  el.dataset.valorActual = valor;
  gsap.to(t, { v: valor, duration: 1, ease: "power3.inOut", onUpdate: () => { el.textContent = formato(t.v); } });
}

// Barras horizontales en HTML: crecen al entrar a la escena
export function barras(contenedor, filas, { max = Math.max(...filas.map(f => Math.abs(f.valor))) } = {}) {
  contenedor.innerHTML = filas.map(f => `<div class="barra ${f.destacada ? "destacada" : ""}">
    <span class="b-nombre">${f.nombre}</span>
    <span class="b-pista"><i style="background:${f.color ?? "var(--acento)"}" data-ancho="${Math.max(Math.abs(f.valor) / max * 100, .4)}"></i></span>
    <span class="b-texto">${f.texto}</span></div>`).join("");
  return () => gsap.fromTo(contenedor.querySelectorAll("i"), { width: "0%" },
    { width: (_, el) => `${el.dataset.ancho}%`, duration: 1.1, ease: "power3.out", stagger: .09 });
}

// Histograma sobre SVG con eje logarítmico; colorear(bordeInferior) decide el color de cada barra
export class Histograma {
  constructor(svg, { cuentas, bordes }, { ancho = 1740, alto = 470, marcas, colorear }) {
    const m = { izq: 30, der: 30, sup: 20, inf: 60 };
    this.x = d3.scaleLinear().domain([bordes[0], bordes.at(-1)]).range([m.izq, ancho - m.der]);
    const y = d3.scaleSqrt().domain([0, Math.max(...cuentas)]).range([alto - m.inf, m.sup]);
    const s = this.s = d3.select(svg).attr("viewBox", `0 0 ${ancho} ${alto}`).attr("class", "grafico");
    this.colorear = colorear; this.alto = alto; this.m = m;
    this.rects = s.selectAll("rect").data(cuentas).join("rect")
      .attr("x", (_, i) => this.x(bordes[i]) + 2).attr("width", (_, i) => this.x(bordes[i + 1]) - this.x(bordes[i]) - 4)
      .attr("y", d => d ? y(d) : alto - m.inf).attr("height", d => d ? alto - m.inf - y(d) : 0).attr("rx", 3)
      .attr("data-b", (_, i) => bordes[i]);
    marcas.forEach(([v, t]) => s.append("text").attr("x", this.x(Math.log10(v))).attr("y", alto - 18).attr("text-anchor", "middle").text(t));
    this.pintar();
  }
  pintar() { this.rects.attr("fill", (_, i, n) => this.colorear(Number(n[i].dataset.b))); }
  entrar() { gsap.from(this.rects.nodes(), { scaleY: 0, transformOrigin: "50% 100%", svgOrigin: undefined, duration: .7, ease: "power3.out", stagger: .012 }); }
}

// Líneas sobre SVG: cada serie puede dibujarse hasta un punto o cambiar sus valores
export class Lineas {
  constructor(svg, { xs, series, ancho = 1740, alto = 500, yMin = 0, yMax, formatoY = d3.format("~s"), etiquetaX = v => v, ticksX }) {
    const m = { izq: 110, der: 30, sup: 20, inf: 56 };
    Object.assign(this, { xs, series, alto });
    this.x = d3.scaleLinear().domain([xs[0], xs.at(-1)]).range([m.izq, ancho - m.der]);
    this.y = d3.scaleLinear().domain([yMin, yMax ?? d3.max(series.flatMap(s => s.datos))]).nice().range([alto - m.inf, m.sup]);
    const s = d3.select(svg).attr("viewBox", `0 0 ${ancho} ${alto}`).attr("class", "grafico");
    const rej = s.append("g").attr("class", "rejilla");
    this.y.ticks(5).forEach(t => {
      rej.append("line").attr("x1", m.izq).attr("x2", ancho - m.der).attr("y1", this.y(t)).attr("y2", this.y(t));
      s.append("text").attr("x", m.izq - 14).attr("y", this.y(t) + 8).attr("text-anchor", "end").text(formatoY(t));
    });
    (ticksX ?? xs).forEach(t => s.append("text").attr("x", this.x(t)).attr("y", alto - 16).attr("text-anchor", "middle").text(etiquetaX(t)));
    this.linea = d3.line().defined(d => d != null).x((_, i) => this.x(xs[i])).y(d => this.y(d)).curve(d3.curveMonotoneX);
    this.trazos = series.map(se => s.append("path").attr("fill", "none").attr("stroke", se.color).attr("stroke-width", se.grosor ?? 5)
      .attr("stroke-linecap", "round").attr("stroke-dasharray", se.punteada ? "10 10" : null).attr("d", this.linea(se.datos)));
    this.s = s;
  }
  // Dibuja la serie de izquierda a derecha, como si se trazara en el momento
  dibujar(i = 0, duracion = 2) {
    const n = this.trazos[i].node(), l = n.getTotalLength();
    gsap.fromTo(n, { strokeDasharray: l, strokeDashoffset: l }, { strokeDashoffset: 0, duration: duracion, ease: "power1.inOut" });
  }
  hasta(indice) { // Muestra cada serie solo hasta `indice`
    this.trazos.forEach((t, i) => t.attr("d", this.linea(this.series[i].datos.map((v, j) => j <= indice ? v : null))));
  }
  mover(i, nuevos, duracion = .9) {
    const ini = this.series[i].datos, t = { v: 0 };
    gsap.to(t, { v: 1, duration: duracion, ease: "power3.inOut", onUpdate: () => {
      this.trazos[i].attr("d", this.linea(ini.map((a, j) => a + (nuevos[j] - a) * t.v)));
    }, onComplete: () => { this.series[i].datos = nuevos; } });
  }
}
