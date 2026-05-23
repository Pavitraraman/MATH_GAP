import json
import asyncio
from time import perf_counter

from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import LLMProviderError
from app.core.logging import get_logger
from app.models.llm import LLMCallLog, PromptVersion
from pydantic import BaseModel

from app.schemas.recommendation import RecommendationPlan

logger = get_logger(__name__)


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
                status = "fallback"
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
            if not response.text:
                raise LLMProviderError("Gemini returned an empty response body.")
            response_payload = json.loads(response.text)
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            return RecommendationPlan.model_validate(response_payload)
        except (json.JSONDecodeError, ValueError) as exc:
            status = "invalid_response"
            response_payload = {"error": str(exc)}
            logger.exception("Gemini returned invalid structured output.")
            raise LLMProviderError("Gemini returned invalid structured JSON.") from exc
        except LLMProviderError:
            status = "error"
            logger.exception("Gemini provider error.")
            raise
        except Exception as exc:
            status = "error"
            response_payload = {"error": str(exc)}
            logger.exception("Gemini request failed.")
            raise LLMProviderError("Gemini request failed.") from exc
        finally:
            latency_ms = (perf_counter() - started) * 1000
            estimated_cost = (
                (input_tokens / 1000) * settings.input_cost_per_1k_tokens_usd
                + (output_tokens / 1000) * settings.output_cost_per_1k_tokens_usd
            )
            self._log_call_details(
                prompt=prompt,
                rendered_prompt=rendered_prompt,
                response_payload=response_payload,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=estimated_cost,
                status=status,
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


    async def generate_structured(
        self,
        *,
        prompt: PromptVersion,
        rendered_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        last_error: Exception | None = None
        for attempt in range(settings.llm_max_retries + 1):
            try:
                return await self._generate_structured_once(
                    prompt=prompt,
                    rendered_prompt=rendered_prompt,
                    schema=schema,
                )
            except LLMProviderError as exc:
                last_error = exc
                if attempt >= settings.llm_max_retries:
                    raise
                delay = settings.llm_retry_base_delay_seconds * (2**attempt)
                logger.warning("Retrying Gemini structured call after failure (attempt %s).", attempt + 1)
                await asyncio.sleep(delay)
        raise LLMProviderError("Gemini request failed after retries.") from last_error

    async def _generate_structured_once(
        self,
        *,
        prompt: PromptVersion,
        rendered_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        started = perf_counter()
        status = "success"
        response_payload: dict = {}
        input_tokens = 0
        output_tokens = 0
        try:
            if self.client is None:
                raise LLMProviderError("Gemini API key is not configured.")
            response = await self.client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=rendered_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=schema.model_json_schema(),
                ),
            )
            if not response.text:
                raise LLMProviderError("Gemini returned an empty response body.")
            response_payload = json.loads(response.text)
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            return schema.model_validate(response_payload)
        except (json.JSONDecodeError, ValueError) as exc:
            status = "invalid_response"
            response_payload = {"error": str(exc)}
            logger.exception("Gemini returned invalid structured output.")
            raise LLMProviderError("Gemini returned invalid structured JSON.") from exc
        except LLMProviderError:
            status = "error"
            logger.exception("Gemini provider error.")
            raise
        except Exception as exc:
            status = "error"
            response_payload = {"error": str(exc)}
            logger.exception("Gemini request failed.")
            raise LLMProviderError("Gemini request failed.") from exc
        finally:
            latency_ms = (perf_counter() - started) * 1000
            estimated_cost = (
                (input_tokens / 1000) * settings.input_cost_per_1k_tokens_usd
                + (output_tokens / 1000) * settings.output_cost_per_1k_tokens_usd
            )
            self._log_call_details(
                prompt=prompt,
                rendered_prompt=rendered_prompt,
                response_payload=response_payload,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=estimated_cost,
                status=status,
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

    def _log_call_details(
        self,
        *,
        prompt: PromptVersion,
        rendered_prompt: str,
        response_payload: dict,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        estimated_cost: float,
        status: str,
    ) -> None:
        # 1. Print to terminal for debugging
        print("\n" + "="*80)
        print(f"🤖 DEBUG: Gemini Response | Prompt: {prompt.name} ({prompt.version}) | Status: {status}")
        print(f"Latency: {latency_ms:.2f}ms | Tokens: {input_tokens} in / {output_tokens} out | Cost: ${estimated_cost:.6f}")
        print("-"*80)
        print(json.dumps(response_payload, indent=2, ensure_ascii=False))
        print("="*80 + "\n")

        # 2. Write to logs/ directory file
        try:
            from datetime import datetime
            from pathlib import Path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "gemini_calls.jsonl"
            
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "prompt_name": prompt.name,
                "prompt_version": prompt.version,
                "prompt": rendered_prompt,
                "response": response_payload,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": estimated_cost,
                "status": status
            }
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error("Failed to write LLM log to logs/ directory: %s", exc)

