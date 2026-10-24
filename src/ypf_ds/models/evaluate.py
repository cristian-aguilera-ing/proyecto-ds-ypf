"""Métricas de regresión en escala original (m3 de petróleo / Mm3 de gas)."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def metricas(y_real, y_pred) -> dict:
    y_real, y_pred = np.asarray(y_real, float), np.asarray(y_pred, float)
    return {
        "mae": float(mean_absolute_error(y_real, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_real, y_pred))),
        "r2": float(r2_score(y_real, y_pred)),
        # WAPE: error absoluto total sobre producción total (robusto a meses con producción ~0)
        "wape": float(np.abs(y_real - y_pred).sum() / max(np.abs(y_real).sum(), 1e-9)),
        "n": int(len(y_real)),
    }


def metricas_por_grupo(df: pd.DataFrame, grupo: str, real="real", pred="pred") -> pd.DataFrame:
    return pd.DataFrame({g: metricas(d[real], d[pred]) for g, d in df.groupby(grupo)}).T


def cobertura(y_real, p10, p90) -> float:
    """Fracción de valores reales dentro de la banda P10-P90 (ideal ~0.8)."""
    y_real = np.asarray(y_real)
    return float(((y_real >= p10) & (y_real <= p90)).mean())


def redondear(d, n=4):
    if isinstance(d, dict):
        return {k: redondear(v, n) for k, v in d.items()}
    if isinstance(d, float):
        return round(d, n)
    return d
