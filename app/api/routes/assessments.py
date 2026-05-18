from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.assessment import AssessmentCreate, AssessmentRead
from app.services.assessment_service import AssessmentService

router = APIRouter()


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def ingest_assessment(
    payload: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
) -> AssessmentRead:
    return await AssessmentService(db).create_assessment(payload)

