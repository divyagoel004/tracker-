from datetime import date, timedelta
import streamlit as st
import plotly.graph_objects as go
from utils.db import (tests_in_week, all_tests, all_questions, get_profile,
                      get_schedule, cache_report, get_cached, test_score, section_stats)
from utils.claude_api import weekly_prompt, stream
from utils.ui import SECTION_FULL, SECTION_ICON, score_color

st.markdown('<p class="page-title">📆 Weekly Report</p><p class="page-sub">Comprehensive week analysis with score trends, section rankings, error patterns and next week\'s plan.</p>', unsafe_allow_html=True)

profile = get_profile()
if not profile:
    st.warning("Set up your profile in **Dashboard** first."); st.stop()

# ── Week selector ──────────────────────────────────────────────────────────────
tests_all = all_tests()
week_set = set()
for t in tests_all:
    try:
        d = date.fromisoformat(t["date"])
        week_set.add(d.isocalendar()[:2])
    except: pass
if not week_set:
    st.info("No tests logged yet."); st.stop()

week_opts = sorted(week_set, reverse=True)
def wlabel(y,w):
    d0 = date.fromisocalendar(y,w,1)
    cur = date.today().isocalendar()
    tag = " ← This week" if (y,w)==(cur[0],cur[1]) else " ← Last week" if w==cur[1]-1 and y==cur[0] else ""
    return f"Week {w}, {y}  ({d0.strftime('%d %b')} – {(d0+timedelta(6)).strftime('%d %b')}){tag}"

sel = st.selectbox("Select week", week_opts, format_func=lambda x: wlabel(*x))
y,w = sel
week_tests = tests_in_week(y,w)
dates      = sorted(set(t.get("date","") for t in week_tests))
week_qs    = [q for q in all_questions() if q.get("date","") in set(dates)]

if not week_tests:
    st.info("No tests in this week."); st.stop()

scores = [test_score(t) for t in week_tests]
avg_sc = round(sum(scores)/len(scores),1)
target = profile.get("target_score",160)

# ── KPIs ───────────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
def kpi(col,l,v,s="",color=None):
    col.markdown(f'<div class="kpi"><div class="kpi-label">{l}</div><div class="kpi-val" style="color:{color or "inherit"}">{v}</div><div class="kpi-sub">{s}</div></div>', unsafe_allow_html=True)
kpi(c1,"Tests This Week",len(week_tests))
kpi(c2,"Study Days",len(dates))
kpi(c3,"Avg Score",f"{avg_sc}/200","",score_color(avg_sc))
kpi(c4,"Best/Worst",f"{max(scores)}/{min(scores)}")
kpi(c5,"Questions Logged",len(week_qs))

# ── Score trend ────────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 📈 Score Trend")
ts_sorted = sorted(week_tests, key=lambda x: x.get("date",""))
xlabels = [f"{t.get('test_name','?')} ({t.get('date','')})" for t in ts_sorted]
yscores  = [test_score(t) for t in ts_sorted]

fig = go.Figure()
fig.add_trace(go.Scatter(x=xlabels, y=yscores, mode="lines+markers+text",
    text=yscores, textposition="top center", line=dict(color="#667eea",width=2.5),
    marker=dict(size=9,color="#667eea"), name="Score"))
fig.add_hline(y=target, line_dash="dash", line_color="#22c55e",
              annotation_text=f"Target {target}", annotation_position="right")
fig.update_layout(height=280, margin=dict(l=0,r=60,t=20,b=50),
    xaxis_tickangle=-20, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    yaxis_range=[0,205], xaxis_title="", yaxis_title="Score /200")
st.plotly_chart(fig, use_container_width=True)

# ── Section table ──────────────────────────────────────────────────────────────
st.markdown("### 🏥 Section Performance")
ss = section_stats(week_tests)
cols = st.columns(4)
for col,(sec,lbl) in zip(cols, SECTION_FULL.items()):
    s = ss.get(sec,{})
    acc = s.get("avg_acc",-1)
    col.markdown(f"""
    <div class="kpi">
      <div class="kpi-label">{SECTION_ICON[sec]} {lbl.split('/')[0]}</div>
      <div class="kpi-val" style="color:{'#22c55e' if acc>=75 else '#f59e0b' if acc>=55 else '#ef4444'}">{acc}%</div>
      <div class="kpi-sub">
        Net: {s.get('avg_net','—')}/25<br>
        Att: {s.get('avg_att','—')} · ✓{s.get('avg_cor','—')} ✗{s.get('avg_wrg','—')}<br>
        Time: {s.get('avg_time','—')}m avg
      </div>
    </div>""", unsafe_allow_html=True)

# ── Error breakdown ────────────────────────────────────────────────────────────
if week_qs:
    from collections import Counter
    st.divider()
    st.markdown(f"### 🧠 Mistake Analysis ({len(week_qs)} questions)")
    c1,c2 = st.columns(2)
    ec = Counter(q.get("error_type","?").split("—")[0].strip() for q in week_qs)
    tc = Counter(q.get("topic","?") for q in week_qs)
    with c1:
        st.markdown("**Error types:**")
        for etype, cnt in ec.most_common():
            pct = round(cnt/len(week_qs)*100)
            bar = "█"*max(1,pct//5) + "░"*(20-max(1,pct//5))
            st.markdown(f"<div style='font-size:12px;margin-bottom:5px'>{etype[:35]}<br><span style='color:#667eea;font-family:monospace;font-size:11px'>{bar}</span> {cnt} ({pct}%)</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("**Hardest topics:**")
        for topic, cnt in tc.most_common(8):
            st.markdown(f"<div style='font-size:13px;margin-bottom:4px'>• {topic} — {cnt} mistake(s)</div>", unsafe_allow_html=True)

# ── Next week schedule preview ─────────────────────────────────────────────────
sched = get_schedule()
next_week_days = None
if sched and sched.get("calendar"):
    nw_start = date.fromisocalendar(y,w,1) + timedelta(7)
    nw_end   = nw_start + timedelta(6)
    next_week_days = [d for d in sched["calendar"]
                      if nw_start.isoformat() <= d.get("date","") <= nw_end.isoformat()]
    if next_week_days:
        st.divider()
        st.markdown("### 🗓️ Next Week's Scheduled Plan")
        for day in next_week_days[:7]:
            with st.expander(f"**{day['weekday']}** {day['date']} — {day.get('phase','')} phase"):
                for sess in day.get("sessions",[]):
                    pc = {"critical":"#ef4444","high":"#f59e0b","medium":"#667eea"}.get(sess.get("priority","medium"),"#aaa")
                    st.markdown(f"""
                    <div style="border-left:2px solid {pc};padding:5px 10px;margin-bottom:5px;font-size:13px">
                      <b>{sess['title']}</b> · {sess['duration_min']} min<br>
                      <span style="color:#666;font-size:12px">{sess.get('detail','')}</span>
                    </div>""", unsafe_allow_html=True)

# ── AI Weekly Report ───────────────────────────────────────────────────────────
st.divider()
st.markdown("### 🤖 Deep Weekly AI Report")
report_key = f"{y}_W{w}"
cached = get_cached("weekly", report_key)
regen = False
if cached:
    st.caption(f"Generated: {cached.get('at','')} · {len(week_tests)} tests")
    regen = st.button("🔄 Regenerate")

if not cached or regen:
    api_key = st.session_state.get("api_key","")
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar.")
    else:
        with st.spinner("Claude is generating your weekly report..."):
            ph = st.empty()
            prompt = weekly_prompt(week_tests, week_qs, profile, wlabel(y,w), next_week_days)
            try:
                result = stream(prompt, api_key, ph)
                cache_report("weekly", report_key, result)
                st.success("Saved!")
            except Exception as e:
                st.error(f"Error: {e}")
elif cached:
    st.markdown(f'<div class="report-wrap">{cached["text"]}</div>', unsafe_allow_html=True)

if cached:
    st.download_button("⬇️ Download", data=cached["text"],
                       file_name=f"weekly_{y}_W{w}.md", mime="text/markdown")
