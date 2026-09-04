"""
Descarga automatica de datasets NHSBSA con localizacion de farmacias.

Usa la API CKAN del Open Data Portal (https://opendata.nhsbsa.net) para
listar TODOS los recursos disponibles de cada dataset y descargarlos.
Segun el propio NHSBSA, el portal ya cubre 2014-2024 en "formato legacy"
y desde enero-2025 en "formato actual" -- todo dentro del mismo dataset,
asi que un solo llamado a la API debería traer la lista completa.

No pude probar este script de punta a punta (mi entorno no tiene salida
a internet) -- si algo falla, mandame el mensaje de error y lo corrijo.

Requisitos: pip install requests
"""
import os
import requests

BASE = "https://opendata.nhsbsa.net/api/3/action"
OUTDIR = "nhsbsa_dispensing_data"

# Datasets a descargar. Se puede comentar el que no interese.
DATASETS = [
    "pharmacy-and-appliance-contractor-dispensing-data",   # actividad por farmacia (el mas relevante para localizacion)
    # "dispensing-doctor-and-personally-administered-padm-dispensing-data",  # medicos rurales dispensadores
]


def listar_recursos(dataset_id):
    """Devuelve la lista de recursos (uno por mes, normalmente) de un dataset."""
    r = requests.get(f"{BASE}/package_show", params={"id": dataset_id}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"La API no pudo resolver el dataset '{dataset_id}': {data}")
    return data["result"]["resources"]


def descargar(url, destino):
    if os.path.exists(destino):
        print(f"  ya existe, salteando: {os.path.basename(destino)}")
        return
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print(f"  descargado: {os.path.basename(destino)} ({os.path.getsize(destino)/1e6:.1f} MB)")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for dataset_id in DATASETS:
        print(f"\n=== {dataset_id} ===")
        carpeta = os.path.join(OUTDIR, dataset_id)
        os.makedirs(carpeta, exist_ok=True)
        recursos = listar_recursos(dataset_id)
        print(f"{len(recursos)} recursos encontrados")
        for rec in recursos:
            url = rec.get("url")
            nombre = rec.get("name", "sin_nombre")
            if not url:
                continue
            ext = url.split(".")[-1].split("?")[0]
            destino = os.path.join(carpeta, f"{nombre}.{ext}")
            try:
                descargar(url, destino)
            except Exception as e:
                print(f"  ERROR con {nombre}: {e}")


if __name__ == "__main__":
    main()
