"""API de predicción de producción de petróleo y gas — Cuenca Neuquina.

Levantar en local: uvicorn api.app:app --reload   (Swagger en http://localhost:8000/docs)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.model import obtener_predictor
from api.schemas import PedidoExistente, PedidoNuevo


@asynccontextmanager
async def lifespan(app: FastAPI):
    obtener_predictor()  # carga modelos y datos una sola vez al arrancar
    yield


app = FastAPI(
    title="Producción No Convencional — Cuenca Neuquina",
    description="Pronóstico de producción de petróleo y gas para pozos existentes y curvas tipo para pozos nuevos.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    p = obtener_predictor()
    return {"estado": "ok", "version_modelos": p.meta["version"], "datos_hasta": p.meta["datos_hasta"]}


@app.get("/metadata")
def metadata():
    m = obtener_predictor().meta
    return {k: m[k] for k in ("version", "datos_hasta", "unidades", "cortes", "modelos", "clustering")}


@app.get("/opciones")
def opciones():
    return obtener_predictor().meta["opciones"]


@app.get("/pozos")
def buscar_pozos(q: str = Query(..., min_length=2, description="Sigla o idpozo (parcial)")):
    return obtener_predictor().buscar_pozos(q)


@app.post("/predict/existente")
def predecir_existente(pedido: PedidoExistente):
    try:
        return obtener_predictor().existente(pedido.idpozo, pedido.horizonte)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e.args[0])) from e


@app.post("/predict/nuevo")
def predecir_nuevo(pedido: PedidoNuevo):
    return obtener_predictor().nuevo(pedido.model_dump())
