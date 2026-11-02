// Utilidades compartidas por las escenas.
export const es = (v, d = 0) => Number(v).toLocaleString("es-AR", { maximumFractionDigits: d, minimumFractionDigits: d });
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
export const COLOR = { petroleo: () => css("--petroleo"), gas: () => css("--gas"), acento: () => css("--acento"), suave: () => css("--suave") };

// Ejecuta la animación de entrada cada vez que se llega a la escena
export function alEntrar(seccion, fn) {
  const correr = () => requestAnimationFrame(fn);
  Reveal.on("slidechanged", e => { if (e.currentSlide === seccion) correr(); });
  if (Reveal.getCurrentSlide() === seccion) correr();
}
