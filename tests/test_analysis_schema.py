from app.schemas.analysis import StudentLLMAnalysis


def test_learning_gap_analysis_schema() -> None:
    payload = StudentLLMAnalysis.model_validate(
        {
            "weak_concepts": [
                {
                    "concept_name": "Fractions",
                    "reasoning": "Student consistently misses fraction additions.",
                    "confidence_score": 0.91,
                }
            ],
            "recommended_learning_strategy": "Review visual fraction modeling first.",
            "personalized_practice_recommendations": [
                "Practice adding simple fractions with like denominators",
                "Practice mixed number subtraction with renaming",
            ],
        }
    )
    assert payload.weak_concepts[0].concept_name == "Fractions"

