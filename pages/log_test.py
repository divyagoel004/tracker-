from datetime import date
import streamlit as st
from utils.db import add_test, all_tests, del_test, test_score
from utils.ui import SECTION_FULL, SECTION_ICON
from utils.scheduler import SECTION_TOPICS

st.markdown('<p class="page-title">📝 Log Mock Test</p><p class="page-sub">Record one or multiple tests per day — each stored separately.</p>', unsafe_allow_html=True)

c1,c2,c3,c4 = st.columns(4)
tname = c1.text_input("Test Name *", placeholder="e.g. Career Power Mock #7")
tdate = c2.date_input("Date", value=date.today())
ttype = c3.selectbox("Type", ["Full Mock","Sectional Practice","PYQ Paper","Topic Test","Grand Test"])
mno   = c4.number_input("Mock #", 1, 999, 1)

st.divider()
st.markdown("### Section Scores")

section_data = {}
for sec in ["quant","english","reasoning","gk"]:
    st.markdown(f'<div class="sec-head">{SECTION_ICON[sec]} {SECTION_FULL[sec]}</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    att  = c1.number_input("Attempted",   0,25,0, key=f"s_{sec}_a")
    cor  = c2.number_input("Correct",     0,25,0, key=f"s_{sec}_c")
    wrg  = c3.number_input("Wrong",       0,25,0, key=f"s_{sec}_w")
    skip = c4.number_input("Skipped",     0,25,0, key=f"s_{sec}_sk")
    tleft= c5.number_input("Qs left @time end",0,25,0, key=f"s_{sec}_tl")
    tused= c6.number_input("Time used(m)",0.0,15.0,15.0,0.5, key=f"s_{sec}_t")
    net  = round(cor - 0.5*wrg, 1)
    acc  = round(cor/att*100) if att else 0
    col = "#22c55e" if acc>=75 else "#f59e0b" if acc>=55 else "#ef4444"
    st.markdown(f'<div style="font-size:12px;color:{col};margin:2px 0 8px">Net score: {net}/25 · Accuracy: {acc}% · Time left when done: {15-tused:.1f}m</div>', unsafe_allow_html=True)
    section_data[sec] = {"attempted":att,"correct":cor,"wrong":wrg,"skipped":skip,
                          "qs_left_at_end":tleft,"time_used":tused,"net_score":net}

st.divider()
st.markdown("### Topic Breakdown *(fill what appeared in this test)*")
topic_data = {}
for sec in ["quant","english","reasoning","gk"]:
    with st.expander(f"{SECTION_ICON[sec]} {SECTION_FULL[sec]} — Topics"):
        rows = []
        hcols = st.columns([3,1,1,1,1.5])
        for h, c in zip(["Topic","Att","Cor","Wrg","Difficulty"], hcols):
            c.markdown(f"**{h}**")
        for i, topic in enumerate(SECTION_TOPICS[sec]):
            tc = st.columns([3,1,1,1,1.5])
            tc[0].markdown(f"<span style='font-size:13px'>{topic}</span>", unsafe_allow_html=True)
            ta = tc[1].number_input("",0,10,0, key=f"tp_{sec}_{i}_a", label_visibility="collapsed")
            tcc= tc[2].number_input("",0,10,0, key=f"tp_{sec}_{i}_c", label_visibility="collapsed")
            tw = tc[3].number_input("",0,10,0, key=f"tp_{sec}_{i}_w", label_visibility="collapsed")
            tf = tc[4].selectbox("",["—","Easy","Medium","Hard"], key=f"tp_{sec}_{i}_f", label_visibility="collapsed")
            if ta > 0 or tcc > 0:
                rows.append({"topic":topic,"attempted":ta,"correct":tcc,"wrong":tw,"feel":tf})
        topic_data[sec] = rows

st.divider()
c1,c2,c3 = st.columns(3)
time_issue = c1.selectbox("Time pressure?",["No — done comfortably","Yes — 1-2 Qs left","Yes — 3+ Qs left","Ran out badly"])
mood       = c2.selectbox("How did you feel?",["Confident","Okay","Stressed","Very bad"])
notes      = c3.text_input("Quick note", placeholder="e.g. Algebra questions were tricky today")

st.divider()
save_col, _ = st.columns([1,3])
if save_col.button("💾 Save Test", type="primary", use_container_width=True):
    if not tname.strip():
        st.error("Please enter a test name.")
    else:
        total = sum(s["net_score"] for s in section_data.values())
        add_test({"test_name":tname.strip(),"date":tdate.isoformat(),"test_type":ttype,
                  "mock_no":mno,"sections":section_data,"topic_data":topic_data,
                  "total_score":round(total,1),"time_issue":time_issue,"mood":mood,"notes":notes})
        st.success(f"✅ Saved! Score: **{round(total,1)}/200**")
        st.balloons()

st.divider()
st.markdown("### All Logged Tests")
tests = sorted(all_tests(), key=lambda x: x.get("date",""), reverse=True)
for t in tests:
    sc = test_score(t); pct = round(sc/200*100)
    col = "#22c55e" if pct>=75 else "#f59e0b" if pct>=55 else "#ef4444"
    c1,c2,c3,c4,c5 = st.columns([2.5,1.2,1,1.5,0.6])
    c1.markdown(f"**{t.get('test_name')}**")
    c2.markdown(f"📅 {t.get('date')}")
    c3.markdown(f"<span style='font-weight:700;color:{col}'>{sc}/200</span>", unsafe_allow_html=True)
    c4.markdown(f"{t.get('mood','—')} · {t.get('test_type','')}")
    if c5.button("🗑️",key=f"dl_{t.get('id')}",help="Delete"):
        del_test(t.get("id")); st.rerun()
