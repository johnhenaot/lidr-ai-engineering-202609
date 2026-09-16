import pytest
from pydantic import ValidationError

from app.config import Settings

ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "APP_ENV",
    "LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Your shell's real env must not decide whether these tests pass."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def build(env_file=None, **overrides) -> Settings:
    """Settings() defaults to reading the project's own .env, which tests must not touch.

    `_env_file` exists at runtime but pydantic's synthesized __init__ hides it from
    type checkers, so the ignore lives here once instead of at every call site.
    """
    return Settings(_env_file=env_file, **overrides)  # type: ignore[call-arg]


def test_defaults_match_the_spec():
    settings = build(openai_api_key="sk-test")

    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.app_env == "development"
    assert settings.log_level == "DEBUG"
    assert settings.anthropic_api_key is None


def test_reads_values_from_an_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-file\nLLM_MODEL=gpt-4o\n")

    settings = build(env_file)

    assert settings.openai_api_key == "sk-from-file"
    assert settings.llm_model == "gpt-4o"


def test_environment_wins_over_the_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-file\nLLM_MODEL=from-file\n")
    monkeypatch.setenv("LLM_MODEL", "from-environment")

    assert build(env_file).llm_model == "from-environment"


def test_selected_provider_requires_its_own_key():
    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY is required"):
        build(llm_provider="anthropic", openai_api_key="sk-test")


def test_other_provider_key_may_be_absent():
    settings = build(llm_provider="anthropic", anthropic_api_key="sk-ant")

    assert settings.openai_api_key is None


def test_empty_key_counts_as_missing():
    with pytest.raises(ValidationError, match="OPENAI_API_KEY is required"):
        build(openai_api_key="")


def test_unknown_provider_is_rejected():
    with pytest.raises(ValidationError, match="'openai' or 'anthropic'"):
        build(llm_provider="gemini", openai_api_key="sk-test")


def test_unrelated_env_vars_are_ignored(monkeypatch):
    monkeypatch.setenv("SOME_UNRELATED_VAR", "whatever")

    assert build(openai_api_key="sk-test").llm_provider == "openai"
