from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, StringConstraints

from app.config import Settings, get_settings
from app.services.llm_service import generate_estimation


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
    estimation = await generate_estimation(body.transcription, settings)
    return EstimateResponse(
        estimation=estimation,
        model=settings.llm_model,
        provider=settings.llm_provider,
    )
