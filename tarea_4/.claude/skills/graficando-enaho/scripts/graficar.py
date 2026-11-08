"""Grafica la pobreza monetaria de la ENAHO por área, sexo, edad o departamento.

Uso (desde la raíz del proyecto):
    uv run .claude/skills/graficando-enaho/scripts/graficar.py --por area
    uv run .claude/skills/graficando-enaho/scripts/graficar.py --por sexo --indicador pobre_extremo

Entra:  salidas/personas_<anio>.parquet y salidas/hogares_<anio>.parquet
Sale:   figuras/pobreza_<por>_<anio>.png
"""

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SALIDAS = Path("salidas")
FIGURAS = Path("figuras")
COLOR = "#2b5c8a"

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa",
    "05": "Ayacucho", "06": "Cajamarca", "07": "Callao", "08": "Cusco",
    "09": "Huancavelica", "10": "Huánuco", "11": "Ica", "12": "Junín",
    "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
    "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes",
    "25": "Ucayali",
}
GRUPOS_EDAD = [0, 18, 30, 45, 60, 200]
ETIQUETAS_EDAD = ["0-17", "18-29", "30-44", "45-59", "60 a más"]
NOMBRES = {"area": "área", "sexo": "sexo", "edad": "grupo de edad",
           "departamento": "departamento", "grupo_minero": "grupo minero"}
GRUPOS = Path("referencias/grupos_mineros.csv")
INDICADORES = {"pobre": "Pobreza monetaria", "pobre_extremo": "Pobreza extrema"}


def tasa(df: pd.DataFrame, grupo: str, indicador: str, peso: str) -> pd.Series:
    """Porcentaje ponderado de personas con el indicador, por grupo."""
    w = df[peso].astype("float64")
    num = (df[indicador] * w).groupby(df[grupo], observed=True).sum()
    den = w.groupby(df[grupo], observed=True).sum()
    return 100 * num / den


def calcular(por: str, indicador: str, anio: int) -> pd.Series:
    if por in ("area", "departamento", "grupo_minero"):
        # Método oficial del INEI: hogares ponderados con factor07 × mieperho
        df = pd.read_parquet(SALIDAS / f"hogares_{anio}.parquet")
        if por == "grupo_minero":
            g = pd.read_csv(GRUPOS, dtype=str)
            df = df.merge(g[["ccdd", "grupo", "grupo_nombre"]], left_on="departamento", right_on="ccdd",
                          how="left", validate="m:1")
            df["grupo_minero"] = df.grupo + ". " + df.grupo_nombre
        serie = tasa(df, por, indicador, "peso")
    else:
        # La sumaria no trae sexo ni edad: personas ponderadas con facpob07
        df = pd.read_parquet(SALIDAS / f"personas_{anio}.parquet")
        if por == "edad":
            df["edad"] = pd.cut(df.edad, GRUPOS_EDAD, right=False, labels=ETIQUETAS_EDAD)
        serie = tasa(df, por, indicador, "facpob07")
    if por == "departamento":
        serie.index = serie.index.map(DEPARTAMENTOS)
    if por == "edad":
        return serie  # el orden natural de la edad se respeta
    return serie.sort_values()  # en barras horizontales, el mayor queda arriba


def graficar(serie: pd.Series, por: str, indicador: str, anio: int) -> Path:
    horizontal = por in ("departamento", "grupo_minero")
    fig, ax = plt.subplots(figsize=(8, 8 if por == "departamento" else 4.5 if horizontal else 5))
    if horizontal:
        barras = ax.barh(serie.index, serie.values, color=COLOR)
        ax.set_xlim(0, serie.max() * 1.15)
        ax.set_xlabel("% de personas")
    else:
        barras = ax.bar(serie.index.astype(str), serie.values, color=COLOR)
        ax.set_ylim(0, serie.max() * 1.15)
        ax.set_ylabel("% de personas")
    ax.bar_label(barras, labels=[f"{v:.1f} %" for v in serie.values], padding=3)
    ax.set_title(f"{INDICADORES[indicador]} por {NOMBRES[por]}, Perú {anio}",
                 loc="left", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01, f"Fuente: INEI, ENAHO {anio}. Porcentaje ponderado de personas.",
             fontsize=8, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    FIGURAS.mkdir(exist_ok=True)
    sufijo = "" if indicador == "pobre" else "_extrema"
    salida = FIGURAS / f"pobreza{sufijo}_{por}_{anio}.png"
    fig.savefig(salida, dpi=200)
    plt.close(fig)
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--por", choices=NOMBRES, required=True)
    parser.add_argument("--indicador", choices=INDICADORES, default="pobre")
    parser.add_argument("--anio", type=int, default=2024)
    args = parser.parse_args()

    if not (SALIDAS / f"personas_{args.anio}.parquet").exists():
        sys.exit(f"Falta salidas/personas_{args.anio}.parquet: usa primero la skill limpiando-enaho.")

    serie = calcular(args.por, args.indicador, args.anio)
    salida = graficar(serie, args.por, args.indicador, args.anio)
    print(f"{INDICADORES[args.indicador]} por {NOMBRES[args.por]} ({args.anio}):")
    for grupo, valor in serie.items():
        print(f"  {grupo}: {valor:.1f} %")
    print(f"Figura guardada en {salida}")


if __name__ == "__main__":
    main()
