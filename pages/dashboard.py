from datetime import date
import streamlit as st
from utils.db import get_profile, set_profile, all_tests, all_questions, test_score, section_stats, active_test_dates
from utils.ui import SECTION_FULL, SECTION_ICON, score_color, acc_badge

st.markdown('<p class="page-title">🏠 Dashboard</p>', unsafe_allow_html=True)

profile = get_profile()
tests = all_tests()
questions = all_questions()

# ── Profile setup ──────────────────────────────────────────────────────────────
with st.expander("⚙️ Profile & Settings", expanded=not bool(profile)):
    c1,c2,c3 = st.columns(3)
    name      = c1.text_input("Name", value=profile.get("name",""))
    tier      = c2.selectbox("Tier", ["Tier 1","Tier 2"], index=0 if profile.get("tier","Tier 1")=="Tier 1" else 1)
    exam_date = c3.date_input("Exam Date", value=date.fromisoformat(profile["exam_date"]) if profile.get("exam_date") else date(2025,8,13))
    c4,c5,c6  = st.columns(3)
    target    = c4.number_input("Target Score (/200)", 100, 200, int(profile.get("target_score",160)), 5)
    hours     = c5.number_input("Study Hours / Day", 1, 16, int(profile.get("study_hours",4)))
    series    = c6.text_input("Mock Series", value=profile.get("mock_series","Career Power"))
    if st.button("💾 Save Profile", type="primary"):
        days = (exam_date - date.today()).days
        set_profile({"name":name,"tier":tier,"exam_date":exam_date.isoformat(),
                     "target_score":target,"study_hours":hours,
                     "mock_series":series,"days_remaining":days})
        st.success("Saved!"); st.rerun()

if not profile:
    st.info("Set up your profile above to start."); st.stop()

days_left  = (date.fromisoformat(profile["exam_date"]) - date.today()).days
scores     = [test_score(t) for t in tests]
avg_score  = round(sum(scores)/len(scores),1) if scores else 0
best_score = max(scores) if scores else 0
gap        = round(profile.get("target_score",160) - avg_score, 1)
target     = profile.get("target_score",160)

# ── KPIs ───────────────────────────────────────────────────────────────────────
st.markdown(f"### Welcome back, {profile.get('name','Student')} 👋")
c1,c2,c3,c4,c5,c6 = st.columns(6)
def kpi(col, label, val, sub="", color=None):
    style = f"color:{color}" if color else ""
    col.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-val" style="{style}">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

urgency_col = "#ef4444" if days_left < 21 else "#f59e0b" if days_left < 42 else "#22c55e"
kpi(c1,"Days to Exam", days_left, "⚠️ Final sprint!" if days_left<21 else "Keep grinding", urgency_col)
kpi(c2,"Tests Logged", len(tests), f"on {len(active_test_dates())} days")
kpi(c3,"Avg Score", f"{avg_score}", f"/{target} target", score_color(avg_score))
kpi(c4,"Best Score", f"{best_score}", "/200")
kpi(c5,"Score Gap", f"{gap:+.1f}", "to target", "#ef4444" if gap>25 else "#f59e0b" if gap>10 else "#22c55e")
kpi(c6,"Questions Logged", len(questions), "in mistake bank")

st.divider()

# ── Section health ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([2,3])
with col1:
    st.markdown("#### 🏥 Section Health")
    if tests:
        ss = section_stats(tests)
        for sec in ["quant","english","reasoning","gk"]:
            s = ss.get(sec,{})
            acc = s.get("avg_acc",-1)
            bar_w = max(0, min(100, acc)) if acc >= 0 else 0
            bar_col = "#22c55e" if acc>=75 else "#f59e0b" if acc>=55 else "#ef4444"
            st.markdown(f"""
            <div style="margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px">
                <span>{SECTION_ICON[sec]} {SECTION_FULL[sec].split('/')[0]}</span>
                <span style="font-weight:600;color:{bar_col}">{acc}% acc | {s.get('avg_net','—')}/25</span>
              </div>
              <div style="background:#f0f0f0;border-radius:4px;height:6px">
                <div style="background:{bar_col};width:{bar_w}%;height:6px;border-radius:4px"></div>
              </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Log tests to see section health.")

with col2:
    st.markdown("#### 📋 Recent Tests")
    recent = sorted(tests, key=lambda x: x.get("created_at",""), reverse=True)[:6]
    for t in recent:
        sc = test_score(t)
        col = score_color(sc)
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 12px;
             border:1px solid #e5e7eb;border-radius:8px;margin-bottom:5px;background:white">
          <div><b>{t.get('test_name','?')}</b> <span style="color:#888;font-size:12px">· {t.get('date','')}</span></div>
          <div style="font-weight:700;color:{col}">{sc}/200</div>
        </div>""", unsafe_allow_html=True)
    if not recent:
        st.info("No tests yet — go to **Log Test**")

# ── Today's schedule preview ───────────────────────────────────────────────────
from utils.db import get_schedule
sched = get_schedule()
today_str = date.today().isoformat()
if sched and sched.get("calendar"):
    today_entry = next((d for d in sched["calendar"] if d["date"]==today_str), None)
    if today_entry:
        st.divider()
        st.markdown("#### 🗓️ Today's Scheduled Plan")
        c = st.columns(min(len(today_entry["sessions"]),4))
        for i, sess in enumerate(today_entry["sessions"][:4]):
            pcolor = {"critical":"#ef4444","high":"#f59e0b","medium":"#667eea","low":"#22c55e"}.get(sess.get("priority","medium"),"#667eea")
            c[i].markdown(f"""
            <div style="border:1px solid #e5e7eb;border-left:3px solid {pcolor};border-radius:8px;padding:10px 12px;background:white">
              <div style="font-size:12px;font-weight:600;margin-bottom:4px">{sess['title']}</div>
              <div style="font-size:11px;color:#888">{sess['duration_min']} min · {sess.get('priority','').upper()}</div>
            </div>""", unsafe_allow_html=True)
        if st.button("📅 View Full Schedule"):
            st.info("Go to **Study Scheduler** in the sidebar.")
