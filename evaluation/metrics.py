def recommendation_precision(recommended_topics: set[str], actual_weak_topics: set[str]) -> float:
    if not recommended_topics:
        return 0.0
    return len(recommended_topics & actual_weak_topics) / len(recommended_topics)


def recommendation_recall(recommended_topics: set[str], actual_weak_topics: set[str]) -> float:
    if not actual_weak_topics:
        return 0.0
    return len(recommended_topics & actual_weak_topics) / len(actual_weak_topics)

