from evaluation.metrics import (
    recommendation_precision,
    recommendation_recall,
    improvement_rate,
    cost_per_session,
    output_consistency,
)

def test_recommendation_precision() -> None:
    recommended = {"Fractions", "Geometry", "Algebra"}
    actual = {"Fractions", "Decimals"}
    # Overlap is {"Fractions"} (size 1)
    # Recommended count is 3
    # Precision should be 1/3
    assert abs(recommendation_precision(recommended, actual) - 0.333333) < 1e-4

def test_recommendation_precision_empty() -> None:
    assert recommendation_precision(set(), {"Fractions"}) == 0.0

def test_recommendation_recall() -> None:
    recommended = {"Fractions", "Geometry"}
    actual = {"Fractions", "Decimals", "Algebra"}
    # Overlap is {"Fractions"} (size 1)
    # Actual count is 3
    # Recall should be 1/3
    assert abs(recommendation_recall(recommended, actual) - 0.333333) < 1e-4

def test_recommendation_recall_empty() -> None:
    assert recommendation_recall({"Fractions"}, set()) == 0.0

def test_improvement_rate() -> None:
    assert abs(improvement_rate(0.60, 0.75) - 0.15) < 1e-6

def test_cost_per_session() -> None:
    assert cost_per_session(0.05, 10) == 0.005
    assert cost_per_session(0.05, 0) == 0.0

def test_output_consistency() -> None:
    sets = [
        {"Fractions", "Geometry"},
        {"Fractions", "Algebra"},
    ]
    # Union is {"Fractions", "Geometry", "Algebra"} (size 3)
    # Intersection is {"Fractions"} (size 1)
    # Jaccard = 1/3
    assert abs(output_consistency(sets) - 0.333333) < 1e-4

def test_output_consistency_single_or_empty() -> None:
    assert output_consistency([]) == 1.0
    assert output_consistency([{"Fractions"}]) == 1.0
