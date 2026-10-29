"""Lógica de predicción reutilizada por la API (y por los notebooks para demos)."""

import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import polars as pl

from ypf_ds import config
from ypf_ds.features import build as fb
from ypf_ds.models.cluster import asignar

NOMBRES_FEATURES = {
    "log_pet_l0": "Petróleo del último mes", "log_gas_l0": "Gas del último mes",
    "log_pet_mm3": "Petróleo promedio 3 meses", "log_gas_mm3": "Gas promedio 3 meses",
    "log_pet_mm6": "Petróleo promedio 6 meses", "log_gas_mm6": "Gas promedio 6 meses",
    "mes_produccion": "Meses en producción", "horizonte": "Horizonte del pronóstico",
    "frac_pico_pet": "Producción actual / pico (petróleo)", "frac_pico_gas": "Producción actual / pico (gas)",
    "log_pico_pet": "Pico histórico de petróleo", "log_pico_gas": "Pico histórico de gas",
    "tend_pet_3": "Tendencia 3 meses (petróleo)", "tend_gas_3": "Tendencia 3 meses (gas)",
    "frac_tef": "Fracción de días en producción", "gor": "Relación gas/petróleo",
    "corte_agua": "Corte de agua", "formacion": "Formación", "areayacimiento": "Área de yacimiento",
    "empresa": "Operadora", "profundidad": "Profundidad", "anio_inicio": "Año de inicio",
    "lat": "Latitud", "lon": "Longitud", "sub_tipo_recurso": "Shale / Tight", "tipopozo": "Tipo de pozo",
    "meses_desde_pico_pet": "Meses desde el pico", "log_acum_pet": "Acumulada de petróleo",
    "log_acum_gas": "Acumulada de gas", "tipoextraccion": "Sistema de extracción",
    "es_horizontal": "Pozo horizontal", "dias_perf": "Días de perforación",
    "dias_term": "Días de terminación (fractura)", "cota": "Cota del terreno",
}


def _nombre(f: str) -> str:
    return NOMBRES_FEATURES.get(f, f)


def predecir_a(trio: dict, X, base) -> dict:
    """Modo A a volumen: P50 = q[t]·ratio; P10/P90 = expm1(log1p(q[t]) + cuantil log)."""
    p50 = np.clip(base * trio["p50"].predict(X), 0, None)
    p10 = np.clip(np.expm1(np.log1p(base) + trio["p10"].predict(X)), 0, None)
    p90 = np.clip(np.expm1(np.log1p(base) + trio["p90"].predict(X)), 0, None)
    return {"p10": np.minimum(p10, p50), "p50": p50, "p90": np.maximum(p90, p50)}


def predecir_b(trio: dict, X) -> dict:
    p50 = np.clip(trio["p50"].predict(X), 0, None)
    p10 = np.clip(np.expm1(trio["p10"].predict(X)), 0, None)
    p90 = np.clip(np.expm1(trio["p90"].predict(X)), 0, None)
    return {"p10": np.minimum(p10, p50), "p50": p50, "p90": np.maximum(p90, p50)}


class Predictor:
    def __init__(self, dir_modelos: Path = config.DIR_MODELOS, panel=config.PANEL, pozos=config.POZOS):
        self.meta = json.loads((dir_modelos / "metadata.json").read_text())
        self.modelos = {n: joblib.load(dir_modelos / f"{n}.joblib")
                        for n in ["petroleo_existente", "gas_existente", "petroleo_nuevo", "gas_nuevo"]}
        self.cluster = joblib.load(dir_modelos / "clustering.joblib")
        self.panel = pl.read_parquet(panel)
        self.pozos = pl.read_parquet(pozos)
        self.fecha_max = self.panel["fecha"].max()
        self.indice = self._indice_busqueda()

    # ---------------------------------------------------------------- utilidades
    def _matriz(self, art: dict, df: pl.DataFrame) -> pd.DataFrame:
        X = df.select(art["columnas"]).to_pandas()
        for c in art["categoricas"]:
            cats = art["categorias"][c]
            v = X[c].astype("object")
            if c == "empresa":
                v = v.where(v.isin(cats), "OTRAS")
            X[c] = pd.Categorical(v.where(v.isin(cats), None), categories=cats)
        return X

    def _explicar(self, art: dict, X: pd.DataFrame, top: int = 6) -> list[dict]:
        """Contribuciones SHAP (TreeSHAP nativo de LightGBM) del modelo puntual, promediadas sobre las filas.

        La unidad depende del modelo:
        - Modo A: puntos del ratio producción futura / último mes ("ratio").
        - Modo B con objetivo L2: m3 o Mm3 por mes ("volumen").
        - Modo B con objetivo Poisson/Tweedie: el modelo es multiplicativo (escala log), así que
          cada contribución se expresa como % de cambio sobre la predicción base ("porcentaje").
        """
        modelo = art["modelos"]["p50"]
        contrib = modelo.predict(X, pred_contrib=True)[:, :-1].mean(axis=0)
        orden = np.argsort(-np.abs(contrib))[:top]
        if art.get("modo") == "existente" or "ratio" in art.get("target", ""):
            unidad = "ratio"
        elif modelo.get_params().get("objective") in ("poisson", "tweedie"):
            unidad, contrib = "porcentaje", np.expm1(contrib) * 100
        else:
            unidad = "volumen"
        return {"unidad": unidad,
                "variables": [{"feature": art["columnas"][i], "descripcion": _nombre(art["columnas"][i]),
                               "impacto": round(float(contrib[i]), 4)} for i in orden]}

    def _perfil_cluster(self, k: int | None):
        if k is None:
            return None
        return next(p for p in self.cluster["perfiles"] if p["cluster"] == k)

    def _indice_busqueda(self) -> pl.DataFrame:
        """Tabla para el buscador: estado de cada pozo (activo si produjo en el último mes del dataset)
        y su producción reciente, para ordenar los resultados por relevancia."""
        con_prod = self.panel.filter((pl.col("prod_pet") > 0) | (pl.col("prod_gas") > 0))
        ultima = con_prod.group_by("idpozo").agg(ultima_produccion=pl.col("fecha").max())
        reciente = (self.panel.filter(pl.col("fecha") == self.fecha_max)
                    .select("idpozo", prod_reciente=pl.col("prod_pet") + pl.col("prod_gas")))
        return (self.pozos.join(ultima, on="idpozo", how="left").join(reciente, on="idpozo", how="left")
                .with_columns(
                    activo=pl.col("ultima_produccion") == self.fecha_max,
                    prod_reciente=pl.col("prod_reciente").fill_null(0),
                    texto=pl.concat_str(["sigla", "areayacimiento", "empresa", "formacion", pl.col("idpozo").cast(pl.String)],
                                        separator=" ").str.to_uppercase()))

    def buscar_pozos(self, q: str, limite: int = 15) -> list[dict]:
        """Busca por sigla, yacimiento, operadora, formación o idpozo. Admite varias palabras ("ypf loma campana"):
        todas tienen que aparecer. Ordena: idpozo exacto, sigla que empieza con la búsqueda, pozos activos
        y mayor producción reciente."""
        palabras = q.strip().upper().split()
        if not palabras:
            return []
        filtro = pl.all_horizontal([pl.col("texto").str.contains(p, literal=True) for p in palabras])
        q_junto = " ".join(palabras)
        res = (self.indice.filter(filtro)
               .with_columns(
                   exacto=pl.col("idpozo").cast(pl.String) == q_junto,
                   empieza=pl.col("sigla").str.to_uppercase().str.starts_with(q_junto)
                   | pl.col("sigla").str.to_uppercase().str.contains("." + q_junto, literal=True))
               .sort(["exacto", "empieza", "activo", "prod_reciente"], descending=True)
               .head(limite))
        return res.select(
            "idpozo", "sigla", "empresa", "formacion", "areayacimiento", "fluido", "activo",
            pl.col("fecha_ultima").cast(pl.String),
            pl.col("ultima_produccion").dt.strftime("%Y-%m").alias("ultima_produccion"),
        ).to_dicts()

    # ---------------------------------------------------------------- Modo A
    def existente(self, idpozo: int, horizonte: int = 12) -> dict:
        info = self.pozos.filter(pl.col("idpozo") == idpozo)
        if info.is_empty():
            raise KeyError(f"El pozo {idpozo} no está en la Cuenca Neuquina o nunca produjo")
        info = info.row(0, named=True)
        hist = self.panel.filter(pl.col("idpozo") == idpozo).sort("fecha")
        feats = fb.features_dinamicas(hist).tail(1).join(
            self.pozos.select("idpozo", "formacion", "sub_tipo_recurso", "areayacimiento", "empresa",
                              "fluido", *fb.NUMERICAS_ESTATICAS), on="idpozo")
        ultimo = feats.row(0, named=True)
        filas = pl.concat([feats.with_columns(horizonte=pl.lit(h, pl.Int8)) for h in range(1, horizonte + 1)])
        fechas = [str(pl.select(pl.lit(ultimo["fecha"]).dt.offset_by(f"{h}mo")).item()) for h in range(1, horizonte + 1)]
        avisos = []
        meses_sin_reporte = (self.fecha_max.year - ultimo["fecha"].year) * 12 + self.fecha_max.month - ultimo["fecha"].month
        if meses_sin_reporte > 0:
            avisos.append(f"El último dato del pozo es {ultimo['fecha']} ({meses_sin_reporte} meses antes del fin "
                          "del dataset): el pronóstico parte de ese mes.")
        if ultimo["prod_pet"] <= 0 and ultimo["prod_gas"] <= 0:
            fila = self.indice.filter(pl.col("idpozo") == idpozo).row(0, named=True)
            desde = fila["ultima_produccion"].strftime("%Y-%m") if fila["ultima_produccion"] else "—"
            avisos.append(f"El pozo no produjo en su último mes informado (última producción: {desde}). "
                          "El modelo pronostica a partir del último mes, así que no hay pronóstico; "
                          "elegí un pozo marcado como activo en el buscador.")
        if info["censurado_izq"]:
            avisos.append("El pozo ya producía antes de 2006: su antigüedad real es mayor a la registrada.")

        resultado = {}
        for fluido, col in fb.FLUIDOS.items():
            art = self.modelos[f"{fluido}_existente"]
            base = float(ultimo[col])
            if base <= 0:
                resultado[fluido] = None
                # Si el pozo no produjo nada, ya hay un aviso general; solo se avisa por fluido si el otro sí produjo
                if ultimo["prod_pet"] > 0 or ultimo["prod_gas"] > 0:
                    avisos.append(f"Sin producción de {fluido} en el último mes: no se pronostica ese fluido.")
                continue
            X = self._matriz(art, filas)
            pred = predecir_a(art["modelos"], X, np.full(len(X), base))
            resultado[fluido] = self._resumen_curva(fechas, pred, base, art, X, fluido, "existente")

        k = self.cluster["asignacion"].get(idpozo)
        hist24 = hist.tail(24)
        return {
            "pozo": {k2: (str(v) if hasattr(v, "isoformat") else v) for k2, v in info.items()},
            "origen": str(ultimo["fecha"]),
            "historia": {"fecha": [str(f) for f in hist24["fecha"]],
                         "petroleo": hist24["prod_pet"].round(2).to_list(),
                         "gas": hist24["prod_gas"].round(2).to_list()},
            "pronostico": resultado,
            "indicadores_actuales": {
                "gor_m3_m3": round(ultimo["prod_gas"] * config.FACTOR_GAS_M3 / ultimo["prod_pet"], 1)
                if ultimo["prod_pet"] > 0 else None,
                "corte_agua": round(ultimo["corte_agua"], 3) if ultimo["corte_agua"] is not None else None,
                "dias_efectivos": ultimo["tef"], "meses_en_produccion": ultimo["mes_produccion"],
                "acum_pet_m3": round(info["acum_pet"], 1), "acum_gas_Mm3": round(info["acum_gas"], 1),
            },
            "cluster": self._perfil_cluster(k),
            "avisos": avisos,
        }

    # ---------------------------------------------------------------- Modo B
    def completar_tipicos(self, datos: dict) -> tuple[dict, list[str]]:
        """Los datos de perforación y terminación son opcionales: si faltan, se usa el valor típico
        del área (mediana de los pozos recientes)."""
        area = next((a for a in self.meta["opciones"]["areas"]
                     if a["areayacimiento"] == datos.get("areayacimiento")), {})
        completados = []
        datos = dict(datos)
        for campo, clave in [("es_horizontal", "horizontal"), ("dias_perf", "dias_perf"), ("dias_term", "dias_term")]:
            if datos.get(campo) is None:
                valor = area.get(clave)
                datos[campo] = int(valor) if campo == "es_horizontal" and valor is not None else valor
                completados.append(campo)
        datos.setdefault("cota", None)
        return datos, completados

    def nuevo(self, datos: dict, meses: int = fb.MESES_CURVA_B) -> dict:
        datos, completados = self.completar_tipicos(datos)
        if isinstance(datos.get("es_horizontal"), bool):
            datos["es_horizontal"] = int(datos["es_horizontal"])
        filas = pl.DataFrame([datos | {"mes_produccion": m} for m in range(1, meses + 1)],
                             schema_overrides={c: pl.Float64 for c in ["dias_perf", "dias_term", "cota"]})
        avisos = self._fuera_de_rango(datos)
        usados = {c for f in fb.FLUIDOS for c in self.modelos[f"{f}_nuevo"]["columnas"]}
        if completados and usados & set(completados):
            avisos.append("Se usaron valores típicos del área para: " + ", ".join(_nombre(c) for c in completados
                          if c in usados) + ".")
        resultado = {}
        for fluido in fb.FLUIDOS:
            art = self.modelos[f"{fluido}_nuevo"]
            X = self._matriz(art, filas)
            pred = predecir_b(art["modelos"], X)
            resultado[fluido] = self._resumen_curva(list(range(1, meses + 1)), pred, None, art, X, fluido, "nuevo")
        k = asignar(self.cluster, resultado["petroleo"]["p50"], resultado["gas"]["p50"])
        pet12, gas12 = sum(resultado["petroleo"]["p50"][:12]), sum(resultado["gas"]["p50"][:12])
        return {
            "entrada": datos, "pronostico": resultado,
            "indicadores": {"gor_12m_m3_m3": round(gas12 * config.FACTOR_GAS_M3 / pet12, 1) if pet12 > 0 else None,
                            "fluido_dominante": "petroleo" if pet12 > 0 and
                            gas12 * config.FACTOR_GAS_M3 / pet12 < config.GOR_CORTE_GAS else "gas"},
            "cluster": self._perfil_cluster(k), "avisos": avisos,
        }

    def _distancia_al_area(self, datos: dict) -> float | None:
        """Distancia aproximada (km, equirectangular) entre el pozo y la mediana de los pozos del área."""
        area = next((a for a in self.meta["opciones"]["areas"]
                     if a["areayacimiento"] == datos.get("areayacimiento")), None)
        if not area or datos.get("lat") is None or datos.get("lon") is None:
            return None
        dlat = math.radians(datos["lat"] - area["lat"])
        dlon = math.radians(datos["lon"] - area["lon"]) * math.cos(math.radians((datos["lat"] + area["lat"]) / 2))
        return 6371.0 * math.hypot(dlat, dlon)

    def _fuera_de_rango(self, datos: dict) -> list[str]:
        avisos = []
        for c, (lo, hi) in self.meta["opciones"]["rangos"].items():
            v = datos.get(c)
            if v is not None and not (lo <= v <= hi):
                avisos.append(f"{_nombre(c)} = {v} está fuera del rango de entrenamiento [{lo}, {hi}]: "
                              "la predicción es una extrapolación.")
        km = self._distancia_al_area(datos)
        if km is not None and km > config.DISTANCIA_AREA_AVISO_KM:
            avisos.append(f"La ubicación está a {km:.0f} km del centro del área {datos['areayacimiento']}: "
                          "revisá la latitud, la longitud o el área elegida.")
        if datos.get("anio_inicio", 0) > int(self.meta["opciones"]["rangos"]["anio_inicio"][1]):
            avisos.append("Pozos futuros: el modelo asume la tecnología de completación del último año conocido.")
        return avisos

    def _resumen_curva(self, eje, pred, base, art, X, fluido, modo) -> dict:
        unidad = "m3" if fluido == "petroleo" else "Mm3"
        p50 = np.array(pred["p50"])
        dias = 30.4
        met = self.meta["modelos"][f"{fluido}_{modo}"]["metricas_test"]
        out = {
            "unidad": unidad, "eje": eje,
            "p10": np.round(pred["p10"], 2).tolist(), "p50": np.round(p50, 2).tolist(),
            "p90": np.round(pred["p90"], 2).tolist(),
            "acumulada_p50": round(float(p50.sum()), 1),
            "acumulada_p10": round(float(np.sum(pred["p10"])), 1),
            "acumulada_p90": round(float(np.sum(pred["p90"])), 1),
            "caudal_diario_inicial": round(float(p50[0] / dias), 2),
            "pico_p50": round(float(p50.max()), 2), "mes_pico": int(np.argmax(p50)) + 1,
            "explicacion": self._explicar(art | {"modo": modo}, X),
        }
        if base is not None:
            out["ultimo_mes"] = round(base, 2)
            out["declinacion_12m"] = round(1 - float(p50[min(11, len(p50) - 1)]) / base, 3) if base > 0 else None
            ph = met["por_horizonte"]
            out["metricas_modelo"] = {"wape": met["modelo"]["wape"], "r2": met["modelo"]["r2"],
                                      "r2_h1": ph["1"]["modelo"]["r2"], "r2_h12": ph["12"]["modelo"]["r2"],
                                      "wape_h1": ph["1"]["modelo"]["wape"], "wape_h12": ph["12"]["modelo"]["wape"],
                                      "cobertura_p10_p90": met["cobertura_p10_p90"]}
        else:
            out["acumulada_12m_p50"] = round(float(p50[:12].sum()), 1)
            out["declinacion_12m"] = round(1 - float(p50[11]) / float(p50.max()), 3) if p50.max() > 0 else None
            out["metricas_modelo"] = {"wape_acum12": met["acum_12m"]["modelo"]["wape"],
                                      "r2_acum12": met["acum_12m"]["modelo"]["r2"],
                                      "cobertura_p10_p90": met["cobertura_p10_p90"]}
        return out
