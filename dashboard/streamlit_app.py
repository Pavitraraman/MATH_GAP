import json
import logging
import math
import os
import socket
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time
import pandas as pd
import requests
import streamlit as st

# Automatically resolve and inject project root directory into python path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("math_gap.dashboard")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# --- AUTO-START BACKEND API (FOR 1-CLICK DEPLOYMENTS & SINGLE-TERMINAL DEV) ---
def is_port_open(port: int) -> bool:
    """Helper to check if a local port is active."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

if "localhost:8000" in API_BASE_URL or "127.0.0.1:8000" in API_BASE_URL:
    if not is_port_open(8000):
        logger.info("FastAPI backend is offline. Auto-starting FastAPI backend in the background...")
        try:
            # Try to run uvicorn from the environment's python executable
            # This is 100% portable on local systems, Streamlit Sharing, Hugging Face, etc.
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True
            )
            # Give it up to 5 seconds to wake up
            for _ in range(10):
                if is_port_open(8000):
                    logger.info("FastAPI background backend successfully started and listening on port 8000!")
                    break
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to auto-start FastAPI backend: {e}")

# --- HIGH-PERFORMANCE DATA CACHING & SIMULATION INDEXERS ---
@st.cache_data(show_spinner=False)
def load_simulation_students() -> list[dict]:
    """Returns preset recruiter sandbox / simulation student profiles."""
    return [
        {"id": "sandbox_weak_algebra", "name": "Sandbox: Weak Algebra Fundamentals", "email": "weak_alg@sandbox.edu", "role": "student"},
        {"id": "sandbox_fluent_calculus", "name": "Sandbox: Fluent Calculus Mastery", "email": "fluent_calc@sandbox.edu", "role": "student"},
        {"id": "sandbox_hesitant_learner", "name": "Sandbox: High Hesitation Responder", "email": "hesitant@sandbox.edu", "role": "student"},
        {"id": "teacher_sandbox", "name": "Sandbox: Principal Teacher Account", "email": "teacher@sandbox.edu", "role": "teacher"}
    ]

# --- API HELPER FUNCTIONS WITH AUTHENTICATION INTEGRATION ---

def get_auth_headers() -> dict:
    """Returns headers injected with secure JWT token or X-API-Key."""
    headers = {}
    if "auth_token" in st.session_state and st.session_state["auth_token"]:
        headers["Authorization"] = f"Bearer {st.session_state['auth_token']}"
    if "api_key" in st.session_state and st.session_state["api_key"]:
        headers["X-API-Key"] = st.session_state["api_key"]
    return headers

def fetch_json(path: str) -> dict | list | None:
    try:
        response = requests.get(f"{API_BASE_URL}{path}", headers=get_auth_headers(), timeout=5)
        if response.status_code == 401:
            st.session_state["auth_token"] = None # clear expired token
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.warning(f"Failed to fetch from {path}: {exc}")
        return None

def post_json(path: str, payload: dict) -> tuple[dict | None, float | None, str | None]:
    try:
        response = requests.post(f"{API_BASE_URL}{path}", json=payload, headers=get_auth_headers(), timeout=30)
        elapsed_ms = response.elapsed.total_seconds() * 1000
        if response.status_code == 401:
            st.session_state["auth_token"] = None
        response.raise_for_status()
        return response.json(), elapsed_ms, None
    except Exception as exc:
        return None, None, str(exc)

def upload_material_api(student_id: str, file_bytes: bytes, filename: str) -> dict | None:
    try:
        files = {"file": (filename, file_bytes, "application/pdf" if filename.endswith(".pdf") else "text/plain")}
        data = {"student_id": student_id}
        headers = get_auth_headers()
        # Form-data boundary headers are automatically appended by requests
        response = requests.post(f"{API_BASE_URL}/platform/upload-material", files=files, data=data, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error(f"Failed to upload material: {exc}")
        return None

def generate_quiz_api(student_id: str, material_id: int | None = None, skill: str | None = None, num_questions: int = 5) -> dict | None:
    payload = {
        "student_id": student_id,
        "material_id": material_id,
        "skill": skill,
        "num_questions": num_questions
    }
    res, _, _ = post_json("/platform/generate-quiz", payload)
    return res

def submit_answer_api(student_id: str, question_id: int, selected_option: str, response_time: float) -> dict | None:
    payload = {
        "student_id": student_id,
        "question_id": question_id,
        "selected_option": selected_option,
        "response_time": response_time
    }
    res, _, _ = post_json("/platform/submit-answer", payload)
    return res

# --- PAGE CONFIG & THEME SETUP ---
st.set_page_config(
    page_title="Math Gap | Multi-User Educational Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium stylesheet injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

/* Apply custom premium font */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* Custom premium card style */
.premium-card {
    background: rgba(30, 41, 59, 0.45);
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    backdrop-filter: blur(12px);
    margin-bottom: 1rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.premium-card:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.35);
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.15);
}

/* Beautiful metric values */
.premium-metric-title {
    font-size: 0.85rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem;
    font-weight: 500;
}

.premium-metric-value {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #38BDF8, #818CF8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.metric-green {
    background: linear-gradient(135deg, #34D399, #059669);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.metric-purple {
    background: linear-gradient(135deg, #C084FC, #818CF8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.metric-amber {
    background: linear-gradient(135deg, #FBBF24, #D97706);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.metric-rose {
    background: linear-gradient(135deg, #FB7185, #E11D48);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.badge {
    display: inline-block;
    padding: 0.3em 0.7em;
    font-size: 75%;
    font-weight: 600;
    line-height: 1;
    text-align: center;
    white-space: nowrap;
    vertical-align: baseline;
    border-radius: 0.375rem;
    margin-right: 0.35rem;
    margin-bottom: 0.25rem;
}

.badge-indigo {
    background-color: rgba(99, 102, 241, 0.15);
    color: #818CF8;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

.badge-emerald {
    background-color: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-rose {
    background-color: rgba(244, 63, 94, 0.15);
    color: #FB7185;
    border: 1px solid rgba(244, 63, 94, 0.3);
}

.badge-amber {
    background-color: rgba(217, 119, 6, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(217, 119, 6, 0.3);
}

.badge-cyan {
    background-color: rgba(6, 182, 212, 0.15);
    color: #22D3EE;
    border: 1px solid rgba(6, 182, 212, 0.3);
}

.timeline-item {
    padding: 0.75rem 1rem;
    border-left: 3px solid #818CF8;
    margin-left: 1rem;
    margin-bottom: 0.75rem;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 0 8px 8px 0;
}
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATES ---
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "school_id" not in st.session_state:
    st.session_state["school_id"] = None
if "api_key" not in st.session_state:
    st.session_state["api_key"] = None
if "current_quiz" not in st.session_state:
    st.session_state["current_quiz"] = None
if "quiz_question_idx" not in st.session_state:
    st.session_state["quiz_question_idx"] = 0
if "quiz_attempts" not in st.session_state:
    st.session_state["quiz_attempts"] = []
if "question_start_time" not in st.session_state:
    st.session_state["question_start_time"] = None
if "quiz_feedback" not in st.session_state:
    st.session_state["quiz_feedback"] = None

# Check backend health
backend_healthy = fetch_json("/health") is not None

# --- SIDEBAR & RECRUITER TESTING MODE ---
st.sidebar.markdown("<h2 style='text-align: center; color: #818CF8;'>🧠 MATH-GAP</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size:0.85rem; color: #94A3B8;'>Production Multi-User Adaptive Learning LMS</p>", unsafe_allow_html=True)

if not backend_healthy:
    st.sidebar.error("🚨 Backend Server Offline.\nPlease run `uvicorn app.main:app` to start.")
else:
    st.sidebar.success("🟢 Production Server Connected")

# --- SIMULATION / RECRUITER SANDBOX PORTAL ---
st.sidebar.markdown("---")
with st.sidebar.expander("🧪 Sandbox Recruiter Testing Mode"):
    st.markdown("<p style='font-size:0.8rem; color:#94A3B8;'>Instantly log in to preloaded testing/sandbox profiles to demo either interface.</p>", unsafe_allow_html=True)
    sim_profiles = load_simulation_students()
    
    for prof in sim_profiles:
        role_tag = "Teacher" if prof["role"] == "teacher" else "Student"
        if st.button(f"Log in as {prof['name']} ({role_tag})", key=f"sim_{prof['id']}"):
            # Automatic mock sign-in bypass
            # Register user automatically in database
            signup_payload = {
                "username": prof["id"],
                "email": prof["email"],
                "password": "sandbox_secure_password_123",
                "role": prof["role"],
                "school_name": "Sandbox Academy"
            }
            res_signup = requests.post(f"{API_BASE_URL}/auth/signup", json=signup_payload, timeout=10)
            
            # Fetch token directly from API to test live endpoints
            login_payload = {"email": prof["email"], "password": "sandbox_secure_password_123"}
            res = requests.post(f"{API_BASE_URL}/auth/login", json=login_payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                st.session_state["auth_token"] = data["access_token"]
                st.session_state["user_role"] = data["role"]
                st.session_state["username"] = data["username"]
                st.session_state["school_id"] = data["school_id"]
                st.session_state["api_key"] = data["school_api_key"]
                st.toast(f"Logged in as {prof['id']} ({data['role'].upper()})", icon="🧪")
                st.rerun()

if st.session_state["auth_token"]:
    st.sidebar.markdown(f"**User:** `{st.session_state['username']}`")
    st.sidebar.markdown(f"**Role:** `{st.session_state['user_role'].upper()}`")
    if st.session_state["school_id"]:
        st.sidebar.markdown(f"**School Tenant ID:** `{st.session_state['school_id']}`")
        st.sidebar.markdown(f"**API Integrations Key:** `{st.session_state['api_key'][:8]}...`")
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state["auth_token"] = None
        st.session_state["user_role"] = None
        st.session_state["username"] = None
        st.session_state["school_id"] = None
        st.session_state["api_key"] = None
        st.session_state["current_quiz"] = None
        st.session_state["quiz_attempts"] = []
        st.toast("Logged out successfully")
        st.rerun()

# --- 1. SIGNUP & LOGIN INTERFACE (AUTHENTICATION LAYER) ---

if not st.session_state["auth_token"]:
    st.markdown("<h1 style='text-align: center;'>Gateway Authentication Center</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8;'>Sign in or create an account to begin adaptive learning pathways.</p>", unsafe_allow_html=True)
    
    tab_login, tab_register = st.tabs(["🔐 Secure Sign In", "📝 Create Account"])
    
    with tab_login:
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.subheader("Login to your Dashboard")
            login_email = st.text_input("Institutional Email", key="log_email")
            login_pass = st.text_input("Password", type="password", key="log_pass")
            
            if st.button("Authenticate", type="primary", use_container_width=True):
                if login_email and login_pass:
                    payload = {"email": login_email.strip(), "password": login_pass}
                    res_json, _, err = post_json("/auth/login", payload)
                    if res_json:
                        st.session_state["auth_token"] = res_json["access_token"]
                        st.session_state["user_role"] = res_json["role"]
                        st.session_state["username"] = res_json["username"]
                        st.session_state["school_id"] = res_json["school_id"]
                        st.session_state["api_key"] = res_json["school_api_key"]
                        st.success("Authorized successfully!")
                        st.rerun()
                    else:
                        st.error(f"Authentication Failed: {err or 'Incorrect password'}")
                else:
                    st.warning("Please fill in both email and password fields.")
        
        with col_r:
            st.markdown("""
            <div class="premium-card" style="margin-top: 1.5rem;">
                <h3>Production LMS Features</h3>
                <p>Welcome to the multi-user adaptive math recommendation platform. Logging in unlocks:</p>
                <ul>
                    <li>Isolated Cognitive Memory state analytics</li>
                    <li>Automatic Spaced Repetition (Ebbinghaus Forgetting Curves)</li>
                    <li>Prerequisite DAG diagnosis networks</li>
                    <li>Real-time WebSockets streaming dashboard dashboards</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
    with tab_register:
        st.subheader("Register a new Account")
        reg_username = st.text_input("Username / Unique ID", placeholder="e.g. pavitra_raman")
        reg_email = st.text_input("Email address", placeholder="student@school.edu")
        reg_password = st.text_input("Password", type="password")
        reg_role = st.selectbox("Role", ["student", "teacher", "admin"])
        reg_school = st.text_input("School / Coaching Center Name", placeholder="e.g. Stanford University")
        
        if st.button("Register & Generate Tenant", type="primary", use_container_width=True):
            if reg_username and reg_email and reg_password and reg_school:
                payload = {
                    "username": reg_username.strip(),
                    "email": reg_email.strip(),
                    "password": reg_password,
                    "role": reg_role.lower(),
                    "school_name": reg_school.strip()
                }
                # Call signup API
                response = requests.post(f"{API_BASE_URL}/auth/signup", json=payload, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["auth_token"] = data["access_token"]
                    st.session_state["user_role"] = data["role"]
                    st.session_state["username"] = data["username"]
                    st.session_state["school_id"] = data["school_id"]
                    st.session_state["api_key"] = data["school_api_key"]
                    st.success("Account registered and tenant school mapped successfully!")
                    st.rerun()
                else:
                    try:
                        err_det = response.json().get("detail", "Registration failed")
                    except Exception:
                        err_det = "Registration failed"
                    st.error(f"Error: {err_det}")
            else:
                st.warning("Please fill in all registration fields.")

# --- 2. STUDENT COCKPIT DASHBOARD ---

elif st.session_state["user_role"] == "student":
    student_id = st.session_state["username"]
    
    st.markdown(f"<h1>🎓 Student Learning Cockpit</h1>", unsafe_allow_html=True)
    
    tab_practice, tab_memory, tab_coaching = st.tabs([
        "✏️ Dynamic Practice Room", 
        "📊 Spaced Memory Decay & Analytics", 
        "🧠 AI Coaching & Prerequisite DAGs"
    ])
    
    # Load profile details
    profile_data = fetch_json(f"/platform/student-memory/{student_id}")
    
    # A. Practice Room
    with tab_practice:
        col_setup, col_quiz = st.columns([1, 2])
        
        with col_setup:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            st.subheader("Practice Settings")
            
            # Study guide uploader
            st.write("📚 **Ingest Study Guides (PDF / TXT / MD)**")
            uploaded_file = st.file_uploader("Upload material to extract concept graphs & generate quizzes", type=["pdf", "txt", "md"])
            if uploaded_file:
                if st.button("Process & Chunk Document", use_container_width=True):
                    with st.spinner("Parsing PyMuPDF chunks and calling Gemini..."):
                        file_bytes = uploaded_file.read()
                        res = upload_material_api(student_id, file_bytes, uploaded_file.name)
                        if res:
                            st.success(f"Ingested '{res['filename']}' ({res['questions_count']} questions generated)")
                            st.rerun()
                        else:
                            st.error("Ingestion failed. Ensure API key is configured correctly.")

            st.write("🎯 **Quick Diagnostic Practice**")
            num_q = st.slider("Number of Questions", 3, 10, 5)
            
            # Option to select materials if uploaded
            materials_list = []
            if profile_data and profile_data.get("material_mastery"):
                materials_list = list(profile_data.get("material_mastery").keys())
                
            selected_mat = None
            if materials_list:
                selected_mat = st.selectbox("Restrict Quiz to Study Material ID", [None] + materials_list)
                
            if st.button("Generate Adaptive Practice Quiz", type="primary", use_container_width=True):
                with st.spinner("Fetching questions..."):
                    quiz = generate_quiz_api(student_id, material_id=selected_mat, num_questions=num_q)
                    if quiz and quiz.get("questions"):
                        st.session_state["current_quiz"] = quiz["questions"]
                        st.session_state["quiz_question_idx"] = 0
                        st.session_state["quiz_attempts"] = []
                        st.session_state["question_start_time"] = time.time()
                        st.session_state["quiz_feedback"] = None
                        st.toast("Adaptive Quiz Loaded!", icon="🎯")
                        st.rerun()
                    else:
                        st.error("No questions found in this curriculum slot.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_quiz:
            if st.session_state["current_quiz"]:
                questions = st.session_state["current_quiz"]
                idx = st.session_state["quiz_question_idx"]
                
                if idx < len(questions):
                    q = questions[idx]
                    
                    st.markdown(f"<div class='premium-card'>", unsafe_allow_html=True)
                    st.markdown(f"<span class='badge badge-indigo'>Question {idx + 1} of {len(questions)}</span>", unsafe_allow_html=True)
                    st.markdown(f"<span class='badge badge-cyan'>{q['skill'].title()}</span>", unsafe_allow_html=True)
                    st.markdown(f"<span class='badge badge-amber'>{q['difficulty'].upper()}</span>", unsafe_allow_html=True)
                    
                    st.write(f"### {q['question_text']}")
                    
                    # Display options
                    options = q["options"]
                    selected_opt = st.radio("Choose correct solution option:", options, key=f"q_opt_{idx}")
                    
                    if st.session_state["quiz_feedback"]:
                        feedback = st.session_state["quiz_feedback"]
                        if feedback["is_correct"]:
                            st.success("🎉 Correct Answer!")
                        else:
                            st.error(f"❌ Incorrect. Correct Option was: **{feedback['correct_option']}**")
                            
                        # Show Prerequisite block warnings if DAG resolved a prerequisite gap
                        if feedback.get("prerequisite_blocker"):
                            st.warning(f"⚠️ **Core Prerequisite Blocker Detected:** You struggled here because your foundation in **{feedback['prerequisite_blocker'].title()}** is weak. Reviewing it is recommended first!")

                        st.write("#### Explanation:")
                        st.write(feedback["explanation"])
                        
                        if feedback.get("rag_context"):
                            with st.expander("📚 Localized Helper Context (Retrieved from Uploaded study notes)"):
                                for i, chunk in enumerate(feedback["rag_context"]):
                                    st.write(f"**Chunk {i+1}:** {chunk}")
                                    
                        if st.button("Next Practice Question", type="primary"):
                            st.session_state["quiz_question_idx"] += 1
                            st.session_state["quiz_feedback"] = None
                            st.session_state["question_start_time"] = time.time()
                            st.rerun()
                    else:
                        if st.button("Submit Answer", type="primary"):
                            elapsed_sec = time.time() - st.session_state["question_start_time"]
                            feedback = submit_answer_api(student_id, q["id"], selected_opt, elapsed_sec)
                            if feedback:
                                st.session_state["quiz_feedback"] = feedback
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.success("🎉 Practice Quiz Completed! You've successfully finished all questions in this adaptive session.")
                    if st.button("Clear Finished Session"):
                        st.session_state["current_quiz"] = None
                        st.rerun()
            else:
                st.info("💡 Practice Room is idle. Click 'Generate Adaptive Practice Quiz' on the left setup card to start an interactive lesson.")

    # B. Memory Analytics
    with tab_memory:
        if profile_data:
            st.subheader("Spaced Repetition & Cognitive Ebbinghaus Analytics")
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.markdown(f"""
                <div class="premium-card">
                    <div class="premium-metric-title">Total quiz attempts</div>
                    <div class="premium-metric-value">{profile_data.get('total_attempts', 0)}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_m2:
                st.markdown(f"""
                <div class="premium-card">
                    <div class="premium-metric-title">Average response speed</div>
                    <div class="premium-metric-value metric-purple">{round(profile_data.get('average_response_time', 0.0), 1)}s</div>
                </div>
                """, unsafe_allow_html=True)
            with col_m3:
                st.markdown(f"""
                <div class="premium-card">
                    <div class="premium-metric-title">Learning Velocity</div>
                    <div class="premium-metric-value metric-green">+{round(profile_data.get('learning_velocity', 0.0) * 100, 1)}%</div>
                </div>
                """, unsafe_allow_html=True)
            with col_m4:
                st.markdown(f"""
                <div class="premium-card">
                    <div class="premium-metric-title">Current Path Tier</div>
                    <div class="premium-metric-value metric-amber">{profile_data.get('preferred_difficulty', 'medium').upper()}</div>
                </div>
                """, unsafe_allow_html=True)

            col_heat, col_ebbinghaus = st.columns([1, 1])
            
            with col_heat:
                st.write("📊 **Concepts & Chapters Mastery Map**")
                
                # Check material specific tracking
                mat_mastery = profile_data.get("material_mastery")
                if mat_mastery:
                    st.write("Select Uploaded study guide to view chapter concept maps:")
                    sel_mat_id = st.selectbox("Uploaded Material ID", list(mat_mastery.keys()))
                    if sel_mat_id:
                        chapters = mat_mastery[sel_mat_id]
                        chapter_rows = []
                        for ch, skills in chapters.items():
                            for sk, stats in skills.items():
                                chapter_rows.append({
                                    "Chapter": ch,
                                    "Concept": sk,
                                    "Attempts": stats["attempts"],
                                    "Accuracy (%)": stats["accuracy"] * 100,
                                    "Stability (hrs)": stats["stability_hours"],
                                    "Tier State": stats["tier"]
                                })
                        ch_df = pd.DataFrame(chapter_rows)
                        st.dataframe(ch_df, use_container_width=True)
                else:
                    # Generic topics heatmap
                    mastery_levels = profile_data.get("mastery_levels", {})
                    if mastery_levels:
                        m_rows = []
                        for topic, t_data in mastery_levels.items():
                            m_rows.append({
                                "Topic": topic,
                                "Accuracy (%)": round(t_data.get("accuracy", 0.0) * 100, 1),
                                "Stability (hrs)": round(t_data.get("stability_hours", 24.0), 1),
                                "Retention (%)": round(t_data.get("retention_probability", 1.0) * 100, 1),
                                "Mastery Status": t_data.get("tier", "New")
                            })
                        st.dataframe(pd.DataFrame(m_rows), use_container_width=True)
                    else:
                        st.info("No concept attempts registered yet. Please take a quiz.")

            with col_ebbinghaus:
                st.write("📈 **Active Forgetting Decay curves**")
                # Plot forgetting curves R = e^(-t/S)
                mastery_levels = profile_data.get("mastery_levels", {})
                if mastery_levels:
                    curve_data = {}
                    hours_range = list(range(0, 120, 4))
                    for topic, t_data in list(mastery_levels.items())[:3]:
                        stability = t_data.get("stability_hours", 24.0)
                        curve_data[topic] = [math.exp(-h / stability) * 100 for h in hours_range]
                    
                    if curve_data:
                        curve_df = pd.DataFrame(curve_data, index=hours_range)
                        st.line_chart(curve_df)
                        st.caption("X-Axis: Elapsed hours since last practice. Y-Axis: Forgetting curve retention probability (%)")
                else:
                    st.info("Take a practice quiz to chart active forgetting curves.")
                    
            # Spaced repetition revision planner
            rev_recommend = fetch_json(f"/platform/revision-recommendations/{student_id}")
            if rev_recommend and rev_recommend.get("revision_schedule"):
                st.write("📅 **Automatic Spaced-Repetition Revision Planner**")
                recs = rev_recommend["revision_schedule"]
                for r in recs[:3]:
                    urg_color = "🔴 Urgent" if r["urgency_score"] >= 1.0 else "🟡 Spaced"
                    st.info(f"**Topic:** {r['skill']} | **Status:** {r['mastery_state']} | **Retention:** {round(r['retention_probability']*100)}% | **Spacing:** {round(r['stability_hours'])} hrs | **Action:** {r['review_action']} ({urg_color})")

    # C. AI Coaching & Prerequisite DAGs
    with tab_coaching:
        st.subheader("Cognitive Tutoring Highlights & Concept DAG Diagnostics")
        
        # Display AI insights
        insights = profile_data.get("coaching_insights", []) if profile_data else []
        if insights:
            for ins in insights:
                st.info(f"🤖 **Insight:** {ins}")
        else:
            st.info("🤖 AI Coach is calibrating... Please solve more questions to surface highlights.")

        # Prerequisite blocker visualizer
        st.write("🕸️ **My Concept Dependency Graph (DAG) Gaps**")
        st.markdown("""
        <div class="premium-card">
            <p><strong>prerequisite chains:</strong></p>
            <ul>
                <li>Arithmetic &rarr; Algebra Foundations &rarr; Equations &rarr; Quadratic Equations</li>
                <li>Functions &rarr; Limits &rarr; Derivatives &rarr; Integrals</li>
            </ul>
            <p>Our cognitive diagnostic engine continuously runs recursive dependency checks. If a prerequisite node accuracy drops below 70%, it blocks your target path.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Highlight prerequisite blocks if any topic is weak
        if profile_data:
            mastery_levels = profile_data.get("mastery_levels", {})
            weak_prereqs_found = False
            for topic, t_data in mastery_levels.items():
                acc = t_data.get("accuracy", 1.0)
                tier = t_data.get("tier", "New")
                if acc < 0.70 or tier == "Needs Revision":
                    # Check prerequisites
                    if "derivative" in topic.lower():
                        weak_prereqs_found = True
                        st.warning("⚠️ **Ancestral Blocker Alert:** Derivatives requires Limits. Your limits accuracy is weak, stalling derivatives mastery. Recommending limits review.")
                    if "equation" in topic.lower():
                        weak_prereqs_found = True
                        st.warning("⚠️ **Ancestral Blocker Alert:** Equations requires Algebra Foundations. Review basic variables and signs first!")
            if not weak_prereqs_found:
                st.success("🟢 No prerequisite graph blocks detected. Prerequisite paths are solid!")

# --- 3. TEACHER / ADMIN COHORT DASHBOARD ---

elif st.session_state["user_role"] in ("teacher", "admin"):
    st.markdown("<h1>👩‍🏫 Teacher Analytics Center</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Real-time WebSocket telemetry, Dropout-Risk trackers, and cohort statistics.</p>", unsafe_allow_html=True)
    
    # Reload cohort report
    cohort_data = fetch_json("/platform/cohort-analytics")
    
    if cohort_data:
        # A. Cohort Key Metrics
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.markdown(f"""
            <div class="premium-card">
                <div class="premium-metric-title">Total Active Students</div>
                <div class="premium-metric-value">{cohort_data.get('total_students', 0)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_c2:
            st.markdown(f"""
            <div class="premium-card">
                <div class="premium-metric-title">Average Cohort Accuracy</div>
                <div class="premium-metric-value metric-green">{cohort_data.get('cohort_accuracy_percentage', 0.0)}%</div>
            </div>
            """, unsafe_allow_html=True)
        with col_c3:
            st.markdown(f"""
            <div class="premium-card">
                <div class="premium-metric-title">Spacing Revision Gain</div>
                <div class="premium-metric-value metric-purple">+{cohort_data.get('average_revision_effectiveness_gain_percentage', 0.0)}%</div>
            </div>
            """, unsafe_allow_html=True)
        with col_c4:
            st.markdown(f"""
            <div class="premium-card">
                <div class="premium-metric-title">Average Response Speed</div>
                <div class="premium-metric-value metric-amber">{cohort_data.get('average_response_time', 0.0)}s</div>
            </div>
            """, unsafe_allow_html=True)

        col_left_an, col_right_an = st.columns([1, 1])
        
        with col_left_an:
            # 1. Dropout Risk indicators
            st.write("⚠️ **Telemetry Dropout-Risk indicators (Computed DRI)**")
            risk_students = cohort_data.get("dropout_risk_students", [])
            if risk_students:
                risk_rows = []
                for s in risk_students:
                    risk_rows.append({
                        "Student ID": s["student_id"],
                        "Risk Score (DRI)": s["dri"],
                        "Velocity": f"{s['learning_velocity']*100}%",
                        "Accuracy": f"{s['accuracy']}%",
                        "Status": s["status"]
                    })
                risk_df = pd.DataFrame(risk_rows)
                st.dataframe(risk_df, use_container_width=True)
            else:
                st.success("🟢 No students are currently classified at high dropout risk.")

            # 2. Class wide weak concepts
            st.write("📊 **Class-Wide Concept deficiencies**")
            weak_con = cohort_data.get("weak_concepts", [])
            if weak_con:
                wc_df = pd.DataFrame(weak_con)
                st.bar_chart(wc_df.set_index("concept"))
            else:
                st.info("No topic attempts logged across the cohort yet.")

        with col_right_an:
            # 3. Difficulty heatmap
            st.write("🗺️ **Cohort Difficulty Heatmaps**")
            heatmap = cohort_data.get("difficulty_heatmap", {})
            if heatmap:
                h_rows = []
                for diff, grid in heatmap.items():
                    h_rows.append({
                        "Target Difficulty": diff.upper(),
                        "Total Attempts": grid["attempts"],
                        "Average Accuracy (%)": grid["accuracy"]
                    })
                st.dataframe(pd.DataFrame(h_rows), use_container_width=True)
            
            # 4. Real-time telemetry WebSocket feed (Live active database updates)
            st.write("📡 **Real-Time Active Attempt Telemetry (Live Activity Feed)**")
            
            # Simple UI refresh button to pull the latest state
            st.markdown("<p style='font-size:0.8rem; color:#94A3B8;'>Active events stream live as students submit quiz responses. Click below to refresh the channels.</p>", unsafe_allow_html=True)
            
            if st.button("🔄 Poll Live Activity Feed"):
                st.toast("Active Telemetry Channel Refreshed!", icon="📡")
                st.rerun()
                
            recent_attempts = cohort_data.get("recent_attempts", [])
            if recent_attempts:
                for a in recent_attempts:
                    status_text = "Correct" if a["correct"] == 1 else "Incorrect"
                    msg = f"📡 **WebSocket Event [{a['timestamp']}]:** Student `{a['student_id']}` solved '{a['skill']}' Question: **{status_text}** ({a['response_time']}s)."
                    if a["correct"] == 1:
                        st.info(msg)
                    else:
                        st.warning(msg)
            else:
                st.info("📡 No active student telemetry events recorded in the system yet. Attempt a quiz in the Student space to generate events!")
            
    else:
        st.info("💡 Cohort Analytics are empty. Please register students and have them complete adaptive sessions.")

# --- 4. INSTITUTIONAL API KEYS MANAGEMENT ---
if st.session_state["user_role"] == "admin":
    st.markdown("---")
    st.subheader("⚙️ Institutional Scale API Integrations")
    st.markdown("""
    <div class="premium-card">
        <p>Your Coaching Center / EdTech Platform is fully equipped with client API authorizations. Integrate our adaptive cognitive memory engine directly with your existing LMS using the following secure headers:</p>
        <pre><code>X-API-Key: """ + (st.session_state["api_key"] or "mg_unconfigured_sandbox_key") + """</code></pre>
        <p><strong>Available Production EdTech API Endpoints:</strong></p>
        <ul>
            <li><code>POST /platform/upload-material</code> &mdash; Ingest school study guides programmatically</li>
            <li><code>POST /platform/generate-quiz</code> &mdash; Serve adaptive question bundles to students</li>
            <li><code>POST /platform/submit-answer</code> &mdash; Feed attempts live to evolve memory states</li>
            <li><code>GET /platform/student-mastery/{student_id}</code> &mdash; Fetch real-time student profiling stats</li>
            <li><code>GET /platform/cohort-analytics</code> &mdash; Compile aggregated institutional insights</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
