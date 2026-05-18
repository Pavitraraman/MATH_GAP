import pandas as pd
import requests
import streamlit as st
from pathlib import Path

from data_pipeline.preprocess import iter_standardized_attempts
from data_pipeline.schemas import StandardizedAttempt
from recommendation_engine.performance import summarize_student_performance
from recommendation_engine.question_bank import build_question_index, recommend_questions

API_BASE_URL = "http://localhost:8000"
DATASET_PATH = Path("students dataset.csv")


@st.cache_data(show_spinner=False)
def load_attempts() -> list[StandardizedAttempt]:
    return list(iter_standardized_attempts(DATASET_PATH))


@st.cache_data(show_spinner=False)
def load_question_index() -> dict[str, list[dict]]:
    return build_question_index(load_attempts())


def fetch_json(path: str) -> dict | list | None:
    try:
        response = requests.get(f"{API_BASE_URL}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def post_json(path: str, payload: dict) -> tuple[dict | None, float | None, str | None]:
    try:
        response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=60)
        elapsed_ms = response.elapsed.total_seconds() * 1000
        response.raise_for_status()
        return response.json(), elapsed_ms, None
    except requests.RequestException as exc:
        return None, None, str(exc)


st.set_page_config(page_title="Math Gap Dashboard", layout="wide")
st.title("Math Gap Learning Analytics Dashboard")

attempts = load_attempts()
attempts_df = pd.DataFrame([attempt.model_dump() for attempt in attempts])
student_ids = sorted(attempts_df["student_id"].astype(str).unique())

selected_student = st.sidebar.selectbox(
    "Student ID",
    student_ids,
    index=student_ids.index("8") if "8" in student_ids else 0,
)
weak_threshold = st.sidebar.slider("Weak concept threshold", 0.0, 1.0, 0.7, 0.05)
min_attempts = st.sidebar.slider("Minimum attempts", 1, 20, 3)
target_difficulty = st.sidebar.selectbox("Recommended difficulty", ["hard", "medium", "easy"])

student_attempts = [attempt for attempt in attempts if attempt.student_id == str(selected_student)]
student_df = pd.DataFrame([attempt.model_dump() for attempt in student_attempts])
summary = summarize_student_performance(
    student_attempts,
    weak_threshold=weak_threshold,
    min_attempts=min_attempts,
)
summary_df = pd.DataFrame(summary["topics"])
weak_df = pd.DataFrame(summary["weak_topics"])

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Attempts", summary["total_attempts"])
metric_b.metric("Overall accuracy", f"{summary['overall_accuracy']:.1%}")
metric_c.metric("Weak concepts", len(summary["weak_topics"]))

st.subheader("Uploaded student data")
st.dataframe(student_df.head(200), use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Topic-wise accuracy")
    if not summary_df.empty:
        st.bar_chart(summary_df[["skill", "accuracy"]].set_index("skill"))
with right:
    st.subheader("Detected weak concepts")
    st.dataframe(weak_df, use_container_width=True)

st.subheader("Gemini analysis output")
if st.button("Run live Gemini analysis"):
    payload = {
        "student_id": summary["student_id"],
        "total_attempts": summary["total_attempts"],
        "overall_accuracy": summary["overall_accuracy"],
        "weak_topics": summary["weak_topics"],
    }
    result, latency_ms, error = post_json("/analysis/learning-gap", payload)
    if error:
        st.error(error)
    else:
        st.session_state["latest_analysis"] = result
        st.session_state["latest_latency_ms"] = latency_ms

if "latest_analysis" in st.session_state:
    live_left, live_right = st.columns([2, 1])
    with live_left:
        st.json(st.session_state["latest_analysis"])
    with live_right:
        st.metric("Live API latency", f"{st.session_state['latest_latency_ms']:.2f} ms")

st.subheader("Recommended questions")
question_index = load_question_index()
recommendations = []
for topic in summary["weak_topics"][:5]:
    recommendations.extend(
        recommend_questions(
            weak_topic=topic["skill"],
            grade_level=8,
            target_difficulty=target_difficulty,
            question_index=question_index,
            limit=3,
        )
    )
st.dataframe(pd.DataFrame(recommendations), use_container_width=True)

st.subheader("Latency metrics")
metrics = fetch_json("/metrics/dashboard")
if metrics:
    cols = st.columns(4)
    cols[0].metric("Avg LLM latency", f"{metrics['average_llm_latency_ms']:.2f} ms")
    cols[1].metric("Total LLM cost", f"${metrics['total_estimated_llm_cost_usd']:.6f}")
    cols[2].metric("Assessments", metrics["total_assessments"])
    cols[3].metric("Recommendations", metrics["total_recommendations"])
else:
    st.info("Start the FastAPI backend to view live service metrics.")

st.subheader("Prompt version and model response logs")
logs = fetch_json("/metrics/llm-logs?limit=20")
if logs:
    logs_df = pd.DataFrame(logs)
    st.dataframe(
        logs_df[["id", "model", "prompt_name", "prompt_version", "latency_ms", "status"]],
        use_container_width=True,
    )
    selected_log_id = st.selectbox("Inspect model response log", logs_df["id"].tolist())
    selected_log = next(item for item in logs if item["id"] == selected_log_id)
    st.caption(f"Prompt version used: {selected_log['prompt_name']} / {selected_log['prompt_version']}")
    st.json({"request": selected_log["request_json"], "response": selected_log["response_json"]})
else:
    st.info("No model response logs available yet, or the FastAPI backend is not running.")
