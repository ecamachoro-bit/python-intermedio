"""Serie 2015-2024 de pobreza monetaria por departamento y por grupo minero (ENAHO, sumaria).

Uso (desde la raíz del proyecto, después de limpiar.py para cada año):
    uv run .claude/skills/limpiando-enaho/scripts/serie_pobreza.py

Entra:  salidas/hogares_<anio>.parquet (2015-2024) y referencias/grupos_mineros.csv
Sale:   salidas/pobreza_departamento_2015_2024.csv  (una fila por departamento y año)
        salidas/pobreza_grupo_minero_2015_2024.csv  (una fila por grupo y año)
Método: % de personas pobres = sum(pobre × factor07 × mieperho) / sum(factor07 × mieperho).
El grupo se calcula juntando los hogares de sus departamentos (ponderado por población), no promediando tasas.
"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SALIDAS = Path("salidas")
GRUPOS = Path("referencias/grupos_mineros.csv")
ANIOS = range(2015, 2025)


def tasa(df: pd.DataFrame, por: str) -> pd.DataFrame:
    df = df.assign(peso=df.peso.astype("float64"))
    g = df.assign(num=df.pobre * df.peso).groupby(por)
    out = (100 * g.num.sum() / g.peso.sum()).rename("pobreza_pct").to_frame()
    out["poblacion_exp"] = g.peso.sum().round()
    out["hogares_muestra"] = g.size()
    return out.reset_index()


def main() -> None:
    grupos = pd.read_csv(GRUPOS, dtype=str)
    assert len(grupos) == 25 and grupos.ccdd.is_unique, "grupos_mineros.csv debe tener los 25 departamentos"
    dptos, grps, faltan = [], [], []
    for anio in ANIOS:
        f = SALIDAS / f"hogares_{anio}.parquet"
        if not f.exists():
            faltan.append(anio)
            continue
        hog = pd.read_parquet(f, columns=["departamento", "pobre", "peso"])
        hog = hog.merge(grupos[["ccdd", "grupo"]], left_on="departamento", right_on="ccdd",
                        how="left", validate="m:1")
        assert hog.grupo.notna().all(), f"{anio}: hay departamentos sin grupo"
        d = tasa(hog, "departamento").assign(anio=anio)
        g = tasa(hog, "grupo").assign(anio=anio)
        nac = tasa(hog.assign(grupo="Perú"), "grupo").assign(anio=anio)
        dptos.append(d)
        grps += [g, nac]
    if faltan:
        print(f"AVISO: faltan los años {faltan}. Corre limpiar.py --anio <año> --solo-sumaria. "
              "La serie queda con hueco en esos años; no se interpola.")
    dep = pd.concat(dptos).merge(grupos[["ccdd", "departamento", "grupo"]].rename(
        columns={"ccdd": "departamento", "departamento": "nombre"}), on="departamento")
    grp = pd.concat(grps)
    nombres = dict(zip(grupos.grupo, grupos.grupo_nombre)) | {"Perú": "Perú (nacional)"}
    grp["grupo_nombre"] = grp.grupo.map(nombres)
    dep = dep[["anio", "departamento", "nombre", "grupo", "pobreza_pct", "poblacion_exp", "hogares_muestra"]]
    grp = grp[["anio", "grupo", "grupo_nombre", "pobreza_pct", "poblacion_exp", "hogares_muestra"]]
    dep.round(4).to_csv(SALIDAS / "pobreza_departamento_2015_2024.csv", index=False, encoding="utf-8")
    grp.round(4).to_csv(SALIDAS / "pobreza_grupo_minero_2015_2024.csv", index=False, encoding="utf-8")

    tabla = grp.pivot(index="anio", columns="grupo", values="pobreza_pct")
    print("Pobreza monetaria (% de personas) por grupo minero:")
    print(tabla.round(1).to_string())
    a0, a1 = min(tabla.index), max(tabla.index)
    # Se resta sin redondear y se redondea al final (redondear antes cambia el resultado en 0.1 pp)
    print(f"\nCambio {a0}-{a1} (puntos porcentuales):")
    print((tabla.loc[a1] - tabla.loc[a0]).round(1).to_string())
    print("\nGuardado: salidas/pobreza_departamento_2015_2024.csv y salidas/pobreza_grupo_minero_2015_2024.csv")


if __name__ == "__main__":
    main()
