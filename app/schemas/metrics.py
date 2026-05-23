from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_assessments: int
    total_recommendations: int
    average_overall_score: float
    average_llm_latency_ms: float
    total_estimated_llm_cost_usd: float
    recommendation_coverage_rate: float


class LLMCallLogRead(BaseModel):
    id: int
    model: str
    prompt_name: str
    prompt_version: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    status: str
    request_json: dict
    response_json: dict

    model_config = {"from_attributes": True}


class EvaluationMetrics(BaseModel):
    recommendation_relevance: float
    improvement_rate: float
    hallucination_rate: float
    average_latency_ms: float
    cost_per_session: float
    output_consistency: float

