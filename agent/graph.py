import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

CONFIG_API_KEY = os.getenv("GROQ_API_KEY")
CONFIG_MODEL_NAME = "openai/gpt-oss-20b"

client = Groq(api_key=CONFIG_API_KEY)

def ask_llm(question: str) -> str:
    response = client.chat.completions.create(
        model=CONFIG_MODEL_NAME,
        messages=[
            {"role": "user", "content": question}
        ],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    response = ask_llm("What is 2+2?")

    print(response)