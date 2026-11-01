"""Learning progress, edition history and the saved paper plan.

progress.json tracks any number of subjects (e.g. "German", "Vocabulary"),
each with spaced-repetition items and short running notes, so lessons build
on each other. plan.json is the paper's layout, designed by the agent from
the reader's wishes and reused until the wishes change.
"""

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

# Days until the next review after each successful repetition.
INTERVALS = [1, 3, 7, 21, 60, 180]


def empty() -> dict:
    return {"edition": 0, "streak_dates": [], "subjects": {}, "history": []}


def load(path: Path) -> dict:
    if not path.exists():
        return empty()
    st = json.loads(path.read_text())
    if "words" in st:  # pre-subjects format: one flat vocabulary list
        items = [{"term": w["word"], **{k: w[k] for k in ("meaning", "added", "reps", "next_review")}}
                 for w in st.pop("words")]
        st["subjects"] = {"Vocabulary": {"items": items, "notes": []}} if items else {}
        st["history"] = [{"date": h["date"], "edition": h["edition"],
                          "covered": [x for x in (h.get("lesson"), h.get("speaking")) if x],
                          "for_tomorrow": h.get("drill_answers", [])} for h in st["history"]]
    return st


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def wishes_hash(cfg: dict) -> str:
    """Changes whenever the reader edits what they want from the paper."""
    basis = json.dumps([cfg.get("reader"), cfg.get("wishes"), cfg.get("sources"),
                        (cfg.get("paper") or {}).get("pages", 2)], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode()).hexdigest()[:12]


def context(st: dict, plan: dict | None, cfg: dict, today: date) -> dict:
    """Everything the agent needs to write today's edition."""
    h = wishes_hash(cfg)
    subjects = {}
    for name, s in st["subjects"].items():
        due = [i for i in s["items"] if date.fromisoformat(i["next_review"]) <= today]
        due.sort(key=lambda i: i["next_review"])
        subjects[name] = {
            "due_for_review": [{"term": i["term"], "meaning": i["meaning"]} for i in due[:5]],
            "known_terms": [i["term"] for i in s["items"]],
            "recent_notes": s["notes"][-7:],
        }
    history = st["history"]
    return {
        "today": today.isoformat(),
        "edition": st["edition"] + 1,
        "wishes_hash": h,
        "replan": plan is None or plan.get("wishes_hash") != h,
        "plan": plan,
        "subjects": subjects,
        "recently_covered": [c for e in history[-21:] for c in e.get("covered", [])],
        "yesterday_for_tomorrow": history[-1].get("for_tomorrow", []) if history else [],
    }


def record(st: dict, content: dict, today: date) -> dict:
    """Fold a finished edition into the state."""
    iso = today.isoformat()
    if any(e["date"] == iso for e in st["history"]):
        return st

    for entry in content.get("learning", []):
        subj = st["subjects"].setdefault(entry["subject"], {"items": [], "notes": []})
        known = {i["term"].lower(): i for i in subj["items"]}
        for term in entry.get("reviewed", []):
            if i := known.get(term.lower()):
                i["reps"] += 1
                step = INTERVALS[min(i["reps"], len(INTERVALS) - 1)]
                i["next_review"] = (today + timedelta(days=step)).isoformat()
        for new in entry.get("introduced", []):
            if new["term"].lower() not in known:
                subj["items"].append({
                    "term": new["term"], "meaning": new["meaning"], "added": iso,
                    "reps": 0, "next_review": (today + timedelta(days=INTERVALS[0])).isoformat(),
                })
        if entry.get("note"):
            subj["notes"].append({"date": iso, "note": entry["note"]})

    st["edition"] += 1
    st["streak_dates"].append(iso)
    st["history"].append({
        "date": iso,
        "edition": st["edition"],
        "covered": content.get("covered", []),
        "for_tomorrow": content.get("for_tomorrow", []),
    })
    return st
