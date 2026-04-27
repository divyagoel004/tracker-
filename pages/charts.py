from datetime import date
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.db import all_tests, get_profile, test_score, section_stats, topic_stats
from utils.ui import SECTION_FULL, SECTION_ICON

st.markdown('<p class="page-title">📈 Progress Charts</p>', unsafe_allow_html=True)

profile = get_profile()
tests = sorted(all_tests(), key=lambda x: x.get("date",""))
if len(tests) < 2:
    st.info("Log at least 2 tests to see charts."); st.stop()

target = profile.get("target_score",160) if profile else 160
scores = [test_score(t) for t in tests]
xlabels = [f"{t.get('test_name','?')}\n{t.get('date','')}" for t in tests]

SEC_COLORS = {"quant":"#667eea","english":"#22c55e","reasoning":"#f59e0b","gk":"#ef4444"}

# ── Score trend ────────────────────────────────────────────────────────────────
st.markdown("### 📊 Score Trend")
def ma(data, n=3):
    return [round(sum(data[max(0,i-n+1):i+1])/(i-max(0,i-n+1)+1),1) for i in range(len(data))]

fig=go.Figure()
fig.add_trace(go.Scatter(x=xlabels,y=scores,mode="lines+markers",name="Score",line=dict(color="#667eea",width=2),marker=dict(size=7)))
fig.add_trace(go.Scatter(x=xlabels,y=ma(scores),mode="lines",name="3-test avg",line=dict(color="#f59e0b",width=2,dash="dot")))
fig.add_hline(y=target,line_dash="dash",line_color="#22c55e",annotation_text=f"Target {target}",annotation_position="right")
fig.update_layout(height=300,margin=dict(l=0,r=80,t=20,b=60),xaxis_tickangle=-20,
    plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",yaxis_range=[0,205],yaxis_title="Score /200")
st.plotly_chart(fig,use_container_width=True)

# ── Section scores ─────────────────────────────────────────────────────────────
st.markdown("### 📐 Section Net Scores")
fig2=go.Figure()
for sec in ["quant","english","reasoning","gk"]:
    sec_scores=[t.get("sections",{}).get(sec,{}).get("net_score",0) for t in tests]
    fig2.add_trace(go.Scatter(x=xlabels,y=sec_scores,mode="lines+markers",name=SECTION_FULL[sec].split("/")[0],line=dict(color=SEC_COLORS[sec],width=2),marker=dict(size=6)))
fig2.add_hline(y=target/4,line_dash="dash",line_color="#888",annotation_text=f"Sec target {round(target/4)}")
fig2.update_layout(height=300,margin=dict(l=0,r=80,t=20,b=60),xaxis_tickangle=-20,
    plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",yaxis_range=[-5,28],yaxis_title="Net score /25")
st.plotly_chart(fig2,use_container_width=True)

# ── Accuracy trend ─────────────────────────────────────────────────────────────
st.markdown("### 🎯 Accuracy Trend")
fig3=go.Figure()
for sec in ["quant","english","reasoning","gk"]:
    accs=[]
    for t in tests:
        sd=t.get("sections",{}).get(sec,{})
        att=sd.get("attempted",0); cor=sd.get("correct",0)
        accs.append(round(cor/att*100) if att else 0)
    fig3.add_trace(go.Scatter(x=xlabels,y=accs,mode="lines+markers",name=SECTION_FULL[sec].split("/")[0],line=dict(color=SEC_COLORS[sec],width=2),marker=dict(size=6)))
fig3.add_hline(y=70,line_dash="dash",line_color="#22c55e",annotation_text="70% target")
fig3.update_layout(height=300,margin=dict(l=0,r=80,t=20,b=60),xaxis_tickangle=-20,
    plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",yaxis_range=[0,105],yaxis_title="Accuracy %")
st.plotly_chart(fig3,use_container_width=True)

# ── Topic heatmap ──────────────────────────────────────────────────────────────
st.markdown("### 🔥 Topic Accuracy Heatmap")
ts = topic_stats(tests)
heat = [{"Topic":f"{s[:2].upper()}: {t}","Acc":v["acc"],"Att":v["avg_att"]} for (s,t),v in ts.items() if v["avg_att"]>0]
if heat:
    df=pd.DataFrame(heat).sort_values("Acc")
    fig4=go.Figure(go.Bar(x=df["Acc"],y=df["Topic"],orientation="h",
        marker=dict(color=df["Acc"],colorscale=[[0,"#ef4444"],[0.5,"#f59e0b"],[1,"#22c55e"]],cmin=0,cmax=100),
        text=[f"{a}%" for a in df["Acc"]],textposition="outside"))
    fig4.update_layout(height=max(300,len(heat)*22),margin=dict(l=0,r=60,t=20,b=0),
        plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",xaxis_range=[0,115],xaxis_title="Accuracy %")
    st.plotly_chart(fig4,use_container_width=True)

# ── Stats table ────────────────────────────────────────────────────────────────
st.markdown("### 📋 All-Time Stats")
ss=section_stats(tests)
rows=[{"Section":SECTION_FULL[sec],"Avg Att":s.get("avg_att","—"),"Avg Correct":s.get("avg_cor","—"),"Avg Wrong":s.get("avg_wrg","—"),"Avg Accuracy":f"{s.get('avg_acc','—')}%","Avg Score /25":s.get("avg_net","—"),"Tests":s.get("n","—")} for sec,s in ss.items()]
st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
