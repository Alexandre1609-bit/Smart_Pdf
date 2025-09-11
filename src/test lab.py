import pymupdf
import pytesseract
from pytesseract import Output
import cv2
import numpy as np
import pandas as pd

def get_book_content():
    pdf_path = input("Select file: ")
    doc = pymupdf.open(pdf_path)
    num_pages = doc.page_count

    all_rows = []
    all_pages = []

    for i in range(num_pages):
        page = doc.load_page(i)
        page_dict = {"page": i+1, "text": [], "graphics": [], "images": [], "ocr": []}

        # --- Text extraction ---
        pdf_data = page.get_text("dict")
        for block in pdf_data["blocks"]:
            if block["type"] == 0:  # text block
                for line in block.get("lines", []):
                    line_text = " ".join(span["text"] for span in line["spans"])
                    page_dict["text"].append(line_text)
                    all_rows.append({"page": i+1, "text": line_text})

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
            ocr_data = pytesseract.image_to_data(cv_img, config="--psm 11 --oem 3", output_type=Output.DICT)
            for j in range(len(ocr_data['text'])):
                if float(ocr_data['conf'][j]) > 80:
                    page_dict["ocr"].append(ocr_data['text'][j])
            # save annotated image
            cv2.imwrite(f"page_{i+1}_ocr.png", cv_img)

        all_pages.append(page_dict)

    # Convert text to DataFrame
    df = pd.DataFrame(all_rows)
    return all_pages, df
