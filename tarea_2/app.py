"""Dashboard de la Tarea 2: explora los documentos y audios procesados y la evaluación de los modelos.

    streamlit run app.py

Solo lee los CSV generados por los notebooks: no ejecuta OCR, ASR ni LLM en vivo.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos"
EJEMPLOS = DATOS / "ejemplos"

st.set_page_config(page_title="Voces y documentos peruanos", page_icon="🎙️", layout="wide")


@st.cache_data
def cargar():
    def leer(nombre):
        ruta = DATOS / nombre
        return pd.read_csv(ruta, keep_default_na=False) if ruta.exists() else pd.DataFrame()
    t = {n: leer(f"{n}.csv") for n in ["documentos", "transcripciones", "extraccion_llm", "fuentes", "metricas",
                                         "metricas_detalle", "asr_alternativos", "ocr_alternativo", "auditoria_llm"]}
    t["documentos"]["caracteres"] = t["documentos"]["texto_ocr"].str.len()
    t["transcripciones"]["minutos"] = t["transcripciones"]["duracion_seg"] / 60
    t["transcripciones"]["palabras"] = (t["transcripciones"]["texto_asr"]
                                        .str.replace(r"\[HABLANTE_\d+\]", "", regex=True).str.split().str.len())
    fuentes = t["fuentes"].set_index("id")
    t["transcripciones"]["condicion"] = t["transcripciones"]["id"].map(fuentes["descripcion"].str.split(" — ").str[0])
    t["transcripciones"]["licencia"] = t["transcripciones"]["id"].map(fuentes["licencia"])
    return t


T = cargar()
docs, aud, llm, met, det = T["documentos"], T["transcripciones"], T["extraccion_llm"], T["metricas"], T["metricas_detalle"]
campos_llm = {r.id: json.loads(r.campos_json) for r in llm.itertuples()} if len(llm) else {}


def ejemplo(id_, extensiones):
    return next((p for e in extensiones if (p := EJEMPLOS / f"{id_}{e}").exists()), None)


def valor_metrica(modelo_contiene):
    fila = met[met["modelo"].str.contains(modelo_contiene, regex=False)] if len(met) else met
    return float(fila["CER/WER"].iloc[0]) if len(fila) else None


# ───────────────────────────────────────── encabezado
st.title("🎙️ ¿Pueden convertirse documentos escaneados y entrevistas en audio en texto estructurado y buscable?")
st.markdown(
    "Pipeline de IA sobre **25 documentos peruanos** (impresos de 1791–1905, fotos de celular y manuscritos) y "
    "**28 entrevistas y testimonios** en español peruano (39 min, Wikimedia Commons). OCR con **PaddleOCR**, "
    "transcripción con **Whisper large-v3-turbo + VAD** y diarización, **seudonimización** de personas privadas y "
    "extracción de campos con **Gemini**. Las métricas CER/WER se calculan sobre **10 documentos y 10 clips** con "
    "transcripción manual. *Tarea 2 · Python intermedio QLAB PUCP · Eliana Camacho.*")

c = st.columns(5)
c[0].metric("Documentos procesados", len(docs))
c[1].metric("Minutos de audio transcritos", f"{aud['minutos'].sum():.1f}")
cer = valor_metrica("PaddleOCR")
c[2].metric("CER PaddleOCR (10 docs)", f"{cer:.2f}" if cer is not None else "—")
wer = valor_metrica("turbo")
c[3].metric("WER Whisper turbo + VAD (10 clips)", f"{wer:.2f}" if wer is not None else "—")
if len(T["auditoria_llm"]) and T["auditoria_llm"]["correcto"].astype(str).isin(["0", "1"]).all():
    ok = T["auditoria_llm"]["correcto"].astype(int).sum()
    c[4].metric("Concordancia LLM vs. auditoría humana", f"{ok / 20:.0%}", f"{ok}/20 correctas", delta_color="off")
else:
    c[4].metric("Concordancia LLM vs. auditoría humana", "—")

# ───────────────────────────────────────── filtros globales
with st.sidebar:
    st.header("🔎 Búsqueda y filtros")
    buscar = st.text_input("Buscar palabra en textos OCR y ASR", placeholder="ej. constitución, parto, Perú")
    tipos = st.multiselect("Tipo de documento", ["impreso", "foto", "manuscrito"], default=["impreso", "foto", "manuscrito"])
    condiciones = sorted(aud["condicion"].dropna().unique())
    conds = st.multiselect("Condición de grabación", condiciones, default=condiciones)
    rango = st.slider("Duración del clip (s)", 0, int(aud["duracion_seg"].max()) + 1, (0, int(aud["duracion_seg"].max()) + 1))
    modelos = sorted(det["modelo"].unique()) if len(det) else []
    modelos_sel = st.multiselect("Modelos en la evaluación", modelos, default=modelos)
    st.caption("Los filtros actualizan las tablas, los gráficos y los exploradores.")

docs_f = docs[docs["tipo"].isin(tipos)]
aud_f = aud[aud["condicion"].isin(conds) & aud["duracion_seg"].between(*rango)]
if buscar:
    docs_f = docs_f[docs_f["texto_ocr"].str.contains(buscar, case=False, regex=False)]
    aud_f = aud_f[aud_f["texto_asr"].str.contains(buscar, case=False, regex=False)]
    st.info(f"«{buscar}» aparece en **{len(docs_f)} documentos** y **{len(aud_f)} clips**.")

tab_res, tab_doc, tab_aud, tab_eval, tab_datos = st.tabs(
    ["📊 Resumen", "📄 Documentos", "🎧 Audios", "🧪 Evaluación de modelos", "⬇️ Datos"])

# ───────────────────────────────────────── resumen
with tab_res:
    g1, g2 = st.columns(2)
    fig = px.histogram(docs_f, x="tipo", color="tipo", category_orders={"tipo": ["impreso", "foto", "manuscrito"]},
                       title="Documentos por tipo (8 impresos, 8 fotos, 9 manuscritos)")
    fig.update_layout(showlegend=False, yaxis_title="Documentos", xaxis_title="")
    g1.plotly_chart(fig, width="stretch")
    fig = px.box(docs_f, x="tipo", y="caracteres", points="all", hover_data=["id"],
                 category_orders={"tipo": ["impreso", "foto", "manuscrito"]},
                 title="Los impresos producen mucho más texto OCR que fotos y manuscritos")
    fig.update_layout(yaxis_title="Caracteres extraídos", xaxis_title="")
    g2.plotly_chart(fig, width="stretch")
    g3, g4 = st.columns(2)
    por = aud_f.groupby("condicion", as_index=False)["minutos"].sum().sort_values("minutos")
    fig = px.bar(por, x="minutos", y="condicion", orientation="h", title="Minutos de audio por condición de grabación")
    fig.update_layout(yaxis_title="", xaxis_title="Minutos")
    g3.plotly_chart(fig, width="stretch")
    fig = px.scatter(aud_f, x="duracion_seg", y="palabras", color="condicion", hover_data=["id"],
                     title="Palabras transcritas frente a duración de cada clip")
    fig.update_layout(xaxis_title="Duración (s)", yaxis_title="Palabras ASR")
    g4.plotly_chart(fig, width="stretch")

# ───────────────────────────────────────── explorador de documentos
with tab_doc:
    if docs_f.empty:
        st.warning("Ningún documento cumple los filtros.")
    else:
        sel = st.selectbox("Documento", docs_f["id"], format_func=lambda i: f"{i} · {docs.set_index('id').loc[i, 'tipo']}")
        d = docs.set_index("id").loc[sel]
        izq, der = st.columns([1, 1])
        with izq:
            img = ejemplo(sel, [".jpg", ".jpeg", ".png"])
            if img:
                st.image(str(img), caption=f"{sel} — {d['fuente']}")
            else:
                st.info("Imagen no publicada (derechos de autor de terceros o captura propia no destinada a difusión). "
                        "Se muestra solo el texto extraído y sus metadatos.")
            st.caption(f"**Fuente y licencia:** {d['fuente']}")
            st.caption(f"**Modelo:** {d['modelo_ocr']}")
        with der:
            st.subheader("Texto OCR (PaddleOCR)")
            st.text_area("ocr", d["texto_ocr"], height=220, label_visibility="collapsed")
            if d["texto_referencia"]:
                st.subheader("Transcripción manual (referencia)")
                st.text_area("ref", d["texto_referencia"], height=140, label_visibility="collapsed")
                fila = det[(det["id"] == sel)]
                if len(fila):
                    st.dataframe(fila[["modelo", "valor"]].rename(columns={"valor": "CER"}).round(3), hide_index=True)
                alt = T["ocr_alternativo"]
                if len(alt) and sel in set(alt["id"]):
                    with st.expander("Texto de Tesseract (OCR alternativo)"):
                        st.write(alt.set_index("id").loc[sel, "Tesseract"])
            st.subheader("Campos extraídos por el LLM")
            st.json(campos_llm.get(sel, {}))

# ───────────────────────────────────────── explorador de audios
with tab_aud:
    if aud_f.empty:
        st.warning("Ningún clip cumple los filtros.")
    else:
        sel = st.selectbox("Clip", aud_f["id"], format_func=lambda i: f"{i} · {aud.set_index('id').loc[i, 'condicion']} · {aud.set_index('id').loc[i, 'duracion_seg']:.0f} s")
        a = aud.set_index("id").loc[sel]
        k = st.columns(3)
        k[0].metric("Duración", f"{a['duracion_seg']:.0f} s")
        k[1].metric("Hablantes detectados", int(a["n_hablantes"]))
        k[2].metric("Palabras", int(a["palabras"]))
        archivo = ejemplo(sel, [".ogg", ".mp3", ".wav", ".opus"])
        if archivo:
            st.audio(str(archivo))
            st.caption(f"Reproducción autorizada por la licencia **{a['licencia']}** (Wikimedia Commons). "
                       f"Fuente: {T['fuentes'].set_index('id').loc[sel, 'fuente_url']}")
        else:
            st.info("Este clip no forma parte de la muestra de audio publicada (solo se publican 4 clips sin menciones a personas privadas). "
                    "Se muestra su transcripción seudonimizada.")
        st.subheader("Transcripción (Whisper large-v3-turbo + VAD, seudonimizada)")
        texto = a["texto_asr"]
        if "[HABLANTE_" in texto:
            for turno in [t for t in texto.split("[HABLANTE_") if t.strip()]:
                n, frase = turno.split("]", 1)
                st.markdown(f"**🗣️ Hablante {n}:** {frase.strip()}")
        else:
            st.write(texto)
        if a["texto_referencia"]:
            st.subheader("Comparación con la referencia manual y otros modelos")
            comp = {"Referencia manual": a["texto_referencia"], "Whisper turbo + VAD": texto}
            alt = T["asr_alternativos"]
            if len(alt) and sel in set(alt["id"]):
                comp |= alt.set_index("id").loc[sel].to_dict()
            st.dataframe(pd.DataFrame({"texto": comp}), width="stretch")
            fila = det[det["id"] == sel]
            if len(fila):
                fig = px.bar(fila, x="modelo", y="valor", title=f"WER por modelo en {sel}", labels={"valor": "WER"})
                st.plotly_chart(fig, width="stretch")
        st.subheader("Campos extraídos por el LLM")
        st.json(campos_llm.get(sel, {}))

# ───────────────────────────────────────── evaluación
with tab_eval:
    if met.empty:
        st.warning("Las métricas aparecen cuando se ejecuta 02_evaluacion.ipynb.")
    else:
        st.subheader("Tabla comparativa (mismos 10 documentos y 10 clips para todos los modelos)")
        st.dataframe(met, hide_index=True, width="stretch")
        det_f = det[det["modelo"].isin(modelos_sel)]
        e1, e2 = st.columns(2)
        fig = px.box(det_f[det_f["métrica"] == "CER"], x="grupo", y="valor", color="modelo", points="all", hover_data=["id"],
                     title="CER por tipo de documento: los manuscritos y fotos concentran el error")
        fig.update_layout(xaxis_title="", yaxis_title="CER")
        e1.plotly_chart(fig, width="stretch")
        fig = px.box(det_f[det_f["métrica"] == "WER"], x="grupo", y="valor", color="modelo", points="all", hover_data=["id"],
                     title="WER por condición de grabación")
        fig.update_layout(xaxis_title="", yaxis_title="WER")
        e2.plotly_chart(fig, width="stretch")
        if len(T["auditoria_llm"]) and T["auditoria_llm"]["correcto"].astype(str).isin(["0", "1"]).all():
            st.subheader("Auditoría humana de 20 extracciones del LLM")
            st.dataframe(T["auditoria_llm"], hide_index=True, width="stretch")

# ───────────────────────────────────────── datos
with tab_datos:
    st.caption("Solo textos revisados y seudonimizados. Los archivos originales se recuperan con datos/fuentes.csv.")
    opcion = st.radio("Tabla", ["Documentos", "Transcripciones", "Extracción LLM", "Fuentes"], horizontal=True)
    tabla = {"Documentos": docs_f.drop(columns=["caracteres"]), "Transcripciones": aud_f.drop(columns=["minutos", "palabras"]),
             "Extracción LLM": llm, "Fuentes": T["fuentes"]}[opcion]
    st.dataframe(tabla, hide_index=True, width="stretch")
    st.download_button(f"Descargar {opcion.lower()} (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                       file_name=f"{opcion.lower().replace(' ', '_')}.csv", mime="text/csv")
