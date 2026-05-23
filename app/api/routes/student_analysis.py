from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import LLMProviderError, StudentNotFoundError
from app.schemas.learning_plan import GenerateLearningPlanRequest, StudentLearningPlan
from app.schemas.student_analysis import AnalyzeStudentRequest, AnalyzeStudentResponse
from app.services.learning_plan_service import LearningPlanService
from data_pipeline.student_analysis import analyze_student_dataset

router = APIRouter()


@router.post("/analyze-student", response_model=AnalyzeStudentResponse)
async def analyze_student(payload: AnalyzeStudentRequest) -> AnalyzeStudentResponse:
    dataset_path = Path(payload.dataset_path)
    if not dataset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {payload.dataset_path}",
        )

    result = analyze_student_dataset(
        dataset_path=dataset_path,
        student_id=payload.student_id,
        weak_threshold=payload.weak_threshold,
        min_attempts=payload.min_attempts,
    )
    return AnalyzeStudentResponse.model_validate(result)


@router.post("/generate-learning-plan", response_model=StudentLearningPlan)
async def generate_learning_plan(
    payload: GenerateLearningPlanRequest,
    db: AsyncSession = Depends(get_db),
) -> StudentLearningPlan:
    try:
        service = LearningPlanService(db)
        return await service.generate_learning_plan(
            student_id=payload.student_id,
            weak_threshold=payload.weak_threshold,
            min_attempts=payload.min_attempts,
        )
    except StudentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the learning plan: {exc}",
        ) from exc

