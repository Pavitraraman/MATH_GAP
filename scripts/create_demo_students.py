import json
from pathlib import Path

def create_demo_students():
    list_path = Path("data/processed/student_list.json")
    attempts_path = Path("data/processed/student_attempts_index.json")
    
    if not list_path.exists() or not attempts_path.exists():
        print("Error: Student index files not found in data/processed/. Run precomputation first.")
        return
        
    print("Loading existing student profile caches...")
    with list_path.open("r", encoding="utf-8") as f:
        student_list = json.load(f)
    with attempts_path.open("r", encoding="utf-8") as f:
        attempts_index = json.load(f)
        
    # --- 1. MODEL WEAK ALGEBRA STUDENT ---
    weak_algebra_attempts = []
    # Struggling with Interpreting Linear Equations (3/10 correct, 22s average time)
    for i in range(10):
        weak_algebra_attempts.append({
            "student_id": "demo_weak_algebra",
            "skill": "Interpreting Linear Equations",
            "correct": 1 if i in (2, 5, 8) else 0,
            "attempt_time": 21.0 + (i % 3) * 2.0,
            "timestamp": 1640995200 + i * 3600,
            "difficulty": "medium" if i < 6 else "easy",
            "problem_id": f"alg_weak_{i}"
        })
    # Struggling with Application: Compare Expressions (2/10 correct, 24.5s average time)
    for i in range(10):
        weak_algebra_attempts.append({
            "student_id": "demo_weak_algebra",
            "skill": "Application: Compare Expressions",
            "correct": 1 if i in (3, 7) else 0,
            "attempt_time": 23.0 + (i % 3) * 1.5,
            "timestamp": 1641031200 + i * 3600,
            "difficulty": "medium",
            "problem_id": f"alg_comp_{i}"
        })
    # Excelling in Properties Of Geometric Figures (9/10 correct, 11s average time)
    for i in range(10):
        weak_algebra_attempts.append({
            "student_id": "demo_weak_algebra",
            "skill": "Properties Of Geometric Figures",
            "correct": 1 if i != 4 else 0,
            "attempt_time": 9.5 + (i % 4) * 1.0,
            "timestamp": 1641067200 + i * 3600,
            "difficulty": "medium" if i < 5 else "hard",
            "problem_id": f"geo_weak_{i}"
        })
        
    # --- 2. MODEL ADVANCED GEOMETRY STUDENT ---
    advanced_geometry_attempts = []
    # Excelling in Pythagorean Theorem (9/10 correct, 7.5s average time)
    for i in range(10):
        advanced_geometry_attempts.append({
            "student_id": "demo_advanced_geometry",
            "skill": "Pythagorean Theorem",
            "correct": 1 if i != 6 else 0,
            "attempt_time": 6.5 + (i % 3) * 1.0,
            "timestamp": 1640995200 + i * 3600,
            "difficulty": "medium" if i < 4 else "hard",
            "problem_id": f"geo_pyth_{i}"
        })
    # Excelling in Transformations Rotations (10/10 correct, 6.2s average time)
    for i in range(10):
        advanced_geometry_attempts.append({
            "student_id": "demo_advanced_geometry",
            "skill": "Transformations Rotations",
            "correct": 1,
            "attempt_time": 5.5 + (i % 3) * 0.7,
            "timestamp": 1641031200 + i * 3600,
            "difficulty": "medium" if i < 3 else "hard",
            "problem_id": f"geo_rot_{i}"
        })
    # Excelling in Properties Of Geometric Figures (9/10 correct, 8.0s average time)
    for i in range(10):
        advanced_geometry_attempts.append({
            "student_id": "demo_advanced_geometry",
            "skill": "Properties Of Geometric Figures",
            "correct": 1 if i != 2 else 0,
            "attempt_time": 7.0 + (i % 4) * 0.8,
            "timestamp": 1641067200 + i * 3600,
            "difficulty": "hard",
            "problem_id": f"geo_fig_{i}"
        })
        
    # --- 3. MODEL SLOW LEARNER PROFILE ---
    slow_learner_attempts = []
    # Moderate accuracy on Multiplying Decimals but extremely slow (6/10 correct, 29.5s average time)
    for i in range(10):
        slow_learner_attempts.append({
            "student_id": "demo_slow_learner",
            "skill": "Multiplying Decimals",
            "correct": 1 if i in (0, 2, 4, 6, 8, 9) else 0,
            "attempt_time": 28.0 + (i % 4) * 1.5,
            "timestamp": 1640995200 + i * 3600,
            "difficulty": "easy" if i < 5 else "medium",
            "problem_id": f"slow_dec_{i}"
        })
    # Moderate accuracy on Proportion but slow (5/10 correct, 32.2s average time)
    for i in range(10):
        slow_learner_attempts.append({
            "student_id": "demo_slow_learner",
            "skill": "Proportion",
            "correct": 1 if i in (1, 3, 5, 7, 9) else 0,
            "attempt_time": 30.5 + (i % 3) * 2.0,
            "timestamp": 1641031200 + i * 3600,
            "difficulty": "medium",
            "problem_id": f"slow_prop_{i}"
        })
    # Moderate accuracy on Square Root but slow (6/10 correct, 28.0s average time)
    for i in range(10):
        slow_learner_attempts.append({
            "student_id": "demo_slow_learner",
            "skill": "Square Root",
            "correct": 1 if i in (0, 2, 3, 5, 7, 8) else 0,
            "attempt_time": 26.5 + (i % 3) * 1.5,
            "timestamp": 1641067200 + i * 3600,
            "difficulty": "easy" if i < 4 else "medium",
            "problem_id": f"slow_sqrt_{i}"
        })
        
    # --- INJECT INTO INDEXES IDEMPOTENTLY ---
    attempts_index["demo_weak_algebra"] = weak_algebra_attempts
    attempts_index["demo_advanced_geometry"] = advanced_geometry_attempts
    attempts_index["demo_slow_learner"] = slow_learner_attempts
    
    # Filter out old demo entries from list
    student_list = [s for s in student_list if s["student_id"] not in ("demo_weak_algebra", "demo_advanced_geometry", "demo_slow_learner")]
    
    # Insert new demo entries at the top of the student list
    demo_entries = [
        {"student_id": "demo_weak_algebra", "attempt_count": 30},
        {"student_id": "demo_advanced_geometry", "attempt_count": 30},
        {"student_id": "demo_slow_learner", "attempt_count": 30}
    ]
    
    student_list = demo_entries + student_list
    
    print(f"Writing student list with demo preloads to {list_path}...")
    with list_path.open("w", encoding="utf-8") as f:
        json.dump(student_list, f, indent=2, ensure_ascii=False)
        
    print(f"Writing student attempts with demo preloads to {attempts_path}...")
    with attempts_path.open("w", encoding="utf-8") as f:
        json.dump(attempts_index, f, ensure_ascii=False)
        
    print("Pre-computation and injection of sample demo students completed successfully!")

if __name__ == "__main__":
    create_demo_students()
