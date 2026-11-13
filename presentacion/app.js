// Arranque: carga datos y guion, inicia Reveal y prepara cada escena.
import { iniciar as bloque1 } from "./escenas/bloque1.js";
import { iniciar as bloque2 } from "./escenas/bloque2.js";
import { iniciar as bloque3 } from "./escenas/bloque3.js";
import { iniciar as pozoNuevo } from "./escenas/pozo-nuevo.js";
import { iniciar as apendice } from "./escenas/apendice.js";
import { avanceAutomatico } from "./lib/avance-auto.js";

const [datos, nb, guion] = await Promise.all(["datos/presentacion.json", "datos/notebooks.json", "guion.md"]
  .map((u, i) => fetch(u).then(r => i < 2 ? r.json() : r.text())));
datos.nb = nb;

// Fases de CRISP-ML(Q): cada escena marca la suya y, si tiene, el riesgo de calidad que se mitigó
const FASES = ["Negocio y datos", "Preparación", "Ingeniería del modelo", "Evaluación", "Despliegue", "Monitoreo"];
for (const sec of document.querySelectorAll("section[data-fase]")) {
  const barra = document.createElement("div");
  barra.className = "fases";
  barra.innerHTML = `<ol>${FASES.map((f, i) => `<li class="${i + 1 === Number(sec.dataset.fase) ? "actual" : ""}">${i + 1}<em> ${f}</em></li>`).join("")}</ol>`;
  if (sec.dataset.riesgo) {
    const [riesgo, mitigacion] = sec.dataset.riesgo.split("|");
    barra.innerHTML += `<p class="riesgo"><b>Riesgo</b> ${riesgo} <i>→</i> <b>Mitigación</b> ${mitigacion}</p>`;
  }
  sec.prepend(barra);
}

// El guion es una sola fuente: cada "## id | orador | tiempo" se vuelve la nota de esa escena
for (const b of guion.split(/^## /m).slice(1)) {
  const [cab, ...cuerpo] = b.split("\n"), [id, orador, tiempo] = cab.split("|").map(t => t.trim());
  const sec = document.querySelector(`#escena-${id}`);
  if (!sec) continue;
  const nota = document.createElement("aside");
  nota.className = "notes";
  nota.innerText = `${orador} · ${tiempo}\n\n${cuerpo.join("\n").trim()}`;
  sec.append(nota);
}

await Reveal.initialize({ hash: true, width: 1920, height: 1080, margin: 0, minScale: .2, maxScale: 2, center: false,
                          controls: false, progress: true, transition: "fade", transitionSpeed: "fast", plugins: [RevealNotes] });
for (const iniciar of [bloque1, bloque2, pozoNuevo, bloque3, apendice]) iniciar(datos);
// La miniatura del control remoto (index.html?vista) no avanza sola: copia la posición de la presentación
if (!new URLSearchParams(location.search).has("vista")) avanceAutomatico(Reveal);

// Portada: mientras se muestra, se apaga el fondo fijo de isolíneas para que no se superponga con el que se dibuja
const marcarPortada = () => document.documentElement.classList.toggle("en-portada", Reveal.getCurrentSlide()?.id === "escena-portada");
Reveal.on("slidechanged", marcarPortada);
marcarPortada();

// Control remoto: abrir la presentación con ?control=CLAVE; las notas y los botones están en /control.html
const claveControl = new URLSearchParams(location.search).get("control");
if (claveControl) import("./lib/control-remoto.js").then(m => m.conectarControl(claveControl, Reveal));

addEventListener("keydown", e => {
  if (e.key.toLowerCase() !== "t") return;
  const r = document.documentElement;
  if (r.dataset.theme === "light") delete r.dataset.theme; else r.dataset.theme = "light";
});

// Portada: las isolíneas se dibujan al entrar
const capa = document.querySelector("#portada-lineas");
capa.innerHTML = await fetch("lib/contornos.svg").then(r => r.text());
const trazos = capa.querySelectorAll("path");
trazos.forEach(p => { const l = p.getTotalLength(); p.style.strokeDasharray = l; p.style.strokeDashoffset = l; });
gsap.to(trazos, { strokeDashoffset: 0, duration: 2.4, ease: "power2.inOut", stagger: .018 });
gsap.from(".portada > *", { y: 28, opacity: 0, duration: .9, ease: "power3.out", stagger: .14, delay: .5 });
