from anthropic import APIError as AnthropicApiError
from anthropic import AsyncAnthropic
from openai import APIError as OpenAIApiError
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.context.examples import ESTIMATION_EXAMPLES
from app.domain.estimate import EstimateDraft, EstimationError

MAX_OUTPUT_TOKENS = 4096

ROLE = (
    "You are a senior software estimator at a consultancy. You turn client "
    "meeting transcripts into professional project estimates that follow the "
    "house style shown in the examples."
)

ESTIMATION_RULES = """\
<estimation_rules>
- Estimate effort in hours only.
- If the transcript states an agreed hourly rate, extract its amount and
  ISO 4217 currency code into `rate`. Otherwise set `rate` to null.
- Never state monetary amounts, rates, or currency in any narrative field.
- Break the work into 5-10 tasks. Give each task Optimistic, Likely and
  Pessimistic hours, with Optimistic < Likely < Pessimistic.
- Summarize the meeting requirements in meeting_summary before estimating.
- Propose a realistic team structure and duration range.
- Do not compute totals, PERT values, subtotals, contingency, or ranges in any
  narrative field; provide only raw estimates.
</estimation_rules>"""

SCOPE_RULES = """\
<scope_rules>
- Estimate only what the transcript asks for. Never invent features.
- Anything the transcript leaves unspecified but the estimate depends on goes under
  Assumptions.
- Anything the client explicitly declines or defers goes under Out of scope.
- Unknowns that could move the numbers go under Risks with an impact level (low, medium,
  high). Larger unknowns lower Confidence and widen the pessimistic hours.
- If the transcript is too thin to estimate responsibly, still produce the estimate, set
  Confidence to Low and list the missing information under Assumptions.
</scope_rules>"""

OUTPUT_RULES = """\
<output_rules>
- Reply with a structured JSON object adhering strictly to the schema.
- Reply in English only.
</output_rules>"""

EXAMPLES_INTRO = (
    "Each example pairs a condensed meeting summary with the estimate we "
    "delivered. New requests arrive as raw transcripts: extract the "
    "requirements first, then estimate."
)


def _format_example(index: int, draft: EstimateDraft) -> str:
    json_content = draft.model_dump_json(indent=2)
    return (
        f'<example id="{index}">\n'
        f"<meeting_summary>\n{draft.meeting_summary.strip()}\n</meeting_summary>\n"
        f"<estimation_json>\n{json_content}\n</estimation_json>\n"
        "</example>"
    )


def build_system_prompt() -> str:
    examples = "\n".join(
        _format_example(index, draft)
        for index, draft in enumerate(ESTIMATION_EXAMPLES, start=1)
    )
    return (
        f"{ROLE}\n\n"
        f"{ESTIMATION_RULES}\n\n"
        f"{SCOPE_RULES}\n\n"
        f"{EXAMPLES_INTRO}\n"
        "<examples>\n"
        f"{examples}\n"
        "</examples>\n\n"
        f"{OUTPUT_RULES}"
    )


def _openai_client(api_key: str | None) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=api_key)


def _anthropic_client(api_key: str | None) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=api_key)


async def _estimate_with_openai(transcript: str, settings: Settings) -> EstimateDraft:
    client = _openai_client(settings.openai_api_key)
    try:
        response = await client.responses.parse(
            model=settings.llm_model,
            instructions=build_system_prompt(),
            input=transcript,
            text_format=EstimateDraft,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    except (OpenAIApiError, ValidationError) as e:
        raise EstimationError(f"OpenAI estimation failed: {e}") from e
    if response.output_parsed is None:
        raise EstimationError("OpenAI failed to produce a structured estimate")
    return response.output_parsed


async def _estimate_with_anthropic(
    transcript: str, settings: Settings
) -> EstimateDraft:
    client = _anthropic_client(settings.anthropic_api_key)
    try:
        response = await client.messages.parse(
            model=settings.llm_model,
            system=build_system_prompt(),
            messages=[{"role": "user", "content": transcript}],
            output_format=EstimateDraft,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
    except (AnthropicApiError, ValidationError) as e:
        raise EstimationError(f"Anthropic estimation failed: {e}") from e
    if response.parsed_output is None:
        raise EstimationError("Anthropic failed to produce a structured estimate")
    return response.parsed_output


async def generate_estimate_draft(
    transcript: str, settings: Settings | None = None
) -> EstimateDraft:
    if settings is None:
        settings = get_settings()
    if settings.llm_provider == "anthropic":
        draft = await _estimate_with_anthropic(transcript, settings)
    else:
        draft = await _estimate_with_openai(transcript, settings)
    if not draft.tasks:
        raise EstimationError("Estimate contains no tasks")
    if draft.rate is not None and draft.rate.amount <= 0:
        raise EstimationError("Hourly rate amount must be positive")
    return draft
