import json
from pathlib import Path
from collections import defaultdict

def precompute_student_attempts():
    attempts_path = Path("data/processed/student_attempts.jsonl")
    index_output_path = Path("data/processed/student_attempts_index.json")
    list_output_path = Path("data/processed/student_list.json")

    print(f"Reading attempts from {attempts_path}...")
    
    student_attempts = defaultdict(list)
    student_counts = defaultdict(int)
    
    count = 0
    with attempts_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            attempt = json.loads(line)
            student_id = attempt.get("student_id")
            if student_id:
                student_counts[student_id] += 1
                # To keep the file lightweight and high performance, cache up to 300 attempts per student
                if len(student_attempts[student_id]) < 300:
                    student_attempts[student_id].append(attempt)
                count += 1
                
    print(f"Processed {count} attempts. Preparing outputs...")
    
    # Create sorted student list
    student_list = []
    for student_id, attempt_count in student_counts.items():
        student_list.append({
            "student_id": student_id,
            "attempt_count": attempt_count
        })
    # Sort by attempt count descending
    student_list.sort(key=lambda x: x["attempt_count"], reverse=True)
    
    print(f"Writing student list to {list_output_path}...")
    with list_output_path.open("w", encoding="utf-8") as f:
        json.dump(student_list, f, indent=2, ensure_ascii=False)
        
    print(f"Writing student attempts index to {index_output_path}...")
    with index_output_path.open("w", encoding="utf-8") as f:
        json.dump(dict(student_attempts), f, ensure_ascii=False)
        
    print("Precomputation of student attempts completed successfully!")

if __name__ == "__main__":
    precompute_student_attempts()
