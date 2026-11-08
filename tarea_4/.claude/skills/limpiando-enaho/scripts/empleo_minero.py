"""Empleo minero e informalidad por departamento, ENAHO 2024 módulo 05 (Empleo).

Minería = CIIU rev.4 (p506r4) 0710-0990 sin hidrocarburos (0610, 0620, 0910).
Minería metálica = 0710, 0721, 0729.
Informalidad (proxy; 'ocupinf' no viene en la base pública 2024):
  - empleador/independiente (p507 1-2): informal si su negocio no tiene RUC (p510a1 == 3)
  - dependiente (p507 3,4,6,7): informal si no está afiliado a pensiones (p558a5 == 5)
  - trabajador familiar no remunerado (p507 5): informal
Ponderado con fac500a; solo residentes habituales ocupados (ocu500 == 1).

Uso (desde la raíz del proyecto):
    uv run .claude/skills/limpiando-enaho/scripts/empleo_minero.py
Entra:  datos/966-Modulo05.zip   Sale: salidas/empleo_minero_2024.csv
Aviso: con menos de 30 mineros en la muestra la cifra del departamento es poco precisa (columna confiable).
"""
import io
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pyreadstat

sys.stdout.reconfigure(encoding="utf-8")
ZIP = Path("datos/966-Modulo05.zip")
SALIDA = Path("salidas/empleo_minero_2024.csv")
if not ZIP.exists():
    sys.exit(f"Falta {ZIP}. Bájalo de https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo05.zip")
with zipfile.ZipFile(ZIP) as z:
    nombre = next(n for n in z.namelist() if n.lower().endswith("enaho01a-2024-500.dta"))
    tmp = Path(tempfile.gettempdir()) / "enaho01a-2024-500.dta"
    tmp.write_bytes(z.read(nombre))
DTA = tmp
cols = ["ubigeo", "p204", "p205", "p206", "ocu500", "p506r4", "p507", "p510a1", "p558a5", "fac500a"]
df, _ = pyreadstat.read_dta(DTA, usecols=cols)
for c in cols[1:]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
res = ((df.p204 == 1) & (df.p205 == 2)) | ((df.p204 == 2) & (df.p206 == 1))
df = df[res & (df.ocu500 == 1)].copy()
df["ccdd"] = df.ubigeo.str[:2]
ciiu = df.p506r4
df["minero"] = ciiu.between(710, 990) & ~ciiu.isin([910])
df["minero_metal"] = ciiu.isin([710, 721, 729])
indep = df.p507.isin([1, 2]); dep = df.p507.isin([3, 4, 6, 7])
df["informal"] = (indep & (df.p510a1 == 3)) | (dep & (df.p558a5 == 5)) | (df.p507 == 5)

def resumen(g):
    w = g.fac500a; m = g.minero
    wm = w[m]
    return pd.Series({
        "ocupados_exp": w.sum(),
        "mineros_exp": wm.sum(),
        "pct_empleo_minero": 100 * wm.sum() / w.sum(),
        "pct_empleo_minero_metal": 100 * w[g.minero_metal].sum() / w.sum(),
        "pct_informal_en_mineria": 100 * wm[g.informal[m]].sum() / wm.sum() if wm.sum() else float("nan"),
        "pct_informal_total": 100 * w[g.informal].sum() / w.sum(),
        "n_mineros_muestra": int(m.sum()),
    })

t = df.groupby("ccdd").apply(resumen, include_groups=False)
t["mineros_informales_exp"] = t.mineros_exp * t.pct_informal_en_mineria / 100
t["pct_empleo_minero_informal"] = 100 * t.mineros_informales_exp / t.ocupados_exp
t["confiable"] = t.n_mineros_muestra >= 30
assert len(t) == 25, f"Se esperaban 25 departamentos y hay {len(t)}"
nac = resumen(df)
print("Nacional:", nac.round(2).to_dict())
SALIDA.parent.mkdir(exist_ok=True)
t.round(4).to_csv(SALIDA, encoding="utf-8")
print(t.round(1).sort_values("pct_empleo_minero_informal", ascending=False).to_string())
