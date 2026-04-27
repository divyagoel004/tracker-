import streamlit as st
from utils.db import all_tests, all_questions, get_profile, cache_report, get_cached
from utils.claude_api import deep_analysis_prompt, stream

st.markdown('<p class="page-title">🔬 Deep Analysis</p><p class="page-sub">On-demand comprehensive analysis across all your data — full diagnosis, growth curve, exam strategy.</p>', unsafe_allow_html=True)

profile = get_profile()
tests   = all_tests()
qs      = all_questions()

if not profile:
    st.warning("Set up profile first."); st.stop()
if len(tests) < 2:
    st.info("Log at least 2 tests to run a deep analysis."); st.stop()

from utils.db import test_score, section_stats, topic_stats
from utils.ui import SECTION_FULL, SECTION_ICON, score_color, acc_badge

scores = [test_score(t) for t in tests]
target = profile.get("target_score",160)

# Quick stats
c1,c2,c3,c4 = st.columns(4)
def kpi(col,l,v,sub="",color=None):
    col.markdown(f'<div class="kpi"><div class="kpi-label">{l}</div><div class="kpi-val" style="color:{color or "inherit"}">{v}</div><div class="kpi-sub">{sub}</div></div>',unsafe_allow_html=True)
kpi(c1,"Tests Analysed",len(tests),f"across {len(set(t.get('date','') for t in tests))} days")
kpi(c2,"Current Avg",f"{round(sum(scores)/len(scores),1)}/200","",score_color(sum(scores)/len(scores)))
kpi(c3,"Target",f"{target}/200","")
kpi(c4,"Questions in Bank",len(qs))

# Topic health heatmap (pre-AI)
st.divider()
st.markdown("### 🔥 Topic Health Map (all time)")
ts = topic_stats(tests)
for sec in ["quant","english","reasoning","gk"]:
    sec_topics = [(t, v) for (s,t),v in ts.items() if s==sec]
    if not sec_topics: continue
    sec_topics.sort(key=lambda x: x[1]["acc"])
    st.markdown(f'<div class="sec-head">{SECTION_ICON[sec]} {SECTION_FULL[sec]}</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(sec_topics),6))
    for i, (topic, v) in enumerate(sec_topics):
        acc = v["acc"]
        col = "#ef4444" if acc<40 else "#f59e0b" if acc<65 else "#3b82f6" if acc<80 else "#22c55e"
        cols[i%6].markdown(f"""
        <div style="border:1px solid {col}44;border-radius:8px;padding:8px;text-align:center;background:{col}11;margin-bottom:6px">
          <div style="font-size:10px;color:#555;margin-bottom:2px">{topic}</div>
          <div style="font-size:1.2rem;font-weight:700;color:{col}">{acc}%</div>
          <div style="font-size:10px;color:#aaa">{v['avg_att']:.0f} att · {v['marks_lost']:.1f} lost</div>
        </div>""", unsafe_allow_html=True)

# Analysis config
st.divider()
st.markdown("### 🎯 Configure Deep Analysis")
focus = st.selectbox("Analysis focus", [
    "Complete diagnosis — all sections, all topics, full exam strategy",
    "Quant only — deep dive into 15-min Quant strategy",
    "Weak sections only — focus on sections below 60% accuracy",
    "Mistake patterns — error analysis from question bank",
    "Score gap analysis — what's needed to hit target",
    "Exam day strategy — optimal attempt order and section approach",
])

date_range = st.selectbox("Data range", [
    "All time","Last 30 days","Last 14 days","Last 7 days"
])

from datetime import date, timedelta
if date_range == "Last 30 days":
    cutoff = (date.today() - timedelta(30)).isoformat()
    analysis_tests = [t for t in tests if t.get("date","") >= cutoff]
    analysis_qs    = [q for q in qs if q.get("date","") >= cutoff]
elif date_range == "Last 14 days":
    cutoff = (date.today() - timedelta(14)).isoformat()
    analysis_tests = [t for t in tests if t.get("date","") >= cutoff]
    analysis_qs    = [q for q in qs if q.get("date","") >= cutoff]
elif date_range == "Last 7 days":
    cutoff = (date.today() - timedelta(7)).isoformat()
    analysis_tests = [t for t in tests if t.get("date","") >= cutoff]
    analysis_qs    = [q for q in qs if q.get("date","") >= cutoff]
else:
    analysis_tests = tests
    analysis_qs    = qs

st.caption(f"Using {len(analysis_tests)} tests and {len(analysis_qs)} questions for this analysis")

# Cache key
cache_key = f"deep_{focus[:20].replace(' ','_')}_{date_range.replace(' ','_')}"
cached = get_cached("deep", cache_key)

col1,col2 = st.columns([1,3])
run_btn  = col1.button("🔬 Run Deep Analysis", type="primary", use_container_width=True)
if cached:
    col2.caption(f"Last generated: {cached.get('at','')} · Click to regenerate")

if run_btn:
    api_key = st.session_state.get("api_key","")
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar.")
    elif len(analysis_tests) < 1:
        st.warning("No tests in the selected date range.")
    else:
        with st.spinner("Claude is running a comprehensive deep analysis..."):
            ph = st.empty()
            prompt = deep_analysis_prompt(analysis_tests, analysis_qs, profile, focus)
            try:
                result = stream(prompt, api_key, ph)
                cache_report("deep", cache_key, result)
                st.success("Analysis complete and saved!")
            except Exception as e:
                st.error(f"Error: {e}")
elif cached:
    st.divider()
    st.markdown(f'<div class="report-wrap">{cached["text"]}</div>', unsafe_allow_html=True)
    st.download_button("⬇️ Download Analysis", data=cached["text"],
                       file_name=f"deep_analysis_{date.today()}.md", mime="text/markdown")
