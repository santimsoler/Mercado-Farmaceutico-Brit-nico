#!/usr/bin/env python3
"""
Modelo de prediccion de cierres de farmacias.
Entrada: nhs_farmacias_localizacion.csv, nhs_farmacias_geolocalizadas.csv
Salida: prediccion_riesgo_cierre.csv

Metodologia (ver informe, seccion 5.5 y anexo A9):
- Se etiquetan 3 cohortes (dic-2022, dic-2023, dic-2024) segun si la farmacia
  activa en ese corte sigue activa 12 meses despues.
- Se comparan regresion logistica, Random Forest y Gradient Boosting,
  entrenando en la primera cohorte y validando en las otras dos.
- Se elige el metodo con mejor desempeño (en este caso, regresion logistica,
  por rendir igual que los no lineales pero ser interpretable).
- El modelo final se reentrena sobre las 3 cohortes combinadas y se aplica
  a las farmacias activas en el ultimo mes disponible.
"""
import pandas as pd, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.impute import SimpleImputer
import warnings
warnings.filterwarnings("ignore")

FEATS = ["vol_prom", "tendencia_12m", "volatilidad", "bua_poblacion", "imd20ind",
         "objetos_1000m", "dist_centro_salud_m", "cadena_dummy"]


def cargar_datos():
    df = pd.read_csv("nhs_farmacias_localizacion.csv", dtype={"YEAR_MONTH": str, "CONTRACTOR_CODE": str})
    prom = df.groupby("CONTRACTOR_CODE")["ITEMS"].mean()
    distancia = prom[prom > prom.quantile(0.99)].index  # excluir venta a distancia
    return df[~df.CONTRACTOR_CODE.isin(distancia)]


def features_en(df, corte):
    """Construye features de los ultimos 12 meses hasta 'corte' (formato YYYYMM)."""
    hist = df[df.YEAR_MONTH <= corte]
    activos = set(hist[hist.YEAR_MONTH == corte].CONTRACTOR_CODE)
    meses = sorted(hist.YEAR_MONTH.unique())[-12:]
    h12 = hist[hist.CONTRACTOR_CODE.isin(activos) & hist.YEAR_MONTH.isin(meses)]
    piv = h12.pivot_table(index="CONTRACTOR_CODE", columns="YEAR_MONTH", values="ITEMS").reindex(columns=meses)
    vol_prom, vol_ini, vol_fin = piv.mean(axis=1), piv.iloc[:, 0], piv.iloc[:, -1]
    tendencia = ((vol_fin / vol_ini.replace(0, np.nan) - 1) * 100).clip(-100, 300)
    volatilidad = (piv.std(axis=1) / piv.mean(axis=1) * 100).clip(0, 200)
    return pd.DataFrame({"vol_prom": vol_prom, "tendencia_12m": tendencia, "volatilidad": volatilidad}), activos


def etiqueta(df, activos_en_corte, corte_futuro):
    activos_futuro = set(df[df.YEAR_MONTH == corte_futuro].CONTRACTOR_CODE)
    return pd.Series({c: int(c not in activos_futuro) for c in activos_en_corte})


def agregar_geo(X, geo):
    geo = geo[["bua_poblacion", "imd20ind", "objetos_1000m", "dist_centro_salud_m", "tipo_negocio"]].copy()
    geo["cadena_dummy"] = (geo.tipo_negocio != "Independiente").astype(int)
    return X.join(geo.drop(columns="tipo_negocio").join(geo["cadena_dummy"]))


def main():
    df = cargar_datos()
    geo = pd.read_csv("nhs_farmacias_geolocalizadas.csv", dtype=str).set_index("CONTRACTOR_CODE")
    for c in ["bua_poblacion", "imd20ind", "objetos_1000m", "dist_centro_salud_m"]:
        geo[c] = pd.to_numeric(geo[c], errors="coerce")

    cohortes = {}
    for corte, corte_fut in [("202212", "202312"), ("202312", "202412"), ("202412", "202512")]:
        X, activos = features_en(df, corte)
        X = agregar_geo(X, geo)
        y = etiqueta(df, activos, corte_fut).reindex(X.index)
        cohortes[corte] = (X[FEATS], y)

    (X1, y1), (X2, y2), (X3, y3) = cohortes.values()
    imp = SimpleImputer(strategy="median").fit(X1)

    modelos = {
        "Logistica": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=10,
                                                class_weight="balanced", random_state=0),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, max_depth=3, random_state=0),
    }
    print("Comparacion de metodos (AUC en validacion):")
    for nombre, m in modelos.items():
        m.fit(imp.transform(X1), y1)
        auc2 = roc_auc_score(y2, m.predict_proba(imp.transform(X2))[:, 1])
        auc3 = roc_auc_score(y3, m.predict_proba(imp.transform(X3))[:, 1])
        print(f"  {nombre:20s} AUC 1 año: {auc2:.3f}  AUC 2 años: {auc3:.3f}")

    # modelo final: logistica, sobre las 3 cohortes combinadas
    Xall = pd.concat([X1, X2, X3])
    yall = pd.concat([y1, y2, y3])
    Xall_i = imp.transform(Xall)
    modelo_final = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xall_i, yall)

    ultimo_mes = sorted(df.YEAR_MONTH.unique())[-1]
    Xhoy, activos_hoy = features_en(df, ultimo_mes)
    Xhoy = agregar_geo(Xhoy, geo)[FEATS]
    Xhoy_i = imp.transform(Xhoy)
    riesgo = pd.Series(modelo_final.predict_proba(Xhoy_i)[:, 1], index=Xhoy.index, name="riesgo_cierre")
    riesgo.to_csv("prediccion_riesgo_cierre.csv")
    print(f"\nFarmacias evaluadas: {len(riesgo)} | riesgo>80%: {(riesgo>0.8).sum()} ({(riesgo>0.8).mean()*100:.1f}%)")


if __name__ == "__main__":
    main()
