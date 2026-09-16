import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestGetSettings:
    def test_default_values(self, monkeypatch):
        """Return default values when optional environment variables are unset."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        settings = get_settings()

        assert settings.llm_provider == "openai"
        assert settings.llm_model == "gpt-4o-mini"
        assert settings.app_env == "development"
        assert settings.log_level == "DEBUG"
        assert settings.anthropic_api_key is None

    def test_returns_cached_instance(self, monkeypatch):
        """Return the same cached Settings instance across repeated calls."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        assert get_settings() is get_settings()

    @pytest.mark.parametrize("provider", ["openai", "anthropic"])
    @pytest.mark.parametrize("key", [None, ""], ids=["missing", "empty"])
    def test_selected_provider_requires_its_own_key(self, monkeypatch, provider, key):
        """Raise ValidationError when active provider API key is missing or empty."""
        monkeypatch.setenv("LLM_PROVIDER", provider)
        if key is not None:
            monkeypatch.setenv(f"{provider.upper()}_API_KEY", key)

        with pytest.raises(
            ValidationError, match=f"{provider.upper()}_API_KEY is required"
        ):
            get_settings()

    @pytest.mark.parametrize(
        ("provider", "other_key"),
        [("openai", "anthropic_api_key"), ("anthropic", "openai_api_key")],
    )
    def test_inactive_provider_key_is_optional(self, monkeypatch, provider, other_key):
        """Allow unselected provider API key to be omitted."""
        monkeypatch.setenv("LLM_PROVIDER", provider)
        monkeypatch.setenv(f"{provider.upper()}_API_KEY", "sk-test")

        settings = get_settings()

        assert getattr(settings, other_key) is None

    def test_unknown_keys_in_env_file_are_ignored(self, monkeypatch, tmp_path):
        """Ignore undeclared variables present in a .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-test\nSOME_UNRELATED_VAR=whatever\n")
        monkeypatch.chdir(tmp_path)

        settings = get_settings()

        assert not hasattr(settings, "some_unrelated_var")
