import camelot 


# --- Camelot tables ---
tables = camelot.read_pdf(pdf_path)

    for i, tables in enumerate(pdf_path):
        xlsx_t = tables.to