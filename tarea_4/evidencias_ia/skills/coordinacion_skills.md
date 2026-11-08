# Coordinación de Skills: pedido en lenguaje natural sin base procesada (mapeando-enaho → limpiando-enaho → mapa)

Exportado del historial de Claude Code con `scripts/exportar_conversacion.py`. Se ocultaron correos y tokens; los resultados largos de herramientas están recortados.

**Herramienta:** `Skill`

```json
{
 "skill": "mapeando-enaho"
}
```

<details><summary>Resultado</summary>

```text
Launching skill: mapeando-enaho
```
</details>

## 👤 Usuario · 2026-11-08 22:48:41

Base directory for this skill: C:\Users\User\AppData\Local\Temp\tarea4_demo_coordinacion\.claude\skills\mapeando-enaho

# Mapear la ENAHO

1. Si no existe `salidas/hogares_2024.parquet`, usa primero la skill `limpiando-enaho`.
2. Si falta `datos/peru_departamental_simple.geojson`, pide bajarlo de
   https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson
3. Desde la raíz del proyecto, corre exactamente:
   `uv run C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion/.claude/skills/mapeando-enaho/scripts/mapear.py`
   - Pobreza extrema: agrega `--indicador pobre_extremo`.
   - Con los grupos mineros (borde de color y letra A/B/C/D): agrega `--marcar-grupos`.
4. Muestra la ruta del mapa, los tres departamentos con más y menos pobreza y la comparación con la referencia de
   la Sesión 16 (`salidas/comparacion_mapa_referencia.csv`, deben coincidir 25/25). Si no coincide, el script se
   detiene: revisa la unión, no corrijas a mano.

## Reglas fijas (ya están en el script)

- Une por código: `ubigeo[:2]` con `FIRST_IDDP`, con `validate="1:1"`. Nunca por nombre.
- Exige 25 departamentos y ninguno sin dato; Lima (15) y Callao (07) van separados.
- Pondera con `factor07 × mieperho`.
- Un solo color de claro a oscuro, desde 0; nunca arcoíris. Leyenda con la unidad: «% de personas».
- Nota al pie con la fuente. PNG a 200 dpi en `mapas/`.

**Herramienta:** `Bash`

```json
{
 "command": "cd C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion && ls salidas datos 2>&1 | head -30"
}
```

<details><summary>Resultado</summary>

```text
ls: cannot access 'salidas': No such file or directory
datos:
498-Modulo34.zip
546-Modulo34.zip
603-Modulo34.zip
634-Modulo34.zip
687-Modulo34.zip
737-Modulo34.zip
759-Modulo34.zip
784-Modulo34.zip
906-Modulo34.zip
966-Modulo02.zip
966-Modulo05.zip
966-Modulo34.zip
peru_departamental_simple.geojson
Shell cwd was reset to C:\Users\User\AppData\Local\Temp\tarea4_demo_coordinacion
```
</details>

## 🤖 Claude · 2026-11-08 22:48:51

Falta `salidas/hogares_2024.parquet`, así que primero uso la skill `limpiando-enaho`.

**Herramienta:** `Skill`

```json
{
 "skill": "limpiando-enaho"
}
```

<details><summary>Resultado</summary>

```text
Launching skill: limpiando-enaho
```
</details>

## 👤 Usuario · 2026-11-08 22:48:51

Base directory for this skill: C:\Users\User\AppData\Local\Temp\tarea4_demo_coordinacion\.claude\skills\limpiando-enaho

# Limpiar la ENAHO

El año es `$0`; si viene vacío, usa 2024. Todo se corre desde la raíz del proyecto (`tarea_4/`).

1. Revisa que existan los zip en `datos/` (`<código>-Modulo34.zip`, y para 2024 también `966-Modulo02.zip` y
   `966-Modulo05.zip`). Códigos INEI: 2015=498, 2016=546, 2017=603, 2018=634, 2019=687, 2020=737, 2021=759,
   2022=784, 2023=906, 2024=966. Si faltan, pide bajarlos de
   `https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/<código>-Modulo34.zip` (igual para 02 y 05).
2. Corre exactamente, sin reescribir la limpieza a mano:
   - 2024 completo (personas + hogares): `uv run C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion/.claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024`
   - Otros años (solo hogares): `uv run C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion/.claude/skills/limpiando-enaho/scripts/limpiar.py --anio <año> --solo-sumaria`
   - Serie por departamento y grupo minero (tras limpiar los 10 años):
     `uv run C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion/.claude/skills/limpiando-enaho/scripts/serie_pobreza.py`
   - Empleo minero e informalidad 2024 (módulo 05): `uv run C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion/.claude/skills/limpiando-enaho/scripts/empleo_minero.py`
3. Lee `salidas/validacion.txt` (o `salidas/validacion_<año>.txt`). Cada verificación dice `[PASA]` o `[FALLA]`.
   Si el RESULTADO es FALLA, el script sale con error: **detente** y muestra el reporte. Nunca ajustes cifras
   para que coincidan con la referencia.
4. Responde con las bases limpias; nunca cuentes filas ni promedies sin ponderar:
   - Departamento, área o grupo: `salidas/hogares_<año>.parquet` con `peso` (= factor07 × mieperho, método INEI).
   - Sexo o edad: `salidas/personas_2024.parquet` con `facpob07`.
   - Serie: `salidas/pobreza_departamento_2015_2024.csv` y `salidas/pobreza_grupo_minero_2015_2024.csv`.
   - Empleo minero: `salidas/empleo_minero_2024.csv` (columna `confiable` = al menos 30 mineros en la muestra).
5. Los grupos mineros (A formal de gran escala, B informal con poco oro declarado, C mixto, D resto) están en
   `referencias/grupos_mineros.csv`, con el criterio de cada departamento. Se unen por código `ccdd`, nunca por nombre.
6. Antes de usar una variable que no está en la base, lee [reference.md](reference.md).

Al responder, di la cifra con un decimal, que está ponderada y la fuente: «Fuente: INEI, ENAHO <año>».

**Herramienta:** `Bash`

```json
{
 "command": "cd C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion && uv run C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion/.claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024 2>&1 | tail -40; cat salidas/validacion.txt 2>&1 | tail -30"
}
```

<details><summary>Resultado</summary>

```text
Using CPython 3.14.6 interpreter at: C:\Users\User\anaconda3\python.exe
Creating virtual environment at: .venv
Installed 89 packages in 2.36s
Validaci�n ENAHO 2024 (c�digo INEI 966)

Hogares en la sumaria:            33,691
Poblaci�n expandida (factor07 x mieperho): 34,482,699
Filas en el m�dulo 200:           117,721
Residentes habituales:            108,664
Filas en la base final:           108,664
Poblaci�n expandida (facpob07):   34,147,768
Pobreza (base de personas, facpob07):    27.53 %

Pobreza (sumaria, factor07 x mieperho):  27.58 %
Pobreza extrema (sumaria):               5.50 %
Pobreza SIN ponderar (solo control, no usar): 20.22 %
Cifra oficial INEI:                      27.6 %

Verificaciones:
[PASA] Llaves de hogar �nicas en la sumaria
[PASA] 25 c�digos territoriales (ubigeo[:2] = 01..25): 25 encontrados
[PASA] Factores de expansi�n positivos y sin vac�os
[PASA] Pobreza nacional ponderada a �0.1 pp del INEI (27.6 %): 27.58 %
[PASA] Llaves de persona �nicas
[PASA] Residentes habituales = 108,664: 108,664
[PASA] La uni�n m:1 no perdi� ni duplic� personas: 108,664 -> 108,664
[PASA] Todas las personas encuentran su hogar
[PASA] Pobreza con personas y facpob07 coherente con la sumaria (�0.2 pp): 27.53 %

RESULTADO: OK, todas las verificaciones pasan
Validación ENAHO 2024 (código INEI 966)

Hogares en la sumaria:            33,691
Población expandida (factor07 x mieperho): 34,482,699
Filas en el módulo 200:           117,721
Residentes h
… [recortado: 1047 caracteres más]
```
</details>

## 🤖 Claude · 2026-11-08 22:49:07

Limpieza OK. Ahora el mapa.

**Herramienta:** `Bash`

```json
{
 "command": "cd C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion && uv run C:/Users/User/AppData/Local/Temp/tarea4_demo_coordinacion/.claude/skills/mapeando-enaho/scripts/mapear.py 2>&1 | tail -30; ls mapas; head -30 salidas/comparacion_mapa_referencia.csv"
}
```

<details><summary>Resultado</summary>

```text
Más pobreza:
  CAJAMARCA: 45.0 %
  LORETO: 43.0 %
  PUNO: 39.9 %
Menos pobreza:
  ICA: 6.0 %
  MOQUEGUA: 11.0 %
  MADRE DE DIOS: 11.1 %
Comparación con la referencia de la Sesión 16: 25/25 coinciden (±0.1 pp) -> salidas/comparacion_mapa_referencia.csv
25 departamentos con dato. Mapa guardado en mapas\pobreza_departamento.png
pobreza_departamento.png
ccdd,departamento,referencia_sesion16,calculado,diferencia
01,AMAZONAS,25.7,25.75,0.0
02,ANCASH,22.8,22.77,0.0
03,APURIMAC,24.0,23.96,0.0
04,AREQUIPA,15.8,15.78,0.0
05,AYACUCHO,32.8,32.76,0.0
06,CAJAMARCA,45.0,45.01,0.0
07,CALLAO,33.9,33.86,0.0
08,CUSCO,18.5,18.54,0.0
09,HUANCAVELICA,33.4,33.4,0.0
10,HUANUCO,39.0,38.96,0.0
11,ICA,6.0,6.01,0.0
12,JUNIN,18.5,18.5,0.0
13,LA LIBERTAD,30.2,30.19,0.0
14,LAMBAYEQUE,14.0,14.04,0.0
15,LIMA,27.1,27.07,0.0
16,LORETO,43.0,42.97,0.0
17,MADRE DE DIOS,11.1,11.15,0.0
18,MOQUEGUA,11.0,10.97,0.0
19,PASCO,39.0,38.97,0.0
20,PIURA,31.9,31.86,0.0
21,PUNO,39.9,39.94,0.0
22,SAN MARTIN,22.0,22.02,0.0
23,TACNA,24.0,23.99,0.0
24,TUMBES,26.9,26.9,0.0
25,UCAYALI,27.1,27.07,0.0
Shell cwd was reset to C:\Users\User\AppData\Local\Temp\tarea4_demo_coordinacion
```
</details>

## 🤖 Claude · 2026-11-08 22:49:29

Hice el mapa de la pobreza monetaria por departamento con la ENAHO 2024 y está guardado en `mapas/pobreza_departamento.png` (PNG a 200 dpi).

Las bases pasaron todas las verificaciones: la pobreza nacional ponderada da 27.6 % (27.58 %), igual que la cifra oficial del INEI. La unión se hizo por código de ubigeo, con 25 departamentos y Lima y Callao por separado. Los 25 departamentos coinciden con la referencia de la Sesión 16 (±0.1 pp). El detalle está en `salidas/comparacion_mapa_referencia.csv`.

| | Departamento | Pobreza (% de personas) |
|---|---|---|
| Más pobreza | Cajamarca | 45.0 |
| | Loreto | 43.0 |
| | Puno | 39.9 |
| Menos pobreza | Ica | 6.0 |
| | Moquegua | 11.0 |
| | Madre de Dios | 11.1 |

Las cifras están ponderadas con factor07 × mieperho. Fuente: INEI, ENAHO 2024.

Si quieres, puedo hacer también el mapa de pobreza extrema o marcar los grupos mineros (A/B/C/D).
