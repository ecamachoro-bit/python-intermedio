"""Convierte datos/procesados/ en web/data/datos.json y web/data/capas.json, los archivos que usa el dashboard."""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
O, P, W = RAIZ / "datos/originales", RAIZ / "datos/procesados", RAIZ / "web/data"
W.mkdir(parents=True, exist_ok=True)
NOMBRES = {"AMAZONAS": "Amazonas", "ANCASH": "Áncash", "APURIMAC": "Apurímac", "AREQUIPA": "Arequipa", "AYACUCHO": "Ayacucho",
           "CAJAMARCA": "Cajamarca", "CALLAO": "Callao", "CUSCO": "Cusco", "HUANCAVELICA": "Huancavelica", "HUANUCO": "Huánuco",
           "ICA": "Ica", "JUNIN": "Junín", "LA LIBERTAD": "La Libertad", "LAMBAYEQUE": "Lambayeque", "LIMA": "Lima", "LORETO": "Loreto",
           "MADRE DE DIOS": "Madre de Dios", "MOQUEGUA": "Moquegua", "PASCO": "Pasco", "PIURA": "Piura", "PUNO": "Puno",
           "SAN MARTIN": "San Martín", "TACNA": "Tacna", "TUMBES": "Tumbes", "UCAYALI": "Ucayali"}

d = pd.read_csv(P / "detecciones_peru.csv")
reg = pd.read_csv(P / "reinfo_departamento.csv")
con = pd.read_csv(P / "defensoria_conflictos_region.csv")
oro = pd.read_csv(P / "oro_anual.csv")
rej = pd.read_csv(P / "reinfo_rejilla.csv")
web = pd.read_csv(P / "reinfo_web_totales.csv")
rp = pd.read_csv(P / "reinfo_provincia.csv")

deps_lista = sorted(NOMBRES)
provs = sorted(d.prov.unique())
periodos = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "Q125", "Q225", "Q325", "Q425", "Q126", "Q226", "Q326"]
pos = {p: i for i, p in enumerate(periodos)}
# Lima Metropolitana y Lima Provincias se suman porque el REINFO y el satélite usan "LIMA"
con["dep2"] = con.dep.replace({"LIMA METROPOLITANA": "LIMA", "LIMA PROVINCIAS": "LIMA"})
conf = con[con.dep2.isin(NOMBRES)].groupby("dep2").total.sum().to_dict()
otros = con[~con.dep2.isin(NOMBRES)].set_index("region").total.to_dict()

bits = d.en_anp.astype(int) + d.en_amort.astype(int) * 2 + d.en_corredor.astype(int) * 4 + d.en_reserva.astype(int) * 8 + (d.nombre_anp == "TAMBOPATA").astype(int) * 16
datos = {
    "deps": [NOMBRES[k] for k in deps_lista], "provs": [p.title().replace(" Del ", " del ").replace(" De ", " de ").replace("Maranon", "Marañón").replace("Jaen", "Jaén") for p in provs], "periodos": periodos,
    "det": {
        "lon": d.lon.round(3).tolist(), "lat": d.lat.round(3).tolist(), "per": d.onset.astype(str).map(pos).astype(int).tolist(),
        "dep": d.dep.map({k: i for i, k in enumerate(deps_lista)}).astype(int).tolist(), "prov": d.prov.map({k: i for i, k in enumerate(provs)}).astype(int).tolist(),
        "bits": bits.astype(int).tolist(), "km": d.km_reinfo.round(1).tolist(),
    },
    "reinfo": {NOMBRES[r.dep]: {"t": int(r.reinfo), "v": int(r.vigentes), "s": int(r.suspendidos)} for r in reg.itertuples() if r.dep in NOMBRES},
    "rej": {"x": rej.gx.round(2).tolist(), "y": rej.gy.round(2).tolist(), "v": rej.VIGENTE.astype(int).tolist(), "s": rej.SUSPENDIDO.astype(int).tolist()},
    "conflictos": {NOMBRES[k]: int(v) for k, v in conf.items()}, "conflictos_otros": otros,
    "conflictos_mineros": {"meses": ["jul 25", "ago", "set", "oct", "nov", "dic", "ene 26", "feb", "mar", "abr", "may", "jun", "jul"], "n": [50, 50, 50, 53, 54, 56, 59, 59, 57, 57, 52, 50, 51]},
    "oro": {str(int(a)): v for a, v in zip(oro.anio, oro["mean"])},
    "padron_hoy": {w.estado: int(w.total) for w in web.itertuples()},
    "corte_reinfo": "26 feb 2025", "fecha_padron_hoy": web.fecha.iloc[0],
}
(W / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def geo(g, campos, tol):
    g = g[g.geometry.notna()].copy()
    g["geometry"] = g.geometry.buffer(0).simplify(tol)
    g = g[~g.geometry.is_empty]
    return json.loads(g[campos + ["geometry"]].to_json(drop_id=True))


anp = gpd.read_file(O / "anp.geojson")
anp = anp[~anp.CATEGORI.fillna("").str.contains("PRIVADA|MUNICIPAL")]
capas = {
    "anp": geo(anp, ["NOMBRE", "CATEGORI"], 0.005),
    "amort": geo(gpd.read_file(O / "amortiguamiento.geojson"), ["NOMBRE"], 0.005),
    "corredor": geo(gpd.read_file(O / "corredor_mdd.geojson"), ["NOMBRE"], 0.002),
    "deps": geo(gpd.read_file(O / "departamentos.geojson").query("~NM_DEPA.str.startswith('LAG')"), ["NM_DEPA"], 0.01),
}
txt = json.dumps(capas, ensure_ascii=False, separators=(",", ":"))
(W / "capas.json").write_text(txt, encoding="utf-8")
print("datos.json", (W / "datos.json").stat().st_size // 1024, "KB | capas.json", (W / "capas.json").stat().st_size // 1024, "KB")
print("sin depto en NOMBRES:", set(reg.dep) - set(NOMBRES), "| conflictos otros:", otros, "| suma:", sum(conf.values()) + sum(otros.values()))
print("reinfo total", sum(v["t"] for v in datos["reinfo"].values()), "| provincias reinfo", len(rp))
