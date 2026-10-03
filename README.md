# Proyecto Final Data Science — Predicción de Producción No Convencional (YPF / Vaca Muerta)

Proyecto final de la carrera Data Science (Ingenias+), cuyo objetivo es **predecir la producción mensual de petróleo de pozos no convencionales (shale/tight) de la cuenca Neuquina**, a partir de datos históricos de producción, profundidad, formación geológica y cuenca. En una segunda etapa, se agrupan los pozos según su curva de declinación usando clustering no supervisado.

## Equipo

- Cristian Alejandro Aguilera
- Abigail Roxana Vicentelo
- Ian Lionel Tapias Díaz

## Estado actual

✅ Pre-Entrega 1 (definición del proyecto) — cerrada
✅ Pre-Entrega 2 (EDA + limpieza, `notebooks/01_eda_limpieza.ipynb`) — cerrada
✅ Pre-Entrega 3 (Modelado supervisado, `notebooks/03_modelado_supervisado.ipynb`) — cerrada, con comparación XGBoost vs. LightGBM
🔜 Modelado no supervisado (clustering, `notebooks/04_modelado_no_supervisado.ipynb`) — próximo paso
🔜 Entrega final (API + Dockerfile) — pendiente

**Modelo actual:** LightGBM, 8 variables, RMSE 439.34, R² 0.888.

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

## 2. Estructura del repositorio

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
├── models/           ← modelos entrenados, guardados en disco (.joblib)
├── reports/          ← gráficos e informes de resultados
├── requirements.txt  ← librerías necesarias
├── Dockerfile         ← (a futuro) para correr el proyecto empaquetado
└── README.md
```

---

## 3. Instalación y puesta en marcha

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

## 4. Cómo trabajar en este repositorio

- **Nunca se trabaja directo sobre `main`.** Cada cambio se hace en una rama propia:

  ```bash
  git checkout main
  git pull origin main
  git checkout -b nombre-de-tu-rama
  ```

- Al terminar, se sube la rama y se abre un Pull Request en GitHub para que el equipo lo revise antes de mergear a `main`.

---

## 5. Notebooks

| Notebook | Contenido |
|---|---|
| `01_eda_limpieza.ipynb` | Análisis exploratorio, detección de nulos y valores anómalos, limpieza del dataset |
| `02_feature_engineering.ipynb` | Creación de variables derivadas (producción del mes anterior, declinación, antigüedad del pozo, etc.) |
| `03_modelado_supervisado.ipynb` | Entrenamiento y comparación de modelos (XGBoost vs. LightGBM) para predecir `prod_pet` |
| `04_modelado_no_supervisado.ipynb` | *(próximo paso)* Clustering K-Means de pozos según su curva de declinación |

## 6. Limitación conocida

El modelo actual subestima sistemáticamente los pozos con picos de producción muy altos (posibles eventos de reestimulación/refractura). Se probaron tres enfoques distintos sin resolverlo de fondo, lo que sugiere que falta en el dataset una variable que capture ese tipo de intervención. Se documenta como limitación aceptada.
