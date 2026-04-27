import streamlit as st
import whisper
import pandas as pd
import os
import re

# --- CONFIGURACIÓN DE PARÁMETROS DE AUDITORÍA ---
PARAMETROS_CALIDAD = {
    "palabras_saludo": ["mejor red movil", "señal y cobertura", "atención preferencial", "movistar total"],
    "datos_validacion": ["cédula", "nombre completo", "dirección", "confirmar su número"],
    "intencion_cancelar": ["cancelar", "retirarme", "dar de baja", "no quiero el servicio"],
    "ofertas_retencion": ["descuento", "beneficio", "meses gratis", "rebaja", "promoción"],
    "palabras_hold": ["un momento", "espera en línea", "disney", "prime video", "verificar en sistema"],
    "limite_silencio": 3.0 
}

st.set_page_config(page_title="Auditor Senior Movistar", layout="wide")
st.title("🎙️ Auditoría Avanzada: Retención y Validación")
st.sidebar.title("📖 Guía de uso")
st.sidebar.info("1. Sube el archivo .mp3\n2. Espera a que termine la transcripción\n3. Revisa el resumen y descarga el Excel.")

@st.cache_resource
def load_model():
    return whisper.load_model("tiny")

model = load_model()
uploaded_file = st.file_uploader("Sube la llamada para análisis detallado", type=["mp3"])

if uploaded_file is not None:
    temp_filename = f"temp_{uploaded_file.name}"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        with st.spinner("Realizando análisis profundo de la negociación..."):
            result = model.transcribe(temp_filename, language="es")
            text_full = result['text']
            text_lower = text_full.lower()
            segments = result['segments']

            # 1. ANÁLISIS DE VALIDACIÓN DE DATOS
            datos_encontrados = [d for d in PARAMETROS_CALIDAD["datos_validacion"] if d in text_lower]
            
            # 2. ANÁLISIS DE RETENCIÓN (DETECCIÓN DE DESCUENTOS)
            quiere_cancelar = any(c in text_lower for c in PARAMETROS_CALIDAD["intencion_cancelar"])
            # Buscamos una cifra o porcentaje cerca de la palabra descuento
            oferta_detalle = re.findall(r"(\d+\s?%|\d+\s?mil|\d+\s?pesos)", text_lower)
            ofrecio_descuento = any(o in text_lower for o in PARAMETROS_CALIDAD["ofertas_retencion"])
            
            aceptacion_cliente = "No detectada"
            if ofrecio_descuento:
                if any(si in text_lower for si in ["acepto", "está bien", "listo", "de acuerdo"]):
                    aceptacion_cliente = "SÍ ACEPÓ"
                elif any(no in text_lower for no in ["no me interesa", "muy caro", "siga con la cancelación"]):
                    aceptacion_cliente = "NO ACEPTÓ"

            # 3. DETECCIÓN DE SILENCIOS Y HOLD
            tiempos_hold = []
            silencios_incomodos = []
            ultima_marca = 0
            for s in segments:
                if any(w in s['text'].lower() for w in PARAMETROS_CALIDAD["palabras_hold"]):
                    tiempos_hold.append(f"{s['start']:.0f}s-{s['end']:.0f}s")
                if (s['start'] - ultima_marca) > PARAMETROS_CALIDAD["limite_silencio"]:
                    silencios_incomodos.append(f"{ultima_marca:.0f}s-{s['start']:.0f}s")
                ultima_marca = s['end']

            # --- INTERFAZ DE RESULTADOS ---
            st.header("📋 Resumen Ejecutivo de la Llamada")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🧐 Validación y Proceso")
                st.write(f"**Datos validados:** {', '.join(datos_encontrados) if datos_encontrados else 'No se detectó validación formal'}")
                st.write(f"**Intención de Cancelación:** {'⚠️ SÍ' if quiere_cancelar else 'No detectada'}")
                st.write(f"**Oferta de Retención:** {'✅ Realizada' if ofrecio_descuento else '❌ No se ofreció'}")
            
            with col2:
                st.subheader("💰 Resultado de la Negociación")
                st.write(f"**Valores detectados (%, $):** {', '.join(oferta_detalle) if oferta_detalle else 'N/A'}")
                st.write(f"**Respuesta del Cliente:** {aceptacion_cliente}")

            st.subheader("📝 Transcripción de la Negociación (Puntos Clave)")
            # Mostramos un extracto donde se menciona el dinero o el descuento
            puntos_clave = [s['text'] for s in segments if any(o in s['text'].lower() for o in PARAMETROS_CALIDAD["ofertas_retencion"])]
            for p in puntos_clave[:3]:
                st.write(f"> *{p}*")

            # --- EXCEL SÚPER DETALLADO ---
            resumen_largo = f"""El cliente { 'sí' if quiere_cancelar else 'no' } manifestó intención de cancelar. 
            El agente validó: {', '.join(datos_encontrados)}. 
            Se detectó oferta de: {', '.join(oferta_detalle)}. 
            El resultado final fue: {aceptacion_cliente}."""

            df_excel = pd.DataFrame({
                "Métrica de Auditoría": ["Resumen de Negociación", "Validación de Datos", "Tiempos Hold", "Silencios", "Aceptó Oferta", "Transcripción Completa"],
                "Detalle": [resumen_largo, ", ".join(datos_encontrados), ", ".join(tiempos_hold), ", ".join(silencios_incomodos), aceptacion_cliente, text_full]
            })
            
            df_excel.to_excel("auditoria_completa.xlsx", index=False)
            st.download_button("📥 Descargar Auditoría Detallada", data=open("auditoria_completa.xlsx", "rb"), file_name=f"Reporte_{uploaded_file.name}.xlsx")

    except Exception as e:
        st.error(f"Error en análisis: {e}")
    finally:
        if os.path.exists(temp_filename): os.remove(temp_filename)
