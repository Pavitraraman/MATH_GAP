import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.learning_plan import StudentLearningPlan, ConceptLearningGap, GenerateLearningPlanRequest

client = TestClient(app)


def test_learning_plan_schemas() -> None:
    # 1. Test ConceptLearningGap schema
    gap = ConceptLearningGap.model_validate({
        "concept_name": "Fractions Addition",
        "reasoning": "Student struggled with common denominators.",
        "recommended_difficulty_progression": "easy -> medium",
        "recommended_question_types": ["Adding fractions with like denominators", "Finding common multiples"],
        "confidence_score": 0.95
    })
    assert gap.concept_name == "Fractions Addition"
    assert gap.confidence_score == 0.95

    # 2. Test StudentLearningPlan schema
    plan = StudentLearningPlan.model_validate({
        "student_id": "student_123",
        "weak_concepts": [gap.model_dump()],
        "personalized_learning_strategy": "First, focus on visual fraction circles."
    })
    assert plan.student_id == "student_123"
    assert len(plan.weak_concepts) == 1
    assert plan.weak_concepts[0].concept_name == "Fractions Addition"


@patch("app.api.routes.student_analysis.LearningPlanService")
def test_generate_learning_plan_endpoint(mock_service_class) -> None:
    # Arrange
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance
    
    mock_plan = StudentLearningPlan(
        student_id="student_456",
        weak_concepts=[
            ConceptLearningGap(
                concept_name="Geometry Angles",
                reasoning="Struggles to identify acute vs obtuse angles.",
                recommended_difficulty_progression="easy",
                recommended_question_types=["Identify acute angles in diagrams"],
                confidence_score=0.88,
            )
        ],
        personalized_learning_strategy="Focus on identifying simple angles visually."
    )
    
    # generate_learning_plan is an async method
    mock_service_instance.generate_learning_plan = AsyncMock(return_value=mock_plan)

    payload = {
        "student_id": "student_456",
        "weak_threshold": 0.65,
        "min_attempts": 2
    }

    # Act
    response = client.post("/generate-learning-plan", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "student_456"
    assert len(data["weak_concepts"]) == 1
    assert data["weak_concepts"][0]["concept_name"] == "Geometry Angles"
    assert data["weak_concepts"][0]["confidence_score"] == 0.88
    assert data["personalized_learning_strategy"] == "Focus on identifying simple angles visually."
    
    # Ensure correct args were passed to the service
    mock_service_instance.generate_learning_plan.assert_called_once_with(
        student_id="student_456",
        weak_threshold=0.65,
        min_attempts=2
    )


@patch("app.api.routes.student_analysis.LearningPlanService")
def test_generate_learning_plan_llm_error(mock_service_class) -> None:
    # Arrange
    from app.core.exceptions import LLMProviderError
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance
    mock_service_instance.generate_learning_plan = AsyncMock(side_effect=LLMProviderError("Gemini API connection timed out."))

    payload = {
        "student_id": "student_err"
    }

    # Act
    response = client.post("/generate-learning-plan", json=payload)

    # Assert
    assert response.status_code == 502
    assert "Gemini API connection timed out" in response.json()["detail"]


@patch("app.api.routes.student_analysis.LearningPlanService")
def test_generate_learning_plan_general_error(mock_service_class) -> None:
    # Arrange
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance
    mock_service_instance.generate_learning_plan = AsyncMock(side_effect=ValueError("Unexpected file reading failure."))

    payload = {
        "student_id": "student_err"
    }

    # Act
    response = client.post("/generate-learning-plan", json=payload)

    # Assert
    assert response.status_code == 500
    assert "Unexpected file reading failure" in response.json()["detail"]
