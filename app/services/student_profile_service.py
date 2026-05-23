import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_platform import StudentLearningProfile, QuizAttempt
from data_pipeline.schemas import StandardizedAttempt
from app.services.retention_decay_engine import RetentionDecayEngine

logger = logging.getLogger("math_gap.student_profile_service")


class StudentProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_profile(self, student_id: str) -> StudentLearningProfile:
        """Fetches a student's persistent profile, initializing it with default values if missing."""
        student_id = str(student_id)
        stmt = select(StudentLearningProfile).where(StudentLearningProfile.student_id == student_id)
        profile = await self.db.scalar(stmt)

        if not profile:
            logger.info("Initializing new persistent student learning memory for student: %s", student_id)
            profile = StudentLearningProfile(
                student_id=student_id,
                mastery_levels={},
                weak_concepts=[],
                average_response_time=0.0,
                total_attempts=0,
                total_retries=0,
                total_skipped=0,
                learning_velocity=0.0,
                preferred_difficulty="medium",
                # Persistent Student Memory Fields
                retention_decay={},
                confidence_trends=[],
                quiz_history=[],
                revision_history=[],
                skipped_concepts=[],
                mastery_history=[],
                coaching_insights=[],
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        # Make sure dict/list properties are not None
        if profile.retention_decay is None:
            profile.retention_decay = {}
        if profile.confidence_trends is None:
            profile.confidence_trends = []
        if profile.quiz_history is None:
            profile.quiz_history = []
        if profile.revision_history is None:
            profile.revision_history = []
        if profile.skipped_concepts is None:
            profile.skipped_concepts = []
        if profile.mastery_history is None:
            profile.mastery_history = []
        if profile.coaching_insights is None:
            profile.coaching_insights = []

        return profile

    async def get_all_student_attempts(self, student_id: str) -> list[StandardizedAttempt]:
        """Combines precomputed static historical attempts with live database quiz attempts."""
        student_id = str(student_id)
        attempts = []

        # 1. Load historical attempts from cached file index
        index_path = Path("data/processed/student_attempts_index.json")
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as f:
                    cached_index = json.load(f)
                    student_attempts_raw = cached_index.get(student_id)
                    if student_attempts_raw:
                        attempts = [StandardizedAttempt(**item) for item in student_attempts_raw]
            except Exception as exc:
                logger.warning("Failed to load historical attempts from cache for student %s: %s", student_id, exc)

        # 2. Fetch live attempts from database
        stmt = (
            select(QuizAttempt)
            .where(QuizAttempt.student_id == student_id)
            .order_by(QuizAttempt.created_at.asc())
        )
        db_attempts = await self.db.scalars(stmt)
        for att in db_attempts:
            # Map database question attempts to StandardizedAttempt schema
            from app.models.learning_platform import Question
            q_stmt = select(Question).where(Question.id == att.question_id)
            q = await self.db.scalar(q_stmt)
            skill = q.skill if q else "General Math"
            
            attempts.append(
                StandardizedAttempt(
                    student_id=att.student_id,
                    skill=skill,
                    correct=att.correct,
                    attempt_time=att.attempt_time,
                    problem_id=str(att.question_id),
                    difficulty=q.difficulty if q else "medium"
                )
            )

        return attempts

    async def update_profile_after_attempt(
        self,
        student_id: str,
        question_id: int,
        correct: int,
        attempt_time: float,
        is_retry: int = 0,
        skipped: int = 0,
        selected_option: str = "",
    ) -> StudentLearningProfile:
        """Saves a quiz attempt and updates learning memory, stability, and Ebbinghaus retention curves in real-time."""
        student_id = str(student_id)

        # 1. Save QuizAttempt record to database
        attempt = QuizAttempt(
            student_id=student_id,
            question_id=question_id,
            selected_option=selected_option,
            correct=correct,
            attempt_time=attempt_time,
            is_retry=is_retry,
            skipped=skipped,
        )
        self.db.add(attempt)
        await self.db.flush()

        # 2. Fetch student profile and attempts
        profile = await self.get_or_create_profile(student_id)
        all_attempts = await self.get_all_student_attempts(student_id)

        # Update base counters
        profile.total_attempts += 1
        if is_retry:
            profile.total_retries += 1
        if skipped:
            profile.total_skipped += 1

        # Fetch attempted question topic
        from app.models.learning_platform import Question
        q_stmt = select(Question).where(Question.id == question_id)
        attempted_q = await self.db.scalar(q_stmt)
        attempted_skill = attempted_q.skill if attempted_q else "General Math"

        if not all_attempts:
            return profile

        # 3. Group attempts by skill
        from collections import defaultdict
        skill_groups = defaultdict(list)
        for att in all_attempts:
            skill_groups[att.skill].append(att)

        # 4. Spaced repetition retention calculations
        now_str = datetime.utcnow().isoformat()
        
        # Load existing stability or set default (24 hours)
        topic_decay_data = profile.retention_decay.get(attempted_skill, {})
        current_stability = topic_decay_data.get("stability_hours", 24.0)
        
        # Compute skill accuracy
        records = skill_groups[attempted_skill]
        tot = len(records)
        corr = sum(r.correct for r in records)
        skill_acc = corr / tot if tot else 0.0

        # Calculate new stability
        new_stability = RetentionDecayEngine.update_memory_stability(
            current_stability, skill_acc, bool(correct)
        )
        
        # Update retention decay registry
        new_decay_dict = dict(profile.retention_decay)
        new_decay_dict[attempted_skill] = {
            "stability_hours": new_stability,
            "last_attempt_time": now_str
        }
        profile.retention_decay = new_decay_dict

        # 5. Compute Mastery Levels & 6-Tier Mastery States
        new_mastery_levels = {}
        new_weak_concepts = []
        total_time = 0.0

        # Ensure mastery_history is list
        mast_history = list(profile.mastery_history)

        for skill, records in skill_groups.items():
            tot = len(records)
            corr = sum(r.correct for r in records)
            accuracy = corr / tot if tot else 0.0
            total_time += sum(r.attempt_time for r in records)

            # Retrieve retention rate R = e^(-t/S)
            decay_data = profile.retention_decay.get(skill, {})
            stability = decay_data.get("stability_hours", 24.0)
            last_attempt = decay_data.get("last_attempt_time", now_str)
            
            retention_prob = RetentionDecayEngine.calculate_retention_probability(
                stability, last_attempt
            )

            # Mastery state classification (6 Tiers)
            if tot < 3:
                tier = "New"
            elif accuracy < 0.50:
                tier = "Learning"
            elif accuracy < 0.70:
                tier = "Improving"
            elif retention_prob < 0.60:
                tier = "Needs Revision"  # Decay trigger overrides other proficient categories
            elif accuracy < 0.90:
                tier = "Proficient"
            else:
                tier = "Mastered"

            # Check if mastery state transitioned to log it in learning timeline
            old_tier_data = profile.mastery_levels.get(skill, {})
            old_tier = old_tier_data.get("tier")
            if old_tier != tier:
                mast_history.append({
                    "timestamp": now_str,
                    "skill": skill,
                    "state": tier,
                    "old_state": old_tier
                })

            new_mastery_levels[skill] = {
                "accuracy": round(accuracy, 4),
                "tier": tier,
                "attempts": tot,
                "retention_probability": retention_prob,
                "stability_hours": stability
            }

            if tot >= 3 and accuracy < 0.70:
                new_weak_concepts.append(skill)

        profile.mastery_levels = new_mastery_levels
        profile.weak_concepts = new_weak_concepts
        profile.mastery_history = mast_history
        profile.average_response_time = round(total_time / len(all_attempts), 2)

        # 6. Calculate Learning Velocity (accuracy progression over last 10 attempts)
        if len(all_attempts) >= 10:
            last_10 = all_attempts[-10:]
            prev_10 = all_attempts[-20:-10] if len(all_attempts) >= 20 else all_attempts[:-10]
            
            last_acc = sum(r.correct for r in last_10) / len(last_10)
            prev_acc = sum(r.correct for r in prev_10) / len(prev_10) if prev_10 else last_acc
            profile.learning_velocity = round(last_acc - prev_acc, 4)
        else:
            profile.learning_velocity = 0.0

        # 7. Preferred difficulty calculation
        overall_acc = sum(r.correct for r in all_attempts) / len(all_attempts)
        if overall_acc < 0.45:
            profile.preferred_difficulty = "easy"
        elif overall_acc > 0.85:
            profile.preferred_difficulty = "hard"
        else:
            profile.preferred_difficulty = "medium"

        # 8. Append Overall Accuracy Trend
        conf_trends = list(profile.confidence_trends)
        conf_trends.append({
            "timestamp": now_str,
            "score": round(overall_acc, 4)
        })
        profile.confidence_trends = conf_trends

        # 9. Generate AI Coaching Insights
        profile.coaching_insights = RetentionDecayEngine.generate_coaching_insights(
            accuracy=overall_acc,
            average_time=profile.average_response_time,
            total_attempts=profile.total_attempts,
            learning_velocity=profile.learning_velocity,
            weak_concepts=profile.weak_concepts,
            retention_decay=profile.retention_decay,
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)

        logger.info("Successfully evolved learning memory for student '%s'. Overall Attempts: %d, Velocity: %.1f%%", student_id, profile.total_attempts, profile.learning_velocity * 100)
        
        return profile
