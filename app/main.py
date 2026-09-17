from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import get_settings
from app.routers import estimations


class HealthResponse(BaseModel):
    status: Literal["ok"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_settings()
    yield


app = FastAPI(
    title="Software Project Estimator",
    description=(
        "Generates software project estimates from meeting transcripts using "
        "cache-augmented generation with historical estimation examples."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(estimations.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
