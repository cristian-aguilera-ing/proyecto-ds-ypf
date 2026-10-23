"""Carga única de los artefactos entrenados para la API."""

import os
from functools import lru_cache
from pathlib import Path

from ypf_ds import config
from ypf_ds.models.predict import Predictor


@lru_cache(maxsize=1)
def obtener_predictor() -> Predictor:
    dir_modelos = Path(os.getenv("DIR_MODELOS", config.DIR_MODELOS))
    dir_datos = Path(os.getenv("DIR_DATOS", config.PANEL.parent))
    return Predictor(dir_modelos, dir_datos / config.PANEL.name, dir_datos / config.POZOS.name)
