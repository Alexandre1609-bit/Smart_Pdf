import pymupdf  

def get_book_content():
    while True:
        try:
            pdf_path = input("Select file: ")
            doc = pymupdf.open(pdf_path)
            break
        except:
            print("File not found")
            continue

    num_pages = doc.page_count
    book_content = []
    for i in range(num_pages):
        page = doc.load_page(i)
        page_text = page.get_text("text")
        raw_txt = page_text.replace("\t", "")
        book_content.append(raw_txt)
        book_content.append(f"\n\n --- page {i+1} break --- \n\n")
    return book_content

def txt_write(book_content):
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write("".join(book_content))

data = get_book_content()
cleaned = [page.lower() for page in data]
txt_write(cleaned)


