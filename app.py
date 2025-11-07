import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
from io import BytesIO

# Importa tus funciones existentes:
from main import parse_pdf  # suponiendo que tu script original se llama main.py

st.set_page_config(page_title="Extractor de PARTIDAS DUA", layout="wide")

st.title("📄 Extractor de PARTIDAS DUA (PDF → Excel)")
st.write("Sube uno o varios archivos PDF y convierte su contenido a una tabla consolidada en Excel.")

uploaded_files = st.file_uploader(
    "Selecciona uno o varios archivos PDF:",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    all_rows = []
    for file in uploaded_files:
        st.info(f"Procesando **{file.name}** ...")
        # Guardamos temporalmente el archivo PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.read())
            tmp_path = Path(tmp.name)
        # Parseamos usando tu función
        df = parse_pdf(tmp_path)
        all_rows.append(df)

    # Concatenamos todo
    final_df = pd.concat(all_rows, ignore_index=True)

    st.success(f"Se procesaron {len(uploaded_files)} archivos correctamente.")
    st.dataframe(final_df, use_container_width=True)

    # Exportar a Excel en memoria
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
