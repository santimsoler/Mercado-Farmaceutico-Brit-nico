#!/usr/bin/env python3
import sys, subprocess
import pandas as pd

CHUNK = 400_000


def procesar(zip_path, member):
    proc = subprocess.Popen(["unzip", "-p", zip_path, member],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    primera = proc.stdout.readline().decode("utf-8-sig", "replace")
    cols = [c.strip() for c in primera.strip().split(",")]
    usecols = [c for c in ["YEAR_MONTH", "CONTRACTOR_CODE", "CONTENT_GROUP", "CONTENT", "VALUE"] if c in cols]
    parciales = []
    reader = pd.read_csv(proc.stdout, header=None, names=cols, usecols=usecols,
                         dtype=str, chunksize=CHUNK, engine="c", on_bad_lines="skip")
    for ch in reader:
        ch = ch[(ch.CONTENT_GROUP == "Prescription Count") & (ch.CONTENT.isin(["Items", "Forms"]))]
        if len(ch) == 0:
            continue
        ch["VALUE"] = pd.to_numeric(ch["VALUE"], errors="coerce")
        g = ch.groupby(["YEAR_MONTH", "CONTRACTOR_CODE", "CONTENT"], dropna=False)["VALUE"].sum().reset_index()
        parciales.append(g)
    proc.stdout.close(); proc.wait()
    if not parciales:
        return pd.DataFrame(columns=["YEAR_MONTH", "CONTRACTOR_CODE", "CONTENT", "VALUE"])
    return pd.concat(parciales, ignore_index=True).groupby(
        ["YEAR_MONTH", "CONTRACTOR_CODE", "CONTENT"], dropna=False)["VALUE"].sum().reset_index()


if __name__ == "__main__":
    zip_path, member, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    out = procesar(zip_path, member)
    stem = member.split("/")[-1].replace(".csv", "")
    out.to_csv(f"{outdir}/{stem}.csv", index=False)
    print(f"{stem}: {len(out)} filas")
