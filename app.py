import streamlit as st
import whisper
import pandas as pd
import os

# Configuración de la interfaz
st.set_page_config(page_title="Monitor de Calidad Movistar", layout="wide")
st.title("🎙️ Análisis Automático de Calidad - Contact Center")

# Carga del modelo de IA (Base es el más rápido para web)
@st.cache_resource
def load_model():
    return whisper.load_model("base")

model = load_model()

# --- CARGA DE ARCHIVO ---
uploaded_file = st.file_uploader("Sube tu llamada en formato .mp3", type=["mp3"])

if uploaded_file is not None:
    with st.spinner("Analizando llamada... esto tardará solo unos segundos"):
        # Guardar temporalmente el audio para que la IA lo lea
        with open("temp_audio.mp3", "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 1. Transcripción (La IA escucha y escribe)
        result = model.transcribe("temp_audio.mp3", language="es")
        text_full = result['text']
        segments = result['segments']

        # 2. Lógica de Verificación de Calidad
        # Saludo exacto solicitado
        saludo_keywords = ["mejor red movil", "señal y cobertura", "atención preferencial", "movistar total"]
        saludo_detectado = any(k in text_full.lower() for k in saludo_keywords)
        
        # Validación de Datos
        datos_keywords = ["cédula", "direccion", "celular", "motivo de su llamada"]
        datos_validados = [k for k in datos_keywords if k in text_full.lower()]
        
        # Detección de Hold (Publicidad Disney/Prime) y Silencios
        holds = []
        silencios = []
        last_end = 0
        for s in segments:
            # Si menciona beneficios en el hold
            if "prime video" in s['text'].lower() or "disney" in s['text'].lower():
                holds.append(f"{s['start']:.1f}s a {s['end']:.1f}s")
            
            # Silencios mayores a 3 segundos
            if (s['start'] - last_end) > 3.0:
                silencios.append(f"{last_end:.1f}s a {s['start']:.1f}s")
            last_end = s['end']

        # Verificación de Encuesta
        encuesta = "Sí" if any(k in text_full.lower() for k in ["encuesta", "transferir", "calificar"]) else "No"

        # --- MOSTRAR RESULTADOS EN LA WEB ---
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("✅ Evaluación de Calidad")
            st.write(f"**Saludo Correcto:** {'Si' if saludo_detectado else 'No'}")
            st.write(f"**Datos Validados:** {', '.join(datos_validados) if datos_validados else 'Ninguno'}")
            st.write(f"**Mención Encuesta:** {encuesta}")
        
        with col2:
            st.subheader("⏳ Tiempos Detectados")
            st.write(f"**Tiempos en Hold:** {', '.join(holds) if holds else 'No se detectó hold'}")
            st.write(f"**Silencios Incómodos:** {', '.join(silencios) if silencios else 'Sin silencios largos'}")

        # --- CREACIÓN DEL ARCHIVO EXCEL ---
        df = pd.DataFrame({
            "Parámetro": ["Saludo Protocolario", "Validación de Datos", "Tiempos Hold", "Silencios Incómodos", "Encuesta", "Lo que dijo el agente (Inicio)"],
            "Resultado": [
                "CORRECTO" if saludo_detectado else "INCORRECTO",
                ", ".join(datos_validados),
                ", ".join(holds),
                ", ".join(silencios),
                encuesta,
                text_full[:400] # Primeros 400 caracteres para el reporte
            ]
        })
        
        st.divider()
        st.subheader("📥 Descarga tu Reporte")
        excel_name = "resultado_calidad.xlsx"
        df.to_excel(excel_name,
