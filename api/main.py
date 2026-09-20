import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from agent.graph import agent_graph, build_system_message

app = FastAPI(title="Aviation Ops Agent")

sessions: dict[str, list] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    messages = sessions.get(session_id, [build_system_message()])

    messages.append({"role": "user", "content": request.message})
    state = agent_graph.invoke({"messages": messages})
    messages = state["messages"]
    sessions[session_id] = messages

    return ChatResponse(session_id=session_id, response=messages[-1]["content"])
