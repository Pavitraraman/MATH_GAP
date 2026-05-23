import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from data_pipeline.schemas import StandardizedAttempt
from recommendation_engine.performance import summarize_student_performance
from app.services.recommendation_service import RecommendationService
from app.models.llm import LearningGapAnalysis

@pytest.fixture
def loaded_attempts():
    path = Path("data/processed/student_attempts_index.json")
    assert path.exists(), "Demo students attempts index does not exist. Run scripts/create_demo_students.py first."
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def question_index():
    path = Path("data/processed/question_index.json")
    assert path.exists(), "Question index does not exist."
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def test_demo_weak_algebra_performance(loaded_attempts) -> None:
    # Arrange
    raw_attempts = loaded_attempts.get("demo_weak_algebra", [])
    attempts = [StandardizedAttempt(**item) for item in raw_attempts]
    
    # Act
    summary = summarize_student_performance(attempts, weak_threshold=0.70, min_attempts=3)
    
    # Assert
    assert summary["student_id"] == "demo_weak_algebra"
    assert summary["total_attempts"] == 30
    
    weak_skills = [w["skill"] for w in summary["weak_topics"]]
    assert "Interpreting Linear Equations" in weak_skills
    assert "Application: Compare Expressions" in weak_skills
    assert "Properties Of Geometric Figures" not in weak_skills
    
    # Algebra accuracy is low (~30%), geometry is high (~90%)
    for t in summary["topics"]:
        if t["skill"] == "Interpreting Linear Equations":
            assert t["accuracy"] == 0.30
            assert t["is_weak"] is True
        elif t["skill"] == "Properties Of Geometric Figures":
            assert t["accuracy"] == 0.90
            assert t["is_weak"] is False

def test_demo_advanced_geometry_performance(loaded_attempts) -> None:
    # Arrange
    raw_attempts = loaded_attempts.get("demo_advanced_geometry", [])
    attempts = [StandardizedAttempt(**item) for item in raw_attempts]
    
    # Act
    summary = summarize_student_performance(attempts, weak_threshold=0.70, min_attempts=3)
    
    # Assert
    assert len(summary["weak_topics"]) == 0
    assert summary["overall_accuracy"] >= 0.90

def test_demo_slow_learner_performance(loaded_attempts) -> None:
    # Arrange
    raw_attempts = loaded_attempts.get("demo_slow_learner", [])
    attempts = [StandardizedAttempt(**item) for item in raw_attempts]
    
    # Act
    summary = summarize_student_performance(attempts, weak_threshold=0.70, min_attempts=3)
    
    # Assert
    assert len(summary["weak_topics"]) == 3
    # Check that average attempt time is slow (>25s) across all topics
    for t in summary["topics"]:
        assert t["average_attempt_time"] > 25.0
        assert t["is_weak"] is True

@pytest.mark.asyncio
@patch("app.services.recommendation_service.select")
async def test_recommendation_adaptation_demo_profiles(mock_select, loaded_attempts, question_index) -> None:
    # Setup mock database session
    mock_db = AsyncMock()
    
    # 1. Test demo_weak_algebra adaptation (should adapt medium -> easy due to low accuracy < 0.40)
    mock_analysis_record = MagicMock(spec=LearningGapAnalysis)
    mock_analysis_record.output_json = {
        "personalized_learning_strategy": "Reinforce algebra.",
        "weak_concepts": [
            {
                "concept_name": "Interpreting Linear Equations",
                "recommended_difficulty_progression": "medium",
                "confidence_score": 0.88
            }
        ]
    }
    mock_db.scalar.return_value = mock_analysis_record
    
    service = RecommendationService(mock_db)
    
    with patch("app.services.recommendation_service.json.load") as mock_json_load:
        # First load: attempts, Second load: question_index
        mock_json_load.side_effect = [loaded_attempts, question_index]
        
        result = await service.get_adaptive_recommendations(
            student_id="demo_weak_algebra",
            weak_threshold=0.70,
            min_attempts=3
        )
        
        assert result.student_id == "demo_weak_algebra"
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.concept_name == "Interpreting Linear Equations"
        # Emp accuracy for Interpreting Linear Equations is 30% (< 40%), so it downscales to easy
        assert rec.difficulty == "easy"
        assert "low historical accuracy" in rec.reasoning

    # 2. Test demo_advanced_geometry adaptation (should adapt medium -> hard due to accuracy > 0.85)
    mock_analysis_record_geo = MagicMock(spec=LearningGapAnalysis)
    mock_analysis_record_geo.output_json = {
        "personalized_learning_strategy": "Enrich geometry.",
        "weak_concepts": [
            {
                "concept_name": "Properties Of Geometric Figures",
                "recommended_difficulty_progression": "medium",
                "confidence_score": 0.95
            }
        ]
    }
    mock_db.scalar.return_value = mock_analysis_record_geo
    
    with patch("app.services.recommendation_service.json.load") as mock_json_load:
        mock_json_load.side_effect = [loaded_attempts, question_index]
        
        result = await service.get_adaptive_recommendations(
            student_id="demo_advanced_geometry",
            weak_threshold=0.70,
            min_attempts=3
        )
        
        assert result.student_id == "demo_advanced_geometry"
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.concept_name == "Properties Of Geometric Figures"
        # Emp accuracy for Properties Of Geometric Figures is 90% (> 85%), so it upscales to hard
        assert rec.difficulty == "hard"
        assert "excellent historical accuracy" in rec.reasoning

    # 3. Test demo_slow_learner adaptation (should adapt medium -> easy due to speed > 25s)
    mock_analysis_record_slow = MagicMock(spec=LearningGapAnalysis)
    mock_analysis_record_slow.output_json = {
        "personalized_learning_strategy": "Pace calculations.",
        "weak_concepts": [
            {
                "concept_name": "Multiplying Decimals",
                "recommended_difficulty_progression": "medium",
                "confidence_score": 0.85
            }
        ]
    }
    mock_db.scalar.return_value = mock_analysis_record_slow
    
    with patch("app.services.recommendation_service.json.load") as mock_json_load:
        mock_json_load.side_effect = [loaded_attempts, question_index]
        
        result = await service.get_adaptive_recommendations(
            student_id="demo_slow_learner",
            weak_threshold=0.70,
            min_attempts=3
        )
        
        assert result.student_id == "demo_slow_learner"
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.concept_name == "Multiplying Decimals"
        # Speed for Multiplying Decimals is >25s, so it downscales to easy
        assert rec.difficulty == "easy"
        assert "slow response speed" in rec.reasoning
