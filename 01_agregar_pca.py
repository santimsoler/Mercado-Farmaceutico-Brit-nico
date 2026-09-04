#!/usr/bin/env python3
"""
Agrega en streaming los archivos PCA (NHS) desde los zips, sin extraerlos a disco.
Produce varios niveles de agregacion + un reporte de integridad por archivo.
"""
import sys, os, io, subprocess, time, json
import pandas as pd

BASE = [
    "YEAR_MONTH", "REGION_NAME", "REGION_CODE",
    "DISPENSER_ACCOUNT_TYPE", "BNF_PRESENTATION_CODE", "BNF_PRESENTATION_NAME",
    "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE",
    "BNF_SECTION_CODE", "BNF_SECTION", "BNF_CHAPTER_CODE", "BNF_CHAPTER",
    "ITEMS", "TOTAL_QUANTITY", "NIC",
]
# La organizacion sub-regional cambia de nombre: STP (hasta 2022-04) -> ICB (desde 2022-05)
ORG = {"STP_CODE": "ORG_CODE", "STP_NAME": "ORG_NAME",
       "ICB_CODE": "ORG_CODE", "ICB_NAME": "ORG_NAME"}
USECOLS = BASE + ["ORG_CODE", "ORG_NAME"]


def leer_encabezado(zip_path, member):
    p = subprocess.Popen(["unzip", "-p", zip_path, member],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    linea = p.stdout.readline().decode("utf-8", "replace")
    p.stdout.close(); p.kill(); p.wait()
    return [c.strip().strip('"').strip() for c in linea.strip().split(",")]

MEASURES = ["ITEMS", "TOTAL_QUANTITY", "NIC"]

# niveles de agregacion: nombre -> columnas clave
NIVELES = {
    "chapter":      ["YEAR_MONTH", "BNF_CHAPTER_CODE", "BNF_CHAPTER"],
    "section":      ["YEAR_MONTH", "BNF_SECTION_CODE", "BNF_SECTION"],
    "chemical":     ["YEAR_MONTH", "BNF_CHEMICAL_SUBSTANCE_CODE", "BNF_CHEMICAL_SUBSTANCE"],
    "presentation": ["YEAR_MONTH", "BNF_PRESENTATION_CODE", "BNF_PRESENTATION_NAME"],
    "region_chap":  ["YEAR_MONTH", "REGION_CODE", "REGION_NAME", "BNF_CHAPTER_CODE"],
    "org":          ["YEAR_MONTH", "ORG_CODE", "ORG_NAME"],
    "dispenser":    ["YEAR_MONTH", "DISPENSER_ACCOUNT_TYPE"],
}

CHUNK = 400_000


def procesar(zip_path, member):
    """Devuelve (dict de DataFrames agregados, dict de diagnostico)."""
    t0 = time.time()
    cols_arch = leer_encabezado(zip_path, member)
    org_cols = [c for c in cols_arch if c in ORG]          # STP_* o ICB_*
    leer = [c for c in BASE if c in cols_arch] + org_cols
    faltantes = [c for c in BASE if c not in cols_arch]
    dtypes = {c: "string" for c in leer if c not in MEASURES}
    dtypes.update({m: "float64" for m in MEASURES})
    esquema = "STP" if any(c.startswith("STP") for c in org_cols) else "ICB"
    if "PHARMACY_ADVANCED_SERVICE" in cols_arch:
        esquema += "+PAS"

    proc = subprocess.Popen(["unzip", "-p", zip_path, member],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    parciales = {k: [] for k in NIVELES}
    filas = 0
    nulos = {}
    ym_vistos = set()
    error = None
    try:
        reader = pd.read_csv(proc.stdout, usecols=leer, dtype=dtypes,
                             chunksize=CHUNK, engine="c")
        for ch in reader:
            ch = ch.rename(columns=ORG)
            filas += len(ch)
            for c in ch.columns:
                nulos[c] = nulos.get(c, 0) + int(ch[c].isna().sum())
            ym_vistos.update(ch["YEAR_MONTH"].dropna().unique().tolist())
            for nombre, claves in NIVELES.items():
                g = ch.groupby(claves, dropna=False, observed=True)[MEASURES].sum().reset_index()
                parciales[nombre].append(g)
            # consolidacion periodica para no acumular memoria
            for nombre, claves in NIVELES.items():
                if len(parciales[nombre]) >= 6:
                    parciales[nombre] = [
                        pd.concat(parciales[nombre], ignore_index=True)
                        .groupby(claves, dropna=False, observed=True)[MEASURES].sum().reset_index()
                    ]
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        proc.wait()

    rc = proc.returncode
    salida = {}
    for nombre, claves in NIVELES.items():
        if parciales[nombre]:
            salida[nombre] = (pd.concat(parciales[nombre], ignore_index=True)
                              .groupby(claves, dropna=False, observed=True)[MEASURES].sum().reset_index())
        else:
            salida[nombre] = pd.DataFrame(columns=claves + MEASURES)

    tot = salida["chapter"][MEASURES].sum() if len(salida["chapter"]) else pd.Series({m: 0.0 for m in MEASURES})
    diag = {
        "archivo": member,
        "zip": os.path.basename(zip_path),
        "filas": filas,
        "unzip_rc": rc,
        "esquema": esquema,
        "cols_faltantes": faltantes,
        "n_cols_archivo": len(cols_arch),
        "error": error,
        "ym_unicos": sorted(ym_vistos),
        "items": float(tot["ITEMS"]),
        "quantity": float(tot["TOTAL_QUANTITY"]),
        "nic": float(tot["NIC"]),
        "nulos_clave": {c: v for c, v in nulos.items() if v > 0},
        "segundos": round(time.time() - t0, 1),
    }
    return salida, diag


def main():
    zip_path, member, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    salida, diag = procesar(zip_path, member)
    stem = member.replace(".csv", "").replace(" ", "_")
    for nombre, df in salida.items():
        d = os.path.join(outdir, nombre)
        os.makedirs(d, exist_ok=True)
        df.to_csv(os.path.join(d, f"{stem}.csv"), index=False)
    with open(os.path.join(outdir, "diag.jsonl"), "a") as f:
        f.write(json.dumps(diag) + "\n")
    print(json.dumps({k: v for k, v in diag.items() if k != "ym_unicos"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
