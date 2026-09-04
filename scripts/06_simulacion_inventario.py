#!/usr/bin/env python3
"""
Traduce el error de pronostico a politica de inventario.
Stock de seguridad = z * desvio del error de pronostico * raiz(lead time).
Se compara la politica basada en cada modelo contra la practica habitual
(reponer segun el ultimo mes o segun media movil).
"""
import numpy as np, pandas as pd
from scipy import stats

r = pd.read_csv("backtest.csv", parse_dates=["origen"])
q = pd.read_csv("unificado/nhs_chemical.csv", dtype={"BNF_CHEMICAL_SUBSTANCE_CODE": str})
nom = dict(zip(q.BNF_CHEMICAL_SUBSTANCE_CODE, q.BNF_CHEMICAL_SUBSTANCE))

Z = {0.90: 1.2816, 0.95: 1.6449, 0.98: 2.0537, 0.99: 2.3263}
LEAD = 1.0          # lead time en meses
DIAS = 30.4

r["err"] = r.pred - r.real
r["real_mes"] = r.real * DIAS
r["costo_unit"] = r.nic_unit

# desvio del error de pronostico por sustancia y modelo (en recetas/dia)
sd = (r.groupby(["modelo", "cod"])
        .agg(sd_err=("err", "std"),
             demanda_dia=("real", "mean"),
             costo=("costo_unit", "mean"),
             clase=("clase", "first"))
        .reset_index())
sd["demanda_mes"] = sd.demanda_dia * DIAS
sd["sd_err_mes"] = sd.sd_err * DIAS

filas = []
for sl, z in Z.items():
    t = sd.copy()
    t["ss_unid"] = z * t.sd_err_mes * np.sqrt(LEAD)
    t["ss_valor"] = t.ss_unid * t.costo
    t["nivel_servicio"] = sl
    filas.append(t)
pol = pd.concat(filas, ignore_index=True)

print("=== STOCK DE SEGURIDAD REQUERIDO (valor total, GBP) ===")
tab = pol.pivot_table(index="modelo", columns="nivel_servicio", values="ss_valor", aggfunc="sum") / 1e6
base = tab.loc["Naive (ultimo mes)"]
tab_r = tab.copy()
for c in tab.columns:
    tab_r[c] = tab[c].map(lambda v: f"{v:8.1f}M")
print(tab_r.sort_values(0.95, key=lambda s: tab[0.95]).to_string())

print("\n=== AHORRO vs REPOSICION POR ULTIMO MES (nivel de servicio 95%) ===")
a = (1 - tab[0.95] / base[0.95]) * 100
for m, v in a.sort_values(ascending=False).items():
    if m != "Naive (ultimo mes)":
        print(f"  {m:26s} {v:5.1f}%   (stock {tab.loc[m,0.95]:7.1f}M vs {base[0.95]:7.1f}M)")

print("\n=== AHORRO vs MEDIA MOVIL 3M (practica mas realista) ===")
b = tab.loc["Media movil 3m"]
a2 = (1 - tab[0.95] / b[0.95]) * 100
for m, v in a2.sort_values(ascending=False).items():
    if m not in ("Naive (ultimo mes)", "Media movil 3m", "Naive estacional (t-12)"):
        print(f"  {m:26s} {v:5.1f}%")

print("\n=== COSTO DE SUBIR EL NIVEL DE SERVICIO (Random Forest) ===")
rf = tab.loc["Random Forest"]
for sl in [0.90, 0.95, 0.98, 0.99]:
    print(f"  servicio {sl:.0%}: stock {rf[sl]:7.1f}M   (+{(rf[sl]/rf[0.90]-1)*100:5.1f}% sobre 90%)")

print("\n=== DONDE ESTA CONCENTRADO EL AHORRO (RF vs media movil, 95%) ===")
rf_s = pol[(pol.modelo == "Random Forest") & (pol.nivel_servicio == 0.95)].set_index("cod")
mm_s = pol[(pol.modelo == "Media movil 3m") & (pol.nivel_servicio == 0.95)].set_index("cod")
d = (mm_s.ss_valor - rf_s.ss_valor).sort_values(ascending=False)
print(f"  Ahorro total: GBP {d.sum()/1e6:.1f}M")
print(f"  Top 10 sustancias concentran: {d.head(10).sum()/d.sum()*100:.1f}% del ahorro")
for c, v in d.head(8).items():
    print(f"    {nom.get(c, c)[:44]:46s} GBP {v/1e6:6.2f}M")

pol.to_csv("politica_inventario.csv", index=False)
