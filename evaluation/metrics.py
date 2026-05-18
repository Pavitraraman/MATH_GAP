def recommendation_precision(recommended_topics: set[str], actual_weak_topics: set[str]) -> float:
    if not recommended_topics:
        return 0.0
    return len(recommended_topics & actual_weak_topics) / len(recommended_topics)


def recommendation_recall(recommended_topics: set[str], actual_weak_topics: set[str]) -> float:
    if not actual_weak_topics:
        return 0.0
    return len(recommended_topics & actual_weak_topics) / len(actual_weak_topics)


def improvement_rate(previous_accuracy: float, current_accuracy: float) -> float:
    return current_accuracy - previous_accuracy


def cost_per_session(total_cost_usd: float, sessions: int) -> float:
    return total_cost_usd / sessions if sessions else 0.0


def output_consistency(outputs: list[set[str]]) -> float:
    if len(outputs) < 2:
        return 1.0
    intersections = 0
    comparisons = 0
    for index, left in enumerate(outputs):
        for right in outputs[index + 1 :]:
            union = left | right
            intersections += len(left & right) / len(union) if union else 1.0
            comparisons += 1
    return intersections / comparisons if comparisons else 1.0

