"""Une narración, música, mapas, gráficos animados y subtítulos en un video vertical de 1080 × 1920.

Entradas: salidas/guion_narrado.json, salidas/escena_N.wav, recursos/visuales/*.png, ../capturas/*.png y ../datos/procesados/*.csv
Salidas: reel.mp4, subtitulos.srt, portada.png, recursos/musica.wav, salidas/cuadro_*.png
Uso: python armar_reel.py [--solo-cuadros]
"""
import csv
import json
import pathlib
import re
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw, ImageFilter, ImageFont

aqui = pathlib.Path(__file__).parent
raiz = aqui.parent
sal, vis, cap = aqui / "salidas", aqui / "recursos/visuales", raiz / "capturas"
ff = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
X0, ANCHO = 80, 880
ALTO_MAPA = 1080
FONDO, TINTA, SUAVE, NARANJA, ORO, PANEL = (19, 21, 22), (248, 245, 238), (190, 194, 196), (255, 122, 58), (242, 190, 72), (20, 22, 24, 215)
PROV = (255, 192, 158)
AZUL, AZUL2 = (86, 156, 240), (176, 201, 233)
PAUSA, INICIO, FINAL = 0.4, 0.5, 1.8
F = "C:/Windows/Fonts/"
fuente = lambda n, t: ImageFont.truetype(F + n, t)
SERIF_B, SANS, SANS_B = "georgiab.ttf", "arial.ttf", "arialbd.ttf"
guion = json.loads((sal / "guion_narrado.json").read_text(encoding="utf-8"))
escenas = guion["escenas"]


def tabla(nombre):
    with (raiz / "datos/procesados" / nombre).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- Datos reales para los gráficos ----------
det = tabla("detecciones_peru.csv")
ANIOS = list(range(2019, 2027))


def serie(cond):
    c = {a: 0 for a in ANIOS}
    for r in det:
        a = int(r["onset_year"])
        if a in c and cond(r):
            c[a] += 1
    return [(("’" + str(a)[2:]), c[a], a >= 2025) for a in ANIOS]


g_nacional = serie(lambda r: True)
g_puerto = serie(lambda r: r["prov"] == "PUERTO INCA")
g_tamb = serie(lambda r: r["nombre_anp"] == "TAMBOPATA")
mdd_t, mdd_f = {a: 0 for a in ANIOS}, {a: 0 for a in ANIOS}
for r in det:
    a = int(r["onset_year"])
    if a in mdd_t and r["dep"] == "MADRE DE DIOS":
        mdd_t[a] += 1
        mdd_f[a] += r["en_corredor"] == "False"
g_corr = [(("’" + str(a)[2:]), 100 * mdd_f[a] / mdd_t[a], a >= 2025) for a in ANIOS]
assert sum(v for _, v, p in g_tamb if not p) == 16 and sum(v for _, v, p in g_tamb if p) == 212
assert round(g_corr[-1][1]) == 50 and round(g_corr[5][1]) == 28
assert sum(v for _, v, _ in g_puerto[5:]) == 431
reg = tabla("reinfo_departamento.csv")
pad_v, pad_s = sum(int(r["vigentes"]) for r in reg), sum(int(r["suspendidos"]) for r in reg)
hoy = {r["estado"]: int(r["total"]) for r in tabla("reinfo_web_totales.csv")}
assert pad_v + pad_s == 87334 and hoy["TODOS"] == 31600


def panel_barras(datos, titulo, prog=1.0, w=560, h=360):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 18, fill=PANEL)
    d.text((22, 16), titulo, font=fuente(SANS_B, 26), fill=TINTA)
    m = max(v for _, v, _ in datos) or 1
    x0, base, ih = 22, h - 44, h - 124
    bw = (w - 44) / len(datos)
    fv, fe = fuente(SANS_B, 22), fuente(SANS, 21)
    for i, (e, v, prov) in enumerate(datos):
        alto = ih * v / m * min(1, prog * 1.15)
        x = x0 + i * bw
        d.rounded_rectangle((x + 5, base - max(alto, 2), x + bw - 5, base), 4, fill=PROV if prov else NARANJA)
        if prog >= 1 or alto > 2:
            d.text((x + bw / 2, base - alto - 6), f"{v:,}" if len(datos) > 0 else "", font=fv, fill=TINTA, anchor="ms")
        d.text((x + bw / 2, base + 26), e, font=fe, fill=SUAVE, anchor="ms")
    return im


def panel_linea(datos, titulo, prog=1.0, w=560, h=360):
    im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * 2 - 1, h * 2 - 1), 36, fill=PANEL)
    d.text((44, 32), titulo, font=fuente(SANS_B, 52), fill=TINTA)
    x0, x1, base, tope = 60, w * 2 - 150, h * 2 - 90, 200
    X = lambda i: x0 + (x1 - x0) * i / (len(datos) - 1)
    Y = lambda v: base - (base - tope) * v / 60
    for v in (0, 20, 40, 60):
        d.line((x0, Y(v), x1, Y(v)), fill=(80, 84, 86), width=2)
    n = 1 + (len(datos) - 1) * min(1, prog * 1.15)
    pts = []
    for i in range(int(n)):
        pts.append((X(i), Y(datos[i][1])))
    if n < len(datos) and int(n) < len(datos):
        f = n - int(n)
        a, b = datos[int(n) - 1][1], datos[int(n)][1]
        pts.append((X(int(n) - 1 + f), Y(a + (b - a) * f)))
    d.line(pts, fill=NARANJA, width=9, joint="curve")
    cx, cy = pts[-1]
    d.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=NARANJA, outline=TINTA, width=4)
    if prog >= 0.8:
        d.text((X(5), Y(datos[5][1]) - 28), f"{datos[5][1]:.0f} %", font=fuente(SANS_B, 46), fill=TINTA, anchor="ms")
        d.text((X(7) + 24, Y(datos[7][1]) + 16), f"{datos[7][1]:.0f} %", font=fuente(SANS_B, 50), fill=TINTA)
    for i, (e, _, _) in enumerate(datos):
        d.text((X(i), base + 52), e, font=fuente(SANS, 42), fill=SUAVE, anchor="ms")
    return im.resize((w, h), Image.LANCZOS)


def panel_padron(prog=1.0):
    im = Image.new("RGBA", (W - 2 * X0, 760), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ancho = W - 2 * X0
    filas = [("Febrero de 2025", pad_v, pad_s), ("Noviembre de 2026", hoy["VIGENTE"], hoy["SUSPENDIDO"])]
    d.text((0, 0), "El padrón del REINFO", font=fuente(SERIF_B, 56), fill=TINTA)
    for k, (t, a, b) in enumerate(filas):
        y = 120 + k * 310
        d.text((0, y), t, font=fuente(SANS_B, 40), fill=SUAVE)
        e = (ancho - 10) / (pad_v + pad_s) * min(1, prog * 1.2)
        wa, wb = a * e, b * e
        d.rounded_rectangle((0, y + 62, max(wa, 4), y + 162), 8, fill=AZUL)
        d.rounded_rectangle((wa + 6, y + 62, wa + 6 + max(wb, 4), y + 162), 8, fill=AZUL2)
        d.text((0, y + 176), f"{a + b:,}", font=fuente(SERIF_B, 54), fill=TINTA)
        d.text((ancho, y + 190), f"{a:,} vigentes · {b:,} suspendidas", font=fuente(SANS, 31), fill=SUAVE, anchor="ra")
    return im


GRAF = {
    "madre_de_dios": lambda p: panel_barras(g_nacional, "Detecciones nuevas, Perú", p, w=760, h=380),
    "puerto_inca": lambda p: panel_barras(g_puerto, "Nuevas en Puerto Inca", p, w=660),
    "tambopata": lambda p: panel_barras(g_tamb, "Nuevas en la R. N. Tambopata", p, w=660),
    "corredor": lambda p: panel_linea(g_corr, "Fuera del corredor, Madre de Dios", p, w=660),
}
CUADRE = {  # imagen, centro x, centro y, ancho inicial, ancho final
    "peru": ("peru", 690, 610, 900, 780),
    "madre_de_dios": ("madre_de_dios", 680, 560, 1040, 900),
    "puerto_inca": ("puerto_inca", 680, 620, 1100, 860),
    "tambopata": ("tambopata", 700, 560, 860, 720),
    "corredor": ("corredor", 680, 600, 1100, 950),
}

# ---------- Música original: acordes suaves generados por código, sin obras de terceros ----------
def musica(segundos, destino, sr=44100):
    n = int(segundos * sr)
    t = np.arange(n) / sr
    salida = np.zeros(n)
    prog = [(110.0, 130.81, 164.81), (87.31, 130.81, 174.61), (98.0, 146.83, 196.0), (82.41, 123.47, 164.81)]
    dur = 6.0
    rng = np.random.default_rng(7)
    for k in range(int(segundos / dur) + 1):
        a, b = int(k * dur * sr), min(n, int((k + 1.4) * dur * sr))
        if a >= n:
            break
        tt = t[a:b] - t[a]
        env = np.minimum(tt / 2.0, 1) * np.minimum((tt[-1] - tt) / 2.2 + 1e-3, 1)
        for f in prog[k % len(prog)]:
            for det_c in (-0.6, 0.6):
                salida[a:b] += env * 0.11 * np.sin(2 * np.pi * (f + det_c) * tt + rng.uniform(0, 6.28))
            salida[a:b] += env * 0.025 * np.sin(2 * np.pi * f * 2 * tt)
    pulso = (np.sin(2 * np.pi * t / 3.0) > 0.985) * 1.0
    grave = np.convolve(pulso, np.exp(-np.arange(int(sr * 0.5)) / (sr * 0.12)), mode="same")
    salida += 0.22 * grave * np.sin(2 * np.pi * 55 * t)
    salida *= np.minimum(t / 2.5, 1) * np.minimum((segundos - t) / 3.0, 1)
    salida = salida / np.abs(salida).max() * 0.8
    sf.write(destino, salida.astype(np.float32), sr)


# ---------- Audio ----------
partes, tiempos, t, sr = [], [], INICIO, None
for i, e in enumerate(escenas, 1):
    a, sr = sf.read(sal / f"escena_{i}.wav", dtype="float32")
    if not partes:
        partes.append(np.zeros(int(INICIO * sr), np.float32))
    partes += [a, np.zeros(int(PAUSA * sr), np.float32)]
    tiempos.append((t, t + len(a) / sr))
    t += len(a) / sr + PAUSA
partes.append(np.zeros(int(FINAL * sr), np.float32))
crudo = np.concatenate(partes)
duracion = len(crudo) / sr
print(f"duración {duracion:.1f} s", flush=True)
assert 45 <= duracion <= 75, "La duración debe estar entre 45 y 75 s"
if "--solo-cuadros" not in sys.argv:
    sf.write(sal / "voz_cruda.wav", crudo, sr)
    musica(duracion, aqui / "recursos/musica.wav")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(sal / "voz_cruda.wav"), "-i", str(aqui / "recursos/musica.wav"), "-filter_complex",
                    "[0:a]aresample=48000,loudnorm=I=-14:TP=-1.5:LRA=11,asplit=2[voz][llave];"
                    "[1:a]aresample=48000,loudnorm=I=-30:TP=-6:LRA=7[mus];"
                    "[mus][llave]sidechaincompress=threshold=0.05:ratio=4:attack=30:release=500[musb];"
                    "[voz][musb]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[out]",
                    "-map", "[out]", "-ac", "2", "-ar", "48000", str(sal / "mezcla.wav")], check=True)

# ---------- Palabras y subtítulos ----------
def tokens(frase):
    """Palabras que se muestran, con un peso según lo que se pronuncia."""
    salida = []
    for trozo in re.split(r"(\{[^}]+\})", frase):
        if trozo.startswith("{"):
            hab, mos = trozo[1:-1].split("|")
            ps = mos.split()
            salida += [(p, (len(hab) + 2) / len(ps)) for p in ps]
        else:
            salida += [(p, len(p) + 2) for p in trozo.split()]
    # Un signo pegado a una cifra queda con la palabra anterior
    limpia = []
    for p, w in salida:
        if re.fullmatch(r"[.,:;?!]+", p) and limpia:
            limpia[-1] = (limpia[-1][0] + p, limpia[-1][1] + w)
        else:
            limpia.append((p, w))
    return limpia


whisper = WhisperModel("small", device="cpu", compute_type="int8")
palabras = []
for i, (e, (ini, fin)) in enumerate(zip(escenas, tiempos)):
    a, s = sf.read(sal / f"escena_{i + 1}.wav", dtype="float32")
    a16 = np.interp(np.arange(0, len(a), s / 16000), np.arange(len(a)), a).astype(np.float32)
    marcas = [w for seg in whisper.transcribe(a16, language="es", word_timestamps=True)[0] for w in seg.words]
    h_ini = ini + (marcas[0].start if marcas else 0)
    h_fin = ini + (marcas[-1].end if marcas else fin - ini)
    tk = tokens(e["frase"])
    pesos = np.array([w for _, w in tk], float)
    bordes = h_ini + np.concatenate([[0], np.cumsum(pesos)]) / pesos.sum() * (h_fin - h_ini)
    palabras += [(bordes[k], bordes[k + 1], tk[k][0], i) for k in range(len(tk))]
bloques, actual = [], []
for w in palabras:
    if actual and (len(actual) == 5 or w[3] != actual[-1][3] or re.search(r"[.:?]$", actual[-1][2])):
        bloques.append(actual)
        actual = []
    actual.append(w)
bloques.append(actual)


def srt_t(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


(aqui / "subtitulos.srt").write_text("\n".join(f"{n}\n{srt_t(b[0][0])} --> {srt_t(b[-1][1])}\n{' '.join(w[2] for w in b)}\n" for n, b in enumerate(bloques, 1)), encoding="utf-8")

# ---------- Capas fijas ----------
def envolver(d, texto, f, ancho):
    lineas, linea = [], ""
    for p in texto.split():
        prueba = (linea + " " + p).strip()
        if d.textlength(prueba, font=f) <= ancho:
            linea = prueba
        else:
            lineas.append(linea)
            linea = p
    return lineas + [linea] if linea else lineas


fuentes_img = {k: Image.open(vis / f"{v[0]}.png").convert("RGB") for k, v in CUADRE.items()}
tablero = Image.open(cap / "dashboard_mapa.png").convert("RGB").crop((30, 0, 1290, 1320))
degradado = Image.new("L", (W, ALTO_MAPA), 0)
for y in range(ALTO_MAPA):
    v = 0 if y < 700 else int(255 * ((y - 700) / (ALTO_MAPA - 700)) ** 1.5)
    if y < 230:
        v = max(v, int(170 * (1 - y / 230)))
    degradado.paste(v, (0, y, W, y + 1))
f_marca, f_etq, f_aviso, f_fuente, f_sub = fuente(SANS_B, 31), fuente(SANS, 37), fuente(SANS_B, 29), fuente(SANS, 26), fuente(SANS_B, 60)


def capa_fija(i):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    osc = Image.new("RGBA", (W, ALTO_MAPA), FONDO + (255,))
    osc.putalpha(degradado)
    im.paste(osc, (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, ALTO_MAPA, W, H), fill=FONDO + (255,))
    d.text((X0, 112), "MINERÍA INFORMAL · LO QUE VE EL SATÉLITE", font=f_marca, fill=TINTA)
    paso = ANCHO // len(escenas)
    for k in range(len(escenas)):
        d.rounded_rectangle((X0 + k * paso, 166, X0 + (k + 1) * paso - 10, 174), 4, fill=NARANJA if k <= i else (110, 112, 114))
    e = escenas[i]
    y = 1040
    if e["id"] != "padron":
        for t_ in range(150, 60, -6):
            fc = fuente(SERIF_B, t_)
            if d.textlength(e["cifra"], font=fc) <= ANCHO:
                break
        d.text((X0, y), e["cifra"], font=fc, fill=TINTA, anchor="ls")
        y += 24
        for li in envolver(d, e["etiqueta"], f_etq, ANCHO):
            d.text((X0, y), li, font=f_etq, fill=SUAVE)
            y += 46
    d.rounded_rectangle((X0, 1524, X0 + 330, 1574), 25, fill=(56, 60, 64))
    d.text((X0 + 165, 1549), "Voz generada con IA", font=f_aviso, fill=TINTA, anchor="mm")
    credito = "Eliana Camacho · QLAB PUCP"
    d.text((X0 + 350, 1549), credito, font=f_fuente, fill=SUAVE, anchor="lm")
    if e["id"] == "cierre":
        lineas = ["Datos: Amazon Mining Watch, MINEM/INGEMMET, Banco Mundial y Defensoría.",
                  "Imagen satelital: Esri. Música original generada por código."]
    else:
        lineas = [f"Fuente: {guion['fuente']}", "Imagen satelital: Esri. Detecciones: señales, no prueba de ilegalidad."]
    for k, li in enumerate(lineas):
        d.text((X0, 1592 + k * 34), li, font=f_fuente, fill=SUAVE)
    return im


capas = [capa_fija(i) for i in range(len(escenas))]
paneles_finales = {k: g(1.0) for k, g in GRAF.items()}
padron_final = panel_padron(1.0)


def fondo(i, t0, t1, seg):
    e = escenas[i]
    u = min(1, max(0, (seg - t0) / max(t1 - t0, 0.1)))
    if e["id"] in CUADRE:
        n, cx, cy, w0, w1 = CUADRE[e["id"]]
        w = w0 + (w1 - w0) * u
        h = w * ALTO_MAPA / W
        x, y = max(0, min(cx - w / 2, 1365 - w)), max(0, cy - h / 2)
        return fuentes_img[e["id"]].resize((W, ALTO_MAPA), Image.BILINEAR, box=(x, y, x + w, min(y + h, 1250)))
    if e["id"] == "cierre":
        desp = 60 + 180 * u
        return tablero.resize((W, ALTO_MAPA), Image.BILINEAR, box=(0, desp, 1260, desp + 1040))
    return Image.new("RGB", (W, ALTO_MAPA), FONDO)


def cuadro(seg):
    i = next((k for k, (a, b) in enumerate(tiempos) if seg < b + PAUSA), len(escenas) - 1)
    t0 = tiempos[i][0]
    t1 = tiempos[i][1] + PAUSA if i < len(escenas) - 1 else duracion
    img = Image.new("RGBA", (W, H), FONDO + (255,))
    img.paste(fondo(i, t0, t1, seg), (0, 0))
    if seg - t0 < 0.3 and i > 0:  # transición suave
        img = Image.blend(img, Image.new("RGBA", (W, H), FONDO + (255,)), max(0, 1 - (seg - t0) / 0.3))
    img.alpha_composite(capas[i])
    e = escenas[i]
    prog = min(1, max(0, (seg - t0 - 0.25) / 1.4))
    if e["id"] in GRAF:
        p = paneles_finales[e["id"]] if prog >= 1 else GRAF[e["id"]](prog)
        img.alpha_composite(p, (W - X0 - p.width + 40, 230))
    if e["id"] == "padron":
        p = padron_final if prog >= 1 else panel_padron(prog)
        img.alpha_composite(p, (X0, 280))
    b = next((b for b in bloques if b[0][0] - 0.05 <= seg <= b[-1][1] + 0.25), None)
    if b:
        d = ImageDraw.Draw(img)
        x, y = X0, 1215 if e["id"] != "padron" else 1160
        for ini, fin, p_, _ in b:
            ap = d.textlength(p_ + " ", font=f_sub)
            if x + ap - X0 > ANCHO + 14:
                x, y = X0, y + 82
            d.text((x, y), p_, font=f_sub, fill=NARANJA if ini <= seg < fin else TINTA)
            x += ap
    return img.convert("RGB")


for i, (a, b) in enumerate(tiempos):
    cuadro(a + (b - a) * 0.7).save(sal / f"cuadro_{i + 1}.png")
print("cuadros de muestra listos", flush=True)
if "--solo-cuadros" in sys.argv:
    raise SystemExit
proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                         "-i", str(sal / "mezcla.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "21",
                         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(aqui / "reel.mp4")], stdin=subprocess.PIPE)
total = int(duracion * FPS)
for n in range(total):
    proc.stdin.write(cuadro(n / FPS).tobytes())
    if n % (FPS * 10) == 0:
        print(f"codificando {n * 100 // total} %", flush=True)
proc.stdin.close()
proc.wait()
cuadro(tiempos[3][0] + 3).save(aqui / "portada.png")
print("reel.mp4", round((aqui / "reel.mp4").stat().st_size / 1e6, 1), "MB", round(duracion, 1), "s", flush=True)
