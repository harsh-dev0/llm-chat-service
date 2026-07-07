# llm-chat-service — Future Roadmap (not in current sprint)

This document exists so future features don't require reworking the architecture — it is **not** a build plan for the current sprint. The current sprint's scope is tool-calling only, no RAG. See `README-current-sprint.md` for what's actually being built now.

## What gets added after the current sprint ships

### RAG (document-grounded answers)
- Add `pgvector` extension to the existing PostgreSQL instance — no new infra required
- Users upload a document to a conversation
- Document gets chunked, embedded, and stored
- On future messages in that conversation, relevant chunks are retrieved and injected into the LLM's context before it answers
- New endpoint: `/chat/{id}/upload-doc`
- New folder: `app/rag/`

### Agentic / multi-step tool use
- Extend the existing tool-calling from Phase 5 so the LLM can chain multiple tool calls in one turn (e.g., search → calculate → answer), not just call one tool per response
- Add a lightweight planning/loop step in `app/services/` to manage multi-turn tool execution

### Conversation memory (long-term)
- Summarize older messages once a conversation exceeds a token budget, so context doesn't grow unbounded
- Store summaries alongside raw messages in the `Messages` table or a new `ConversationSummaries` table

## Why this is documented but not built now

Bringing in RAG or multi-step agent behavior before the core chat + auth + tool-calling loop is solid would mean debugging retrieval and agent logic on top of an unstable foundation. Building it in this order also means the current sprint stays a complete, demoable product on its own — it doesn't depend on this roadmap being finished to be resume-ready.

## Updated folder structure once this roadmap is built

```text
llm-chat-service/
│
├── app/
│   ├── api/
│   ├── auth/
│   ├── chat/
│   ├── users/
│   ├── tools/
│   ├── rag/          # new
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

No action needed on this file until the current sprint (tool-calling, no RAG) is fully working end-to-end.
