"""Clustering de pozos por forma de su curva de producción (aprendizaje no supervisado).

Cada pozo se describe con sus primeros 12 meses de producción del fluido principal normalizados
por el pico (forma de la curva), comprimidos con SVD, más el tamaño del pico y la relación
gas/petróleo. Se agrupa con K-Means eligiendo k por silhouette.
"""

import joblib
import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ypf_ds import config

MESES = 12
K_CANDIDATOS = range(3, 9)


def vector_pozo(pet: np.ndarray, gas: np.ndarray) -> np.ndarray:
    """Features de un pozo a partir de sus primeros 12 meses de petróleo (m3) y gas (Mm3)."""
    pet, gas = np.asarray(pet, float)[:MESES], np.asarray(gas, float)[:MESES]
    # Fluido principal en energía equivalente aproximada (1 m3 petróleo ~ 1 Mm3 gas)
    principal = pet if pet.sum() >= gas.sum() else gas
    pico = principal.max()
    forma = principal / pico if pico > 0 else np.zeros(MESES)
    gor = np.log1p(gas.sum() * config.FACTOR_GAS_M3 / max(pet.sum(), 1e-3))
    return np.concatenate([forma, [np.log1p(pet.max()), np.log1p(gas.max()), gor]])


def matriz_pozos(panel: pl.DataFrame, pozos: pl.DataFrame):
    validos = pozos.filter(~pl.col("censurado_izq") & (pl.col("meses_historia") >= MESES))["idpozo"]
    sub = (panel.filter(pl.col("idpozo").is_in(validos.implode()) & (pl.col("mes_produccion") <= MESES))
           .sort("idpozo", "mes_produccion")
           .group_by("idpozo", maintain_order=True)
           .agg(pl.col("prod_pet"), pl.col("prod_gas")))
    M = np.vstack([vector_pozo(np.array(p), np.array(g)) for p, g in zip(sub["prod_pet"], sub["prod_gas"])])
    return sub["idpozo"].to_numpy(), M


def _transformador():
    return make_pipeline(StandardScaler(), TruncatedSVD(n_components=6, random_state=config.SEMILLA))


def describir(etiquetas, M) -> list[dict]:
    """Resumen interpretable por cluster: pico, declinación al mes 12 y GOR."""
    out = []
    for k in sorted(set(etiquetas)):
        m = M[etiquetas == k]
        pico_pet, pico_gas = np.expm1(np.median(m[:, MESES])), np.expm1(np.median(m[:, MESES + 1]))
        gor = np.expm1(np.median(m[:, MESES + 2]))
        retencion = float(np.median(m[:, MESES - 1]))  # producción del mes 12 / pico
        fluido = "Petróleo" if gor < config.GOR_CORTE_GAS else "Gas"
        out.append({"cluster": int(k), "pozos": int(len(m)), "fluido": fluido,
                    "pico_pet_mediano_m3": round(float(pico_pet), 1),
                    "pico_gas_mediano_Mm3": round(float(pico_gas), 1),
                    # Sin petróleo el GOR no está definido (pozos de gas seco)
                    "gor_mediano": round(float(gor), 0) if pico_pet >= 1 else None,
                    "retencion_mes12": round(retencion, 3)})
    # Etiquetas legibles: tamaño relativo del pico dentro del mismo fluido
    for f in ("Petróleo", "Gas"):
        grupo = sorted([d for d in out if d["fluido"] == f],
                       key=lambda d: d["pico_pet_mediano_m3"] if f == "Petróleo" else d["pico_gas_mediano_Mm3"])
        niveles = {1: [None], 2: ["bajo", "alto"], 3: ["bajo", "medio", "alto"],
                   4: ["bajo", "medio", "alto", "muy alto"]}.get(len(grupo))
        for i, d in enumerate(grupo):
            nivel = niveles[i] if niveles else f"nivel {i + 1}"
            decl = "declinación fuerte" if d["retencion_mes12"] < 0.35 else "declinación suave"
            d["nombre"] = " · ".join(x for x in [f, nivel and f"pico {nivel}", decl] if x)
    return out


def entrenar_clustering(panel: pl.DataFrame, pozos: pl.DataFrame) -> dict:
    ids, M = matriz_pozos(panel, pozos)
    trans = _transformador()
    Z = trans.fit_transform(M)
    evaluacion = {}
    for k in K_CANDIDATOS:
        lab = KMeans(k, n_init=10, random_state=config.SEMILLA).fit_predict(Z)
        evaluacion[k] = {"silhouette": round(float(silhouette_score(Z, lab)), 4),
                         "davies_bouldin": round(float(davies_bouldin_score(Z, lab)), 4)}
    k = max(evaluacion, key=lambda k: evaluacion[k]["silhouette"])
    km = KMeans(k, n_init=10, random_state=config.SEMILLA).fit(Z)
    perfiles = describir(km.labels_, M)
    joblib.dump({"transformador": trans, "kmeans": km, "perfiles": perfiles,
                 "asignacion": dict(zip(ids.tolist(), km.labels_.tolist()))},
                config.DIR_MODELOS / "clustering.joblib", compress=3)
    print(f"[cluster] k={k} {evaluacion[k]} sobre {len(ids)} pozos")
    return {"k": k, "pozos": int(len(ids)), "evaluacion": evaluacion, "perfiles": perfiles}


def asignar(artefacto: dict, pet, gas) -> int:
    z = artefacto["transformador"].transform(vector_pozo(pet, gas).reshape(1, -1))
    return int(artefacto["kmeans"].predict(z)[0])
