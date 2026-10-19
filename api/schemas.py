"""Esquemas de entrada y salida de la API."""
from typing import List

from pydantic import BaseModel, Field


class PozoEntrada(BaseModel):
    """Datos de un pozo para estimar su produccion de petroleo del mes siguiente.

    El modelo solo se entreno con pozos que tuvieron petroleo en los dos meses
    previos (meses de calendario consecutivos), por eso esos valores deben ser mayores a cero.
    """

    antiguedad_meses: int = Field(
        ge=3, le=600,
        description="Meses de calendario desde el primer mes con datos del pozo hasta el mes a predecir "
                    "(1 = primer mes del pozo). Minimo 3.")
    prod_pet_mes_anterior: float = Field(
        gt=0, description="Produccion de petroleo del mes anterior. Mayor a 0.")
    prod_pet_hace_2_meses: float = Field(
        gt=0, description="Produccion de petroleo de hace dos meses. Mayor a 0.")
    prod_gas_mes_anterior: float = Field(
        ge=0, description="Produccion de gas del mes anterior.")
    profundidad: float = Field(
        gt=0, le=15000, description="Profundidad del pozo en metros.")
    formacion: str = Field(
        min_length=1, description="Formacion geologica (ver GET /opciones).")
    cuenca: str = Field(
        min_length=1, description="Cuenca (ver GET /opciones).")

    model_config = {
        "json_schema_extra": {
            "example": {
                "antiguedad_meses": 12,
                "prod_pet_mes_anterior": 1500.0,
                "prod_pet_hace_2_meses": 1650.0,
                "prod_gas_mes_anterior": 300.0,
                "profundidad": 3000,
                "formacion": "vaca muerta",
                "cuenca": "NEUQUINA",
            }
        }
    }


class PrediccionSalida(BaseModel):
    produccion_predicha: float
    produccion_mes_anterior: float
    variacion_predicha: float
    variacion_porcentual: float
    advertencias: List[str]
    unidad: str
    version_modelo: str
