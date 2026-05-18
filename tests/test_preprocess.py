from data_pipeline.preprocess import normalize_column_name


def test_normalize_column_name() -> None:
    assert normalize_column_name("studentId") == "student_id"
    assert normalize_column_name("timeTaken") == "time_taken"
    assert normalize_column_name("confidence(BORED)") == "confidence_bored"

