from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import auth, analysis, assessments, health, metrics, recommendations, student_analysis, prompt_logs, platform
from app.core.config import settings


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger = logging.getLogger("math_gap.startup")
    
    # Create all database tables on startup if they do not exist (useful for dev fallbacks)
    from app.db.base import Base
    import app.models
    from app.db import session as db_session
    from sqlalchemy.ext.asyncio import create_async_engine
    
    active_engine = db_session.engine
    active_backend = "PostgreSQL" if "postgresql" in str(active_engine.url) else "SQLite"
    
    try:
        # Try to connect and run create_all using the default database engine
        async with active_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print(f"🚀 Active Database Backend: {active_backend} (Connected successfully)")
        logger.info(f"Active Database Backend: {active_backend}")
    except Exception as exc:
        if active_backend == "PostgreSQL":
            print(f"⚠️ PostgreSQL connection failed: {exc}")
            print("🔄 Falling back to SQLite for local development mode...")
            logger.warning("PostgreSQL connection failed, switching to SQLite: %s", exc)
            
            # Switch to SQLite with aiosqlite driver
            sqlite_url = "sqlite+aiosqlite:///math_gap.db"
            sqlite_engine = create_async_engine(sqlite_url)
            
            # Reconfigure the global module variables in app.db.session
            db_session.engine = sqlite_engine
            db_session.SessionLocal.configure(bind=sqlite_engine)
            
            # Retry database table creation with the SQLite engine
            async with sqlite_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("🚀 Active Database Backend: SQLite (Fallback activated)")
            logger.info("Active Database Backend: SQLite (Fallback activated)")
        else:
            # If SQLite itself fails, raise the exception
            logger.error("SQLite database initialization failed: %s", exc)
            raise exc
        
    print("Registered FastAPI routes:")
    for route in app_instance.routes:
        methods = ",".join(sorted(getattr(route, "methods", None) or []))
        if not methods:
            methods = "WS"
        print(f"{methods} {route.path}")
        logger.info("%s %s", methods, route.path)
    yield
    # Dispose of the active engine (correctly closes SQLite or PostgreSQL)
    await db_session.engine.dispose()



from fastapi import FastAPI, Depends
from app.core.rate_limiter import rate_limiter

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    dependencies=[Depends(rate_limiter)],
)


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "Math Gap API Running"}


app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(student_analysis.router, tags=["student-analysis"])
app.include_router(prompt_logs.router, prefix="/prompts", tags=["prompts"])
app.include_router(platform.router, prefix="/platform", tags=["platform"])

