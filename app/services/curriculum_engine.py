import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_platform import Question, QuizAttempt
from app.services.student_profile_service import StudentProfileService

logger = logging.getLogger("math_gap.curriculum_engine")


class CurriculumEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def select_next_question(self, student_id: str, skill: str) -> Question | None:
        """Dynamically decides the next question and difficulty level based on live performance and spacing rules."""
        student_id = str(student_id)

        # 1. Fetch persistent learning profile & attempts history
        profile_service = StudentProfileService(self.db)
        profile = await profile_service.get_or_create_profile(student_id)
        all_attempts = await profile_service.get_all_student_attempts(student_id)

        # 2. Gather skill-specific historical performance metrics
        skill_attempts = [a for a in all_attempts if a.skill.lower() == skill.lower()]
        
        hist_accuracy = 0.5
        hist_speed = 15.0
        
        if skill_attempts:
            hist_accuracy = sum(a.correct for a in skill_attempts) / len(skill_attempts)
            hist_speed = sum(a.attempt_time for a in skill_attempts) / len(skill_attempts)

        # 3. Target Difficulty Adaptation
        # Get baseline preferred difficulty from profile
        base_difficulty = profile.preferred_difficulty
        adapted_difficulty = base_difficulty

        # Downgrade triggers (low accuracy or high latency)
        if hist_accuracy < 0.40 or hist_speed > 25.0:
            if base_difficulty == "hard":
                adapted_difficulty = "medium"
            elif base_difficulty == "medium":
                adapted_difficulty = "easy"
        
        # Upgrade triggers (high accuracy)
        if hist_accuracy > 0.85:
            if base_difficulty == "easy":
                adapted_difficulty = "medium"
            elif base_difficulty == "medium":
                adapted_difficulty = "hard"

        # 4. Fetch all available questions in the database mapping this skill
        stmt = select(Question).where(Question.skill == skill)
        q_result = await self.db.scalars(stmt)
        candidates = list(q_result.all())

        if not candidates:
            # Try fuzzy matching skill
            stmt = select(Question).where(Question.skill.icontains(skill))
            q_result = await self.db.scalars(stmt)
            candidates = list(q_result.all())
            
        if not candidates:
            # Return any question in the DB as absolute fallback
            stmt = select(Question).limit(5)
            q_result = await self.db.scalars(stmt)
            candidates = list(q_result.all())

        if not candidates:
            logger.warning("No questions found in database for skill '%s' or fallback.", skill)
            return None

        # 5. Extract mistake history and mastered questions
        # Build last attempts for each question
        question_last_status = {}
        stmt = (
            select(QuizAttempt)
            .where(QuizAttempt.student_id == student_id)
            .order_by(QuizAttempt.created_at.asc())
        )
        db_attempts = await self.db.scalars(stmt)
        for att in db_attempts:
            question_last_status[att.question_id] = att.correct

        # 6. Apply Multi-Factor Scoring incorporating Spaced Decay & Mastery Telemetry
        scored_candidates = []
        W_DIFFICULTY = 0.4
        W_RECENCY = 0.3
        W_URGENCY = 0.3

        # Extract memory variables safely from profile
        skill_mastery = (profile.mastery_levels or {}).get(skill, {})
        mastery_state = skill_mastery.get("tier", "New")
        retention_prob = skill_mastery.get("retention_probability", 1.0)
        velocity = profile.learning_velocity or 0.0

        for q in candidates:
            # Score S_difficulty
            if q.difficulty.lower() == adapted_difficulty.lower():
                S_difficulty = 1.0
            elif (q.difficulty.lower() == "medium" and adapted_difficulty in ("easy", "hard")) or \
                 (adapted_difficulty == "medium" and q.difficulty.lower() in ("easy", "hard")):
                S_difficulty = 0.5
            else:
                S_difficulty = 0.1

            # High learning velocity challenges the student with harder questions
            if velocity > 0.05 and q.difficulty == "hard":
                S_difficulty += 0.2
            # Low learning velocity supports the student with easier questions
            elif velocity < -0.05 and q.difficulty == "easy":
                S_difficulty += 0.2

            # Score S_recency
            status = question_last_status.get(q.id)
            if status == 0:
                S_recency = 1.0  # Spaced retry priority
            elif status == 1:
                S_recency = -100.0  # Mastered questions strictly filtered out
            else:
                S_recency = 0.5  # Fresh unattempted question

            # Score S_urgency (Spaced Repetition & Decay priority)
            S_urgency = 0.0
            if mastery_state == "Needs Revision":
                S_urgency += 2.0  # Spaced review boost
            
            # Prioritize questions whose topic is actively decaying
            S_urgency += (1.0 - retention_prob) * 1.5

            total_score = W_DIFFICULTY * S_difficulty + W_RECENCY * S_recency + W_URGENCY * S_urgency
            
            # Skip mastered questions
            if total_score < 0:
                continue

            scored_candidates.append((q, total_score))

        if not scored_candidates:
            # Fallback if all questions are mastered: clear mastery history for this skill to allow reviews
            logger.info("Student mastered all questions in '%s'. Allowing review of mastered questions...", skill)
            return candidates[0]

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        chosen_question = scored_candidates[0][0]

        logger.info(
            "Selected next question #%s for student '%s' in '%s'. Difficulty adapted: %s -> %s (accuracy: %.1f%%, speed: %.1fs)",
            chosen_question.problem_id, student_id, skill, base_difficulty, chosen_question.difficulty, hist_accuracy * 100, hist_speed
        )

        return chosen_question
