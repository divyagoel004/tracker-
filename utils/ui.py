CSS = """
<style>
[data-testid="stSidebarNav"]{display:none}
.block-container{padding-top:1.2rem;padding-bottom:2rem}
.stTabs [data-baseweb="tab"]{font-size:13px;padding:7px 16px}

.page-title{font-size:1.6rem;font-weight:600;margin-bottom:0.2rem;color:var(--text-color)}
.page-sub{font-size:13px;color:#888;margin-bottom:1rem}

.kpi{background:#f8f9ff;border:1px solid #e0e4ff;border-radius:10px;padding:.9rem 1rem;text-align:center}
.kpi-label{font-size:11px;color:#888;margin-bottom:3px;text-transform:uppercase;letter-spacing:.04em}
.kpi-val{font-size:1.6rem;font-weight:600;line-height:1.1}
.kpi-sub{font-size:11px;color:#aaa;margin-top:3px}

.sec-head{border-left:3px solid #667eea;padding:5px 12px;background:linear-gradient(90deg,#667eea18,transparent);border-radius:0 6px 6px 0;font-weight:600;font-size:14px;margin:14px 0 6px}

.tip{background:#fffbeb;border:1px solid #f59e0b44;border-radius:7px;padding:8px 12px;font-size:12px;margin-bottom:10px}

.session-card{border:1px solid #e5e7eb;border-radius:8px;padding:10px 14px;margin-bottom:7px;background:white}
.session-card.critical{border-left:3px solid #ef4444}
.session-card.high{border-left:3px solid #f59e0b}
.session-card.medium{border-left:3px solid #667eea}
.session-card.low{border-left:3px solid #86efac}

.q-card{background:white;border:1px solid #e5e7eb;border-radius:8px;padding:10px 14px;margin-bottom:7px;border-left:3px solid #ef4444}

.badge{display:inline-block;font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px;margin-left:5px}
.b-red{background:#fee2e2;color:#b91c1c}
.b-amber{background:#fef3c7;color:#92400e}
.b-green{background:#d1fae5;color:#065f46}
.b-blue{background:#dbeafe;color:#1e40af}
.b-purple{background:#ede9fe;color:#5b21b6}
.b-gray{background:#f3f4f6;color:#374151}

.report-wrap{background:#f8faff;border-left:4px solid #667eea;border-radius:0 10px 10px 0;padding:1.4rem 1.6rem;line-height:1.85}
</style>
"""

SECTION_FULL = {
    "quant":     "Quantitative Aptitude",
    "english":   "English Language",
    "reasoning": "General Intelligence & Reasoning",
    "gk":        "General Awareness / GK",
}

SECTION_ICON = {"quant":"📐","english":"📖","reasoning":"🧠","gk":"🌍"}

PRIORITY_COLOR = {"critical":"#ef4444","high":"#f59e0b","medium":"#667eea","low":"#22c55e","unknown":"#9ca3af"}

def acc_badge(acc):
    if acc < 0:   return '<span class="badge b-gray">No data</span>'
    if acc < 40:  return f'<span class="badge b-red">🔴 {acc}%</span>'
    if acc < 65:  return f'<span class="badge b-amber">🟠 {acc}%</span>'
    if acc < 80:  return f'<span class="badge b-blue">🟡 {acc}%</span>'
    return f'<span class="badge b-green">🟢 {acc}%</span>'

def score_color(score, max_score=200):
    pct = score / max_score * 100
    if pct >= 75: return "#22c55e"
    if pct >= 55: return "#f59e0b"
    return "#ef4444"
