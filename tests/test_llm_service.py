import types

import pytest

from app.config import Settings
from app.services import llm_service
from app.services.llm_service import (
    ESTIMATION_RULES,
    EXAMPLES_INTRO,
    MAX_OUTPUT_TOKENS,
    OUTPUT_RULES,
    ROLE,
    SCOPE_RULES,
    build_system_prompt,
    generate_estimation,
)

TRANSCRIPT = "The client wants an online booking portal for 12 locations."
ESTIMATE = "## Estimate: Booking Portal"


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch):
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


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
        fakes = [
            {
                "meeting_summary": "  Client needs a CRM.  \n",
                "estimation": "\n## Estimate: CRM\n",
            },
            {
                "meeting_summary": "Second",
                "estimation": "## Estimate: Second",
            },
        ]
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

    def test_formats_examples_with_xml_tags_and_stripped_content(self, fake_examples):
        """Format each example with 1-based id tag and stripped whitespace."""
        prompt = build_system_prompt()

        expected_block = (
            '<example id="1">\n'
            "<meeting_summary>\nClient needs a CRM.\n</meeting_summary>\n"
            "<estimation>\n## Estimate: CRM\n</estimation>\n"
            "</example>\n"
            '<example id="2">\n'
            "<meeting_summary>\nSecond\n</meeting_summary>\n"
            "<estimation>\n## Estimate: Second\n</estimation>\n"
            "</example>"
        )
        assert f"<examples>\n{expected_block}\n</examples>" in prompt


class TestGenerateEstimationWithOpenAI:
    @pytest.fixture
    def settings(self):
        return make_settings(llm_provider="openai", llm_model="gpt-4o-mini")

    @pytest.fixture
    def mock_openai(self, mocker):
        def install(output_text=ESTIMATE):
            mock_create = mocker.AsyncMock(
                return_value=types.SimpleNamespace(output_text=output_text)
            )
            fake_client = types.SimpleNamespace(
                responses=types.SimpleNamespace(create=mock_create)
            )
            factory = mocker.patch.object(
                llm_service, "_openai_client", return_value=fake_client
            )
            return types.SimpleNamespace(create=mock_create, factory=factory)

        return install

    @pytest.mark.anyio
    async def test_returns_response_output_text(self, mock_openai, settings):
        """Return the aggregated output text of the OpenAI response."""
        mock_openai()

        assert await generate_estimation(TRANSCRIPT, settings) == ESTIMATE

    @pytest.mark.anyio
    async def test_builds_client_with_openai_api_key(self, mock_openai, settings):
        """Build the OpenAI client with the configured OpenAI API key."""
        mocks = mock_openai()

        await generate_estimation(TRANSCRIPT, settings)

        mocks.factory.assert_called_once_with("sk-openai")

    @pytest.mark.anyio
    async def test_sends_system_prompt_as_instructions(self, mock_openai, settings):
        """Send the system prompt through the instructions parameter."""
        mocks = mock_openai()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["instructions"] == build_system_prompt()

    @pytest.mark.anyio
    async def test_sends_transcript_as_input(self, mock_openai, settings):
        """Send the transcript through the input parameter."""
        mocks = mock_openai()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["input"] == TRANSCRIPT

    @pytest.mark.anyio
    async def test_uses_configured_model(self, mock_openai, settings):
        """Request the model configured in settings."""
        mocks = mock_openai()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.anyio
    async def test_caps_output_tokens(self, mock_openai, settings):
        """Cap the response length at the shared output token limit."""
        mocks = mock_openai()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["max_output_tokens"] == MAX_OUTPUT_TOKENS


class TestGenerateEstimationWithAnthropic:
    @pytest.fixture
    def settings(self):
        return make_settings(llm_provider="anthropic", llm_model="claude-haiku-4-5")

    @pytest.fixture
    def mock_anthropic(self, mocker):
        def install(*blocks):
            blocks = blocks or (types.SimpleNamespace(type="text", text=ESTIMATE),)
            mock_create = mocker.AsyncMock(
                return_value=types.SimpleNamespace(content=list(blocks))
            )
            fake_client = types.SimpleNamespace(
                messages=types.SimpleNamespace(create=mock_create)
            )
            factory = mocker.patch.object(
                llm_service, "_anthropic_client", return_value=fake_client
            )
            return types.SimpleNamespace(create=mock_create, factory=factory)

        return install

    @pytest.mark.anyio
    async def test_returns_response_text(self, mock_anthropic, settings):
        """Return the text content of the Anthropic response."""
        mock_anthropic()

        assert await generate_estimation(TRANSCRIPT, settings) == ESTIMATE

    @pytest.mark.anyio
    async def test_builds_client_with_anthropic_api_key(self, mock_anthropic, settings):
        """Build the Anthropic client with the configured Anthropic API key."""
        mocks = mock_anthropic()

        await generate_estimation(TRANSCRIPT, settings)

        mocks.factory.assert_called_once_with("sk-anthropic")

    @pytest.mark.anyio
    async def test_sends_system_prompt_as_system(self, mock_anthropic, settings):
        """Send the system prompt through the system parameter."""
        mocks = mock_anthropic()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["system"] == build_system_prompt()

    @pytest.mark.anyio
    async def test_sends_transcript_as_user_message(self, mock_anthropic, settings):
        """Send the transcript as a single user message."""
        mocks = mock_anthropic()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["messages"] == [
            {"role": "user", "content": TRANSCRIPT}
        ]

    @pytest.mark.anyio
    async def test_uses_configured_model(self, mock_anthropic, settings):
        """Request the model configured in settings."""
        mocks = mock_anthropic()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["model"] == "claude-haiku-4-5"

    @pytest.mark.anyio
    async def test_caps_output_tokens(self, mock_anthropic, settings):
        """Cap the response length at the shared output token limit."""
        mocks = mock_anthropic()

        await generate_estimation(TRANSCRIPT, settings)

        assert mocks.create.call_args.kwargs["max_tokens"] == MAX_OUTPUT_TOKENS

    @pytest.mark.anyio
    async def test_joins_text_blocks_in_order(self, mock_anthropic, settings):
        """Join multiple text blocks in sequence to produce complete output."""
        mock_anthropic(
            types.SimpleNamespace(type="text", text="## Estimate: "),
            types.SimpleNamespace(type="text", text="Booking Portal"),
        )

        assert await generate_estimation(TRANSCRIPT, settings) == ESTIMATE

    @pytest.mark.anyio
    async def test_skips_non_text_blocks(self, mock_anthropic, settings):
        """Omit thinking and tool use blocks when extracting response text."""
        mock_anthropic(
            types.SimpleNamespace(type="thinking", thinking="weighing the scope"),
            types.SimpleNamespace(type="tool_use", name="calculator"),
            types.SimpleNamespace(type="text", text=ESTIMATE),
        )

        assert await generate_estimation(TRANSCRIPT, settings) == ESTIMATE


class TestGenerateEstimation:
    @pytest.fixture
    def branches(self, mocker):
        return types.SimpleNamespace(
            openai=mocker.patch.object(
                llm_service, "_estimate_with_openai", return_value=ESTIMATE
            ),
            anthropic=mocker.patch.object(
                llm_service, "_estimate_with_anthropic", return_value=ESTIMATE
            ),
        )

    @pytest.mark.anyio
    async def test_dispatches_to_anthropic_when_provider_is_anthropic(self, branches):
        """Route to the Anthropic branch when the configured provider is anthropic."""
        settings = make_settings(llm_provider="anthropic")

        await generate_estimation(TRANSCRIPT, settings)

        branches.anthropic.assert_awaited_once_with(TRANSCRIPT, settings)
        branches.openai.assert_not_awaited()

    @pytest.mark.anyio
    async def test_dispatches_to_openai_when_provider_is_openai(self, branches):
        """Route to the OpenAI branch when the configured provider is openai."""
        settings = make_settings(llm_provider="openai")

        await generate_estimation(TRANSCRIPT, settings)

        branches.openai.assert_awaited_once_with(TRANSCRIPT, settings)
        branches.anthropic.assert_not_awaited()

    @pytest.mark.anyio
    async def test_resolves_settings_when_omitted(self, mocker, branches):
        """Resolve settings through get_settings when no settings are supplied."""
        settings = make_settings()
        mocker.patch.object(llm_service, "get_settings", return_value=settings)

        await generate_estimation(TRANSCRIPT)

        branches.openai.assert_awaited_once_with(TRANSCRIPT, settings)
