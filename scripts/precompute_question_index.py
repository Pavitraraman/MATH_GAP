import json
from pathlib import Path
from collections import defaultdict

def infer_difficulty(accuracy: float) -> str:
    if accuracy >= 0.8:
        return "easy"
    if accuracy >= 0.5:
        return "medium"
    return "hard"

def precompute_index():
    attempts_path = Path("data/processed/student_attempts.jsonl")
    output_path = Path("data/processed/question_index.json")

    print(f"Reading attempts from {attempts_path}...")
    
    # We group correctness by (skill, problem_id)
    by_problem = defaultdict(list)
    
    count = 0
    with attempts_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            attempt = json.loads(line)
            skill = attempt.get("skill")
            problem_id = attempt.get("problem_id")
            correct = attempt.get("correct")
            
            if skill and problem_id is not None and correct is not None:
                by_problem[(skill, str(problem_id))].append(int(correct))
                count += 1
                
    print(f"Processed {count} attempts. Building index...")
    
    index = defaultdict(list)
    for (skill, problem_id), scores in by_problem.items():
        accuracy = sum(scores) / len(scores)
        index[skill].append({
            "problem_id": problem_id,
            "empirical_accuracy": round(accuracy, 4),
            "difficulty": infer_difficulty(accuracy),
            "attempts_count": len(scores)
        })
        
    # Sort questions under each skill by empirical accuracy (easiest to hardest or hardest to easiest)
    for skill in index:
        index[skill].sort(key=lambda item: item["empirical_accuracy"])
        
    print(f"Index built with {len(index)} skills. Writing to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        json.dump(dict(index), out, indent=2, ensure_ascii=False)
        
    print("Precomputation completed successfully!")

if __name__ == "__main__":
    precompute_index()
