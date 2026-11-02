// Código vivo: valores de código enlazados a un gráfico. Se cambian con un paso de la presentación
// (el valor se tipea solo) o arrastrando el número a izquierda o derecha.
const ESPERA_TECLA = 0.045;

export class CodigoVivo {
  // valores: { nombre: { lista: [...], actual, formato? } } · alCambiar(estado): redibuja el gráfico
  constructor(raiz, valores, alCambiar) {
    Object.assign(this, { raiz, valores, alCambiar, lineas: {} });
    this.estado = Object.fromEntries(Object.entries(valores).map(([k, v]) => [k, v.actual]));
    for (const el of raiz.querySelectorAll(".valor")) {
      el.textContent = this.formato(el.dataset.valor, this.estado[el.dataset.valor]);
      this.habilitarArrastre(el);
    }
  }
  formato(nombre, v) { return this.valores[nombre].formato?.(v) ?? String(v); }
  elemento(nombre) { return this.raiz.querySelector(`.valor[data-valor="${nombre}"]`); }

  // Tipea el valor nuevo (borra y escribe) y recién ahí mueve el gráfico: causa y efecto
  fijar(nombre, valor, { tipear = true } = {}) {
    const el = this.elemento(nombre), viejo = el.textContent, nuevo = this.formato(nombre, valor);
    this.lineas[nombre]?.kill();
    this.estado[nombre] = valor;
    if (!tipear) { el.textContent = nuevo; this.alCambiar({ ...this.estado }); return; }
    el.classList.add("tipeando", "activo");
    const tl = this.lineas[nombre] = gsap.timeline({ onComplete: () => {
      el.classList.remove("tipeando"); this.alCambiar({ ...this.estado });
      gsap.delayedCall(1.1, () => el.classList.remove("activo"));
    } });
    [...viejo].forEach((_, i) => tl.call(() => { el.textContent = viejo.slice(0, viejo.length - i - 1) || "​"; }, null, `+=${ESPERA_TECLA}`));
    [...nuevo].forEach((_, i) => tl.call(() => { el.textContent = nuevo.slice(0, i + 1); }, null, `+=${ESPERA_TECLA * 1.6}`));
  }

  habilitarArrastre(el) {
    const nombre = el.dataset.valor, { lista } = this.valores[nombre], PX_POR_PASO = 42;
    let inicio, indice;
    el.addEventListener("pointerdown", e => {
      inicio = e.clientX; indice = lista.indexOf(this.estado[nombre]);
      el.setPointerCapture(e.pointerId); el.classList.add("activo"); e.stopPropagation();
    });
    el.addEventListener("pointermove", e => {
      if (inicio == null) return;
      const i = Math.max(0, Math.min(lista.length - 1, indice + Math.round((e.clientX - inicio) / PX_POR_PASO)));
      if (lista[i] !== this.estado[nombre]) this.fijar(nombre, lista[i], { tipear: false });
    });
    el.addEventListener("pointerup", () => { inicio = null; el.classList.remove("activo"); });
  }
}

// Aplica los pasos de una escena con los fragmentos de Reveal: cada tecla avanza un paso, y al retroceder vuelve
export function enlazarPasos(seccion, pasos, inicial, vivo) {
  const aplicar = n => {
    const p = n < 0 ? inicial : pasos[n];
    Object.entries(p).forEach(([k, v]) => { if (vivo.estado[k] !== v) vivo.fijar(k, v); });
  };
  Reveal.on("fragmentshown", e => { if (seccion.contains(e.fragment)) aplicar(Number(e.fragment.dataset.paso)); });
  Reveal.on("fragmenthidden", e => { if (seccion.contains(e.fragment)) aplicar(Number(e.fragment.dataset.paso) - 1); });
}
