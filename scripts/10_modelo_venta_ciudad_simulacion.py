#!/usr/bin/env python3
"""
Modelo de venta por ciudad y simulacion de apertura de una farmacia nueva.
Entrada: nhs_farmacias_geolocalizadas.csv (panel de farmacias activas con
         variables geograficas), prediccion_riesgo_cierre.csv (opcional,
         para la version ajustada por cierres en curso)
Salida: simulacion_ciudades_gbm.csv, simulacion_ciudades_gbm_ajustada.csv

Metodologia (ver informe, seccion 5.4/5.6 y anexo A10):
- Se compara regresion lineal, Ridge, Random Forest y Gradient Boosting
  para predecir el volumen mensual de una farmacia a partir de
  caracteristicas de su ciudad (poblacion, cantidad de farmacias,
  centralidad, distancia a centro de salud, privacion socioeconomica,
  tipo de negocio, rural/urbano), por validacion cruzada de 5 particiones.
- Se elige Gradient Boosting (mejor R2 y RMSE).
- Se simula, para cada ciudad de >=20.000 habitantes, cuanto venderia una
  farmacia nueva de perfil independiente en el perfil tipico de esa ciudad,
  incrementando en 1 la cantidad de farmacias actuales.
- La version ajustada excluye del calculo a las farmacias con riesgo de
  cierre >80% antes de construir el perfil de la ciudad.
"""
import pandas as pd, numpy as np
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_validate
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import warnings
warnings.filterwarnings("ignore")

FEATS = ["bua_poblacion", "n_farmacias_ciudad", "hab_x_farmacia", "objetos_1000m",
         "dist_centro_salud_m", "imd20ind", "es_cadena_nacional", "es_cadena_regional",
         "es_supermercado", "rural_dummy"]


def preparar_panel(path_geo):
    act = pd.read_csv(path_geo, dtype=str)
    for c in ["bua_poblacion", "imd20ind", "objetos_1000m", "dist_centro_salud_m", "lat", "long"]:
        act[c] = pd.to_numeric(act[c], errors="coerce")
    act["vol_mensual_prom"] = pd.to_numeric(act["vol_mensual_prom"], errors="coerce")
    act = act.dropna(subset=["bua_poblacion", "bua_nombre", "vol_mensual_prom"])
    act["n_farmacias_ciudad"] = act.groupby("bua_nombre")["CONTRACTOR_CODE"].transform("nunique")
    act["hab_x_farmacia"] = act.bua_poblacion / act.n_farmacias_ciudad
    act["rural_dummy"] = act.ruc21ind.astype(str).str.startswith("R").astype(int)
    act["es_cadena_nacional"] = (act.tipo_negocio == "Cadena nacional").astype(int)
    act["es_cadena_regional"] = (act.tipo_negocio == "Cadena regional").astype(int)
    act["es_supermercado"] = (act.tipo_negocio == "Supermercado").astype(int)
    return act


def comparar_metodos(act):
    X = act[FEATS]
    y = act["vol_mensual_prom"]
    imp = SimpleImputer(strategy="median")
    Xi = imp.fit_transform(X)
    modelos = {
        "Lineal (OLS)": LinearRegression(),
        "Ridge": Ridge(alpha=5.0),
        "Random Forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=15, random_state=0),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0),
    }
    kf = KFold(n_splits=5, shuffle=True, random_state=0)
    print(f"n={len(act)} farmacias | validacion cruzada 5-fold\n")
    for nombre, m in modelos.items():
        pipe = make_pipeline(StandardScaler(), m) if nombre in ("Lineal (OLS)", "Ridge") else m
        res = cross_validate(pipe, Xi, y, cv=kf, scoring=("r2", "neg_root_mean_squared_error"))
        print(f"  {nombre:20s} R2: {res['test_r2'].mean():.3f}   RMSE: {-res['test_neg_root_mean_squared_error'].mean():,.0f}")
    return imp


def simular(act, imp, excluir_codigos=None, min_poblacion=20000):
    base = act if excluir_codigos is None else act[~act.CONTRACTOR_CODE.isin(excluir_codigos)]
    modelo = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0)
    modelo.fit(imp.transform(act[FEATS]), act["vol_mensual_prom"])

    ciudad = base.groupby("bua_nombre").agg(
        poblacion=("bua_poblacion", "first"), n_farmacias=("CONTRACTOR_CODE", "nunique"),
        objetos_1000m_prom=("objetos_1000m", "mean"), dist_cs_prom=("dist_centro_salud_m", "mean"),
        imd_prom=("imd20ind", "mean"), rural_dummy=("rural_dummy", "mean")).reset_index()
    ciudad = ciudad[ciudad.poblacion >= min_poblacion].copy()

    sim = ciudad.copy()
    sim["n_farmacias_ciudad"] = sim.n_farmacias + 1
    sim["hab_x_farmacia"] = sim.poblacion / sim.n_farmacias_ciudad
    sim["bua_poblacion"] = sim.poblacion
    sim["objetos_1000m"] = sim.objetos_1000m_prom
    sim["dist_centro_salud_m"] = sim.dist_cs_prom
    sim["imd20ind"] = sim.imd_prom
    sim["es_cadena_nacional"] = 0
    sim["es_cadena_regional"] = 0
    sim["es_supermercado"] = 0
    sim["rural_dummy"] = sim.rural_dummy.round()
    sim["venta_predicha_nueva"] = modelo.predict(sim[FEATS])
    return sim.sort_values("venta_predicha_nueva", ascending=False)


def main():
    act = preparar_panel("nhs_farmacias_geolocalizadas.csv")
    imp = comparar_metodos(act)

    sim_base = simular(act, imp)
    sim_base.to_csv("simulacion_ciudades_gbm.csv", index=False)

    try:
        riesgo = pd.read_csv("prediccion_riesgo_cierre.csv", index_col=0)["riesgo_cierre"]
        en_riesgo = riesgo[riesgo > 0.8].index
        sim_ajustada = simular(act, imp, excluir_codigos=en_riesgo)
        sim_ajustada.to_csv("simulacion_ciudades_gbm_ajustada.csv", index=False)
    except FileNotFoundError:
        print("prediccion_riesgo_cierre.csv no encontrado; se omite la version ajustada por cierres.")

    for etiqueta_, lo, hi in [("Chicas (20-60k)", 20000, 60000),
                              ("Medianas (60-200k)", 60000, 200000),
                              ("Grandes (200k+)", 200000, 10**8)]:
        sub = sim_base[(sim_base.poblacion >= lo) & (sim_base.poblacion < hi)]
        print(f"\n{etiqueta_} - top 5: {sub.head(5).bua_nombre.tolist()}")


if __name__ == "__main__":
    main()
