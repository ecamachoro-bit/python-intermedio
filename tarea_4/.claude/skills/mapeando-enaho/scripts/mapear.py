"""Mapa de la pobreza monetaria de la ENAHO por departamento.

Uso (desde la raíz del proyecto):
    uv run .claude/skills/mapeando-enaho/scripts/mapear.py

Entra:  salidas/hogares_<anio>.parquet y datos/peru_departamental_simple.geojson
Sale:   mapas/pobreza_departamento.png
"""

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SALIDAS = Path("salidas")
GEOJSON = Path("datos/peru_departamental_simple.geojson")
URL_GEOJSON = (
    "https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
    "sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson"
)
MAPAS = Path("mapas")
INDICADORES = {"pobre": "Pobreza monetaria", "pobre_extremo": "Pobreza extrema"}


def pobreza_por_departamento(anio: int, indicador: str) -> pd.DataFrame:
    """Método oficial del INEI: hogares ponderados con factor07 × mieperho."""
    hog = pd.read_parquet(SALIDAS / f"hogares_{anio}.parquet")
    num = (hog[indicador] * hog.peso).groupby(hog.departamento).sum()
    den = hog.peso.groupby(hog.departamento).sum()
    return (100 * num / den).rename("pobreza").reset_index()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anio", type=int, default=2024)
    parser.add_argument("--indicador", choices=INDICADORES, default="pobre")
    parser.add_argument("--marcar-grupos", action="store_true",
                        help="Escribe la letra del grupo minero (referencias/grupos_mineros.csv) en cada departamento")
    args = parser.parse_args()

    if not (SALIDAS / f"hogares_{args.anio}.parquet").exists():
        sys.exit(f"Falta salidas/hogares_{args.anio}.parquet: usa primero la skill limpiando-enaho.")
    if not GEOJSON.exists():
        sys.exit(f"Falta {GEOJSON}. Bájalo de {URL_GEOJSON}")

    tasas = pobreza_por_departamento(args.anio, args.indicador)
    mapa = gpd.read_file(GEOJSON)
    mapa["FIRST_IDDP"] = mapa.FIRST_IDDP.astype(str).str.zfill(2)

    # Une por código, nunca por nombre: «APURIMAC» no es «Apurímac»
    mapa = mapa.merge(tasas, left_on="FIRST_IDDP", right_on="departamento",
                      how="left", validate="1:1")
    assert len(mapa) == 25, f"Se esperaban 25 departamentos y hay {len(mapa)}"
    sin_dato = mapa.loc[mapa.pobreza.isna(), "NOMBDEP"].tolist()
    assert not sin_dato, f"Departamentos sin dato: {sin_dato}"

    fig, ax = plt.subplots(figsize=(7, 9))
    mapa.plot(
        column="pobreza", cmap="Reds", vmin=0, ax=ax,
        edgecolor="white", linewidth=0.5, legend=True,
        legend_kwds={"label": "% de personas", "shrink": 0.6},
    )
    if args.marcar_grupos:
        grupos = pd.read_csv("referencias/grupos_mineros.csv", dtype=str)
        mapa = mapa.merge(grupos[["ccdd", "grupo"]], left_on="FIRST_IDDP", right_on="ccdd", how="left",
                          validate="1:1")
        assert mapa.grupo.notna().all(), "Hay departamentos sin grupo minero"
        borde = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a"}
        for g, color in borde.items():
            mapa[mapa.grupo == g].boundary.plot(ax=ax, color=color, linewidth=1.8)
        for _, f in mapa.iterrows():
            if f.FIRST_IDDP == "07":   # Callao es muy pequeño: su cifra va en la nota al pie
                continue
            pt = f.geometry.representative_point()
            ax.annotate(f"{f.grupo}\n{f.pobreza:.0f}", (pt.x, pt.y), ha="center", va="center", fontsize=6.5,
                        color="black" if f.pobreza < 30 else "white", fontweight="bold")
        from matplotlib.lines import Line2D
        ax.legend(handles=[Line2D([], [], color=c, lw=2, label=l) for c, l in
                           [("#2a78d6", "A. Formal de gran escala"), ("#eb6834", "B. Informal, poco oro declarado"),
                            ("#1baf7a", "C. Mixto")]] + [Line2D([], [], color="white", label="D. Resto (sin borde)")],
                  loc="lower left", fontsize=7, frameon=False, title="Borde = grupo minero", title_fontsize=7)
    ax.set_axis_off()
    titulo = f"{INDICADORES[args.indicador]} por departamento, Perú {args.anio}"
    if args.marcar_grupos:
        callao = mapa.loc[mapa.FIRST_IDDP == "07", "pobreza"].iloc[0]
        titulo += "\nletra = grupo minero, número = % de personas pobres"
        fig.text(0.02, 0.045, f"Callao (D): {callao:.1f} %.", fontsize=8, color="gray")
    ax.set_title(titulo,
                 loc="left", fontweight="bold")
    fig.text(0.02, 0.02, f"Fuente: INEI, ENAHO {args.anio}. Lima (15) y Callao (07) por separado. "
             "Unión por código ubigeo[:2] = FIRST_IDDP.",
             fontsize=8, color="gray")

    MAPAS.mkdir(exist_ok=True)
    sufijo = ("" if args.indicador == "pobre" else "_extrema") + ("_grupos_mineros" if args.marcar_grupos else "")
    salida = MAPAS / f"pobreza{sufijo}_departamento.png"
    fig.savefig(salida, dpi=200, bbox_inches="tight")
    plt.close(fig)

    orden = mapa.sort_values("pobreza", ascending=False)
    print("Más pobreza:")
    for _, fila in orden.head(3).iterrows():
        print(f"  {fila.NOMBDEP}: {fila.pobreza:.1f} %")
    print("Menos pobreza:")
    for _, fila in orden.tail(3).iloc[::-1].iterrows():
        print(f"  {fila.NOMBDEP}: {fila.pobreza:.1f} %")
    # Comparación con la referencia de la Sesión 16
    ref_path = Path("referencias/pobreza_departamento_2024.csv")
    if args.anio == 2024 and args.indicador == "pobre" and ref_path.exists():
        ref = pd.read_csv(ref_path, dtype={"ccdd": str})
        comp = mapa[["FIRST_IDDP", "pobreza"]].merge(ref, left_on="FIRST_IDDP", right_on="ccdd", validate="1:1")
        comp["diferencia"] = (comp.pobreza.round(1) - comp.pobreza_pct).round(1)
        coinciden = int((comp.diferencia.abs() <= 0.1).sum())
        comp[["ccdd", "departamento", "pobreza_pct", "pobreza", "diferencia"]].rename(
            columns={"pobreza_pct": "referencia_sesion16", "pobreza": "calculado"}).round(2).to_csv(
            SALIDAS / "comparacion_mapa_referencia.csv", index=False, encoding="utf-8")
        print(f"Comparación con la referencia de la Sesión 16: {coinciden}/25 coinciden (±0.1 pp) "
              "-> salidas/comparacion_mapa_referencia.csv")
        assert coinciden == 25, "El mapa no coincide con la referencia de la Sesión 16"
    print(f"25 departamentos con dato. Mapa guardado en {salida}")


if __name__ == "__main__":
    main()
