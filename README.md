# llm-chat-service

A backend service for an LLM-powered chat application — built incrementally with FastAPI, PostgreSQL, JWT auth, and LLM tool-calling.

This README describes the **current sprint scope**. RAG (document retrieval) is intentionally **not** part of this build — it's a future addition, not a current phase. Keeping it out for now keeps the sprint focused: get chat + auth + LLM + tools working end-to-end before adding retrieval on top.

## What it does (this sprint)

1. Users sign up and log in — get a JWT, stay authenticated across requests.
2. Users create conversations and send messages.
3. Messages go to an LLM. The LLM can call tools (weather, calculator, web search, custom Python execution) mid-response and use the results to answer.
4. Responses stream back token-by-token, not as one blocking blob.
5. Every conversation and message is persisted in PostgreSQL — history survives across sessions.
6. Runs in Docker; basic rate limiting and logging in place.

## Build order

| Stage | What gets added |
|---|---|
| 1. Core API | Health check, User CRUD, Chat CRUD, Message CRUD |
| 2. Database | PostgreSQL — Users, Conversations, Messages tables |
| 3. Auth | Signup/Login, JWT issuing + validation, protected routes |
| 4. LLM | Connect an LLM provider, stream responses, persist chat history |
| 5. Tool calling | Weather tool, calculator tool, web search tool, custom Python execution tool |
| 6. Production hardening | Docker, Redis, rate limiting, logging, background tasks |

**No RAG in this build.** No vector DB, no embeddings, no document upload/retrieval. That's a deliberate scope cut for this sprint.

## Folder structure

```text
llm-chat-service/
│
├── app/
│   ├── api/
│   ├── auth/
│   ├── chat/
│   ├── users/
│   ├── tools/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── database/
│   ├── middleware/
│   ├── core/
│   └── main.py
│
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Why this scope

Each stage builds on the one before it, and none of them are skippable shortcuts: a real auth system needs a working DB layer first, streaming needs an LLM connection before tools can hook into it, and tool-calling needs a stable message loop before it's worth adding. RAG is left out deliberately — it's a separate concern (embeddings, a vector store, retrieval logic) layered on top of a chat system that has to work correctly on its own first. Adding it now would mean building on an unfinished foundation.

See `README-future-roadmap.md` for what comes after this sprint (RAG, agent behavior, etc.) — not being built now, just documented so the architecture doesn't need to be reworked later.