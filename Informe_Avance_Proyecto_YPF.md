# Informe de Avance — Proyecto Final Data Science (YPF / Vaca Muerta)

**Proyecto:** Predicción y Optimización de la Producción de Hidrocarburos No Convencionales (Vaca Muerta / YPF)
**Fecha:** 3 al 7 de septiembre de 2026
**Etapa actual:** Pre-Entrega 2 (EDA + limpieza) — CERRADA. Próximo paso: Feature Engineering.

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

### 5.3 Anomalías detectadas (diagnóstico inicial)

- **Profundidad:** rango observado de 0 a 378.939 (unidad esperada: metros). 122 registros superan los 10.000, lo cual es físicamente imposible para un pozo real.
- **Producción negativa:** 1 registro con `prod_pet` negativo y 2 con `prod_gas` negativo, sobre 421.046 filas — volumen insignificante pero sin sentido físico.

---

## 6. `notebooks/01_eda_limpieza.ipynb` — EDA visual

Se construyó el notebook de EDA para visualizar las anomalías antes de decidir cómo tratarlas. Estructura: carga de datos (reutilizando `data_loader.py`), gráfico de % de nulos por columna, histogramas de `profundidad` (completo y con zoom 1-10.000) con tabla de los 20 casos más extremos, histogramas y tabla de producción negativa, boxplots de las tres variables clave, y serie temporal de producción total anual.

**Entorno:** se instalaron `matplotlib`, `seaborn`, `jupyter`, `ipykernel` dentro del `venv` y se actualizó `requirements.txt`.

### Hallazgos confirmados con los gráficos

- **Profundidad >10.000 — un solo pozo, no ruido disperso:** los 122 registros sospechosos corresponden todos al mismo pozo (`idpozo 156804`, formación "lajas"), con el valor 378.939 repetido en cada uno de sus registros mensuales a lo largo de los años — es un error puntual de carga en origen, no un conjunto de outliers estadísticos independientes.
- **Profundidad = 0:** 5.738 filas, pero correspondientes a **164 pozos distintos** — a diferencia del caso anterior, sí se trata como dato faltante genuino (el campo nunca se cargó para esos pozos).
- **Producción (`prod_pet`, `prod_gas`):** distribución fuertemente sesgada a la derecha, comportamiento esperado en datos de producción de hidrocarburos (muchos pozos de baja producción, pocos de alta). A tener en cuenta para aplicar `log1p` en el feature engineering.
- **Producción negativa:** las 3 filas confirmadas tienen magnitudes chicas (-12, -7, -0.001), consistentes con correcciones/rectificaciones cargadas con signo.
- **Serie temporal (datos crudos):** curva de crecimiento exponencial 2006-2025 esperable del boom de Vaca Muerta, pero con una **caída artificial en 2026** — el dataset todavía no tiene los 12 meses cargados para ese año (no es una caída real de producción).

---

## 7. `src/preprocessor.py` — reglas de limpieza implementadas

Módulo con responsabilidad de transformación (a diferencia de `data_loader.py`, que solo lee y valida). Cada función recibe un DataFrame y devuelve uno nuevo (sin modificar in-place), permitiendo encadenarlas en `pipeline_preprocesamiento()`:

| Función | Regla aplicada |
|---|---|
| `descartar_columnas_vacias` | Elimina `vida_util` y `observaciones` (>90% nulos) |
| `imputar_categoricas` | Imputa con la moda: `tipoextraccion`, `tipoestado`, `tipopozo`, `clasificacion`, `subclasificacion`, `sub_tipo_recurso` (nulos <0.25%) |
| `corregir_profundidad` | Valores fuera del rango plausible (100–10.000) se tratan como faltantes y se imputan con la **mediana por formación geológica** (no mediana global, porque la profundidad varía según formación). Esta regla genérica resuelve tanto el caso del pozo 156804 como los 164 pozos con profundidad = 0, sin necesidad de excepciones manuales por ID. |
| `corregir_produccion_negativa` | Clipea a 0 los valores negativos de `prod_pet` y `prod_gas` |
| `marcar_anio_incompleto` | Agrega columna booleana `anio_completo` para poder excluir 2026 de análisis de tendencia anual, sin perder esas filas para el modelado |

### Verificación de resultados (antes / después)

| Métrica | Antes | Después |
|---|---|---|
| Shape | 421.046 × 40 | 421.046 × 39 |
| Nulos en `profundidad` | 122 casos >10.000 + 5.738 en 0 | 0 |
| `prod_pet` negativa | 1 | 0 |
| `prod_gas` negativa | 2 | 0 |
| Filas marcadas año incompleto (2026) | — | 34.386 |

### Verificación visual (sección 8 del notebook)

- El histograma de `profundidad` post-limpieza muestra una distribución realista concentrada entre 1.500 y 7.000, con pico en ~3.000 — sin rastro del valor erróneo de 378.939.
- La serie temporal recalculada **excluyendo el año incompleto** muestra la curva de crecimiento limpia 2006-2025, sin la caída artificial de 2026.

Con esto, la Pre-Entrega 2 (EDA + limpieza) queda **cerrada y verificada tanto numérica como visualmente**.

---

## 8. Próximos pasos

1. Construir `notebooks/02_feature_engineering.ipynb`: variables derivadas (declinación mes a mes, edad del pozo, ratios gas/petróleo, codificación de variables categóricas como `formacion` y `cuenca`) sobre el DataFrame limpio (`pipeline_preprocesamiento`).
2. Definir la variable objetivo y el esquema de train/test (respetando la dimensión temporal — no mezclar meses futuros en el set de entrenamiento).
3. Avanzar con el modelado supervisado (regresión) y no supervisado (clustering de curvas de declinación) según el plan original.
