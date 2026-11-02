"""Arma datos/presentacion.json con números reales del proyecto para las escenas animadas.

Nada se escribe a mano: sale de models/metadata.json, de los Parquet y del modelo entrenado.
Correr desde la raíz del repo: python presentacion/generar_datos.py
"""

import json
from pathlib import Path

import numpy as np
import polars as pl

from ypf_ds import config
from ypf_ds.models.baselines import ajustar_arps
from ypf_ds.models.predict import Predictor

SALIDA = Path(__file__).parent / "datos" / "presentacion.json"
NOTEBOOKS = Path(__file__).parent / "datos" / "notebooks.json"
AREA_POZO_NUEVO = "LOMA CAMPANA-LLL"
PROFUNDIDADES = list(range(3000, 7001, 500))
ANIOS = list(range(2018, 2027, 2))


def pozo_gancho(p: Predictor) -> dict:
    """Pozo real de Vaca Muerta con al menos 48 meses y la mayor acumulada: muestra pico y declinación."""
    pozo = (p.pozos.filter((pl.col("formacion") == "vaca muerta") & (pl.col("fluido") == "petroleo")
                           & (pl.col("meses_historia") >= 48) & (pl.col("es_horizontal") == 1))
            .sort("acum_pet", descending=True).row(0, named=True))
    h = p.panel.filter(pl.col("idpozo") == pozo["idpozo"]).sort("fecha")
    q = h["prod_pet"].to_numpy()
    pico = int(np.argmax(q))
    qi, di, b, _ = ajustar_arps(q[pico:], ventana=len(q) - pico)
    return {"idpozo": pozo["idpozo"], "sigla": pozo["sigla"], "area": pozo["areayacimiento"], "empresa": pozo["empresa"],
            "fecha": [str(f)[:7] for f in h["fecha"]], "petroleo": [round(float(v), 1) for v in q],
            "pico_mes": pico, "pico_m3": float(q[pico]),
            "caida_12m": round(1 - float(q[min(pico + 12, len(q) - 1)]) / float(q[pico]), 3),
            "arps": {"qi": round(float(qi), 1), "di": round(float(di), 4), "b": round(float(b), 3)}}


def barrido_pozo_nuevo(p: Predictor) -> dict:
    """Curvas del modelo real para cada combinación de profundidad y año (pozo de Vaca Muerta)."""
    area = next(a for a in p.meta["opciones"]["areas"] if a["areayacimiento"] == AREA_POZO_NUEVO)
    base = {"formacion": "vaca muerta", "sub_tipo_recurso": "SHALE", "areayacimiento": AREA_POZO_NUEVO,
            "empresa": "YPF S.A.", "tipopozo": "Petrolífero", "lat": area["lat"], "lon": area["lon"]}
    curvas = {}
    for prof in PROFUNDIDADES:
        for anio in ANIOS:
            r = p.nuevo(base | {"profundidad": prof, "anio_inicio": anio})["pronostico"]["petroleo"]
            curvas[f"{prof}_{anio}"] = {"p10": [round(v, 1) for v in r["p10"]], "p50": [round(v, 1) for v in r["p50"]],
                                        "p90": [round(v, 1) for v in r["p90"]], "acum12": round(sum(r["p50"][:12]))}
    return {"area": AREA_POZO_NUEVO, "profundidades": PROFUNDIDADES, "anios": ANIOS, "curvas": curvas,
            "profundidad_tipica": round(area["profundidad"])}


def dataset_crudo() -> dict:
    """Tamaño del CSV original y reparto por cuenca, antes de cualquier limpieza."""
    lf = pl.scan_csv(config.DATA_RAW, infer_schema_length=0)
    cuencas = (lf.group_by("cuenca").agg(filas=pl.len(), pozos=pl.col("idpozo").n_unique())
               .sort("filas", descending=True).collect())
    return {"filas": int(cuencas["filas"].sum()), "columnas": len(lf.collect_schema()), "cuencas": cuencas.to_dicts()}


def profundidad_cruda() -> dict:
    """Profundidad informada por pozo en el CSV original: muestra el error de 378.939 m."""
    v = (pl.scan_csv(config.DATA_RAW, infer_schema_length=0).filter(pl.col("cuenca") == "NEUQUINA")
         .select(pl.col("idpozo"), pl.col("profundidad").cast(pl.Float64, strict=False)).drop_nulls()
         .group_by("idpozo").agg(pl.col("profundidad").max()).collect()["profundidad"].to_numpy())
    cuentas, bordes = np.histogram(np.log10(v[v > 0]), bins=44, range=(0, 5.8))
    return {"bordes": [round(float(b), 3) for b in bordes], "cuentas": cuentas.tolist(), "maximo": float(v.max())}


def explicacion_ejemplo(p: Predictor, idpozo: int = 160694) -> dict:
    """SHAP real de un pronóstico: las variables que más empujaron la predicción de ese pozo."""
    r = p.existente(idpozo, 12)
    c = r["pronostico"]["petroleo"]
    return {"sigla": r["pozo"]["sigla"], "acumulada_p50": c["acumulada_p50"], "variables": c["explicacion"]["variables"]}


def produccion_anual(p: Predictor) -> dict:
    """Producción total y pozos activos por año completo: muestra el crecimiento de Vaca Muerta."""
    a = (p.panel.filter(pl.col("anio") <= 2025).group_by("anio")
         .agg(pet=pl.col("prod_pet").sum(), gas=pl.col("prod_gas").sum(),
              pozos=pl.col("idpozo").filter(pl.col("prod_pet") + pl.col("prod_gas") > 0).n_unique()).sort("anio"))
    return {"anio": a["anio"].to_list(), "pet_millon_m3": [round(v / 1e6, 3) for v in a["pet"]],
            "gas_millon_m3": [round(v / 1e6, 3) for v in a["gas"]], "pozos": a["pozos"].to_list()}


def gor(p: Predictor) -> dict:
    """Histograma del GOR por pozo (escala log) y pozos de cada fluido según dónde se ponga el corte."""
    v = p.pozos.filter(pl.col("gor_acum").is_not_null() & (pl.col("gor_acum") > 0))["gor_acum"].to_numpy()
    cuentas, bordes = np.histogram(np.log10(v), bins=48, range=(0, 6))
    total = p.pozos.height
    cortes = [300, 1000, 3000, 10000, 30000]
    petroleo = {c: int(p.pozos.filter(pl.col("gor_acum") < c).height) for c in cortes}
    return {"bordes": [round(float(b), 3) for b in bordes], "cuentas": cuentas.tolist(), "cortes": cortes,
            "total": total, "petroleo": petroleo, "elegido": int(config.GOR_CORTE_GAS)}


def metricas(p: Predictor) -> dict:
    m = p.meta["modelos"]
    pe, ge = m["petroleo_existente"]["metricas_test"], m["gas_existente"]["metricas_test"]
    H = sorted(pe["por_horizonte"], key=int)

    def serie(met, quien, campo):
        return [round(met["por_horizonte"][h][quien][campo], 4) for h in H]

    return {"horizontes": [int(h) for h in H],
            "r2": {"petroleo": serie(pe, "modelo", "r2"), "gas": serie(ge, "modelo", "r2"),
                   "petroleo_pers": serie(pe, "persistencia", "r2"), "gas_pers": serie(ge, "persistencia", "r2")},
            "backtest": {"petroleo": pe["backtest_origen_2023_12"], "gas": ge["backtest_origen_2023_12"]},
            "cortes": p.meta["cortes"], "alcance_v1": pe["alcance_proyecto_anterior"]["modelo"]["r2"],
            "nuevo": {f: m[f"{f}_nuevo"]["metricas_test"] for f in ("petroleo", "gas")},
            "clustering": {k: p.meta["clustering"][k] for k in ("evaluacion", "k", "perfiles", "pozos")}}


def verificar_notebooks() -> list[str]:
    """Cada número de datos/notebooks.json tiene que seguir apareciendo en las salidas de su notebook."""
    def numeros(v):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return [v]
        if isinstance(v, (dict, list)):
            return [n for h in (v.values() if isinstance(v, dict) else v) for n in numeros(h)]
        return []

    faltan = []
    for seccion, valores in json.loads(NOTEBOOKS.read_text()).items():
        if seccion.startswith("_"):
            continue
        nb = json.loads((Path("notebooks") / valores["nb"]).read_text())
        # Las tablas con estilo (pandas Styler) solo guardan su salida en HTML
        salidas = " ".join("".join(o.get("text", [])) + "".join(o.get("data", {}).get("text/plain", []))
                           + "".join(o.get("data", {}).get("text/html", []))
                           for c in nb["cells"] for o in c.get("outputs", []))
        for n in numeros({k: v for k, v in valores.items() if k != "nb"}):
            if str(n) not in salidas:
                faltan.append(f"{valores['nb']} · {seccion}: {n}")
    return faltan


def main():
    faltan = verificar_notebooks()
    print("notebooks.json coincide con los notebooks" if not faltan else "No aparecen en su notebook:\n  " + "\n  ".join(faltan))
    p = Predictor()
    datos = {"version_modelos": p.meta["version"], "datos_hasta": p.meta["datos_hasta"],
             "panel": {"filas": p.panel.height, "pozos": p.pozos.height},
             "crudo": dataset_crudo() | {"profundidad": profundidad_cruda()}, "shap": explicacion_ejemplo(p), "anual": produccion_anual(p), "gor": gor(p),
             "gancho": pozo_gancho(p), "pozo_nuevo": barrido_pozo_nuevo(p), "metricas": metricas(p)}
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")))
    print(f"{SALIDA} · {SALIDA.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
