# Sage — Specification

Status: implemented; not yet run against live Bedrock (pending AWS credentials).
This spec describes the system as built. See `ARCHITECTURE.md` for diagrams and
`README.md` for setup.

## 1. Purpose

Sage is a chatbot built on **Amazon Bedrock** with **Claude** models. It
provides a streaming chat experience over a web UI and a terminal CLI, with
optional retrieval-augmented generation (RAG) over a **Bedrock Knowledge Base**.

## 2. Goals / Non-goals

**Goals**
- Token-by-token streaming chat backed by Claude on Bedrock.
- Optional grounding in the user's own documents via a Bedrock Knowledge Base,
  with source citations.
- Per-conversation memory; in-process or Redis-backed.
- One orchestration pipeline reused by multiple frontends (web, CLI).
- Deployable as a container with no AWS keys baked in.

**Non-goals**
- Document ingestion / Knowledge Base creation (done in AWS, out of app scope).
- User accounts or multi-tenant authz (only a single optional API key).
- Anthropic server-side tools or refusal fallbacks (unavailable on Bedrock).
- Agentic tool use / function calling (not part of this version).

## 3. Users & use cases

- **End user** chats in the browser or terminal and gets grounded, cited
  answers.
- **Operator** configures the model, region, Knowledge Base, auth, and memory
  backend via environment variables, and deploys the container.

## 4. Functional requirements

1. **Streaming generation** — responses stream token-by-token from Bedrock to
   the client.
2. **RAG (optional)** — when `KNOWLEDGE_BASE_ID` is set, retrieve top-k passages
   per question, inject them into the prompt, and return their source labels.
   When unset, answer without retrieval.
3. **Conversation memory** — retain the last `MAX_TURNS` turns per `session_id`;
   in-process by default, Redis when `REDIS_URL` is set.
4. **Model selection** — a default model plus a per-request override validated
   against an allow-list (`MODEL_CHOICES`).
5. **Adaptive thinking** — off by default; toggleable per deployment, per UI
   session, or per CLI invocation.
6. **Auth (optional)** — when `API_KEY` is set, `/api/chat` and `/api/reset`
   require a matching `X-API-Key` header.
7. **Friendly errors** — Bedrock/AWS failures are mapped to actionable messages
   and surfaced to the client instead of raw stack traces.
8. **Usage/cost reporting** — input/output token counts and an approximate USD
   cost are logged and returned per turn.
9. **Frontends** — a web UI (multi-chat sidebar, Markdown, copy, picker) and a
   terminal CLI, both consuming the same pipeline.

## 5. HTTP API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | — | Serves the chat UI (`static/index.html`). |
| GET | `/api/health` | — | `{status, model}`. |
| GET | `/api/config` | — | UI bootstrap: `{models, default_model, thinking_default, rag_enabled, auth_required}`. |
| POST | `/api/chat` | API key* | Streams the reply as Server-Sent Events. |
| POST | `/api/reset` | API key* | Clears a session's memory: `{session_id}`. |

\* Required only when `API_KEY` is configured.

### `POST /api/chat` request

```json
{
  "session_id": "uuid",
  "message": "string",
  "model": "us.anthropic.claude-opus-4-8 | null",
  "enable_thinking": true
}
```

`model` is optional and silently falls back to the default if it isn't in the
allow-list. `enable_thinking` is optional (defaults to the server setting).

### `POST /api/chat` response — SSE event stream

`Content-Type: text/event-stream`; each event is `data: <json>\n\n`. Event
types, in order:

| `type` | Payload | When |
|---|---|---|
| `sources` | `{ "sources": [{ "source": str, "score": float? }] }` | Once, before deltas, only if RAG returned passages. |
| `delta` | `{ "text": str }` | Repeated, one per streamed chunk. |
| `done` | `{ "usage": { "input_tokens", "output_tokens", "est_cost_usd", "model" } }` | Once, at the end of a successful turn. |
| `error` | `{ "message": str }` | On failure (terminates the stream; the turn is not persisted). |

## 6. Data shapes

- **Session message** (memory): `{ "role": "user" | "assistant", "content": str }`.
- **Passage** (`app/rag.py`): `{ text: str, source: str, score: float | None }`.
  `source` is a best-effort label derived from the retrieval result's location.

## 7. Configuration (environment / `.env`)

| Variable | Default | Meaning |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Region with Bedrock + Claude enabled. |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-opus-4-8` | Cross-region inference-profile id (note `us.` prefix). |
| `KNOWLEDGE_BASE_ID` | *(empty)* | Bedrock KB id; empty disables RAG. |
| `RAG_TOP_K` | `5` | Passages retrieved per question. |
| `RAG_MIN_SCORE` | `0.0` | Drop passages scoring below this. |
| `MAX_TOKENS` | `4096` | Max output tokens. |
| `ENABLE_THINKING` | `false` | Default adaptive-thinking state. |
| `API_KEY` | *(empty)* | If set, require `X-API-Key` on chat endpoints. |
| `REDIS_URL` | *(empty)* | Redis for shared/persistent sessions; empty = in-memory. |
| `MAX_TURNS` | `12` | Turns kept per session. |
| `LOG_LEVEL` | `INFO` | Logging verbosity. |

## 8. Behavioral rules

- **Retrieve-then-generate**: the app fetches passages and injects them as a
  second `system` block, then streams Claude's answer itself (not Bedrock's
  `retrieve_and_generate`), keeping prompt, citations, and streaming under app
  control.
- **Persona**: answer concisely in Markdown; when context is provided, ground in
  it and cite source labels; if the answer isn't in context, say so and do not
  invent facts or citations.
- **Persistence**: a turn is written to memory only after the generation
  succeeds; failed turns leave memory unchanged.
- **Memory scope**: history is keyed by `session_id`; the web UI uses one per
  sidebar chat and also mirrors messages in browser localStorage for re-render.

## 9. Security

- Optional API-key gate on chat endpoints.
- AWS credentials resolved via the standard provider chain (prefer an IAM role
  in production — see `deploy/`); never embedded in the app.
- `RedisStore` keys expire after 24h.
- Knowledge Base content is injected as context, not executed; no tool use.

## 10. Deployment

Container-based **AWS App Runner** with an IAM instance role for Bedrock, port
`8000`, health check `/api/health`, env-var config, optional ElastiCache Redis.
Full procedure in `deploy/APP_RUNNER.md`.

## 11. Testing

`pytest` suite mocks Bedrock and retrieval (`tests/conftest.py`) so it runs
without AWS. `scripts/eval_rag.py` evaluates retrieval quality against a live
Knowledge Base.

## 12. Open items / future work

- Run against live Bedrock and confirm the inference-profile id.
- Markdown-only UI today; consider richer source rendering.
- Single API key only; add real auth for multi-user production.
- In-memory store loses history on restart unless `REDIS_URL` is set; required
  for multi-instance/autoscaled deploys.
