# Software Project Estimator

Turns a client meeting transcript into a structured software project estimate
(PERT task breakdown, assumptions, exclusions, risks, confidence) via an LLM.

Architecture is **CAG** (Cache-Augmented Generation): a small, static set of
historical estimates is injected into the system prompt on every call — no
retrieval step. The byte-identical prefix is cache-friendly for provider prompt
caching.

## Requirements

[uv](https://docs.astral.sh/uv/) · Python 3.11

## Setup

```bash
uv sync
cp .env.example .env   # then fill in the key for your provider
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | when `LLM_PROVIDER=openai` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | when `LLM_PROVIDER=anthropic` | — | Anthropic API key |
| `LLM_PROVIDER` | no | `openai` | `openai` \| `anthropic` |
| `LLM_MODEL` | no | `gpt-4o-mini` | Must match the provider: `gpt-4o-mini` ↔ `openai`, `claude-haiku-4-5` ↔ `anthropic` |
| `APP_ENV` | no | `development` | Environment label |
| `LOG_LEVEL` | no | `DEBUG` | Log level label |

Only the selected provider's key is required; startup fails fast if it is missing.

## Run

```bash
uv run uvicorn app.main:app --reload
```

Swagger UI at `/docs`, health check at `/health`.

## Usage

```bash
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d @docs/estimate-request.json
```

```json
{
  "estimation": "## Estimate: Landing Page with CRM Integration\n...",
  "model": "gpt-4o-mini",
  "provider": "openai"
}
```

## Architecture

Request flow: the router validates the body and resolves `Settings` through FastAPI
dependency injection, the service assembles the system prompt (role, estimation
rules, static examples) and calls the provider SDK, and the Markdown estimate comes
back alongside the model and provider that produced it.

The knowledge base is `ESTIMATION_EXAMPLES` — editing that list is how you change
the house style, and it is the only thing that has to fit in the context window.
Providers sit behind one prompt and one response contract, so switching between
OpenAI and Anthropic is a config change, not a code change.

Layout is enforced by CI rather than documented here, so it cannot drift.

## Quality

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

CI runs these on every push and PR, plus a folder-structure check and a `/health`
smoke test. No real API keys needed — CI never makes a paid LLM call (the smoke
test uses a placeholder key).
