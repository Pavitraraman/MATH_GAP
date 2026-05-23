# 🧠 MATH-GAP: Why I built an adaptive, cognitive learning companion

> **Live Demo Link:** 🚀 [Try the Live App Here!](https://math-gap.streamlit.app) *(Replace this with your deployed Streamlit URL once you click the 1-minute deploy button below!)*

---

### 💡 The Backstory: Why existing AI tools failed my learning

When I wanted to learn advanced math online, I quickly realized that the tools we all rely on are fundamentally broken for actual learning:

*   **ChatGPT** is conversational but has **no structural memory of my brain**. It doesn't track what I struggled with yesterday, it has no concept of mathematical dependencies (it will happily try to teach you Derivatives even if you are failing Limits), and it just hands you the final answers. That gives you a nice "feeling" of understanding, but it prevents active recall and real learning.
*   **NotebookLM** is fantastic for summarizing complex PDFs, but **summarizing isn't learning**. It can't give you interactive quizzes that dynamically adapt in difficulty when you struggle, it doesn't know when a concept is fading from your memory, and it doesn't track your response speed to gauge your actual comprehension.

**So, I built MATH-GAP.** 

I wanted to transform raw study notes (PDFs, textbooks, slide decks) into a **continuous, self-healing cognitive companion**. It maps a student's mind as a structured concept graph, mathematically predicts memory decay over real-world hours, and recursively catches learning gaps before they derail a student.

---

## ⚡ How is MATH-GAP different from generic AI?

| Feature | ChatGPT | NotebookLM | 🧠 **MATH-GAP** (My Project) |
| :--- | :--- | :--- | :--- |
| **Cognitive Memory** | ❌ None (Conversational only) | ❌ None (Document-level only) | **Yes**: Tracks individual concept retention over time |
| **Prerequisite Mapping** | ❌ Assumes you know everything | ❌ Non-interactive reading | **Yes**: Uses a Directed Acyclic Graph (DAG) to isolate root gaps |
| **Active Testing** | ❌ Simple prompt answers | ❌ Static study guides | **Yes**: Generates dynamic quizzes that adapt based on your past mistakes |
| **Memory Decay** | ❌ None | ❌ None | **Yes**: Modeled mathematically using the **Ebbinghaus Forgetting Curve** |
| **Teacher Telemetry** | ❌ None | ❌ None | **Yes**: Direct DB-backed student attempt telemetry via **WebSockets** |

---

## 🛠️ The Engineering Challenges I Had to Solve

I wanted this to be a production-grade, multi-tenant learning infrastructure, not just a simple API wrapper. Here are the core layers I designed, wrote, and verified:

### 1. The Prerequisite Directed Acyclic Graph (DAG) Engine
In mathematics, learning is hierarchical. If you struggle with **Derivatives**, the root cause is almost always a weak understanding of **Limits**. 
Instead of just giving more Derivative questions, my custom DAG prerequisite engine recursively traces a student's history back to find the root blocker. If your score on *Limits* is low, the backend immediately flags this with a diagnostic alert: 
> 🛑 *"Struggling with Derivatives because Limits mastery is weak."*
And it redirects you to shore up your fundamentals first.

### 2. Spaced Repetition via the Ebbinghaus Forgetting Curve
I mathematically modeled the **Ebbinghaus Forgetting Curve** directly into the PostgreSQL/SQLite database schemas:
$$R = e^{-\frac{t}{S}}$$
Every time a student submits an answer, the backend instantly recalculates their **Memory Stability ($S$)**:
*   **Correct answer?** Stability grows exponentially: $S_{\text{new}} = S_{\text{old}} \cdot (1.5 + 2 \cdot \text{Accuracy})$.
*   **Incorrect answer?** Stability is cut in half ($S_{\text{new}} = S_{\text{old}} \cdot 0.5$).
The second a student's retention ($R$) drops below **$60\%$**, the topic automatically flags itself as `Needs Revision` and gets pushed to their daily practice planner.

### 3. A 100% Resilient, Self-Healing Fallback Engine
I didn't want this platform to break if the Google Gemini API went offline or if someone ran the app without an API key. 
I built a native Python regex and TF-IDF keyword parser. If the Gemini API call fails, the app **automatically self-heals**: it parses your uploaded PDF, extracts the math concepts (e.g., *Matrices*, *Algebra*), and populates high-quality practice quizzes using a preloaded fallback question bank. It is completely bulletproof.

### 4. Real-Time Telemetry & The Dropout Risk Index ($DRI$)
For teachers, I built an aggregated cohort dashboard. It doesn't just show grades—it calculates a student's **Dropout Risk Index ($DRI$)** based on their rolling accuracy, response hesitation, and memory decay rate:
$$DRI = 0.4 \cdot (1.0 - \text{Accuracy}_{\text{rolling}}) + 0.4 \cdot (1.0 - R) + 0.2 \cdot \min\left(1.0, \frac{\text{Time}_{\text{avg}}}{30.0}\right)$$
I also wired up FastAPI **WebSockets** so that student attempts are streamed *live* to the teacher's screen as they happen.

---

## 🚀 Get Your Own Running Link in 1 Minute (For Free!)

I wanted this project to be instantly accessible to recruiters. You can deploy it completely for free on **Streamlit Community Cloud** directly from your GitHub:

1. **Fork or Push** this repository to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub.
3. Click **"Create App"**, select this repository, set the Main file path to `dashboard/streamlit_app.py`, and click **Deploy**!
4. *That's it!* Because of the custom background server launcher I wrote, Streamlit Sharing will automatically spin up the FastAPI backend and database in the background inside the container. It runs 100% standalone out-of-the-box!

---

## 💻 Local Developer Guide

### 1. Zero-Setup Launch (Single-Terminal Mode)
I hate having to open three terminals to run a simple project. I updated the Streamlit runner to **automatically check for and start the FastAPI backend** on startup. You only need to run a single command:

```powershell
# 1. Activate your virtual environment
.venv\Scripts\activate

# 2. Run the cockpit (starts both the frontend and background backend!)
streamlit run dashboard/streamlit_app.py
```
Open **`http://localhost:8501`** in your browser and you're ready to go!

### 2. Recruiter Sandbox Mode (In-App)
I built a **🧪 Recruiter Sandbox Mode** directly into the sidebar so you can test the platform instantly without filling out long registration forms:
*   **Test as a Struggling Student**: Click *Sandbox: Weak Algebra Fundamentals*. Go to the Dynamic Practice Room, submit answers, and see your Ebbinghaus curve and DAG concept graphs adapt live.
*   **Test as a Teacher**: Click *Sandbox: Principal Teacher Account*. You can see student DRI indicators, average accuracy charts, and click `🔄 Poll Live Activity Feed` to see real-time mock student activity.

---

## 🧪 Verification & Automated Tests

I wrote a comprehensive automated test suite consisting of **44 backend tests** covering JWT auth, database isolation, Ebbinghaus decay formulas, and prerequisite DAG loops:

```powershell
.venv\Scripts\pytest -v
```

All 44 tests pass successfully with 100% green status.
