import logging

logger = logging.getLogger("math_gap.concept_graph")


class ConceptGraph:
    # Static Cognitive Directed Acyclic Graph (DAG) defining prerequisites: Prerequisite -> Target
    PREREQUISITES = {
        # Calculus track
        "limits": ["functions"],
        "derivatives": ["limits"],
        "integrals": ["derivatives"],
        
        # Algebra track
        "algebra foundations": ["arithmetic"],
        "equations": ["algebra foundations"],
        "quadratic equations": ["equations"],
        "systems of equations": ["equations"],
        
        # Arithmetic & Numbers
        "arithmetic": ["number systems"],
    }

    # Case-insensitive maps for safety
    _normalized_prereqs = {k.lower(): [v.lower() for v in val] for k, val in PREREQUISITES.items()}

    @classmethod
    def get_prerequisites(cls, concept: str) -> list[str]:
        """Returns direct prerequisite concepts for a given concept name."""
        concept_lower = concept.strip().lower()
        
        # Handle exact match or fuzzy skill matching
        for k, v in cls._normalized_prereqs.items():
            if k in concept_lower or concept_lower in k:
                return v
        return []

    @classmethod
    def find_root_learning_gap(
        cls,
        concept: str,
        mastery_levels: dict,
    ) -> tuple[str | None, str | None]:
        """
        Recursively analyzes a concept's prerequisites to pinpoint the root weak concept.
        
        Returns:
            (root_gap, prerequisite_reason)
            - root_gap: The deepest weak prerequisite blocking progression.
            - prerequisite_reason: A human-readable diagnostic sentence.
        """
        concept_lower = concept.strip().lower()
        prereqs = cls.get_prerequisites(concept_lower)
        
        if not prereqs:
            return None, None

        for prereq in prereqs:
            # Check if student has attempted and is weak in this prerequisite
            # We look up case-insensitively in mastery_levels
            prereq_mastery = None
            for key, val in mastery_levels.items():
                if key.lower().strip() == prereq:
                    prereq_mastery = val
                    break
            
            if prereq_mastery:
                accuracy = prereq_mastery.get("accuracy", 1.0)
                tier = prereq_mastery.get("tier", "New")
                
                # Flag as weak if accuracy < 70% or tier is Needs Revision
                if accuracy < 0.70 or tier in ("Needs Revision", "Learning"):
                    # Recurse deeper to see if this prerequisite itself has a prerequisite failure
                    deep_gap, deep_reason = cls.find_root_learning_gap(prereq, mastery_levels)
                    if deep_gap:
                        return deep_gap, deep_reason
                        
                    return prereq, f"Prerequisite '{prereq.title()}' is weak (Accuracy: {round(accuracy * 100)}%)"

        return None, None
