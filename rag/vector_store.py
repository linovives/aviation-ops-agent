import chromadb
from rag.embeddings import get_embedding
from rag.chunk_text import chunk_text
from rag.extract_text import extract_pdf_text

CONFIG_DB_PATH = "data/chroma_db"
CONFIG_COLLECTION_NAME = "ftl_regulation"

client = chromadb.PersistentClient(path=CONFIG_DB_PATH)
collection = client.get_or_create_collection(name=CONFIG_COLLECTION_NAME)

def add_chunks_to_collection(chunks: list) -> None:
    ids = []
    documents = []
    embeddings = []

    for i, chunk in enumerate(chunks):
        ids.append(f"chunk_{i}")
        documents.append(chunk)
        embeddings.append(get_embedding(chunk))

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
    )


if __name__ == "__main__":
    text = extract_pdf_text("data/regulations/flt_regulation.pdf")
    chunks = chunk_text(text, 150, 30)
    add_chunks_to_collection(chunks)
    print(f"Added {len(chunks)} chunks to the collection")