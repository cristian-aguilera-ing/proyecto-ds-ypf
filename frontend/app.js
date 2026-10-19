// Frontend de pruebas: habla con la API a traves de nginx (/api/...)
const API = "/api";

// Datos que se guardan mientras la pagina esta abierta
const estado = {
  opciones: null,
  info: null,
  valorReal: null,       // valor real del ejemplo elegido (si hay)
  historial: [],
};

// ---------- utilidades ----------

function porId(id) {
  return document.getElementById(id);
}

function formatear(numero, decimales) {
  if (decimales === undefined) decimales = 1;
  return Number(numero).toLocaleString("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimales,
  });
}

// "m3" -> "m³" y "Mm3" -> "Mm³" para mostrar
function conSuperindice(unidad) {
  return unidad.replace(/3$/, "³");
}

async function pedir(ruta, opciones) {
  const respuesta = await fetch(API + ruta, opciones);
  let cuerpo = null;
  try {
    cuerpo = await respuesta.json();
  } catch (error) {
    cuerpo = null;
  }
  if (!respuesta.ok) {
    const error = new Error(textoDeError(cuerpo, respuesta.status));
    error.status = respuesta.status;
    throw error;
  }
  return cuerpo;
}

// La API devuelve el error como texto (HTTPException) o como lista (validacion)
function textoDeError(cuerpo, status) {
  if (!cuerpo || !cuerpo.detail) return "Error " + status + " al consultar la API.";
  if (typeof cuerpo.detail === "string") return cuerpo.detail;
  return cuerpo.detail
    .map(function (e) {
      const campo = e.loc ? e.loc[e.loc.length - 1] : "dato";
      return campo + ": " + e.msg;
    })
    .join(" | ");
}

// ---------- arranque ----------

async function iniciar() {
  const aviso = porId("estado-api");
  porId("enlace-docs").href = window.location.protocol + "//" + window.location.hostname + ":8000/docs";

  try {
    const salud = await pedir("/health");
    if (!salud.modelo_cargado) {
      aviso.textContent = "API conectada, pero el modelo no esta entrenado.";
      aviso.className = "estado mal";
      mostrarError(
        "Falta entrenar el modelo. Corré: docker compose --profile train run --rm entrenar " +
        "y despues reinicia la API con: docker compose restart api"
      );
      porId("boton-estimar").disabled = true;
      return;
    }
    estado.info = await pedir("/info");
    estado.opciones = await pedir("/opciones");
  } catch (error) {
    aviso.textContent = "No se pudo conectar con la API.";
    aviso.className = "estado mal";
    mostrarError(error.message);
    porId("boton-estimar").disabled = true;
    return;
  }

  aviso.textContent = "API conectada. Modelo del " + estado.info.version_modelo + ".";
  aviso.className = "estado ok";

  armarFormulario();
  armarEjemplos();
  armarTarjetaDelModelo();
}

function armarFormulario() {
  const unidades = estado.opciones.unidades;
  document.querySelectorAll(".u-pet").forEach(function (el) {
    el.textContent = conSuperindice(unidades.petroleo);
  });
  document.querySelectorAll(".u-gas").forEach(function (el) {
    el.textContent = conSuperindice(unidades.gas);
  });
  porId("unidad").textContent = conSuperindice(unidades.petroleo) + " por mes";

  llenarSelect(porId("formacion"), estado.opciones.formaciones);
  llenarSelect(porId("cuenca"), estado.opciones.cuencas);
}

function llenarSelect(select, opciones) {
  select.innerHTML = "";
  opciones.forEach(function (opcion) {
    const el = document.createElement("option");
    el.value = opcion.nombre;
    el.textContent = opcion.nombre + " (" + formatear(opcion.pozos, 0) + " pozos)";
    select.appendChild(el);
  });
}

function armarEjemplos() {
  const contenedor = porId("ejemplos");
  contenedor.innerHTML = "";
  estado.opciones.ejemplos.forEach(function (ejemplo, indice) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "ejemplo";
    boton.textContent = ejemplo.titulo;
    boton.title = ejemplo.descripcion;
    boton.setAttribute("aria-pressed", "false");
    boton.addEventListener("click", function () {
      cargarEjemplo(indice);
    });
    contenedor.appendChild(boton);
  });
}

function cargarEjemplo(indice) {
  const ejemplo = estado.opciones.ejemplos[indice];
  Object.keys(ejemplo.entrada).forEach(function (campo) {
    porId(campo).value = ejemplo.entrada[campo];
  });
  estado.valorReal = ejemplo.valor_real;

  document.querySelectorAll(".ejemplo").forEach(function (boton, i) {
    boton.setAttribute("aria-pressed", i === indice ? "true" : "false");
  });
  limpiarErroresDeCampos();
  porId("formulario").requestSubmit();
}

// ---------- formulario ----------

const CAMPOS_NUMERICOS = [
  "antiguedad_meses",
  "profundidad",
  "prod_pet_mes_anterior",
  "prod_pet_hace_2_meses",
  "prod_gas_mes_anterior",
];

function limpiarErroresDeCampos() {
  CAMPOS_NUMERICOS.forEach(function (campo) {
    porId(campo).removeAttribute("aria-invalid");
  });
}

// Chequeos simples en el navegador (la API valida de nuevo)
function leerFormulario() {
  limpiarErroresDeCampos();
  const datos = {
    formacion: porId("formacion").value,
    cuenca: porId("cuenca").value,
  };
  const problemas = [];

  CAMPOS_NUMERICOS.forEach(function (campo) {
    const texto = porId(campo).value;
    const numero = parseFloat(texto);
    let minimo = 0;
    if (campo === "antiguedad_meses") minimo = 3;
    const exigeMayorACero = campo === "prod_pet_mes_anterior" || campo === "prod_pet_hace_2_meses" || campo === "profundidad";

    let esValido = texto !== "" && !isNaN(numero) && numero >= minimo;
    if (exigeMayorACero && numero <= 0) esValido = false;

    if (!esValido) {
      porId(campo).setAttribute("aria-invalid", "true");
      problemas.push(campo);
    }
    datos[campo] = campo === "antiguedad_meses" ? Math.round(numero) : numero;
  });

  return { datos: datos, problemas: problemas };
}

async function enviarFormulario(evento) {
  evento.preventDefault();
  ocultarError();

  const lectura = leerFormulario();
  if (lectura.problemas.length > 0) {
    mostrarError("Revisá los campos marcados: antigüedad desde 3 meses y petróleo y profundidad mayores a 0.");
    return;
  }

  const boton = porId("boton-estimar");
  boton.disabled = true;
  boton.textContent = "Estimando...";

  try {
    const respuesta = await pedir("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lectura.datos),
    });
    mostrarResultado(respuesta, lectura.datos);
  } catch (error) {
    mostrarError(error.message);
  } finally {
    boton.disabled = false;
    boton.textContent = "Estimar producción";
  }
}

// ---------- resultado ----------

function mostrarResultado(respuesta, datos) {
  porId("vacio").hidden = true;
  porId("resultado").hidden = false;

  porId("cifra").textContent = formatear(respuesta.produccion_predicha, 1);
  porId("unidad").textContent = conSuperindice(respuesta.unidad) + " por mes";

  const variacion = porId("variacion");
  const signo = respuesta.variacion_porcentual >= 0 ? "+" : "";
  variacion.textContent =
    signo + formatear(respuesta.variacion_porcentual, 1) + " % respecto del mes anterior (" +
    signo + formatear(respuesta.variacion_predicha, 1) + " " + conSuperindice(respuesta.unidad) + ")";
  variacion.className = "variacion " + (respuesta.variacion_porcentual >= 0 ? "sube" : "baja");

  // Barras: todas a la misma escala (la mayor ocupa todo el ancho)
  const valores = {
    anterior: respuesta.produccion_mes_anterior,
    modelo: respuesta.produccion_predicha,
    real: estado.valorReal,
  };
  const mayor = Math.max(valores.anterior, valores.modelo, valores.real || 0);

  ["anterior", "modelo", "real"].forEach(function (clave) {
    const fila = document.querySelector('.barra[data-barra="' + clave + '"]');
    const valor = valores[clave];
    if (valor === null || valor === undefined) {
      fila.hidden = true;
      return;
    }
    fila.hidden = false;
    fila.querySelector(".barra-valor").textContent = formatear(valor, 1);
    fila.querySelector(".barra-relleno").style.width = (100 * valor / mayor) + "%";
  });

  // Advertencias
  const lista = porId("avisos");
  lista.innerHTML = "";
  respuesta.advertencias.forEach(function (texto) {
    const item = document.createElement("li");
    item.textContent = texto;
    lista.appendChild(item);
  });

  porId("json").textContent = JSON.stringify(respuesta, null, 2);

  agregarAlHistorial(respuesta, datos);
}

function mostrarError(texto) {
  const caja = porId("error");
  caja.textContent = texto;
  caja.hidden = false;
}

function ocultarError() {
  porId("error").hidden = true;
}

// ---------- historial ----------

function agregarAlHistorial(respuesta, datos) {
  estado.historial.unshift({
    formacion: datos.formacion,
    antiguedad: datos.antiguedad_meses,
    anterior: respuesta.produccion_mes_anterior,
    estimacion: respuesta.produccion_predicha,
    real: estado.valorReal,
  });
  estado.historial = estado.historial.slice(0, 8);
  dibujarHistorial();
}

function dibujarHistorial() {
  const cuerpo = porId("historial-filas");
  cuerpo.innerHTML = "";

  if (estado.historial.length === 0) {
    cuerpo.innerHTML = '<tr class="vacio"><td colspan="5">Todavía no hiciste ninguna estimación.</td></tr>';
    return;
  }

  estado.historial.forEach(function (fila) {
    const tr = document.createElement("tr");
    const real = fila.real === null || fila.real === undefined ? "-" : formatear(fila.real, 1);
    const celdas = [
      [fila.formacion, ""],
      [formatear(fila.antiguedad, 0) + " meses", "num"],
      [formatear(fila.anterior, 1), "num"],
      [formatear(fila.estimacion, 1), "num"],
      [real, "num"],
    ];
    celdas.forEach(function (celda) {
      const td = document.createElement("td");
      td.textContent = celda[0];
      if (celda[1]) td.className = celda[1];
      tr.appendChild(td);
    });
    cuerpo.appendChild(tr);
  });
}

// ---------- tarjeta del modelo ----------

function armarTarjetaDelModelo() {
  const info = estado.info;
  const m = info.metricas_test;
  const b = info.metricas_baseline;
  const unidad = conSuperindice(info.unidades.petroleo);
  const rango = info.rango_entrenamiento;

  let html = "";
  html += "<p>El modelo se entrenó con datos hasta " + (info.anio_corte - 1) + " (" +
    formatear(info.filas_entrenamiento, 0) + " pozos-mes) y se evaluó en " + info.anio_corte +
    "-" + (info.anio_corte + 1) + " (" + formatear(info.filas_prueba, 0) + " pozos-mes). " +
    "Se compara contra un método simple: suponer que el pozo produce lo mismo que el mes anterior.</p>";

  html += '<div class="metricas"><table><thead><tr><th></th><th class="num">Error medio (MAE)</th>' +
    '<th class="num">RMSE</th><th class="num">R²</th><th class="num">Error medio en picos</th></tr></thead><tbody>';
  html += "<tr><td>Modelo</td><td class='num'>" + formatear(m.mae, 1) + "</td><td class='num'>" + formatear(m.rmse, 1) +
    "</td><td class='num'>" + formatear(m.r2, 3) + "</td><td class='num'>" + formatear(m.error_medio_picos, 0) + "</td></tr>";
  html += "<tr><td>Repetir el mes anterior</td><td class='num'>" + formatear(b.mae, 1) + "</td><td class='num'>" + formatear(b.rmse, 1) +
    "</td><td class='num'>" + formatear(b.r2, 3) + "</td><td class='num'>" + formatear(b.error_medio_picos, 0) + "</td></tr>";
  html += "</tbody></table></div>";

  html += "<p>Los errores están en " + unidad + " por mes. «Picos» son los meses con producción real mayor a 10.000.</p>";

  if (m.error_medio_picos > b.error_medio_picos) {
    html += "<p><strong>Limitación:</strong> en los picos extremos el modelo subestima más que el método simple. " +
      "El máximo mensual que vio al entrenar fue " + formatear(rango.prod_pet_max, 0) + " " + unidad +
      " y los modelos de árboles no predicen por encima de lo que conocen. La interfaz avisa cuando un pozo se sale de ese rango.</p>";
  }

  porId("modelo-contenido").innerHTML = html;
}

// ---------- eventos ----------

// Si el usuario cambia algo a mano, ya no es el ejemplo: se borra el valor real
function olvidarEjemplo() {
  estado.valorReal = null;
  document.querySelectorAll(".ejemplo").forEach(function (boton) {
    boton.setAttribute("aria-pressed", "false");
  });
}

document.addEventListener("DOMContentLoaded", function () {
  porId("formulario").addEventListener("submit", enviarFormulario);
  porId("formulario").addEventListener("input", olvidarEjemplo);
  porId("formulario").addEventListener("change", olvidarEjemplo);
  porId("limpiar").addEventListener("click", function () {
    estado.historial = [];
    dibujarHistorial();
  });
  iniciar();
});
