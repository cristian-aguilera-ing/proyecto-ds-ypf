"""Configuración central del proyecto: rutas, umbrales de limpieza y cortes temporales."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Rutas
DATA_RAW = RAIZ / "data" / "raw" / "produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv"
DATA_POZOS_C4 = RAIZ / "data" / "raw" / "capitulo-iv-pozos.csv"  # padrón de pozos (opcional)
DATA_INTERIM = RAIZ / "data" / "interim" / "neuquina.parquet"
PANEL = RAIZ / "data" / "processed" / "panel_neuquina.parquet"
POZOS = RAIZ / "data" / "processed" / "pozos_neuquina.parquet"
DIR_MODELOS = RAIZ / "models"
DIR_FIGURAS = RAIZ / "reports" / "figuras"

# Filtro de población
CUENCA = "NEUQUINA"
TIPOS_POZO_EXCLUIDOS = ["Inyección de Agua", "Inyección de Gas", "Sumidero", "Acuífero"]
CLASIFICACION_EXCLUIDA = "SERVICIO"

# Columnas que se leen del CSV crudo (el resto está vacío, es constante o es metadata de carga)
COLUMNAS_UTILES = [
    "anio", "mes", "idpozo", "prod_pet", "prod_gas", "prod_agua", "tef",
    "tipoextraccion", "tipoestado", "tipopozo", "empresa", "sigla", "profundidad",
    "formacion", "areayacimiento", "areapermisoconcesion", "cuenca", "provincia",
    "coordenadax", "coordenaday", "proyecto", "clasificacion", "subclasificacion",
    "sub_tipo_recurso",
]

# Umbrales de limpieza
PROFUNDIDAD_MIN = 300.0
PROFUNDIDAD_MAX = 8000.0
GOR_CORTE_GAS = 3000.0  # m3 gas / m3 petróleo: por encima el pozo se considera de gas

# Unidades del dataset: petróleo en m3, gas en miles de m3 (Mm3)
FACTOR_GAS_M3 = 1000.0

# Cortes temporales (fecha = primer día del mes)
FIN_TRAIN = "2022-12-01"
FIN_VALID = "2023-12-01"
FIN_TEST = "2025-12-01"

HORIZONTES = [1, 3, 6, 12]
LAGS = [1, 2, 3, 6, 12]
SEMILLA = 42
