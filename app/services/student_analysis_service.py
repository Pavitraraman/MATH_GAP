import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm import LearningGapAnalysis
from app.schemas.analysis import StudentLLMAnalysis
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService


class StudentAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze_summary(self, summary: dict) -> StudentLLMAnalysis:
        prompt = await PromptService(self.db).get_prompt("student_performance_analysis", "v1")
        rendered_prompt = prompt.template.format(summary_json=json.dumps(summary, ensure_ascii=False))
        result = await LLMService(self.db).generate_structured(
            prompt=prompt,
            rendered_prompt=rendered_prompt,
            schema=StudentLLMAnalysis,
        )
        self.db.add(
            LearningGapAnalysis(
                student_id=str(summary.get("student_id")),
                prompt_name=prompt.name,
                prompt_version=prompt.version,
                model=settings.gemini_model,
                input_summary_json=summary,
                output_json=result.model_dump(),
            )
        )
        await self.db.commit()
        return result
