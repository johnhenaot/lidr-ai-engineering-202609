from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import Settings, get_settings
from app.context.examples import ESTIMATION_EXAMPLES

MAX_OUTPUT_TOKENS = 4096

ROLE = (
    "You are a senior software estimator at a consultancy. You turn client "
    "meeting transcripts into professional project estimates that follow the "
    "house style shown in the examples."
)

ESTIMATION_RULES = """\
<estimation_rules>
- Estimate effort in hours. Never quote money unless the transcript states
  an hourly rate.
- Break the work into 5-10 tasks. Give each task Optimistic, Likely and
  Pessimistic hours, with Optimistic < Likely < Pessimistic.
- PERT per task = round((Optimistic + 4 * Likely + Pessimistic) / 6).
- PERT subtotal = sum of the PERT column.
- Contingency = 20% of the PERT subtotal when confidence is high, up to 25%
  when confidence is low, rounded to the nearest hour.
- Total estimate = PERT subtotal + Contingency.
- Likely range = PERT subtotal to the sum of the Pessimistic column.
- Re-add every column and total before answering; all numbers must be arithmetically
  consistent.
</estimation_rules>"""

SCOPE_RULES = """\
<scope_rules>
- Estimate only what the transcript asks for. Never invent features.
- Anything the transcript leaves unspecified but the estimate depends on goes under
  Assumptions.
- Anything the client explicitly declines or defers goes under Out of scope.
- Unknowns that could move the numbers go under Risks with an impact level (low, medium,
  high). Larger unknowns lower Confidence, widen the ranges and raise Contingency.
- If the transcript is too thin to estimate responsibly, still produce the estimate, set
  Confidence to Low and list the missing information under Assumptions.
</scope_rules>"""

OUTPUT_RULES = """\
<output_rules>
- Reply in English, Markdown only, using exactly the section order of the examples:
  "## Estimate:" title, Assumptions, Out of scope, Task breakdown table, totals block,
  Recommended team, Estimated duration, Risks, Confidence.
- End the Confidence section with "Estimate valid for N days."
- Start directly with the "## Estimate:" title. No preamble and no closing remarks.
</output_rules>"""

EXAMPLES_INTRO = (
    "Each example pairs a condensed meeting summary with the estimate we "
    "delivered. New requests arrive as raw transcripts: extract the "
    "requirements first, then estimate."
)


def _format_example(index: int, example: dict[str, str]) -> str:
    return (
        f'<example id="{index}">\n'
        f"<meeting_summary>\n{example['meeting_summary'].strip()}\n</meeting_summary>\n"
        f"<estimation>\n{example['estimation'].strip()}\n</estimation>\n"
        "</example>"
    )


def build_system_prompt() -> str:
    examples = "\n".join(
        _format_example(index, example)
        for index, example in enumerate(ESTIMATION_EXAMPLES, start=1)
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


async def _estimate_with_openai(transcript: str, settings: Settings) -> str:
    client = _openai_client(settings.openai_api_key)
    response = await client.responses.create(
        model=settings.llm_model,
        instructions=build_system_prompt(),
        input=transcript,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    return response.output_text


async def _estimate_with_anthropic(transcript: str, settings: Settings) -> str:
    client = _anthropic_client(settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.llm_model,
        system=build_system_prompt(),
        messages=[{"role": "user", "content": transcript}],
        max_tokens=MAX_OUTPUT_TOKENS,
    )
    return "".join(block.text for block in response.content if block.type == "text")


async def generate_estimation(transcript: str, settings: Settings | None = None) -> str:
    if settings is None:
        settings = get_settings()
    if settings.llm_provider == "anthropic":
        return await _estimate_with_anthropic(transcript, settings)
    return await _estimate_with_openai(transcript, settings)
