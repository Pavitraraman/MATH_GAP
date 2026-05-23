from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.llm import PromptVersion, LLMCallLog
from app.schemas.metrics import LLMCallLogRead
from pydantic import BaseModel

router = APIRouter()

class PromptVersionInfo(BaseModel):
    name: str
    version: str
    template: str

@router.get("", response_model=list[dict])
async def list_available_prompts() -> list[dict]:
    """Scan the prompts directory and list all available prompts and versions."""
    prompts_dir = Path("prompts")
    if not prompts_dir.exists():
        return []
    
    results = []
    for prompt_path in prompts_dir.iterdir():
        if prompt_path.is_dir():
            prompt_name = prompt_path.name
            versions = []
            for file_path in prompt_path.glob("*.txt"):
                versions.append(file_path.stem)
            results.append({
                "name": prompt_name,
                "versions": sorted(versions)
            })
    return results

@router.get("/{name}/{version}", response_model=PromptVersionInfo)
async def get_prompt_version(name: str, version: str) -> PromptVersionInfo:
    """Fetch the template text for a specific prompt version."""
    template_path = Path("prompts") / name / f"{version}.txt"
    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt version {name}/{version} not found on disk."
        )
    try:
        template = template_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read prompt template: {exc}"
        )
    return PromptVersionInfo(name=name, version=version, template=template)

@router.get("/logs", response_model=list[LLMCallLogRead])
async def get_prompt_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> list[LLMCallLogRead]:
    """Fetch recent LLM call logs to track latency, token usage, cost, and outputs."""
    stmt = select(LLMCallLog).order_by(LLMCallLog.created_at.desc()).limit(limit)
    result = await db.scalars(stmt)
    return [LLMCallLogRead.model_validate(item) for item in result.all()]
