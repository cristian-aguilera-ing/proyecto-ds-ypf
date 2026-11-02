// Escena 10: cambiar profundidad y año en la llamada al modelo mueve la curva real P10–P50–P90.
import { CodigoVivo, enlazarPasos } from "../lib/codigo-vivo.js";
import { CurvaBanda, contarHasta } from "../lib/graficos.js";

export function iniciar(datos) {
  const seccion = document.querySelector("#escena-pozo-nuevo");
  const { curvas, profundidades, anios } = datos.pozo_nuevo;
  const yMax = Math.max(...Object.values(curvas).flatMap(c => c.p90));
  const grafico = new CurvaBanda(seccion.querySelector("svg"), { yMax });
  const acum = seccion.querySelector(".dato .v");
  const inicial = { profundidad: 3000, anio_inicio: 2018 };
  const dibujar = e => {
    const c = curvas[`${e.profundidad}_${e.anio_inicio}`];
    grafico.mover(c); contarHasta(acum, c.acum12);
  };
  const vivo = new CodigoVivo(seccion.querySelector(".codigo"), {
    profundidad: { lista: profundidades, actual: inicial.profundidad },
    anio_inicio: { lista: anios, actual: inicial.anio_inicio },
  }, dibujar);
  dibujar(inicial);
  enlazarPasos(seccion, [
    { profundidad: 5000, anio_inicio: 2018 },
    { profundidad: 7000, anio_inicio: 2018 },
    { profundidad: 7000, anio_inicio: 2024 },
  ], inicial, vivo);
}
