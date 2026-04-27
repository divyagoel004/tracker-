from datetime import date, timedelta
import streamlit as st
from utils.db import get_profile, all_tests, get_schedule, section_stats, topic_stats
from utils.scheduler import build_schedule, SECTION_FULL as SF, SECTION_TOPICS
from utils.ui import SECTION_FULL, SECTION_ICON, PRIORITY_COLOR

st.markdown('<p class="page-title">🗓️ Study Scheduler</p><p class="page-sub">Auto-generates a personalised day-by-day study plan based on your weak areas, exam date and available time.</p>', unsafe_allow_html=True)

profile = get_profile()
if not profile:
    st.warning("Set up your profile in **Dashboard** first."); st.stop()

tests = all_tests()
existing = get_schedule()

# ── Config form ────────────────────────────────────────────────────────────────
st.markdown("### ⚙️ Configure Your Schedule")

with st.form("sched_form"):
    c1,c2,c3 = st.columns(3)
    exam_date  = c1.date_input("Exam Date",
        value=date.fromisoformat(profile["exam_date"]) if profile.get("exam_date") else date(2025,8,13))
    hours_pd   = c2.number_input("Study Hours / Day", 2, 14, int(profile.get("study_hours",4)))
    target_sc  = c3.number_input("Target Score (/200)", 100, 200, int(profile.get("target_score",160)), 5)

    c1,c2 = st.columns(2)
    study_days = c1.multiselect("Study days",
        ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
        default=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"])
    mock_days  = c2.multiselect("Mock test days",
        ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
        default=["Saturday"])

    c1,c2,c3 = st.columns(3)
    focus_mode = c1.selectbox("Focus mode", [
        "weak_first — Fix critical weak topics first",
        "balanced — Mix of weak, moderate, strong",
        "strong_first — Maintain strengths, patch weaknesses"
    ]).split(" — ")[0]
    revision_day = c2.checkbox("Include Sunday revision session", value=True)
    
    # Weak section override
    weak_override = c3.multiselect("Force-prioritise sections (optional)",
        ["quant","english","reasoning","gk"],
        format_func=lambda x: SECTION_FULL[x],
        default=[])

    # Topic overrides
    with st.expander("🎯 Advanced: Pin specific topics to top of queue"):
        pin_topics = []
        for sec in ["quant","english","reasoning","gk"]:
            pinned = st.multiselect(f"Pin {SECTION_FULL[sec]} topics",
                SECTION_TOPICS[sec], key=f"pin_{sec}")
            for t in pinned:
                pin_topics.append({"sec":sec,"topic":t})

    submitted = st.form_submit_button("🚀 Generate Schedule", type="primary", use_container_width=True)

if submitted:
    if not study_days:
        st.error("Select at least one study day.")
    elif (exam_date - date.today()).days <= 0:
        st.error("Exam date must be in the future.")
    else:
        with st.spinner("Building your personalised schedule..."):
            config = {
                "exam_date": exam_date.isoformat(),
                "study_days": study_days,
                "mock_days": mock_days,
                "hours_per_day": hours_pd,
                "focus_mode": focus_mode,
                "weak_sections": weak_override,
                "include_revision_day": revision_day,
                "target_score": target_sc,
                "tests": tests,
                "pin_topics": pin_topics,
            }
            sched = build_schedule(config)
            st.success("✅ Schedule generated!")
            st.rerun()

# ── Display schedule ───────────────────────────────────────────────────────────
sched = get_schedule()
if not sched or sched.get("error"):
    st.info("Configure and generate a schedule above."); st.stop()

summary = sched.get("summary",{})
today = date.today().isoformat()

# ── Summary cards ──────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 📊 Schedule Overview")
c1,c2,c3,c4,c5 = st.columns(5)
def kpi(col,l,v,sub=""):
    col.markdown(f'<div class="kpi"><div class="kpi-label">{l}</div><div class="kpi-val">{v}</div><div class="kpi-sub">{sub}</div></div>',unsafe_allow_html=True)
kpi(c1,"Days Planned",summary.get("total_days","?"))
kpi(c2,"Exam In",f"{summary.get('exam_in_days','?')}d")
kpi(c3,"Full Mocks",summary.get("mock_count","?"))
kpi(c4,"Critical Topics",summary.get("critical_topics","?"),"need immediate work")
kpi(c5,"Generated",sched.get("generated_at","?"))

# Critical topics alert
if summary.get("top_critical"):
    st.markdown('<div class="tip">🔴 <b>Critical topics identified:</b> ' + " · ".join(summary["top_critical"]) + '</div>', unsafe_allow_html=True)

# Phases
phases = sched.get("phases",[])
if phases:
    st.markdown("### 📅 Study Phases")
    pc = st.columns(len(phases))
    phase_colors = ["#ef4444","#f59e0b","#667eea","#22c55e"]
    for i, (ph, col) in enumerate(zip(phases, pc)):
        c = phase_colors[i % len(phase_colors)]
        col.markdown(f"""
        <div style="border:1px solid {c}33;border-top:3px solid {c};border-radius:8px;padding:10px 12px;background:white">
          <div style="font-weight:600;font-size:13px;color:{c}">{ph['name']}</div>
          <div style="font-size:12px;color:#888;margin-top:3px">{ph['days']} days</div>
          <div style="font-size:12px;margin-top:5px">{ph['focus']}</div>
        </div>""", unsafe_allow_html=True)

# Topic priority table
tp = sched.get("topic_priority",[])
if tp:
    with st.expander("📋 Full Topic Priority List (how topics are ordered in your plan)"):
        cols = st.columns([2.5,1.5,1,1,1.5])
        for h,c in zip(["Topic","Section","Accuracy","Status","Marks Lost"],cols):
            c.markdown(f"**{h}**")
        for t in tp[:30]:
            c1,c2,c3,c4,c5 = st.columns([2.5,1.5,1,1,1.5])
            cls = t.get("class","unknown")
            badge = {"critical":"🔴","weak":"🟠","moderate":"🟡","strong":"🟢","unknown":"⚪"}.get(cls,"⚪")
            c1.markdown(f"<span style='font-size:13px'>{t['topic']}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='font-size:12px;color:#888'>{SECTION_FULL.get(t['sec'],'?').split('/')[0]}</span>", unsafe_allow_html=True)
            c3.markdown(f"<span style='font-size:13px'>{t['acc']}%</span>" if t['acc']>=0 else "—", unsafe_allow_html=True)
            c4.markdown(f"{badge} {cls}", unsafe_allow_html=True)
            c5.markdown(f"<span style='font-size:13px'>{t['marks_lost']:.1f}</span>", unsafe_allow_html=True)

# ── Calendar view ──────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 📆 Day-by-Day Plan")

cal = sched.get("calendar",[])
view_opts = ["This week","Next week","Full calendar","By date range"]
v = st.radio("View", view_opts, horizontal=True)

today_d = date.today()
if v == "This week":
    start = today_d - timedelta(days=today_d.weekday())
    end   = start + timedelta(6)
    show  = [d for d in cal if start.isoformat() <= d.get("date","") <= end.isoformat()]
elif v == "Next week":
    start = today_d - timedelta(days=today_d.weekday()) + timedelta(7)
    end   = start + timedelta(6)
    show  = [d for d in cal if start.isoformat() <= d.get("date","") <= end.isoformat()]
elif v == "By date range":
    dc1,dc2 = st.columns(2)
    rng_start = dc1.date_input("From", value=today_d)
    rng_end   = dc2.date_input("To",   value=today_d + timedelta(14))
    show = [d for d in cal if rng_start.isoformat() <= d.get("date","") <= rng_end.isoformat()]
else:
    show = cal[:42]

if not show:
    st.info("No scheduled days in this range. The schedule covers study days only (not off days).")

SESSION_ICONS = {
    "mock":"🎯","review":"🔍","topic_study":"📚","sectional_drill":"⏱️",
    "gk_daily":"🌍","speed_drill":"⚡","revision":"🔄"
}

for day in show:
    is_today = day["date"] == today
    bcolor   = "#667eea" if is_today else "#e5e7eb"
    header   = f"{'📍 TODAY — ' if is_today else ''}{day['weekday']} {day['date']} · {day.get('phase','')} phase"

    with st.expander(header, expanded=is_today):
        sessions = day.get("sessions",[])
        total_min = sum(s.get("duration_min",0) for s in sessions)
        st.markdown(f"<div style='font-size:12px;color:#888;margin-bottom:8px'>📊 {len(sessions)} sessions · {total_min} min total · {day.get('hours',0)}h study day</div>", unsafe_allow_html=True)

        if day.get("is_mock_day"):
            st.markdown('<span style="background:#fee2e2;color:#b91c1c;font-size:11px;font-weight:600;padding:2px 8px;border-radius:10px">📝 MOCK DAY</span>', unsafe_allow_html=True)
        
        for sess in sessions:
            stype = sess.get("type","")
            icon  = SESSION_ICONS.get(stype,"📌")
            prio  = sess.get("priority","medium")
            pc    = {"critical":"#ef4444","high":"#f59e0b","medium":"#667eea","low":"#22c55e"}.get(prio,"#aaa")
            cls_map = {"critical":"🔴","high":"🟠","moderate":"🟡","strong":"🟢","unknown":"⚪"}
            cls_badge = f' <span style="font-size:10px;color:#aaa">[{cls_map.get(sess.get("class",""),"")} {sess.get("class","")}  · {sess.get("acc","")}% acc]</span>' if sess.get("class") else ""
            st.markdown(f"""
            <div style="border:1px solid #e5e7eb;border-left:3px solid {pc};border-radius:0 8px 8px 0;padding:9px 14px;margin-bottom:6px;background:white">
              <div style="font-size:13px;font-weight:600">{icon} {sess['title']} <span style="color:#aaa;font-weight:400">· {sess['duration_min']} min</span>{cls_badge}</div>
              <div style="font-size:12px;color:#555;margin-top:3px">{sess.get('detail','')}</div>
            </div>""", unsafe_allow_html=True)

# ── Export ─────────────────────────────────────────────────────────────────────
st.divider()
if st.button("📋 Export Schedule as Text"):
    lines = ["SSC CGL Study Schedule\n" + "="*40]
    for day in cal:
        lines.append(f"\n{day['weekday']} {day['date']} [{day.get('phase','')}]")
        for s in day.get("sessions",[]):
            lines.append(f"  • {s['title']} ({s['duration_min']} min)")
            lines.append(f"    → {s.get('detail','')}")
    st.download_button("⬇️ Download Schedule", data="\n".join(lines),
                       file_name="ssc_cgl_schedule.txt", mime="text/plain")
