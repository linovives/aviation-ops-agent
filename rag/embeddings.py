from sentence_transformers import SentenceTransformer

CONFIG_MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(CONFIG_MODEL_NAME)

def get_embedding(text: str):
    return model.encode(text)

if __name__ == "__main__":
    print(get_embedding("Hello World"))