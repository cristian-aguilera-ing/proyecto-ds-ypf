// Lado de la presentación del control remoto: publica la diapositiva actual y sus notas, y obedece
// las órdenes de las páginas de control. Solo se activa con ?control=CLAVE en la URL, así que sin
// ese parámetro (o sin el servicio) la presentación funciona igual, offline.
// Usa long polling (no SSE): los túneles rápidos de Cloudflare no entregan eventos SSE.

export function conectarControl(clave, Reveal) {
  const base = "control-api";
  const cabeceras = { "Content-Type": "application/json", "X-Clave": clave };
  const id = (crypto.randomUUID?.() ?? String(Math.random()).slice(2)) + "-presentador";

  // La nota está oculta, así que innerText devuelve textContent sin los <br> del guion: se cambian por saltos de línea
  const textoNota = aside => {
    if (!aside) return "";
    const copia = aside.cloneNode(true);
    copia.querySelectorAll("br").forEach(br => br.replaceWith("\n"));
    return copia.textContent.trim();
  };

  // Pasos: fragmentos de la escena (sin contar los de las subdiapositivas). "Sola": avanza con data-avance
  const diapositivas = () => Reveal.getHorizontalSlides().map(s => {
    const sec = s.querySelector(":scope > section") ?? s;
    return {
      titulo: (sec.querySelector("h1, h2")?.textContent ?? sec.id).replace(/\s+/g, " ").trim(),
      notas: textoNota(sec.querySelector("aside.notes")),
      pasos: sec.querySelectorAll(".fragment").length,
      sola: Boolean(sec.dataset.avance),
    };
  });

  const posicion = () => { const { h, f } = Reveal.getIndices(); return { indice: h, fragmento: f ?? -1 }; };

  const publicar = () => {
    fetch(`${base}/estado`, { method: "POST", headers: cabeceras,
      body: JSON.stringify({ id, ...posicion(), diapositivas: diapositivas() }) }).catch(() => {});
  };

  // "Siguiente" y "anterior" son relativas: solo se cumplen si el control las mandó viendo la misma posición
  // que tiene la presentación. Así un doble toque, dos controles a la vez o una orden atrasada por el túnel
  // no avanzan dos veces: la segunda llega con una posición vieja y se descarta.
  const alDia = o => {
    if (!o.base) return true;  // control viejo sin posición: se obedece como antes
    const p = posicion();
    return o.base.indice === p.indice && o.base.fragmento === p.fragmento;
  };
  const ordenes = {
    siguiente: o => alDia(o) && (Reveal.next(), true),
    anterior: o => alDia(o) && (Reveal.prev(), true),
    ir: o => Number.isInteger(o.indice) && (Reveal.slide(o.indice), true),
  };

  async function escuchar() {
    let desde = -1, instancia = null;
    for (;;) {
      try {
        const r = await fetch(`${base}/ordenes?id=${id}&desde=${desde}`, { headers: cabeceras });
        if (r.status === 401) return console.warn("Control remoto: clave incorrecta");
        const d = await r.json();
        const nueva = d.instancia !== instancia;  // primera conexión o relé reiniciado
        instancia = d.instancia;
        desde = d.ultimo;
        let descartada = false;
        for (const o of d.ordenes) if (!ordenes[o.accion]?.(o)) descartada = true;
        // Se republica al conectarse, si se descartó una orden (el control estaba atrasado) y, como latido,
        // en cada vuelta sin órdenes (~20 s): si el relé ignoró un estado, el control se corrige solo
        if (nueva || descartada || !d.ordenes.length) publicar();
      } catch { await new Promise(r => setTimeout(r, 2000)); }
    }
  }

  for (const ev of ["slidechanged", "fragmentshown", "fragmenthidden"]) Reveal.on(ev, publicar);
  escuchar();
}
