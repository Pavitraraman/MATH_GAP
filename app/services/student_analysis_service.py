import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analysis import StudentLLMAnalysis
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService


class StudentAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze_summary(self, summary: dict) -> StudentLLMAnalysis:
        prompt = await PromptService(self.db).get_prompt("student_performance_analysis", "v1")
        rendered_prompt = prompt.template.format(summary_json=json.dumps(summary, ensure_ascii=False))
        return await LLMService(self.db).generate_structured(
            prompt=prompt,
            rendered_prompt=rendered_prompt,
            schema=StudentLLMAnalysis,
        )

