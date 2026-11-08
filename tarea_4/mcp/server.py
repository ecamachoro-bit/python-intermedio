"""Servidor MCP del BCRP (Tarea 4). Basado en el proyecto de la Sesión 04 y completado.

    uv run pytest mcp -q                                      # 8 pruebas originales + 2 propias
    uv run mcp/server.py                                      # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run mcp/server.py

Herramientas: buscar_series, serie, resumen (las del curso) y tres propias:
  - brecha_oro: compara la exportación de oro (SUNAT, vía BCRP) con la producción declarada (MINEM, vía BCRP)
    y calcula cuánto oro se exporta sin producción registrada.
  - oro_por_departamento: producción de oro declarada por departamento (17 series MINEM vía BCRP).
  - comparar_periodos: compara el promedio de una serie entre dos intervalos.
Recurso: bcrp://serie/{codigo}. Prompt: informe(tema).

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import re
import time
import unicodedata
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

# Series del oro (anuales) que usa la herramienta propia
COD_PRODUCCION_ORO = "RD15543DA"   # Producción minera de oro - total, en gramos finos (fuente MINEM)
COD_EXPORTACION_ORO = "PM40098BA"  # Exportaciones de oro - volumen; el valor está en MILES de onzas troy (ver nota)
GRAMOS_POR_ONZA_TROY = 31.1034768

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, y serie para los datos. Para el oro usa brecha_oro. "
    "No calcules a mano: cita siempre el código de la serie, el periodo y la fuente."))

MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8,
         "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en mcp/datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "oro produccion", "exportaciones oro volumen". frecuencia: "Diaria", "Mensual",
    "Trimestral" o "Anual". Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos.
    Si no hay resultados, prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# ---------------------------------------------------------------- consulta de datos

def _periodo_api(texto, frecuencia):
    """Convierte '2025-01', '2025-01-15', '2025-T1' o '2025' al formato que pide la API."""
    texto = str(texto).strip()
    f = frecuencia.lower()
    if f == "diaria":
        return texto
    if f == "anual":
        return texto[:4]
    if f == "trimestral":
        m = re.match(r"(\d{4})-?T?(\d)", texto)
        return f"{m.group(1)}-{m.group(2)}" if m else texto
    m = re.match(r"(\d{4})-(\d{1,2})", texto)   # mensual
    return f"{m.group(1)}-{int(m.group(2))}" if m else texto


def _periodo_normal(nombre, frecuencia):
    """Convierte 'Ene.2025', '01.Oct.26', 'T1.25' o '2025' a '2025-01', '2026-10-01', '2025-T1' o '2025'."""
    f = frecuencia.lower()
    if f == "diaria":
        d, mes, a = nombre.split(".")
        return f"{2000 + int(a)}-{MESES[mes]:02d}-{int(d):02d}"
    if f == "mensual":
        mes, a = nombre.split(".")
        return f"{a}-{MESES[mes]:02d}"
    if f == "trimestral":
        t, a = nombre.split(".")
        return f"{2000 + int(a) if len(a) == 2 else a}-{t}"
    return nombre


_CACHE: dict = {}


def _bajar(codigo, desde, hasta):
    url = f"{API}/{codigo}/json/{desde}/{hasta}"
    if url in _CACHE:
        return _CACHE[url]
    for intento in range(4):
        r = httpx.get(url, timeout=60, follow_redirects=True)
        try:
            datos = r.json()
            break
        except ValueError:   # la API responde HTML cuando recibe muchos pedidos seguidos
            time.sleep(2 + 3 * intento)
    else:
        raise ToolError(f"La API del BCRP no devolvió datos para {codigo} ({url}). Intenten más tarde.")
    _CACHE[url] = (datos, url)
    return datos, url


def _datos(codigo, desde, hasta):
    ficha = _ficha(codigo)
    frecuencia = ficha["frecuencia"]
    datos, url = _bajar(codigo, _periodo_api(desde, frecuencia), _periodo_api(hasta, frecuencia))
    filas = []
    for p in datos.get("periods", []):
        v = p["values"][0]
        try:
            valor = float(v)
        except (TypeError, ValueError):   # "n.d." = no disponible
            continue
        filas.append({"periodo": _periodo_normal(p["name"], frecuencia), "valor": valor})
    if not filas:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}.")
    return ficha, filas, url


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos oficiales de una serie del BCRP entre dos periodos.

    Formato de los periodos según la frecuencia de la serie: mensual "2025-01", diaria "2026-10-01",
    trimestral "2025-T1", anual "2025". Devuelve el código, el nombre, la frecuencia, la lista de
    {"periodo", "valor"} (sin los "n.d.") y la URL de la fuente.
    """
    ficha, filas, url = _datos(codigo, desde, hasta)
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"],
            "datos": filas, "fuente": url}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Resume una serie del BCRP: primer y último dato, cambio absoluto, variación %, promedio, máximo y mínimo.

    Úsenla siempre en vez de hacer cuentas a mano. Los periodos van como en `serie`.
    """
    ficha, filas, url = _datos(codigo, desde, hasta)
    df = pd.DataFrame(filas)
    primero, ultimo = filas[0], filas[-1]
    imax, imin = df.valor.idxmax(), df.valor.idxmin()
    return {
        "codigo": codigo, "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"],
        "n": len(df), "primero": primero, "ultimo": ultimo,
        "cambio": round(ultimo["valor"] - primero["valor"], 6),
        "variacion_pct": round(100 * (ultimo["valor"] / primero["valor"] - 1), 4) if primero["valor"] else None,
        "promedio": round(float(df.valor.mean()), 6),
        "maximo": {"periodo": df.periodo[imax], "valor": float(df.valor[imax])},
        "minimo": {"periodo": df.periodo[imin], "valor": float(df.valor[imin])},
        "fuente": url,
    }


# ---------------------------------------------------------------- herramientas propias

def calcular_brecha(produccion_grs: dict, exportacion_miles_oz: dict) -> list[dict]:
    """Cálculo puro (sin red), para poder probarlo. Entradas: {año: valor}.

    Producción en gramos finos → toneladas: /1e6.
    Exportación en miles de onzas troy → toneladas: ×1000 ×31.1034768 /1e6.
    """
    filas = []
    for anio in sorted(set(produccion_grs) & set(exportacion_miles_oz)):
        p, e = produccion_grs[anio], exportacion_miles_oz[anio]
        if p is None or e is None:
            continue
        prod_t = p / 1e6
        exp_t = e * 1000 * GRAMOS_POR_ONZA_TROY / 1e6
        brecha_t = exp_t - prod_t
        filas.append({"anio": int(anio), "produccion_t": round(prod_t, 1), "exportacion_t": round(exp_t, 1),
                      "brecha_t": round(brecha_t, 1), "brecha_pct": round(100 * brecha_t / exp_t, 1)})
    return filas


@mcp.tool(annotations=SOLO_LECTURA)
def brecha_oro(anio_inicio: int = 2015, anio_fin: int = 2024) -> dict:
    """Brecha anual entre el oro que exporta el Perú y el oro que declara producir, en toneladas.

    Usa dos series anuales oficiales del BCRP: RD15543DA (producción de oro, gramos finos, MINEM) y
    PM40098BA (volumen exportado de oro; aunque la etiqueta dice "millones de onzas troy", los valores son
    MILES de onzas troy: 6514 en 2024 ≈ 203 t, que es lo que reportan BCRP y SUNAT).
    brecha_t = exportación − producción; brecha_pct = brecha / exportación × 100, es decir, la parte del oro
    exportado que no tiene producción registrada (un indicador indirecto de oro de origen informal o ilegal,
    no una medición directa). Devuelve la tabla por año, el promedio de la brecha y la fuente.
    """
    if anio_inicio > anio_fin:
        raise ToolError("anio_inicio debe ser menor o igual que anio_fin")
    _, prod, url_p = _datos(COD_PRODUCCION_ORO, str(anio_inicio), str(anio_fin))
    _, expo, url_e = _datos(COD_EXPORTACION_ORO, str(anio_inicio), str(anio_fin))
    filas = calcular_brecha({int(x["periodo"]): x["valor"] for x in prod},
                            {int(x["periodo"]): x["valor"] for x in expo})
    if not filas:
        raise ToolError(f"No hay años con producción y exportación de oro entre {anio_inicio} y {anio_fin}.")
    return {
        "series": {"produccion": COD_PRODUCCION_ORO, "exportacion": COD_EXPORTACION_ORO},
        "unidad": "toneladas finas de oro",
        "datos": filas,
        "brecha_promedio_t": round(sum(f["brecha_t"] for f in filas) / len(filas), 1),
        "brecha_promedio_pct": round(sum(f["brecha_pct"] for f in filas) / len(filas), 1),
        "fuente": [url_p, url_e],
    }


# Producción anual de oro por departamento (grs. finos, MINEM vía BCRP). Clave: código INEI del departamento.
ORO_DEPARTAMENTO = {
    "02": ("Áncash", "RD15544DA"), "03": ("Apurímac", "RD15545DA"), "04": ("Arequipa", "RD15546DA"),
    "05": ("Ayacucho", "RD15547DA"), "06": ("Cajamarca", "RD15548DA"), "08": ("Cusco", "RD15549DA"),
    "09": ("Huancavelica", "RD15550DA"), "11": ("Ica", "RD15551DA"), "12": ("Junín", "RD15552DA"),
    "13": ("La Libertad", "RD15553DA"), "14": ("Lambayeque", "RD15554DA"), "15": ("Lima", "RD15555DA"),
    "17": ("Madre de Dios", "RD15556DA"), "18": ("Moquegua", "RD15557DA"), "19": ("Pasco", "RD15558DA"),
    "21": ("Puno", "RD15559DA"), "23": ("Tacna", "RD15560DA"),
}


@mcp.tool(annotations=SOLO_LECTURA)
def oro_por_departamento(anio_inicio: int = 2015, anio_fin: int = 2024) -> dict:
    """Producción de oro declarada por departamento (toneladas) y su participación en el total nacional.

    Usa las 17 series anuales oficiales del BCRP "Producción de productos mineros según departamentos - Oro"
    (RD15544DA ... RD15560DA, gramos finos, fuente MINEM) y el total RD15543DA. Para cada departamento devuelve
    su código INEI (ccdd, el mismo de ubigeo[:2] en la ENAHO), la producción del primer y último año, el
    cambio %, el total del periodo y su participación % en el total nacional del periodo. Los departamentos
    que no figuran (p. ej. Piura, Amazonas) no tienen producción de oro declarada en estas series.
    """
    if anio_inicio > anio_fin:
        raise ToolError("anio_inicio debe ser menor o igual que anio_fin")
    _, total, url_total = _datos(COD_PRODUCCION_ORO, str(anio_inicio), str(anio_fin))
    total_t = sum(x["valor"] for x in total) / 1e6
    filas, fuentes = [], [url_total]
    for ccdd, (nombre, codigo) in ORO_DEPARTAMENTO.items():
        try:
            _, datos, url = _datos(codigo, str(anio_inicio), str(anio_fin))
        except ToolError as e:   # se informa, no se inventa
            filas.append({"ccdd": ccdd, "departamento": nombre, "codigo": codigo, "error": str(e)})
            continue
        fuentes.append(url)
        por_anio = {int(x["periodo"]): x["valor"] / 1e6 for x in datos}
        a0, a1 = min(por_anio), max(por_anio)
        suma = sum(por_anio.values())
        filas.append({
            "ccdd": ccdd, "departamento": nombre, "codigo": codigo,
            "produccion_inicio_t": round(por_anio[a0], 2), "produccion_fin_t": round(por_anio[a1], 2),
            "cambio_pct": round(100 * (por_anio[a1] / por_anio[a0] - 1), 1) if por_anio[a0] else None,
            "total_periodo_t": round(suma, 1),
            "participacion_pct": round(100 * suma / total_t, 1),
        })
    filas.sort(key=lambda f: f.get("total_periodo_t", -1), reverse=True)
    return {"periodo": f"{anio_inicio}-{anio_fin}", "unidad": "toneladas finas de oro",
            "total_nacional_t": round(total_t, 1), "departamentos": filas, "fuente": fuentes}


@mcp.tool(annotations=SOLO_LECTURA)
def comparar_periodos(codigo: str, desde_a: str, hasta_a: str, desde_b: str, hasta_b: str) -> dict:
    """Compara el promedio de una serie del BCRP entre dos intervalos (A y B).

    Ejemplo: producción de oro 2015-2019 frente a 2020-2024. Devuelve el promedio, mínimo y máximo de cada
    intervalo, la diferencia de promedios (B − A) y la variación % del promedio de B respecto de A.
    """
    _, a, url_a = _datos(codigo, desde_a, hasta_a)
    _, b, url_b = _datos(codigo, desde_b, hasta_b)

    def stats(filas, desde, hasta):
        v = [x["valor"] for x in filas]
        return {"desde": desde, "hasta": hasta, "n": len(v), "promedio": round(sum(v) / len(v), 6),
                "minimo": min(v), "maximo": max(v)}

    sa, sb = stats(a, desde_a, hasta_a), stats(b, desde_b, hasta_b)
    return {"codigo": codigo, "nombre": _ficha(codigo)["nombre"], "periodo_a": sa, "periodo_b": sb,
            "diferencia": round(sb["promedio"] - sa["promedio"], 6),
            "variacion_pct": round(100 * (sb["promedio"] / sa["promedio"] - 1), 4) if sa["promedio"] else None,
            "fuente": [url_a, url_b]}


# ---------------------------------------------------------------- recurso y prompt

@mcp.resource("bcrp://serie/{codigo}")
def ficha_serie(codigo: str) -> dict:
    """Ficha descriptiva de una serie del BCRP: nombre, categoría, frecuencia, inicio y última actualización."""
    return _ficha(codigo)


@mcp.prompt()
def informe(tema: str) -> str:
    """Plantilla para un informe breve con series oficiales del BCRP."""
    return (f"Escribe un informe breve sobre: {tema}.\n"
            "1. Usa buscar_series para encontrar los códigos; no los inventes.\n"
            "2. Usa resumen, comparar_periodos o brecha_oro para cada cifra; no hagas cuentas a mano.\n"
            "3. Cita cada cifra con su código de serie, su periodo y la fuente (BCRPData).\n"
            "4. Si una herramienta falla o no hay datos, dilo en vez de estimar.\n"
            "5. Separa los hechos (cifras) de la interpretación, y no presentes asociaciones como causas.")


if __name__ == "__main__":
    mcp.run()
