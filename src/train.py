"""
Entrena el modelo final y guarda todo lo que necesita la API en models/.

El modelo es un LightGBM que predice la VARIACION de produccion de petroleo
respecto del mes anterior (iteracion 8 del notebook 03). La produccion
final se obtiene sumando esa variacion al mes anterior (ver src/predict.py).

Uso, desde la raiz del proyecto:
    python -m src.train                       # usa los parametros de Optuna si existen
    python -m src.train --parametros base     # usa los parametros base

Necesita data/processed/produccion_con_features.csv (lo genera el notebook 02, que
tambien calcula las variables del mes anterior que usa el modelo).
"""
import argparse
import json
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

RUTA_DATOS = os.environ.get("DATA_PATH", "data/processed/produccion_con_features.csv")
CARPETA_MODELOS = os.environ.get("MODELS_DIR", "models")
ANIO_CORTE = 2024

COLUMNAS_FEATURES = [
    "antiguedad_meses",
    "prod_pet_mes_anterior",
    "prod_gas_mes_anterior",
    "declinacion_pet_anterior",
    "ratio_gas_petroleo_anterior",
    "profundidad",
    "formacion_cod",
    "cuenca_cod",
]

PARAMETROS_BASE = {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1}


def cargar_parametros(tipo):
    # Si piden los de Optuna y el archivo existe, los usamos; si no, los base
    ruta = os.path.join(CARPETA_MODELOS, "mejores_parametros_optuna.json")
    if tipo == "optuna" and os.path.exists(ruta):
        with open(ruta) as archivo:
            return "optuna", json.load(archivo)
    if tipo == "optuna":
        print("AVISO: no existe", ruta, "-> se usan los parametros base")
    return "base", dict(PARAMETROS_BASE)


def preparar_datos():
    df = pd.read_csv(RUTA_DATOS)
    df = df.sort_values(["idpozo", "anio", "mes"]).reset_index(drop=True)

    # El CSV tiene que venir del notebook 02 actualizado (meses de calendario)
    faltan = [c for c in COLUMNAS_FEATURES + ["prod_pet_hace_2_meses"] if c not in df.columns]
    if faltan:
        raise SystemExit("Al CSV le faltan las columnas " + str(faltan) + ". Volve a correr el notebook 02.")

    # Alcance del modelo: pozos con petroleo en los dos meses previos (notebook 03, Paso 11)
    en_alcance = (df["prod_pet_mes_anterior"] > 0) & (df["prod_pet_hace_2_meses"] > 0)
    df_modelo = df[df["anio_completo"] & en_alcance].copy()
    return df, df_modelo


def calcular_metricas(y_real, y_pred):
    picos = y_real > 10000
    return {
        "mae": round(float(mean_absolute_error(y_real, y_pred)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_real, y_pred))), 3),
        "r2": round(float(r2_score(y_real, y_pred)), 4),
        "error_medio_picos": round(float((y_real[picos] - y_pred[picos]).mean()), 1),
    }


def armar_opciones(df, columna_nombre, columna_codigo):
    # Tabla nombre -> codigo, ordenada por cantidad de pozos (la mas usada primero)
    tabla = df.groupby([columna_nombre, columna_codigo])["idpozo"].nunique().reset_index()
    tabla = tabla.sort_values("idpozo", ascending=False)
    return [
        {"nombre": fila[columna_nombre], "codigo": int(fila[columna_codigo]), "pozos": int(fila["idpozo"])}
        for _, fila in tabla.iterrows()
    ]


def armar_ejemplo(titulo, descripcion, fila):
    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "idpozo": int(fila["idpozo"]),
        "entrada": {
            "antiguedad_meses": int(fila["antiguedad_meses"]),
            "prod_pet_mes_anterior": round(float(fila["prod_pet_mes_anterior"]), 2),
            "prod_pet_hace_2_meses": round(float(fila["prod_pet_hace_2_meses"]), 2),
            "prod_gas_mes_anterior": round(float(fila["prod_gas_mes_anterior"]), 2),
            "profundidad": round(float(fila["profundidad"]), 1),
            "formacion": fila["formacion"],
            "cuenca": fila["cuenca"],
        },
        "valor_real": round(float(fila["prod_pet"]), 2),
    }


def elegir_tipico(grupo):
    # Fila "tipica": produccion previa cercana a la mediana del grupo y variacion cercana a la mediana
    mediana_previa = grupo["prod_pet_mes_anterior"].median()
    cercanas = grupo[(grupo["prod_pet_mes_anterior"] / mediana_previa).between(0.75, 1.25)]
    variacion = cercanas["prod_pet"] / cercanas["prod_pet_mes_anterior"] - 1
    return cercanas.loc[(variacion - variacion.median()).abs().idxmin()]


def elegir_ejemplos(test, antiguedad_max):
    # test ya contiene solo filas del alcance, que son las que la API puede recibir
    ejemplos = []

    # 1. Pozo joven de Vaca Muerta, con produccion tipica para ese grupo
    grupo = test[(test["formacion"] == "vaca muerta") & test["antiguedad_meses"].between(10, 14)]
    fila = elegir_tipico(grupo)
    ejemplos.append(armar_ejemplo(
        "Pozo joven de Vaca Muerta", "Alrededor de un anio de vida, produccion tipica del grupo.", fila))

    # 2. Pozo maduro
    grupo = test[test["antiguedad_meses"].between(100, antiguedad_max)]
    fila = elegir_tipico(grupo)
    ejemplos.append(armar_ejemplo(
        "Pozo maduro", "Mas de 100 meses de historia, produccion baja y estable.", fila))

    # 3. El pico mas alto del periodo de prueba (fuera del rango de entrenamiento)
    fila = test.loc[test["prod_pet"].idxmax()]
    ejemplos.append(armar_ejemplo(
        "Pico extremo", "El mes de mayor produccion del periodo de prueba, fuera de lo visto al entrenar.", fila))
    return ejemplos


def main():
    lector = argparse.ArgumentParser()
    lector.add_argument("--parametros", choices=["base", "optuna"], default="optuna")
    args = lector.parse_args()

    df, df_modelo = preparar_datos()
    train = df_modelo[df_modelo["anio"] < ANIO_CORTE]
    test = df_modelo[df_modelo["anio"] >= ANIO_CORTE]
    print("Filas de entrenamiento:", len(train), "| filas de prueba:", len(test))

    tipo, parametros = cargar_parametros(args.parametros)
    print("Parametros usados:", tipo, parametros)

    # El objetivo es la variacion respecto del mes anterior
    y_variacion = train["prod_pet"] - train["prod_pet_mes_anterior"]
    modelo = LGBMRegressor(**parametros, random_state=42, verbose=-1)
    modelo.fit(train[COLUMNAS_FEATURES], y_variacion)

    # Evaluacion en el periodo de prueba (produccion = mes anterior + variacion, piso en 0)
    prediccion = (test["prod_pet_mes_anterior"] + modelo.predict(test[COLUMNAS_FEATURES])).clip(lower=0)
    metricas = calcular_metricas(test["prod_pet"], prediccion)
    baseline = calcular_metricas(test["prod_pet"], test["prod_pet_mes_anterior"])
    print("Metricas en prueba:", metricas)
    print("Baseline (repetir el mes anterior):", baseline)

    metadatos = {
        "version_modelo": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "descripcion": "LightGBM que predice la variacion de produccion de petroleo respecto del mes anterior",
        "parametros_tipo": tipo,
        "parametros": parametros,
        "features": COLUMNAS_FEATURES,
        "anio_corte": ANIO_CORTE,
        "filas_entrenamiento": int(len(train)),
        "filas_prueba": int(len(test)),
        "metricas_test": metricas,
        "metricas_baseline": baseline,
        "rango_entrenamiento": {
            "prod_pet_mes_anterior_max": round(float(train["prod_pet_mes_anterior"].max()), 1),
            "prod_pet_max": round(float(train["prod_pet"].max()), 1),
            "profundidad_min": float(train["profundidad"].min()),
            "profundidad_max": float(train["profundidad"].max()),
            "antiguedad_max": int(train["antiguedad_meses"].max()),
        },
        # OJO: confirmar las unidades en la descripcion oficial del dataset
        "unidades": {"petroleo": "m3", "gas": "Mm3"},
        "formaciones": armar_opciones(df, "formacion", "formacion_cod"),
        "cuencas": armar_opciones(df, "cuenca", "cuenca_cod"),
        "ejemplos": elegir_ejemplos(test, int(train["antiguedad_meses"].max())),
    }

    os.makedirs(CARPETA_MODELOS, exist_ok=True)
    joblib.dump(modelo, os.path.join(CARPETA_MODELOS, "modelo_produccion_pet.joblib"))
    joblib.dump(COLUMNAS_FEATURES, os.path.join(CARPETA_MODELOS, "columnas_features.joblib"))
    with open(os.path.join(CARPETA_MODELOS, "metadatos.json"), "w", encoding="utf-8") as archivo:
        json.dump(metadatos, archivo, ensure_ascii=False, indent=2)
    print("Guardado en", CARPETA_MODELOS + "/: modelo_produccion_pet.joblib, columnas_features.joblib, metadatos.json")


if __name__ == "__main__":
    main()
