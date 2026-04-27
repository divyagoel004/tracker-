from datetime import date
import streamlit as st
from utils.db import add_question, all_questions, del_question
from utils.ui import SECTION_FULL
from utils.scheduler import SECTION_TOPICS

st.markdown('<p class="page-title">❓ Log Difficult Questions</p><p class="page-sub">Every question you log builds your personal mistake intelligence — Claude uses this in every report.</p>', unsafe_allow_html=True)

c1,c2,c3 = st.columns(3)
sec    = c1.selectbox("Section", list(SECTION_FULL.keys()), format_func=lambda x: SECTION_FULL[x])
topic  = c2.selectbox("Topic", SECTION_TOPICS[sec])
qdate  = c3.date_input("Date", value=date.today())

qtext  = st.text_area("Question text *(paste the full question)*", height=90,
                       placeholder="e.g. A train covers 360 km at 60 km/h. Find the time...")
c1,c2,c3 = st.columns(3)
etype  = c1.selectbox("Error type", [
    "Conceptual gap — didn't know the concept/formula",
    "Calculation error — knew approach but made arithmetic mistake",
    "Time pressure — ran out of time, rushed",
    "Wrong reading — misread the question",
    "Guessed wrong — pure blind guess",
    "Silly mistake — knew it but answered wrong",
    "Trap option — chose a distractor",
])
your_ans    = c2.text_input("Your answer", placeholder="e.g. 8 hours")
correct_ans = c3.text_input("Correct answer", placeholder="e.g. 6 hours")
note = st.text_area("Concept note / correct approach *(what you learned)*", height=60,
                     placeholder="e.g. Use Speed = Distance/Time. I mistakenly divided by 60 instead of the speed.")

if st.button("💾 Save Question", type="primary"):
    if not qtext.strip():
        st.error("Please enter the question text.")
    else:
        add_question({"section":sec,"topic":topic,"date":qdate.isoformat(),
                      "question_text":qtext.strip(),"error_type":etype,
                      "your_answer":your_ans,"correct_answer":correct_ans,"note":note})
        st.success("✅ Question logged!"); st.rerun()

st.divider()
st.markdown("### Recent Questions")
qs = sorted(all_questions(), key=lambda x: x.get("created_at",""), reverse=True)

fc1,fc2,fc3 = st.columns(3)
fs = fc1.selectbox("Section", ["All"]+list(SECTION_FULL.keys()), format_func=lambda x:"All Sections" if x=="All" else SECTION_FULL[x])
ft = fc2.text_input("Topic keyword")
fe = fc3.selectbox("Error type", ["All","Conceptual","Calculation","Time pressure","Wrong reading","Guessed","Silly","Trap"])

filt = qs
if fs!="All":  filt = [q for q in filt if q.get("section")==fs]
if ft:         filt = [q for q in filt if ft.lower() in q.get("topic","").lower()]
if fe!="All":  filt = [q for q in filt if fe.lower() in q.get("error_type","").lower()]

st.markdown(f"**{len(filt)} questions**")
ECOL = {"Conceptual":"#ef4444","Calculation":"#f59e0b","Time":"#8b5cf6","Wrong":"#3b82f6","Guessed":"#6b7280","Silly":"#f97316","Trap":"#ec4899"}
for q in filt[:60]:
    ec = next((v for k,v in ECOL.items() if k.lower() in q.get("error_type","").lower()), "#aaa")
    with st.expander(f"[{SECTION_FULL.get(q.get('section','?'),'?')} · {q.get('topic','?')}] {q.get('question_text','')[:80]}... — {q.get('date','')}"):
        c1,c2 = st.columns([4,1])
        c1.markdown(f"**Q:** {q.get('question_text','')}")
        c1.markdown(f"**Your ans:** {q.get('your_answer','—')}  |  **Correct:** {q.get('correct_answer','—')}")
        c1.markdown(f"**Error:** <span style='color:{ec};font-weight:600'>{q.get('error_type','—')}</span>", unsafe_allow_html=True)
        if q.get("note"): c1.markdown(f"**Note:** {q.get('note')}")
        if c2.button("🗑️",key=f"dq_{q.get('id')}"):
            del_question(q.get("id")); st.rerun()
