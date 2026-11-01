"""Descarga las fuentes originales de la Tarea 3 en datos/originales/.

Fuentes: Amazon Mining Watch (detecciones satelitales), INGEMMET/GEOCATMIN (REINFO, áreas
naturales, reservas, demarcación) y Banco Mundial (precio del oro).

Del REINFO solo se piden campos NO personales: nunca nombres, representantes ni RUC.
Uso: python scripts/obtener_datos.py
"""
import json
import time
import urllib.parse as up
import urllib.request as ur
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ORIG = RAIZ / "datos" / "originales"
UA = {"User-Agent": "Mozilla/5.0 (tarea academica QLAB PUCP)"}
GEO = "https://geocatmin.ingemmet.gob.pe/arcgis/rest/services"
AMW = "https://data.source.coop/earthgenome/amazon-mining-watch/amazon_basin_detections.geojson"
ORO = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
       "related/CMO-Historical-Data-Monthly.xlsx")
DEFENSORIA = "https://www.defensoria.gob.pe/wp-content/uploads/2026/08/Reporte-de-Conflictos-Sociales-n-269.pdf"
CAMPOS_REINFO = ("OBJECTID,M_TIPO_PERSONA,ORIGEN,A_INSCRIPCION,DEPARTAMENTO,PROVINCIA,DISTRITO,ID_DEPA,"
                 "ID_PROV,ID_DIST,FLG_TB,FLG_COOROK,TIPO_ACT,LATITUD_G84,LONGITUD_G84,PUBLICAR,"
                 "FECHA_ACTUALIZACION,ESTADO")
CAMPOS_REINFO = "OBJECTID,ORIGEN,DEPARTAMENTO,PROVINCIA,DISTRITO,TIPO_ACT,FECHA_ACTUALIZACION,ESTADO"
CAPAS = {
    "anp": ("SERV_AREA_RESERVADA", 10, "OBJECTID,CODIGO,NOMBRE,CATEGORI,CLASE,HAS,USO"),
    "amortiguamiento": ("SERV_AREA_RESERVADA", 11, "OBJECTID,CODIGO,NOMBRE,CATEGORI,CLASE,HAS"),
    "reserva_indigena": ("SERV_AREA_RESERVADA", 19, "OBJECTID,NOMBRE,CATEGORI,CLASE"),
    "reserva_territorial": ("SERV_AREA_RESERVADA", 20, "OBJECTID,NOMBRE,CATEGORI,CLASE"),
    "corredor_mdd": ("SERV_CATASTRO_MADRE_DIOS", 1, "OBJECTID,NOMBRE,CATEGORI,NORMA,HAS"),
    "departamentos": ("SERV_CARTOGRAFIA_DEMARCACION_WGS84", 0, "OBJECTID,NM_DEPA,CD_DEPA"),
    "provincias": ("SERV_CARTOGRAFIA_DEMARCACION_WGS84", 1, "OBJECTID,NM_PROV,NM_DEPA,CD_PROV"),
}


def pedir(url, datos=None, intentos=5, espera=60):
    for i in range(intentos):
        try:
            cuerpo = up.urlencode(datos).encode() if datos else None
            with ur.urlopen(ur.Request(url, data=cuerpo, headers=UA), timeout=espera) as r:
                return r.read()
        except Exception as e:  # red inestable del servicio público
            if i == intentos - 1:
                raise
            print("  reintento", i + 1, e)
            time.sleep(3 * (i + 1))


def bajar(url, destino):
    if destino.exists() and destino.stat().st_size > 0:
        print("ya existe", destino.name)
        return
    destino.write_bytes(pedir(url, espera=300))
    print("bajado", destino.name, destino.stat().st_size)


def oids(capa_url):
    return sorted(json.loads(pedir(f"{capa_url}/query", {"where": "1=1", "returnIdsOnly": "true", "f": "json"}))["objectIds"])


def capa_a_geojson(servicio, capa, campos, destino, lote=200, simplificar=None):
    if destino.exists() and destino.stat().st_size > 0:
        print("ya existe", destino.name)
        return
    url = f"{GEO}/{servicio}/MapServer/{capa}"
    ids = oids(url)
    feats = []
    for i in range(0, len(ids), lote):
        q = {"objectIds": ",".join(map(str, ids[i:i + lote])), "outFields": campos, "returnGeometry": "true",
             "outSR": "4326", "f": "geojson"}
        if simplificar:
            q["maxAllowableOffset"] = simplificar
        feats += json.loads(pedir(f"{url}/query", q, espera=120)).get("features", [])
        time.sleep(0.2)
    destino.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")
    print(destino.name, len(feats), "de", len(ids))


def reinfo(destino):
    """Descarga atributos no personales y la posición del punto (los campos de lat/lon vienen vacíos)."""
    if destino.exists() and destino.stat().st_size > 0:
        print("ya existe", destino.name)
        return
    url = f"{GEO}/SERV_REINFO/MapServer/0"
    ids = oids(url)
    filas = []
    for i in range(0, len(ids), 500):
        q = {"objectIds": ",".join(map(str, ids[i:i + 500])), "outFields": CAMPOS_REINFO,
             "returnGeometry": "true", "outSR": "4326", "f": "json"}
        for x in json.loads(pedir(f"{url}/query", q, espera=60))["features"]:
            g = x.get("geometry") or {}
            filas.append({**x["attributes"], "lon": g.get("x"), "lat": g.get("y")})
        time.sleep(0.1)
        if (i // 500) % 20 == 0:
            print("  reinfo", len(filas), "/", len(ids), flush=True)
    import pandas as pd
    pd.DataFrame(filas).to_csv(destino, index=False, encoding="utf-8")
    print(destino.name, len(filas))


if __name__ == "__main__":
    ORIG.mkdir(parents=True, exist_ok=True)
    bajar(AMW, ORIG / "amw_detecciones.geojson")
    bajar(ORO, ORIG / "banco_mundial_cmo.xlsx")
    bajar(DEFENSORIA, ORIG / "defensoria_reporte_269.pdf")
    reinfo(ORIG / "reinfo_sin_datos_personales.csv")
    for nombre, (s, c, f) in CAPAS.items():
        capa_a_geojson(s, c, f, ORIG / f"{nombre}.geojson", lote=25, simplificar=0.001)
    (ORIG / "fuentes.json").write_text(json.dumps({
        "descargado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "amw": AMW, "reinfo": f"{GEO}/SERV_REINFO/MapServer/0", "areas": f"{GEO}/SERV_AREA_RESERVADA/MapServer",
        "oro": ORO, "defensoria": DEFENSORIA,
    }, indent=2), encoding="utf-8")
