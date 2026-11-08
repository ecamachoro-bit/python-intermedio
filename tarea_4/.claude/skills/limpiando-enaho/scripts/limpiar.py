"""Limpia la ENAHO del INEI: une sumaria (módulo 34) y miembros (módulo 02).

Uso (desde la raíz del proyecto):
    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
    uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2019 --solo-sumaria   # años de la serie

Entra:  datos/<codigo>-Modulo34.zip y datos/<codigo>-Modulo02.zip
Sale:   salidas/personas_<anio>.parquet (una fila por residente habitual),
        salidas/hogares_<anio>.parquet (una fila por hogar, con peso oficial)
        y salidas/validacion.txt
"""

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

# Código de la encuesta en el portal de microdatos del INEI
CODIGOS = {2015: 498, 2016: 546, 2017: 603, 2018: 634, 2019: 687,
           2020: 737, 2021: 759, 2022: 784, 2023: 906, 2024: 966}
# Pobreza monetaria oficial del INEI (% de personas), informes técnicos anuales de pobreza
POBREZA_OFICIAL = {2015: 21.8, 2016: 20.7, 2017: 21.7, 2018: 20.5, 2019: 20.2,
                   2020: 30.1, 2021: 25.9, 2022: 27.5, 2023: 29.0, 2024: 27.6}
RESIDENTES_2024 = 108_664
DEPARTAMENTOS = {f"{i:02d}" for i in range(1, 26)}
TOLERANCIA = 0.1

LLAVES_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES_HOGAR + ["codperso"]
LLAVES_TEXTO = LLAVES_PERSONA + ["ubigeo"]

COLS_PERSONA = LLAVES_PERSONA + [
    "p203", "p204", "p205", "p206", "p207", "p208a", "facpob07",
]
COLS_HOGAR = LLAVES_HOGAR + [
    "anio", "ubigeo", "dominio", "estrato", "pobreza", "mieperho", "factor07",
]

DATOS = Path("datos")
SALIDAS = Path("salidas")


def leer_dta(zip_path: Path, patron: str) -> pd.DataFrame:
    """1 · Leer: abre el .dta dentro del zip con las llaves como texto."""
    if not zip_path.exists():
        sys.exit(f"Falta {zip_path}. Bájalo del portal de microdatos del INEI.")
    with zipfile.ZipFile(zip_path) as z:
        nombres = [n for n in z.namelist() if re.search(patron, n, re.IGNORECASE)]
        if not nombres:
            sys.exit(f"No encontré {patron} dentro de {zip_path}")
        with z.open(nombres[0]) as f:
            df = pd.read_stata(io.BytesIO(f.read()), convert_categoricals=False)
    df = normalizar(df)
    for col in LLAVES_TEXTO:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


def normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """2 · Normalizar: minúsculas; «aÑo» llega con la Ñ rota y pasa a anio."""
    df.columns = [re.sub(r"[^a-z0-9_]", "ni", c.lower()) for c in df.columns]
    return df


def filtrar_residentes(personas: pd.DataFrame) -> pd.DataFrame:
    """3 · Filtrar: solo residentes habituales."""
    residente = ((personas.p204 == 1) & (personas.p205 == 2)) | (
        (personas.p204 == 2) & (personas.p206 == 1)
    )
    return personas[residente].copy()


def construir(base: pd.DataFrame) -> pd.DataFrame:
    """5 · Construir variables de análisis."""
    base["departamento"] = base.ubigeo.str[:2]
    base["urbano"] = base.estrato <= 5
    base["area"] = base.urbano.map({True: "Urbana", False: "Rural"})
    if "p207" in base.columns:  # solo la base de personas trae sexo y edad
        base["sexo"] = base.p207.map({1: "Hombre", 2: "Mujer"})
        base["edad"] = base.p208a
    base["pobre"] = base.pobreza <= 2
    base["pobre_extremo"] = base.pobreza == 1
    return base


def pct(indicador: pd.Series, peso: pd.Series) -> float:
    return float(100 * (indicador * peso).sum() / peso.sum())


def verificar(checks: list, nombre: str, ok: bool, detalle: str = "") -> bool:
    checks.append(f"[{'PASA' if ok else 'FALLA'}] {nombre}" + (f": {detalle}" if detalle else ""))
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anio", type=int, default=2024)
    parser.add_argument("--solo-sumaria", action="store_true",
                        help="Solo la sumaria (hogares): para los años de la serie 2015-2023")
    args = parser.parse_args()
    anio = args.anio
    if anio not in CODIGOS:
        sys.exit(f"Año {anio} sin código INEI conocido. Agrégalo en CODIGOS.")
    codigo = CODIGOS[anio]
    checks: list[str] = []
    oficial = POBREZA_OFICIAL.get(anio)

    sumaria = leer_dta(DATOS / f"{codigo}-Modulo34.zip", rf"sumaria-{anio}\.dta$")
    hogares = sumaria[COLS_HOGAR].copy()
    verificar(checks, "Llaves de hogar únicas en la sumaria", not hogares.duplicated(LLAVES_HOGAR).any())
    hogares = construir(hogares)
    hogares["peso"] = hogares.factor07.astype("float64") * hogares.mieperho.astype("float64")
    dptos = set(hogares.departamento.unique())
    verificar(checks, "25 códigos territoriales (ubigeo[:2] = 01..25)", dptos == DEPARTAMENTOS,
              f"{len(dptos)} encontrados")
    verificar(checks, "Factores de expansión positivos y sin vacíos",
              bool(hogares.factor07.notna().all() and (hogares.factor07 > 0).all()))
    pobreza_sumaria = pct(hogares.pobre, hogares.peso)
    extrema_sumaria = pct(hogares.pobre_extremo, hogares.peso)
    pobreza_simple = 100 * hogares.pobre.mean()
    # El INEI publica con un decimal: se compara la cifra redondeada a un decimal
    verificar(checks, f"Pobreza nacional ponderada a ±{TOLERANCIA} pp del INEI ({oficial} %)",
              oficial is not None and abs(round(pobreza_sumaria, 1) - oficial) <= TOLERANCIA + 1e-9,
              f"{pobreza_sumaria:.2f} %")

    reporte = [f"Validación ENAHO {anio} (código INEI {codigo})", "",
               f"Hogares en la sumaria:            {len(hogares):,}",
               f"Población expandida (factor07 x mieperho): {hogares.peso.sum():,.0f}"]

    if not args.solo_sumaria:
        miembros = leer_dta(DATOS / f"{codigo}-Modulo02.zip", rf"enaho01-{anio}-200\.dta$")
        filas_modulo = len(miembros)
        personas = filtrar_residentes(miembros[COLS_PERSONA])
        verificar(checks, "Llaves de persona únicas", not personas.duplicated(LLAVES_PERSONA).any())
        if anio == 2024:
            verificar(checks, f"Residentes habituales = {RESIDENTES_2024:,}", len(personas) == RESIDENTES_2024,
                      f"{len(personas):,}")
        # Unir: cada persona con su hogar; m:1 avisa si un hogar se repite
        base = personas.merge(hogares.drop(columns=["urbano", "area", "pobre", "pobre_extremo", "departamento"]),
                              on=LLAVES_HOGAR, how="left", validate="m:1")
        verificar(checks, "La unión m:1 no perdió ni duplicó personas", len(base) == len(personas),
                  f"{len(personas):,} -> {len(base):,}")
        verificar(checks, "Todas las personas encuentran su hogar", bool(base.pobreza.notna().all()))
        base = construir(base)
        pobreza_personas = pct(base.pobre, base.facpob07)
        verificar(checks, "Pobreza con personas y facpob07 coherente con la sumaria (±0.2 pp)",
                  abs(pobreza_personas - pobreza_sumaria) <= 0.2, f"{pobreza_personas:.2f} %")
        reporte += [f"Filas en el módulo 200:           {filas_modulo:,}",
                    f"Residentes habituales:            {len(personas):,}",
                    f"Filas en la base final:           {len(base):,}",
                    f"Población expandida (facpob07):   {base.facpob07.sum():,.0f}",
                    f"Pobreza (base de personas, facpob07):    {pobreza_personas:.2f} %"]

    reporte += ["",
                f"Pobreza (sumaria, factor07 x mieperho):  {pobreza_sumaria:.2f} %",
                f"Pobreza extrema (sumaria):               {extrema_sumaria:.2f} %",
                f"Pobreza SIN ponderar (solo control, no usar): {pobreza_simple:.2f} %",
                f"Cifra oficial INEI:                      " + (f"{oficial} %" if oficial is not None else "sin dato"),
                "", "Verificaciones:", *checks, ""]
    todo_ok = all(c.startswith("[PASA]") for c in checks)
    reporte.append("RESULTADO: " + ("OK, todas las verificaciones pasan" if todo_ok else
                                    "FALLA: revisar las verificaciones marcadas; no usar la base"))

    SALIDAS.mkdir(exist_ok=True)
    hogares.to_parquet(SALIDAS / f"hogares_{anio}.parquet", index=False)
    nombre_val = "validacion.txt" if not args.solo_sumaria else f"validacion_{anio}.txt"
    if not args.solo_sumaria:
        base.to_parquet(SALIDAS / f"personas_{anio}.parquet", index=False)
    (SALIDAS / nombre_val).write_text("\n".join(reporte) + "\n", encoding="utf-8")
    print("\n".join(reporte))
    if not todo_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
