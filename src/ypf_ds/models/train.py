"""Entrenamiento de los modelos finales (petróleo y gas, modos A y B) con LightGBM.

Para cada combinación:
1. Optuna busca hiperparámetros entrenando con train (<= 2022) y midiendo en valid (2023).
   El modelo puntual minimiza el error cuadrático en volumen (m3 / Mm3), que es lo que se reporta:
   - Modo A: target = q[t+h] / q[t] (ratio de declinación) con peso q[t]^2  <=>  (q[t+h] - q[t]·ratio)^2.
   - Modo B: target = q en escala original; Optuna elige el objetivo (L2, Poisson o Tweedie).
   Modelar en log y volver con expm1 subestima la media (desigualdad de Jensen): se probó y daba
   un sesgo de -25%.
2. Se reentrena con train + valid y se evalúa en test (2024-2025) contra los baselines.
3. Se entrenan modelos de cuantiles P10 / P90 para la banda de incertidumbre.
4. Se reentrena con todos los datos y se guardan los artefactos que usa la API.

Uso: python -m ypf_ds.models.train [--trials 25] [--sin-mlflow]
"""

import argparse
import datetime as dt
import json
import re
import warnings

import joblib
import lightgbm as lgb
import numpy as np
import optuna
import polars as pl

from ypf_ds import config
from ypf_ds.features import build as fb
from ypf_ds.models import baselines as bl
from ypf_ds.models import evaluate as ev
from ypf_ds.models.cluster import entrenar_clustering
from ypf_ds.models.predict import predecir_a, predecir_b

MAX_FILAS_FIT = 1_200_000
MAX_FILAS_OPTUNA = 400_000
RATIO_MAX = 10.0  # recorte de ratios absurdos cuando el mes de origen tiene producción ínfima
FECHA_ORIGEN_BACKTEST = dt.date(2023, 12, 1)
warnings.filterwarnings("ignore", category=UserWarning)


def _muestra(n: int, maximo: int, semilla=config.SEMILLA) -> np.ndarray:
    idx = np.arange(n)
    if n <= maximo:
        return idx
    return np.sort(np.random.default_rng(semilla).choice(idx, maximo, replace=False))


def _parametros_base(objetivo="regression", alpha=None) -> dict:
    p = {"objective": objetivo, "verbosity": -1, "random_state": config.SEMILLA, "n_jobs": -1}
    if alpha is not None:
        p["alpha"] = alpha
    return p


def optimizar(X_tr, y_tr, X_va, y_va, n_trials: int, w_tr=None, w_va=None,
              objetivos=("regression",)) -> dict:
    """Búsqueda bayesiana (TPE) de hiperparámetros con early stopping sobre la validación temporal.

    La métrica es el RMSE (ponderado si hay pesos) en la escala del target puntual.
    """
    w_va_ = np.ones(len(y_va)) if w_va is None else w_va

    def objetivo(trial):
        params = _parametros_base(trial.suggest_categorical("objective", list(objetivos))) | {
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 255, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 500, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "subsample_freq": 1,
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10, log=True),
            "n_estimators": 2000,
        }
        m = lgb.LGBMRegressor(**params)
        m.fit(X_tr, y_tr, sample_weight=w_tr, eval_set=[(X_va, y_va)], eval_sample_weight=[w_va_],
              eval_metric="l2", callbacks=[lgb.early_stopping(50, verbose=False, first_metric_only=True)])
        trial.set_user_attr("n_estimators", int(m.best_iteration_ or params["n_estimators"]))
        return float(np.sqrt(np.average((m.predict(X_va) - y_va) ** 2, weights=w_va_)))

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    estudio = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=config.SEMILLA))
    estudio.optimize(objetivo, n_trials=n_trials)
    mejor = estudio.best_trial
    return mejor.params | {"subsample_freq": 1, "n_estimators": mejor.user_attrs["n_estimators"],
                           "rmse_valid": mejor.value}


def ajustar(X, y, params: dict, objetivo=None, alpha=None, peso=None) -> lgb.LGBMRegressor:
    objetivo = objetivo or params.get("objective", "regression")
    p = _parametros_base(objetivo, alpha) | {k: v for k, v in params.items() if k not in ("rmse_valid", "objective")}
    idx = _muestra(len(y), MAX_FILAS_FIT)
    return lgb.LGBMRegressor(**p).fit(X.iloc[idx], y[idx], sample_weight=None if peso is None else peso[idx])


def ajustar_trio(X, y_puntual, y_log, params, peso=None) -> dict:
    """Modelo puntual (media, en volumen) y cuantiles P10 / P90 (en escala log: los cuantiles
    son invariantes a transformaciones monótonas, así que expm1 del cuantil log es el cuantil real)."""
    return {"p50": ajustar(X, y_puntual, params, peso=peso),
            "p10": ajustar(X, y_log, params, "quantile", 0.1),
            "p90": ajustar(X, y_log, params, "quantile", 0.9)}


# ---------------------------------------------------------------- Modo A: pozo existente

def entrenar_modo_a(panel, pozos, fluido, n_trials) -> tuple[dict, dict]:
    df = fb.dataset_modo_a(panel, pozos, fluido)
    columnas = fb.columnas_modelo_a(df)
    part = fb.particion_temporal(df["fecha_obj"])
    X, categorias = fb.a_pandas(df, columnas, fb.CATEGORICAS_A)
    y = df["y"].to_numpy()
    base = df["prod_origen"].to_numpy()
    real = df["prod_obj"].to_numpy()
    ratio, peso = np.minimum(real / base, RATIO_MAX), base ** 2

    tr, va, te = (part == "train"), (part == "valid"), (part == "test")
    i_tr = np.flatnonzero(tr)[_muestra(tr.sum(), MAX_FILAS_OPTUNA)]
    i_va = np.flatnonzero(va)[_muestra(va.sum(), MAX_FILAS_OPTUNA // 2)]
    params = optimizar(X.iloc[i_tr], ratio[i_tr], X.iloc[i_va], ratio[i_va], n_trials, peso[i_tr], peso[i_va])

    entrena = tr | va
    trio = ajustar_trio(X[entrena], ratio[entrena], y[entrena], params, peso[entrena])
    pred = predecir_a(trio, X[te], base[te])

    lag1 = "log_pet_l1" if fluido == "petroleo" else "log_gas_l1"
    eval_df = df.filter(pl.Series(te)).select("idpozo", "horizonte", lag1).to_pandas()
    eval_df["real"], eval_df["pred"], eval_df["persistencia"] = real[te], pred["p50"], base[te]
    # Alcance del proyecto anterior: 1 mes adelante y pozos con producción en t y t-1
    anterior = eval_df[(eval_df.horizonte == 1) & (eval_df[lag1] > 0)]
    metricas = {
        "modelo": ev.metricas(real[te], pred["p50"]),
        "persistencia": ev.metricas(real[te], base[te]),
        "cobertura_p10_p90": ev.cobertura(real[te], pred["p10"], pred["p90"]),
        "por_horizonte": {
            int(h): {"modelo": ev.metricas(d.real, d.pred), "persistencia": ev.metricas(d.real, d.persistencia)}
            for h, d in eval_df.groupby("horizonte")
        },
        "alcance_proyecto_anterior": {"modelo": ev.metricas(anterior.real, anterior.pred),
                                      "persistencia": ev.metricas(anterior.real, anterior.persistencia)},
        "backtest_origen_2023_12": backtest_fijo(panel, df, X, trio, fluido),
    }
    metricas = ev.redondear(metricas)
    print(f"[A-{fluido}] test modelo={metricas['modelo']} | persistencia={metricas['persistencia']}")

    final = ajustar_trio(X, ratio, y, params, peso)
    artefacto = {"modelos": final, "columnas": columnas, "categoricas": fb.CATEGORICAS_A,
                 "categorias": categorias, "fluido": fluido}
    return artefacto, {"parametros": params, "metricas_test": metricas,
                       "filas": {"train": int(tr.sum()), "valid": int(va.sum()), "test": int(te.sum())}}


def backtest_fijo(panel, df, X, trio, fluido) -> dict:
    """Pronóstico a 12 meses desde 2023-12 para todos los pozos activos: modelo vs Arps vs persistencia."""
    col = fb.FLUIDOS[fluido]
    mask = (df["fecha"] == FECHA_ORIGEN_BACKTEST).to_numpy()
    sub = df.filter(pl.Series(mask))
    pred = predecir_a(trio, X[mask], sub["prod_origen"].to_numpy())["p50"]
    historias = {k: v[col].to_numpy() for (k,), v in
                 panel.filter(pl.col("fecha") <= FECHA_ORIGEN_BACKTEST).sort("fecha").group_by("idpozo")}
    arps = np.empty(sub.height)
    for pozo, filas in sub.with_row_index("_i").group_by("idpozo"):
        hs = filas["horizonte"].to_numpy()
        arps[filas["_i"].to_numpy()] = bl.pronostico_arps(historias[pozo[0]], hs)
    real = sub["prod_obj"].to_numpy()
    return {"pozos": int(sub["idpozo"].n_unique()),
            "modelo": ev.metricas(real, pred), "arps": ev.metricas(real, arps),
            "persistencia": ev.metricas(real, sub["prod_origen"].to_numpy())}


# ---------------------------------------------------------------- Modo B: pozo nuevo

def entrenar_modo_b(panel, pozos, fluido, n_trials) -> tuple[dict, dict]:
    df = fb.dataset_modo_b(panel, pozos, fluido)
    anio = df["anio_inicio"].to_numpy()
    part = np.select([anio <= 2022, anio == 2023, anio <= 2025], ["train", "valid", "test"], "fuera")
    y = df["y"].to_numpy()
    real = df["prod_obj"].to_numpy()
    tr, va, te = (part == "train"), (part == "valid"), (part == "test")

    # Selección de variables por validación 2023 (nunca mirando el test):
    # base vs base + datos de perforación/terminación del Capítulo IV
    candidatos = {"base": fb.FEATURES_B}
    if df["dias_term"].is_not_null().mean() > 0.5:
        candidatos["base+capitulo_iv"] = fb.FEATURES_B + fb.FEATURES_C4
    busquedas = {}
    for nombre, cols in candidatos.items():
        Xc, _ = fb.a_pandas(df, cols, fb.CATEGORICAS_B)
        busquedas[nombre] = optimizar(Xc[tr], real[tr], Xc[va], real[va], n_trials,
                                      objetivos=("regression", "poisson", "tweedie"))
    elegido = min(busquedas, key=lambda k: busquedas[k]["rmse_valid"])
    columnas, params = candidatos[elegido], busquedas[elegido]
    seleccion = {"elegido": elegido, "rmse_valid": {k: round(v["rmse_valid"], 3) for k, v in busquedas.items()}}
    print(f"[B-{fluido}] variables: {seleccion}")
    X, categorias = fb.a_pandas(df, columnas, fb.CATEGORICAS_B)
    entrena = tr | va
    trio = ajustar_trio(X[entrena], real[entrena], y[entrena], params)
    pred = predecir_b(trio, X[te])
    tabla_base = bl.curva_mediana(df.filter(pl.Series(entrena)))
    base = bl.predecir_curva_mediana(tabla_base, df.filter(pl.Series(te)))

    # Acumulada 12 meses por pozo (solo pozos de test con sus 12 primeros meses informados)
    ev_df = df.filter(pl.Series(te)).select("idpozo", "mes_produccion").to_pandas()
    ev_df["real"], ev_df["pred"], ev_df["base"] = real[te], pred["p50"], base
    m12 = ev_df[ev_df.mes_produccion <= 12]
    completos = m12.groupby("idpozo").filter(lambda d: len(d) == 12)
    acum = completos.groupby("idpozo")[["real", "pred", "base"]].sum()
    metricas = ev.redondear({
        "mensual": {"modelo": ev.metricas(real[te], pred["p50"]), "curva_mediana": ev.metricas(real[te], base)},
        "acum_12m": {"pozos": int(len(acum)), "modelo": ev.metricas(acum.real, acum.pred),
                     "curva_mediana": ev.metricas(acum.real, acum.base)},
        "cobertura_p10_p90": ev.cobertura(real[te], pred["p10"], pred["p90"]),
        "seleccion_variables": seleccion,
    })
    print(f"[B-{fluido}] acum12 modelo={metricas['acum_12m']['modelo']} | "
          f"mediana={metricas['acum_12m']['curva_mediana']}")

    final = ajustar_trio(X, real, y, params)
    artefacto = {"modelos": final, "columnas": columnas, "categoricas": fb.CATEGORICAS_B,
                 "categorias": categorias, "fluido": fluido}
    return artefacto, {"parametros": params, "metricas_test": metricas,
                       "filas": {"train": int(tr.sum()), "valid": int(va.sum()), "test": int(te.sum())}}


# ---------------------------------------------------------------- Orquestación

def opciones_formulario(pozos: pl.DataFrame) -> dict:
    p = fb.agrupar_empresas(pozos)
    # Valores típicos por área para prellenar el formulario: se priorizan los pozos recientes (>= 2020),
    # que reflejan la práctica actual de perforación y terminación
    reciente = pl.col("anio_inicio") >= 2020
    tipico = lambda c: pl.coalesce(pl.col(c).filter(reciente).median(), pl.col(c).median())
    areas = (p.group_by("areayacimiento").agg(
        lat=pl.col("lat").median(), lon=pl.col("lon").median(), profundidad=tipico("profundidad"),
        dias_perf=tipico("dias_perf"), dias_term=tipico("dias_term"),
        horizontal=pl.coalesce(pl.col("es_horizontal").filter(reciente).mean(),
                               pl.col("es_horizontal").mean()) >= 0.5,
        n=pl.len()).sort("areayacimiento"))
    return {
        "formacion": p["formacion"].value_counts().sort("count", descending=True)["formacion"].to_list(),
        "sub_tipo_recurso": sorted(p["sub_tipo_recurso"].drop_nulls().unique().to_list()),
        "tipopozo": sorted(p["tipopozo"].drop_nulls().unique().to_list()),
        "empresa": p["empresa"].value_counts().sort("count", descending=True)["empresa"].to_list(),
        "areas": areas.to_dicts(),
        "rangos": {"profundidad": [float(p["profundidad"].min()), float(p["profundidad"].max())],
                   "lat": [float(p["lat"].min()), float(p["lat"].max())],
                   "lon": [float(p["lon"].min()), float(p["lon"].max())],
                   "anio_inicio": [int(p["anio_inicio"].min()), int(p["anio_inicio"].max())],
                   "dias_perf": [0.0, float(p["dias_perf"].max())],
                   "dias_term": [0.0, float(p["dias_term"].max())]},
    }


def main(n_trials: int = 25, usar_mlflow: bool = True):
    panel, pozos = pl.read_parquet(config.PANEL), pl.read_parquet(config.POZOS)
    config.DIR_MODELOS.mkdir(exist_ok=True)
    meta = {"version": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "datos_hasta": str(panel["fecha"].max()),
            "unidades": {"petroleo": "m3/mes", "gas": "Mm3/mes (miles de m3)"},
            "cortes": {"train": f"<= {config.FIN_TRAIN}", "valid": "2023", "test": "2024-2025"},
            "modelos": {}}

    if usar_mlflow:
        import mlflow
        mlflow.set_tracking_uri(f"sqlite:///{config.RAIZ / 'mlflow.db'}")
        mlflow.set_experiment("produccion_neuquina")

    for modo, fn in [("existente", entrenar_modo_a), ("nuevo", entrenar_modo_b)]:
        for fluido in fb.FLUIDOS:
            nombre = f"{fluido}_{modo}"
            artefacto, info = fn(panel, pozos, fluido, n_trials)
            joblib.dump(artefacto, config.DIR_MODELOS / f"{nombre}.joblib", compress=3)
            meta["modelos"][nombre] = info
            if usar_mlflow:
                with mlflow.start_run(run_name=nombre):
                    mlflow.log_params({k: v for k, v in info["parametros"].items()})
                    plano = pl.json_normalize([info["metricas_test"]], separator=".").row(0, named=True)
                    # MLflow solo acepta letras, números, _ - . / y espacios en los nombres
                    mlflow.log_metrics({re.sub(r"[^\w\-./ ]", "_", k): v for k, v in plano.items()
                                        if isinstance(v, (int, float)) and not isinstance(v, bool)})

    meta["clustering"] = entrenar_clustering(panel, pozos)
    meta["opciones"] = opciones_formulario(pozos)
    meta["opciones"]["usa_capitulo_iv"] = any(
        info["metricas_test"].get("seleccion_variables", {}).get("elegido") == "base+capitulo_iv"
        for info in meta["modelos"].values())
    (config.DIR_MODELOS / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print("Artefactos guardados en", config.DIR_MODELOS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=25)
    ap.add_argument("--sin-mlflow", action="store_true")
    a = ap.parse_args()
    main(a.trials, not a.sin_mlflow)
