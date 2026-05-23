import json
from pathlib import Path
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.recommendation import Recommendation
from app.schemas.recommendation import (
    RecommendationPlan,
    RecommendationRead,
    StudyActivity,
    WeakTopic,
    RecommendedQuestion,
    AdaptiveRecommendationItem,
    AdaptiveRecommendationResponse,
)
from app.core.exceptions import LLMProviderError, StudentNotFoundError
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from recommendation_engine.weak_topics import detect_weak_topics


class RecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_for_assessment(self, assessment_id: int) -> RecommendationRead | None:
        assessment = await self.db.scalar(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        if assessment is None:
            return None

        weak_topics = detect_weak_topics(assessment.topic_scores)
        prompt = await PromptService(self.db).get_active_prompt()
        rendered_prompt = prompt.template.format(
            grade_level=assessment.grade_level,
            overall_score=assessment.overall_score,
            weak_topics=[item.model_dump() for item in weak_topics],
        )
        plan = await LLMService(self.db).generate_plan(
            prompt=prompt,
            rendered_prompt=rendered_prompt,
            fallback_plan=self._build_fallback_plan(weak_topics),
        )

        # Enrich plan with actual question recommendations from the precomputed question bank
        plan.recommended_questions = self._get_question_recommendations(
            weak_topics=weak_topics,
            grade_level=assessment.grade_level
        )

        recommendation = Recommendation(
            assessment_id=assessment.id,
            student_id=assessment.student_id,
            weak_topics_json=[item.model_dump() for item in weak_topics],
            plan_json=plan.model_dump(),
        )
        self.db.add(recommendation)
        await self.db.commit()
        await self.db.refresh(recommendation)

        return RecommendationRead(
            id=recommendation.id,
            assessment_id=recommendation.assessment_id,
            student_id=recommendation.student_id,
            weak_topics=[WeakTopic.model_validate(item) for item in recommendation.weak_topics_json],
            plan=plan,
            created_at=recommendation.created_at,
        )

    async def get_adaptive_recommendations(
        self,
        student_id: str,
        weak_threshold: float = 0.7,
        min_attempts: int = 3,
    ) -> AdaptiveRecommendationResponse:
        student_id = str(student_id)

        # 1. Fetch latest LearningGapAnalysis from DB
        from app.models.llm import LearningGapAnalysis

        stmt = (
            select(LearningGapAnalysis)
            .where(LearningGapAnalysis.student_id == student_id)
            .order_by(desc(LearningGapAnalysis.created_at))
            .limit(1)
        )
        analysis_record = await self.db.scalar(stmt)

        # If no analysis exists, dynamically generate it
        if not analysis_record:
            from app.services.learning_plan_service import LearningPlanService
            await LearningPlanService(self.db).generate_learning_plan(
                student_id=student_id,
                weak_threshold=weak_threshold,
                min_attempts=min_attempts,
            )
            # Re-fetch
            analysis_record = await self.db.scalar(stmt)

        if not analysis_record:
            raise ValueError(f"Could not fetch or generate learning gap analysis for student {student_id}")

        analysis_output = analysis_record.output_json
        personalized_strategy = analysis_output.get("personalized_learning_strategy", "No strategy available.")
        weak_concepts_list = analysis_output.get("weak_concepts", [])

        # 2. Retrieve student attempts history
        attempts = []
        index_path = Path("data/processed/student_attempts_index.json")
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as f:
                    cached_index = json.load(f)
                    student_attempts_raw = cached_index.get(student_id)
                    if student_attempts_raw:
                        from data_pipeline.schemas import StandardizedAttempt
                        attempts = [StandardizedAttempt(**item) for item in student_attempts_raw]
            except Exception:
                pass

        if not attempts:
            from data_pipeline.student_analysis import load_student_attempts
            csv_path = Path("students dataset.csv")
            jsonl_path = Path("data/processed/student_attempts.jsonl")
            target_path = csv_path if csv_path.exists() else jsonl_path
            if target_path.exists():
                attempts = load_student_attempts(target_path, student_id)
                
        if not attempts:
            raise StudentNotFoundError(f"Student ID '{student_id}' has no attempts recorded or does not exist.")

        # 3. Build student profile context:
        # - Accuracy per skill
        # - Response speed per skill
        # - Previous mistake questions (incorrect last attempt)
        # - Mastered questions (correct last attempt)
        from collections import defaultdict
        skill_attempts = defaultdict(list)
        problem_attempts = defaultdict(list)

        for att in attempts:
            skill_attempts[att.skill].append(att)
            problem_attempts[att.problem_id].append(att)

        skill_accuracy = {}
        skill_speed = {}
        for skill, records in skill_attempts.items():
            tot = len(records)
            corr = sum(r.correct for r in records)
            skill_accuracy[skill] = corr / tot if tot else 0.0
            skill_speed[skill] = sum(r.attempt_time for r in records) / tot if tot else 0.0

        mistake_problems = set()
        mastered_problems = set()
        for pid, records in problem_attempts.items():
            last_attempt = records[-1]
            if last_attempt.correct == 1:
                mastered_problems.add(pid)
            else:
                mistake_problems.add(pid)

        # 4. Load question index
        question_index = {}
        q_index_path = Path("data/processed/question_index.json")
        if q_index_path.exists():
            try:
                with q_index_path.open("r", encoding="utf-8") as f:
                    question_index = json.load(f)
            except Exception:
                pass

        # 5. Dynamic scoring weights
        W_TOPIC = 0.5
        W_DIFFICULTY = 0.3
        W_RECENCY = 0.2

        recommendations = []

        # Score and rank questions for each weak concept diagnosed
        for concept in weak_concepts_list:
            concept_name = concept.get("concept_name", "")
            matched_key = None
            for key in question_index.keys():
                if key.lower() == concept_name.lower():
                    matched_key = key
                    break

            if not matched_key:
                for key in question_index.keys():
                    if key.lower() in concept_name.lower() or concept_name.lower() in key.lower():
                        matched_key = key
                        break

            if not matched_key:
                continue

            # Target difficulty adaptation
            gemini_difficulty = concept.get("recommended_difficulty_progression", "medium").lower()
            if "easy" in gemini_difficulty:
                base_difficulty = "easy"
            elif "hard" in gemini_difficulty:
                base_difficulty = "hard"
            else:
                base_difficulty = "medium"

            adapted_difficulty = base_difficulty
            hist_accuracy = skill_accuracy.get(matched_key, 0.5)
            hist_speed = skill_speed.get(matched_key, 15.0)

            adaptation_reason = []
            if hist_speed > 25.0:
                if base_difficulty == "hard":
                    adapted_difficulty = "medium"
                elif base_difficulty == "medium":
                    adapted_difficulty = "easy"
                adaptation_reason.append(f"slow response speed ({hist_speed:.1f}s)")

            if hist_accuracy < 0.40:
                if base_difficulty == "hard":
                    adapted_difficulty = "medium"
                elif base_difficulty == "medium":
                    adapted_difficulty = "easy"
                adaptation_reason.append(f"low historical accuracy ({hist_accuracy:.1%})")

            if hist_accuracy > 0.85:
                if base_difficulty == "easy":
                    adapted_difficulty = "medium"
                elif base_difficulty == "medium":
                    adapted_difficulty = "hard"
                adaptation_reason.append(f"excellent historical accuracy ({hist_accuracy:.1%})")

            candidates = question_index.get(matched_key, [])
            scored_candidates = []

            for q in candidates:
                q_id = str(q["problem_id"])

                # Topic Match Score S_topic
                S_topic = float(concept.get("confidence_score", 0.8))

                # Difficulty Score S_difficulty
                q_diff = q["difficulty"].lower()
                if q_diff == adapted_difficulty:
                    S_difficulty = 1.0
                elif (q_diff == "medium" and adapted_difficulty in ("easy", "hard")) or \
                     (adapted_difficulty == "medium" and q_diff in ("easy", "hard")):
                    S_difficulty = 0.5
                else:
                    S_difficulty = 0.1

                # Recency/Mistake Score S_recency
                if q_id in mistake_problems:
                    S_recency = 1.0
                elif q_id in mastered_problems:
                    S_recency = -100.0
                else:
                    S_recency = 0.5

                total_score = W_TOPIC * S_topic + W_DIFFICULTY * S_difficulty + W_RECENCY * S_recency

                if total_score < 0:
                    continue

                scored_candidates.append((q, total_score))

            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            top_candidates = scored_candidates[:3]

            recommended_qs = [
                RecommendedQuestion(
                    problem_id=str(item[0]["problem_id"]),
                    skill=matched_key,
                    grade_level=8,
                    difficulty=item[0]["difficulty"],
                    empirical_accuracy=float(item[0]["empirical_accuracy"])
                )
                for item in top_candidates
            ]

            adaptation_str = f" (adapted from {base_difficulty} due to {', '.join(adaptation_reason)})" if adaptation_reason else ""
            concept_reasoning = (
                f"Selected {concept_name} with target difficulty {adapted_difficulty}{adaptation_str} "
                f"based on Gemini's diagnosed gap (confidence: {concept.get('confidence_score', 0.8):.0%}) "
                f"and historical student metrics: accuracy {hist_accuracy:.1%}, average speed {hist_speed:.1f}s."
            )

            avg_relevance = sum(item[1] for item in top_candidates) / len(top_candidates) if top_candidates else 0.0

            recommendations.append(
                AdaptiveRecommendationItem(
                    concept_name=concept_name,
                    recommended_questions=recommended_qs,
                    difficulty=adapted_difficulty,
                    reasoning=concept_reasoning,
                    topic_relevance_score=round(avg_relevance, 4)
                )
            )

        recommendations.sort(key=lambda x: x.topic_relevance_score, reverse=True)

        response = AdaptiveRecommendationResponse(
            student_id=student_id,
            personalized_learning_strategy=personalized_strategy,
            recommendations=recommendations
        )

        # Save recommendation run log for evaluation analysis
        try:
            from datetime import datetime
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "recommendation_runs.jsonl"

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "student_id": student_id,
                "overall_attempts": len(attempts),
                "overall_accuracy": round(sum(r.correct for r in attempts) / len(attempts) if attempts else 0.0, 4),
                "scoring_weights": {
                    "topic_match": W_TOPIC,
                    "difficulty_progression": W_DIFFICULTY,
                    "recency": W_RECENCY
                },
                "recommendation_plan": response.model_dump()
            }
            with log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return response

    @staticmethod
    def _get_question_recommendations(
        weak_topics: list[WeakTopic],
        grade_level: int,
        limit_per_topic: int = 3
    ) -> list[RecommendedQuestion]:
        index_path = Path("data/processed/question_index.json")
        if not index_path.exists():
            return []
        try:
            with index_path.open("r", encoding="utf-8") as f:
                question_index = json.load(f)
        except Exception:
            return []

        results = []
        for item in weak_topics:
            target_diff = "easy" if item.severity == "high" else "medium"

            candidates = [
                q for q in question_index.get(item.topic, [])
                if q["difficulty"] == target_diff
            ]
            if not candidates:
                candidates = question_index.get(item.topic, [])

            for q in candidates[:limit_per_topic]:
                results.append(
                    RecommendedQuestion(
                        problem_id=str(q["problem_id"]),
                        skill=item.topic,
                        grade_level=grade_level,
                        difficulty=q["difficulty"],
                        empirical_accuracy=float(q["empirical_accuracy"])
                    )
                )
        return results

    @staticmethod
    def _build_fallback_plan(weak_topics: list[WeakTopic]) -> RecommendationPlan:
        return RecommendationPlan(
            summary="Rule-based fallback plan generated because Gemini is not configured.",
            weak_topics=weak_topics,
            activities=[
                StudyActivity(
                    topic=item.topic,
                    action=f"Review fundamentals and complete targeted practice for {item.topic}.",
                    difficulty="foundational" if item.severity == "high" else "intermediate",
                    estimated_minutes=30 if item.severity == "high" else 20,
                )
                for item in weak_topics
            ],
            recommended_questions=[],
            next_assessment_focus=[item.topic for item in weak_topics],
        )
