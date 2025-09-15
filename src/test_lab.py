import pymupdf
import pytesseract
from pytesseract import Output
import cv2
import numpy as np
import pandas as pd
import camelot
import tkinter as tk
from tkinter import filedialog


def get_book_content():
    # --- Use Tkinter to pick the PDF ---
    root = tk.Tk()
    root.withdraw()  # hide main window
    pdf_path = filedialog.askopenfilename(
        title="Select PDF file",
        filetypes=[("PDF files", "*.pdf")]
    )
    root.destroy()  # destroy the hidden Tk instance

    if not pdf_path:
        print("No file selected. Exiting...")
        return [], pd.DataFrame(), pd.DataFrame()

    doc = pymupdf.open(pdf_path)
    num_pages = doc.page_count

    all_rows = []
    all_pages = []

    for page_num in range(num_pages):
        page = doc.load_page(page_num)
        page_dict = {"page": page_num + 1, "text": [], "graphics": [], "images": [], "ocr": []}

        # --- Text extraction ---
        pdf_data = page.get_text("dict")
        for block in pdf_data["blocks"]:
            if block["type"] == 0:
                for line in block.get("lines", []):
                    line_text = " ".join(span["text"] for span in line["spans"])
                    page_dict["text"].append(line_text)
                    all_rows.append({"page": page_num + 1, "text": line_text})

        # --- Graphics ---
        page_dict["graphics"] = page.get_drawings()

        # --- Images ---
        images_info = []
        for img in page.get_images():
            xref, width, height, bpc = img[0], img[2], img[3], img[4]
            images_info.append(f"[IMAGE id={xref} size={width}x{height} bpc={bpc}]")
        page_dict["images"] = images_info

        # --- OCR fallback ---
        raw_txt = " ".join(page_dict["text"])
        if not raw_txt.strip():
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            np_img = np.frombuffer(img_bytes, np.uint8)
            cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            ocr_data = pytesseract.image_to_data(
                cv_img, config="--psm 11 --oem 3", output_type=Output.DICT
            )
            for j in range(len(ocr_data['text'])):
                if float(ocr_data['conf'][j]) > 80:
                    page_dict["ocr"].append(ocr_data['text'][j])
            cv2.imwrite(f"page_{page_num + 1}_ocr.png", cv_img)

        all_pages.append(page_dict)

    # --- Put into DataFrame ---
    df = pd.DataFrame(all_rows)

    # --- Pre-cleaning ---
    df['text'] = df['text'].str.lower()
    df["text"] = df["text"].str.strip()
    df = df[df["text"].str.len() > 0]
    df.drop_duplicates(inplace=True)

    # --- Word-level features ---
    df["word_count"] = df["text"].apply(lambda x: len(x.split()))
    df["char_count"] = df["text"].apply(len)
    df["avg_word_len"] = df["char_count"] / df["word_count"].replace(0, np.nan)

    df.to_csv("output_text.csv", index=False)
    print(f"Saved output_text.csv with {len(df)} text lines.")

    # --- Camelot tables ---
    tables = camelot.read_pdf(pdf_path)
    print(f"Found {len(tables)} tables.")

    all_table_dfs = []

    for i, table in enumerate(tables):
        print(f"Table {i} parsing report: {table.parsing_report}")
        table.df.to_csv(f'table_{i}.csv', index=False)
        table.df.to_excel(f'table_{i}.xlsx', index=False)
        table.df.to_json(f'table_{i}.json', orient="records", indent=4)  
        all_table_dfs.append(table.df)

    # Merge all tables if any
    merged_tables = pd.concat(all_table_dfs, ignore_index=True) if all_table_dfs else pd.DataFrame()

    return all_pages, df, merged_tables


def save_file(text_df):
    root = tk.Tk()
    root.withdraw()  

    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*")],
        title="Save file"
    )

    root.destroy()  

    if not file_path:
        print("Save cancelled.")
        return

    # Save CSV, Excel, JSON
    text_df.to_csv(file_path, index=False)
    base_path = file_path.rsplit(".", 1)[0]
    text_df.to_excel(f"{base_path}.xlsx", index=False)
    text_df.to_json(f"{base_path}.json", orient="records", indent=4)

    print(f"Files saved as:\n{file_path}\n{base_path}.xlsx\n{base_path}.json")


if __name__ == "__main__":
    pages, text_df, table_dfs = get_book_content()
    print(f"Extracted {len(pages)} pages, {len(text_df)} text lines, and {len(table_dfs)} tables.")

    # GUI 
    root = tk.Tk()
    root.geometry("300x150")
    root.title("Save Files")

    save_button = tk.Button(root, text="Save Files", command=lambda: save_file(text_df))
    save_button.pack(pady=30)

    root.mainloop()
