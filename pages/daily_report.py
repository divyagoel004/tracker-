from datetime import date
import streamlit as st
from utils.db import tests_on, questions_on, get_profile, get_schedule, cache_report, get_cached, test_score, active_test_dates
from utils.claude_api import daily_prompt, stream
from utils.ui import SECTION_FULL, SECTION_ICON, score_color

st.markdown('<p class="page-title">📅 Daily Report</p><p class="page-sub">Deep analysis of every test you took on a given day + scheduled plan compliance.</p>', unsafe_allow_html=True)

profile = get_profile()
if not profile:
    st.warning("Set up your profile in **Dashboard** first."); st.stop()

all_dates = active_test_dates()
c1,c2 = st.columns([2,4])
if all_dates:
    sel_date = c1.selectbox("Date", all_dates, format_func=lambda d: f"{d} {'← Today' if d==date.today().isoformat() else ''}")
else:
    sel_date = c1.date_input("Date", value=date.today()).isoformat()

day_tests = tests_on(sel_date)
day_qs    = questions_on(sel_date)

# ── Day summary bar ────────────────────────────────────────────────────────────
if day_tests:
    scores = [test_score(t) for t in day_tests]
    avg_sc = round(sum(scores)/len(scores),1)
    target = profile.get("target_score",160)
    gap    = round(target - avg_sc,1)

    c1,c2,c3,c4,c5 = st.columns(5)
    def kpi(col,label,val,sub="",color=None):
        style = f"color:{color}" if color else ""
        col.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-val" style="{style}">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)
    kpi(c1,"Tests Today",len(day_tests))
    kpi(c2,"Avg Score",f"{avg_sc}/200","",score_color(avg_sc))
    kpi(c3,"Best Score",f"{max(scores)}/200")
    kpi(c4,"Gap",f"{gap:+}","to target","#ef4444" if gap>20 else "#f59e0b" if gap>5 else "#22c55e")
    kpi(c5,"Questions Logged",len(day_qs))

    # Test cards
    st.divider()
    st.markdown(f"### Tests on {sel_date}")
    for t in day_tests:
        sc = test_score(t); col = score_color(sc)
        with st.expander(f"{t.get('test_name','?')} — **{sc}/200** ({round(sc/200*100)}%)  · {t.get('mood','—')}"):
            cols = st.columns(4)
            for i,(sec,lbl) in enumerate(SECTION_FULL.items()):
                sd = t.get("sections",{}).get(sec,{})
                ns = sd.get("net_score",0)
                acc = round(sd.get("correct",0)/sd.get("attempted",1)*100) if sd.get("attempted",0) else 0
                c2c = "#22c55e" if acc>=75 else "#f59e0b" if acc>=55 else "#ef4444"
                cols[i].markdown(f"""
                <div style="border:1px solid #e5e7eb;border-radius:8px;padding:8px 10px;text-align:center">
                  <div style="font-size:11px;color:#888">{SECTION_ICON[sec]} {lbl.split('/')[0]}</div>
                  <div style="font-size:1.3rem;font-weight:700;color:{c2c}">{ns}/25</div>
                  <div style="font-size:11px;color:#aaa">{acc}% · {sd.get('attempted',0)} att · {sd.get('time_used',15):.0f}m</div>
                </div>""", unsafe_allow_html=True)
            if t.get("notes"):
                st.markdown(f"📝 **Notes:** {t['notes']}")
            if t.get("time_issue") and t["time_issue"] != "No — done comfortably":
                st.markdown(f"⏰ **Time issue:** {t['time_issue']}")

    # Difficult questions
    if day_qs:
        st.divider()
        st.markdown(f"### ❓ Difficult Questions Today ({len(day_qs)})")
        for q in day_qs:
            st.markdown(f"""
            <div class="q-card">
              <span style="font-size:11px;color:#888">{SECTION_FULL.get(q.get('section','?'),'?')} · {q.get('topic','?')}</span>
              <span style="font-size:10px;background:#fee2e2;color:#b91c1c;padding:1px 6px;border-radius:8px;margin-left:8px">{q.get('error_type','?').split('—')[0].strip()}</span>
              <div style="font-size:13px;margin-top:4px">{q.get('question_text','')[:150]}</div>
            </div>""", unsafe_allow_html=True)

    # Today's schedule
    sched = get_schedule()
    today_plan = None
    if sched and sched.get("calendar"):
        today_plan = next((d for d in sched["calendar"] if d["date"]==sel_date), None)

    if today_plan:
        st.divider()
        st.markdown("### 🗓️ Today's Scheduled Plan")
        for sess in today_plan.get("sessions",[]):
            pcol = {"critical":"#ef4444","high":"#f59e0b","medium":"#667eea","low":"#22c55e"}.get(sess.get("priority","medium"),"#aaa")
            st.markdown(f"""
            <div style="border:1px solid #e5e7eb;border-left:3px solid {pcol};border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:6px;background:white">
              <div style="font-weight:600;font-size:13px">{sess['title']} <span style="color:#aaa;font-weight:400;font-size:12px">· {sess['duration_min']} min</span></div>
              <div style="font-size:12px;color:#666;margin-top:3px">{sess.get('detail','')}</div>
            </div>""", unsafe_allow_html=True)

    # ── AI Deep Report ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🤖 Deep Daily AI Report")

    cached = get_cached("daily", sel_date)
    regen = False
    if cached:
        st.caption(f"Generated: {cached.get('at','')} · {len(day_tests)} tests · {len(day_qs)} questions")
        regen = st.button("🔄 Regenerate Report")
    
    if not cached or regen:
        api_key = st.session_state.get("api_key","")
        if not api_key:
            st.warning("Enter your Anthropic API key in the sidebar.")
        else:
            with st.spinner("Claude is generating your deep daily report..."):
                ph = st.empty()
                prompt = daily_prompt(day_tests, day_qs, profile, sel_date, today_plan)
                try:
                    result = stream(prompt, api_key, ph)
                    cache_report("daily", sel_date, result)
                    st.success("Report saved!")
                except Exception as e:
                    st.error(f"Error: {e}")
    elif cached:
        st.markdown(f'<div class="report-wrap">{cached["text"]}</div>', unsafe_allow_html=True)

    if cached:
        st.download_button("⬇️ Download Report", data=cached["text"],
                           file_name=f"daily_{sel_date}.md", mime="text/markdown")
else:
    st.info(f"No tests logged for **{sel_date}**.")
    if all_dates:
        st.markdown("**Days with data:** " + " · ".join(all_dates[:8]))
    st.markdown("Go to **Log Test** to add today's results.")
