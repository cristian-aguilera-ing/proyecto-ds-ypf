"""Tests de la API con TestClient (requiere los modelos entrenados en models/)."""

import polars as pl
import pytest
from fastapi.testclient import TestClient

from api.app import app
from ypf_ds import config


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200 and r.json()["estado"] == "ok"


def test_opciones(cliente):
    o = cliente.get("/opciones").json()
    assert "vaca muerta" in o["formacion"] and o["areas"]


def test_buscar(cliente):
    res = cliente.get("/pozos", params={"q": "LCa"}).json()
    assert res and all("idpozo" in p for p in res)


def test_existente(cliente):
    panel = pl.read_parquet(config.PANEL)
    activo = panel.filter((pl.col("fecha") == panel["fecha"].max()) & (pl.col("prod_pet") > 0)
                          & (pl.col("prod_gas") > 0))["idpozo"][0]
    r = cliente.post("/predict/existente", json={"idpozo": int(activo), "horizonte": 6})
    assert r.status_code == 200
    j = r.json()
    for fluido in ("petroleo", "gas"):
        curva = j["pronostico"][fluido]
        assert len(curva["p50"]) == 6
        assert all(a <= b <= c for a, b, c in zip(curva["p10"], curva["p50"], curva["p90"]))
    assert not any("último dato" in a for a in j["avisos"])


def test_existente_inexistente(cliente):
    assert cliente.post("/predict/existente", json={"idpozo": 1}).status_code == 404


def test_nuevo(cliente):
    pedido = {"formacion": "vaca muerta", "sub_tipo_recurso": "SHALE", "areayacimiento": "LOMA CAMPANA",
              "empresa": "YPF S.A.", "tipopozo": "Petrolífero", "profundidad": 3000,
              "lat": -38.3, "lon": -69.0, "anio_inicio": 2025}
    r = cliente.post("/predict/nuevo", json=pedido)
    assert r.status_code == 200
    j = r.json()
    assert len(j["pronostico"]["petroleo"]["p50"]) == 24
    assert j["pronostico"]["petroleo"]["acumulada_12m_p50"] > 0


def test_nuevo_invalido(cliente):
    assert cliente.post("/predict/nuevo", json={"formacion": "vaca muerta"}).status_code == 422


def test_nuevo_con_opcionales(cliente):
    base = {"formacion": "vaca muerta", "sub_tipo_recurso": "SHALE", "areayacimiento": "LOMA CAMPANA",
            "empresa": "YPF S.A.", "tipopozo": "Petrolífero", "profundidad": 5500,
            "lat": -38.35, "lon": -68.6, "anio_inicio": 2025}
    r = cliente.post("/predict/nuevo", json=base | {"es_horizontal": True, "dias_perf": 70, "dias_term": 60})
    assert r.status_code == 200
    assert r.json()["entrada"]["dias_term"] == 60
    assert cliente.post("/predict/nuevo", json=base | {"dias_term": -5}).status_code == 422
