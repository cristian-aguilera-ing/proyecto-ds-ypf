# Predicción de producción de petróleo y gas no convencional — Cuenca Neuquina

Proyecto final del programa **Data Science — Energía Digital 2026 (Fundación YPF)**.

## Equipo

- Cristian Alejandro Aguilera
- Abigail Roxana Vicentelo
- Ian Lionel Tapias Díaz

## Documentación

| Documento | Contenido |
|---|---|
| [docs/Pre_Entrega_1_YPF](docs/Pre_Entrega_1_YPF.pdf) | Definición del problema y dataset |
| [docs/Pre_Entrega_2_YPF](docs/Pre_Entrega_2_YPF.pdf) | EDA, limpieza y transformación |
| [docs/Pre_Entrega_3_YPF](docs/Pre_Entrega_3_YPF.pdf) | Feature engineering y modelado supervisado |
| [docs/Pre_Entrega_4_YPF](docs/Pre_Entrega_4_YPF.pdf) | Clustering y SVD |
| [docs/Informe_Avance_Proyecto_YPF](docs/Informe_Avance_Proyecto_YPF.pdf) | Estado del proyecto y cambios de la versión 1 a la 2 |
| [docs/guia_del_proyecto](docs/guia_del_proyecto.pdf) | Instalación, ejecución y flujo de trabajo con Git |
| [docs/guia_frontend](docs/guia_frontend.pdf) | Cómo leer el frontend (también en [Markdown](docs/guia_frontend.md)) |

Cada documento está en `.docx` (editable) y `.pdf`, salvo la guía del frontend, que está en `.md` y `.pdf`.

![Aplicación web: pronóstico de petróleo y gas con tres pestañas](docs/img/01_inicio.png)

## Novedades y correcciones de la versión final

| Área | Cambio |
|---|---|
| Frontend | Rediseño con superficies translúcidas, fondo de isolíneas de la cuenca y **modo claro / oscuro** (por defecto oscuro) |
| Frontend | Nueva pestaña **"Métricas del modelo"**: 4 indicadores y 8 gráficos de test 2024–2025 (R² y WAPE por horizonte, backtest contra Arps, pozo nuevo contra curva mediana, cobertura P10–P90, elección de k, perfiles de clusters y comparación con la versión 1) |
| Frontend | Desplegable **"Cómo leer este gráfico"** en cada gráfico, botón **Limpiar** y descripción del sistema en el encabezado |
| Frontend | Buscador con estado **activo / sin producción**, búsqueda por varias palabras y orden por relevancia |
| Corrección | Elegir un pozo sin producción en su último mes rompía la pantalla; ahora muestra un aviso y no pronostica |
| API | **Validación de coordenadas** dentro de la Cuenca Neuquina (lat −40 a −34, lon −70,5 a −67) con mensaje claro, y aviso si el pozo queda a más de 50 km del área elegida |
| API / Docker | **Memoria de 921 MB a 336 MB**: un worker, Polars con 2 hilos, tope de 1 GB y sin `shap` en la imagen (ver "Consumo de memoria") |
| Corrección | El ejemplo de Swagger y del README usaba un `idpozo` que no existe (159640); ahora usa 166848 (PLU.Nq.LCa-3039(h)) |
| Tests | De 15 a **28 tests** (búsqueda, pozos sin producción, campos opcionales, límites de la cuenca y aviso de distancia) |
| Documentación | Guía del frontend con capturas nuevas, Informe de Avance y guía del proyecto actualizados |

Predice la producción mensual de **petróleo (m³)** y **gas (Mm³ = miles de m³)** de pozos no convencionales (shale / tight) de la **Cuenca Neuquina**, en dos modos:

| Modo | Pregunta que responde | Entrada | Salida |
|---|---|---|---|
| **A · Pozo existente** | ¿Cuánto va a producir este pozo los próximos 1–12 meses? | `idpozo` (búsqueda por sigla) | Curva mensual P10/P50/P90, acumulada, declinación, GOR, cluster, explicación SHAP |
| **B · Pozo nuevo** | ¿Qué curva tipo esperar de un pozo a perforar? | formación, shale/tight, yacimiento, operadora, tipo de pozo, profundidad, ubicación, año | Curva de 24 meses P10/P50/P90, acumulada 12 y 24 meses, pico, GOR esperado, cluster |

Petróleo y gas tienen **modelos separados** (la relación gas/petróleo por pozo es bimodal: son en la práctica dos poblaciones distintas).

---

## 1. Dataset

- Fuente: Secretaría de Energía de la Nación — *Producción de pozos de gas y petróleo no convencional* (Capítulo IV). [Descarga CSV](http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv) → guardar en `data/raw/` sin renombrar.
- Crudo: 421.046 filas × 40 columnas, 2006-01 → 2026-07, 4 cuencas.
- **Cuenca Neuquina:** 404.037 filas, 4.862 pozos (96% del dataset).
- Complemento opcional: padrón de pozos *Capítulo IV* (`capitulo-iv-pozos.csv`, mismo portal de datos.energia.gob.ar) en `data/raw/`; si no está, el pipeline funciona igual.
- Dataset de trabajo (versionado en el repo): `data/processed/panel_neuquina.parquet` (pozo × mes) y `data/processed/pozos_neuquina.parquet` (1 fila por pozo).

## 2. Hallazgos del EDA → decisiones de limpieza

| Hallazgo | Decisión |
|---|---|
| Neuquina concentra el 96% de las filas y casi todo el petróleo | Filtrar solo Neuquina (modelo especializado) |
| Inyectores, sumideros, acuíferos y pozos de servicio | Excluidos (no son productores) |
| `vida_util` 98% nulo, `observaciones` 94%, `iny_*` ~100% en 0 | Columnas descartadas |
| Profundidad 0 (1,4%) y un pozo con 378.939 m | Fuera de [300, 8000] m → mediana del pozo → (formación, yacimiento) → formación |
| `tef` > días del mes y meses con producción pero `tef = 0` | Acotado a [0, días del mes]; `tef = 0` con producción → mes completo |
| Un pozo con lat/lon invertidas | Intercambio de coordenadas |
| 981 pozos cambiaron de operadora | Se usa la última operadora |
| Meses sin fila (pozos parados) | **Grilla mensual continua** por pozo (lags = meses calendario reales) |
| Producción con sesgo extremo (p99 ≈ 700× mediana) | Modelado en escala `log1p` |
| GOR por pozo bimodal (petróleo ~cientos, gas ~decenas de miles m³/m³) | Modelos separados; fluido = petróleo si GOR < 3.000 |
| Pozos que ya producían en 2006 (inicio del registro) | Marcados como censurados: excluidos del modo B y del clustering |

La limpieza completa (`src/ypf_ds/data/clean.py`) corre en ~2 segundos con **Polars** (lectura lazy). El EDA usa además **DuckDB** para consultas SQL directas sobre los DataFrames.

## 3. Modelos

**Validación temporal** (nunca se entrena con el futuro): train ≤ 2022 · validación 2023 (Optuna) · **test 2024–2025**. En el modo B el corte es por año de inicio del pozo.

- **Modo A:** LightGBM sobre filas (pozo, mes de origen *t*, horizonte *h* = 1…12). Target: ratio `q[t+h] / q[t]` (la declinación relativa), ponderado por `q[t]²`. 53 features: lags 1/2/3/6/12, medias móviles, pico, fracción del pico, acumulada, caudal por día efectivo, GOR, corte de agua, tendencia, meses en producción, formación, yacimiento, operadora, ubicación, profundidad, año de inicio.
- **Modo B:** LightGBM sobre filas (pozo, mes de vida 1…24). Target: producción del mes en volumen; Optuna elige el objetivo (L2, Poisson o Tweedie). Features conocidas antes de perforar.
- **Incertidumbre:** modelos de **cuantiles** P10 y P90 además del modelo puntual.
- **Hiperparámetros:** Optuna (TPE) con early stopping sobre la validación 2023.
- **Comparación de algoritmos** (notebook 03): persistencia, Ridge, árbol de decisión, KNN, Random Forest, MLP, XGBoost, LightGBM; Optuna vs GridSearch.
- **Baselines:** persistencia (repetir el último mes), **Arps hiperbólica** ajustada por pozo, y curva mediana por formación × tipo de pozo × mes de vida.
- **No supervisado** (notebook 04): forma de la curva de 12 meses + pico + GOR → **SVD** → **K-Means** (k por silhouette), comparado con DBSCAN.
- **Explicabilidad** (notebook 05): SHAP global; la API devuelve las contribuciones SHAP de cada predicción.
- **MLflow:** cada entrenamiento registra parámetros y métricas en `mlflow.db` (`mlflow ui --backend-store-uri sqlite:///mlflow.db`).

### Resultados en test (2024–2025)

**Modo A · pozo existente** (713.822 filas de petróleo y 850.222 de gas; horizontes 1–12 meses):

| Fluido | Modelo | MAE | RMSE | R² | WAPE |
|---|---|---|---|---|---|
| Petróleo (m³) | **LightGBM** | **215** | **537** | **0,730** | **0,369** |
| | Persistencia | 364 | 898 | 0,246 | 0,625 |
| Gas (Mm³) | **LightGBM** | **263** | **823** | **0,779** | **0,375** |
| | Persistencia | 377 | 1.191 | 0,536 | 0,539 |

Backtest: pronóstico a 12 meses desde diciembre 2023 para todos los pozos activos (WAPE, menor es mejor):

| Fluido | Pozos | LightGBM | Arps hiperbólica | Persistencia |
|---|---|---|---|---|
| Petróleo | 2.291 | **0,357** | 0,583 | 0,665 |
| Gas | 2.724 | **0,385** | 0,474 | 0,518 |

**Modo B · pozo nuevo** (pozos que arrancaron en 2024–2025, nunca vistos en el entrenamiento; acumulada de los primeros 12 meses, 729 pozos):

| Fluido | Modelo | MAE | R² | WAPE |
|---|---|---|---|---|
| Petróleo (m³) | **LightGBM** | **9.940** | **0,448** | **0,309** |
| | Curva mediana por formación y tipo | 16.253 | −0,282 | 0,505 |
| Gas (Mm³) | **LightGBM** (Tweedie) | **6.508** | **0,860** | **0,282** |
| | Curva mediana por formación y tipo | 9.499 | 0,724 | 0,412 |

**Cobertura de la banda P10–P90** en test (ideal 0,80): 0,81 petróleo A · 0,79 gas A · 0,74 petróleo B · 0,73 gas B.

**Clustering:** K-Means con k = 4 sobre 4.144 pozos (silhouette 0,22): tres tipos de pozos de petróleo (pico alto / medio / bajo, con distinta declinación) y uno de gas. DBSCAN no encuentra grupos densos separados (las curvas forman un continuo).

### Error según el horizonte y comparación con el proyecto anterior

El R² global del modo A promedia horizontes de 1 a 12 meses. Por horizonte (test 2024–2025):

| Horizonte | R² petróleo | R² persistencia petróleo | R² gas | R² persistencia gas |
|---|---|---|---|---|
| 1 mes | **0,889** | 0,817 | **0,882** | 0,836 |
| 3 meses | 0,745 | 0,503 | 0,793 | 0,614 |
| 6 meses | 0,658 | 0,085 | 0,755 | 0,458 |
| 12 meses | 0,630 | −0,840 | 0,721 | 0,341 |

El proyecto anterior (`proyecto-ds-ypf`) reportaba **R² 0,907**, pero medía otra cosa: 1 mes adelante, solo pozos con producción en los dos meses previos, solo petróleo y todas las cuencas. Con ese mismo alcance, este modelo obtiene **R² 0,906** (persistencia 0,876; el anterior tenía 0,878 de baseline): **son equivalentes**. La diferencia es que este proyecto pronostica hasta 12 meses, donde repetir el último mes falla por completo y el modelo mantiene R² de 0,63–0,72.

### Complemento: padrón Capítulo IV (`capitulo-iv-pozos.csv`)

El padrón de pozos se une por `idpozo` (98% de cobertura) y agrega cota, profundidad de respaldo y las fechas de perforación y terminación, de donde salen `dias_perf` y `dias_term`. Además, la sigla `(h)` marca los pozos horizontales: en Vaca Muerta petróleo producen ~10 veces más en su primer año.

En el entrenamiento, Optuna compara para el modo B el set de variables base contra base + Capítulo IV y elige por **RMSE en validación 2023**:
- **Petróleo:** 1.072,8 (base) vs 1.079,2 (con Capítulo IV).
- **Gas:** 1.961,5 vs 1.963,0.

Se mantuvo el set base: la profundidad medida (que en pozos horizontales incluye la rama lateral) y el año de inicio ya capturaban esa información. El padrón queda integrado en la limpieza (profundidad de respaldo, `es_horizontal`) y la selección se repite en cada reentrenamiento.

**Decisión clave de modelado:** entrenar en `log1p` y volver con `expm1` subestimaba la producción total en ~25% (desigualdad de Jensen). El modelo puntual se entrena para minimizar el error en volumen (ratio `q[t+h]/q[t]` ponderado por `q[t]²` en el modo A; volumen directo con objetivo L2/Tweedie en el modo B) y los cuantiles P10/P90 en escala log.

## Guía de uso del frontend

Cómo leer cada indicador, el gráfico, las bandas P10–P90, la explicación SHAP, el cluster, los avisos y el dashboard de métricas: **[docs/guia_frontend.md](docs/guia_frontend.md)** (también en [PDF](docs/guia_frontend.pdf)).

![Pestaña Métricas del modelo](docs/img/08_metricas.png)

## 4. Estructura

```
├── data/raw/                 CSV original (no versionado)
├── data/processed/           panel y tabla de pozos limpios (Parquet)
├── notebooks/                01 EDA · 02 limpieza y transformación · 03 supervisado · 04 clustering y SVD · 05 SHAP
├── src/ypf_ds/
│   ├── config.py             rutas, umbrales y cortes temporales
│   ├── data/                 load.py (ingesta) · clean.py (limpieza y panel)
│   ├── features/build.py     features y targets de ambos modos
│   └── models/               train.py · predict.py · baselines.py · evaluate.py · cluster.py
├── models/                   artefactos .joblib + metadata.json
├── api/                      app.py (FastAPI) · model.py (carga de modelos) · schemas.py (Pydantic)
├── frontend/                 HTML + JS + Chart.js: pozo existente, pozo nuevo y métricas
├── docker/                   Dockerfiles y nginx.conf
├── tests/                    limpieza, no-fuga de datos, API y validación (28 tests)
├── compose.yaml · Makefile · requirements.txt · requirements-api.txt
```

## 5. Cómo correrlo

### Con entorno virtual (desarrollo)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python -m ypf_ds.data.clean          # limpieza → data/processed/
python -m ypf_ds.models.train        # entrenamiento → models/
pytest -q                            # 28 tests
uvicorn api.app:app --reload         # API en http://localhost:8000/docs
```

El frontend en modo desarrollo: `python -m http.server 5500 -d frontend` y abrir http://localhost:5500.

### Con Docker (todo el proyecto)

```bash
docker compose up --build -d
```

- Frontend: http://localhost:8080
- API + Swagger: http://localhost:8000/docs

Reentrenar dentro de un contenedor: `docker compose --profile train run --rm train`.

### Consumo de memoria

Medido con `docker stats` en la imagen de la API, después de 60 pedidos (existente, nuevo y búsqueda):

| Configuración | RAM en reposo | RAM tras 60 pedidos |
|---|---|---|
| Antes: 2 workers de uvicorn, Polars con todos los hilos | 921 MB | 972 MB |
| Ahora: 1 worker, Polars con 2 hilos | 336 MB | 344 MB |

- **Los `.joblib` no son el problema:** los 5 modelos pesan 7,4 MB en disco y suman ~60 MB en memoria.
- **Lo que pesa** son las librerías (Polars, pandas, LightGBM y scikit-learn: ~245 MB) y la lectura del panel de producción. Son 37 MB de datos, pero Polars reservaba ~195 MB al leerlo con 12 hilos; con 2 hilos reserva ~110 MB.
- **Cada worker de uvicorn es un proceso con su propia copia** de modelos y datos. Por eso 2 workers duplicaban la RAM sin aportar nada: cada pronóstico tarda ~35 ms (existente) y ~20 ms (nuevo).
- `compose.yaml` fija un tope de 1 GB para la API. Si el consumo se disparara, Docker reinicia ese contenedor sin afectar al resto de la máquina.
- La imagen ya no instala `shap`: la API calcula las contribuciones con el TreeSHAP nativo de LightGBM (`pred_contrib`).

## 6. API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado y versión de los modelos |
| GET | `/metadata` | Métricas de test, parámetros y clusters |
| GET | `/opciones` | Valores válidos para el formulario (formaciones, áreas con lat/lon/profundidad típicas, rangos) |
| GET | `/pozos?q=LCa` | Búsqueda de pozos por sigla o idpozo |
| POST | `/predict/existente` | Pronóstico de un pozo existente |
| POST | `/predict/nuevo` | Curva tipo de un pozo nuevo |

Las entradas se validan con Pydantic: un pedido inválido responde **422** con el motivo. En `/predict/nuevo` la latitud tiene que estar entre −40 y −34 y la longitud entre −70,5 y −67 (`config.LIMITES_CUENCA`), y si el pozo queda a más de 50 km del centro del área elegida la respuesta incluye un aviso.

```bash
curl -X POST localhost:8000/predict/existente -H "Content-Type: application/json" \
     -d '{"idpozo": 166848, "horizonte": 12}'

curl -X POST localhost:8000/predict/nuevo -H "Content-Type: application/json" -d '{
  "formacion": "vaca muerta", "sub_tipo_recurso": "SHALE", "areayacimiento": "LOMA CAMPANA",
  "empresa": "YPF S.A.", "tipopozo": "Petrolífero", "profundidad": 3000,
  "lat": -38.3, "lon": -69.0, "anio_inicio": 2026}'
```

La respuesta incluye, por fluido: curva P10/P50/P90, acumuladas, caudal diario inicial, pico, declinación a 12 meses, métricas del modelo en test y las variables que más influyeron (SHAP). Además: GOR, corte de agua, tipo de pozo (cluster) y avisos (datos viejos, valores fuera del rango de entrenamiento, pozos censurados).

## 7. Sesgos, límites e IA responsable

- **Sesgo de representación:** Vaca Muerta y YPF concentran la mayoría de los pozos; en formaciones u operadoras con pocos datos las predicciones son menos confiables (se agrupan las operadoras chicas en "OTRAS").
- **Variables omitidas:** el dataset público no tiene longitud de rama lateral, número de etapas de fractura ni volumen de arena, que son los principales determinantes de la productividad de un pozo nuevo. El año de inicio funciona como *proxy* de la tecnología de completación.
- **Drift tecnológico y de mercado:** la productividad por pozo crece año a año; los pozos futuros pueden superar la predicción. Hay que reentrenar periódicamente (el pipeline completo se reejecuta con un comando).
- **Eventos no predecibles:** paradas por mantenimiento, restricciones de transporte o decisiones comerciales no están en los datos; la banda P10–P90 da una idea de la incertidumbre, no la elimina.
- **Extrapolación:** la API avisa cuando una entrada está fuera del rango de entrenamiento.
- **Uso:** herramienta orientativa y educativa; no reemplaza un estudio de reservorio ni debe ser la única base de decisiones de inversión.
- **Uso de IA en el desarrollo:** se usaron asistentes de código como apoyo; todas las decisiones de limpieza y modelado están justificadas en los notebooks y verificadas con tests.
