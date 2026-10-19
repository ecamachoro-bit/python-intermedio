import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from transformers import pipeline

BASE = Path(__file__).parent
MODELO = os.getenv("MODELO_HF", str(BASE / "modelo"))  # en la nube: repo de Hugging Face
ETIQUETAS = ["politica", "economia", "deportes", "ciencia_tecnologia"]

st.set_page_config(page_title="Clasificador de noticias peruanas", page_icon="📰", layout="wide")


@st.cache_data
def cargar_datos():
    return pd.read_csv(BASE / "datos" / "noticias.csv")


@st.cache_data
def cargar_metricas():
    return json.loads((BASE / "modelo" / "metricas.json").read_text(encoding="utf-8"))


@st.cache_resource
def cargar_modelo():
    return pipeline("text-classification", model=MODELO, top_k=None)


df = cargar_datos()
m = cargar_metricas()

# 1. Encabezado y contexto
st.title("📰 ¿Pueden convertir titulares peruanos en un clasificador de noticias?")
st.markdown(
    f"""**Metodología:** se recolectaron **{m['n_noticias']} titulares de El Comercio** desde sus sitemaps públicos de noticias,
    se etiquetaron según su sección editorial (política, economía, deportes, ciencia y tecnología) y se validaron con un LLM
    (`{m['modelo_llm']}`) más una auditoría humana. Con las noticias donde ambas fuentes coinciden se ajustó
    **DistilBERT multilingüe** (split 70/15/15 estratificado) y se comparó con un modelo zero-shot sin entrenar."""
)

# 2. Filtros en la barra lateral
st.sidebar.header("Filtros")
medios = st.sidebar.multiselect("Medio", sorted(df["medio"].unique()), default=sorted(df["medio"].unique()))
categorias = st.sidebar.multiselect("Categoría", ETIQUETAS, default=ETIQUETAS)
filtrado = df[df["medio"].isin(medios) & df["etiqueta"].isin(categorias)]

# 3. Indicadores clave
c1, c2, c3 = st.columns(3)
c1.metric("Noticias recolectadas", m["n_noticias"], delta=f"{len(filtrado)} con los filtros", delta_color="off")
c2.metric("F1 macro en test", f"{m['f1_test']:.3f}", delta=f"{m['f1_test'] - m['f1_zero_shot']:+.3f} vs. zero-shot")
c3.metric("Acuerdo LLM vs. humano", f"{m['acuerdo_humano']:.0%}", delta=f"{m['acuerdo_aciertos']}/20 casos", delta_color="off")

# 4. Visualización y exploración
izq, der = st.columns([1, 2])
with izq:
    conteo = filtrado["etiqueta"].value_counts().reset_index()
    st.plotly_chart(px.bar(conteo, x="etiqueta", y="count", color="etiqueta", text="count",
                           title="Distribución de categorías (filtrada)",
                           labels={"etiqueta": "Categoría", "count": "Noticias"}),
                    width="stretch")
with der:
    st.dataframe(filtrado[["fecha", "etiqueta", "titular", "bajada", "url"]], width="stretch", height=380,
                 column_config={"url": st.column_config.LinkColumn("url")})
    st.download_button("⬇️ Descargar CSV filtrado", filtrado.to_csv(index=False).encode("utf-8"),
                       "noticias_filtradas.csv", "text/csv")

# 5. Probador interactivo en vivo
st.subheader("🔮 Probador en vivo")
titular = st.text_input("Escribe o pega un titular nuevo",
                        placeholder="Ej.: BCR mantiene su tasa de referencia por tercer mes consecutivo")
if st.button("Clasificar", type="primary"):
    if not titular.strip():
        st.warning("Escribe un titular primero.")
    else:
        with st.spinner("Clasificando..."):
            res = cargar_modelo()([titular])[0]
        mejor = res[0]
        st.success(f"Categoría predicha: **{mejor['label']}** — confianza **{mejor['score']:.1%}**")
        st.plotly_chart(px.bar(pd.DataFrame(res), x="score", y="label", orientation="h", range_x=[0, 1],
                               labels={"score": "Probabilidad", "label": "Categoría"}),
                        width="stretch")
