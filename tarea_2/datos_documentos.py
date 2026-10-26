"""Arma el corpus de 25 documentos de la Tarea 2.

    .venv/Scripts/python datos_documentos.py

- 8 impresos nítidos y 4 manuscritos históricos peruanos de archive.org (dominio público), descargados
  a 1500 px de ancho con pausas de 1.5 s y User-Agent descriptivo.
- 8 fotos con sombra o inclinación y 5 manuscritos propios (capturas de la autora, sin datos personales),
  que se copian desde datos/raw/documentos/propias/.

Todo queda en datos/raw/documentos/ (fuera de Git). Devuelve la tabla de fuentes.
"""
import shutil
import time
from pathlib import Path

import pandas as pd
import requests

CARPETA = Path(__file__).resolve().parent / "datos" / "raw" / "documentos"
UA = {"User-Agent": "tarea2-qlab-pucp/1.0 (curso Python intermedio QLAB PUCP; github.com/ecamachoro-bit)"}

PD_ANTIGUO = "Dominio público (obra anterior a 1900)"
PD_EEUU = "Dominio público en EE. UU. (publicado antes de 1930)"
PROPIA = "Captura propia de la autora, sin datos personales (CC BY 4.0)"

# id: (tipo, identificador en archive.org, página, descripción, licencia)
ARCHIVO = {
    "doc_001": ("impreso", "cartapastoralque00orih", 10, "Carta pastoral del obispo José Calixto de Orihuela, Lima 1820", PD_ANTIGUO),
    "doc_002": ("impreso", "constitucionpoli00peru", 8, "Constitución Política de la República Peruana, 1823 (cap. III-IV)", PD_ANTIGUO),
    "doc_003": ("impreso", "constitucionpoli00peru", 14, "Constitución Política de la República Peruana, 1823 (colegios electorales)", PD_ANTIGUO),
    "doc_004": ("impreso", "basesdelaconstit00peru", 3, "Bases de la Constitución Política de la República Peruana, 1822", PD_ANTIGUO),
    "doc_005": ("impreso", "mercurioperuanod00cale", 12, "Mercurio Peruano n.º 383, Lima 1791", PD_ANTIGUO),
    "doc_006": ("impreso", "lospueblosdelpe00sanmgoog", 20, "Los pueblos del Perú (provincias de Luya y Áncash), 1905", PD_EEUU),
    "doc_007": ("impreso", "elproblemanacio01capegoog", 20, "El problema nacional de la educación pública, Lima 1902", PD_EEUU),
    "doc_008": ("impreso", "itsmodefitzcarra00torr", 12, "Istmo de Fitzcarrald: informe a la Junta de Vías Fluviales, Lima 1903", PD_EEUU),
    "doc_022": ("manuscrito", "diariodeoperacio00peru", 6, "Diario de operaciones del Ejército Real del Perú, 1824 (portada)", PD_ANTIGUO),
    "doc_023": ("manuscrito", "diariodeoperacio00peru", 10, "Diario de operaciones del Ejército Real del Perú, 1824", PD_ANTIGUO),
    "doc_024": ("manuscrito", "exmoseordespuesq00cant", 8, "Ejército Nacional de Lima: resúmenes históricos, marzo 1822", PD_ANTIGUO),
    "doc_025": ("manuscrito", "exmoseordespuesq00cant", 4, "Oficio al virrey del Perú, Jauja 1822", PD_ANTIGUO),
}

# id: (tipo, archivo en propias/, descripción)
PROPIAS = {f"doc_{9 + i:03d}": ("foto", f"foto_{i + 1:02d}", "Foto de celular de un texto impreso, con sombra o inclinación")
           for i in range(8)}
PROPIAS |= {f"doc_{17 + i:03d}": ("manuscrito", f"manuscrito_{i + 1:02d}", "Texto escrito a mano por la autora")
            for i in range(5)}


def _descargar(url, intentos=5):
    for i in range(intentos):
        r = requests.get(url, headers=UA, timeout=120)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(10 * (i + 1))
            continue
        r.raise_for_status()
        return r.content
    raise RuntimeError(f"No se pudo descargar {url}")


def armar() -> pd.DataFrame:
    CARPETA.mkdir(parents=True, exist_ok=True)
    filas = []
    for did, (tipo, ident, pag, desc, lic) in ARCHIVO.items():
        ruta = CARPETA / f"{did}.jpg"
        url = f"https://archive.org/download/{ident}/page/n{pag}_w1500.jpg"
        if not ruta.exists():
            ruta.write_bytes(_descargar(url))
            time.sleep(1.5)
        filas.append({"id": did, "modalidad": "documento", "tipo": tipo, "descripcion": desc,
                      "archivo": f"datos/raw/documentos/{ruta.name}",
                      "fuente_url": f"https://archive.org/details/{ident}/page/n{pag}", "licencia": lic,
                      "acceso": f"Descarga directa: {url} (o ejecutar datos_documentos.py)"})
    for did, (tipo, base, desc) in PROPIAS.items():
        origen = next((p for p in (CARPETA / "propias").glob(base + ".*")), None)
        if origen is None:
            print(f"Falta {base} en {CARPETA / 'propias'}")
            continue
        ruta = CARPETA / f"{did}{origen.suffix.lower()}"
        if not ruta.exists():
            shutil.copy(origen, ruta)
        filas.append({"id": did, "modalidad": "documento", "tipo": tipo, "descripcion": desc,
                      "archivo": f"datos/raw/documentos/{ruta.name}", "fuente_url": "Captura propia",
                      "licencia": PROPIA, "acceso": "Archivo de la autora; muestra publicada en datos/ejemplos/"})
    return pd.DataFrame(filas).sort_values("id", ignore_index=True)


if __name__ == "__main__":
    tabla = armar()
    print(tabla[["id", "tipo", "licencia"]].to_string(index=False))
    print(tabla["tipo"].value_counts().to_string())
