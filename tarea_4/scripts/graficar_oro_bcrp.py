"""Gráfico BCRP: oro exportado vs. oro con producción declarada, 2015-2024 (toneladas).

    uv run scripts/graficar_oro_bcrp.py        # después de scripts/consultar_bcrp.py (o de la herramienta MCP)

Entra: salidas/brecha_oro_2015_2024.json (respuesta de la herramienta MCP brecha_oro)
Sale:  figuras/bcrp_oro_exportacion_produccion_2015_2024.png
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ENTRADA = Path("salidas/brecha_oro_2015_2024.json")
SALIDA = Path("figuras/bcrp_oro_exportacion_produccion_2015_2024.png")

if not ENTRADA.exists():
    sys.exit(f"Falta {ENTRADA}: corre scripts/consultar_bcrp.py o la herramienta MCP brecha_oro.")
d = pd.DataFrame(json.loads(ENTRADA.read_text(encoding="utf-8"))["datos"])

fig, ax = plt.subplots(figsize=(9, 5))
ax.fill_between(d.anio, d.produccion_t, d.exportacion_t, color="#f6d2c3", label="Brecha (exportado sin producción declarada)")
ax.plot(d.anio, d.exportacion_t, color="#eb6834", lw=2, marker="o", ms=4, label="Exportación (PM40098BA)")
ax.plot(d.anio, d.produccion_t, color="#2a78d6", lw=2, marker="o", ms=4, label="Producción declarada (RD15543DA)")
for _, f in d[d.anio.isin([d.anio.min(), 2020, d.anio.max()])].iterrows():
    ax.annotate(f"{f.brecha_t:.0f} t\n({f.brecha_pct:.0f} %)", (f.anio, (f.produccion_t + f.exportacion_t) / 2),
                ha="center", va="center", fontsize=8, color="#3d3d3a")
ax.set_ylim(0, 240)
ax.set_xticks(d.anio)
ax.set_ylabel("Toneladas finas de oro")
ax.grid(axis="y", color="#e6e6e3", lw=0.8)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, fontsize=8, loc="lower left")
i, f = d.iloc[0], d.iloc[-1]
ax.set_title(f"La brecha entre el oro exportado y el declarado pasó de {i.brecha_pct:.0f} % a {f.brecha_pct:.0f} %, "
             f"{i.anio:.0f}-{f.anio:.0f}\nPerú: exportación y producción de oro, toneladas finas",
             loc="left", fontsize=11, fontweight="bold")
fig.text(0.01, 0.01, "Fuente: BCRP (BCRPData), RD15543DA (producción, MINEM) y PM40098BA (exportación, SUNAT; "
         "miles de onzas troy convertidas a t). Cálculo: herramienta MCP brecha_oro.", fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
SALIDA.parent.mkdir(exist_ok=True)
fig.savefig(SALIDA, dpi=200)
print(f"Figura guardada en {SALIDA}")
print(d.to_string(index=False))
