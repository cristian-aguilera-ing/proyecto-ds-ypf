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

  const diapositivas = () => Reveal.getHorizontalSlides().map(s => ({
    titulo: (s.querySelector("h1, h2")?.textContent ?? s.id).replace(/\s+/g, " ").trim(),
    notas: textoNota(s.querySelector("aside.notes")),
  }));

  const publicar = () => {
    const { h, f } = Reveal.getIndices();
    fetch(`${base}/estado`, { method: "POST", headers: cabeceras,
      body: JSON.stringify({ id, indice: h, fragmento: f ?? -1, diapositivas: diapositivas() }) }).catch(() => {});
  };

  const ordenes = {
    siguiente: () => Reveal.next(),
    anterior: () => Reveal.prev(),
    ir: o => Number.isInteger(o.indice) && Reveal.slide(o.indice),
  };

  async function escuchar() {
    let desde = -1, instancia = null;
    for (;;) {
      try {
        const r = await fetch(`${base}/ordenes?id=${id}&desde=${desde}`, { headers: cabeceras });
        if (r.status === 401) return console.warn("Control remoto: clave incorrecta");
        const d = await r.json();
        // Primera conexión o relé reiniciado: hay que volver a publicar el estado
        if (d.instancia !== instancia) { instancia = d.instancia; publicar(); }
        desde = d.ultimo;
        for (const o of d.ordenes) ordenes[o.accion]?.(o);
      } catch { await new Promise(r => setTimeout(r, 2000)); }
    }
  }

  for (const ev of ["slidechanged", "fragmentshown", "fragmenthidden"]) Reveal.on(ev, publicar);
  escuchar();
}
