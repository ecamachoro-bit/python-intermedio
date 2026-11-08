"""Tabla integrada por departamento y por grupo minero: ENAHO (pobreza, empleo minero) + BCRP (oro declarado).

    uv run scripts/indicadores.py

Entra: salidas/pobreza_departamento_2015_2024.csv, salidas/pobreza_grupo_minero_2015_2024.csv,
       salidas/empleo_minero_2024.csv, salidas/oro_por_departamento_2015_2024.json (herramienta MCP),
       referencias/grupos_mineros.csv
Sale:  salidas/indicadores.csv (25 departamentos) y salidas/indicadores_grupo.csv (4 grupos + Perú)
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
S = Path("salidas")

pob = pd.read_csv(S / "pobreza_departamento_2015_2024.csv", dtype={"departamento": str})
tab = pob.pivot(index="departamento", columns="anio", values="pobreza_pct")
dep = pd.read_csv("referencias/grupos_mineros.csv", dtype=str)[["ccdd", "departamento", "grupo"]]
dep = dep.set_index("ccdd")
dep["pobreza_2015"] = tab[2015]
dep["pobreza_2019"] = tab[2019]
dep["pobreza_2024"] = tab[2024]
dep["cambio_2015_2024_pp"] = tab[2024] - tab[2015]

emp = pd.read_csv(S / "empleo_minero_2024.csv", dtype={"ccdd": str}).set_index("ccdd")
dep["pct_empleo_minero_2024"] = emp.pct_empleo_minero
dep["pct_informal_en_mineria_2024"] = emp.pct_informal_en_mineria
dep["n_mineros_muestra"] = emp.n_mineros_muestra

oro = json.loads((S / "oro_por_departamento_2015_2024.json").read_text(encoding="utf-8"))
o = pd.DataFrame(oro["departamentos"]).set_index("ccdd")
dep["oro_participacion_2015_2024_pct"] = o.participacion_pct
dep["oro_2015_t"] = o.produccion_inicio_t
dep["oro_2024_t"] = o.produccion_fin_t
dep["oro_cambio_2015_2024_pct"] = o.cambio_pct
dep["oro_participacion_2015_2024_pct"] = dep.oro_participacion_2015_2024_pct.fillna(0.0)  # sin serie = 0 declarado
assert len(dep) == 25 and dep.pobreza_2024.notna().all()
dep.round(2).reset_index().to_csv(S / "indicadores.csv", index=False, encoding="utf-8")

# Por grupo: pobreza (de la serie ponderada), oro declarado (suma de toneladas) y empleo minero (ponderado)
grp = pd.read_csv(S / "pobreza_grupo_minero_2015_2024.csv").pivot(index="grupo", columns="anio", values="pobreza_pct")
g = pd.DataFrame({"pobreza_2015": grp[2015], "pobreza_2019": grp[2019], "pobreza_2020": grp[2020],
                  "pobreza_2024": grp[2024]})
g["cambio_2015_2024_pp"] = g.pobreza_2024 - g.pobreza_2015
g["cambio_2019_2024_pp"] = g.pobreza_2024 - g.pobreza_2019
emp = emp.join(dep.grupo)
for col, fn in {"mineros_exp": "sum", "ocupados_exp": "sum", "mineros_informales_exp": "sum"}.items():
    g[col] = emp.groupby("grupo")[col].sum()
g["pct_empleo_minero_2024"] = 100 * g.mineros_exp / g.ocupados_exp
g["pct_informal_en_mineria_2024"] = 100 * g.mineros_informales_exp / g.mineros_exp
dep_oro = dep.reset_index().merge(o[["total_periodo_t"]], left_on="ccdd", right_index=True, how="left")
g["oro_2015_2024_t"] = dep_oro.groupby("grupo").total_periodo_t.sum()
g["oro_participacion_pct"] = 100 * g.oro_2015_2024_t / oro["total_nacional_t"]
g["oro_2015_t"] = dep.groupby("grupo").oro_2015_t.sum()
g["oro_2024_t"] = dep.groupby("grupo").oro_2024_t.sum()
g = g.drop(columns=["mineros_exp", "ocupados_exp", "mineros_informales_exp"])
g.round(2).to_csv(S / "indicadores_grupo.csv", encoding="utf-8")

print("Por grupo:\n" + g.round(1).to_string())
print("\nGrupo B por departamento:\n" + dep[dep.grupo == "B"].round(1).to_string())
print("\nGuardado: salidas/indicadores.csv y salidas/indicadores_grupo.csv")
