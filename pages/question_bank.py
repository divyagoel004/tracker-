# pages/question_bank.py
from collections import Counter
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import all_questions, del_question
from utils.ui import SECTION_FULL
from utils.scheduler import SECTION_TOPICS

st.markdown('<p class="page-title">📚 Question Bank</p><p class="page-sub">Your personal mistake database — searchable, filterable, chartable.</p>', unsafe_allow_html=True)

qs = sorted(all_questions(), key=lambda x: x.get("created_at",""), reverse=True)
if not qs:
    st.info("No questions logged yet. Go to **Log Questions** to start."); st.stop()

# Stats
c1,c2,c3,c4 = st.columns(4)
ec = Counter(q.get("error_type","?").split("—")[0].strip() for q in qs)
tc = Counter(q.get("topic","?") for q in qs)
sc = Counter(q.get("section","?") for q in qs)
c1.metric("Total",len(qs))
c2.metric("Top error", ec.most_common(1)[0][0][:20] if ec else "—")
c3.metric("Hardest topic", tc.most_common(1)[0][0] if tc else "—")
c4.metric("Weakest section", SECTION_FULL.get(sc.most_common(1)[0][0],"?").split("/")[0] if sc else "—")

# Filters
st.divider()
c1,c2,c3,c4 = st.columns(4)
fs   = c1.selectbox("Section",["All"]+list(SECTION_FULL.keys()), format_func=lambda x:"All" if x=="All" else SECTION_FULL[x])
ft   = c2.text_input("Topic")
fe   = c3.selectbox("Error",["All","Conceptual","Calculation","Time pressure","Wrong reading","Guessed","Silly","Trap"])
fq   = c4.text_input("Search question text")

filt = qs
if fs!="All":  filt=[q for q in filt if q.get("section")==fs]
if ft:         filt=[q for q in filt if ft.lower() in q.get("topic","").lower()]
if fe!="All":  filt=[q for q in filt if fe.lower() in q.get("error_type","").lower()]
if fq:         filt=[q for q in filt if fq.lower() in q.get("question_text","").lower()]

view = st.radio("View",["Cards","Table","Charts"], horizontal=True, label_visibility="collapsed")
st.markdown(f"**{len(filt)} / {len(qs)} questions**")

ECOL={"Conceptual":"#ef4444","Calculation":"#f59e0b","Time":"#8b5cf6","Wrong":"#3b82f6","Guessed":"#6b7280","Silly":"#f97316","Trap":"#ec4899"}

if view=="Table":
    rows=[{"Date":q.get("date"),"Section":SECTION_FULL.get(q.get("section","?"),"?"),"Topic":q.get("topic"),"Question":q.get("question_text","")[:80]+"...","Error":q.get("error_type","").split("—")[0].strip()[:25],"Correct":q.get("correct_answer","—")} for q in filt]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=500)
elif view=="Charts":
    c1,c2=st.columns(2)
    with c1:
        st.markdown("**By topic**")
        top_tc=tc.most_common(12)
        fig=go.Figure(go.Bar(x=[t[1] for t in top_tc[::-1]],y=[t[0] for t in top_tc[::-1]],orientation="h",marker_color="#667eea"))
        fig.update_layout(height=350,margin=dict(l=0,r=0,t=10,b=0),plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)
    with c2:
        st.markdown("**By error type**")
        fig2=go.Figure(go.Pie(labels=list(ec.keys()),values=list(ec.values()),hole=0.4,marker_colors=["#ef4444","#f59e0b","#8b5cf6","#3b82f6","#6b7280","#f97316","#ec4899"]))
        fig2.update_layout(height=350,margin=dict(l=0,r=0,t=10,b=0),paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2,use_container_width=True)
else:
    for q in filt[:80]:
        ec2=next((v for k,v in ECOL.items() if k.lower() in q.get("error_type","").lower()),"#aaa")
        with st.expander(f"[{q.get('topic','?')}] {q.get('question_text','')[:80]}... · {q.get('date','')}"):
            c1,c2=st.columns([4,1])
            c1.markdown(f"**Section:** {SECTION_FULL.get(q.get('section','?'),'?')}")
            c1.markdown(f"**Q:** {q.get('question_text','')}")
            c1.markdown(f"**Your ans:** {q.get('your_answer','—')} | **Correct:** {q.get('correct_answer','—')}")
            c1.markdown(f"**Error:** <span style='color:{ec2};font-weight:600'>{q.get('error_type','—')}</span>",unsafe_allow_html=True)
            if q.get("note"): c1.markdown(f"**Note:** {q['note']}")
            if c2.button("🗑️",key=f"dq_{q.get('id')}"): del_question(q.get("id")); st.rerun()
