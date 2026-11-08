"""Evolución 2015-2024 de la pobreza monetaria por grupo minero (ENAHO) y, opcional, la brecha del oro (BCRP).

Uso (desde la raíz del proyecto):
    uv run .claude/skills/graficando-enaho/scripts/serie_grupos.py
    uv run .claude/skills/graficando-enaho/scripts/serie_grupos.py --brecha salidas/brecha_oro_2015_2024.json

Entra:  salidas/pobreza_grupo_minero_2015_2024.csv (de limpiando-enaho/serie_pobreza.py)
        y, opcional, el JSON que devuelve la herramienta MCP brecha_oro
Sale:   figuras/pobreza_grupos_mineros_2015_2024.png
        figuras/brecha_oro_y_pobreza_2015_2024.png (si se pasa --brecha): dos paneles con eje x común,
        nunca dos ejes y en el mismo panel.
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SERIE = Path("salidas/pobreza_grupo_minero_2015_2024.csv")
FIGURAS = Path("figuras")
# Colores categóricos en orden fijo (paleta de referencia validada); Perú en gris discontinuo
ESTILO = {
    "A": ("#2a78d6", "-", "A. Formal de gran escala"),
    "B": ("#eb6834", "-", "B. Informal, poco oro declarado"),
    "C": ("#1baf7a", "-", "C. Mixto"),
    "D": ("#eda100", "-", "D. Resto"),
    "Perú": ("#6b6b6b", "--", "Perú (nacional)"),
}
TINTA = "#3d3d3a"


def panel_pobreza(ax, tabla):
    for g, (color, ls, etiqueta) in ESTILO.items():
        if g in tabla:
            s = tabla[g]
            ax.plot(s.index, s.values, ls, color=color, lw=2, marker="o", ms=4, label=etiqueta)
    # Etiquetas directas al final, separadas al menos 1.6 puntos para que no choquen
    finales = sorted(((tabla[g].iloc[-1], g) for g in ESTILO if g in tabla))
    y_prev = -99
    for v, g in finales:
        y = max(v, y_prev + 1.6)
        ax.annotate(f"{g} {v:.1f}", (tabla.index[-1], v), xytext=(tabla.index[-1] + 0.15, y),
                    textcoords="data", va="center", fontsize=8, color=TINTA)
        y_prev = y
    ax.axvspan(2019.5, 2020.5, color="#e6e6e3", zorder=0)
    ax.text(2020, 2, "COVID-19", ha="center", fontsize=7, color="#6b6b6b")
    ax.set_ylim(0, max(45, tabla.max().max() * 1.1))
    ax.set_ylabel("% de personas en pobreza")
    ax.grid(axis="y", color="#e6e6e3", lw=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brecha", help="JSON devuelto por la herramienta MCP brecha_oro")
    a = p.parse_args()
    if not SERIE.exists():
        sys.exit(f"Falta {SERIE}: usa primero la skill limpiando-enaho (limpiar.py por año y serie_pobreza.py).")
    df = pd.read_csv(SERIE)
    tabla = df.pivot(index="anio", columns="grupo", values="pobreza_pct")
    FIGURAS.mkdir(exist_ok=True)
    nota = ("Fuente: INEI, ENAHO 2015-2024 (sumaria), ponderado con factor07 × mieperho. "
            "Grupos: referencias/grupos_mineros.csv (clasificación 2024).")

    fig, ax = plt.subplots(figsize=(9, 5.2))
    panel_pobreza(ax, tabla)
    ax.set_title("La pobreza bajó en los departamentos de minería formal y subió en el resto, 2015-2024\n"
                 "Pobreza monetaria por grupo de departamentos según su perfil minero",
                 loc="left", fontsize=11, fontweight="bold")
    ax.set_xticks(tabla.index)
    fig.text(0.01, 0.01, nota, fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.03, 0.97, 1))
    salida = FIGURAS / "pobreza_grupos_mineros_2015_2024.png"
    fig.savefig(salida, dpi=200)
    plt.close(fig)
    print(f"Figura guardada en {salida}")

    if a.brecha:
        br = pd.DataFrame(json.loads(Path(a.brecha).read_text(encoding="utf-8"))["datos"])
        br = br[br.anio.between(tabla.index.min(), tabla.index.max())]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8), sharex=True, height_ratios=[1, 1.4])
        barras = ax1.bar(br.anio, br.brecha_pct, color="#7a7a75", width=0.65)
        ax1.bar_label(barras, labels=[f"{v:.0f} %" for v in br.brecha_pct], fontsize=8, padding=2)
        ax1.set_ylim(0, 60)
        ax1.set_ylabel("% del oro exportado\nsin producción declarada")
        ax1.set_title("Oro exportado sin producción declarada (BCRP)", loc="left", fontsize=10)
        ax1.spines[["top", "right"]].set_visible(False)
        panel_pobreza(ax2, tabla)
        ax2.set_title("Pobreza monetaria por grupo minero (ENAHO)", loc="left", fontsize=10)
        ax2.set_xticks(tabla.index)
        fig.suptitle("Mientras crecía la brecha del oro, la pobreza del grupo informal se mantuvo como la más alta",
                     x=0.01, ha="left", fontsize=11, fontweight="bold")
        fig.text(0.01, 0.01, "Fuentes: BCRP, series RD15543DA y PM40098BA (herramienta MCP brecha_oro); "
                 "INEI, ENAHO 2015-2024. Asociación descriptiva, no causal.", fontsize=7, color="gray")
        fig.tight_layout(rect=(0, 0.02, 0.97, 0.97))
        salida2 = FIGURAS / "brecha_oro_y_pobreza_2015_2024.png"
        fig.savefig(salida2, dpi=200)
        plt.close(fig)
        print(f"Figura guardada en {salida2}")

    print("\nPobreza (% de personas) por grupo:")
    print(tabla.round(1).to_string())


if __name__ == "__main__":
    main()
