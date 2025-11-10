import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image

import json
import gspread
from google.oauth2.service_account import Credentials

# Leer el JSON desde Secrets
creds_json = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
scope = ["https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_json, scopes=scope)
client = gspread.authorize(creds)

# Abrir la hoja de Google
spreadsheet = client.open("Vuelco MAGNUS_DESGLOSE")
sheet = spreadsheet.worksheet("DESGLOSE")

# Importamos tu lógica de procesamiento
from main import parse_pdf  # Asegúrate de que tu script original se llame main.py

# Configuración general de la página
st.set_page_config(
    page_title="Extractor de PARTIDAS DUA",
    page_icon="icono.ico",
    layout="wide"
)

# Encabezado
logo = Image.open("imagen.png")
st.image(logo, width=500)
st.markdown(
    "<h3 style='color:#132136;margin-top:-10px;'>Extractor de PARTIDAS DUA  |  (PDF → Google Sheets)</h3>",
    unsafe_allow_html=True
)
st.caption("Departamento de Aduanas - Bernardino Abad SL")
st.divider()

st.write("Sube uno o varios archivos PDF y convierte su contenido a una tabla consolidada en Google Sheets.")

# CSS
st.markdown("""
<style>
/* Fondo general */
.stApp {
    background-color: #F8FAFD;
}

/* Botones principales */
.stButton>button {
    background-color: #004C91;
    color: white;
    border-radius: 8px;
    padding: 0.6em 1.2em;
    font-weight: 600;
}

/* Texto y títulos */
h1, h2, h3, h4 {
    color: #004C91;
}
</style>
""", unsafe_allow_html=True)

# Subida de archivos
uploaded_files = st.file_uploader(
    "Selecciona uno o varios archivos PDF:",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    all_rows = []
    errores = []

    # Barra de progreso
    progress = st.progress(0, text="Preparando archivos...")

    for i, file in enumerate(uploaded_files):
        st.info(f"Procesando **{file.name}** ...")

        try:
            # Guardamos temporalmente el PDF subido
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.read())
                tmp_path = Path(tmp.name)

            # Parseamos el PDF usando tu función
            df = parse_pdf(tmp_path)

            # Solo añadimos si tiene filas válidas
            if not df.empty:
                all_rows.append(df)
            else:
                errores.append(f"⚠️ {file.name}: no se extrajo ninguna partida válida.")

        except Exception as e:
            errores.append(f"❌ Error procesando {file.name}: {e}")

        # Actualizar barra de progreso
        progress.progress((i + 1) / len(uploaded_files),
                          text=f"Procesando {file.name} ({i + 1}/{len(uploaded_files)})")

    # Quitar la barra
    progress.empty()

    # Mostrar errores si existen
    if errores:
        st.warning("Algunos archivos no se procesaron correctamente:")
        for err in errores:
            st.write(err)

    # Consolidar resultados
    if all_rows:
        final_df = pd.concat(all_rows, ignore_index=True)
        st.success(f"✅ Se procesaron {len(all_rows)} de {len(uploaded_files)} archivos correctamente.")
        st.dataframe(final_df, use_container_width=True)

        # --- VOLCAR DATOS A GOOGLE SHEETS ---
        try:
            # Convertir DataFrame a lista de listas (sin encabezado)
            data_values = final_df.values.tolist()

            # Respetar rango B9:G107 (99 filas máximo)
            max_rows = 107 - 9 + 1  # 99 filas
            data_to_insert = data_values[:max_rows]

            # Actualizar rango específico en la hoja
            sheet.update("B9:G107", data_to_insert)

            st.success("📤 Datos volcados correctamente en Google Sheets (B9:G107).")
        except Exception as e:
            st.error(f"❌ Error al volcar datos a Google Sheets: {e}")

    else:
        st.error("No se pudo generar ningún resultado. Revisa los archivos PDF subidos.")



















