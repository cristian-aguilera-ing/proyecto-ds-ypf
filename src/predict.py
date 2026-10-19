"""
Logica de prediccion, usada por la API.

El modelo NO predice la produccion directamente: predice cuanto CAMBIA la
produccion respecto del mes anterior. La produccion final es:
    produccion = prod_pet_mes_anterior + variacion_predicha   (con piso en 0)
"""
import json
import os

import joblib
import pandas as pd

CARPETA_MODELOS = os.environ.get("MODELS_DIR", "models")


def cargar_artefactos(carpeta=None):
    carpeta = carpeta or CARPETA_MODELOS
    modelo = joblib.load(os.path.join(carpeta, "modelo_produccion_pet.joblib"))
    with open(os.path.join(carpeta, "metadatos.json"), encoding="utf-8") as archivo:
        metadatos = json.load(archivo)
    return modelo, metadatos


def buscar_codigo(nombre, opciones):
    # Compara sin importar mayusculas/minusculas ni espacios de mas
    buscado = nombre.strip().lower()
    for opcion in opciones:
        if opcion["nombre"].strip().lower() == buscado:
            return opcion["codigo"]
    return None


def armar_features(datos, metadatos):
    """Convierte los datos que carga el usuario en las 8 variables del modelo."""
    pet_anterior = datos["prod_pet_mes_anterior"]
    pet_hace_2 = datos["prod_pet_hace_2_meses"]
    gas_anterior = datos["prod_gas_mes_anterior"]

    fila = {
        "antiguedad_meses": datos["antiguedad_meses"],
        "prod_pet_mes_anterior": pet_anterior,
        "prod_gas_mes_anterior": gas_anterior,
        # Declinacion del mes anterior = cambio entre hace 2 meses y el mes anterior
        "declinacion_pet_anterior": (pet_anterior - pet_hace_2) / pet_hace_2,
        # Ratio gas/petroleo del mes anterior
        "ratio_gas_petroleo_anterior": gas_anterior / pet_anterior,
        "profundidad": datos["profundidad"],
        "formacion_cod": buscar_codigo(datos["formacion"], metadatos["formaciones"]),
        "cuenca_cod": buscar_codigo(datos["cuenca"], metadatos["cuencas"]),
    }
    return pd.DataFrame([fila])[metadatos["features"]]


def armar_advertencias(datos, metadatos):
    """Avisos cuando el pozo cae fuera de lo que el modelo vio al entrenar."""
    rango = metadatos["rango_entrenamiento"]
    avisos = []
    if datos["prod_pet_mes_anterior"] > rango["prod_pet_mes_anterior_max"]:
        avisos.append(
            "La produccion del mes anterior supera el maximo visto al entrenar ("
            + str(rango["prod_pet_mes_anterior_max"]) + "). Los modelos de arboles no "
            "extrapolan: la prediccion probablemente subestime la produccion real."
        )
    if not (rango["profundidad_min"] <= datos["profundidad"] <= rango["profundidad_max"]):
        avisos.append(
            "La profundidad esta fuera del rango de entrenamiento ("
            + str(rango["profundidad_min"]) + " a " + str(rango["profundidad_max"]) + ")."
        )
    if datos["antiguedad_meses"] > rango["antiguedad_max"]:
        avisos.append(
            "La antiguedad supera la maxima vista al entrenar (" + str(rango["antiguedad_max"]) + " meses)."
        )
    return avisos


def predecir(datos, modelo, metadatos):
    """datos: diccionario con los campos de entrada. Devuelve un diccionario."""
    X = armar_features(datos, metadatos)
    variacion = float(modelo.predict(X)[0])

    mes_anterior = datos["prod_pet_mes_anterior"]
    produccion = max(mes_anterior + variacion, 0.0)  # la produccion no puede ser negativa
    variacion_final = produccion - mes_anterior

    return {
        "produccion_predicha": round(produccion, 2),
        "produccion_mes_anterior": round(mes_anterior, 2),
        "variacion_predicha": round(variacion_final, 2),
        "variacion_porcentual": round(100 * variacion_final / mes_anterior, 2),
        "advertencias": armar_advertencias(datos, metadatos),
        "unidad": metadatos["unidades"]["petroleo"],
        "version_modelo": metadatos["version_modelo"],
    }
