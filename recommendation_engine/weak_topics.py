from app.models.assessment import TopicScore
from app.schemas.recommendation import WeakTopic


def detect_weak_topics(topic_scores: list[TopicScore], threshold: float = 70.0) -> list[WeakTopic]:
    results: list[WeakTopic] = []
    for item in topic_scores:
        if item.score >= threshold:
            continue
        severity = "high" if item.score < 50 else "medium"
        results.append(WeakTopic(topic=item.topic, score=item.score, severity=severity))
    return sorted(results, key=lambda item: item.score)

