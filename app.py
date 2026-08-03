import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
creds_json = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_json, scopes=scope)
client = gspread.authorize(creds)

# Abrir hoja de Google
spreadsheet = client.open("Vuelco MAGNUS_DESGLOSE")
sheet = spreadsheet.worksheet("DESGLOSE")

# --- IMPORTAR TU FUNCIÓN DE PROCESO ---
from main import parse_pdf  # Asegúrate de que tu script principal se llame main.py

# --- CONFIGURACIÓN DE STREAMLIT ---
st.set_page_config(
    page_title="Extractor de PARTIDAS DUA",
    page_icon="icono.ico",
    layout="wide"
)

# Encabezado con logo
logo = Image.open("imagen.png")
st.image(logo, width=500)
st.markdown(
    "<h3 style='color:#132136;margin-top:-10px;'>Extractor de PARTIDAS DUA  |  (PDF → Excel / Google Sheets)</h3>",
    unsafe_allow_html=True
)
st.caption("Departamento de Aduanas - Bernardino Abad SL")
st.divider()

st.write("Sube uno o varios archivos PDF y convierte su contenido a una tabla consolidada.")

# CSS personalizado
st.markdown("""
<style>
.stApp { background-color: #F8FAFD; }
.stButton>button { background-color: #004C91; color: white; border-radius: 8px; padding: 0.6em 1.2em; font-weight: 600; }
h1, h2, h3, h4 { color: #004C91; }
</style>
""", unsafe_allow_html=True)

# --- SUBIDA DE ARCHIVOS ---
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
            # Guardar temporalmente el PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.read())
                tmp_path = Path(tmp.name)

            # Parsear PDF
            df = parse_pdf(tmp_path)

            if not df.empty:
                all_rows.append(df)
            else:
                errores.append(f"⚠️ {file.name}: no se extrajo ninguna partida válida.")

        except Exception as e:
            errores.append(f"❌ Error procesando {file.name}: {e}")

        # Actualizar barra de progreso
        progress.progress((i + 1) / len(uploaded_files),
                          text=f"Procesando {file.name} ({i + 1}/{len(uploaded_files)})")

    progress.empty()

    # Mostrar errores si los hay
    if errores:
        st.warning("Algunos archivos no se procesaron correctamente:")
        for err in errores:
            st.write(err)

    # Consolidar resultados
    if all_rows:
        final_df = pd.concat(all_rows, ignore_index=True)
        st.success(f"✅ Se procesaron {len(all_rows)} de {len(uploaded_files)} archivos correctamente.")
        st.dataframe(final_df, use_container_width=True)

        # --- Descarga en Excel opcional ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            final_df.to_excel(writer, index=False, sheet_name="Partidas")
        output.seek(0)

        st.download_button(
            label="⬇️ Descargar Excel consolidado",
            data=output,
            file_name="partidas_consolidadas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- Botón para volcar a Google Sheets ---
        if st.button("💾 Volcar a Google Sheets"):
            try:
                # Limpiar rango previo
                sheet.batch_clear(["B9:G107"])

                # Sanitizar DataFrame reemplazando valores NaN/None por cadenas vacías
                df_clean = final_df.fillna("")

                # Preparar datos satinizados (sin encabezado)
                values = df_clean.values.tolist()
                total_rows = len(values)
                total_cells = total_rows * 6  # columnas B-G = 6

                # Crear barra de progreso para el volcado
                progress_gs = st.progress(0, text="Volcando a Google Sheets...")

                cell_list = sheet.range(f"B9:G{8+total_rows}")
        
                # Asignar valores a celdas con seguimiento de progreso
                flat_values = [v for row in values for v in row]
                for idx, (cell, value) in enumerate(zip(cell_list, flat_values)):
                    cell.value = value
                    progress_gs.progress((idx + 1) / total_cells, text="Volcando a Google Sheets...")

                sheet.update_cells(cell_list)
                progress_gs.empty()
                st.success("✅ Datos volcados correctamente en Google Sheets")

            except Exception as e:
                st.error(f"❌ Error al volcar datos: {e}")

    else:
        st.error("No se pudo generar ningún resultado. Revisa los archivos PDF subidos.")























