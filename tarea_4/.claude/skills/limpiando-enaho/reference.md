# Referencia ENAHO 2024

## Columnas de `salidas/personas_2024.parquet`

Una fila por residente habitual (108,664 filas).

| Columna | Qué es |
|---|---|
| conglome, vivienda, hogar, codperso | Llaves (texto, con ceros a la izquierda) |
| ubigeo | Código de distrito (texto, 6 dígitos) |
| departamento | `ubigeo[:2]`: 01 Amazonas … 15 Lima, 07 Callao … 25 Ucayali |
| dominio | 1–3 costa norte/centro/sur, 4–6 sierra, 7 selva, 8 Lima Metropolitana |
| estrato | 1–5 urbano, 6–8 rural |
| area | «Urbana» o «Rural» |
| p203 | Parentesco con el jefe del hogar (1 = jefe) |
| p204, p205, p206 | Preguntas de residencia (ya filtradas) |
| p207, sexo | 1 «Hombre», 2 «Mujer» |
| p208a, edad | Edad en años |
| pobreza | 1 pobre extremo, 2 pobre no extremo, 3 no pobre |
| pobre, pobre_extremo | Booleanos: pobreza ≤ 2 y pobreza == 1 |
| mieperho | Miembros del hogar |
| facpob07 | Factor de expansión de personas: úsalo para toda cifra de personas |
| factor07 | Factor de expansión de hogares |

## Cómo ponderar

```python
import pandas as pd
base = pd.read_parquet("salidas/personas_2024.parquet")
pobreza = 100 * (base.pobre * base.facpob07).sum() / base.facpob07.sum()   # 27.5 %
por_dpto = base.groupby("departamento").apply(
    lambda d: 100 * (d.pobre * d.facpob07).sum() / d.facpob07.sum())
```

La cifra oficial (27.6 %) se calcula en la sumaria con `factor07 × mieperho`; con la base de personas y `facpob07` sale 27.53 %. La diferencia es normal.

## `salidas/hogares_2024.parquet`

Una fila por hogar (33,691), con `departamento`, `area`, `pobre`, `pobre_extremo` y `peso = factor07 × mieperho`. Es el método oficial del INEI: úsala para cifras por departamento o área que deban coincidir con las publicadas (Cusco 18.5 %, Cajamarca 45.0 %, Ica 6.0 %). Para sexo y edad usa la base de personas, porque la sumaria no las trae.

```python
hog = pd.read_parquet("salidas/hogares_2024.parquet")
hog.groupby("departamento").apply(lambda d: 100 * (d.pobre * d.peso).sum() / d.peso.sum())
```

## Variables que no están en la base

Están en los zip de `datos/`; cada uno trae `Diccionario2024.pdf`.

- Gasto e ingreso del hogar (`gashog2d`, `inghog2d`), líneas de pobreza (`linea`, `linpe`): sumaria, módulo 34.
- Estado civil (`p209`), lengua y educación: módulo 02 y módulo 03.

Para agregarlas, edita `COLS_PERSONA` o `COLS_HOGAR` en `scripts/limpiar.py` y vuelve a correrlo. Así la base cambia para todo el equipo, no solo en una respuesta.

## Seis trampas

1. Ceros a la izquierda: las llaves y el ubigeo se leen como texto.
2. La columna del año llega como «aÑo»: el script la normaliza a `anio`.
3. Solo residentes habituales: `(p204==1 & p205==2) | (p204==2 & p206==1)`.
4. Uniones con `validate="m:1"`.
5. Ponderar siempre: 33,691 hogares representan a más de 34 millones de personas.
6. `pobreza` es un código, no un número.

## Serie 2015-2024 y grupos mineros (Tarea 4)

| Archivo | Una fila por | Qué tiene |
|---|---|---|
| `salidas/hogares_<año>.parquet` (2015-2024) | hogar | `departamento`, `area`, `pobre`, `pobre_extremo`, `peso` (float64) |
| `salidas/validacion_<año>.txt` | — | Validación de cada año contra la pobreza oficial del INEI |
| `salidas/pobreza_departamento_2015_2024.csv` | departamento × año | `pobreza_pct`, `poblacion_exp`, `hogares_muestra`, `grupo` |
| `salidas/pobreza_grupo_minero_2015_2024.csv` | grupo × año | Igual, para A, B, C, D y Perú (hogares juntados, no promedio de tasas) |
| `salidas/empleo_minero_2024.csv` | departamento | `% del empleo en minería`, `% informal en minería`, `n_mineros_muestra`, `confiable` |
| `referencias/grupos_mineros.csv` | departamento | `ccdd`, `grupo` (A/B/C/D), `criterio` |

Pobreza oficial del INEI usada para validar (% de personas): 2015 21.8 · 2016 20.7 · 2017 21.7 · 2018 20.5 ·
2019 20.2 · 2020 30.1 · 2021 25.9 · 2022 27.5 · 2023 29.0 · 2024 27.6.

### Módulo 05 (empleo), variables usadas

- `ocu500 == 1` ocupado; `fac500a` factor de expansión del módulo de empleo.
- `p506r4` rama CIIU rev. 4 (4 dígitos sin cero inicial): minería = 710-990 sin 910 (hidrocarburos); metálica = 710, 721, 729.
- `p507` categoría ocupacional; `p510a1` registro del negocio en SUNAT (3 = sin RUC); `p558a5` (5 = no afiliado a pensiones).
- La base pública 2024 **no trae** `ocupinf`: la informalidad es un proxy (independiente sin RUC, dependiente sin
  pensión, familiar no remunerado). No es la tasa oficial del INEI.
