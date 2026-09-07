"""
data_loader.py
Ingesta y validación inicial de datos crudos.
No transforma datos: solo lee, valida columnas/tipos mínimos, y devuelve.
"""

from pathlib import Path
import pandas as pd

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Columnas que el resto del pipeline (EDA, feature engineering, modelado)
# va a asumir que existen. Si el CSV no las tiene, mejor fallar acá
# y no 10 pasos después con un KeyError confuso.
COLUMNAS_ESPERADAS = [
    "idempresa", "anio", "mes", "idpozo",
    "prod_pet", "prod_gas", "prod_agua",
    "tef", "tipoestado", "tipopozo",
    "formacion", "profundidad", "cuenca", "provincia",
    "coordenadax", "coordenaday",
    "tipo_de_recurso", "sub_tipo_recurso",
]


def cargar_produccion_no_convencional(
    nombre_archivo: str = "produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv",
) -> pd.DataFrame:
    """
    Lee el CSV crudo de producción de pozos no convencionales.
    Valida que las columnas mínimas esperadas estén presentes.
    No imputa, no filtra, no transforma: eso es responsabilidad
    de preprocessor.py.
    """
    ruta = RAW_DATA_DIR / nombre_archivo

    if not ruta.exists():
        raise FileNotFoundError(
            f"No encontré el archivo en {ruta}. "
            f"Revisá que esté en data/raw/ con ese nombre exacto."
        )

    df = pd.read_csv(ruta)

    faltantes = set(COLUMNAS_ESPERADAS) - set(df.columns)
    if faltantes:
        raise ValueError(
            f"Al CSV le faltan columnas esperadas: {faltantes}. "
            f"¿Cambió el formato del dataset en datos.gob.ar?"
        )

    return df

def validar_calidad(df: pd.DataFrame) -> dict:
    """
    Inspecciona la calidad de los datos crudos sin modificarlos.
    Devuelve un diccionario con hallazgos para revisar en el EDA.
    No imputa ni corrige nada — solo diagnostica.
    """
    reporte = {}

    # Duplicados: no debería haber más de un registro por pozo-año-mes
    duplicados = df.duplicated(subset=["idpozo", "anio", "mes"]).sum()
    reporte["duplicados_pozo_anio_mes"] = int(duplicados)

    # Nulos por columna (solo las que tienen al menos 1)
    nulos = df.isnull().sum()
    reporte["columnas_con_nulos"] = nulos[nulos > 0].to_dict()

    # Rango de profundidad: valores físicamente imposibles (pozos no llegan a 300km)
    reporte["profundidad_max"] = float(df["profundidad"].max())
    reporte["profundidad_min"] = float(df["profundidad"].min())
    reporte["pozos_profundidad_sospechosa"] = int((df["profundidad"] > 10000).sum())

    # Producción negativa no tiene sentido físico
    reporte["prod_pet_negativa"] = int((df["prod_pet"] < 0).sum())
    reporte["prod_gas_negativa"] = int((df["prod_gas"] < 0).sum())

    # Rango temporal cubierto
    reporte["anio_min"] = int(df["anio"].min())
    reporte["anio_max"] = int(df["anio"].max())

    return reporte

def cargar_capitulo_iv_pozos(
    nombre_archivo: str = "capitulo-iv-pozos.csv",
) -> pd.DataFrame:
    """
    Lee el CSV de metadatos de pozos (Capítulo IV).
    Complementario al de producción; útil solo si necesitás
    cruzar variables que no vengan ya en el dataset principal.
    """
    ruta = RAW_DATA_DIR / nombre_archivo

    if not ruta.exists():
        raise FileNotFoundError(
            f"No encontré el archivo en {ruta}. "
            f"Revisá que esté en data/raw/ con ese nombre exacto."
        )

    return pd.read_csv(ruta)

if __name__ == "__main__":
    df = cargar_produccion_no_convencional()
    print(df.shape)
    print(df.head())

    print("\n--- Reporte de calidad ---")
    reporte = validar_calidad(df)
    for clave, valor in reporte.items():
        print(f"{clave}: {valor}")