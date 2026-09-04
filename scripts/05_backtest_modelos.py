#!/usr/bin/env python3
"""
Backtest de origen movil: 12 origenes (jul-2025 a jun-2026).
En cada origen se entrena solo con informacion anterior y se predice el mes siguiente.
Las series se normalizan por su media de entrenamiento para poder apilarlas.
"""
import sys, numpy as np, pandas as pd, warnings, json
from sklearn.linear_model import Ridge, LassoCV
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
warnings.filterwarnings("ignore")

df = pd.read_csv("panel.csv", parse_dates=["fecha"])
FEAT_ESC = ["lag1","lag2","lag3","lag6","lag12","ma3","ma6","ma12","sd6","tend3","tend12"]
FEAT_OTR = ["sin1","cos1","sin2","cos2","ratio_habiles","t"]
FEAT = FEAT_ESC + FEAT_OTR

i0, i1 = int(sys.argv[1]), int(sys.argv[2])
origenes = sorted(df.fecha.unique())[-12:][i0:i1]
filas = []

for org in origenes:
    tr = df[df.fecha < org].copy()
    te = df[df.fecha == org].copy()
    if len(tr) == 0 or len(te) == 0:
        continue
    # escala: media de la serie en entrenamiento (sin mirar el test)
    esc = tr.groupby("cod")["y"].mean().rename("esc")
    tr = tr.join(esc, on="cod"); te = te.join(esc, on="cod")
    te = te[te.esc.notna() & (te.esc > 0)]
    tr = tr[tr.esc > 0]

    for d in (tr, te):
        for c in FEAT_ESC + ["y"]:
            d[c + "_n"] = d[c] / d["esc"]

    Xtr = tr[[c+"_n" for c in FEAT_ESC] + FEAT_OTR].values
    ytr = tr["y_n"].values
    Xte = te[[c+"_n" for c in FEAT_ESC] + FEAT_OTR].values

    preds = {}
    preds["Naive (ultimo mes)"]      = te["lag1"].values
    preds["Naive estacional (t-12)"] = te["lag12"].values
    preds["Media movil 3m"]          = te["ma3"].values

    m = Ridge(alpha=1.0).fit(Xtr, ytr)
    preds["Ridge apilado"] = m.predict(Xte) * te["esc"].values

    m = LassoCV(cv=3, n_alphas=8, max_iter=2000, n_jobs=1).fit(Xtr, ytr)
    preds["Lasso apilado"] = m.predict(Xte) * te["esc"].values

    m = RandomForestRegressor(n_estimators=200, min_samples_leaf=5,
                              n_jobs=1, random_state=0).fit(Xtr, ytr)
    preds["Random Forest"] = m.predict(Xte) * te["esc"].values

    m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.06,
                                      random_state=0).fit(Xtr, ytr)
    preds["Gradient Boosting"] = m.predict(Xte) * te["esc"].values

    preds["Combinacion (Ridge+RF)"] = (preds["Ridge apilado"] + preds["Random Forest"]) / 2

    for nombre, p in preds.items():
        filas.append(pd.DataFrame({
            "origen": org, "modelo": nombre, "cod": te["cod"].values,
            "clase": te["clase"].values, "real": te["y"].values,
            "pred": np.maximum(p, 0), "dias": te["dias"].values,
            "nic_unit": (te["nic"] / te["items"]).values,
        }))
    print(f"  origen {pd.Timestamp(org):%Y-%m} listo", flush=True)

res = pd.concat(filas, ignore_index=True)
res.to_csv(f"bt_{i0}_{i1}.csv", index=False)
print("guardado", f"bt_{i0}_{i1}.csv", len(res))
