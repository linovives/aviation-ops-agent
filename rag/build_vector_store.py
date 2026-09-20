from rag.extract_text import extract_pdf_text
from rag.chunk_text import chunk_text
from rag.vector_store import add_chunks_to_collection

PDF_PATH = "data/regulations/flt_regulation.pdf"
CHUNK_SIZE = 150
CHUNK_OVERLAP = 30


def build() -> None:
    text = extract_pdf_text(PDF_PATH)
    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    add_chunks_to_collection(chunks)
    print(f"Indexed {len(chunks)} chunks from {PDF_PATH} into the ftl_regulation collection")


if __name__ == "__main__":
    build()
