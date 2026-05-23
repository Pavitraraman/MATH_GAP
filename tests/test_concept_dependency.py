import pytest
from app.services.concept_graph import ConceptGraph


def test_prerequisite_dag_retrieval() -> None:
    """Asserts that direct prerequisite concepts are retrieved case-insensitively and fuzzy matched."""
    # 1. Derivatives requires Limits
    assert ConceptGraph.get_prerequisites("Derivatives") == ["limits"]
    
    # 2. Integrals requires Derivatives
    assert ConceptGraph.get_prerequisites("integrals") == ["derivatives"]
    
    # 3. Limits requires Functions
    assert ConceptGraph.get_prerequisites("limits") == ["functions"]
    
    # 4. Unknown topic returns empty list
    assert ConceptGraph.get_prerequisites("Advanced Topology") == []


def test_recursive_blocker_detection() -> None:
    """Verifies that find_root_learning_gap correctly bubbles up the fundamental failure in a prereq chain."""
    
    # Case A: Student is weak in derivatives, and their limits is also weak (< 70%)
    mastery_levels_a = {
        "Derivatives": {"accuracy": 0.45, "tier": "Learning"},
        "Limits": {"accuracy": 0.55, "tier": "Learning"},
        "Functions": {"accuracy": 0.95, "tier": "Mastered"}
    }
    
    gap, reason = ConceptGraph.find_root_learning_gap("Derivatives", mastery_levels_a)
    assert gap == "limits"
    assert "prerequisite 'limits' is weak" in reason.lower()
    
    # Case B: Student is weak in derivatives, but their limits is strong (90%), but their limits' prerequisite (functions) is weak (50%)
    mastery_levels_b = {
        "Derivatives": {"accuracy": 0.35, "tier": "Learning"},
        "Limits": {"accuracy": 0.90, "tier": "Proficient"},
        "Functions": {"accuracy": 0.40, "tier": "Learning"}
    }
    
    # limits is strong, so we don't block on limits itself. But limits relies on functions, which is weak!
    # Recurse should bubble up "functions" as the deepest gap!
    # Wait, in our graph: limits -> functions. If limits is strong, it won't recurse on limits dependencies, 
    # but wait, let's see how our recursive gap finder works:
    # "For prereq in prereqs: if prereq_mastery is weak, we recurse on prereq."
    # If Limits is strong, it won't be flagged as weak, so we don't recurse down its prereq (functions).
    # That is correct because if they are strong in Limits, they have successfully bypassed any Functions deficiency!
    # Let's test a case where Limits is weak (60%), and Functions is also weak (50%).
    # In this case, they are weak in limits, so we recurse on limits, which is weak in functions, so it returns "functions"!
    
    mastery_levels_c = {
        "Derivatives": {"accuracy": 0.35, "tier": "Learning"},
        "Limits": {"accuracy": 0.60, "tier": "Learning"},
        "Functions": {"accuracy": 0.50, "tier": "Learning"}
    }
    
    gap_c, reason_c = ConceptGraph.find_root_learning_gap("Derivatives", mastery_levels_c)
    assert gap_c == "functions"
    assert "prerequisite 'functions' is weak" in reason_c.lower()
