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

def query_regulations(question: str, top_k: int = 3) -> list:
    question_embedding = get_embedding(question)

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
    )

    return results["documents"][0]

if __name__ == "__main__":
    question = "What is the minimum rest period after a flight duty period?"
    results = query_regulations(question)
    for result in results:
        print(result)
        print("---")