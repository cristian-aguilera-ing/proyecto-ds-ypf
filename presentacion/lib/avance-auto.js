// Avance automático: las escenas con pasos (fragmentos) los recorren solas con los tiempos del guion.
// Cada escena declara `data-avance="10,19"`: los segundos, desde que se entra, en que aparece cada paso.
// Si quien presenta avanza o retrocede con el teclado, el reloj sigue desde ese paso. La tecla A lo pausa.
export function avanceAutomatico(Reveal) {
  let temporizador = null, activo = true, entrada = 0;

  const cancelar = () => { clearTimeout(temporizador); temporizador = null; };
  const tiempos = sec => (sec?.dataset.avance ?? "").split(",").map(Number).filter(Number.isFinite);
  const pasoActual = () => Reveal.getIndices().f ?? -1;

  // Programa el paso siguiente respecto del momento de entrada a la escena, sin acumular el desfase de las animaciones
  const programar = () => {
    cancelar();
    const sec = Reveal.getCurrentSlide(), t = tiempos(sec), i = pasoActual() + 1;
    if (!activo || i >= t.length) return;
    const espera = Math.max(t[i] * 1000 - (performance.now() - entrada), 1500);
    temporizador = setTimeout(() => { if (Reveal.getCurrentSlide() === sec) Reveal.nextFragment(); }, espera);
  };

  Reveal.on("slidechanged", () => {
    entrada = performance.now();
    // Si se llega desde abajo o desde el apéndice, la escena ya viene con sus pasos mostrados: no se repite
    if (pasoActual() < 0) programar(); else cancelar();
  });
  Reveal.on("fragmentshown", programar);
  Reveal.on("fragmenthidden", cancelar);
  entrada = performance.now();
  if (pasoActual() < 0) programar();

  addEventListener("keydown", e => {
    if (e.key.toLowerCase() !== "a" || e.ctrlKey || e.metaKey) return;
    activo = !activo;
    if (activo) programar(); else cancelar();
    const aviso = document.querySelector("#aviso-auto") ?? document.body.appendChild(Object.assign(document.createElement("div"), { id: "aviso-auto" }));
    aviso.textContent = activo ? "Avance automático: activado" : "Avance automático: en pausa";
    aviso.classList.add("visible");
    setTimeout(() => aviso.classList.remove("visible"), 1800);
  });
}
