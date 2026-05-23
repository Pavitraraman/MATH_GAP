import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.learning_platform import Question, StudentLearningProfile
from app.services.content_ingestion_service import ContentIngestionService
from app.services.rag_service import RAGService
from app.services.student_profile_service import StudentProfileService
from app.services.curriculum_engine import CurriculumEngine

client = TestClient(app)


def test_pdf_extraction_and_chunking() -> None:
    # Arrange
    ingestion = ContentIngestionService(None)
    mock_pdf_bytes = b"%PDF-1.4 Mock PDF Content"
    
    # Mock fitz.open to return a mock document with text
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Pythagorean Theorem: a^2 + b^2 = c^2. In a right triangle, side square equals leg squares sum."
    
    mock_doc = MagicMock()
    mock_doc.__iter__.return_value = [mock_page]
    
    with patch("app.services.content_ingestion_service.fitz.open", return_value=mock_doc):
        # Act
        text = ingestion.extract_text(mock_pdf_bytes, "pythagoras.pdf")
        chunks = ingestion.chunk_text(text, chunk_size=30, overlap=10)
        
        # Assert
        assert "Pythagorean Theorem" in text
        assert len(chunks) > 0
        assert chunks[0] == text[:30]


def test_local_keyword_cosine_similarity() -> None:
    # Arrange
    rag = RAGService(None)
    query = "Pythagorean Theorem triangle hypotenuse"
    chunk_perfect = "In a right triangle, the Pythagorean Theorem calculates the hypotenuse from sides."
    chunk_irrelevant = "Linear equations denote straight lines with constant slope value coordinates."
    
    # Act
    sim_perfect = rag._compute_keyword_similarity(query, chunk_perfect)
    sim_irrelevant = rag._compute_keyword_similarity(query, chunk_irrelevant)
    
    # Assert
    assert sim_perfect > 0.1
    assert sim_perfect > sim_irrelevant


@pytest.mark.asyncio
@patch("app.services.rag_service.RAGService.get_embedding")
@patch("app.services.rag_service.select")
async def test_dual_mode_rag_search(mock_select, mock_embed) -> None:
    # Arrange
    mock_db = AsyncMock()
    rag = RAGService(mock_db)
    
    mock_chunk_1 = MagicMock()
    mock_chunk_1.id = 101
    mock_chunk_1.material_id = 1
    mock_chunk_1.text = "Geometry properties and angles of a polygon."
    mock_chunk_1.embedding = [0.1, 0.2, 0.3]
    
    mock_chunk_2 = MagicMock()
    mock_chunk_2.id = 102
    mock_chunk_2.material_id = 1
    mock_chunk_2.text = "Solving linear expressions and equations."
    mock_chunk_2.embedding = [0.9, 0.0, 0.1]
    
    mock_result = MagicMock()
    mock_result.all.return_value = [mock_chunk_1, mock_chunk_2]
    mock_db.scalars = AsyncMock(return_value=mock_result)
    mock_embed.return_value = [0.12, 0.22, 0.28]  # closer to chunk 1
    
    # Act
    results = await rag.search_relevant_context(
        student_id="student_live",
        query="angles and polygon shape properties",
        limit=2
    )
    
    # Assert
    assert len(results) == 2
    # Chunk 1 should be ranked first because query vector is mathematically closer to it
    assert results[0]["chunk_id"] == 101
    assert results[0]["similarity_score"] > 0.0


@pytest.mark.asyncio
async def test_adaptive_curriculum_question_selection() -> None:
    # Arrange
    mock_db = AsyncMock()
    
    mock_q1 = Question(
        id=201,
        problem_id="prob_easy",
        skill="Angles",
        question_text="Find x",
        options=["A) 1", "B) 2"],
        correct_option="A",
        difficulty="easy"
    )
    mock_q2 = Question(
        id=202,
        problem_id="prob_hard",
        skill="Angles",
        question_text="Solve advanced proof",
        options=["A) proof", "B) wrong"],
        correct_option="A",
        difficulty="hard"
    )
    
    # Mock DB query returning these questions
    mock_result = MagicMock()
    mock_result.all.return_value = [mock_q1, mock_q2]
    mock_db.scalars = AsyncMock(return_value=mock_result)
    
    # Mock StudentProfileService to return an attempts list reflecting poor performance
    # This should trigger adaptive difficulty downscaling (bringing hard -> easy)
    with patch("app.services.student_profile_service.StudentProfileService.get_or_create_profile") as mock_profile, \
         patch("app.services.student_profile_service.StudentProfileService.get_all_student_attempts") as mock_attempts, \
         patch("app.services.curriculum_engine.select") as mock_select:
             
        mock_prof = StudentLearningProfile(student_id="student_struggle", preferred_difficulty="hard")
        mock_profile.return_value = mock_prof
        
        # Struggles with accuracy < 40%
        mock_attempts.return_value = [
            MagicMock(skill="Angles", correct=0, attempt_time=28.0),
            MagicMock(skill="Angles", correct=0, attempt_time=30.0)
        ]
        
        curriculum = CurriculumEngine(mock_db)
        
        # Act
        next_q = await curriculum.select_next_question("student_struggle", "Angles")
        
        # Assert
        assert next_q is not None
        # Should adapt difficulty from hard down to easy, prioritizing the easy question!
        assert next_q.difficulty == "easy"
        assert next_q.problem_id == "prob_easy"


@patch("app.api.routes.platform.ContentIngestionService")
def test_upload_material_route(mock_ingestion_class) -> None:
    # Arrange
    from app.api import deps
    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=MagicMock())
    
    app.dependency_overrides[deps.resolve_student_id] = lambda: "student_upload"
    app.dependency_overrides[deps.get_db] = lambda: mock_db
    
    try:
        mock_service_instance = MagicMock()
        mock_ingestion_class.return_value = mock_service_instance
        
        mock_material = MagicMock()
        mock_material.id = 50
        mock_material.filename = "notes.pdf"
        mock_material.extracted_concepts = ["Algebra"]
        
        mock_questions = [MagicMock(), MagicMock()]
        
        mock_service_instance.ingest_material = AsyncMock(return_value=(mock_material, mock_questions))
        
        # Act
        response = client.post(
            "/platform/upload-material",
            data={"student_id": "student_upload"},
            files={"file": ("notes.pdf", b"%PDF-1.4 mock", "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["material_id"] == 50
        assert data["filename"] == "notes.pdf"
        assert data["questions_count"] == 2
        assert "Algebra" in data["extracted_concepts"]
    finally:
        app.dependency_overrides.clear()
