"""Construcción de features y targets para los dos modos de predicción.

Modo A (pozo existente): desde un mes de origen t, con la historia hasta t inclusive, se predice
la producción de los meses t+1 ... t+12. Las filas se apilan por horizonte (h es una feature),
así un único modelo devuelve la curva completa de pronóstico.

Modo B (pozo nuevo): con atributos conocidos antes de perforar, se predice la producción de cada
uno de los primeros 24 meses de vida (curva tipo); mes_produccion es una feature.

Todas las features dinámicas usan solo datos <= t (shift / rolling hacia atrás): no hay fuga.
"""

import numpy as np
import pandas as pd
import polars as pl

from ypf_ds import config

FLUIDOS = {"petroleo": "prod_pet", "gas": "prod_gas"}

CATEGORICAS_A = ["formacion", "sub_tipo_recurso", "areayacimiento", "empresa", "fluido",
                 "tipoextraccion", "tipoestado"]
NUMERICAS_ESTATICAS = ["profundidad", "lat", "lon", "anio_inicio"]

CATEGORICAS_B = ["formacion", "sub_tipo_recurso", "areayacimiento", "empresa", "tipopozo"]
FEATURES_B = CATEGORICAS_B + NUMERICAS_ESTATICAS + ["mes_produccion"]
# Variables del padrón Capítulo IV (perforación y terminación): se usan solo si mejoran la validación
FEATURES_C4 = ["es_horizontal", "dias_perf", "dias_term", "cota"]
MESES_CURVA_B = 24
TOP_EMPRESAS = 15


def agrupar_empresas(pozos: pl.DataFrame) -> pl.DataFrame:
    """Operadoras chicas se agrupan en 'OTRAS' para no fragmentar la categoría."""
    top = pozos["empresa"].value_counts().sort("count", descending=True).head(TOP_EMPRESAS)["empresa"]
    return pozos.with_columns(
        empresa=pl.when(pl.col("empresa").is_in(top.implode())).then("empresa").otherwise(pl.lit("OTRAS"))
    )


def features_dinamicas(panel: pl.DataFrame) -> pl.DataFrame:
    """Features en el mes de origen t calculadas con la historia del pozo hasta t."""
    lp = {f: pl.col(c).log1p() for f, c in [("pet", "prod_pet"), ("gas", "prod_gas"), ("agua", "prod_agua")]}
    exprs = []
    for f, e in lp.items():
        exprs.append(e.alias(f"log_{f}_l0"))
        for k in config.LAGS:
            exprs.append(e.shift(k).over("idpozo").alias(f"log_{f}_l{k}"))
        exprs.append(e.rolling_mean(3, min_samples=1).over("idpozo").alias(f"log_{f}_mm3"))
        exprs.append(e.rolling_mean(6, min_samples=1).over("idpozo").alias(f"log_{f}_mm6"))
    for f, c in [("pet", "prod_pet"), ("gas", "prod_gas")]:
        pico = pl.col(c).cum_max().over("idpozo")
        exprs += [
            pico.log1p().alias(f"log_pico_{f}"),
            (pl.col(c) / pico).fill_nan(0).alias(f"frac_pico_{f}"),
            pl.col(c).cum_sum().over("idpozo").log1p().alias(f"log_acum_{f}"),
            (pl.col(c) / pl.col("tef")).fill_nan(0).fill_null(0).log1p().alias(f"log_q_{f}"),
        ]
    out = panel.sort("idpozo", "fecha").with_columns(exprs)
    out = out.with_columns(
        frac_tef=pl.col("tef") / pl.col("dias_mes"),
        gor=(pl.col("prod_gas") * config.FACTOR_GAS_M3 / pl.col("prod_pet")).log1p().fill_nan(None),
        corte_agua=(pl.col("prod_agua") / (pl.col("prod_agua") + pl.col("prod_pet"))).fill_nan(None),
        tend_pet_3=pl.col("log_pet_l0") - pl.col("log_pet_l3"),
        tend_gas_3=pl.col("log_gas_l0") - pl.col("log_gas_l3"),
        ceros_6=(pl.col("prod_pet") + pl.col("prod_gas") == 0).cast(pl.Int8)
        .rolling_sum(6, min_samples=1).over("idpozo"),
    )
    # Meses desde el pico de petróleo: mes actual menos el mes en que se alcanzó el máximo acumulado
    mes_pico = (pl.when(pl.col("prod_pet") == pl.col("prod_pet").cum_max().over("idpozo"))
                .then(pl.col("mes_produccion")).forward_fill().over("idpozo"))
    return out.with_columns(meses_desde_pico_pet=pl.col("mes_produccion") - mes_pico)


def dataset_modo_a(panel: pl.DataFrame, pozos: pl.DataFrame, fluido: str,
                   horizontes=range(1, 13)) -> pl.DataFrame:
    """Filas (pozo, origen t, horizonte h) con target y = log1p(prod_{t+h}) - log1p(prod_t).

    Solo se usan orígenes con producción del fluido > 0 en t (el pozo está activo) y
    targets en meses efectivamente informados (no reconstruidos por la grilla).
    """
    col = FLUIDOS[fluido]
    base = features_dinamicas(panel).join(
        agrupar_empresas(pozos).select(["idpozo", "formacion", "sub_tipo_recurso", "areayacimiento",
                                        "empresa", "fluido", *NUMERICAS_ESTATICAS]),
        on="idpozo",
    )
    partes = []
    for h in horizontes:
        futuro = pl.col(col).shift(-h).over("idpozo")
        partes.append(
            base.with_columns(
                horizonte=pl.lit(h, pl.Int8),
                fecha_obj=pl.col("fecha").shift(-h).over("idpozo"),
                prod_obj=futuro,
                faltante_obj=pl.col("mes_faltante").shift(-h).over("idpozo"),
            ).filter((pl.col(col) > 0) & pl.col("prod_obj").is_not_null() & ~pl.col("faltante_obj"))
        )
    df = pl.concat(partes)
    return df.with_columns(
        prod_origen=pl.col(col),
        y=pl.col("prod_obj").log1p() - pl.col(col).log1p(),
    ).drop("faltante_obj")


def columnas_modelo_a(df: pl.DataFrame) -> list[str]:
    dinamicas = [c for c in df.columns if c.startswith(("log_", "frac_", "tend_"))] + [
        "gor", "corte_agua", "ceros_6", "meses_desde_pico_pet", "mes_produccion", "mes"]
    return CATEGORICAS_A + NUMERICAS_ESTATICAS + dinamicas + ["horizonte"]


def dataset_modo_b(panel: pl.DataFrame, pozos: pl.DataFrame, fluido: str) -> pl.DataFrame:
    """Filas (pozo, mes_produccion 1..24) con target y = log1p(prod) para pozos con inicio observado."""
    col = FLUIDOS[fluido]
    estaticos = agrupar_empresas(pozos).filter(~pl.col("censurado_izq")).select(
        ["idpozo", *CATEGORICAS_B, *NUMERICAS_ESTATICAS, *FEATURES_C4])
    return (
        panel.filter((pl.col("mes_produccion") <= MESES_CURVA_B) & ~pl.col("mes_faltante"))
        .select("idpozo", "fecha", "mes_produccion", col)
        .join(estaticos, on="idpozo")
        .with_columns(y=pl.col(col).log1p(), prod_obj=pl.col(col))
    )


def a_pandas(df: pl.DataFrame, columnas: list[str], categoricas: list[str], categorias: dict | None = None):
    """Convierte a pandas con dtype category fijo (mismas categorías en train, test y API)."""
    X = df.select(columnas).to_pandas()
    categorias = categorias or {c: sorted(df[c].drop_nulls().unique().to_list()) for c in categoricas}
    for c in categoricas:
        X[c] = X[c].astype("object").where(X[c].notna(), None)
        X[c] = X[c].astype(pd.CategoricalDtype(categorias[c]))
    return X, categorias


def particion_temporal(fechas: pl.Series) -> np.ndarray:
    """'train' (<= 2022), 'valid' (2023), 'test' (2024-2025), 'fuera' (2026, no se evalúa)."""
    import datetime as dt
    d = fechas.to_numpy()
    lim = [np.datetime64(dt.date.fromisoformat(x)) for x in (config.FIN_TRAIN, config.FIN_VALID, config.FIN_TEST)]
    return np.select([d <= lim[0], d <= lim[1], d <= lim[2]], ["train", "valid", "test"], "fuera")
