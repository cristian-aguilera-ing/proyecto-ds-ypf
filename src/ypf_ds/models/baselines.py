"""Baselines que todo modelo tiene que superar.

- Persistencia: la producción futura es igual a la del último mes.
- Arps hiperbólica: curva de declinación clásica de ingeniería de reservorios, ajustada por pozo.
- Curva mediana: para pozos nuevos, mediana histórica por formación, tipo de pozo y mes de vida.
"""

import numpy as np
import polars as pl
from scipy.optimize import curve_fit


def arps(t, qi, di, b):
    """q(t) = qi / (1 + b·di·t)^(1/b)."""
    return qi / np.power(1.0 + b * di * t, 1.0 / b)


def ajustar_arps(historia: np.ndarray, ventana: int = 24):
    """Ajusta Arps sobre los últimos `ventana` meses con producción > 0, desde el pico.

    Devuelve (qi, di, b, t_ultimo) o None si no hay datos suficientes.
    """
    h = np.asarray(historia, float)[-ventana:]
    t = np.arange(len(h), dtype=float)
    pico = int(np.argmax(h))
    t, h = t[pico:] - t[pico], h[pico:]
    m = h > 0
    if m.sum() < 4:
        return None
    try:
        p, _ = curve_fit(arps, t[m], h[m], p0=[h[m][0], 0.1, 1.0],
                         bounds=([0, 1e-4, 0.01], [h.max() * 3 + 1, 5.0, 2.0]), maxfev=2000)
        return (*p, t[-1])
    except (RuntimeError, ValueError):
        return None


def pronostico_arps(historia: np.ndarray, horizontes, ventana: int = 24) -> np.ndarray:
    """Pronóstico Arps para cada horizonte; si el ajuste falla, persistencia."""
    ajuste = ajustar_arps(historia, ventana)
    ultimo = float(historia[-1])
    if ajuste is None:
        return np.full(len(horizontes), ultimo)
    qi, di, b, t0 = ajuste
    return arps(t0 + np.asarray(horizontes, float), qi, di, b)


def curva_mediana(train: pl.DataFrame, claves=("formacion", "tipopozo", "mes_produccion")) -> pl.DataFrame:
    """Mediana de log1p(producción) por grupo, con respaldo por mes de vida solamente."""
    return train.group_by(list(claves)).agg(base=pl.col("y").median())


def predecir_curva_mediana(tabla: pl.DataFrame, df: pl.DataFrame,
                           claves=("formacion", "tipopozo", "mes_produccion")) -> np.ndarray:
    respaldo = tabla.group_by("mes_produccion").agg(base_m=pl.col("base").median())
    out = (df.select(list(claves)).with_row_index("_i")
           .join(tabla, on=list(claves), how="left")
           .join(respaldo, on="mes_produccion", how="left")
           .sort("_i"))
    return np.expm1(out.select(pl.coalesce("base", "base_m")).to_series().to_numpy())
