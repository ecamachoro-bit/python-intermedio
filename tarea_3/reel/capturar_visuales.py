"""Captura del dashboard las imágenes del reel y las capturas para LinkedIn (Chrome sin ventana)."""
import pathlib
import subprocess
import sys
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

aqui = pathlib.Path(__file__).parent
raiz = aqui.parent
vis = aqui / "recursos" / "visuales"
cap = raiz / "capturas"
vis.mkdir(parents=True, exist_ok=True)
cap.mkdir(exist_ok=True)
d = pd.read_csv(raiz / "datos/procesados/detecciones_peru.csv")
pi = d[d.prov == "PUERTO INCA"]
ta = d[(d.nombre_anp == "TAMBOPATA") & (d.onset_year >= 2025)]
VISTAS = {
    "peru": ("", (-74.8, -9.6), 5.05, 2.0),
    "madre_de_dios": ("", (-70.2, -12.9), 8.3, 1.7),
    "puerto_inca": ("desde=2024", (pi.lon.median(), pi.lat.median()), 9.7, 2.6),
    "tambopata": ("desde=2025", (ta.lon.median(), ta.lat.median()), 10.6, 3.6),
    "corredor": ("zona=fuera&desde=2025", (-70.25, -12.9), 8.3, 2.2),
}
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8766", "--bind", "127.0.0.1", "--directory", str(raiz / "web")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)
op = Options()
for x in ["--headless=new", "--window-size=1400,1400", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]:
    op.add_argument(x)
dr = webdriver.Chrome(options=op)


def listo():
    for _ in range(80):
        if dr.execute_script("return !!(window.__listo && window.__mapa && window.__mapa.getLayer('det-c'))"):
            return
        time.sleep(0.5)
    raise RuntimeError("el dashboard no cargó")


try:
    for nombre, (q, c, z, radio) in VISTAS.items():
        dr.get(f"http://127.0.0.1:8766/index.html?fondo=sat&{q}")
        listo()
        dr.execute_script("""
          const s = document.createElement('style');
          s.textContent = '#mapa{position:fixed!important;inset:0;width:100vw!important;height:100vh!important;z-index:9999;border-radius:0!important}.maplibregl-control-container{display:none}.filtros{position:static!important}';
          document.head.appendChild(s);
          const m = window.__mapa; m.resize();
          m.jumpTo({center: arguments[0], zoom: arguments[1]});
          m.setPaintProperty('det-c', 'circle-radius', arguments[2]);
          m.setPaintProperty('det-c', 'circle-color', ['case', ['==', ['get', 'r'], 1], '#ff6a2b', '#ffc9a8']);
          m.setPaintProperty('det-c', 'circle-opacity', 0.95);
          m.setPaintProperty('deps-l', 'line-color', '#ffffff');
          m.setPaintProperty('anp-l', 'line-color', '#6ff0bd');
          m.setPaintProperty('amort-l', 'line-color', '#6ff0bd');
          m.setPaintProperty('cor-l', 'line-color', '#ffd34d');
          m.setPaintProperty('cor-l', 'line-width', 3);
          window.__idle = false; m.once('idle', () => { window.__idle = true; });
          m.triggerRepaint();
        """, [float(c[0]), float(c[1])], z, radio)
        for _ in range(60):
            if dr.execute_script("return window.__idle"):
                break
            time.sleep(0.5)
        time.sleep(1.5)
        dr.save_screenshot(str(vis / f"{nombre}.png"))
        print(nombre, c, flush=True)
    # Capturas normales del tablero para LinkedIn y el cierre del reel
    dr.set_window_size(1320, 1320)
    dr.get("http://127.0.0.1:8766/index.html")
    listo()
    time.sleep(5)
    dr.execute_script("document.querySelector('.filtros').style.position='static'; document.querySelector('#filtros').scrollIntoView({behavior:'instant'})")
    time.sleep(3)
    dr.save_screenshot(str(cap / "dashboard_mapa.png"))
    dr.execute_script("document.querySelector('.rejilla').scrollIntoView({behavior:'instant'})")
    time.sleep(1)
    dr.save_screenshot(str(cap / "dashboard_graficos.png"))
    dr.set_window_size(1320, 1000)
    dr.execute_script("window.scrollTo({top:0,behavior:'instant'})")
    time.sleep(1)
    dr.save_screenshot(str(cap / "dashboard_portada.png"))
finally:
    dr.quit()
    srv.terminate()
