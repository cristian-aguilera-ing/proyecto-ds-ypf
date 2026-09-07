# Informe de Avance — Proyecto Final Data Science (YPF / Vaca Muerta)

**Proyecto:** Predicción y Optimización de la Producción de Hidrocarburos No Convencionales (Vaca Muerta / YPF)
**Fecha:** 3 de septiembre de 2026
**Etapa actual:** Preparación de datos — previa a Pre-Entrega 2 (EDA)

---

## 1. Objetivo del proyecto

Predecir la curva de producción acumulada mensual de petróleo y gas en pozos no convencionales (shale/tight) de la cuenca Neuquina, a partir de parámetros geológicos y de completación, usando regresión supervisada (XGBoost / LightGBM) y clustering no supervisado (K-Means) para agrupar pozos según su curva de declinación.

---

## 2. Fuente de datos

Se identificó y descargó el dataset oficial de la **Secretaría de Energía de la Nación Argentina**, dentro del dataset "Producción de petróleo y gas por pozo (Capítulo IV)":

- **Archivo principal:** *Producción de Pozos de Gas y Petróleo No Convencional* — ya viene filtrado a pozos shale/tight, evitando tener que separarlos manualmente del resto del universo de pozos convencionales.
- **Archivo complementario:** *Capítulo IV - Pozos* — metadatos de pozos (se descargó pero, como se detalla más abajo, no resultó necesario para el cruce inicial).

Portal: https://datos.gob.ar/dataset/energia-produccion-petroleo-gas-por-pozo-capitulo-iv

**Nota:** una primera exploración en Google Colab había mostrado solo 5.701 filas (2015-2018), lo cual resultó ser una muestra parcial. El archivo efectivamente cargado en el entorno de trabajo (VS Code) contiene el histórico completo.

---

## 3. Entorno de trabajo

- **Estructura de repositorio** creada según el estándar del curso (`data/`, `notebooks/`, `src/`, `api/`, `models/`, `reports/`, más `Dockerfile`, `requirements.txt`, `README.md`).
- **Entorno virtual** creado con `python3 -m venv venv` (Python 3.14.6, instalado vía Homebrew) para aislar las dependencias del sistema operativo.
- `venv/` agregado a `.gitignore` para no versionarlo.
- Dependencias instaladas dentro del entorno (`pandas` por el momento) y congeladas en `requirements.txt` con `pip freeze`.

---

## 4. `src/data_loader.py`

Se construyó el módulo de ingesta con responsabilidad única: **leer y validar los datos crudos, sin transformarlos** (esa tarea queda reservada a `preprocessor.py`).

Funciones implementadas:

- **`cargar_produccion_no_convencional()`**: lee el CSV principal desde `data/raw/`, valida que estén presentes las columnas mínimas esperadas por el resto del pipeline y falla con un error claro si no lo están (en vez de dejar que el problema aparezca más adelante en el modelado).
- **`cargar_capitulo_iv_pozos()`**: lee el CSV complementario de metadatos de pozos, mismo criterio de validación.
- **`validar_calidad()`**: función de diagnóstico que no modifica datos, solo reporta: duplicados, nulos por columna, rangos sospechosos de profundidad, producción negativa y cobertura temporal. Pensada como insumo directo para el EDA.

Decisión de diseño: las rutas se resuelven de forma relativa a la ubicación del script (no al directorio desde donde se ejecuta), evitando el problema de rutas absolutas que exige evitar la consigna de reproducibilidad del curso.

---

## 5. Resultados obtenidos hasta el momento

### 5.1 Dimensiones y cobertura

| Métrica | Valor |
|---|---|
| Filas totales | 421.046 |
| Columnas | 40 |
| Rango temporal | 2006 – 2026 |
| Duplicados (pozo-año-mes) | 0 |

### 5.2 Columnas con valores nulos

| Columna | Nulos | % aprox. sobre 421.046 |
|---|---|---|
| `vida_util` | 412.082 | ~97.9% |
| `observaciones` | 397.045 | ~94.3% |
| `clasificacion` | 922 | ~0.2% |
| `subclasificacion` | 922 | ~0.2% |
| `tipoextraccion` | 614 | ~0.15% |
| `tipoestado` | 614 | ~0.15% |
| `tipopozo` | 614 | ~0.15% |
| `sub_tipo_recurso` | 452 | ~0.1% |

### 5.3 Anomalías detectadas

- **Profundidad:** rango observado de 0 a 378.939 (unidad esperada: metros). 122 pozos superan los 10.000, lo cual es físicamente imposible para un pozo real — indica error de carga o de unidad en el dato de origen.
- **Producción negativa:** 1 registro con `prod_pet` negativo y 2 con `prod_gas` negativo, sobre 421.046 filas — volumen insignificante pero sin sentido físico (posibles rectificaciones cargadas con signo).

---

## 6. Decisiones pendientes (a resolver en `preprocessor.py`, después del EDA visual)

1. **`vida_util` y `observaciones`**: candidatas a descartarse por falta de datos (>94% nulos).
2. **Nulos menores** (`tipoextraccion`, `tipoestado`, `tipopozo`, `clasificacion`, `subclasificacion`, `sub_tipo_recurso`): imputación por moda o eliminación puntual de filas, dado el bajo volumen relativo.
3. **Profundidad anómala**: definir si los 122 casos sospechosos son error de unidad (¿de cm en vez de m?) o directamente outliers a excluir/clipear. Pendiente de confirmar con histograma en el EDA.
4. **Profundidad = 0**: revisar si corresponde a pozos sin dato cargado (equivalente a nulo) más que a un valor real.
5. **Producción negativa**: filtrar o corregir las 3 filas afectadas.
6. **Metadatos de pozo**: el archivo principal ya trae `formacion`, `profundidad`, `cuenca`, `provincia` y coordenadas — el cruce con `capitulo-iv-pozos.csv` no resultó necesario para las variables identificadas hasta ahora; se conserva el archivo por si se necesita enriquecer con algo puntual más adelante.

---

## 7. Avance posterior: construcción de `notebooks/01_eda_limpieza.ipynb`

Se armó el notebook de EDA, pensado únicamente para **visualizar** las anomalías detectadas por `validar_calidad()` — todavía sin limpiar nada, para tomar las decisiones de la Sección 6 con evidencia visual antes de escribirlas en `preprocessor.py`.

Estructura del notebook:

1. Carga de datos reutilizando `data_loader.py` (importado desde `src/`).
2. Gráfico de barras con % de nulos por columna, para confirmar visualmente qué columnas descartar.
3. Histogramas de `profundidad` (uno con todo el rango, otro con zoom a 1–10.000) más una tabla de los 20 casos más sospechosos (>10.000), para buscar un patrón antes de decidir si son error de unidad o outliers a eliminar.
4. Histogramas de `prod_pet` / `prod_gas` y tabla puntual de las 3 filas con producción negativa.
5. Boxplots de profundidad (clipeada), `prod_pet` y `prod_gas`.
6. Serie temporal de producción total anual (petróleo y gas), como primera vista agregada de la cuenca.
7. Celda de conclusiones en blanco, a completar tras observar los gráficos.

### Entorno

Se instalaron las librerías necesarias para graficar y correr notebooks dentro del `venv`: `matplotlib`, `seaborn`, `jupyter`, `ipykernel` (pendiente `pip freeze > requirements.txt` al finalizar la instalación).

### Estado al cierre de la sesión

Se abrió `01_eda_limpieza.ipynb` en VS Code y, al ejecutar la primera celda (imports + carga de datos), el editor solicitó seleccionar el kernel de Jupyter. La instalación de las librerías estaba terminando de correr en ese momento. **Quedó pendiente**: seleccionar el intérprete del `venv` como kernel y ejecutar el notebook completo.

---

## 8. Próximos pasos (a retomar)

1. Seleccionar el kernel del `venv` en VS Code y correr todas las celdas de `01_eda_limpieza.ipynb`.
2. Observar los gráficos y completar la celda de conclusiones (en particular: patrón en los 122 pozos con profundidad >10.000, y qué son los casos con profundidad = 0).
3. Con esas conclusiones, definir las reglas de limpieza concretas y trasladarlas a `src/preprocessor.py`.
