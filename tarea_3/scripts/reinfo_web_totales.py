"""Consulta el total actual del padrón público del REINFO por estado (solo conteos, sin datos personales).

Sirve para comparar el padrón de hoy con la capa geográfica de GEOCATMIN, cuyo corte es anterior.
"""
import csv
import re
import ssl
import time
import urllib.parse as up
import urllib.request as ur
from datetime import date
from http.cookiejar import CookieJar
from pathlib import Path

URL = "https://pad.minem.gob.pe/REINFO_WEB/Index.aspx"
SALIDA = Path(__file__).resolve().parents[1] / "datos/procesados/reinfo_web_totales.csv"
op = ur.build_opener(ur.HTTPCookieProcessor(CookieJar()), ur.HTTPSHandler(context=ssl.create_default_context()))
op.addheaders = [("User-Agent", "Mozilla/5.0 (tarea academica QLAB PUCP)")]


def ocultos(html):
    return {n: up.unquote(v) for n, v in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]+" value="([^"]*)"', html)}


def total(html):
    m = re.search(r"Total\s*(?:<[^>]+>\s*)*([\d,.]+)", re.sub(r"(?s)<(script|style).*?</\1>", "", html))
    return int(re.sub(r"\D", "", m.group(1))) if m else None


html = op.open(URL, timeout=60).read().decode("utf-8", "replace")
filas = []
for codigo, nombre in (("1", "VIGENTE"), ("0", "SUSPENDIDO"), ("9", "TODOS")):
    campos = {**ocultos(html), "ddllistado": codigo, "ddltipersona": "99", "txtruc": "", "txtdeclarante": "", "txtidunidad": "",
              "txtnomderecho": "", "ddldepartamento": "99", "ddlordenado": "1", "ddlforma": "ASC", "btnBuscar": "Buscar",
              "__EVENTTARGET": "", "__EVENTARGUMENT": ""}
    r = op.open(ur.Request(URL, data=up.urlencode(campos).encode()), timeout=90).read().decode("utf-8", "replace")
    filas.append({"fecha": date.today().isoformat(), "estado": nombre, "total": total(r)})
    print(filas[-1])
    time.sleep(1)
with SALIDA.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["fecha", "estado", "total"])
    w.writeheader()
    w.writerows(filas)
