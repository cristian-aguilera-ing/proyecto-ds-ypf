"""
data_loader.py (version simple)
Este archivo solo sirve para CARGAR el dataset y mostrar un
resumen basico de como esta. No cambia ni corrige nada todavia.
"""

import pandas as pd

# Nombre del archivo que descargamos de datos.gob.ar
NOMBRE_ARCHIVO = "produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv"
RUTA_ARCHIVO = "data/raw/" + NOMBRE_ARCHIVO

# Le decimos a pandas que estas columnas tienen pocos valores distintos
# repetidos muchas veces (ej: "provincia" solo tiene un puñado de valores
# posibles). Guardarlas como "category" en vez de texto normal ahorra
# bastante memoria en un archivo de 421.000 filas.
COLUMNAS_CATEGORIA = {
    "anio": "int16",
    "mes": "int8",
    "idempresa": "category",
    "empresa": "category",
    "tipoextraccion": "category",
    "tipoestado": "category",
    "tipopozo": "category",
    "cuenca": "category",
    "provincia": "category",
    "tipo_de_recurso": "category",
}

# Estas columnas son fechas, pero si no le avisamos a pandas las lee
# como si fueran texto. Le pedimos que las convierta a fecha de una vez.
COLUMNAS_FECHA = ["fechaingreso", "fecha_data"]


def cargar_datos():
    """
    Lee el archivo CSV y lo devuelve como un DataFrame de pandas,
    ya con los tipos de dato correctos (numeros, categorias y fechas).
    """
    df = pd.read_csv(
        RUTA_ARCHIVO,
        sep=",",
        encoding="utf-8-sig",  # evita problemas si el archivo trae un caracter invisible al inicio
        low_memory=False,      # analiza el archivo completo antes de definir los tipos de columna
        parse_dates=COLUMNAS_FECHA,
        dtype=COLUMNAS_CATEGORIA,
    )
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
