import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
from io import BytesIO

# Importamos tu lógica de procesamiento
from main import parse_pdf  # Asegúrate de que tu script original se llame main.py

# Configuración general de la página
st.set_page_config(page_title="Extractor de PARTIDAS DUA", layout="wide")
st.title("📄 Extractor de PARTIDAS DUA (PDF → Excel)")
st.write("Sube uno o varios archivos PDF y convierte su contenido a una tabla consolidada en Excel.")

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

        # Crear Excel en memoria
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

    else:
        st.error("No se pudo generar ningún resultado. Revisa los archivos PDF subidos.")
