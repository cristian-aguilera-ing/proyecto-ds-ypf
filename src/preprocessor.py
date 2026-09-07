"""
preprocessor.py
Transformaciones de limpieza sobre los datos crudos ya cargados por data_loader.py.
Cada función hace UNA cosa y devuelve un DataFrame nuevo (no modifica in-place),
para poder testear y encadenar los pasos con claridad.
"""

import pandas as pd

COLUMNAS_A_DESCARTAR = ["vida_util", "observaciones"]

COLUMNAS_CATEGORICAS_A_IMPUTAR = [
    "tipoextraccion", "tipoestado", "tipopozo",
    "clasificacion", "subclasificacion", "sub_tipo_recurso",
]

PROFUNDIDAD_MIN_PLAUSIBLE = 100      # por debajo de esto, se considera dato faltante
PROFUNDIDAD_MAX_PLAUSIBLE = 10000    # por encima de esto, se considera error de carga


def descartar_columnas_vacias(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina columnas con nulos abrumadores (>90%) que no aportan señal."""
    return df.drop(columns=COLUMNAS_A_DESCARTAR, errors="ignore")


def imputar_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Imputa nulos en columnas categóricas con la moda de cada columna.
    Válido acá porque el volumen de nulos es mínimo (<0.25% de las filas) —
    no distorsiona la distribución real de la variable.
    """
    df = df.copy()
    for col in COLUMNAS_CATEGORICAS_A_IMPUTAR:
        if col in df.columns and df[col].isnull().any():
            moda = df[col].mode(dropna=True)
            if len(moda) > 0:
                df[col] = df[col].fillna(moda.iloc[0])
    return df


def corregir_profundidad(df: pd.DataFrame) -> pd.DataFrame:
    """
    Trata como dato faltante (NaN) los valores de profundidad fuera de rango
    plausible (0-100 o >10.000), y los imputa con la mediana de profundidad
    de pozos de la MISMA FORMACIÓN — más preciso que usar la mediana global,
    porque la profundidad varía mucho según formación geológica.

    Caso puntual detectado: idpozo 156804 tiene 378939 repetido en todos sus
    registros (error de carga en origen, no un outlier estadístico disperso).
    Esta función lo corrige igual que cualquier otro caso fuera de rango,
    sin necesidad de tratarlo como excepción manual.
    """
    df = df.copy()
    fuera_de_rango = ~df["profundidad"].between(
        PROFUNDIDAD_MIN_PLAUSIBLE, PROFUNDIDAD_MAX_PLAUSIBLE
    )
    df.loc[fuera_de_rango, "profundidad"] = pd.NA

    # Mediana por formación (fallback: mediana global si la formación
    # no tiene ningún valor válido)
    mediana_por_formacion = df.groupby("formacion")["profundidad"].transform("median")
    mediana_global = df["profundidad"].median()

    df["profundidad"] = df["profundidad"].fillna(mediana_por_formacion)
    df["profundidad"] = df["profundidad"].fillna(mediana_global)

    return df


def corregir_produccion_negativa(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clipea a 0 los valores negativos de producción (físicamente imposibles).
    Volumen insignificante (3 filas de 421.046) — consistente con
    rectificaciones cargadas con signo en el sistema de origen.
    """
    df = df.copy()
    df["prod_pet"] = df["prod_pet"].clip(lower=0)
    df["prod_gas"] = df["prod_gas"].clip(lower=0)
    return df


def marcar_anio_incompleto(df: pd.DataFrame, anio_actual: int, mes_actual: int) -> pd.DataFrame:
    """
    Agrega una columna booleana 'anio_completo' para que los análisis
    agregados por año (ej. producción total anual) puedan excluir o marcar
    el año en curso, que todavía no tiene los 12 meses cargados y por lo
    tanto no es comparable con años anteriores.
    """
    df = df.copy()
    df["anio_completo"] = ~(
        (df["anio"] == anio_actual)
    )
    return df


def pipeline_preprocesamiento(
    df: pd.DataFrame, anio_actual: int = 2026, mes_actual: int = 9
) -> pd.DataFrame:
    """
    Corre todos los pasos de limpieza en el orden correcto.
    Devuelve un DataFrame nuevo, listo para feature engineering.
    """
    df = descartar_columnas_vacias(df)
    df = imputar_categoricas(df)
    df = corregir_profundidad(df)
    df = corregir_produccion_negativa(df)
    df = marcar_anio_incompleto(df, anio_actual, mes_actual)
    return df


if __name__ == "__main__":
    from data_loader import cargar_produccion_no_convencional, validar_calidad

    df_crudo = cargar_produccion_no_convencional()
    df_limpio = pipeline_preprocesamiento(df_crudo)

    print("--- Antes ---")
    for k, v in validar_calidad(df_crudo).items():
        print(f"{k}: {v}")

    print("\n--- Después ---")
    print(f"Shape: {df_limpio.shape}")
    print(f"Nulos en profundidad: {df_limpio['profundidad'].isnull().sum()}")
    print(f"Producción negativa (pet): {(df_limpio['prod_pet'] < 0).sum()}")
    print(f"Producción negativa (gas): {(df_limpio['prod_gas'] < 0).sum()}")
    print(f"Filas año incompleto (2026): {(~df_limpio['anio_completo']).sum()}")
