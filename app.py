import streamlit as st
import whisper
import pandas as pd
import os

# Configuración de la interfaz
st.set_page_config(page_title="Auditor de Saludos Movistar", layout="wide")
st.title("🎙️ Análisis de Calidad: Verificación de Saludo")

@st.cache_resource
def load_model():
    return whisper.load_model("tiny") # Tiny es ideal para detectar saludos rápido

model = load_model()

uploaded_file = st.file_uploader("Sube tu llamada .mp3", type=["mp3"])

if uploaded_file is not None:
    with st.spinner("Escuchando el saludo y analizando..."):
        with open("temp_audio.mp3", "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 1. Transcripción
        result = model.transcribe("temp_audio.mp3", language="es")
        text_full = result['text']
        segments = result['segments']

        # 2. EXTRACCIÓN DEL SALUDO LITERAL
        # Tomamos los primeros 2 o 3 segmentos de la llamada (donde ocurre el saludo)
        saludo_literal = ""
        for i, s in enumerate(segments):
            if i < 3: # El saludo siempre está en los primeros 3 bloques de habla
                saludo_literal += s['text'] + " "
        
        # 3. VERIFICACIÓN DEL PROTOCOLO
        # Definimos las frases clave que SIEMPRE deben estar
        keywords_obligatorias = ["mejor red movil", "señal y cobertura", "atención preferencial", "movistar total"]
        
        # Contamos cuántas de las frases obligatorias dijo
        aciertos = [k for k in keywords_obligatorias if k in saludo_literal.lower()]
        cumple_protocolo = len(aciertos) >= 3 # Cumple si dice al menos 3 de las frases

        # --- MOSTRAR RESULTADOS ---
        st.divider()
        if cumple_protocolo:
            st.success(f"✅ **SALUDO CORRECTO**")
        else:
            st.error(f"❌ **SALUDO INCORRECTO** (Faltaron frases del protocolo)")
        
        st.info(f"**Lo que el agente dijo exactamente:**\n\n\"{saludo_literal.strip()}\"")

        # --- EXCEL DETALLADO ---
        df = pd.DataFrame({
            "Métrica de Calidad": ["Estado del Saludo", "Saludo Literal (Lo que dijo)", "Motivo detectado", "Encuesta", "Hold/Espera"],
            "Resultado": [
                "CORRECTO" if cumple_protocolo else "INCORRECTO",
                saludo_literal.strip(), # Aquí verás exactamente qué dijo el agente
                text_full[text_full.lower().find("motivo"):text_full.lower().find("motivo")+100] if "motivo" in text_full.lower() else "No detectado",
                "Sí" if "encuesta" in text_full.lower() else "No",
                "Detectado" if "disney" in text_full.lower() or "prime" in text_full.lower() else "No detectado"
            ]
        })

        st.divider()
        excel_name = f"Auditoria_{uploaded_file.name}.xlsx"
        df.to_excel(excel_name, index=False)
        with open(excel_name, "rb") as file:
            st.download_button(label="📥 Descargar Reporte de Saludo", data=file, file_name=excel_name)
