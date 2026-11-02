# El proyecto según CRISP-ML(Q)

**Proyecto Data Science — Fundación YPF 2026 · Grupo 10 · Comisión 3**  
Cristian Alejandro Aguilera · Abigail Roxana Vicentelo · Ian Lionel Tapias Díaz

Este documento ordena todo el proyecto con la metodología **CRISP-ML(Q)**. Para cada fase indica qué se hizo, dónde está, qué métricas salieron de los notebooks y qué **riesgos de calidad** encontramos, con su mitigación y la evidencia. Es la misma estructura de la presentación final (`presentacion/`): la banda superior de cada escena marca la fase y el riesgo.

> **En una frase:** predecimos la producción mensual de petróleo y gas de pozos de la Cuenca Neuquina, tanto de pozos que ya producen (modo A) como de pozos que todavía no existen (modo B), con un rango de incertidumbre y una explicación de cada pronóstico, y lo entregamos como un sistema web en Docker.

---

## 1. Qué es CRISP-ML(Q) y por qué lo usamos

CRISP-ML(Q) (*Cross-Industry Standard Process for Machine Learning with Quality assurance*) es la adaptación de CRISP-DM a proyectos de machine learning que terminan en producción. Lo propusieron Studer et al. (2021).

| | CRISP-DM | CRISP-ML(Q) |
|---|---|---|
| Fases | 6: negocio, datos, preparación, modelado, evaluación, despliegue | 6: negocio y datos, preparación, ingeniería del modelo, evaluación, despliegue, **monitoreo y mantenimiento** |
| Comprensión del negocio y de los datos | Dos fases separadas | Una sola fase, porque la factibilidad depende de los datos disponibles |
| Calidad | No tiene un método explícito | En **cada fase**: identificar riesgos, mitigarlos y dejar evidencia |
| Después del despliegue | Termina | El modelo envejece: hay que monitorearlo y reentrenarlo |

**Por qué conviene en este proyecto:**

1. **Llega a producción.** Hay una API (FastAPI), una web y todo corre en Docker. CRISP-DM no cubre lo que pasa después del despliegue.
2. **Los problemas que resolvimos son riesgos de calidad.** Fuga de datos, sesgo del target, métricas infladas y consumo de memoria tienen un riesgo, una mitigación y evidencia: un test, una métrica o un commit.
3. **Muestra lo que falta.** La fase 6 (monitoreo) es la que todavía no implementamos. CRISP-ML(Q) obliga a decirlo y a planificarla.

---

## 2. Fase 1 · Comprensión del negocio y de los datos

**Objetivo.** Saber cuánto va a producir un pozo. Un pozo de shale pierde más de la mitad de su producción en el primer año (el pozo de ejemplo YPF.Nq.LLL-1577(h) cae 59,5 % en los 12 meses después del pico). Sin anticipar esa caída se planifican mal la perforación, las instalaciones, el transporte y las reservas.

**Criterio de éxito, definido antes de modelar:** superar en R² y en error (WAPE) a dos referencias:
- **Persistencia:** repetir el último mes.
- **Curva de Arps:** el método clásico de la industria.

**Datos.** Producción mensual por pozo de la Secretaría de Energía (no convencional), desde 2006.

| Dato (notebook 01) | Valor |
|---|---|
| CSV crudo | 421.046 filas × 40 columnas |
| Cuenca Neuquina | 404.037 filas (96 %), 4.862 pozos |
| Profundidad máxima informada | 378.939 m (error de carga) |
| Filas con profundidad 0 | 5.738 (1,4 %) |
| Filas con más días de producción que el mes | 15 |
| Filas con producción negativa | 2 (gas) |
| Filas con latitud y longitud invertidas | 68 (un pozo) |
| Pozos con meses sin registro | 703 |
| Outliers de profundidad por IQR | límites 204–7.540 m, 1.324 filas (0,3 %) |

**Hallazgo que definió el proyecto:** el GOR (gas por m³ de petróleo) por pozo es **bimodal**. Hay dos poblaciones: petróleo y gas.

**Riesgos de calidad**

| Riesgo | Mitigación | Evidencia |
|---|---|---|
| Mezclar cuencas con otra geología y muy pocos pozos | Modelo especializado solo en Neuquina | `src/ypf_ds/data/clean.py`, notebook 01 |
| Errores de carga en el dato crudo | Reglas de limpieza explícitas (fase 2) | Notebook 01 §2, README §2 |
| Tratar petróleo y gas como un solo problema | Modelos separados por fluido; corte GOR = 3.000 m³/m³ | Notebook 01 §5; quedan 2.708 pozos de petróleo y 1.974 de gas |

---

## 3. Fase 2 · Preparación de los datos

**Qué se hizo** (`src/ypf_ds/data/clean.py`, `src/ypf_ds/features/build.py`, notebook 02):

| Regla | Antes | Después |
|---|---|---|
| Producción negativa | 2 | 0 |
| `tef` mayor que los días del mes | 15 | 0 |
| Profundidad nula o imposible (fuera de 300–8.000 m) | 5.890 | 0 (se imputa por pozo → formación y yacimiento → formación) |
| Coordenadas invertidas | 68 | 0 |
| Duplicados pozo-mes | 0 | 0 |

- **Resultado:** panel de **382.992 filas y 4.682 pozos** productores. Corre en ~2 segundos con Polars.
- **Grilla mensual continua:** cada pozo tiene todos sus meses. Se reconstruyeron **566** meses, para que "el mes anterior" sea siempre el mes calendario anterior.
- **Censura:** 57 pozos ya producían al inicio del registro. Se excluyen del modo B y del clustering.

**Ingeniería de variables**

| Grupo | Modo A (pozo existente) | Modo B (pozo nuevo) |
|---|---|---|
| Historia de producción: rezagos 1, 2, 3, 6 y 12 meses y medias móviles de petróleo, gas y agua | 24 | — |
| Ciclo de vida: pico, fracción del pico, acumulada, caudal y meses desde el pico | 9 | — |
| Estado operativo: días efectivos, tendencia de 3 meses, GOR, corte de agua y meses sin producción | 6 | — |
| Atributos del pozo: formación, subtipo, área y empresa; en A también fluido, extracción y estado; en B, tipo de pozo | 7 | 5 |
| Ubicación, profundidad y año de inicio | 4 | 4 |
| Mes de vida, mes calendario y horizonte | 3 | 1 |
| **Total** | **53** | **10** |

**Padrón Capítulo IV** (notebook 02). Agregaba días de perforación, días de terminación y cota, con 98,3 %, 98,3 % y 96,4 % de cobertura. Correlacionan con la acumulada de 12 meses (0,386, 0,370 y −0,155), pero menos que la profundidad (0,734) o el año de inicio (0,599), y **no mejoraron la validación** del modo B. No se usa.

**Riesgos de calidad**

| Riesgo | Mitigación | Evidencia |
|---|---|---|
| Meses faltantes que rompen los rezagos | Grilla mensual continua | `test_grilla_continua` |
| **Fuga de datos** en las variables | Todas las variables dinámicas usan solo datos hasta el mes t (`shift` y `rolling` hacia atrás) | `test_features_sin_fuga`, `test_target_es_futuro`; en una iteración anterior se corrigió una fuga en `ratio_gas_petroleo` (commit `c9a2479`) |
| Errores de carga que vuelven | Chequeos automáticos sobre el panel limpio | `test_sin_negativos_ni_duplicados`, `test_tef_acotado`, `test_pozos_validos` |
| Sumar datos que no aportan | El Capítulo IV solo se usa si mejora la validación | `test_capitulo_iv`, notebook 02 |

---

## 4. Fase 3 · Ingeniería del modelo

**Planteo.** Dos preguntas distintas exigen dos modos, y cada modo va por fluido: **4 modelos LightGBM**.
- **Modo A:** desde un mes t con historia, predice t+1 … t+12. El horizonte es una variable, así que un solo modelo da toda la curva.
- **Modo B:** con lo que se sabe antes de perforar, predice los meses 1 a 24 de vida.

**Validación sin mirar el futuro.** Entrenamiento hasta 2022, validación en 2023 (para Optuna) y test 2024–2025, usado una sola vez. En el modo B el corte es por año de inicio, así que los pozos de test nunca se vieron.

**Comparación de algoritmos** (notebook 03 §1, misma muestra de petróleo):

| Modelo | MAE | RMSE | R² | WAPE | Tiempo (s) |
|---|---|---|---|---|---|
| Random Forest | 242,3 | 584,4 | **0,731** | 0,381 | 49,3 |
| KNN (k = 25) | 249,3 | 588,2 | 0,728 | 0,392 | 1,8 |
| Árbol de decisión | 253,3 | 634,8 | 0,683 | 0,399 | 2,5 |
| **LightGBM** | 254,6 | 610,3 | 0,707 | 0,401 | 7,2 |
| MLP | 262,1 | 617,0 | 0,700 | 0,413 | 3,1 |
| XGBoost | 262,3 | 625,8 | 0,692 | 0,413 | 4,0 |
| Ridge | 267,3 | 650,5 | 0,667 | 0,421 | 0,1 |
| Persistencia (referencia) | 335,8 | 844,3 | 0,439 | 0,528 | — |

**Por qué LightGBM y no Random Forest.** La diferencia de R² es chica (0,707 contra 0,731), pero LightGBM:
- entrena unas 7 veces más rápido, lo que permite usar 1,6 millones de filas;
- maneja categorías y nulos de forma nativa;
- admite pesos y regresión por cuantiles, que usamos para las bandas P10–P90.

**Elección del target** (notebook 03 §2):

| Target | MAE | RMSE | R² | WAPE | Sesgo (pronóstico / real) |
|---|---|---|---|---|---|
| `log1p` | 254,6 | 610,3 | 0,707 | 0,401 | **0,812** |
| Ratio ponderado por volumen | 218,1 | 544,0 | 0,767 | 0,343 | **1,005** |

En escala log el modelo estima la mediana, no el volumen total, y subestimaba la producción ~19 %.

**Validación cruzada temporal** (5 folds con ventana creciente): R² **0,788 ± 0,024**, WAPE 0,344 ± 0,016.

| Fold | Valida desde | Hasta | Filas de train | R² | WAPE |
|---|---|---|---|---|---|
| 1 | 2016-11 | 2019-02 | 29.996 | 0,777 | 0,349 |
| 2 | 2019-02 | 2020-11 | 59.988 | 0,763 | 0,370 |
| 3 | 2020-11 | 2022-05 | 89.980 | 0,813 | 0,331 |
| 4 | 2022-05 | 2023-08 | 119.972 | 0,816 | 0,333 |
| 5 | 2023-08 | 2026-07 | 149.964 | 0,773 | 0,338 |

**Hiperparámetros: Optuna contra GridSearch** (notebook 03 §4):

| Método | RMSE de validación (log) | Tiempo |
|---|---|---|
| GridSearch | 1,18899 | 83,8 s |
| Optuna (TPE) | **1,18698** | **78,5 s** |

**Riesgos de calidad**

| Riesgo | Mitigación | Evidencia |
|---|---|---|
| Métricas infladas por mezclar el futuro | Corte temporal y validación cruzada temporal | Notebook 03 §3: R² estable entre folds (± 0,024) |
| **Sesgo del target** en log (0,812) | Ratio ponderado por volumen (1,005) | Notebook 03 §2 |
| Elegir el modelo solo por una métrica | Comparación en 5 métricas y tiempo, contra una referencia | Notebook 03 §1 |
| Hiperparámetros sobreajustados al test | Optuna busca solo sobre validación 2023 | Notebook 03 §4 |

---

## 5. Fase 4 · Evaluación

**Test 2024–2025, modo A** (notebook 03 §5):

| Modelo | MAE | RMSE | R² | WAPE |
|---|---|---|---|---|
| Petróleo · LightGBM | 216,0 | 540,1 | **0,728** | 0,371 |
| Petróleo · persistencia | 364,0 | 898,5 | 0,246 | 0,625 |
| Gas · LightGBM | 266,6 | 837,9 | **0,770** | 0,380 |
| Gas · persistencia | 377,5 | 1.191,3 | 0,536 | 0,539 |

- **Residuos:** media −8,8 m³ y mediana −0,2 m³, sin sesgo sistemático.
- **R² por horizonte:** petróleo 0,889 → 0,745 → 0,658 → 0,630 (h = 1, 3, 6, 12); gas 0,882 → 0,793 → 0,755 → 0,721. La persistencia cae a −0,84 en petróleo a 12 meses.
- **Comparación con la versión anterior:** el R² "bajó" de 0,907 a 0,73, pero miden cosas distintas. Con el mismo alcance (solo el mes siguiente) da **0,906**, equivalente. La versión actual pronostica hasta 12 meses.
- **Contra Arps** (backtest con origen dic-2023, 2.291 pozos, acumulada de 12 meses): WAPE del modelo 35,7 % contra 58,3 % de Arps.

**Por categoría de producción** (terciles):

| Fluido | Accuracy | F1 baja | F1 media | F1 alta |
|---|---|---|---|---|
| Petróleo | 0,844 | 0,867 | 0,789 | 0,876 |
| Gas | 0,792 | 0,783 | 0,743 | 0,852 |

**Por formación** (petróleo, R²): Agrio 0,842 · Punta Rosada 0,793 · Lajas 0,778 · Quintuco 0,772 · **Vaca Muerta 0,687** (494.347 filas) · Los Molles 0,572 · Basamento 0,369 · Mulichinco 0,257 · Precuyo 0,236.

**Modo B: pozos nuevos** (729 pozos de test, acumulada de 12 meses):

| Fluido | LightGBM R² | WAPE | Curva mediana R² | WAPE |
|---|---|---|---|---|
| Petróleo | **0,448** | 0,309 | −0,282 | 0,505 |
| Gas | **0,860** | 0,282 | 0,724 | 0,411 |

El fluido dominante de un pozo nuevo se acierta en el **99,6 %** de los casos.

**Incertidumbre: cobertura de la banda P10–P90** (esperada 80 %):

| Modelo | Cobertura en test |
|---|---|
| Petróleo existente | 80,8 % |
| Gas existente | 79,0 % |
| Petróleo nuevo | 74,2 % |
| Gas nuevo | 73,2 % |

**Clustering: tipos de pozo** (notebook 04). SVD a 6 componentes (85,5 % de la varianza) y K-Means.

| k | Silhouette | Davies-Bouldin | Calinski-Harabasz |
|---|---|---|---|
| 2 | 0,246 | 1,510 | 1.547 |
| 3 | 0,214 | 1,528 | 1.316 |
| **4** | **0,221** | **1,426** | 1.207 |
| 5 | 0,198 | 1,471 | 1.107 |
| 6–10 | 0,178–0,201 | 1,366–1,402 | 844–1.047 |

Elegimos **k = 4**:
- k = 2 tiene la silhouette más alta, pero dos grupos no describen tipos de pozo.
- Entre 3 y 10 grupos, k = 4 tiene la mejor silhouette y el mejor Davies-Bouldin hasta k = 5.

Los cuatro grupos son:
- petróleo, pico alto, declinación fuerte (1.621 pozos);
- petróleo, pico medio, declinación suave (1.300);
- petróleo, pico bajo, declinación fuerte (529);
- gas, declinación suave (694).

DBSCAN dejaba entre el 23,4 % y el 84,4 % de los pozos como ruido. El 7,1 % de los pozos tiene silhouette negativa: es una estructura débil y continua.

**Explicabilidad** (notebook 05). TreeSHAP muestra qué empujó cada pronóstico. La variable que más pesa es la relación entre la producción actual y el pico: el modelo aprendió que un pozo que ya pasó su pico sigue declinando.

**Riesgos de calidad**

| Riesgo | Mitigación | Evidencia |
|---|---|---|
| Comparar métricas de distinto alcance | Medir con el mismo alcance que la versión anterior | 0,906 contra 0,907 |
| Modelo que no supera lo simple | Comparar contra persistencia y Arps | R² 0,630 contra −0,84 a 12 meses; WAPE 35,7 % contra 58,3 % |
| Buen promedio que esconde segmentos malos | Métricas por formación y por categoría | Notebook 03 §5 |
| Intervalos demasiado seguros | Medir y reportar la cobertura | 73–74 % en pozos nuevos, informado como límite |
| Grupos forzados en curvas continuas | Varias métricas internas y reporte de silhouette baja | Notebook 04 §2 y §5 |
| Modelo de caja negra | SHAP en cada predicción, también en la API | Notebook 05; `pred_contrib` en `src/ypf_ds/models/predict.py` |

---

## 6. Fase 5 · Despliegue

**Arquitectura:**

```text
CSV público
  → limpieza con Polars
  → 4 modelos LightGBM
  → API FastAPI (api/)
  → web (frontend/)
```

Todo corre en Docker con `docker compose up -d`. La presentación se sirve en el puerto 8090.

**Devolución del profesor y respuesta:**

| Pedido | Qué se hizo | Evidencia |
|---|---|---|
| Cuidar la memoria | Se midió: los modelos pesan 7,4 MB y no eran la causa. Cada worker de uvicorn duplicaba modelos y datos. Con 1 worker y Polars con 2 hilos la RAM bajó de **921 MB a 336 MB**, y cada pronóstico tarda ~35 ms. | Commit `010deb9`, README "Consumo de memoria" |
| Validar coordenadas | La API rechaza ubicaciones fuera de la Cuenca Neuquina y avisa si el pozo queda lejos del área elegida | PR #11, `test_nuevo_fuera_de_la_cuenca`, `test_nuevo_lejos_del_area` |

**Riesgos de calidad**

| Riesgo | Mitigación | Evidencia |
|---|---|---|
| Consumo de memoria del servicio | 1 worker y tope de 1 GB en `compose.yaml` | 921 → 336 MB |
| Entradas inválidas | Validación de rangos y coordenadas | 28 tests (`tests/test_api.py`, `tests/test_datos.py`) |
| Pozos sin producción que rompían la pantalla | Aviso en lugar de error | `test_existente_sin_produccion` |
| Que el usuario no sepa leer el resultado | Pestaña "Métricas del modelo" y guías "Cómo leer este gráfico" | `docs/guia_frontend.md` |

---

## 7. Fase 6 · Monitoreo y mantenimiento

Es la fase que **todavía no está implementada**. Hoy existe un chequeo de salud (`/health` y `HEALTHCHECK` de Docker), un tope de memoria y los tests. Falta monitorear el modelo en sí.

| Límite o riesgo | Por qué importa | Próximo paso |
|---|---|---|
| Deriva de los datos | La tecnología de perforación cambia cada año: un modelo entrenado hasta 2025 envejece | Reentrenar con cada publicación de la Secretaría y vigilar el WAPE mes a mes contra lo real |
| Banda angosta en pozos nuevos | Cobertura de 73–74 % contra el 80 % esperado | Recalibrar los cuantiles, por ejemplo con predicción conformal |
| Faltan datos de fractura | Etapas, arena y largo de rama no son públicos; limitan el modo B de petróleo (R² 0,45) | Sumar el padrón de fractura si se publica |
| Formaciones con peor ajuste | Precuyo (0,24) y Mulichinco (0,26) contra 0,69 en Vaca Muerta | Avisar en la web cuando el pronóstico es menos confiable |

---

## 8. Resumen de riesgos y mitigaciones

| Fase | Riesgo | Mitigación |
|---|---|---|
| 1 | Mezclar cuencas | Solo Neuquina |
| 1 | Dos fluidos en un modelo | Petróleo y gas por separado (GOR 3.000) |
| 2 | Errores de carga | Reglas de limpieza con tests |
| 2 | Rezagos rotos por meses faltantes | Grilla mensual continua (566 meses) |
| 2 | Fuga de datos | Solo historia hasta t; `test_features_sin_fuga` |
| 3 | Métricas infladas | Corte temporal; CV temporal R² 0,788 ± 0,024 |
| 3 | Sesgo del target | Ratio ponderado: 0,812 → 1,005 |
| 4 | Comparación injusta con la versión anterior | Mismo alcance: 0,906 |
| 4 | No superar lo simple | Persistencia y Arps como referencia |
| 4 | Intervalos sobreconfiados | Cobertura medida: 73–81 % |
| 4 | Caja negra | SHAP por predicción |
| 5 | Memoria | 921 → 336 MB |
| 5 | Coordenadas inválidas | Validación en la API |
| 6 | Deriva y envejecimiento | Pendiente: reentrenar y monitorear |

---

## Referencia

Studer, S., Bui, T. B., Drescher, C., Hanuschkin, A., Winkler, L., Peters, S. y Müller, K.-R. (2021). *Towards CRISP-ML(Q): A Machine Learning Process Model with Quality Assurance Methodology*. Machine Learning and Knowledge Extraction, 3(2), 392–413. https://doi.org/10.3390/make3020020

Las métricas de este documento salen de las salidas ejecutadas de `notebooks/01` a `05` y de `models/metadata.json`. `presentacion/generar_datos.py` verifica que sigan coincidiendo con los notebooks.
