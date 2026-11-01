"""Limpia y cruza las fuentes. Escribe tablas en datos/procesados/ (sin datos personales).

Cruces:
- Detecciones satelitales (AMW) x provincias oficiales, áreas naturales, amortiguamiento, reservas
  indígenas y corredor minero de Madre de Dios.
- Detecciones x REINFO: distancia al punto declarado más cercano.
- REINFO x áreas naturales y reservas.
- Detecciones nuevas por año x precio del oro (Banco Mundial).
- Departamentos x conflictos de la Defensoría (reporte n.° 269).
"""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pymupdf
from scipy.spatial import cKDTree
from shapely.validation import make_valid

RAIZ = Path(__file__).resolve().parents[1]
O, P = RAIZ / "datos/originales", RAIZ / "datos/procesados"
P.mkdir(parents=True, exist_ok=True)
UTM = 32718  # metros, para medir distancias en el Perú
UMBRAL_KM = 5
AGUA = ("LAGO", "LAGUNA")
ANIOS = list(range(2018, 2027))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper().strip()
    return re.sub(r"\s+", " ", s)


def capa(nombre):
    g = gpd.read_file(O / f"{nombre}.geojson")
    g = g[g.geometry.notna()].copy()
    g["geometry"] = g.geometry.apply(make_valid)
    return g[~g.geometry.is_empty]


def dentro(pts, pol):
    """Booleano: el punto cae dentro de algún polígono de pol."""
    idx = gpd.sjoin(pts[["geometry"]], pol[["geometry"]], predicate="within").index.unique()
    return pts.index.isin(idx)


def xy(g):
    u = g.to_crs(UTM).geometry
    return np.c_[u.x, u.y]


# ---------- Límites y áreas ----------
deps = capa("departamentos")
deps = deps[~deps.NM_DEPA.str.startswith(AGUA)].dissolve("NM_DEPA").reset_index()
provs = capa("provincias")
anp_todo = capa("anp")
# Las áreas de conservación privadas y municipales tienen otro régimen: se analizan SINANPE y regionales
anp = anp_todo[~anp_todo.CATEGORI.fillna("").str.contains("PRIVADA|MUNICIPAL")].copy()
amort = capa("amortiguamiento")
reservas = pd.concat([capa("reserva_indigena"), capa("reserva_territorial")], ignore_index=True)
corredor = capa("corredor_mdd")

# ---------- Satélite ----------
det = gpd.read_file(O / "amw_detecciones.geojson", columns=["confidence", "onset", "onset_year", "status"])
det["geometry"] = det.representative_point()
det = det[det.geometry.within(deps.union_all())].reset_index(drop=True)
antes = len(det)
det["clave"] = det.geometry.x.round(5).astype(str) + "_" + det.geometry.y.round(5).astype(str)
det = det.drop_duplicates("clave").drop(columns="clave").reset_index(drop=True)
print("detecciones Perú:", len(det), "| duplicados quitados:", antes - len(det))
j = gpd.sjoin(det, provs[["NM_PROV", "NM_DEPA", "geometry"]], predicate="within", how="left")
j = j[~j.index.duplicated()]
det["dep"], det["prov"] = j.NM_DEPA.map(norm), j.NM_PROV.map(norm)
print("detecciones sin provincia:", int(det.dep.eq("NAN").sum()))
det["en_anp"] = dentro(det, anp)
det["en_amort"] = dentro(det, amort) & ~det.en_anp
det["en_reserva"] = dentro(det, reservas)
det["en_corredor"] = dentro(det, corredor)
nom = gpd.sjoin(det[["geometry"]], anp[["NOMBRE", "geometry"]], predicate="within", how="left")
det["nombre_anp"] = nom.groupby(level=0).NOMBRE.first()

# ---------- REINFO ----------
r = pd.read_csv(O / "reinfo_sin_datos_personales.csv")
crudo = len(r)
r = r.drop_duplicates("OBJECTID")
r["dep"], r["prov"], r["dist"] = r.DEPARTAMENTO.map(norm), r.PROVINCIA.map(norm), r.DISTRITO.map(norm)
r["corte"] = pd.to_datetime(r.FECHA_ACTUALIZACION, unit="ms").dt.strftime("%Y-%m-%d")
gr = gpd.GeoDataFrame(r, geometry=gpd.points_from_xy(r.lon, r.lat), crs=4326)
gr["en_peru"] = dentro(gr, deps)
jr = gpd.sjoin(gr[["geometry"]], deps[["NM_DEPA", "geometry"]], predicate="within", how="left")
jr = jr[~jr.index.duplicated()]
gr["dep_geo"] = jr.NM_DEPA.map(norm)
gr["dep_coincide"] = gr.dep == gr.dep_geo
gr["en_anp"] = dentro(gr, anp)
gr["en_amort"] = dentro(gr, amort) & ~gr.en_anp
gr["en_reserva"] = dentro(gr, reservas)
print("REINFO:", crudo, "| corte:", gr.corte.unique().tolist(), "| en Perú:", round(gr.en_peru.mean(), 4),
      "| depto declarado = depto de la coordenada:", round(gr.dep_coincide.mean(), 4))
gv = gr[gr.dep_coincide]  # cruces espaciales: solo coordenadas coherentes con lo declarado

# ---------- Distancia detección -> REINFO más cercano ----------
puntos = xy(det)
det["km_reinfo"] = np.round(cKDTree(xy(gv)).query(puntos)[0] / 1000, 2)
det["km_vigente"] = np.round(cKDTree(xy(gv[gv.ESTADO == "VIGENTE"])).query(puntos)[0] / 1000, 2)
det["sin_registro"] = det.km_reinfo > UMBRAL_KM
det["sin_vigente"] = det.km_vigente > UMBRAL_KM
det["lon"], det["lat"] = det.geometry.x.round(4), det.geometry.y.round(4)
det.drop(columns="geometry").to_csv(P / "detecciones_peru.csv", index=False, encoding="utf-8")

# ---------- Tablas ----------
det.groupby(["dep", "onset_year"]).size().unstack(fill_value=0).reindex(columns=ANIOS, fill_value=0).to_csv(P / "detecciones_dep_anio.csv")
es = lambda v: (lambda s: (s == v).sum())
gr.groupby("dep").agg(reinfo=("ESTADO", "size"), vigentes=("ESTADO", es("VIGENTE")), suspendidos=("ESTADO", es("SUSPENDIDO")),
                      explotacion=("TIPO_ACT", es("EXPLOTACION")), en_anp=("en_anp", "sum"), en_amort=("en_amort", "sum"),
                      en_reserva=("en_reserva", "sum")).reset_index().to_csv(P / "reinfo_departamento.csv", index=False)
gr.groupby(["dep", "prov"]).agg(reinfo=("ESTADO", "size"), vigentes=("ESTADO", es("VIGENTE"))).reset_index().to_csv(P / "reinfo_provincia.csv", index=False)
gr.groupby(["ORIGEN", "ESTADO"]).size().unstack(fill_value=0).to_csv(P / "reinfo_origen_estado.csv")
# Rejilla de unos 5.5 km para el mapa: no se publican puntos individuales del padrón
gr["gx"], gr["gy"] = (gr.lon / 0.05).round() * 0.05, (gr.lat / 0.05).round() * 0.05
gr[gr.en_peru].groupby(["gx", "gy", "ESTADO"]).size().unstack(fill_value=0).reset_index().round(3).to_csv(P / "reinfo_rejilla.csv", index=False)

# Precio del oro: promedio anual en US$/onza
h = pd.read_excel(O / "banco_mundial_cmo.xlsx", sheet_name="Monthly Prices", header=4)
h = h.rename(columns={h.columns[0]: "mes"})[["mes", "Gold"]]
h = h[h.mes.astype(str).str.match(r"^\d{4}M\d{2}$")].copy()
h["Gold"] = pd.to_numeric(h.Gold, errors="coerce")
h["anio"] = h.mes.str[:4].astype(int)
h[h.anio >= 2017].to_csv(P / "oro_mensual.csv", index=False)
h[h.anio.between(2017, 2026)].groupby("anio").Gold.agg(["mean", "count"]).round(1).to_csv(P / "oro_anual.csv")

# Defensoría: Cuadro 3 (conflictos por región)
pdf = pymupdf.open(O / "defensoria_reporte_269.pdf")
filas = re.findall(r"\n([^\n\d%]+?) ?\n(\d+) ?\n([\d.]+)% ?\n(\d+) ?\n(\d+)", pdf[34].get_text())
con = pd.DataFrame(filas, columns=["region", "total", "pct", "activos", "latentes"])
con["dep"] = con.region.map(norm)
con[["total", "activos", "latentes"]] = con[["total", "activos", "latentes"]].astype(int)
con = con[con.dep != "TOTAL"]
assert con.total.sum() == 191, con.total.sum()
con.to_csv(P / "defensoria_conflictos_region.csv", index=False)
print("Defensoría suma:", con.total.sum(), "| regiones:", len(con))
print(re.sub(r"\s+", " ", pdf[46].get_text())[100:600])
print(re.sub(r"\s+", " ", pdf[48].get_text())[100:700])
