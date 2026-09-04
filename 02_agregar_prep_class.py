#!/usr/bin/env python3
import sys, subprocess, time
import pandas as pd

USECOLS = ["YEAR_MONTH", "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE",
           "PREP_CLASS", "PRESCRIBED_PREP_CLASS", "ITEMS", "NIC"]
DTYPES = {c: "string" for c in USECOLS if c not in ("ITEMS", "NIC")}
DTYPES.update({"ITEMS": "float64", "NIC": "float64"})
CHUNK = 400_000


def procesar(zip_path, member):
    proc = subprocess.Popen(["unzip", "-p", zip_path, member],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    parciales = []
    reader = pd.read_csv(proc.stdout, usecols=USECOLS, dtype=DTYPES, chunksize=CHUNK, engine="c")
    for ch in reader:
        g = (ch.groupby(["YEAR_MONTH", "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE",
                         "PREP_CLASS", "PRESCRIBED_PREP_CLASS"], dropna=False, observed=True)
             [["ITEMS", "NIC"]].sum().reset_index())
        parciales.append(g)
    proc.stdout.close(); proc.wait()
    out = pd.concat(parciales, ignore_index=True)
    out = (out.groupby(["YEAR_MONTH", "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE",
                        "PREP_CLASS", "PRESCRIBED_PREP_CLASS"], dropna=False, observed=True)
           [["ITEMS", "NIC"]].sum().reset_index())
    return out


if __name__ == "__main__":
    zip_path, member, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    out = procesar(zip_path, member)
    stem = member.replace(".csv", "").replace(" ", "_")
    out.to_csv(f"{outdir}/{stem}.csv", index=False)
    print(f"{member}: {len(out)} filas, {time.time()-t0:.1f}s")
