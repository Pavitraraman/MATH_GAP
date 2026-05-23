from pathlib import Path

from data_pipeline.student_analysis import analyze_student_dataset


def test_analyze_student_dataset_writes_output(tmp_path: Path) -> None:
    csv_path = tmp_path / "dataset.csv"
    csv_path.write_text(
        "\n".join(
            [
                "studentId,skill,timeTaken,correct,startTime,problemId",
                "1,fractions,10,0,100,p1",
                "1,fractions,20,1,101,p2",
                "1,fractions,30,0,102,p3",
                "1,geometry,15,1,103,p4",
            ]
        ),
        encoding="utf-8",
    )

    result = analyze_student_dataset(
        dataset_path=csv_path,
        student_id="1",
        output_dir=tmp_path / "processed_outputs",
        weak_threshold=0.7,
        min_attempts=2,
    )

    assert result["student_id"] == "1"
    assert result["weak_topics"][0]["skill"] == "Fractions"
    assert result["average_response_time"] == 18.75
    assert Path(result["output_path"]).exists()
