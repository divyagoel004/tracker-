import json
from datetime import date, datetime, timedelta
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://divyagoellcs_db_user:bTMkq329XwGtNDSG@cluster0.jmt0zun.mongodb.net/?appName=Cluster0"

_mongo_client = None
def _col():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)
    return _mongo_client["ssc_tracker"]["data"]

def _r(p):
    key = p.replace(".json", "")
    doc = _col().find_one({"_id": key})
    if doc:
        return doc["value"]
    return [] if p.endswith("s.json") else {}

def _w(p, d):
    key = p.replace(".json", "")
    _col().update_one({"_id": key}, {"$set": {"value": d}}, upsert=True)

# ── profile ────────────────────────────────────────────────────────────────────
def get_profile(): return _r("profile.json")
def set_profile(d): _w("profile.json", d)

# ── tests ──────────────────────────────────────────────────────────────────────
def all_tests(): return _r("tests.json")

def add_test(t):
    tests = all_tests()
    if "id" not in t:
        t["id"] = f"t_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    t.setdefault("created_at", datetime.now().isoformat())
    tests.append(t)
    _w("tests.json", tests)
    return t["id"]

def del_test(tid): _w("tests.json", [t for t in all_tests() if t.get("id") != tid])

def tests_on(day): return [t for t in all_tests() if t.get("date") == day]

def tests_in_week(y, w):
    out = []
    for t in all_tests():
        try:
            d = date.fromisoformat(t["date"])
            if d.isocalendar()[:2] == (y, w): out.append(t)
        except: pass
    return out

def tests_in_range(start: date, end: date):
    out = []
    for t in all_tests():
        try:
            d = date.fromisoformat(t["date"])
            if start <= d <= end: out.append(t)
        except: pass
    return out

# ── questions ──────────────────────────────────────────────────────────────────
def all_questions(): return _r("questions.json")

def add_question(q):
    qs = all_questions()
    if "id" not in q:
        q["id"] = f"q_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    q.setdefault("created_at", datetime.now().isoformat())
    qs.append(q)
    _w("questions.json", qs)

def del_question(qid): _w("questions.json", [q for q in all_questions() if q.get("id") != qid])

def questions_on(day): return [q for q in all_questions() if q.get("date") == day]

def questions_in_dates(dates):
    ds = set(dates)
    return [q for q in all_questions() if q.get("date") in ds]

# ── schedule ───────────────────────────────────────────────────────────────────
def get_schedule(): return _r("schedule.json")
def set_schedule(d): _w("schedule.json", d)

# ── reports cache ──────────────────────────────────────────────────────────────
def get_reports():
    doc = _col().find_one({"_id": "reports"})
    return doc["value"] if doc and isinstance(doc.get("value"), dict) else {}

def cache_report(kind, key, text, meta=None):
    r = get_reports()
    r.setdefault(kind, {})[key] = {
        "text": text, "at": datetime.now().isoformat(), "meta": meta or {}
    }
    _w("reports.json", r)

def get_cached(kind, key):
    return get_reports().get(kind, {}).get(key)

# ── analytics helpers ──────────────────────────────────────────────────────────
def test_score(t):
    s = 0
    for sd in t.get("sections", {}).values():
        s += sd.get("correct", 0) - 0.5 * sd.get("wrong", 0)
    return round(s, 1)

def section_stats(tests):
    out = {}
    for sec in ["quant", "english", "reasoning", "gk"]:
        rows = [t["sections"][sec] for t in tests if sec in t.get("sections", {}) and t["sections"][sec].get("attempted", 0) > 0]
        if not rows:
            out[sec] = {}; continue
        out[sec] = {
            "avg_att":  round(sum(r["attempted"] for r in rows) / len(rows), 1),
            "avg_cor":  round(sum(r["correct"]   for r in rows) / len(rows), 1),
            "avg_wrg":  round(sum(r["wrong"]     for r in rows) / len(rows), 1),
            "avg_acc":  round(sum(r["correct"] / r["attempted"] * 100 for r in rows) / len(rows), 1),
            "avg_time": round(sum(r.get("time_used", 15) for r in rows) / len(rows), 1),
            "avg_net":  round(sum(r["correct"] - 0.5 * r["wrong"] for r in rows) / len(rows), 1),
            "n": len(rows)
        }
    return out

def topic_stats(tests):
    agg = {}
    for t in tests:
        for sec, rows in t.get("topic_data", {}).items():
            for r in rows:
                if not r.get("attempted"): continue
                k = (sec, r["topic"])
                if k not in agg: agg[k] = {"att": [], "cor": [], "wrg": [], "feel": []}
                agg[k]["att"].append(r["attempted"])
                agg[k]["cor"].append(r["correct"])
                agg[k]["wrg"].append(r["wrong"])
                agg[k]["feel"].append(r.get("feel", "?"))
    out = {}
    for (sec, topic), v in agg.items():
        n = len(v["att"])
        avg_att = sum(v["att"]) / n
        avg_cor = sum(v["cor"]) / n
        avg_wrg = sum(v["wrg"]) / n
        acc = round(avg_cor / avg_att * 100) if avg_att else 0
        out[(sec, topic)] = {
            "avg_att": round(avg_att, 1), "avg_cor": round(avg_cor, 1),
            "avg_wrg": round(avg_wrg, 1), "acc": acc,
            "feel": max(set(v["feel"]), key=v["feel"].count),
            "marks_lost": round((avg_wrg * 0.5 + (avg_att - avg_cor - avg_wrg)), 2),
            "n": n
        }
    return out

def active_test_dates():
    return sorted(set(t.get("date", "") for t in all_tests() if t.get("date")), reverse=True)
