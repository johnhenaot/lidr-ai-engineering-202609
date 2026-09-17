import types

import httpx2
import pytest
from anthropic import APIError as AnthropicApiError
from openai import APIError as OpenAIApiError

from app.config import Settings
from app.domain.estimate import (
    Duration,
    EstimateDraft,
    EstimationError,
    HourlyRate,
    Risk,
    TaskDraft,
    TeamMember,
)
from app.services import llm_service
from app.services.llm_service import (
    ESTIMATION_RULES,
    EXAMPLES_INTRO,
    MAX_OUTPUT_TOKENS,
    OUTPUT_RULES,
    ROLE,
    SCOPE_RULES,
    build_system_prompt,
    generate_estimate_draft,
)

TRANSCRIPT = "The client wants an online booking portal for 12 locations."
SAMPLE_DRAFT = EstimateDraft(
    meeting_summary="Client needs a booking portal.",
    estimate_title="Booking Portal",
    assumptions=["ERP exposes API."],
    out_of_scope=["Mobile app."],
    tasks=[TaskDraft(name="Discovery", optimistic=10, likely=20, pessimistic=30)],
    team=[TeamMember(role="engineers", quantity=2, details="")],
    duration=Duration(floor=2, ceiling=4, unit="weeks"),
    risks=[Risk(label="Integration", impact="high", detail="Discovery needed.")],
    confidence="High",
    confidence_rationale="Scope is clear.",
    validity_days=30,
)


def make_settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        openai_api_key="sk-openai",
        anthropic_api_key="sk-anthropic",
        **overrides,
    )


class TestBuildSystemPrompt:
    @pytest.fixture
    def fake_examples(self, monkeypatch):
        fakes = [SAMPLE_DRAFT]
        monkeypatch.setattr(llm_service, "ESTIMATION_EXAMPLES", fakes)
        return fakes

    def test_assembles_sections_in_order(self, fake_examples):
        """Assemble sections in role, rules, examples, and output order."""
        prompt = build_system_prompt()
        sections = [
            ROLE,
            ESTIMATION_RULES,
            SCOPE_RULES,
            EXAMPLES_INTRO,
            "<examples>",
            OUTPUT_RULES,
        ]
        positions = [prompt.index(s) for s in sections]

        assert positions == sorted(positions)

    def test_formats_examples_with_xml_tags_and_json_payload(self, fake_examples):
        """Format each example with 1-based id tag, meeting summary, and json."""
        prompt = build_system_prompt()
        expected_json = SAMPLE_DRAFT.model_dump_json(indent=2)

        expected_block = (
            '<example id="1">\n'
            f"<meeting_summary>\n{SAMPLE_DRAFT.meeting_summary}\n</meeting_summary>\n"
            f"<estimation_json>\n{expected_json}\n</estimation_json>\n"
            "</example>"
        )
        assert f"<examples>\n{expected_block}\n</examples>" in prompt


class TestGenerateEstimationWithOpenAI:
    @pytest.fixture(autouse=True)
    def clear_settings_env(self, monkeypatch):
        for field in Settings.model_fields:
            monkeypatch.delenv(field.upper(), raising=False)
            monkeypatch.delenv(field.lower(), raising=False)

    @pytest.fixture
    def settings(self):
        return make_settings(llm_provider="openai", llm_model="gpt-4o-mini")

    @pytest.fixture
    def mock_openai(self, mocker):
        def install(output_parsed=SAMPLE_DRAFT):
            mock_parse = mocker.AsyncMock(
                return_value=types.SimpleNamespace(output_parsed=output_parsed)
            )
            fake_client = types.SimpleNamespace(
                responses=types.SimpleNamespace(parse=mock_parse)
            )
            factory = mocker.patch.object(
                llm_service, "_openai_client", return_value=fake_client
            )
            return types.SimpleNamespace(parse=mock_parse, factory=factory)

        return install

    @pytest.mark.anyio
    async def test_returns_parsed_draft(self, mock_openai, settings):
        """Return the parsed EstimateDraft from OpenAI structured output."""
        mock_openai()

        assert await generate_estimate_draft(TRANSCRIPT, settings) is SAMPLE_DRAFT

    @pytest.mark.anyio
    async def test_builds_client_with_openai_api_key(self, mock_openai, settings):
        """Build the OpenAI client with the configured OpenAI API key."""
        mocks = mock_openai()

        await generate_estimate_draft(TRANSCRIPT, settings)

        mocks.factory.assert_called_once_with("sk-openai")

    @pytest.mark.anyio
    async def test_sends_system_prompt_as_instructions(self, mock_openai, settings):
        """Send the system prompt through the instructions parameter."""
        mocks = mock_openai()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["instructions"] == build_system_prompt()

    @pytest.mark.anyio
    async def test_sends_transcript_as_input(self, mock_openai, settings):
        """Send the transcript through the input parameter."""
        mocks = mock_openai()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["input"] == TRANSCRIPT

    @pytest.mark.anyio
    async def test_uses_configured_model(self, mock_openai, settings):
        """Request the model configured in settings."""
        mocks = mock_openai()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.anyio
    async def test_passes_estimate_draft_as_text_format(self, mock_openai, settings):
        """Pass EstimateDraft schema as text_format for structured parsing."""
        mocks = mock_openai()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["text_format"] is EstimateDraft

    @pytest.mark.anyio
    async def test_caps_output_tokens(self, mock_openai, settings):
        """Cap the response length at the shared output token limit."""
        mocks = mock_openai()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["max_output_tokens"] == MAX_OUTPUT_TOKENS

    @pytest.mark.anyio
    async def test_raises_estimation_error_when_output_parsed_is_none(
        self, mock_openai, settings
    ):
        """Raise EstimationError when OpenAI returns no parsed estimate."""
        mock_openai(output_parsed=None)

        with pytest.raises(EstimationError):
            await generate_estimate_draft(TRANSCRIPT, settings)

    @pytest.mark.anyio
    async def test_raises_estimation_error_when_openai_api_fails(
        self, mocker, settings
    ):
        """Raise EstimationError when OpenAI API call fails."""
        req = httpx2.Request("POST", "https://api.openai.com/v1")
        mock_parse = mocker.AsyncMock(
            side_effect=OpenAIApiError("connection dropped", request=req, body=None)
        )
        fake_client = types.SimpleNamespace(
            responses=types.SimpleNamespace(parse=mock_parse)
        )
        mocker.patch.object(llm_service, "_openai_client", return_value=fake_client)

        with pytest.raises(EstimationError, match="OpenAI estimation failed"):
            await generate_estimate_draft(TRANSCRIPT, settings)


class TestGenerateEstimationWithAnthropic:
    @pytest.fixture(autouse=True)
    def clear_settings_env(self, monkeypatch):
        for field in Settings.model_fields:
            monkeypatch.delenv(field.upper(), raising=False)
            monkeypatch.delenv(field.lower(), raising=False)

    @pytest.fixture
    def settings(self):
        return make_settings(llm_provider="anthropic", llm_model="claude-haiku-4-5")

    @pytest.fixture
    def mock_anthropic(self, mocker):
        def install(parsed_output=SAMPLE_DRAFT):
            mock_parse = mocker.AsyncMock(
                return_value=types.SimpleNamespace(parsed_output=parsed_output)
            )
            fake_client = types.SimpleNamespace(
                messages=types.SimpleNamespace(parse=mock_parse)
            )
            factory = mocker.patch.object(
                llm_service, "_anthropic_client", return_value=fake_client
            )
            return types.SimpleNamespace(parse=mock_parse, factory=factory)

        return install

    @pytest.mark.anyio
    async def test_returns_parsed_draft(self, mock_anthropic, settings):
        """Return the parsed EstimateDraft from Anthropic structured output."""
        mock_anthropic()

        assert await generate_estimate_draft(TRANSCRIPT, settings) is SAMPLE_DRAFT

    @pytest.mark.anyio
    async def test_builds_client_with_anthropic_api_key(self, mock_anthropic, settings):
        """Build the Anthropic client with the configured Anthropic API key."""
        mocks = mock_anthropic()

        await generate_estimate_draft(TRANSCRIPT, settings)

        mocks.factory.assert_called_once_with("sk-anthropic")

    @pytest.mark.anyio
    async def test_sends_system_prompt_as_system(self, mock_anthropic, settings):
        """Send the system prompt through the system parameter."""
        mocks = mock_anthropic()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["system"] == build_system_prompt()

    @pytest.mark.anyio
    async def test_sends_transcript_as_user_message(self, mock_anthropic, settings):
        """Send the transcript as a single user message."""
        mocks = mock_anthropic()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["messages"] == [
            {"role": "user", "content": TRANSCRIPT}
        ]

    @pytest.mark.anyio
    async def test_uses_configured_model(self, mock_anthropic, settings):
        """Request the model configured in settings."""
        mocks = mock_anthropic()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["model"] == "claude-haiku-4-5"

    @pytest.mark.anyio
    async def test_passes_estimate_draft_as_output_format(
        self, mock_anthropic, settings
    ):
        """Pass EstimateDraft schema as output_format for structured parsing."""
        mocks = mock_anthropic()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["output_format"] is EstimateDraft

    @pytest.mark.anyio
    async def test_caps_output_tokens(self, mock_anthropic, settings):
        """Cap the response length at the shared output token limit."""
        mocks = mock_anthropic()

        await generate_estimate_draft(TRANSCRIPT, settings)

        assert mocks.parse.call_args.kwargs["max_tokens"] == MAX_OUTPUT_TOKENS

    @pytest.mark.anyio
    async def test_raises_estimation_error_when_parsed_output_is_none(
        self, mock_anthropic, settings
    ):
        """Raise EstimationError when Anthropic returns no parsed estimate."""
        mock_anthropic(parsed_output=None)

        with pytest.raises(EstimationError):
            await generate_estimate_draft(TRANSCRIPT, settings)

    @pytest.mark.anyio
    async def test_raises_estimation_error_when_anthropic_api_fails(
        self, mocker, settings
    ):
        """Raise EstimationError when Anthropic API call fails."""
        req = httpx2.Request("POST", "https://api.anthropic.com/v1")
        mock_parse = mocker.AsyncMock(
            side_effect=AnthropicApiError("connection dropped", request=req, body=None)
        )
        fake_client = types.SimpleNamespace(
            messages=types.SimpleNamespace(parse=mock_parse)
        )
        mocker.patch.object(llm_service, "_anthropic_client", return_value=fake_client)

        with pytest.raises(EstimationError, match="Anthropic estimation failed"):
            await generate_estimate_draft(TRANSCRIPT, settings)


class TestGenerateEstimation:
    @pytest.fixture(autouse=True)
    def clear_settings_env(self, monkeypatch):
        for field in Settings.model_fields:
            monkeypatch.delenv(field.upper(), raising=False)
            monkeypatch.delenv(field.lower(), raising=False)

    @pytest.fixture
    def branches(self, mocker):
        return types.SimpleNamespace(
            openai=mocker.patch.object(
                llm_service, "_estimate_with_openai", return_value=SAMPLE_DRAFT
            ),
            anthropic=mocker.patch.object(
                llm_service, "_estimate_with_anthropic", return_value=SAMPLE_DRAFT
            ),
        )

    @pytest.mark.anyio
    async def test_dispatches_to_anthropic_when_provider_is_anthropic(self, branches):
        """Route to the Anthropic branch when the configured provider is anthropic."""
        settings = make_settings(llm_provider="anthropic")

        assert await generate_estimate_draft(TRANSCRIPT, settings) is SAMPLE_DRAFT

        branches.anthropic.assert_awaited_once_with(TRANSCRIPT, settings)
        branches.openai.assert_not_awaited()

    @pytest.mark.anyio
    async def test_dispatches_to_openai_when_provider_is_openai(self, branches):
        """Route to the OpenAI branch when the configured provider is openai."""
        settings = make_settings(llm_provider="openai")

        assert await generate_estimate_draft(TRANSCRIPT, settings) is SAMPLE_DRAFT

        branches.openai.assert_awaited_once_with(TRANSCRIPT, settings)
        branches.anthropic.assert_not_awaited()

    @pytest.mark.anyio
    async def test_resolves_settings_when_omitted(self, mocker, branches):
        """Resolve settings through get_settings when no settings are supplied."""
        settings = make_settings()
        mocker.patch.object(llm_service, "get_settings", return_value=settings)

        assert await generate_estimate_draft(TRANSCRIPT) is SAMPLE_DRAFT

        branches.openai.assert_awaited_once_with(TRANSCRIPT, settings)

    @pytest.mark.anyio
    async def test_raises_estimation_error_when_draft_contains_no_tasks(self, mocker):
        """Raise EstimationError when parsed draft contains an empty task list."""
        empty_draft = SAMPLE_DRAFT.model_copy(update={"tasks": []})
        mocker.patch.object(
            llm_service, "_estimate_with_openai", return_value=empty_draft
        )
        settings = make_settings(llm_provider="openai")

        with pytest.raises(EstimationError, match="Estimate contains no tasks"):
            await generate_estimate_draft(TRANSCRIPT, settings)

    @pytest.mark.anyio
    async def test_raises_estimation_error_when_hourly_rate_is_non_positive(
        self, mocker
    ):
        """Raise EstimationError when parsed draft contains a non-positive rate."""
        invalid_draft = SAMPLE_DRAFT.model_copy(
            update={"rate": HourlyRate(amount=0.0, currency="USD")}
        )
        mocker.patch.object(
            llm_service, "_estimate_with_openai", return_value=invalid_draft
        )
        settings = make_settings(llm_provider="openai")

        with pytest.raises(
            EstimationError, match="Hourly rate amount must be positive"
        ):
            await generate_estimate_draft(TRANSCRIPT, settings)
