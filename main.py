import re
import argparse
from pathlib import Path

import pandas as pd

# Intentamos usar pdfplumber; si no, PyPDF2
try:
    import pdfplumber  # type: ignore
    PDF_BACKEND = "pdfplumber"
except Exception:
    from PyPDF2 import PdfReader  # type: ignore
    PDF_BACKEND = "pypdf2"


def _normalize_number(s: str):
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None

    # Eliminar espacios normales y espacios de no separación
    s = s.replace('\u00A0', '').replace(' ', '')

    # Caso 1: Formato europeo con decimales (ej. "1.209,82")
    if ',' in s:
        s = s.replace('.', '')    # Quitar puntos de miles
        s = s.replace(',', '.')    # Cambiar coma por punto decimal
    else:
        # Caso 2: Formato entero con punto de miles (ej. "1.750")
        if s.count('.') == 1 and len(s.split('.')[1]) == 3:
            s = s.replace('.', '')

    try:
        return float(s)
    except ValueError:
        return None


def _extract_text(pdf_path: Path) -> str:
    if PDF_BACKEND == "pdfplumber":
        out = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for p in pdf.pages:
                out.append(p.extract_text(x_tolerance=1, y_tolerance=1) or "")
        return "\n".join(out)
    else:
        reader = PdfReader(str(pdf_path))
        return "\n".join([pg.extract_text() or "" for pg in reader.pages])


def _slice_partidas(text: str):
    pat = re.compile(r"(PARTIDA\s+\d+\.?.*?)(?=(?:\nPARTIDA\s+\d+\.?)|\Z)", re.IGNORECASE | re.DOTALL)
    return [m.group(1) for m in pat.finditer(text)]


def _get(pattern: re.Pattern, block: str, group=1, as_float=False):
    m = pattern.search(block)
    if not m:
        return None
    val = m.group(group).strip()
    if as_float:
        return _normalize_number(val)
    return val


def parse_pdf(pdf_path: Path) -> pd.DataFrame:
    text = _extract_text(pdf_path)
    partidas = _slice_partidas(text)
    rows = []

    # Expresiones regulares adaptables
    pos_pat = re.compile(r"Pos\.?\s*Estad[íi]stica:\s*([\d\s]{6,12})", re.IGNORECASE)
    desc_pat = re.compile(
        r"Desc\.?\s*Mercanc[ií]a:\s*(.*?)(?=\n\s*(?:Bultos:|Pa[íi]s|C[oó]digo\s+CUS:|Embalajes:|\Z))",
        re.IGNORECASE | re.DOTALL
    )
    bultos_pat = re.compile(r"Bultos:\s*([\d\.]+)", re.IGNORECASE)
    pbr_pat = re.compile(r"Peso\s+Bruto:\s*([\d\.\,]+)", re.IGNORECASE)
    pnt_pat = re.compile(r"Peso\s+Neto:\s*([\d\.\,]+)", re.IGNORECASE)
    factura_pat = re.compile(r"Factura:\s*([\d\.\,]+)\s*€", re.IGNORECASE)

    for blk in partidas:
        pos = _get(pos_pat, blk)
        if pos:
            pos = re.sub(r"\s+", "", pos)

        desc = _get(desc_pat, blk)
        if desc:
            desc = re.sub(r"\s+", " ", desc).strip(" .")

        bultos = _get(bultos_pat, blk, as_float=True)
        pbr = _get(pbr_pat, blk, as_float=True)
        pnt = _get(pnt_pat, blk, as_float=True)
        factura = _get(factura_pat, blk, as_float=True)

        # Filtramos filas completamente vacías
        if any([pos, desc, bultos, pbr, pnt, factura]):
            rows.append({
                "Posición Estadística": pos,
                "Descripción": desc,
                "Bultos": bultos,
                "Peso Bruto (kg)": pbr,
                "Peso Neto (kg)": pnt,
                "Factura (€)": factura
            })

    df = pd.DataFrame(rows, columns=[
        "Posición Estadística", "Descripción", "Bultos",
        "Peso Bruto (kg)", "Peso Neto (kg)", "Factura (€)"
    ])
    return df


def process(input_dir: Path, output_dir: Path, consolidated: Path | None):
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for pdf in sorted(input_dir.glob("*.pdf")):
        try:
            df = parse_pdf(pdf)
            out = output_dir / f"{pdf.stem}_partidas_min.xlsx"
            df.to_excel(out, index=False)
            print(f"[OK] {pdf.name} -> {out.name} ({len(df)} filas)")
            if consolidated is not None:
                aux = df.copy()
                aux.insert(0, "Archivo", pdf.name)
                all_rows.append(aux)
        except Exception as e:
            print(f"[ERROR] {pdf.name}: {e}")
    if consolidated is not None and all_rows:
        big = pd.concat(all_rows, ignore_index=True)
        big.to_excel(consolidated, index=False)
        print(f"[OK] Consolidado -> {consolidated.name} ({len(big)} filas)")


def main():
    ap = argparse.ArgumentParser(description="Extrae PARTIDAS mínimas de DUA (PDF) a Excel.")
    ap.add_argument("--input", required=True, help="Carpeta con PDFs")
    ap.add_argument("--output", required=True, help="Carpeta de salida")
    ap.add_argument("--consolidated", default=None, help="Ruta de Excel consolidado (opcional)")
    args = ap.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    consolidated = Path(args.consolidated) if args.consolidated else None

    process(input_dir, output_dir, consolidated)


if __name__ == "__main__":
    main()
