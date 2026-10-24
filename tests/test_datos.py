"""Tests de limpieza y de ausencia de fuga de datos en las features."""

import polars as pl
import pytest

from ypf_ds import config
from ypf_ds.features import build as fb


@pytest.fixture(scope="module")
def panel():
    return pl.read_parquet(config.PANEL)


@pytest.fixture(scope="module")
def pozos():
    return pl.read_parquet(config.POZOS)


def test_sin_negativos_ni_duplicados(panel):
    assert panel.filter((pl.col("prod_pet") < 0) | (pl.col("prod_gas") < 0) | (pl.col("prod_agua") < 0)).is_empty()
    assert panel.height == panel.unique(["idpozo", "fecha"]).height


def test_tef_acotado(panel):
    assert panel.filter((pl.col("tef") < 0) | (pl.col("tef") > pl.col("dias_mes"))).is_empty()


def test_grilla_continua(panel):
    saltos = (panel.sort("idpozo", "fecha")
              .with_columns(d=(pl.col("fecha").dt.year() * 12 + pl.col("fecha").dt.month()).diff().over("idpozo"))
              .filter(pl.col("d").is_not_null() & (pl.col("d") != 1)))
    assert saltos.is_empty()


def test_pozos_validos(pozos):
    assert pozos["profundidad"].null_count() == 0
    assert pozos["profundidad"].is_between(config.PROFUNDIDAD_MIN, config.PROFUNDIDAD_MAX).all()
    assert pozos["lon"].is_between(-72, -65).all() and pozos["lat"].is_between(-42, -34).all()
    assert set(pozos["fluido"].unique()) == {"petroleo", "gas"}


def test_features_sin_fuga(panel, pozos):
    """Cambiar la producción futura de un pozo no debe alterar sus features en meses anteriores."""
    pozo = pozos.sort("meses_historia", descending=True)["idpozo"][0]
    sub = panel.filter(pl.col("idpozo") == pozo).sort("fecha")
    corte = sub["fecha"][40]
    alterado = sub.with_columns(
        prod_pet=pl.when(pl.col("fecha") > corte).then(pl.col("prod_pet") * 10).otherwise("prod_pet"))
    a = fb.features_dinamicas(sub).filter(pl.col("fecha") <= corte)
    b = fb.features_dinamicas(alterado).filter(pl.col("fecha") <= corte)
    assert a.equals(b)


def test_target_es_futuro(panel, pozos):
    df = fb.dataset_modo_a(panel.filter(pl.col("idpozo").is_in(pozos["idpozo"].head(50).implode())),
                           pozos, "petroleo", horizontes=[1, 6])
    meses = lambda c: pl.col(c).dt.year() * 12 + pl.col(c).dt.month()
    assert df.filter(meses("fecha_obj") - meses("fecha") != pl.col("horizonte").cast(pl.Int32)).is_empty()


def test_capitulo_iv(pozos):
    if not config.DATA_POZOS_C4.exists():
        pytest.skip("capitulo-iv-pozos.csv no está en data/raw")
    assert pozos["dias_term"].is_not_null().mean() > 0.95
    assert (pozos["dias_perf"].drop_nulls() >= 0).all() and (pozos["dias_term"].drop_nulls() >= 0).all()
    # Los pozos horizontales tienen más profundidad medida (incluye la rama lateral)
    med = pozos.group_by("es_horizontal").agg(pl.col("profundidad").median()).sort("es_horizontal")
    assert med["profundidad"][1] > med["profundidad"][0]
