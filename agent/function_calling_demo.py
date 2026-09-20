import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

CONFIG_API_KEY = os.getenv("GROQ_API_KEY")
CONFIG_MODEL_NAME = "openai/gpt-oss-20b"

client = Groq(api_key=CONFIG_API_KEY)


def get_fake_weather(city: str) -> dict:
    return {"city": city, "condition": "clear sky", "temp_c": 21}


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_fake_weather",
            "description": "Get the current weather for a given city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Madrid' or 'Barcelona'.",
                    },
                },
                "required": ["city"],
            },
        },
    }
]

available_tools = {
    "get_fake_weather": get_fake_weather,
}

messages = [
    {"role": "user", "content": "What's the weather like in Madrid and in Barcelona?"},
]

while True:
    response = client.chat.completions.create(
        model=CONFIG_MODEL_NAME,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message
    print(response_message)

    tool_calls = response_message.tool_calls

    if not tool_calls:
        print(response_message.content)
        break

    messages.append(response_message)

    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)

        function_to_call = available_tools[function_name]
        function_result = function_to_call(**function_args)

        print(f"calling {function_name}({function_args}) -> {function_result}")

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_result),
            }
        )
