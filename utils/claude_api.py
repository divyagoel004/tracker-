import google.generativeai as genai
import streamlit as st
from utils.db import section_stats, topic_stats, test_score

SECTION_FULL = {
    "quant":     "Quantitative Aptitude",
    "english":   "English Language",
    "reasoning": "General Intelligence & Reasoning",
    "gk":        "General Awareness / GK",
}

def _fmt_tests(tests):
    lines = []
    for t in tests:
        sc = test_score(t)
        secs = t.get("sections", {})
        row = f"  [{t.get('date')}] {t.get('test_name','?')} → {sc}/200"
        for s in ["quant","english","reasoning","gk"]:
            sd = secs.get(s,{})
            row += f" | {s[:2].upper()}: {sd.get('attempted',0)}att/{sd.get('correct',0)}cor/{sd.get('wrong',0)}wrg ({sd.get('time_used',15):.0f}m)"
        if t.get("notes"): row += f" | Note: {t['notes'][:60]}"
        lines.append(row)
    return "\n".join(lines)

def _fmt_topics(tests):
    ts = topic_stats(tests)
    lines = []
    for sec in ["quant","english","reasoning","gk"]:
        sec_lines = []
        for (s, topic), v in ts.items():
            if s != sec: continue
            flag = "🔴" if v["acc"]<40 else "🟠" if v["acc"]<65 else "🟡" if v["acc"]<80 else "🟢"
            sec_lines.append(f"    {flag} {topic:<32} att:{v['avg_att']:.1f} cor:{v['avg_cor']:.1f} wrg:{v['avg_wrg']:.1f} acc:{v['acc']}% marks_lost:{v['marks_lost']:.1f} feel:{v['feel']}")
        if sec_lines:
            lines.append(f"\n  {SECTION_FULL[sec]}:")
            lines.extend(sorted(sec_lines, key=lambda x: int(x.split("acc:")[1].split("%")[0])))
    return "\n".join(lines)

def _fmt_questions(qs):
    if not qs: return "  None logged."
    lines = []
    for q in qs[-30:]:
        lines.append(f"  [{q.get('section','?').upper()} | {q.get('topic','?')}] {q.get('error_type','?').split('(')[0][:25]}: {q.get('question_text','')[:100]} | Correct: {q.get('correct_answer','—')} | Note: {q.get('note','')[:60]}")
    return "\n".join(lines)

def _fmt_section_stats(tests):
    ss = section_stats(tests)
    lines = []
    for sec, v in ss.items():
        if not v: continue
        lines.append(f"  {SECTION_FULL[sec]}: avg_attempted={v['avg_att']} avg_correct={v['avg_cor']} avg_wrong={v['avg_wrg']} accuracy={v['avg_acc']}% avg_net={v['avg_net']}/25 avg_time={v['avg_time']}m (n={v['n']} tests)")
    return "\n".join(lines)

# ── DAILY DEEP ANALYSIS ────────────────────────────────────────────────────────
def daily_prompt(day_tests, day_qs, profile, target_date, sched_today=None):
    scores = [test_score(t) for t in day_tests]
    avg_sc = round(sum(scores)/len(scores),1) if scores else 0
    target = profile.get("target_score",160)
    gap = round(target - avg_sc, 1)
    days_left = profile.get("days_remaining", "?")

    sched_block = ""
    if sched_today:
        slines = [f"  - {s['title']} ({s['duration_min']} min) [{s['priority']}]" for s in sched_today.get("sessions",[])]
        sched_block = f"\nTODAY'S SCHEDULED PLAN:\n" + "\n".join(slines)

    return f"""You are an expert SSC CGL coach. Generate a DEEP DAILY REPORT for {target_date}.

STUDENT: Exam={profile.get('tier','Tier 1')} | Date={profile.get('exam_date')} | Target={target}/200 | Days left={days_left}
FORMAT: 15 min/section strict, no carry-over, -0.5 negative marking.

TODAY'S TESTS ({len(day_tests)} test(s), avg={avg_sc}/200, gap from target={gap:+}):
{_fmt_tests(day_tests)}

TODAY'S TOPIC BREAKDOWN:
{_fmt_topics(day_tests)}

SECTION STATS TODAY:
{_fmt_section_stats(day_tests)}

DIFFICULT QUESTIONS LOGGED TODAY ({len(day_qs)}):
{_fmt_questions(day_qs)}
{sched_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate the DEEP DAILY REPORT in this EXACT structure:

## 📊 Daily Scorecard
- Score for each test today. Average vs target. Gap analysis.
- Section-by-section net score table with verdict: ✅ On track / ⚠️ Needs work / 🔴 Critical

## 🔬 Deep Section Analysis

### Quant Analysis
- Accuracy %. Attempt rate. Time situation (ran out / finished early / optimal).
- Exact topics that hurt today. Was the 3-pass system followed?
- Topics attempted that should have been skipped. Topics skipped that were easy.

### English Analysis
- Accuracy %. Which question type is dragging the score?
- Was the within-section order correct (RC first, vocab last)?

### Reasoning Analysis
- Accuracy %. Fast topics vs time-heavy topics breakdown.
- Puzzles/Seating: attempted or skipped? Right call?

### GK/GS Analysis
- Was GK maxed out? How many left unattempted?
- Topics correct vs wrong. Current affairs vs Static GK split.

## 🧠 Error Pattern Analysis
Categorise today's difficult questions:
- Conceptual gaps (list topics): ...
- Calculation errors (recurring?): ...
- Time pressure errors: ...
- Careless/silly mistakes: ...
- Overall: what is the DOMINANT error pattern today?

## 🎯 15-Min Format Compliance Score
Rate today's performance on the 15-min format: /10
- Which sections ran over time?
- Which sections had poor question ordering?
- What needs to change in tomorrow's mock strategy?

## ✅ Today's Wins (be specific)
List 2-3 concrete things that went well. Use actual numbers.

## 🔴 Today's Critical Findings
Top 2-3 most urgent issues. Each must have:
  - The problem (with numbers)
  - Root cause
  - Immediate fix

## 📋 Tomorrow's Action Plan
Exactly 3 actions, each with:
  1. **[Section/Topic]** What to do → How long → Target metric
  2. **[Section/Topic]** What to do → How long → Target metric
  3. **[Section/Topic]** What to do → How long → Target metric

## 💡 Technique Tips
For the 2 weakest topics today, give one specific shortcut or technique.

## 📈 Running Score Projection
At today's performance level, projected exam score: X/200
What needs to change to hit {target}: [specific 1-2 actions]

Keep it structured, specific, and data-driven. Every claim must reference the actual numbers above."""

# ── WEEKLY DEEP REPORT ─────────────────────────────────────────────────────────
def weekly_prompt(week_tests, week_qs, profile, week_label, sched_next_week=None):
    scores = [test_score(t) for t in week_tests]
    dates = sorted(set(t.get("date","") for t in week_tests))
    target = profile.get("target_score",160)

    next_week_block = ""
    if sched_next_week:
        days_block = []
        for day in sched_next_week[:7]:
            sess = [f"    • {s['title']}" for s in day.get("sessions",[])[:3]]
            days_block.append(f"  {day['weekday']} ({day['date']}):\n" + "\n".join(sess))
        next_week_block = "\nSCHEDULED PLAN FOR NEXT WEEK:\n" + "\n".join(days_block)

    return f"""You are an expert SSC CGL coach. Generate a COMPREHENSIVE WEEKLY REPORT.

STUDENT: Exam={profile.get('tier','Tier 1')} | Date={profile.get('exam_date')} | Target={target}/200 | Days left={profile.get('days_remaining','?')}
WEEK: {week_label} | Study days: {len(dates)} | Tests taken: {len(week_tests)}
FORMAT: 15 min/section strict, no carry-over, -0.5 negative marking.

ALL TESTS THIS WEEK:
{_fmt_tests(week_tests)}

SECTION STATISTICS THIS WEEK:
{_fmt_section_stats(week_tests)}

TOPIC-WISE AVERAGES THIS WEEK:
{_fmt_topics(week_tests)}

ALL DIFFICULT QUESTIONS THIS WEEK ({len(week_qs)}):
{_fmt_questions(week_qs)}
{next_week_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate the DEEP WEEKLY REPORT:

## 📈 Weekly Progress Overview
- Score trend: first test → last test. Direction: improving/plateauing/declining.
- Best day and worst day — what caused the difference?
- Weekly avg vs target gap. Is the gap closing or widening?

## 🏆 Section Leaderboard This Week
Rank all 4 sections. For each:
| Section | Avg Score | Avg Accuracy | Time Status | Trend | Verdict |
Show as a proper table. Be specific with numbers.

## 🔴 Top 5 Weak Topics (This Week)
For each: topic name | avg accuracy | marks being lost | root cause | fix
Sorted by marks impact (highest loss first).

## 📈 Top 3 Improved Topics
What actually got better compared to the general difficulty. With numbers.

## 🧠 Mistake Pattern Deep-Dive
From all {len(week_qs)} questions logged:
- Error type breakdown (% conceptual / % calculation / % time / % careless)
- Which sections have which error types? (e.g., Quant = 60% conceptual, Reasoning = 70% careless)
- Recurring mistake pattern (same topic wrong multiple days?)
- One insight that the student might have missed

## ⏱️ 15-Min Sectional Compliance
- Which section has the worst time management?
- Is attempt rate too high (risking negatives) or too low (leaving marks)?
- Optimal attempt target per section based on this week's data.

## 📊 GK Assessment
- Average attempted vs possible (25). Marks left on table per test.
- Is GK being treated as the highest-ROI section?
- Topics within GK that are weak.

## 🗓️ Next Week's Focused Plan
Based on this week's data:
1. **Primary focus topic** (most critical to fix): [topic] → daily target → study approach
2. **Secondary focus topic**: [topic] → daily target → study approach
3. **Section to sectional drill**: [section] → 15-min drills → frequency
4. **Mock test target**: X mocks next week | target score: X/200
5. **GK daily target**: X questions/day | focus areas

## 📊 Schedule Compliance Check (if scheduled plan existed)
- Was the schedule followed? Which sessions were likely skipped?
- Impact of any missed sessions on this week's performance.

## 🎯 Honest Exam Projection
Current average: {round(sum(scores)/len(scores),1) if scores else '?'}/200
Week-on-week improvement rate: X points/week
At this rate, projected exam score: X/200
To hit {target}/200, need to gain: X points
Feasibility assessment: Achievable with X / Challenging / At risk
What needs to change immediately: [1 specific action]

Be comprehensive, structured, and data-driven. Use the actual numbers."""

# ── DEEP ANALYSIS (on-demand) ──────────────────────────────────────────────────
def deep_analysis_prompt(all_tests_data, all_qs, profile, analysis_focus):
    scores = [test_score(t) for t in all_tests_data]
    target = profile.get("target_score",160)
    return f"""You are an expert SSC CGL coach. Perform a COMPREHENSIVE DEEP ANALYSIS across all available data.

STUDENT: {profile.get('name','Student')} | Exam={profile.get('tier','Tier 1')} | Date={profile.get('exam_date')} | Target={target}/200 | Days left={profile.get('days_remaining','?')}
TOTAL TESTS ANALYSED: {len(all_tests_data)} | DATE RANGE: {min(t.get('date','') for t in all_tests_data) if all_tests_data else '?'} to {max(t.get('date','') for t in all_tests_data) if all_tests_data else '?'}

ALL TEST DATA:
{_fmt_tests(all_tests_data[-20:])}

SECTION STATISTICS (ALL TIME):
{_fmt_section_stats(all_tests_data)}

TOPIC STATISTICS (ALL TIME):
{_fmt_topics(all_tests_data)}

QUESTION BANK ({len(all_qs)} entries):
{_fmt_questions(all_qs)}

FOCUS AREA: {analysis_focus}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate a DEEP COMPREHENSIVE ANALYSIS:

## 🔍 Complete Performance Diagnosis
Full section-by-section diagnosis. For each section:
- Current level vs required level
- Core problem (speed? accuracy? concept? strategy?)
- Specific evidence from the data

## 📉 Critical Weak Links (sorted by exam impact)
Top 5 topics costing the most marks overall. For each:
- Mark loss quantified
- Why this keeps happening (pattern from error logs)
- Exact fix with timeline

## 📈 Growth Curve Analysis
- Score trend across all tests. Actual numbers.
- Which sections have improved. Which are stuck.
- Rate of improvement: is it fast enough to hit target by exam date?

## 🎯 Attempt Strategy Diagnosis
- For each section: is the student over-attempting, under-attempting, or optimal?
- Specific recommendations for the 15-min format
- Expected score gain from fixing attempt strategy alone

## ⚡ Quick Wins (next 7 days)
Topics where 3-5 days of focused work = significant score gain.
For each: current acc% → realistic target acc% → marks gain.

## 🗺️ Strategic Recommendations
Given the exam date and current level:
1. Which sections to invest the most time in
2. Which topics to permanently skip (low ROI in 15 min format)
3. Daily non-negotiables (must-do every single day)
4. Red flags that need immediate attention

## 📊 Exam Day Strategy
Given this student's current profile, recommend:
- Optimal section attempt order
- Within-section question order for each section
- Attempt targets per section
- When to skip vs attempt (specific to their weak topics)
- Expected score range: pessimistic / realistic / optimistic

Be the most specific, actionable coach this student has ever had."""

# ── Streaming ──────────────────────────────────────────────────────────────────
def stream(prompt, api_key, placeholder):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    full = ""
    response = model.generate_content(prompt, stream=True)
    for chunk in response:
        if chunk.text:
            full += chunk.text
            placeholder.markdown(full)
    return full
