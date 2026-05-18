import argparse
import json
import logging
from pathlib import Path

from data_pipeline.preprocess import iter_standardized_attempts, write_jsonl

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "preprocessing.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def export_standardized_records(
    source_csv: str | Path,
    output_jsonl: str | Path,
    *,
    sample_json: str | Path | None = None,
    sample_size: int = 5,
) -> int:
    count = write_jsonl(source_csv, output_jsonl)
    logger.info("Wrote %s standardized records to %s", count, output_jsonl)

    if sample_json is not None:
        sample = [
            attempt.model_dump()
            for _, attempt in zip(range(sample_size), iter_standardized_attempts(source_csv))
        ]
        Path(sample_json).write_text(json.dumps(sample, indent=2), encoding="utf-8")
        logger.info("Wrote %s sample records to %s", len(sample), sample_json)

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess the educational dataset into standardized JSONL.")
    parser.add_argument("--input", default="students dataset.csv")
    parser.add_argument("--output", default="data/processed/student_attempts.jsonl")
    parser.add_argument("--sample-output", default="sample_outputs/standardized_attempts_sample.json")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.sample_output).parent.mkdir(parents=True, exist_ok=True)
    count = export_standardized_records(args.input, args.output, sample_json=args.sample_output)
    print(f"Wrote {count} standardized records to {args.output}")


if __name__ == "__main__":
    main()

