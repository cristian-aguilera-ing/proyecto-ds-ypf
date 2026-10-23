"""Limpieza y armado del panel mensual de la Cuenca Neuquina.

Genera dos tablas:
- panel: una fila por pozo y mes, en una grilla mensual continua (sin meses salteados).
- pozos: una fila por pozo con sus atributos estáticos y resúmenes de producción.

Uso: python -m ypf_ds.data.clean
"""

import polars as pl

from ypf_ds import config
from ypf_ds.data.load import escanear_crudo


def filtrar_poblacion(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Cuenca Neuquina y solo pozos productores (sin inyectores, sumideros ni pozos de servicio)."""
    return lf.filter(
        (pl.col("cuenca") == config.CUENCA)
        & ~pl.col("tipopozo").is_in(config.TIPOS_POZO_EXCLUIDOS).fill_null(False)
        & (pl.col("clasificacion") != config.CLASIFICACION_EXCLUIDA).fill_null(True)
    )


def corregir_valores(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Negativos a 0, tef acotado a los días del mes, profundidad imposible a nulo, coordenadas invertidas."""
    fecha = pl.date(pl.col("anio"), pl.col("mes"), 1)
    dias_mes = fecha.dt.month_end().dt.day().cast(pl.Float64)
    invertida = pl.col("coordenadax") > -60  # la longitud de Neuquina está entre -71 y -66
    prof = pl.col("profundidad")
    return lf.with_columns(
        fecha=fecha,
        dias_mes=dias_mes,
        prod_pet=pl.col("prod_pet").clip(lower_bound=0),
        prod_gas=pl.col("prod_gas").clip(lower_bound=0),
        prod_agua=pl.col("prod_agua").clip(lower_bound=0),
        tef=pl.col("tef").clip(0, dias_mes),
        profundidad=pl.when(prof.is_between(config.PROFUNDIDAD_MIN, config.PROFUNDIDAD_MAX)).then(prof),
        lon=pl.when(invertida).then(pl.col("coordenaday")).otherwise(pl.col("coordenadax")),
        lat=pl.when(invertida).then(pl.col("coordenadax")).otherwise(pl.col("coordenaday")),
    ).drop("coordenadax", "coordenaday", "cuenca")


def _ultimo_no_nulo(col: str) -> pl.Expr:
    return pl.col(col).drop_nulls().last().alias(col)


def leer_capitulo_iv(ruta=config.DATA_POZOS_C4) -> pl.DataFrame | None:
    """Padrón de pozos del Capítulo IV: cota, profundidad y fechas de perforación y terminación.

    Aporta la duración de la perforación y de la terminación (proxy de la cantidad de etapas de
    fractura), datos conocidos antes de que el pozo produzca. Si el archivo no está, devuelve None.
    """
    if not ruta.exists():
        return None
    fechas = ["adjiv_fecha_inicio_perf", "adjiv_fecha_fin_perf", "adjiv_fecha_inicio_term", "adjiv_fecha_fin_term"]
    c4 = pl.read_csv(ruta, encoding="utf8-lossy", columns=["idpozo", "cota", "profundidad", *fechas],
                     schema_overrides={"idpozo": pl.Int64, "cota": pl.Float64, "profundidad": pl.Float64})
    ini_p, fin_p, ini_t, fin_t = (pl.col(c).str.to_date(strict=False) for c in fechas)
    prof = pl.col("profundidad")
    return c4.select(
        "idpozo",
        cota=pl.when(pl.col("cota") > 0).then("cota"),
        profundidad_c4=pl.when(prof.is_between(config.PROFUNDIDAD_MIN, config.PROFUNDIDAD_MAX)).then(prof),
        dias_perf=(fin_p - ini_p).dt.total_days().cast(pl.Float64).clip(0, 400),
        dias_term=(fin_t - ini_t).dt.total_days().cast(pl.Float64).clip(0, 300),
        fecha_fin_term=fin_t,
    ).unique("idpozo")


def tabla_pozos(df: pl.DataFrame, fecha_min_dataset, c4: pl.DataFrame | None = None) -> pl.DataFrame:
    """Atributos estáticos por pozo. Para categóricas se toma el último valor informado
    (por ejemplo, la operadora actual si el pozo cambió de manos)."""
    con_prod = df.filter((pl.col("prod_pet") > 0) | (pl.col("prod_gas") > 0))
    inicio = con_prod.group_by("idpozo").agg(
        fecha_inicio=pl.col("fecha").min(),
        tipoextraccion_inicial=pl.col("tipoextraccion").sort_by("fecha").drop_nulls().first(),
    )
    estaticas = (
        df.sort("fecha")
        .group_by("idpozo")
        .agg(
            *[_ultimo_no_nulo(c) for c in [
                "sigla", "empresa", "formacion", "sub_tipo_recurso", "areayacimiento",
                "areapermisoconcesion", "provincia", "tipopozo", "proyecto",
                "clasificacion", "subclasificacion", "tipoestado"]],
            profundidad=pl.col("profundidad").median(),
            lat=pl.col("lat").median(),
            lon=pl.col("lon").median(),
            fecha_ultima=pl.col("fecha").max(),
            acum_pet=pl.col("prod_pet").sum(),
            acum_gas=pl.col("prod_gas").sum(),
            acum_agua=pl.col("prod_agua").sum(),
            pico_pet=pl.col("prod_pet").max(),
            pico_gas=pl.col("prod_gas").max(),
        )
        .join(inicio, on="idpozo", how="inner")  # pozos que nunca produjeron quedan afuera
    )
    if c4 is not None:
        estaticas = estaticas.join(c4, on="idpozo", how="left")
    else:
        estaticas = estaticas.with_columns(
            *[pl.lit(None, pl.Float64).alias(c) for c in ["cota", "profundidad_c4", "dias_perf", "dias_term"]],
            fecha_fin_term=pl.lit(None, pl.Date))
    # Profundidad faltante: Capítulo IV, mediana por (formación, yacimiento), por formación, global
    estaticas = estaticas.with_columns(
        es_horizontal=pl.col("sigla").str.contains(r"\(h\)").cast(pl.Int8),
        profundidad=pl.coalesce(
            "profundidad",
            "profundidad_c4",
            pl.col("profundidad").median().over(["formacion", "areayacimiento"]),
            pl.col("profundidad").median().over("formacion"),
            pl.col("profundidad").median(),
        )
    )
    gor = pl.col("acum_gas") * config.FACTOR_GAS_M3 / pl.col("acum_pet")
    return estaticas.with_columns(
        anio_inicio=pl.col("fecha_inicio").dt.year(),
        # El registro arranca en 2006: los pozos que ya aparecen ese año venían produciendo antes
        censurado_izq=pl.col("fecha_inicio").dt.year() == fecha_min_dataset.year,
        gor_acum=pl.when(pl.col("acum_pet") > 0).then(gor),
        fluido=pl.when((pl.col("acum_pet") > 0) & (gor < config.GOR_CORTE_GAS))
        .then(pl.lit("petroleo")).otherwise(pl.lit("gas")),
    ).sort("idpozo")


def grilla_mensual(df: pl.DataFrame, pozos: pl.DataFrame) -> pl.DataFrame:
    """Reindexa cada pozo a todos los meses entre su primer mes productivo y su último reporte.
    Los meses sin fila quedan con producción 0 y mes_faltante = True."""
    rango = pozos.select(
        "idpozo",
        fecha=pl.date_ranges("fecha_inicio", "fecha_ultima", interval="1mo"),
    ).explode("fecha")
    cols = ["idpozo", "fecha", "prod_pet", "prod_gas", "prod_agua", "tef", "dias_mes",
            "tipoestado", "tipoextraccion"]
    panel = rango.join(df.select(cols), on=["idpozo", "fecha"], how="left")
    dias = pl.col("fecha").dt.month_end().dt.day().cast(pl.Float64)
    panel = panel.with_columns(
        mes_faltante=pl.col("prod_pet").is_null(),
        dias_mes=dias,
        **{c: pl.col(c).fill_null(0.0) for c in ["prod_pet", "prod_gas", "prod_agua", "tef"]},
    )
    # tef = 0 con producción > 0 es un error de carga: se asume el mes completo
    hay_prod = (pl.col("prod_pet") > 0) | (pl.col("prod_gas") > 0)
    panel = panel.with_columns(
        tef=pl.when(hay_prod & (pl.col("tef") == 0)).then(pl.col("dias_mes")).otherwise(pl.col("tef"))
    )
    return panel.sort("idpozo", "fecha").with_columns(
        mes_produccion=pl.int_range(1, pl.len() + 1).over("idpozo").cast(pl.Int32),
        anio=pl.col("fecha").dt.year(),
        mes=pl.col("fecha").dt.month(),
    )


def ultimo_mes_completo(df: pl.DataFrame):
    """Si el último mes tiene menos del 90% de los pozos del mes previo, se considera de carga incompleta."""
    por_mes = df.group_by("fecha").agg(n=pl.col("idpozo").n_unique()).sort("fecha")
    ultimo, previo = por_mes[-1], por_mes[-2]
    if ultimo["n"].item() < 0.9 * previo["n"].item():
        return previo["fecha"].item()
    return ultimo["fecha"].item()


def construir(guardar: bool = True) -> tuple[pl.DataFrame, pl.DataFrame]:
    df = corregir_valores(filtrar_poblacion(escanear_crudo())).collect()
    if guardar:
        config.DATA_INTERIM.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(config.DATA_INTERIM)
    fecha_corte = ultimo_mes_completo(df)
    df = df.filter(pl.col("fecha") <= fecha_corte)
    pozos = tabla_pozos(df, df["fecha"].min(), leer_capitulo_iv())
    panel = grilla_mensual(df, pozos)
    pozos = pozos.join(panel.group_by("idpozo").agg(meses_historia=pl.len()), on="idpozo")
    if guardar:
        config.PANEL.parent.mkdir(parents=True, exist_ok=True)
        panel.write_parquet(config.PANEL)
        pozos.write_parquet(config.POZOS)
    return panel, pozos


if __name__ == "__main__":
    panel, pozos = construir()
    print(f"Panel: {panel.height:,} filas | Pozos: {pozos.height:,} | "
          f"{panel['fecha'].min()} → {panel['fecha'].max()}")
    print(pozos.group_by("fluido").len())
