# Informe de Avance — Proyecto Final Data Science (YPF / Vaca Muerta)

**Proyecto:** Predicción y Optimización de la Producción de Hidrocarburos No Convencionales (Vaca Muerta / YPF)
**Fecha:** 3 al 12 de septiembre de 2026
**Etapa actual:** Pre-Entrega 3 (Modelado Supervisado) — CERRADA. Próximo paso: Modelado No Supervisado (clustering).

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

## 8. Cambio de estilo de código

A partir de esta etapa, todo el código del proyecto (`data_loader.py`, `preprocessor.py` y los notebooks) se reescribió en un **estilo más simple y lineal**: funciones únicas con pasos comentados en vez de múltiples funciones encadenadas con validaciones extensas. Se prioriza la legibilidad y la capacidad de explicar el código en la defensa oral, por sobre patrones más avanzados (type hints, manejo de excepciones, rutas independientes del directorio de ejecución). El comportamiento y los resultados numéricos son equivalentes a la versión anterior.

---

## 9. `notebooks/02_feature_engineering.ipynb` — Variables derivadas

Se crearon variables nuevas sobre el dataset limpio, pensadas para darle al modelo información sobre el comportamiento de cada pozo a lo largo del tiempo:

| Variable | Descripción |
|---|---|
| `antiguedad_meses` | Número de mes de producción del pozo (1 = primer mes registrado) |
| `prod_pet_mes_anterior` / `prod_gas_mes_anterior` | Producción del mes anterior (lag), por pozo |
| `declinacion_pet` / `declinacion_gas` | % de variación respecto al mes anterior |
| `ratio_gas_petroleo` | Relación gas/petróleo del mes |
| `prod_pet_acumulada` / `prod_gas_acumulada` | Producción acumulada del pozo hasta ese mes |
| `formacion_cod` / `cuenca_cod` | Codificación numérica de las variables categóricas `formacion` y `cuenca` |

**Verificación visual:** se graficó la curva de producción mensual y acumulada del pozo con más historia cargada, confirmando que la producción acumulada es siempre creciente (como corresponde a una suma acumulada) y que la curva mensual muestra el patrón esperable de un pozo no convencional. Se detectó un pico de producción puntual en ese pozo (posible reestimulación/refractura, o un pozo pre-boom de 2006 con comportamiento distinto al shale típico) — queda anotado como punto de atención para el modelado.

El resultado se guardó en `data/processed/produccion_con_features.csv` para uso directo del notebook de modelado.

---

## 10. `notebooks/03_modelado_supervisado.ipynb` — Regresión (predicción de `prod_pet`)

### 10.1 Diseño del experimento

- **Variable objetivo:** `prod_pet` (producción mensual de petróleo por pozo).
- **Modelo:** XGBoost (`XGBRegressor`), parámetros base sin optimizar (`n_estimators=200`, `max_depth=5`, `learning_rate=0.1`).
- **Separación train/test respetando el tiempo** (no aleatoria): entrenamiento con años anteriores a 2024, prueba con 2024-2025 — simula la situación real de predecir producción futura, no interpolar el pasado.
- Se excluyeron del entrenamiento: el primer mes de cada pozo (sin "mes anterior" disponible) y el año 2026 (incompleto).

### 10.2 Iteración 1 — Modelo base (7 features)

Features: `antiguedad_meses`, `prod_pet_mes_anterior`, `prod_gas_mes_anterior`, `ratio_gas_petroleo`, `profundidad`, `formacion_cod`, `cuenca_cod`.

**Resultado:** MAE 195.11 — RMSE 520.31 — R² 0.853. El gráfico de real vs. predicho mostró buen ajuste en el rango bajo-medio de producción, pero **subestimación sistemática de los pozos con picos de producción muy altos** (>10.000). `prod_pet_mes_anterior` concentró más del 90% de la importancia del modelo.

### 10.3 Iteración 2 — Fuga de datos detectada y descartada

Se intentó agregar `declinacion_pet` (variación % respecto al mes **actual**) como feature, buscando mejorar la detección de picos. El R² subió a **0.978**, un salto sospechosamente alto.

**Diagnóstico:** `declinacion_pet` se calcula como `(prod_pet - prod_pet_mes_anterior) / prod_pet_mes_anterior` — la variable objetivo (`prod_pet`) queda embebida en la fórmula de una de las features. Combinando `prod_pet_mes_anterior` y `declinacion_pet`, el valor de `prod_pet` se puede despejar algebraicamente (`prod_pet = prod_pet_mes_anterior × (1 + declinacion_pet)`), por lo que el modelo no estaba prediciendo: estaba recibiendo la respuesta disfrazada. Se confirmó el diagnóstico observando que, pese al R² casi perfecto, el error en los picos altos (>10.000) seguía siendo grande (2.580 de error promedio) — si la mejora fuera real, ese error también debería haber bajado.

**Esta versión fue descartada** y no es utilizable en producción, ya que `declinacion_pet` no puede calcularse en el momento de predecir (requiere conocer de antemano el dato que se busca estimar).

### 10.4 Iteración 3 — Modelo corregido (8 features)

Se reemplazó la variable con fuga de datos por `declinacion_pet_anterior` (declinación calculada con el mes anterior al anterior, es decir, información ya conocida al momento de predecir — sin fuga).

**Resultado:** MAE 163.33 — RMSE 445.42 — R² 0.885. Mejora **real y modesta** respecto al modelo base (R² +0.032), consistente con una variable que aporta señal genuina sin “ver” el futuro. `declinacion_pet_anterior` aparece como tercera variable en importancia (por detrás de `prod_pet_mes_anterior` y `antiguedad_meses`), sin dominar el modelo como ocurría con la versión con fuga. **El problema de subestimación de picos altos (>10.000) persistía.**

### 10.5 Iteración 4 — Máximo histórico del pozo (descartada)

Se agregó `prod_pet_maxima_anterior` (máximo histórico de producción del pozo, calculado solo con datos hasta el mes anterior — sin fuga), buscando que el modelo reconociera qué pozos tienen antecedentes de picos altos.

**Resultado:** MAE 165.63 — RMSE 444.47 — R² 0.885. Prácticamente idéntico al modelo anterior; el gráfico de importancia de variables mostró que el modelo casi no utilizó esta variable. **Descartada** por no aportar mejora real, priorizando un modelo más simple.

### 10.6 Iteración 5 — Log-transform del objetivo (descartada)

En vez de agregar otra variable, se probó entrenar el modelo sobre `log(1 + prod_pet)` en lugar del valor directo — una técnica estándar para atenuar el efecto de distribuciones muy sesgadas sobre el error cuadrático de entrenamiento.

**Resultado:** MAE 163.09 — RMSE 501.67 — R² 0.854. El RMSE empeoró notablemente y el error en picos altos subió a 6.028 (peor que las versiones anteriores). El gráfico de real vs. predicho reveló el motivo: al revertir el logaritmo (`expm1`), pequeños errores en escala logarítmica se amplifican exponencialmente, generando **sobreestimaciones extremas** (predicciones de hasta 35.000 para pozos que producían realmente 7.000-10.000). **Descartada** por introducir un problema nuevo y más grave que el que buscaba resolver.

### 10.7 Modelo final

Tras 4 iteraciones sobre el modelo base, la combinación ganadora es la del **Paso 10.4** (8 features, entrenamiento directo sobre `prod_pet`, sin log-transform ni variable de máximo histórico) — la mejor relación entre métricas y simplicidad del modelo.

### 10.8 Tabla comparativa completa

| Métrica | Base (7 features) | Con fuga (descartado) | + máxima histórica (descartado) | Log-transform (descartado) | **Modelo FINAL (8 features)** |
|---|---|---|---|---|---|
| MAE | 195.11 | 38.86 | 165.63 | 163.09 | **163.33** |
| RMSE | 520.31 | 204.07 | 444.47 | 501.67 | **445.42** |
| R² | 0.853 | 0.978 | 0.885 | 0.854 | **0.885** |

### 10.9 Limitación conocida (aceptada)

En todas las versiones válidas, el modelo **subestima los pozos con picos de producción muy altos** (posibles eventos de reestimulación/refractura). Se probaron dos enfoques distintos para resolverlo (una variable nueva y un cambio de objetivo de entrenamiento) y ninguno mejoró el resultado — uno de ellos incluso lo empeoró de forma más grave. Esto sugiere que el problema no es de ingeniería sobre los datos disponibles, sino de **ausencia de una variable que el dataset no incluye** (por ejemplo, si se programó una intervención en el pozo). Se documenta como limitación conocida y se avanza con evidencia en mano, en vez de continuar iterando sin garantía de mejora.

El modelo final se guardó en `models/modelo_produccion_pet.joblib`.

---

## 11. Próximos pasos

1. `notebooks/04_modelado_no_supervisado_dl.ipynb`: clustering (K-Means) de pozos según su curva de producción/declinación — potencialmente informado por los pozos con picos que el modelo supervisado no logra predecir bien.
2. Evaluar una ronda de optimización de hiperparámetros (Optuna) y explicabilidad (SHAP) sobre el modelo de regresión, si el cronograma lo permite.
3. Entrega Final: API en FastAPI, Dockerfile y documentación completa en README.md.
