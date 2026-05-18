from pathlib import Path

from data_pipeline.preprocess import write_jsonl


if __name__ == "__main__":
    source = Path("students dataset.csv")
    output = Path("data/processed/student_attempts.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    count = write_jsonl(source, output)
    print(f"Wrote {count} standardized attempts to {output}")

