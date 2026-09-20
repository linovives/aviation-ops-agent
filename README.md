# Aviation Ops Agent

A tool-calling AI agent that answers aviation operations questions by combining two sources: real flight schedules (AeroDataBox API) and EASA Flight Time Limitations (FTL) regulations, retrieved via RAG. Built with LangGraph orchestrating the Groq API (`openai/gpt-oss-20b`) directly through the official `groq` SDK, without `langchain-groq`.

Personal portfolio project to demonstrate RAG, agent orchestration, and tool-calling in a real (if narrow) operational domain.

## What it does

Ask it things like:

- "What is the minimum rest period after a flight duty period?" — answered purely from the EASA FTL regulation text.
- "What flights are departing from Barcelona in the next few hours?" — resolves "Barcelona" to an airport code, then queries real flight data.
- "A crew member reports for duty in Madrid at 14:00 — what flights leave before 18:00, and what's the max duty period they could legally be assigned?" — combines both sources in one answer.

The agent decides on its own which tool(s) to call, in what order, and whether it needs multiple rounds of tool calls before answering.

## How it works

```
question ──> [call_model] ──tool_calls?──> [execute_tools] ──┐
                  ▲                                          │
                  └──────────────────────────────────────────┘
                  no tool_calls
                  │
                  ▼
                final answer
```

A LangGraph `StateGraph` with two nodes:

- **`call_model`** — sends the conversation history to Groq along with the 3 tool schemas. The model either answers directly or requests one or more tool calls.
- **`execute_tools`** — runs whichever tools were requested locally, appends their results to the conversation, and loops back to `call_model`.

The loop continues until the model responds without requesting any more tools.

### Tools available to the agent

| Tool | Purpose |
|---|---|
| `search_regulations` | Semantic search (ChromaDB + `all-MiniLM-L6-v2`) over the EASA FTL regulation PDF. |
| `search_flights` | Real scheduled flights for an airport, within a window of at most 12 hours (an AeroDataBox API constraint). Filters out marketing codeshare duplicates and caps the result at 50 flights total (split across departures/arrivals) to stay within token budget. |
| `search_airport` | Resolves a city or airport name (e.g. "Barcelona") to its ICAO/IATA codes, since `search_flights` needs a code, not a name. |

### Data pipeline (`data_pipeline/`)

`aerodatabox_client.py` wraps the AeroDataBox REST API (airport search, flights-by-airport) and handles its non-JSON failure modes (204 no content, 400 invalid window, 404 unknown airport) so a bad query never crashes the agent. `database.py` is an earlier standalone experiment that persists flights into a local SQLite database — it is not wired into the live agent, which queries the API directly instead.

### RAG pipeline (`rag/`)

`extract_text.py` (PDF → text) → `chunk_text.py` (word-based chunking with overlap) → `embeddings.py` (`sentence-transformers`) → `vector_store.py` (ChromaDB, persisted at `data/chroma_db/`). `build_vector_store.py` runs the whole pipeline in one command and is idempotent (`upsert`, safe to re-run).

## Tech stack

Python 3.12 · [uv](https://docs.astral.sh/uv/) · [Groq](https://groq.com/) (`openai/gpt-oss-20b`) · [LangGraph](https://www.langchain.com/langgraph) · [ChromaDB](https://www.trychroma.com/) · `sentence-transformers` · [FastAPI](https://fastapi.tiangolo.com/) · `pytest` · Docker

## Project structure

```
agent/            tools.py (schemas + implementations), graph.py (the LangGraph agent)
api/              FastAPI app exposing the agent over HTTP
data_pipeline/    AeroDataBox API client and SQLite storage experiment
rag/              PDF extraction, chunking, embeddings, vector store, build script
tests/            pytest suite (mocked, no real API calls)
data/             regulation PDF (tracked) + generated flights.db / chroma_db (gitignored)
Dockerfile        builds the vector store into the image, CPU-only torch
```

## Setup

Requires an [AeroDataBox](https://rapidapi.com/aedbx-aedbx/api/aerodatabox) API key (via RapidAPI) and a [Groq](https://console.groq.com/) API key.

```bash
git clone <this-repo>
cd aviation-ops-agent
cp .env.example .env   # fill in AERODATABOX_API_KEY, AERODATABOX_HOST, GROQ_API_KEY
uv sync
uv run python -m rag.build_vector_store   # indexes the FTL regulation PDF into ChromaDB
```

## Usage

### Interactive CLI

```bash
uv run python -m agent.graph
```

Ask questions one after another (conversation memory is kept within the session); type `exit` to quit.

### HTTP API

```bash
uv run uvicorn api.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What flights are departing from Madrid in the next few hours?"}'
```

Response includes a `session_id` — pass it back on subsequent requests to continue the same conversation:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "and arrivals?", "session_id": "<the one you got back>"}'
```

Interactive API docs at `http://127.0.0.1:8000/docs`. Health check at `GET /health`.

### Docker

```bash
docker build -t aviation-ops-agent .
docker run -p 8000:8000 --env-file .env aviation-ops-agent
```

The image builds the vector store from the tracked PDF at build time, so it doesn't depend on any local generated data.

## Testing

```bash
uv run python -m pytest tests/ -v
```

28 tests covering the tool implementations, the graph's nodes and routing, the AeroDataBox client's error handling, and the API — all mocked, no real API calls or costs.

## Known limitations

- **Groq free-tier rate limit (8000 tokens/minute)**: long conversations or questions that need both `search_flights` and `search_regulations` at once can occasionally hit this. No retry/backoff is implemented — a real production deployment on a paid tier wouldn't hit this.
- **No defensive handling for malformed tool calls**: if the model requested a tool name outside the 3 defined ones, or sent invalid JSON arguments, the graph would raise rather than recover gracefully. Low risk with only 3 tools and forced schemas, but a known gap.
- **Sessions are in-memory** in the API (`dict`, single process) — they don't survive a restart and wouldn't work across multiple workers. Fine for a demo, not for production.
- **No frontend** — the agent is reachable via the CLI, `curl`, or the Swagger UI at `/docs`.
