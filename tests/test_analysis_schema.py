from app.schemas.analysis import StudentLLMAnalysis


def test_learning_gap_analysis_schema() -> None:
    payload = StudentLLMAnalysis.model_validate(
        {
            "weak_concepts": [{"topic": "Fractions", "confidence": 0.91}],
            "recommended_difficulty_progression": ["foundational", "guided", "independent"],
            "suggested_practice_strategy": ["Review fraction equivalence", "Practice mixed-number conversion"],
        }
    )
    assert payload.weak_concepts[0].topic == "Fractions"
