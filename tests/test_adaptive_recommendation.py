import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.schemas.recommendation import AdaptiveRecommendationResponse, AdaptiveRecommendationItem, RecommendedQuestion
from data_pipeline.schemas import StandardizedAttempt

client = TestClient(app)


def test_adaptive_recommendation_schemas() -> None:
    # 1. Test schema validation for recommended items
    rec_q = RecommendedQuestion(
        problem_id="p_99",
        skill="Algebra",
        grade_level=8,
        difficulty="medium",
        empirical_accuracy=0.67
    )
    
    item = AdaptiveRecommendationItem(
        concept_name="Algebra",
        recommended_questions=[rec_q],
        difficulty="medium",
        reasoning="Recommended algebra medium difficulty based on diagnosed algebraic learning gaps.",
        topic_relevance_score=0.8875
    )
    
    response = AdaptiveRecommendationResponse(
        student_id="student_1",
        personalized_learning_strategy="Focus on algebra fundamentals first.",
        recommendations=[item]
    )
    
    assert response.student_id == "student_1"
    assert len(response.recommendations) == 1
    assert response.recommendations[0].concept_name == "Algebra"
    assert response.recommendations[0].topic_relevance_score == 0.8875


@patch("app.api.routes.recommendations.RecommendationService")
def test_get_student_recommendations_endpoint(mock_service_class) -> None:
    # Arrange
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance
    
    rec_response = AdaptiveRecommendationResponse(
        student_id="student_123",
        personalized_learning_strategy=" Pedagogical strategy goes here.",
        recommendations=[
            AdaptiveRecommendationItem(
                concept_name="Fractions Addition",
                recommended_questions=[
                    RecommendedQuestion(
                        problem_id="p_1",
                        skill="Fractions Addition",
                        grade_level=8,
                        difficulty="easy",
                        empirical_accuracy=0.45
                    )
                ],
                difficulty="easy",
                reasoning="Adapted target difficulty to easy due to low historical speed.",
                topic_relevance_score=0.92
            )
        ]
    )
    mock_service_instance.get_adaptive_recommendations = AsyncMock(return_value=rec_response)

    # Act
    response = client.get("/recommendations/student_123?weak_threshold=0.7&min_attempts=3")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "student_123"
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["concept_name"] == "Fractions Addition"
    assert data["recommendations"][0]["topic_relevance_score"] == 0.92
    
    # Ensure correct arguments were forwarded to the service
    mock_service_instance.get_adaptive_recommendations.assert_called_once_with(
        student_id="student_123",
        weak_threshold=0.7,
        min_attempts=3
    )


@patch("app.api.routes.recommendations.RecommendationService")
def test_get_student_recommendations_not_found(mock_service_class) -> None:
    # Arrange
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance
    mock_service_instance.get_adaptive_recommendations = AsyncMock(side_effect=ValueError("Student attempts log is empty."))

    # Act
    response = client.get("/recommendations/unknown_student")

    # Assert
    assert response.status_code == 404
    assert "Student attempts log is empty" in response.json()["detail"]


@patch("app.services.recommendation_service.Path.exists")
@patch("app.services.recommendation_service.json.load")
@patch("app.services.recommendation_service.select")
@pytest.mark.asyncio
async def test_scoring_and_adaptation_logic(mock_select, mock_json_load, mock_path_exists) -> None:
    # Arrange
    from app.services.recommendation_service import RecommendationService
    
    mock_db = AsyncMock()
    
    # Mock database to return a mock LearningGapAnalysis
    mock_analysis_record = MagicMock()
    mock_analysis_record.output_json = {
        "personalized_learning_strategy": "Master equations.",
        "weak_concepts": [
            {
                "concept_name": "Equations",
                "recommended_difficulty_progression": "medium",
                "confidence_score": 0.90
            }
        ]
    }
    mock_db.scalar.return_value = mock_analysis_record
    
    # Mock Question Index JSON cache
    mock_path_exists.return_value = True
    mock_json_load.return_value = {
        "Equations": [
            {"problem_id": "eq_1", "difficulty": "easy", "empirical_accuracy": 0.40},
            {"problem_id": "eq_2", "difficulty": "medium", "empirical_accuracy": 0.60},
            {"problem_id": "eq_3", "difficulty": "hard", "empirical_accuracy": 0.85}
        ]
    }

    # Setup the student attempts to reflect slow response speed
    # Average response speed > 25 seconds should trigger difficulty downgrade (medium -> easy)
    student_attempts = [
        StandardizedAttempt(student_id="student_slow", skill="Equations", correct=0, attempt_time=30, problem_id="eq_1"),
        StandardizedAttempt(student_id="student_slow", skill="Equations", correct=0, attempt_time=28, problem_id="eq_2")
    ]
    
    service = RecommendationService(mock_db)
    
    # Inject our mock loaded attempts directly using patch
    with patch("app.services.recommendation_service.json.load") as mock_attempts_load:
        mock_attempts_load.side_effect = [
            {"student_slow": [att.model_dump() for att in student_attempts]}, # Student attempts index
            mock_json_load.return_value                                       # Question index
        ]
        
        # Act
        result = await service.get_adaptive_recommendations(
            student_id="student_slow",
            weak_threshold=0.7,
            min_attempts=2
        )
        
        # Assert
        assert result.student_id == "student_slow"
        assert len(result.recommendations) == 1
        rec_item = result.recommendations[0]
        assert rec_item.concept_name == "Equations"
        
        # Target difficulty must be adapted (downgraded to "easy" due to response speed > 25s)
        assert rec_item.difficulty == "easy"
        assert "slow response speed" in rec_item.reasoning
        
        # Since target difficulty was adapted to "easy", eq_1 (easy) must have a higher score
        # and be ranked first. Let's inspect recommended questions.
        assert len(rec_item.recommended_questions) > 0
        assert rec_item.recommended_questions[0].problem_id == "eq_1"
        assert rec_item.recommended_questions[0].difficulty == "easy"
