# Graph Report - proyecto-ds-ypf  (2026-10-27)

## Corpus Check
- 35 files · ~165,372 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 26 file(s) not represented in the graph (top: (none) 8, .ipynb 7, .joblib 5)

## Summary
- 391 nodes · 735 edges · 14 communities (9 shown, 5 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 86 edges (avg confidence: 0.88)
- Token cost: 269,225 input · 0 output

## Community Hubs (Navigation)
- Entrenamiento y baselines
- Pre-Entregas (conceptos)
- Informe y guías del proyecto
- README, frontend y Docker
- Limpieza de datos y tests
- API FastAPI
- Frontend JavaScript
- Predictor (inferencia)
- Tests de la API
- Features modos A y B
- Ejemplos guiados
- pyproject (paquete ypf-ds)

## God Nodes (most connected - your core abstractions)
1. `Pre-Entrega 1 — Definición del Problema y Dataset` - 24 edges
2. `Pre-Entrega 2 — EDA y Limpieza de Datos` - 19 edges
3. `Pre-Entrega 3 — Feature Engineering y Modelado Supervisado` - 19 edges
4. `entrenar_modo_a()` - 16 edges
5. `entrenar_modo_b()` - 14 edges
6. `Predictor` - 13 edges
7. `Pipeline de limpieza (clean.py)` - 12 edges
8. `obtener_predictor()` - 11 edges
9. `Pre-Entrega 4 — Modelado No Supervisado (Clustering y SVD)` - 11 edges
10. `Versión 2 — Cuenca Neuquina, petróleo y gas` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Guía para leer el frontend` --semantically_similar_to--> `Sesgos, límites e IA responsable`  [INFERRED] [semantically similar]
  docs/guia_frontend.md → README.md
- `obtener_predictor()` --uses--> `Predictor`  [INFERRED]
  api/model.py → src/ypf_ds/models/predict.py
- `Métricas del modelo (R², WAPE, cobertura)` --conceptually_related_to--> `Resultados en test 2024–2025`  [INFERRED]
  docs/guia_frontend.md → README.md
- `Avisos (recuadros amarillos)` --conceptually_related_to--> `API FastAPI (/health, /metadata, /opciones, /pozos, /predict/existente, /predict/nuevo)`  [INFERRED]
  docs/guia_frontend.md → README.md
- `Guía para leer el frontend` --references--> `Modo A · Pozo existente`  [INFERRED]
  docs/guia_frontend.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Despliegue Docker: api + frontend + train** — compose_prediccion_neuquina, compose_api, compose_frontend, compose_train, requirements_api_dependencias, requirements_entorno_completo [INFERRED 0.85]
- **Salida interpretable de la predicción (bandas, SHAP, cluster, avisos)** — readme_modelos_cuantiles_p10_p90, readme_shap_explicabilidad, readme_clustering_svd_kmeans, docs_guia_frontend_avisos, frontend_index_resultado [INFERRED 0.85]
- **Pipeline de modelado supervisado** — readme_validacion_temporal, readme_lightgbm, readme_optuna, readme_baselines, readme_mlflow_tracking, readme_desigualdad_jensen_log1p [EXTRACTED 1.00]
- **Pipeline end-to-end: ingesta → limpieza → features → modelos → API** — docs_pre_entrega_2_ypf_ingesta_polars_lazy, docs_pre_entrega_2_ypf_limpieza_clean_py, docs_pre_entrega_3_ypf_feature_engineering_build, docs_pre_entrega_3_ypf_cuatro_modelos, docs_pre_entrega_1_ypf_api_fastapi [INFERRED 0.85]
- **Pipeline de clustering: escalado + SVD + K-Means asignado en API** — docs_pre_entrega_4_ypf_representacion_curva_normalizada, docs_pre_entrega_2_ypf_standard_scaler, docs_pre_entrega_4_ypf_truncated_svd, docs_pre_entrega_4_ypf_kmeans_k4, docs_pre_entrega_4_ypf_cluster_en_api [EXTRACTED 1.00]
- **Evaluación LightGBM contra baselines de la industria** — docs_pre_entrega_1_ypf_lightgbm, docs_pre_entrega_1_ypf_baseline_persistencia, docs_pre_entrega_1_ypf_baseline_arps, docs_pre_entrega_3_ypf_resultados_test, docs_pre_entrega_3_ypf_backtest_arps [EXTRACTED 1.00]
- **Pipeline de modelado v2 (limpieza, features, entrenamiento, predicción, API)** — docs_guia_del_proyecto_clean_py, docs_guia_del_proyecto_features_build_py, docs_guia_del_proyecto_train_py, docs_guia_del_proyecto_predict_py, docs_guia_del_proyecto_api_app [INFERRED 0.85]
- **Lectura de resultados de pronóstico en el frontend** — docs_guia_frontend_tarjetas_indicadores, docs_guia_frontend_p10_p50_p90, docs_guia_frontend_shap_que_explica, docs_guia_frontend_cluster_tipo_pozo, docs_guia_frontend_metricas_r2_wape_cobertura [EXTRACTED 1.00]

## Communities (14 total, 5 thin omitted)

### Community 0 - "Entrenamiento y baselines"
Cohesion: 0.05
Nodes (29): a_pandas(), ajustar_arps(), arps(), curva_mediana(), predecir_curva_mediana(), pronostico_arps(), asignar(), describir() (+21 more)

### Community 1 - "Pre-Entregas (conceptos)"
Cohesion: 0.06
Nodes (71): Algoritmos comparados (Ridge, Árbol, KNN, RF, MLP, XGBoost), API FastAPI, Bandas de incertidumbre P10–P90, Baseline: curva de declinación de Arps, Baseline: persistencia (repetir el último mes), Capítulo IV — Pozos (capitulo-iv-pozos.csv), Cuenca Neuquina (alcance del proyecto), Curvas de declinación pronunciadas y heterogéneas (+63 more)

### Community 2 - "Informe y guías del proyecto"
Cohesion: 0.06
Nodes (44): api/app.py, model.py, schemas.py, src/ypf_ds/data/clean.py (limpieza, Capítulo IV, grilla mensual), src/ypf_ds/models/cluster.py (SVD + K-Means), src/ypf_ds/config.py (rutas, umbrales, cortes temporales), CSV de producción no convencional (data/raw), Docker Compose (API + frontend, perfil train), Estructura del código (src/ypf_ds, api, frontend), src/ypf_ds/features/build.py (features modos A y B) (+36 more)

### Community 3 - "README, frontend y Docker"
Cohesion: 0.06
Nodes (40): Servicio api (puerto 8000), Servicio frontend (nginx, puerto 8080), Docker Compose prediccion-neuquina, Servicio train (perfil train), Buscador de pozos (activo / sin producción), GOR (relación gas/petróleo), Guía para leer el frontend, Información técnica (GOR, corte de agua, días efectivos) (+32 more)

### Community 4 - "Limpieza de datos y tests"
Cohesion: 0.09
Nodes (18): construir(), corregir_valores(), filtrar_poblacion(), grilla_mensual(), leer_capitulo_iv(), tabla_pozos(), ultimo_mes_completo(), _ultimo_no_nulo() (+10 more)

### Community 5 - "API FastAPI"
Cohesion: 0.14
Nodes (10): buscar_pozos(), health(), lifespan(), metadata(), opciones(), predecir_existente(), predecir_nuevo(), obtener_predictor() (+2 more)

### Community 6 - "Frontend JavaScript"
Cohesion: 0.21
Nodes (17): cargarOpciones(), COLORES, completarArea(), css(), ejecutar(), fmt(), graficos, iniciar() (+9 more)

### Community 8 - "Tests de la API"
Cohesion: 0.11
Nodes (3): cliente(), test_existente(), test_existente_sin_produccion()

### Community 9 - "Features modos A y B"
Cohesion: 0.18
Nodes (6): agrupar_empresas(), columnas_modelo_a(), dataset_modo_a(), dataset_modo_b(), features_dinamicas(), particion_temporal()

## Knowledge Gaps
- **32 isolated node(s):** `ypf-ds`, `Equipo (Aguilera, Vicentelo, Tapias Díaz)`, `Dataset Secretaría de Energía (Capítulo IV no convencional)`, `Arps hiperbólica`, `Unidades (m³/mes petróleo, Mm³/mes gas)` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 121 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Estructura del código (src/ypf_ds, api, frontend)` connect `Informe y guías del proyecto` to `Entrenamiento y baselines`?**
  _High betweenness centrality (0.263) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Pre-Entrega 1 — Definición del Problema y Dataset` (e.g. with `Pre-Entrega 2 — EDA y Limpieza de Datos` and `Pre-Entrega 3 — Feature Engineering y Modelado Supervisado`) actually correct?**
  _`Pre-Entrega 1 — Definición del Problema y Dataset` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ypf-ds`, `Equipo (Aguilera, Vicentelo, Tapias Díaz)`, `Dataset Secretaría de Energía (Capítulo IV no convencional)` to the rest of the system?**
  _32 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Entrenamiento y baselines` be split into smaller, more focused modules?**
  _Cohesion score 0.05126582278481013 - nodes in this community are weakly interconnected._
- **Why does `Pre-Entrega 4 — Modelado No Supervisado (Clustering y SVD)` connect `Pre-Entregas (conceptos)` to `Entrenamiento y baselines`?**
  _High betweenness centrality (0.258) - this node is a cross-community bridge._
- **Should `Pre-Entregas (conceptos)` be split into smaller, more focused modules?**
  _Cohesion score 0.055533199195171024 - nodes in this community are weakly interconnected._
- **Should `Informe y guías del proyecto` be split into smaller, more focused modules?**
  _Cohesion score 0.06207482993197279 - nodes in this community are weakly interconnected._