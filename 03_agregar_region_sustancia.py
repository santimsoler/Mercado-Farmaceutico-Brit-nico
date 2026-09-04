#!/usr/bin/env python3
import sys, subprocess
import pandas as pd

CHUNK = 400_000
WHITELIST = set(open("/home/claude/work/whitelist.txt").read().split())

BASE = ["YEAR_MONTH", "REGION_NAME", "REGION_CODE",
        "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE",
        "ITEMS", "TOTAL_QUANTITY", "NIC"]


def leer_encabezado(zip_path, member):
    p = subprocess.Popen(["unzip", "-p", zip_path, member],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    linea = p.stdout.readline().decode("utf-8", "replace")
    p.stdout.close(); p.kill(); p.wait()
    return [c.strip().strip('"').strip() for c in linea.strip().split(",")]


def procesar(zip_path, member):
    cols_arch = leer_encabezado(zip_path, member)
    leer = [c for c in BASE if c in cols_arch]
    dtypes = {c: "string" for c in leer if c not in ("ITEMS", "TOTAL_QUANTITY", "NIC")}
    dtypes.update({m: "float64" for m in ["ITEMS", "TOTAL_QUANTITY", "NIC"] if m in leer})

    proc = subprocess.Popen(["unzip", "-p", zip_path, member],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    parciales = []
    reader = pd.read_csv(proc.stdout, usecols=leer, dtype=dtypes, chunksize=CHUNK, engine="c")
    for ch in reader:
        ch = ch[ch.BNF_CHEMICAL_SUBSTANCE_CODE.isin(WHITELIST)]
        if len(ch) == 0:
            continue
        g = (ch.groupby(["YEAR_MONTH", "REGION_CODE", "REGION_NAME",
                         "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE"], dropna=False)
             [["ITEMS", "NIC"]].sum().reset_index())
        parciales.append(g)
    proc.stdout.close(); proc.wait()
    if not parciales:
        return pd.DataFrame(columns=["YEAR_MONTH","REGION_CODE","REGION_NAME",
                                     "BNF_CHEMICAL_SUBSTANCE_CODE","BNF_CHEMICAL_SUBSTANCE","ITEMS","NIC"])
    out = pd.concat(parciales, ignore_index=True)
    return (out.groupby(["YEAR_MONTH", "REGION_CODE", "REGION_NAME",
                         "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE"], dropna=False)
           [["ITEMS", "NIC"]].sum().reset_index())


if __name__ == "__main__":
    zip_path, member, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    out = procesar(zip_path, member)
    stem = member.replace(".csv", "").replace(" ", "_")
    out.to_csv(f"{outdir}/{stem}.csv", index=False)
    print(f"{member}: {len(out)} filas")
