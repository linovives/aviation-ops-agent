import os
import json
from datetime import date
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from groq import Groq
from langgraph.graph import StateGraph, END
from rag.vector_store import query_regulations
from agent.tools import TOOLS, AVAILABLE_TOOLS

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


def _add_messages(left: list, right: list) -> list:
    return left + right


class AgentState(TypedDict):
    messages: Annotated[list, _add_messages]


def call_model(state: AgentState) -> AgentState:
    response = client.chat.completions.create(
        model=CONFIG_MODEL_NAME,
        messages=state["messages"],
        tools=TOOLS,
        tool_choice="auto",
    )
    response_message = response.choices[0].message

    message = {"role": "assistant", "content": response_message.content}
    if response_message.tool_calls:
        message["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": tool_call.type,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in response_message.tool_calls
        ]

    return {"messages": [message]}


def execute_tools(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message["tool_calls"]:
        function_name = tool_call["function"]["name"]
        function_args = json.loads(tool_call["function"]["arguments"])
        function_to_call = AVAILABLE_TOOLS[function_name]
        function_result = function_to_call(**function_args)
        content = function_result if isinstance(function_result, str) else json.dumps(function_result)

        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": function_name,
                "content": content,
            }
        )

    return {"messages": tool_messages}


def route_after_model(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.get("tool_calls"):
        return "execute_tools"
    return END


graph_builder = StateGraph(AgentState)
graph_builder.add_node("call_model", call_model)
graph_builder.add_node("execute_tools", execute_tools)
graph_builder.set_entry_point("call_model")
graph_builder.add_conditional_edges("call_model", route_after_model, {"execute_tools": "execute_tools", END: END})
graph_builder.add_edge("execute_tools", "call_model")

agent_graph = graph_builder.compile()


def build_system_message() -> dict:
    return {
        "role": "system",
        "content": (
            f"Today's date is {date.today().isoformat()}. "
            "You are an aviation operations assistant with access to EASA Flight Time "
            "Limitations regulations and real flight schedule data. When the user names "
            "a city or airport instead of giving a code, call search_airport first to "
            "resolve it before calling search_flights."
        ),
    }


def ask_agent(question: str) -> str:
    initial_state = {"messages": [build_system_message(), {"role": "user", "content": question}]}
    final_state = agent_graph.invoke(initial_state)
    return final_state["messages"][-1]["content"]


if __name__ == "__main__":
    messages = [build_system_message()]
    while True:
        question = input("> ")
        if question.strip().lower() in ("exit", "salir", "quit"):
            break
        messages.append({"role": "user", "content": question})
        state = agent_graph.invoke({"messages": messages})
        messages = state["messages"]
        print(messages[-1]["content"])