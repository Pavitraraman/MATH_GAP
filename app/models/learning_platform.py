from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class StudentLearningProfile(Base):
    __tablename__ = "student_learning_profiles"

    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    mastery_levels: Mapped[dict] = mapped_column(JSON, default=dict)  # Maps topic -> {accuracy: float, tier: str}
    weak_concepts: Mapped[list] = mapped_column(JSON, default=list)  # List of weak concept strings
    average_response_time: Mapped[float] = mapped_column(Float, default=0.0)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    total_retries: Mapped[int] = mapped_column(Integer, default=0)
    total_skipped: Mapped[int] = mapped_column(Integer, default=0)
    learning_velocity: Mapped[float] = mapped_column(Float, default=0.0)  # accuracy improvement rate
    preferred_difficulty: Mapped[str] = mapped_column(String(32), default="medium")
    
    # Persistent Student Memory Fields
    retention_decay: Mapped[dict] = mapped_column(JSON, default=dict)  # Maps topic -> {stability_hours: float, last_attempt_time: str}
    confidence_trends: Mapped[list] = mapped_column(JSON, default=list)  # List of {timestamp: str, score: float}
    quiz_history: Mapped[list] = mapped_column(JSON, default=list)  # List of quiz metadata dicts
    revision_history: Mapped[list] = mapped_column(JSON, default=list)  # List of {timestamp: str, skill: str}
    skipped_concepts: Mapped[list] = mapped_column(JSON, default=list)  # List of skipped skill names
    mastery_history: Mapped[list] = mapped_column(JSON, default=list)  # List of {timestamp: str, skill: str, state: str}
    coaching_insights: Mapped[list] = mapped_column(JSON, default=list)  # List of dynamic tutoring highlights strings
    
    # Uploaded-Material-Specific Memory Tracking
    material_mastery: Mapped[dict] = mapped_column(JSON, default=dict)  # Maps material_id -> chapter -> concept -> {accuracy, stability, tier}
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    file_type: Mapped[str] = mapped_column(String(32))  # e.g., "pdf", "txt", "md"
    content: Mapped[str] = mapped_column(Text)
    extracted_concepts: Mapped[list] = mapped_column(JSON, default=list)  # List of concept names mapped from text
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chunks: Mapped[list["MaterialChunk"]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON, nullable=True)  # List of floats representing chunk vectors
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    material: Mapped[Material] = relationship(back_populates="chunks")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="SET NULL"), nullable=True, index=True)
    problem_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # e.g., curriculum id or UUID
    skill: Mapped[str] = mapped_column(String(128), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)  # List of options: ["A) ...", "B) ..."]
    correct_option: Mapped[str] = mapped_column(String(8))  # "A", "B", "C", "D"
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium")  # "easy", "medium", "hard"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuizQuestionAssociation(Base):
    __tablename__ = "quiz_question_associations"

    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    selected_option: Mapped[str] = mapped_column(String(8))
    correct: Mapped[int] = mapped_column(Integer)  # 0 or 1
    attempt_time: Mapped[float] = mapped_column(Float, default=0.0)
    is_retry: Mapped[int] = mapped_column(Integer, default=0)  # 0 or 1
    skipped: Mapped[int] = mapped_column(Integer, default=0)  # 0 or 1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
