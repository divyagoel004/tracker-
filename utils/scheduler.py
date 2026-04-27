"""
Schedule engine — builds a full daily study schedule from:
  - exam date
  - available days/hours
  - weak topics (from analytics)
  - user preferences
"""
from datetime import date, timedelta
from utils.db import get_schedule, set_schedule, topic_stats, section_stats, all_tests, get_profile

SECTION_FULL = {
    "quant": "Quantitative Aptitude",
    "english": "English Language",
    "reasoning": "General Intelligence & Reasoning",
    "gk": "General Awareness / GK",
}

QUANT_TOPICS  = ["Percentage","Ratio & Proportion","Profit & Loss","SI/CI",
                  "Time & Work","Time Speed Distance","Number System","Algebra",
                  "Geometry/Mensuration","Trigonometry","DI"]
ENGLISH_TOPICS = ["Reading Comprehension","Cloze Test","Error Spotting",
                   "Sentence Improvement","Synonyms/Antonyms","Idioms & Phrases",
                   "Para Jumbles","One Word Substitution"]
REASONING_TOPICS = ["Analogy","Number Series","Letter Series","Coding-Decoding",
                     "Syllogism","Blood Relations","Puzzles & Seating",
                     "Direction Sense","Matrix/Mirror","Venn Diagrams"]
GK_TOPICS = ["History","Geography","Polity","Economics",
             "Physics","Chemistry","Biology","Current Affairs","Static GK"]

SECTION_TOPICS = {
    "quant": QUANT_TOPICS, "english": ENGLISH_TOPICS,
    "reasoning": REASONING_TOPICS, "gk": GK_TOPICS
}

# 15-min format skip list for Quant
QUANT_SKIP = ["Geometry/Mensuration", "Trigonometry"]
QUANT_FAST = ["Percentage","Ratio & Proportion","Profit & Loss","SI/CI","Number System"]

DAYS_MAP = {
    "Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,
    "Friday":4,"Saturday":5,"Sunday":6
}

def classify_topic(sec, topic, tstats):
    s = tstats.get((sec, topic))
    if not s: return "unknown"
    acc = s["acc"]
    if acc < 40: return "critical"
    if acc < 65: return "weak"
    if acc < 80: return "moderate"
    return "strong"

def priority_topics(tests, n=15):
    """Return top-N topics sorted by marks lost (impact)."""
    tstats = topic_stats(tests)
    ranked = sorted(tstats.items(), key=lambda x: -x[1]["marks_lost"])
    return [(sec, topic, data) for (sec, topic), data in ranked][:n]

def build_schedule(config: dict) -> dict:
    """
    config keys:
      exam_date, study_days (list of weekday names), hours_per_day,
      mock_days (list of weekday names), weak_sections (list),
      focus_mode ('balanced'|'weak_first'|'strong_first'),
      include_revision_day (bool), tests (list of test dicts)
    """
    today = date.today()
    exam  = date.fromisoformat(config["exam_date"])
    days_left = (exam - today).days
    if days_left <= 0:
        return {"error": "Exam date is in the past."}

    study_days  = config.get("study_days", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"])
    hours_pd    = config.get("hours_per_day", 4)
    mock_days   = config.get("mock_days", ["Saturday","Sunday"])
    focus       = config.get("focus_mode", "weak_first")
    weak_secs   = config.get("weak_sections", [])
    tests       = config.get("tests", all_tests())
    target      = config.get("target_score", 160)
    revision_day = config.get("include_revision_day", True)

    # Analyse weak areas
    tstats = topic_stats(tests)
    sstats = section_stats(tests)

    # Classify all topics
    topic_priority = []
    for sec in ["quant","english","reasoning","gk"]:
        for topic in SECTION_TOPICS[sec]:
            cls = classify_topic(sec, topic, tstats)
            ts = tstats.get((sec, topic), {})
            topic_priority.append({
                "sec": sec, "topic": topic, "class": cls,
                "acc": ts.get("acc", -1), "marks_lost": ts.get("marks_lost", 0),
                "feel": ts.get("feel", "unknown")
            })

    # Sort by priority
    order = {"critical": 0, "weak": 1, "moderate": 2, "strong": 3, "unknown": 4}
    if focus == "weak_first":
        topic_priority.sort(key=lambda x: (order[x["class"]], -x["marks_lost"]))
    elif focus == "strong_first":
        topic_priority.sort(key=lambda x: (-x["acc"],))
    else:  # balanced
        topic_priority.sort(key=lambda x: (order[x["class"]], -x["marks_lost"]))

    # Build day-by-day plan
    phases = _compute_phases(days_left, hours_pd)
    calendar = []
    topic_queue = list(topic_priority)
    tq_idx = 0
    week_mock_count = 0
    d = today

    while d < exam:
        weekday = d.strftime("%A")
        if weekday not in study_days:
            d += timedelta(days=1)
            continue

        is_mock_day  = weekday in mock_days
        is_last_2wks = (exam - d).days <= 14
        phase = _get_phase(days_left, (d - today).days, phases)

        entry = {
            "date": d.isoformat(),
            "weekday": weekday,
            "phase": phase,
            "is_mock_day": is_mock_day,
            "hours": hours_pd,
            "sessions": []
        }

        if is_mock_day:
            entry["sessions"].append({
                "type": "mock", "duration_min": 60,
                "title": "Full Mock Test (4×15 min strict timer)",
                "detail": "Do all 4 sections as separate 15-min blocks. No free flow. Log results immediately after.",
                "priority": "high"
            })
            entry["sessions"].append({
                "type": "review", "duration_min": 90,
                "title": "Mock Review & Error Logging",
                "detail": "Review every wrong answer. Understand the concept. Log difficult questions in app.",
                "priority": "high"
            })
            if hours_pd > 3:
                # Add GK on mock days always
                entry["sessions"].append({
                    "type": "gk", "duration_min": 30,
                    "title": "GK Daily Revision",
                    "detail": "20 GK questions timed. Target under 9 min. Focus: Current Affairs + Static GK",
                    "priority": "medium"
                })
        else:
            # Assign topic sessions
            slots = _time_slots(hours_pd, is_last_2wks, revision_day and weekday=="Sunday")
            for slot in slots:
                if slot["type"] == "topic":
                    if tq_idx < len(topic_queue):
                        tp = topic_queue[tq_idx % len(topic_queue)]
                        tq_idx += 1
                        entry["sessions"].append({
                            "type": "topic_study",
                            "duration_min": slot["duration"],
                            "title": f"{SECTION_FULL[tp['sec']]} — {tp['topic']}",
                            "sec": tp["sec"], "topic": tp["topic"],
                            "class": tp["class"], "acc": tp["acc"],
                            "detail": _topic_instruction(tp, phase),
                            "priority": "critical" if tp["class"] == "critical" else "high" if tp["class"] == "weak" else "medium"
                        })
                elif slot["type"] == "sectional":
                    # Pick weakest section for sectional drill
                    ws = _weakest_section(sstats, weak_secs)
                    entry["sessions"].append({
                        "type": "sectional_drill",
                        "duration_min": slot["duration"],
                        "title": f"15-Min Sectional Drill — {SECTION_FULL.get(ws, ws)}",
                        "sec": ws,
                        "detail": "25 questions, strict 15-min timer. Use 3-pass system. Log time left.",
                        "priority": "high"
                    })
                elif slot["type"] == "gk":
                    entry["sessions"].append({
                        "type": "gk_daily",
                        "duration_min": slot["duration"],
                        "title": "GK Daily Drill",
                        "detail": "20 questions timed. Alternate: Current Affairs day / Static GK day.",
                        "priority": "medium"
                    })
                elif slot["type"] == "revision":
                    entry["sessions"].append({
                        "type": "revision",
                        "duration_min": slot["duration"],
                        "title": "Weekly Revision",
                        "detail": "Revise all topics studied this week. Redo any wrong questions from question bank.",
                        "priority": "medium"
                    })
                elif slot["type"] == "speed":
                    entry["sessions"].append({
                        "type": "speed_drill",
                        "duration_min": slot["duration"],
                        "title": "Speed & Calculation Drill",
                        "detail": "Squares/cubes recall, fraction-% table, 20 arithmetic Qs in 10 min.",
                        "priority": "medium"
                    })

        calendar.append(entry)
        d += timedelta(days=1)
        if len(calendar) >= 84:  # cap at 12 weeks display
            break

    sched = {
        "generated_at": date.today().isoformat(),
        "config": config,
        "phases": phases,
        "topic_priority": topic_priority,
        "calendar": calendar,
        "summary": _schedule_summary(calendar, topic_priority, days_left, target, sstats)
    }
    set_schedule(sched)
    return sched

def _compute_phases(days_left, hours_pd):
    if days_left >= 60:
        return [
            {"name":"Foundation","days": days_left-42, "focus":"Concept building + weak topic mastery"},
            {"name":"Practice","days":28,"focus":"Mocks + topic drills + speed building"},
            {"name":"Revision","days":10,"focus":"Full mocks daily + mistake revision"},
            {"name":"Final Sprint","days":4,"focus":"Sectional drills + GK maxing + confidence"},
        ]
    elif days_left >= 30:
        return [
            {"name":"Intensive Practice","days":days_left-14,"focus":"Mocks + weak topics + speed"},
            {"name":"Revision","days":10,"focus":"Full mocks + mistake revision"},
            {"name":"Final Sprint","days":4,"focus":"Sectional drills + GK"},
        ]
    elif days_left >= 14:
        return [
            {"name":"Revision","days":days_left-4,"focus":"Mocks every day + weak topic quick revision"},
            {"name":"Final Sprint","days":4,"focus":"Sectional drills only + GK maxing"},
        ]
    else:
        return [{"name":"Final Sprint","days":days_left,"focus":"Sectional drills + GK + confidence"}]

def _get_phase(total_days, elapsed, phases):
    acc = 0
    for ph in phases:
        acc += ph["days"]
        if elapsed < acc: return ph["name"]
    return phases[-1]["name"]

def _time_slots(hours, is_last_2wks, is_revision_day):
    mins = hours * 60
    slots = []
    if is_revision_day:
        slots.append({"type":"revision","duration":60})
        mins -= 60
    slots.append({"type":"speed","duration":15})
    mins -= 15
    slots.append({"type":"gk","duration":20})
    mins -= 20
    # Fill remaining with topic + sectional alternating
    while mins >= 45:
        if mins >= 90:
            slots.append({"type":"topic","duration":75})
            mins -= 75
        if mins >= 45:
            slots.append({"type":"sectional","duration":20})
            mins -= 20
    return slots

def _weakest_section(sstats, prefer=None):
    if prefer:
        return prefer[0]
    order = sorted(sstats.items(), key=lambda x: x[1].get("avg_acc", 100) if x[1] else 100)
    return order[0][0] if order else "quant"

def _topic_instruction(tp, phase):
    cls = tp["class"]
    topic = tp["topic"]
    sec = tp["sec"]
    acc = tp.get("acc", -1)
    base = {
        "critical": f"CRITICAL ({acc}% accuracy). Restart from basics. Watch 1 concept video → solve 15 easy questions → 10 medium questions. Do NOT attempt hard yet.",
        "weak": f"WEAK ({acc}% accuracy). Revise formula sheet → solve 20 medium questions timed → identify where mistakes happen.",
        "moderate": f"MODERATE ({acc}% accuracy). Solve 15 mixed questions timed. Focus on speed — target under 45 sec/question.",
        "strong": f"STRONG ({acc}% accuracy). Maintenance only — 10 quick questions. Move to next topic fast.",
        "unknown": f"NOT YET TRACKED. Learn the topic basics, solve 15 questions, log data in next mock."
    }
    phase_note = ""
    if phase == "Final Sprint":
        phase_note = " [FINAL SPRINT: Only revise — no new concepts. Do PYQs only.]"
    elif phase == "Revision":
        phase_note = " [REVISION PHASE: Focus on mistakes from question bank.]"
    return base.get(cls, "") + phase_note

def _schedule_summary(calendar, topic_priority, days_left, target, sstats):
    mock_count = sum(1 for d in calendar for s in d["sessions"] if s["type"] == "mock")
    critical = [t for t in topic_priority if t["class"] == "critical"]
    weak = [t for t in topic_priority if t["class"] == "weak"]
    return {
        "total_days": len(calendar),
        "mock_count": mock_count,
        "critical_topics": len(critical),
        "weak_topics": len(weak),
        "top_critical": [f"{t['sec'].upper()}: {t['topic']}" for t in critical[:5]],
        "exam_in_days": days_left,
    }
