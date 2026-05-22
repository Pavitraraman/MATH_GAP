from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import analysis, assessments, health, metrics, recommendations
from app.core.config import settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger = logging.getLogger("math_gap.startup")
    print("Registered FastAPI routes:")
    for route in app_instance.routes:
        methods = ",".join(sorted(route.methods or []))
        print(f"{methods} {route.path}")
        logger.info("%s %s", methods, route.path)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "Math Gap API Running"}


app.include_router(health.router, tags=["health"])
app.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
