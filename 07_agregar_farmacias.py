#!/usr/bin/env python3
import sys, subprocess
import pandas as pd

CHUNK = 400_000


def procesar(zip_path, member):
    proc = subprocess.Popen(["unzip", "-p", zip_path, member],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    # leer encabezado para saber que columnas hay en esta version del esquema
    primera = proc.stdout.readline().decode("utf-8-sig", "replace")
    cols = [c.strip() for c in primera.strip().split(",")]
    resto = proc.stdout  # el resto del stream, sin la primera linea

    usecols = [c for c in ["YEAR_MONTH", "PHARMACY_ACCOUNT_TYPE", "CONTRACTOR_CODE",
                           "CONTRACTOR_NAME", "POSTCODE", "CONTENT_GROUP", "CONTENT", "VALUE"]
              if c in cols]

    parciales = []
    reader = pd.read_csv(resto, header=None, names=cols, usecols=usecols,
                         dtype=str, chunksize=CHUNK, engine="c", on_bad_lines="skip")
    for ch in reader:
        ch = ch[(ch.CONTENT_GROUP == "Prescription Count") & (ch.CONTENT == "Items")]
        if len(ch) == 0:
            continue
        ch["VALUE"] = pd.to_numeric(ch["VALUE"], errors="coerce")
        g = (ch.groupby(["YEAR_MONTH", "PHARMACY_ACCOUNT_TYPE", "CONTRACTOR_CODE",
                         "CONTRACTOR_NAME", "POSTCODE"], dropna=False)["VALUE"]
             .sum().reset_index())
        parciales.append(g)
    proc.stdout.close(); proc.wait()
    if not parciales:
        return pd.DataFrame(columns=["YEAR_MONTH", "PHARMACY_ACCOUNT_TYPE", "CONTRACTOR_CODE",
                                     "CONTRACTOR_NAME", "POSTCODE", "ITEMS"])
    out = pd.concat(parciales, ignore_index=True)
    out = (out.groupby(["YEAR_MONTH", "PHARMACY_ACCOUNT_TYPE", "CONTRACTOR_CODE",
                        "CONTRACTOR_NAME", "POSTCODE"], dropna=False)["VALUE"]
           .sum().reset_index().rename(columns={"VALUE": "ITEMS"}))
    return out


if __name__ == "__main__":
    zip_path, member, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    out = procesar(zip_path, member)
    stem = member.split("/")[-1].replace(".csv", "")
    out.to_csv(f"{outdir}/{stem}.csv", index=False)
    print(f"{stem}: {len(out)} farmacias")
