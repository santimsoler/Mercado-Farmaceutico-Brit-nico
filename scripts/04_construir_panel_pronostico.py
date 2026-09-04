#!/usr/bin/env python3
"""
Construye el panel de modelado a nivel sustancia quimica (clase A y B).
Unidad: recetas por dia del mes (ITEMS / dias), para separar calendario de estacionalidad.
"""
import numpy as np, pandas as pd

q = pd.read_csv("unificado/nhs_chemical.csv",
                dtype={"YEAR_MONTH": str, "BNF_CHEMICAL_SUBSTANCE_CODE": str})
q["fecha"] = pd.to_datetime(q["YEAR_MONTH"], format="%Y%m")

# --- clasificacion ABC por gasto acumulado ---
g = q.groupby("BNF_CHEMICAL_SUBSTANCE_CODE")["NIC"].sum().sort_values(ascending=False)
cum = g.cumsum() / g.sum() * 100
clase = pd.Series(np.where(cum <= 80, "A", np.where(cum <= 95, "B", "C")), index=g.index)

# --- panel balanceado: series con los 66 meses ---
piv_items = q.pivot_table(index="fecha", columns="BNF_CHEMICAL_SUBSTANCE_CODE", values="ITEMS")
piv_nic = q.pivot_table(index="fecha", columns="BNF_CHEMICAL_SUBSTANCE_CODE", values="NIC")
completas = piv_items.columns[piv_items.notna().sum() == 66]
sel = [c for c in completas if clase[c] in ("A", "B")]

df = (piv_items[sel].stack().rename("items").reset_index()
      .rename(columns={"BNF_CHEMICAL_SUBSTANCE_CODE": "cod"}))
df["nic"] = piv_nic[sel].stack().values
df["clase"] = df["cod"].map(clase)

# --- calendario ---
df["dias"] = df["fecha"].dt.days_in_month
df["habiles"] = df["fecha"].apply(
    lambda d: np.busday_count(d.strftime("%Y-%m-01"),
                              (d + pd.offsets.MonthBegin(1)).strftime("%Y-%m-%d")))
df["y"] = df["items"] / df["dias"]          # variable objetivo: recetas por dia
df["mes"] = df["fecha"].dt.month
df["t"] = (df["fecha"].dt.year - 2021) * 12 + df["fecha"].dt.month - 1

df = df.sort_values(["cod", "fecha"]).reset_index(drop=True)
gb = df.groupby("cod")["y"]

# --- rezagos y medias moviles (solo pasado) ---
for l in [1, 2, 3, 6, 12]:
    df[f"lag{l}"] = gb.shift(l)
for w in [3, 6, 12]:
    df[f"ma{w}"] = gb.shift(1).rolling(w).mean().reset_index(level=0, drop=True)
df["sd6"] = gb.shift(1).rolling(6).std().reset_index(level=0, drop=True)
df["tend3"] = df["lag1"] - df["lag3"]
df["tend12"] = df["lag1"] - df["lag12"]

# --- Fourier anual ---
for k in [1, 2]:
    df[f"sin{k}"] = np.sin(2 * np.pi * k * df["mes"] / 12)
    df[f"cos{k}"] = np.cos(2 * np.pi * k * df["mes"] / 12)

df["ratio_habiles"] = df["habiles"] / df["dias"]

df = df.dropna().reset_index(drop=True)

df.to_csv("panel.csv", index=False)

print(f"Series: {df.cod.nunique()} (A: {(clase[sel]=='A').sum()}, B: {(clase[sel]=='B').sum()})")
print(f"Observaciones: {len(df):,} | meses: {df.fecha.min():%Y-%m} a {df.fecha.max():%Y-%m}")
print(f"Cobertura de gasto de las series usadas: "
      f"{g[sel].sum()/g.sum()*100:.1f}% del total")
