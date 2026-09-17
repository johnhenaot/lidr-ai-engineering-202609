# AGENTS.md

## Overview

FastAPI service turning a client meeting transcript into a structured project
estimate. CAG architecture: the static examples in `app/context/examples.py` are
injected into the system prompt on every call; there is no retrieval step.

Python 3.11, uv, Pydantic v2, ruff, pytest. OpenAI (Responses API) or Anthropic
(Messages API), selected by `LLM_PROVIDER`.

## Commands

```bash
uv sync                                 # install from uv.lock
cp .env.example .env                    # set the key for your provider
uv run uvicorn app.main:app --reload    # /docs, /health
uv run ruff check && uv run ruff format
uv run pytest
uv run pytest tests/test_config.py      # one module
uv run pytest -k health                 # by keyword
```

- Add dependencies with `uv add` / `uv add --dev`; never hand-edit `pyproject.toml`. CI runs `uv sync --locked`.
- Match `LLM_MODEL` to `LLM_PROVIDER` (`gpt-4o-mini` ↔ openai, `claude-haiku-4-5` ↔ anthropic) or the provider returns 404. Only the selected provider's key is required.

## Testing

- Mirror the module under test: `tests/test_<module>.py`.
- Mark async tests `@pytest.mark.anyio`; `pytest-asyncio` is not installed.
- Override settings with `app.dependency_overrides[get_settings]`; clear on teardown.
- Never make a real LLM call. CI requires no real secrets; the smoke test sets a placeholder key.
- Write the test first; watch it fail for the right reason.
- Test one behavior per test; "and" in a name means split it.
- Delete any test no production change can turn red, or that another test already covers.
- Test project logic, never framework or library defaults.
- Never assert on static config strings; titles and versions are change detectors.
- Reach private functions through their public caller only.
- Mock with `pytest-mock`; patch the name where it is used, not where it is defined.
- Keep fixtures in the class that uses them.
- Group in a `TestSubject` class, name methods `test_snake_case_sentence`, write PEP 257 imperative docstrings.

## Code style

- Write no comments or docstrings in production code; name things precisely instead.
- Specify behavior in tests, not prose.
- Fix the code rather than silencing a linter.
- Never set config that restates a tool default.

## CI

`.github/workflows/ci.yml`, on every push and pull request:

- `structure` — asserts the file layout and that `.env` is gitignored. Update its path list when moving files.
- `test` — `uv sync --locked`, ruff, pytest, then boots the server and curls `/health` and `/docs`.

Keep actions SHA-pinned, `permissions: contents: read`, `persist-credentials: false`.
Check changes with `actionlint` and `zizmor`.

## Before reporting done

- Run `uv run ruff check && uv run ruff format --check && uv run pytest` and read the output.
- Never commit or push without explicit approval; stage and report.
- Write technical content in English.
- Keep the README scannable: describe flow and boundaries, never directory trees.

## Gotchas

- Call `get_settings()`; never instantiate `Settings()` at import — it crashes pytest collection when no key is set.
- Lifespan validates settings at startup; inside `with TestClient(app)` it calls `get_settings()` directly, so `dependency_overrides` do not apply during startup.
- Isolate settings tests with `monkeypatch.chdir(tmp_path)` to prevent `pydantic-settings` from reading a developer's local `.env`.
- Patch `estimations.generate_estimation`, not the service module; the router imports the name.
- Check SDK types against the installed version. This stack uses `httpx2`, `Response.output_text` is `str`, and Anthropic's `ContentBlock` is a union — filter `block.type == "text"`.
- Do not trust LLM arithmetic; PERT sums drift. Compute derived numbers in Python if exactness matters.
