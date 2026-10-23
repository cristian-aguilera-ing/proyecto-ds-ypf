"""Ingesta del CSV crudo de la Secretaría de Energía con Polars (lectura lazy)."""

import polars as pl

from ypf_ds import config

TIPOS = {
    "anio": pl.Int32, "mes": pl.Int8, "idpozo": pl.Int64,
    "prod_pet": pl.Float64, "prod_gas": pl.Float64, "prod_agua": pl.Float64,
    "tef": pl.Float64, "profundidad": pl.Float64,
    "coordenadax": pl.Float64, "coordenaday": pl.Float64,
}


def escanear_crudo(ruta=config.DATA_RAW) -> pl.LazyFrame:
    """Devuelve el CSV crudo como LazyFrame, solo con las columnas útiles.

    Al ser lazy, los filtros posteriores (por ejemplo la cuenca) se empujan a la lectura
    y nunca se cargan en memoria las filas descartadas.
    """
    return (
        pl.scan_csv(ruta, encoding="utf8-lossy", schema_overrides=TIPOS, infer_schema_length=10_000)
        .select(config.COLUMNAS_UTILES)
    )


def diagnostico(lf: pl.LazyFrame) -> dict:
    """Resumen de calidad del dato crudo, sin corregir nada."""
    df = lf.collect()
    return {
        "filas": df.height,
        "pozos": df["idpozo"].n_unique(),
        "duplicados_pozo_mes": df.height - df.unique(["idpozo", "anio", "mes"]).height,
        "nulos_pct": {c: round(v / df.height * 100, 2)
                      for c, v in df.null_count().row(0, named=True).items() if v},
        "negativos": {c: int((df[c] < 0).sum()) for c in ["prod_pet", "prod_gas", "prod_agua", "tef"]},
        "profundidad_fuera_rango": int(((df["profundidad"] < config.PROFUNDIDAD_MIN)
                                        | (df["profundidad"] > config.PROFUNDIDAD_MAX)).sum()),
        "coordenadas_invertidas": int((df["coordenadax"] > -60).sum()),
    }
