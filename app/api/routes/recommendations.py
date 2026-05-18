from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.recommendation import RecommendationRead
from app.services.recommendation_service import RecommendationService

router = APIRouter()


@router.post("/{assessment_id}", response_model=RecommendationRead)
async def create_recommendation(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
) -> RecommendationRead:
    result = await RecommendationService(db).generate_for_assessment(assessment_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )
    return result

