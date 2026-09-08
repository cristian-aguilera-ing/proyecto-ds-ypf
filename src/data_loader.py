"""
data_loader.py (version simple)
Este archivo solo sirve para CARGAR el dataset y mostrar un
resumen basico de como esta. No cambia ni corrige nada todavia.
"""

import pandas as pd

# Nombre del archivo que descargamos de datos.gob.ar
NOMBRE_ARCHIVO = "produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv"
RUTA_ARCHIVO = "data/raw/" + NOMBRE_ARCHIVO


def cargar_datos():
    """
    Lee el archivo CSV y lo devuelve como un DataFrame de pandas.
    """
    df = pd.read_csv(RUTA_ARCHIVO)
    return df


def mostrar_resumen(df):
    """
    Imprime en pantalla algunos datos basicos para chequear
    que todo se cargo bien y ver si hay problemas de calidad.
    """
    print("Cantidad de filas y columnas:", df.shape)

    print("\nColumnas con valores nulos (vacios):")
    nulos = df.isnull().sum()
    print(nulos[nulos > 0])

    print("\nCuantos pozos repetidos hay (mismo pozo, mismo mes, mismo anio):")
    duplicados = df.duplicated(subset=["idpozo", "anio", "mes"]).sum()
    print(duplicados)

    print("\nValor maximo y minimo de profundidad:")
    print("Maximo:", df["profundidad"].max())
    print("Minimo:", df["profundidad"].min())

    print("\nCuantos pozos tienen produccion negativa (no deberia pasar):")
    print("Petroleo:", (df["prod_pet"] < 0).sum())
    print("Gas:", (df["prod_gas"] < 0).sum())


# Esto se ejecuta solo si corremos este archivo directamente,
# para probar rapido que la funcion de carga funciona bien.
if __name__ == "__main__":
    datos = cargar_datos()
    mostrar_resumen(datos)
