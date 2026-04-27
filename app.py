import streamlit as st
import whisper
import pandas as pd
import os

# Configuración de la interfaz
st.set_page_config(page_title="Auditor Movistar Pro", layout="wide")
st.title("🎙️ Auditor de Calidad Movistar")

@st.cache_resource
def load_model():
    return whisper.load_model("tiny")

model = load_model()

# --- CARGA DE ARCHIVO ---
uploaded_file = st.file_uploader("Sube tu llamada .mp3", type=["mp3"])

if uploaded_file is not None:
    # Creamos un nombre seguro para el archivo temporal
    temp_filename = f"temp_{uploaded_file.name}"
    
    with st.spinner("Procesando audio..."):
        # Guardar el archivo físicamente para que Whisper no falle
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())

    try:
        with st.spinner("La IA está escuchando la llamada..."):
            # 1. Transcripción
            result = model.transcribe(temp_filename, language="es")
            text_full = result['text']
            segments = result['segments']

            # 2. Análisis de Saludo (Primeros segundos)
            saludo_literal = ""
            for i, s in enumerate(segments):
                if i < 3: saludo_literal += s['text'] + " "
            
            keywords_saludo = ["mejor red movil", "señal y cobertura", "atención preferencial", "movistar total"]
            aciertos = [k for k in keywords_saludo if k in saludo_literal.lower()]
            cumple_saludo = len(aciertos) >= 2 

            # 3. Mostrar Resultados
            st.divider()
            if cumple_saludo:
                st.success("✅ SALUDO CORRECTO")
            else:
                st.error("❌ SALUDO INCORRECTO")
            
            st.info(f"**Saludo escuchado:** {saludo_literal}")

            # 4. Excel
            df = pd.DataFrame({
                "Métrica": ["Estado Saludo", "Texto Literal", "Encuesta", "Motivo"],
                "Resultado": [
                    "CORRECTO" if cumple_saludo else "INCORRECTO",
                    saludo_literal,
                    "Sí" if "encuesta" in text_full.lower() else "No",
                    text_full[:200]
                ]
            })
            
            st.divider()
            df.to_excel("reporte.xlsx", index=False)
            with open("reporte.xlsx", "rb") as file:
                st.download_button("📥 Descargar Excel", data=file, file_name=f"Analisis_{uploaded_file.name}.xlsx")

    except Exception as e:
        st.error(f"Hubo un error al procesar: {e}")
    finally:
        # Limpieza: Borramos el archivo temporal para no llenar el servidor
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
