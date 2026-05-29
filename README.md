# CartAgent - Agentic RAG + HITL

A **multi-skill AI agent** built with **FastAPI**, **LangGraph**, **OpenAI ChatGPT**, and **ChromaDB**. The agent routes each request to the right skill - Q&A (RAG), Order (HITL), or Track - and orchestrates the full conversation flow. 7 nodes, 3 skills, 1 checkpointer, ChromaDB-backed semantic retrieval.

## Skills

| Skill | Trigger | What happens |
|---|---|---|
| **Q&A (RAG)** | "Tell me about laptops" | Classify → search catalog → LLM composes answer from results |
| **Order (HITL)** | "I want to buy a ProBook 15" | LLM extracts product → draft → interrupt → confirm → place |
| **Track** | "Where is my order?" | Look up order registry by session → return status + ETA |

## Quick start

```bash
cp .env.example .env
make build
make up
make index
```
