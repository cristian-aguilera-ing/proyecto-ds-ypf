"""
preprocessor.py (version simple)
Este archivo toma los datos crudos y los va LIMPIANDO paso a paso.
Cada paso es un pedazo de codigo separado por comentarios, para
poder leerlo de arriba a abajo como una receta.
"""

import pandas as pd


def limpiar_datos(df):
    """
    Recibe el DataFrame crudo y devuelve uno nuevo, ya limpio.
    """

    # Hacemos una copia para no modificar el original por error
    df = df.copy()

    # ------------------------------------------------------------
    # PASO 1: Borrar columnas que estan casi vacias y no sirven
    # ------------------------------------------------------------
    df = df.drop(columns=["vida_util", "observaciones"])

    # ------------------------------------------------------------
    # PASO 2: Rellenar los pocos nulos que quedan en columnas de texto
    # con el valor mas comun de cada columna
    # ------------------------------------------------------------
    columnas_texto = [
        "tipoextraccion", "tipoestado", "tipopozo",
        "clasificacion", "subclasificacion", "sub_tipo_recurso",
    ]
    for columna in columnas_texto:
        valor_mas_comun = df[columna].mode()[0]
        df[columna] = df[columna].fillna(valor_mas_comun)

    # ------------------------------------------------------------
    # PASO 3: Arreglar la profundidad
    # Sabemos que un pozo real mide entre 100 y 10.000 metros.
    # Todo lo que este fuera de ese rango lo marcamos como "no sabemos"
    # y despues lo completamos con la mediana de esa misma formacion.
    # ------------------------------------------------------------
    fuera_de_rango = (df["profundidad"] < 100) | (df["profundidad"] > 10000)
    df.loc[fuera_de_rango, "profundidad"] = None

    medianas_por_formacion = df.groupby("formacion")["profundidad"].median()

    for formacion in medianas_por_formacion.index:
        es_esta_formacion = df["formacion"] == formacion
        es_nulo = df["profundidad"].isnull()
        df.loc[es_esta_formacion & es_nulo, "profundidad"] = medianas_por_formacion[formacion]

    # Por si quedo algun nulo suelto, lo llenamos con la mediana general
    df["profundidad"] = df["profundidad"].fillna(df["profundidad"].median())

    # ------------------------------------------------------------
    # PASO 4: La produccion no puede ser negativa. Si hay algun
    # valor negativo, lo dejamos en 0.
    # ------------------------------------------------------------
    df.loc[df["prod_pet"] < 0, "prod_pet"] = 0
    df.loc[df["prod_gas"] < 0, "prod_gas"] = 0

    # ------------------------------------------------------------
    # PASO 5: Marcar el anio actual como "incompleto", porque
    # todavia no tiene los 12 meses cargados y no se puede comparar
    # de forma justa con los anios anteriores.
    # ------------------------------------------------------------
    anio_actual = 2026
    df["anio_completo"] = df["anio"] != anio_actual

    return df


# Prueba rapida: cargamos, limpiamos, y mostramos como quedo
if __name__ == "__main__":
    from data_loader import cargar_datos

    df_crudo = cargar_datos()
    df_limpio = limpiar_datos(df_crudo)

    print("Filas y columnas antes:", df_crudo.shape)
    print("Filas y columnas despues:", df_limpio.shape)
    print("Nulos en profundidad despues de limpiar:", df_limpio["profundidad"].isnull().sum())
    print("Produccion negativa despues de limpiar:", (df_limpio["prod_pet"] < 0).sum())
