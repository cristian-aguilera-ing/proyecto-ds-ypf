"""Esquemas de entrada de la API (Pydantic v2)."""

from pydantic import BaseModel, Field


class PedidoExistente(BaseModel):
    idpozo: int = Field(..., description="Identificador del pozo (idpozo de la Secretaría de Energía)",
                        examples=[159640])
    horizonte: int = Field(12, ge=1, le=12, description="Meses a pronosticar desde el último dato")


class PedidoNuevo(BaseModel):
    formacion: str = Field(..., examples=["vaca muerta"])
    sub_tipo_recurso: str = Field(..., pattern="^(SHALE|TIGHT)$", examples=["SHALE"])
    areayacimiento: str = Field(..., examples=["LOMA CAMPANA"])
    empresa: str = Field("YPF S.A.", examples=["YPF S.A."])
    tipopozo: str = Field(..., examples=["Petrolífero"])
    profundidad: float = Field(..., gt=0, lt=12000, description="Profundidad del pozo en metros",
                               examples=[3000])
    lat: float = Field(..., ge=-42, le=-34, examples=[-38.3])
    lon: float = Field(..., ge=-72, le=-65, examples=[-69.0])
    anio_inicio: int = Field(..., ge=2006, le=2035, examples=[2026])
    # Opcionales (padrón Capítulo IV): si se omiten se usa el valor típico del área
    es_horizontal: bool | None = Field(None, description="Pozo horizontal (rama lateral)", examples=[True])
    dias_perf: float | None = Field(None, ge=0, le=400, description="Días de perforación", examples=[70])
    dias_term: float | None = Field(None, ge=0, le=300, description="Días de terminación / fractura",
                                    examples=[60])
