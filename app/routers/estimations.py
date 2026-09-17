from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints

from app.config import Settings, get_settings
from app.domain.estimate import EstimationError
from app.services.estimate_formatter import render_markdown
from app.services.llm_service import generate_estimate_draft


class EstimateRequest(BaseModel):
    transcription: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]


class EstimateResponse(BaseModel):
    estimation: str
    model: str
    provider: Literal["openai", "anthropic"]


router = APIRouter(tags=["estimations"])


@router.post("/estimate")
async def estimate(
    body: EstimateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> EstimateResponse:
    try:
        draft = await generate_estimate_draft(body.transcription, settings)
    except EstimationError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return EstimateResponse(
        estimation=render_markdown(draft),
        model=settings.llm_model,
        provider=settings.llm_provider,
    )
