import os
from dotenv import load_dotenv
from groq import Groq
from rag.vector_store import query_regulations

load_dotenv()

CONFIG_API_KEY = os.getenv("GROQ_API_KEY")
CONFIG_MODEL_NAME = "openai/gpt-oss-20b"

client = Groq(api_key=CONFIG_API_KEY)

def ask_with_context(question: str) -> str:
    chunks = query_regulations(question)
    context = "\n\n".join(chunks)

    prompt = f"""Answer the question using only the following context. If the answer is not in the context, say you don't know.

            Context:
            {context}

            Question: {question}"""

    return ask_llm(prompt)

def ask_llm(question: str) -> str:
    response = client.chat.completions.create(
        model=CONFIG_MODEL_NAME,
        messages=[
            {"role": "user", "content": question}
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    answer = ask_with_context("What is the minimum rest period after a flight duty period?")
    print(answer)