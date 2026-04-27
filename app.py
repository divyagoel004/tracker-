import streamlit as st
from utils.ui import CSS

st.set_page_config(
    page_title="SSC CGL Pro Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 📊 SSC CGL Pro")
    st.divider()
    page = st.radio("", [
        "🏠 Dashboard",
        "📝 Log Test",
        "❓ Log Questions",
        "📅 Daily Report",
        "📆 Weekly Report",
        "🔬 Deep Analysis",
        "🗓️ Study Scheduler",
        "📚 Question Bank",
        "📈 Charts",
    ], label_visibility="collapsed")
    st.divider()
    st.session_state["api_key"] = st.text_input(
        "🔑 API Key", type="password",
        value=st.session_state.get("api_key",""),
        placeholder="AIza...",
        help="Gemini API key — aistudio.google.com"
    )
    st.caption("All data stored locally in /data folder")

p = page.split(" ",1)[1].strip()
pages = {
    "Dashboard":     "pages/dashboard.py",
    "Log Test":      "pages/log_test.py",
    "Log Questions": "pages/log_questions.py",
    "Daily Report":  "pages/daily_report.py",
    "Weekly Report": "pages/weekly_report.py",
    "Deep Analysis": "pages/deep_analysis.py",
    "Study Scheduler":"pages/scheduler.py",
    "Question Bank": "pages/question_bank.py",
    "Charts":        "pages/charts.py",
}
if p in pages:
    exec(open(pages[p]).read())
