"""Imprime los indicadores, hallazgos y pruebas de sensibilidad a partir de datos/procesados/."""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 220, "display.max_columns", 40, "display.max_rows", 80)
P = Path(__file__).resolve().parents[1] / "datos/procesados"
d = pd.read_csv(P / "detecciones_peru.csv")
reg = pd.read_csv(P / "reinfo_departamento.csv")
con = pd.read_csv(P / "defensoria_conflictos_region.csv")
oro = pd.read_csv(P / "oro_anual.csv", index_col=0)
ori = pd.read_csv(P / "reinfo_origen_estado.csv", index_col=0)
N = len(d)
mdd = d[d.dep == "MADRE DE DIOS"]
print("detecciones:", N, "| REINFO:", int(reg.reinfo.sum()), "| vigentes:", int(reg.vigentes.sum()))

print("== Serie nacional")
s = d.groupby("onset_year").size()
print(pd.DataFrame({"n": s, "acum": s.cumsum(), "conf": d.groupby("onset_year").confidence.median().round(2)}).T)
print("trimestres 2025-26:", d[d.onset_year >= 2025].groupby("onset").size().to_dict())

print("\n== Por departamento")
t = d.groupby("dep").agg(det=("lon", "size"), anp=("en_anp", "sum"), amort=("en_amort", "sum"), reserva=("en_reserva", "sum"),
                         corredor=("en_corredor", "sum"), sin_reg=("sin_registro", "mean"), sin_vig=("sin_vigente", "mean"),
                         km_med=("km_reinfo", "median"))
t = t.join(reg.set_index("dep")[["reinfo", "vigentes"]]).join(con.set_index("dep")[["total"]].rename(columns={"total": "conflictos"}))
t["det_por_vig"] = (t.det / t.vigentes).round(1)
print(t.sort_values("det", ascending=False).round(3))

print("\n== Sensibilidad: % detecciones a más de X km de un punto REINFO")
for km in (1, 2, 5, 10, 20):
    print(km, "km | todas", round((d.km_reinfo > km).mean() * 100, 1), "| fuera MDD", round((d[d.dep != "MADRE DE DIOS"].km_reinfo > km).mean() * 100, 1),
          "| MDD", round((mdd.km_reinfo > km).mean() * 100, 1), "| Puerto Inca", round((d[d.prov == "PUERTO INCA"].km_reinfo > km).mean() * 100, 1),
          "| vs vigente todas", round((d.km_vigente > km).mean() * 100, 1))

print("\n== Madre de Dios: corredor minero por año")
print(mdd.groupby("onset_year").en_corredor.agg(["size", "sum", "mean"]).round(3).T)
print("fuera del corredor total", int((~mdd.en_corredor).sum()), round((~mdd.en_corredor).mean() * 100, 1))

print("\n== Áreas naturales")
print(d[d.en_anp].groupby("nombre_anp").size().sort_values(ascending=False).head(12))
print(d[d.en_anp].groupby("onset_year").size().to_dict())
print("amort por año", d[d.en_amort].groupby("onset_year").size().to_dict())
print("reservas", int(d.en_reserva.sum()))
print("REINFO dentro de ANP", int(reg.en_anp.sum()), "amort", int(reg.en_amort.sum()), "reserva", int(reg.en_reserva.sum()))

print("\n== Provincias con más detecciones nuevas 2024-2026 vs 2018-2023")
pv = d.assign(rec=d.onset_year >= 2024).groupby(["dep", "prov", "rec"]).size().unstack(fill_value=0).rename(columns={False: "hasta2023", True: "desde2024"})
pv["total"] = pv.sum(axis=1)
print(pv.sort_values("desde2024", ascending=False).head(12))

print("\n== Oro vs detecciones nuevas (2019-2024, años confirmados)")
x = pd.DataFrame({"nuevas": s, "oro": oro["mean"]}).loc[2019:2024]
print(x.T.round(0), "corr Pearson", round(x.corr().iloc[0, 1], 2), "Spearman", round(x.corr("spearman").iloc[0, 1], 2), "n", len(x))
x2 = pd.DataFrame({"nuevas": s, "oro": oro["mean"]}).loc[2019:2025]
print("con 2025 provisional:", round(x2.corr().iloc[0, 1], 2)); print("oro", oro["mean"].round(0).to_dict(), oro["count"].to_dict())

print("\n== REINFO")
print(ori)
print(reg.sort_values("reinfo", ascending=False).head(8).to_string())
print("suspendidos %", round(reg.suspendidos.sum() / reg.reinfo.sum() * 100, 1))
print("\n== Desencuentro: top REINFO vs top detecciones")
comb = reg.set_index("dep")[["reinfo", "vigentes"]].join(d.groupby("dep").size().rename("det")).join(con.set_index("dep").total.rename("conflictos")).fillna(0)
comb["pct_reinfo"] = (comb.reinfo / comb.reinfo.sum() * 100).round(1)
comb["pct_det"] = (comb.det / comb.det.sum() * 100).round(1)
print(comb.sort_values("reinfo", ascending=False).head(14))
print("Spearman REINFO-conflictos", round(comb[["reinfo", "conflictos"]].corr("spearman").iloc[0, 1], 2), "| REINFO-det", round(comb[["reinfo", "det"]].corr("spearman").iloc[0, 1], 2))
