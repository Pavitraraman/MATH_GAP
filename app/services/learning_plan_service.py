import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import StudentNotFoundError
from app.models.llm import LearningGapAnalysis
from app.schemas.learning_plan import StudentLearningPlan
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from data_pipeline.schemas import StandardizedAttempt
from recommendation_engine.performance import summarize_student_performance

logger = logging.getLogger("math_gap.learning_plan_service")

class LearningPlanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_learning_plan(
        self,
        student_id: str,
        weak_threshold: float = 0.7,
        min_attempts: int = 3,
    ) -> StudentLearningPlan:
        student_id = str(student_id)
        
        # 1. Load student attempts (try cached index first, then fall back to CSV)
        attempts = []
        index_path = Path("data/processed/student_attempts_index.json")
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as f:
                    cached_index = json.load(f)
                    student_attempts_raw = cached_index.get(student_id)
                    if student_attempts_raw:
                        attempts = [StandardizedAttempt(**item) for item in student_attempts_raw]
                        logger.info("Loaded %d attempts for student %s from cached index", len(attempts), student_id)
            except Exception as exc:
                logger.warning("Failed to read from cached student attempts index: %s", exc)

        if not attempts:
            logger.info("Attempting to load attempts from CSV/JSONL for student %s", student_id)
            from data_pipeline.student_analysis import load_student_attempts
            # Look up dataset in root
            csv_path = Path("students dataset.csv")
            jsonl_path = Path("data/processed/student_attempts.jsonl")
            target_path = csv_path if csv_path.exists() else jsonl_path
            
            if target_path.exists():
                attempts = load_student_attempts(target_path, student_id)
                logger.info("Loaded %d attempts from file %s", len(attempts), target_path)

        if not attempts:
            raise StudentNotFoundError(f"Student ID '{student_id}' has no attempts recorded or does not exist.")


        # 2. Summarize student performance
        summary = summarize_student_performance(
            attempts,
            weak_threshold=weak_threshold,
            min_attempts=min_attempts,
        )

        # 3. Retrieve and render prompt
        prompt_service = PromptService(self.db)
        prompt = await prompt_service.get_prompt("student_learning_plan", "v1")
        rendered_prompt = prompt.template.format(summary_json=json.dumps(summary, ensure_ascii=False))

        # 4. Invoke LLM with retries, validation, and logging
        llm_service = LLMService(self.db)
        result = await llm_service.generate_structured(
            prompt=prompt,
            rendered_prompt=rendered_prompt,
            schema=StudentLearningPlan,
        )

        # 5. Save the analysis to database
        self.db.add(
            LearningGapAnalysis(
                student_id=student_id,
                prompt_name=prompt.name,
                prompt_version=prompt.version,
                model=settings.gemini_model,
                input_summary_json=summary,
                output_json=result.model_dump(),
            )
        )
        await self.db.commit()

        return result
