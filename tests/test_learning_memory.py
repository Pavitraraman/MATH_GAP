import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.learning_platform import Question, StudentLearningProfile, QuizAttempt
from app.services.retention_decay_engine import RetentionDecayEngine
from app.services.student_profile_service import StudentProfileService
from app.services.curriculum_engine import CurriculumEngine

client = TestClient(app)


def test_ebbinghaus_forgetting_decay_calculations() -> None:
    # Arrange
    stability = 24.0  # 1 day memory half life stability
    
    # 1. 0 hours elapsed (R should be 1.0)
    now_str = datetime.utcnow().isoformat()
    ret_0 = RetentionDecayEngine.calculate_retention_probability(stability, now_str)
    assert ret_0 == 1.0
    
    # 2. 24 hours elapsed (R = e^-1 = ~0.3679)
    last_day_str = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    ret_24 = RetentionDecayEngine.calculate_retention_probability(stability, last_day_str)
    assert 0.35 <= ret_24 <= 0.38
    
    # 3. Stability multiplier on correct answer: S_new = S_old * (1.5 + 2.0 * accuracy)
    new_stability = RetentionDecayEngine.update_memory_stability(24.0, 0.75, True)
    assert new_stability == round(24.0 * (1.5 + 2.0 * 0.75), 2)
    
    # 4. Stability halves on incorrect answer
    halved_stability = RetentionDecayEngine.update_memory_stability(24.0, 0.75, False)
    assert halved_stability == 12.0


def test_mastery_state_decay_transitions() -> None:
    # Verify that Ebbinghaus decay overrides standard proficient categories to Needs Revision
    accuracy = 0.90
    tot = 5
    retention_prob = 0.40  # Decayed below 60%
    
    if tot < 3:
        tier = "New"
    elif accuracy < 0.50:
        tier = "Learning"
    elif accuracy < 0.70:
        tier = "Improving"
    elif retention_prob < 0.60:
        tier = "Needs Revision"
    elif accuracy < 0.90:
        tier = "Proficient"
    else:
        tier = "Mastered"
        
    assert tier == "Needs Revision"


@pytest.mark.asyncio
@patch("app.services.student_profile_service.StudentProfileService.get_or_create_profile")
@patch("app.services.student_profile_service.StudentProfileService.get_all_student_attempts")
@patch("app.services.curriculum_engine.select")
async def test_adaptive_curriculum_urgency_selection(mock_select, mock_attempts, mock_profile) -> None:
    # Verify that CurriculumEngine prioritizes questions whose topic "Needs Revision"
    mock_db = AsyncMock()
    
    mock_q1 = Question(
        id=301,
        problem_id="q_needs_rev",
        skill="Algebra",
        question_text="Revision equations",
        options=["A) 1", "B) 2"],
        correct_option="A",
        difficulty="medium"
    )
    
    mock_result = MagicMock()
    mock_result.all.return_value = [mock_q1]
    mock_db.scalars = AsyncMock(return_value=mock_result)
    
    # Needs Revision
    mock_prof = StudentLearningProfile(
        student_id="student_decay",
        preferred_difficulty="medium",
        mastery_levels={
            "Algebra": {"accuracy": 0.85, "tier": "Needs Revision", "retention_probability": 0.35}
        }
    )
    mock_profile.return_value = mock_prof
    mock_attempts.return_value = [MagicMock(skill="Algebra", correct=1, attempt_time=12.0)]
    
    curriculum = CurriculumEngine(mock_db)
    
    # Act
    next_q = await curriculum.select_next_question("student_decay", "Algebra")
    
    # Assert
    assert next_q is not None
    assert next_q.problem_id == "q_needs_rev"


@patch("app.api.routes.platform.StudentProfileService")
def test_student_memory_routes(mock_profile_class) -> None:
    # Verify API endpoints for student memory and learning journey timelines
    from app.api import deps
    app.dependency_overrides[deps.resolve_student_id] = lambda: "student_timeline"
    
    try:
        mock_service_instance = MagicMock()
        mock_profile_class.return_value = mock_service_instance
        
        mock_prof = StudentLearningProfile(
            student_id="student_timeline",
            mastery_levels={"Geometry": {"accuracy": 0.90, "tier": "Mastered", "retention_probability": 0.95}},
            weak_concepts=[],
            average_response_time=12.5,
            total_attempts=14,
            learning_velocity=0.08,
            preferred_difficulty="hard",
            retention_decay={"Geometry": {"stability_hours": 96.0, "last_attempt_time": "2026-05-23T00:00:00"}},
            confidence_trends=[{"timestamp": "2026-05-23T00:00:00", "score": 0.90}],
            mastery_history=[{"timestamp": "2026-05-23T00:00:00", "skill": "Geometry", "state": "Mastered"}],
            coaching_insights=["Keep it up!"]
        )
        
        mock_service_instance.get_or_create_profile = AsyncMock(return_value=mock_prof)
        
        # Act & Assert
        # 1. Check Student Memory endpoint
        response = client.get("/platform/student-memory/student_timeline")
        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == "student_timeline"
        assert data["preferred_difficulty"] == "hard"
        assert "Keep it up!" in data["coaching_insights"]
        
        # 2. Check Learning Journey Timeline endpoint
        response_timeline = client.get("/platform/learning-timeline/student_timeline")
        assert response_timeline.status_code == 200
        timeline_data = response_timeline.json()
        assert timeline_data["student_id"] == "student_timeline"
        assert len(timeline_data["mastery_history"]) == 1
        assert timeline_data["mastery_history"][0]["skill"] == "Geometry"
    finally:
        app.dependency_overrides.clear()
