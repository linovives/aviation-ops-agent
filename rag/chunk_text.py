from rag.extract_text import extract_pdf_text

def chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    words = text.split()
    chunks = []
    start = 0

    while start<len(words):
        piece = words[start:start+chunk_size]
        chunk = " ".join(piece)
        chunks.append(chunk)
        start += (chunk_size - overlap)

    return chunks

if __name__ == "__main__":
    texto = extract_pdf_text("data/regulations/flt_regulation.pdf")
    chunks = chunk_text(texto, 150, 30)
    print(len(chunks))
    print(chunks[0]) 