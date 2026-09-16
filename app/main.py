from fastapi import FastAPI

from app.routers import estimations

app = FastAPI(title="Software Project Estimator", version="0.1.0")
app.include_router(estimations.router)
