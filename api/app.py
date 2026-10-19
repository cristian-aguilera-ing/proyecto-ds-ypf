"""
API para estimar la produccion mensual de petroleo de pozos no convencionales.

Correr local (desde la raiz del proyecto):
    uvicorn api.app:app --reload
Documentacion interactiva: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import PozoEntrada, PrediccionSalida
from src.predict import buscar_codigo, cargar_artefactos, predecir

# Aca guardamos el modelo una vez cargado (se carga al arrancar, no en cada pedido)
estado = {"modelo": None, "metadatos": None, "error": None}

MENSAJE_SIN_MODELO = (
    "El modelo no esta cargado. Entrenalo con: "
    "docker compose --profile train run --rm entrenar  (o: python -m src.train)"
)


@asynccontextmanager
async def ciclo_de_vida(app):
    try:
        estado["modelo"], estado["metadatos"] = cargar_artefactos()
        print("Modelo cargado:", estado["metadatos"]["version_modelo"])
    except FileNotFoundError as error:
        estado["error"] = str(error)
        print("ATENCION:", MENSAJE_SIN_MODELO)
    yield


app = FastAPI(
    title="Pozos no convencionales - Prediccion de produccion de petroleo",
    description="Estima la produccion de petroleo del mes siguiente de un pozo de Vaca Muerta "
                "a partir de su historial reciente. Proyecto final de Data Science.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

# Para poder probar la API desde otro origen (por ejemplo abriendo el frontend a mano)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def exigir_modelo():
    if estado["modelo"] is None:
        raise HTTPException(status_code=503, detail=MENSAJE_SIN_MODELO)


@app.get("/health")
def health():
    """Siempre responde 200 si la API esta viva; indica si el modelo esta cargado."""
    return {"estado": "ok", "modelo_cargado": estado["modelo"] is not None}


@app.get("/info")
def info():
    """Datos del modelo: version, metricas en prueba, baseline y rango de entrenamiento."""
    exigir_modelo()
    m = estado["metadatos"]
    return {
        "version_modelo": m["version_modelo"],
        "descripcion": m["descripcion"],
        "parametros_tipo": m["parametros_tipo"],
        "features": m["features"],
        "anio_corte": m["anio_corte"],
        "filas_entrenamiento": m["filas_entrenamiento"],
        "filas_prueba": m["filas_prueba"],
        "metricas_test": m["metricas_test"],
        "metricas_baseline": m["metricas_baseline"],
        "rango_entrenamiento": m["rango_entrenamiento"],
        "unidades": m["unidades"],
    }


@app.get("/opciones")
def opciones():
    """Formaciones, cuencas y ejemplos reales para probar el modelo."""
    exigir_modelo()
    m = estado["metadatos"]
    return {
        "formaciones": m["formaciones"],
        "cuencas": m["cuencas"],
        "ejemplos": m["ejemplos"],
        "unidades": m["unidades"],
    }


@app.post("/predict", response_model=PrediccionSalida)
def predict(pozo: PozoEntrada):
    """Estima la produccion de petroleo del mes siguiente."""
    exigir_modelo()
    metadatos = estado["metadatos"]
    datos = pozo.model_dump()

    if buscar_codigo(datos["formacion"], metadatos["formaciones"]) is None:
        raise HTTPException(status_code=422, detail="Formacion desconocida: '" + datos["formacion"] + "'. Ver GET /opciones.")
    if buscar_codigo(datos["cuenca"], metadatos["cuencas"]) is None:
        raise HTTPException(status_code=422, detail="Cuenca desconocida: '" + datos["cuenca"] + "'. Ver GET /opciones.")

    return predecir(datos, estado["modelo"], metadatos)
