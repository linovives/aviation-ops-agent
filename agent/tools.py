from rag.vector_store import query_regulations
from data_pipeline.aerodatabox_client import get_airport_flights


def search_regulations(question: str) -> str:
    chunks = query_regulations(question)
    return "\n\n".join(chunks)


def search_flights(code_type: str, code: str, from_local: str, to_local: str) -> dict:
    return get_airport_flights(code_type, code, from_local, to_local)