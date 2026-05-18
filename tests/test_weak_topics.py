from app.schemas.recommendation import WeakTopic
from recommendation_engine.weak_topics import detect_weak_topics


class DummyTopic:
    def __init__(self, topic: str, score: float) -> None:
        self.topic = topic
        self.score = score


def test_detect_weak_topics_sorts_lowest_first() -> None:
    result = detect_weak_topics(
        [
            DummyTopic("algebra", 65),
            DummyTopic("fractions", 45),
            DummyTopic("geometry", 88),
        ]
    )
    assert result == [
        WeakTopic(topic="fractions", score=45, severity="high"),
        WeakTopic(topic="algebra", score=65, severity="medium"),
    ]

