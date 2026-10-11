# Proyecto Final Data Science — Predicción de Producción No Convencional (YPF / Vaca Muerta)

Proyecto final de la carrera Data Science (Ingenias+), cuyo objetivo es **predecir la producción mensual de petróleo de pozos no convencionales (shale/tight) de la cuenca Neuquina**, a partir de datos históricos de producción, profundidad, formación geológica y cuenca. Además, se agrupan los pozos según su comportamiento productivo usando clustering no supervisado (K-Means).

## Equipo

- Cristian Alejandro Aguilera
- Abigail Roxana Vicentelo
- Ian Lionel Tapias Díaz

## Estado actual

✅ Pre-Entrega 1 (definición del proyecto) — cerrada
✅ Pre-Entrega 2 (EDA + limpieza, `notebooks/01_eda_limpieza.ipynb`) — cerrada
✅ Pre-Entrega 3 (Modelado supervisado, `notebooks/03_modelado_supervisado.ipynb`) — cerrada, con comparación XGBoost vs. LightGBM
✅ Pre-Entrega 4 (Modelado no supervisado, `notebooks/04_modelado_no_supervisado_dl.ipynb`) — cerrada, K-Means con k = 4
🔜 Entrega final (API + Dockerfile) — pendiente

**Modelo supervisado actual:** LightGBM, 8 variables, RMSE 439.34, R² 0.888.

**Clustering actual:** K-Means con k = 4 sobre 4.295 pozos (silhouette 0.473).

---

## 1. El dataset

Los datos son públicos, publicados por la **Secretaría de Energía de la Nación Argentina**, dentro del dataset *"Producción de petróleo y gas por pozo (Capítulo IV)"*.

- **Filas:** 421.046
- **Columnas:** 40 (39 tras la limpieza)
- **Rango temporal:** 2006 – 2026
- **Granularidad:** una fila = un pozo, en un mes y año puntual
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

El diagnóstico inicial detectó anomalías reales de calidad de datos: la profundidad tenía valores imposibles (hasta 378.939), pero los 122 registros sospechosos correspondían a un único pozo con un error de carga repetido en todos sus meses, y otros 164 pozos tenían la profundidad en 0 (dato faltante). Había solo 3 filas con producción negativa (correcciones cargadas con signo) y las columnas `vida_util` y `observaciones` tenían más de 90% de nulos. La producción tiene una distribución fuertemente sesgada a la derecha (muchos pozos chicos, pocos muy productivos) y la serie temporal muestra el crecimiento exponencial del boom de Vaca Muerta, con una caída aparente en 2026 que se debe a que ese año está incompleto.

## 3. Modelos ajustados

**Supervisado (regresión):** se predice `prod_pet` con LightGBM y 8 variables (antigüedad del pozo, producción de gas y de petróleo del mes anterior, declinación del mes previo, ratio gas/petróleo, profundidad, formación y cuenca), con un split temporal (entrenamiento hasta 2023, prueba 2024-2025). Se compararon XGBoost y LightGBM (empate técnico, con ligera ventaja de LightGBM: RMSE 439.34, R² 0.888). En el camino se detectó y descartó una fuga de datos (R² de 0.978, imposible de usar en producción). El modelo subestima los pozos con picos muy altos (más de 10.000), una limitación aceptada.

**No supervisado (clustering):** se resumió cada pozo en 4 variables (pico de producción, declinación típica, antigüedad y ratio gas/petróleo) y se agruparon con K-Means. La primera versión, con promedios, dejó dos clusters de un solo pozo por valores extremos, por lo que se corrigió usando medianas, filtrando pozos sin producción real, recortando la declinación y aplicando logaritmo. Con k = 4 (elegido por codo, silhouette e interpretabilidad) se obtuvieron cuatro grupos: pozos modernos de alta producción, pozos viejos de producción media, pozos viejos con mucho gas y casi nada de petróleo, y pozos recién puestos en producción. Los 94 pozos con pico mayor a 10.000 caen casi todos en el grupo de pozos modernos.

---

## 4. Estructura del repositorio

```
proyecto-ds-ypf/
├── data/
│   ├── raw/          ← CSV originales (no versionados, ver sección 1)
│   └── processed/    ← versiones limpias, generadas por el código
├── notebooks/        ← análisis paso a paso, con texto y gráficos
├── src/              ← funciones reutilizables que los notebooks importan
│   ├── data_loader.py    ← lectura y validación de datos crudos
│   └── preprocessor.py   ← limpieza y transformación
├── api/              ← (a futuro) API para exponer el modelo
├── models/           ← modelos entrenados (LightGBM, XGBoost, K-Means y scaler), en .joblib
├── reports/          ← gráficos e informes de resultados
├── requirements.txt  ← librerías necesarias
├── Dockerfile         ← (a futuro) para correr el proyecto empaquetado
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
| `02_feature_engineering.ipynb` | Creación de variables derivadas (producción del mes anterior, declinación, antigüedad del pozo, etc.) |
| `03_modelado_supervisado.ipynb` | Entrenamiento y comparación de modelos (XGBoost vs. LightGBM) para predecir `prod_pet` |
| `04_modelado_no_supervisado_dl.ipynb` | Clustering K-Means de pozos (4 variables por pozo, k = 4), con la corrección de la primera versión y el cruce con los pozos de pico alto |

## 8. Limitación conocida

El modelo actual subestima sistemáticamente los pozos con picos de producción muy altos (posibles eventos de reestimulación/refractura). Se probaron tres enfoques distintos sin resolverlo de fondo, lo que sugiere que falta en el dataset una variable que capture ese tipo de intervención. Se documenta como limitación aceptada.
