from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_assessments: int
    total_recommendations: int
    average_overall_score: float
    average_llm_latency_ms: float
    total_estimated_llm_cost_usd: float
    recommendation_coverage_rate: float

