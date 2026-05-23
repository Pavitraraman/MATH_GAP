from pydantic import BaseModel, Field


class ConceptExtractionSchema(BaseModel):
    concepts: list[str] = Field(description="List of core math concepts/topics extracted from study notes.")


class IngestedQuizQuestion(BaseModel):
    problem_id: str = Field(description="Unique string identifier or hash for this question.")
    skill: str = Field(description="Math skill/concept name this question maps to.")
    question_text: str = Field(description="The multiple choice question text.")
    options: list[str] = Field(description="Exactly 4 multiple choice options starting with A), B), C), D).")
    correct_option: str = Field(description="The correct option letter: 'A', 'B', 'C', or 'D'.")
    explanation: str = Field(description="Detailed explanation of the solution.")
    difficulty: str = Field(description="Difficulty rating: 'easy', 'medium', or 'hard'.")


class IngestedQuizSchema(BaseModel):
    concepts: list[str] = Field(description="Extracted key mathematical concepts from the material.")
    questions: list[IngestedQuizQuestion] = Field(description="List of generated adaptive quiz questions based on the notes.")
