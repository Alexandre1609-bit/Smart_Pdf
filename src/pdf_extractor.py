import pymupdf
import pytesseract
from pytesseract import Output
import cv2
import numpy as np
import pandas as pd
import camelot
import tkinter as tk
from tkinter import filedialog
import os

def get_book_content(pdf_path):
    doc = pymupdf.open(pdf_path)
    num_pages = doc.page_count

    all_rows = []
    all_pages = []

    for page_num in range(num_pages):
        page = doc.load_page(page_num)
        page_dict = {"page": page_num+1, "text": [], "graphics": [], "images": [], "ocr": []}

        # --- Text extraction ---
        pdf_data = page.get_text("dict")
        for block in pdf_data["blocks"]:
            if block["type"] == 0:
                for line in block.get("lines", []):
                    line_text = " ".join(span["text"] for span in line["spans"])
                    page_dict["text"].append(line_text)
                    all_rows.append({"page": page_num+1, "text": line_text})

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
            cv2.imwrite(f"page_{page_num+1}_ocr.png", cv_img)

        all_pages.append(page_dict)

    df = pd.DataFrame(all_rows)
    return all_pages, df

def save_outputs(output_dir, pages, text_df, table_dfs):
    
    text_df.to_csv(os.path.join(output_dir, "output_text.csv"), index=False)
    print(f"Saved output_text.csv with {len(text_df)} text lines.")

    # --- Save tables ---
    for i, table_df in enumerate(table_dfs):
        table_df.to_csv(os.path.join(output_dir, f'table_{i}.csv'), index=False)
        table_df.to_excel(os.path.join(output_dir, f'table_{i}.xlsx'), engine="openpyxl", index=False)
        table_df.to_json(os.path.join(output_dir, f'table_{i}.json'), orient="records", force_ascii=False)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    pdf_file = filedialog.askopenfilename(title="Select PDF file", filetypes=[("PDF files", "*.pdf")])
    if not pdf_file:
        exit("No PDF selected.")

    output_dir = filedialog.askdirectory(title="Select output folder")
    if not output_dir:
        exit("No output folder selected.")

    pages, text_df = get_book_content(pdf_file)

    # --- Camelot tables ---
    tables = camelot.read_pdf(pdf_file)
    table_dfs = [table.df for table in tables]

    save_outputs(output_dir, pages, text_df, table_dfs)
    print(f"Extraction complete! Saved all outputs in {output_dir}")
