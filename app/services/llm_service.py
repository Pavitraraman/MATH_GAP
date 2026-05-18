import json
from time import perf_counter

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm import LLMCallLog, PromptVersion
from app.schemas.recommendation import RecommendationPlan


class LLMService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    async def generate_plan(
        self,
        *,
        prompt: PromptVersion,
        rendered_prompt: str,
        fallback_plan: RecommendationPlan,
    ) -> RecommendationPlan:
        started = perf_counter()
        status = "success"
        response_payload: dict = {}
        input_tokens = 0
        output_tokens = 0

        try:
            if self.client is None:
                response_payload = fallback_plan.model_dump()
                return fallback_plan

            response = await self.client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=rendered_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=RecommendationPlan.model_json_schema(),
                ),
            )
            response_payload = json.loads(response.text)
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            return RecommendationPlan.model_validate(response_payload)
        except Exception as exc:
            status = "error"
            response_payload = {"error": str(exc)}
            raise
        finally:
            latency_ms = (perf_counter() - started) * 1000
            estimated_cost = (
                (input_tokens / 1000) * settings.input_cost_per_1k_tokens_usd
                + (output_tokens / 1000) * settings.output_cost_per_1k_tokens_usd
            )
            self.db.add(
                LLMCallLog(
                    model=settings.gemini_model,
                    prompt_name=prompt.name,
                    prompt_version=prompt.version,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=estimated_cost,
                    status=status,
                    request_json={"prompt": rendered_prompt},
                    response_json=response_payload,
                )
            )
            await self.db.commit()

