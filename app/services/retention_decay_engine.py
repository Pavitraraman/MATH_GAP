import math
import logging
from datetime import datetime

logger = logging.getLogger("math_gap.retention_decay_engine")


class RetentionDecayEngine:
    @staticmethod
    def calculate_retention_probability(stability_hours: float, last_attempt_time: str) -> float:
        """Calculates Ebbinghaus retention probability R = e^(-t/S) based on elapsed time."""
        if not last_attempt_time:
            return 1.0
        
        try:
            last_time = datetime.fromisoformat(last_attempt_time)
            elapsed = datetime.utcnow() - last_time
            elapsed_hours = elapsed.total_seconds() / 3600.0
            
            # stability_hours must be positive to prevent division by zero
            if stability_hours <= 0:
                stability_hours = 24.0
                
            retention = math.exp(-elapsed_hours / stability_hours)
            return round(retention, 4)
        except Exception as exc:
            logger.error("Error calculating retention decay: %s", exc)
            return 1.0

    @staticmethod
    def update_memory_stability(current_stability: float, topic_accuracy: float, is_correct: bool) -> float:
        """Computes modified stability multipliers S_new = S_old * multiplier based on correctness."""
        if current_stability <= 0:
            current_stability = 24.0  # Default initial stability is 24 hours (1 day)

        if is_correct:
            # Memory strength grows exponentially with positive reviews
            multiplier = 1.5 + (2.0 * topic_accuracy)
            new_stability = current_stability * multiplier
        else:
            # Memory strength drops by 50% on incorrect attempts
            new_stability = current_stability * 0.5

        # Clamp stability between 1 hour and 720 hours (30 days) for realistic spacing curves
        return round(max(1.0, min(720.0, new_stability)), 2)

    @classmethod
    def generate_coaching_insights(
        cls,
        accuracy: float,
        average_time: float,
        total_attempts: int,
        learning_velocity: float,
        weak_concepts: list[str],
        retention_decay: dict,
    ) -> list[str]:
        """Generates dynamic AI coaching insights based on learning profile indicators."""
        insights = []

        # 1. Spaced Repetition / Decay insights
        rapid_decay_topics = []
        for topic, data in retention_decay.items():
            stability = data.get("stability_hours", 24.0)
            if stability < 12.0:
                rapid_decay_topics.append(topic)
                
        if rapid_decay_topics:
            insights.append(
                f"Your retention on '{rapid_decay_topics[0]}' drops rapidly. Try reviewing it every 12 hours."
            )
        else:
            insights.append("Your spaced repetition retention curve is currently stable across core math topics.")

        # 2. Hesitation / Time insights
        if average_time > 25.0:
            insights.append("You hesitate more in word problems and multi-step equations. Try focusing on visual scaffolds.")
        else:
            insights.append("Your calculation response speed is fast, showing strong computational fluency.")

        # 3. Learning velocity insights
        if learning_velocity > 0.05:
            insights.append("Dynamic progress shows you improve faster with medium-difficulty progression pathways.")
        elif learning_velocity < -0.05:
            insights.append("Recent rolling scores show regression. Downscaling practice questions to build foundational skills.")
        else:
            insights.append("Mastery velocity is plateauing. Recommending curriculum upscaling to challenge stagnation points.")

        # 4. Spacing decay alerts
        if len(weak_concepts) > 0:
            insights.append(f"Conceptual gaps detected in '{weak_concepts[0]}'. Spacing automatic review intervals.")

        return insights
