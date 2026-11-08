"""Verificación independiente de cifras del informe: NO usa los scripts de las Skills ni el servidor MCP.

ENAHO: lee los .dta originales con pyreadstat (otra librería que la de limpiar.py) y recalcula la pobreza.
BCRP:  pide los datos a la API de BCRPData con urllib (sin httpx ni el MCP) y recalcula la brecha y los cambios.
    uv run evaluacion/verificar_cifras.py
"""
import io, json, sys, tempfile, urllib.request, zipfile
from pathlib import Path
import pandas as pd, pyreadstat

sys.stdout.reconfigure(encoding="utf-8")
GRUPOS = pd.read_csv("referencias/grupos_mineros.csv", dtype=str).set_index("ccdd").grupo

def sumaria(codigo, anio):
    with zipfile.ZipFile(f"datos/{codigo}-Modulo34.zip") as z:
        n = next(x for x in z.namelist() if x.lower().endswith(f"sumaria-{anio}.dta"))
        tmp = Path(tempfile.gettempdir()) / f"verif_{anio}.dta"; tmp.write_bytes(z.read(n))
    df, _ = pyreadstat.read_dta(str(tmp), usecols=["ubigeo", "pobreza", "factor07", "mieperho"])
    df["w"] = df.factor07.astype(float) * df.mieperho.astype(float)
    df["ccdd"] = df.ubigeo.astype(str).str.zfill(6).str[:2]
    df["grupo"] = df.ccdd.map(GRUPOS)
    return df

def tasa(d): return 100 * (d.w * (d.pobreza <= 2)).sum() / d.w.sum()

res = []
s24, s15 = sumaria(966, 2024), sumaria(498, 2015)
for g in "AB":
    a, b = tasa(s15[s15.grupo == g]), tasa(s24[s24.grupo == g])
    res.append((f"ENAHO pobreza grupo {g} 2015 / 2024 / cambio", f"{a:.2f} / {b:.2f} / {b - a:+.2f} pp"))
res.append(("ENAHO pobreza Madre de Dios 2024", f"{tasa(s24[s24.ccdd == '17']):.1f} %"))
res.append(("ENAHO pobreza nacional 2024", f"{tasa(s24):.2f} %"))

url = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/RD15543DA-PM40098BA-RD15556DA/json/2015/2024"
d = json.loads(urllib.request.urlopen(url, timeout=60).read().decode("utf-8"))
# La API devuelve las series ordenadas por código, no en el orden pedido: se ubican por su nombre
nombres = [x["name"] for x in d["config"]["series"]]
i_prod = next(i for i, n in enumerate(nombres) if "Total" in n)
i_expo = next(i for i, n in enumerate(nombres) if "Volumen" in n)
i_mdd = next(i for i, n in enumerate(nombres) if "Madre de Dios" in n)
v = {p["name"]: [float(p["values"][i]) for i in (i_prod, i_expo, i_mdd)] for p in d["periods"]}
for anio in ("2015", "2024"):
    prod, expo = v[anio][0] / 1e6, v[anio][1] * 1000 * 31.1034768 / 1e6
    res.append((f"BCRP brecha del oro {anio}", f"{expo - prod:.1f} t = {100 * (expo - prod) / expo:.1f} % del exportado"))
res.append(("BCRP oro Madre de Dios 2015→2024", f"{v['2015'][2] / 1e6:.2f} t → {v['2024'][2] / 1e6:.2f} t "
            f"({100 * (v['2024'][2] / v['2015'][2] - 1):.1f} %)"))
for k, x in res:
    print(f"{k}: {x}")
