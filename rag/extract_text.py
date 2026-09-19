from pypdf import PdfReader


def extract_pdf_text(pdf_path: str) -> str:

    reader = PdfReader(pdf_path)

    regulations = ""

    for page in reader.pages:
        regulations += page.extract_text()

    return regulations


if __name__ == "__main__":
    texto = extract_pdf_text("data/regulations/flt_regulation.pdf")
    print(texto[:500])