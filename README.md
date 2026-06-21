# Sage

A chatbot built on **Amazon Bedrock** with **Claude** models. Python + FastAPI
backend, streaming web chat UI, and optional **RAG** over your own documents via
**Bedrock Knowledge Bases**.

## Features

- 💬 Streaming chat UI (token-by-token, SSE) with multi-chat sidebar, Markdown & copy
- 🖥️ Terminal CLI (`python -m app.cli`) sharing the same pipeline
- 🧠 Claude on Bedrock via the official Anthropic SDK (`AnthropicBedrock`)
- 📚 Retrieval-augmented answers from a Bedrock Knowledge Base (optional)
- 🗂️ Per-session conversation memory (in-process or Redis-backed)
- 🎚️ In-UI model picker + adaptive-thinking toggle
- 🔐 Optional API-key auth on the chat endpoints
- 📊 Token-usage & rough cost logging per turn
- 🩺 Friendly, actionable error messages for common Bedrock/AWS failures
- 🐳 Dockerfile + compose (with Redis); pytest suite that runs without AWS

## Architecture

```
Browser (static/index.html)
   │  POST /api/chat  (SSE stream)
   ▼
FastAPI (app/main.py)
   ├── rag.py            → boto3 bedrock-agent-runtime.retrieve()   ← Knowledge Base
   └── chat.py           → AnthropicBedrock.messages.stream()       ← Claude (Bedrock)
```

We use boto3 for Knowledge Base retrieval (not exposed in the Anthropic SDK) and
the Anthropic SDK for generation — `retrieve` then generate, so Sage controls
the prompt and streams the response, rather than the all-in-one
`retrieve_and_generate`.

See [ARCHITECTURE.md](ARCHITECTURE.md) for component and request-flow diagrams
and the key design decisions, and [SPEC.md](SPEC.md) for the functional spec and
the HTTP/SSE API.

## Prerequisites

- Python 3.10+
- An AWS account with **Bedrock access in your region**

### One-time AWS / Bedrock setup

1. **Enable Claude model access.** AWS Console → **Bedrock** → *Model access* →
   request access to the Anthropic Claude models you want. Approval is usually
   instant.
2. **Find the model id.** Bedrock → *Inference and Assessment* → *Cross-region
   inference*. Newer Claude models use an inference profile id with a region
   prefix, e.g. `us.anthropic.claude-opus-4-8`. Put it in `BEDROCK_MODEL_ID`.
3. **Configure credentials** (any one of):
   - `aws configure` (creates a shared profile — recommended for local dev)
   - environment variables `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
   - an IAM role (when running on AWS)

   The IAM principal needs `bedrock:InvokeModelWithResponseStream` (and
   `bedrock:Retrieve` if you use a Knowledge Base).
4. **(Optional) Create a Knowledge Base** for RAG. Bedrock → *Knowledge Bases* →
   create one backed by an S3 bucket of your documents, sync it, then copy its
   **Knowledge Base ID** into `KNOWLEDGE_BASE_ID`. Leave it empty to run without
   RAG.

## Run it

```bash
cd Chatbot
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt

copy .env.example .env          # then edit .env with your region / model / KB id

python -m uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

Health check: http://127.0.0.1:8000/api/health

### Or use the terminal (CLI)

Same retrieval + generation pipeline, streamed to stdout:

```bash
python -m app.cli                                  # default model
python -m app.cli --model us.anthropic.claude-sonnet-4-6 --thinking
# /reset clears memory · /exit (or Ctrl-D) quits
```

## Configuration

All settings come from `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Region with Bedrock + Claude access |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-opus-4-8` | Claude inference profile id |
| `KNOWLEDGE_BASE_ID` | *(empty)* | Bedrock KB id; empty = no RAG |
| `RAG_TOP_K` | `5` | Passages retrieved per question |
| `RAG_MIN_SCORE` | `0.0` | Drop passages below this relevance score |
| `MAX_TOKENS` | `4096` | Max output tokens |
| `ENABLE_THINKING` | `false` | Adaptive thinking (quality vs. latency) |
| `API_KEY` | *(empty)* | If set, require `X-API-Key` on chat endpoints |
| `REDIS_URL` | *(empty)* | Redis for shared/persistent sessions; empty = in-memory |
| `MAX_TURNS` | `12` | Conversation turns kept per session |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Project layout

```
app/
  main.py            FastAPI routes, SSE streaming, auth, /api/config
  config.py          Settings + model registry + pricing
  bedrock_client.py  AnthropicBedrock client
  rag.py             Knowledge Base retrieval
  chat.py            Orchestration, memory, persona, usage logging
  store.py           Session memory (in-memory / Redis)
  errors.py          Friendly Bedrock/AWS error messages
  cli.py             Terminal chatbot (stdio)
static/
  index.html         Chat UI (sidebar/multi-chat, Markdown, copy, picker)
tests/               pytest suite (mocks Bedrock — no AWS needed)
scripts/
  eval_rag.py        Knowledge Base retrieval eval harness
  evalset.json       Sample eval cases
deploy/
  APP_RUNNER.md      AWS App Runner deployment guide
  bedrock-iam-policy.json  Instance-role policy for Bedrock
  push-to-ecr.sh     Build + push the image to ECR
Dockerfile, docker-compose.yml
```

## Deploy to AWS

See [deploy/APP_RUNNER.md](deploy/APP_RUNNER.md) — container-based App Runner
with a Bedrock IAM instance role (no AWS keys in the app), `/api/health` health
check, and env-var config. Build/push with `deploy/push-to-ecr.sh`.

## Docker

```bash
copy .env.example .env     # fill in AWS_REGION, BEDROCK_MODEL_ID, etc.
docker compose up --build
```

Compose also starts Redis and points `REDIS_URL` at it, so sessions persist
across restarts. Open http://127.0.0.1:8000. For AWS credentials in containers,
prefer mounting `~/.aws` or attaching an IAM role over putting keys in `.env`.

## Testing

```bash
pip install -r requirements-dev.txt
pytest                       # all tests mock Bedrock + retrieval; no AWS needed
```

Once a Knowledge Base is live, evaluate retrieval quality:

```bash
python -m scripts.eval_rag  # edit scripts/evalset.json for your docs
```

## Notes & next steps

- Conversation memory is in-process (lost on restart). Swap `_sessions` in
  `app/chat.py` for Redis/DB for production.
- For higher throughput / lower cost, set `BEDROCK_MODEL_ID` to a Sonnet profile
  (e.g. `us.anthropic.claude-sonnet-4-6`).
- Bedrock does not support Anthropic server-side tools or refusal fallbacks; the
  Messages API surface (streaming, thinking, system prompts) works as usual.
