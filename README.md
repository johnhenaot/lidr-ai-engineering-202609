# Software Project Estimator

Turns a client meeting transcript into a structured software project estimate
(PERT task breakdown, assumptions, out of scope, risks, confidence) via an LLM.

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

The router receives the transcript, the LLM service parses it into a structured
estimate draft (OpenAI Responses or Anthropic Messages API), and Python computes
all PERT math, contingency, and Markdown formatting deterministically.

Both providers sit behind a shared prompt and response contract — switching
between OpenAI and Anthropic is a config change, not a code change.

## Quality

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

CI runs these on every push and PR, plus layout verification and a `/health`
smoke test. No real API keys needed — CI never makes a paid LLM call (smoke test
uses a placeholder key).
