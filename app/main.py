from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.routers import estimations


class HealthResponse(BaseModel):
    status: Literal["ok"]


app = FastAPI(
    title="Software Project Estimator",
    description=(
        "Generates software project estimates from meeting transcripts using "
        "cache-augmented generation with historical estimation examples."
    ),
    version="0.1.0",
)

app.include_router(estimations.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
