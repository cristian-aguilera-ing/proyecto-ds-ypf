"""Esquemas de entrada de la API (Pydantic v2)."""

from pydantic import BaseModel, Field, field_validator

from ypf_ds.config import LIMITES_CUENCA


class PedidoExistente(BaseModel):
    idpozo: int = Field(..., description="Identificador del pozo (idpozo de la Secretaría de Energía)",
                        examples=[166848])
    horizonte: int = Field(12, ge=1, le=12, description="Meses a pronosticar desde el último dato")


class PedidoNuevo(BaseModel):
    formacion: str = Field(..., examples=["vaca muerta"])
    sub_tipo_recurso: str = Field(..., pattern="^(SHALE|TIGHT)$", examples=["SHALE"])
    areayacimiento: str = Field(..., examples=["LOMA CAMPANA"])
    empresa: str = Field("YPF S.A.", examples=["YPF S.A."])
    tipopozo: str = Field(..., examples=["Petrolífero"])
    profundidad: float = Field(..., gt=0, lt=12000, description="Profundidad del pozo en metros",
                               examples=[3000])
    # Rango de la Cuenca Neuquina (config.LIMITES_CUENCA); fuera de él el modelo no tiene datos
    lat: float = Field(..., examples=[-38.3], json_schema_extra={"minimum": LIMITES_CUENCA["lat"][0],
                                                                 "maximum": LIMITES_CUENCA["lat"][1]})
    lon: float = Field(..., examples=[-69.0], json_schema_extra={"minimum": LIMITES_CUENCA["lon"][0],
                                                                 "maximum": LIMITES_CUENCA["lon"][1]})
    anio_inicio: int = Field(..., ge=2006, le=2035, examples=[2026])
    # Opcionales (padrón Capítulo IV): si se omiten se usa el valor típico del área
    es_horizontal: bool | None = Field(None, description="Pozo horizontal (rama lateral)", examples=[True])
    dias_perf: float | None = Field(None, ge=0, le=400, description="Días de perforación", examples=[70])
    dias_term: float | None = Field(None, ge=0, le=300, description="Días de terminación / fractura",
                                    examples=[60])

    @field_validator("lat", "lon")
    @classmethod
    def dentro_de_la_cuenca(cls, v: float, info) -> float:
        lo, hi = LIMITES_CUENCA[info.field_name]
        if not lo <= v <= hi:
            nombre = "latitud" if info.field_name == "lat" else "longitud"
            raise ValueError(f"La {nombre} {v} está fuera de la Cuenca Neuquina (debe estar entre {lo} y {hi}).")
        return v
