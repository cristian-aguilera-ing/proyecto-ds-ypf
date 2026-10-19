# Proyecto Final Data Science — Predicción de Producción No Convencional (YPF / Vaca Muerta)

Proyecto final de la carrera Data Science (Ingenias+), cuyo objetivo es **predecir la producción mensual de petróleo de pozos no convencionales (shale/tight)**, principalmente de la cuenca Neuquina, a partir de datos históricos de producción, profundidad, formación geológica y cuenca. Además, se agrupan los pozos según su comportamiento productivo usando clustering no supervisado (K-Means).

## Equipo

- Cristian Alejandro Aguilera
- Abigail Roxana Vicentelo
- Ian Lionel Tapias Díaz

## Estado actual

✅ Pre-Entrega 1 (definición del proyecto) — cerrada
✅ Pre-Entrega 2 (EDA + limpieza, `notebooks/01_eda_limpieza.ipynb`) — cerrada
✅ Pre-Entrega 3 (Modelado supervisado, `notebooks/03_modelado_supervisado.ipynb`) — cerrada, con comparación XGBoost vs. LightGBM
✅ Pre-Entrega 4 (Modelado no supervisado, `notebooks/04_modelado_no_supervisado_dl.ipynb`) — cerrada, K-Means con k = 4
✅ Explicabilidad con SHAP (`notebooks/05_explicabilidad_shap_dl.ipynb`) — hecha sobre el modelo final
✅ Optimización de hiperparámetros (Optuna, `notebooks/06_optimizacion_optuna_dl.ipynb`) — hecha, con validación temporal
✅ Entrega final (API FastAPI + frontend de pruebas + Docker Compose) — funcionando, ver sección 9

**Modelo supervisado actual:** LightGBM que predice la variación mensual de producción de petróleo, 8 variables e hiperparámetros optimizados con Optuna: MAE 154.26, RMSE 398.75, R² 0.907 (baseline de repetir el mes anterior: MAE 170.92, RMSE 456.92, R² 0.878).

**Clustering actual:** K-Means con k = 4 sobre 4.295 pozos (silhouette 0.473).

---

## 1. El dataset

Los datos son públicos, publicados por la **Secretaría de Energía de la Nación Argentina**, dentro del dataset *"Producción de petróleo y gas por pozo (Capítulo IV)"*.

- **Filas:** 421.046
- **Columnas:** 40 (39 tras la limpieza)
- **Rango temporal:** 2006 – 2026
- **Granularidad:** una fila = un pozo, en un mes y año puntual
- **Cuencas:** 4 (la cuenca Neuquina concentra el 95,5% de los 5.089 pozos)
- **Variable objetivo (lo que predecimos):** `prod_pet` (producción de petróleo del pozo, en ese mes)

### Cómo descargar el dataset

El archivo CSV **no está versionado en este repositorio** (ver sección de estructura de carpetas más abajo) porque es pesado y viene de una fuente externa que se actualiza periódicamente. Para conseguirlo:

1. Copiá este link completo:

   ```
   http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv
   ```

2. Pegalo directo en la barra de tu navegador (no funciona si hacés clic desde algunos lectores de Markdown — tiene que ser copiado y pegado completo).
3. La descarga del CSV arranca automáticamente.
4. Guardá el archivo descargado dentro de la carpeta `data/raw/` del proyecto, sin cambiarle el nombre.

---

## 2. Hallazgos del análisis exploratorio

El diagnóstico inicial detectó anomalías reales de calidad de datos: la profundidad tenía valores imposibles (hasta 378.939), pero los 122 registros sospechosos correspondían a un único pozo con un error de carga repetido en todos sus meses, y otros 164 pozos tenían la profundidad en 0 (dato faltante). Había solo 3 filas con producción negativa (correcciones cargadas con signo) y las columnas `vida_util` y `observaciones` tenían más de 90% de nulos. La producción tiene una distribución fuertemente sesgada a la derecha (muchos pozos chicos, pocos muy productivos) y la serie temporal muestra el crecimiento exponencial del boom de Vaca Muerta, con una caída aparente en 2026 que se debe a que ese año está incompleto. Además, 704 de los 5.089 pozos tienen meses sin fila (por ejemplo, un pozo parado que retoma), por lo que la antigüedad y las variables del mes anterior se calculan en meses de calendario y no contando filas.

## 3. Modelos ajustados

**Supervisado (regresión):** se predice la producción de petróleo del mes siguiente (`prod_pet`) para pozos que produjeron petróleo en los dos meses previos (el *alcance* del modelo: cubre el 93.5% de los meses con producción del período de prueba; los meses en que un pozo retoma la producción quedan afuera). Se usan 8 variables (antigüedad del pozo en meses de calendario, producción de gas y de petróleo del mes anterior, declinación y ratio gas/petróleo del mes previo, profundidad, formación y cuenca) y un split temporal (entrenamiento hasta 2023, prueba 2024-2025). Se compararon XGBoost y LightGBM (empate técnico: RMSE 441.70 y 440.63) y se detectaron y corrigieron dos fugas de datos: `declinacion_pet` (R² de 0.979, imposible de usar en producción) y `ratio_gas_petroleo`, que usaba la producción del mismo mes que se quiere predecir. Se agregó un baseline simple (repetir el mes anterior, R² 0.878) para medir el aporte real del modelo. El modelo final no predice el nivel de producción sino su **variación respecto del mes anterior**, y la predicción se obtiene sumando esa variación al mes anterior (con piso en 0): así mejora todas las métricas (RMSE 408.75, R² 0.903). Después se optimizaron los hiperparámetros con Optuna usando una validación temporal dentro del entrenamiento (sin mirar el período de prueba), lo que bajó el RMSE a 398.75 (R² 0.907) y redujo la brecha entre entrenamiento y prueba. Subestima los pozos con picos muy altos (más de 10.000), una limitación aceptada.

**No supervisado (clustering):** se resumió cada pozo en 4 variables (pico de producción, declinación típica, antigüedad y ratio gas/petróleo) y se agruparon con K-Means. La primera versión, con promedios, dejó dos clusters de un solo pozo por valores extremos, por lo que se corrigió usando medianas, filtrando pozos sin producción real, recortando la declinación y aplicando logaritmo. Con k = 4 (elegido por codo, silhouette e interpretabilidad) se obtuvieron cuatro grupos: pozos modernos de alta producción, pozos viejos de producción media, pozos viejos con mucho gas y casi nada de petróleo, y pozos recién puestos en producción (75 pozos, casi todos con 10 meses de historia o menos). Los 94 pozos con pico mayor a 10.000 caen casi todos en el grupo de pozos modernos.

---

## 4. Estructura del repositorio

```
proyecto-ds-ypf/
├── data/
│   ├── raw/          ← CSV originales (no versionados, ver sección 1)
│   └── processed/    ← versiones limpias, generadas por el código
├── notebooks/        ← análisis paso a paso, con texto y gráficos
├── src/              ← funciones reutilizables
│   ├── data_loader.py    ← lectura y validación de datos crudos
│   ├── preprocessor.py   ← limpieza y transformación
│   ├── train.py          ← entrena el modelo final y guarda lo que usa la API
│   └── predict.py        ← lógica de predicción (mes anterior + variación)
├── api/              ← backend FastAPI
│   ├── app.py            ← endpoints: /health, /info, /opciones, /predict
│   └── schemas.py        ← validación de entrada y salida
├── frontend/         ← interfaz web de pruebas (HTML + JS, servida por nginx)
├── models/           ← modelos entrenados y metadatos (.joblib, .json)
├── reports/          ← gráficos e informes de resultados
├── docs/             ← informe de avance y pre-entregas
├── compose.yaml      ← levanta API + frontend (y el entrenamiento, bajo demanda)
├── Dockerfile        ← imagen de la API y del entrenamiento
├── requirements.txt       ← librerías para los notebooks
├── requirements-api.txt   ← librerías mínimas para la API (Docker)
└── README.md
```

---

## 5. Instalación y puesta en marcha

```bash
# 1. Cloná el repositorio
git clone https://github.com/cristian-aguilera-ing/proyecto-ds-ypf.git
cd proyecto-ds-ypf

# 2. Creá y activá el entorno virtual
python3 -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

# 3. Instalá las dependencias
pip install -r requirements.txt

# 4. Descargá el dataset (ver sección 1) y guardalo en data/raw/
```

## 6. Cómo trabajar en este repositorio

- **Nunca se trabaja directo sobre `main`.** Cada cambio se hace en una rama propia:

  ```bash
  git checkout main
  git pull origin main
  git checkout -b nombre-de-tu-rama
  ```

- Al terminar, se sube la rama y se abre un Pull Request en GitHub para que el equipo lo revise antes de mergear a `main`.

---

## 7. Notebooks

| Notebook | Contenido |
|---|---|
| `01_eda_limpieza.ipynb` | Análisis exploratorio, detección de nulos y valores anómalos, limpieza del dataset |
| `02_feature_engineering.ipynb` | Creación de variables derivadas en meses de calendario (antigüedad, producción del mes anterior, declinación, ratio gas/petróleo y sus versiones del mes anterior) |
| `03_modelado_supervisado.ipynb` | Entrenamiento y comparación de modelos (XGBoost vs. LightGBM), corrección de fugas de datos, alcance explícito del modelo, baseline y modelo de variación para predecir `prod_pet` |
| `04_modelado_no_supervisado_dl.ipynb` | Clustering K-Means de pozos (4 variables por pozo, k = 4), con la corrección de la primera versión y el cruce con los pozos de pico alto |
| `05_explicabilidad_shap_dl.ipynb` | Explicabilidad con SHAP sobre el modelo final: importancia y dirección del efecto de cada variable, y análisis de los picos subestimados |
| `06_optimizacion_optuna_dl.ipynb` | Optimización de hiperparámetros del modelo final con Optuna y validación temporal, con chequeo de overfitting |

**Orden de ejecución:** 01 → 02 → 03 → 04 → 06 → 05. El notebook 02 genera el CSV que usan todos los demás; el 06 guarda el modelo principal optimizado (que reemplaza al que guarda el 03) y el 05 explica ese modelo, por eso se corre después.

## 8. Limitación conocida

El modelo subestima los pozos con picos de producción muy altos (más de 10.000 por mes, en las unidades del dataset). Se probaron varios enfoques sin resolverlo de fondo. La explicación más probable combina dos causas: el modelo casi no vio producciones tan altas al entrenar (el máximo hasta 2023 fue 15.943, contra 26.593 en el período de prueba) y los modelos de árboles no extrapolan, y es posible que además falte una variable que capture intervenciones en el pozo (reestimulaciones). En esos meses extremos, repetir el valor del mes anterior sigue siendo mejor que el modelo. Se documenta como limitación aceptada.

---

## 9. Correr la API y el frontend con Docker

Requisitos: Docker Desktop (o Docker Engine con el plugin Compose) y haber generado `data/processed/produccion_con_features.csv` con la versión actual del notebook 02 (tiene que incluir las variables del mes anterior; si el CSV es de una versión vieja, el entrenamiento avisa qué columnas faltan).

```bash
# 1. Entrenar el modelo dentro del contenedor (guarda el modelo y los metadatos en models/)
docker compose --profile train run --rm entrenar

# 2. Levantar la API y el frontend
docker compose up --build

# 3. Abrir
#    Frontend de pruebas:  http://localhost:8080
#    API (Swagger):        http://localhost:8000/docs

# Apagar
docker compose down
```

El paso 1 usa los hiperparámetros de Optuna si existe `models/mejores_parametros_optuna.json` (lo genera el notebook 06) y, si no, los parámetros base. Para forzar los base: `docker compose --profile train run --rm entrenar python -m src.train --parametros base`. Si se vuelve a entrenar con la API ya levantada, reiniciarla con `docker compose restart api`.

**Cómo usar la API.** El modelo predice la producción de petróleo del mes siguiente a partir del historial reciente del pozo. Ejemplo:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"antiguedad_meses": 12, "prod_pet_mes_anterior": 1500, "prod_pet_hace_2_meses": 1650,
       "prod_gas_mes_anterior": 300, "profundidad": 3000,
       "formacion": "vaca muerta", "cuenca": "NEUQUINA"}'
```

| Endpoint | Qué hace |
|---|---|
| `GET /health` | Indica si la API está viva y si el modelo está cargado |
| `GET /info` | Versión del modelo, métricas en el período de prueba y rango de entrenamiento |
| `GET /opciones` | Formaciones, cuencas y ejemplos reales para probar |
| `POST /predict` | Estima la producción del mes siguiente |

**Cómo funciona la predicción.** El modelo no predice la producción directamente sino su variación respecto del mes anterior; la API suma esa variación al mes anterior y pone un piso en 0. Los pozos deben tener petróleo en los dos meses previos (meses de calendario consecutivos) y al menos 3 meses de antigüedad, medida en meses de calendario desde el primer mes con datos (el modelo se entrenó solo con ese tipo de filas: los meses en que un pozo retoma la producción quedan fuera de su alcance). Cuando un pozo se sale del rango de entrenamiento, la respuesta incluye una advertencia (por ejemplo, producciones por encima del máximo visto al entrenar, donde el modelo tiende a subestimar).
