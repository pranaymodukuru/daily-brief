"""Learning progress: vocabulary with spaced repetition, plus edition history."""

import json
from datetime import date, timedelta
from pathlib import Path

# Days until the next review after each successful repetition.
INTERVALS = [1, 3, 7, 21, 60, 180]

EMPTY = {"edition": 0, "streak_dates": [], "words": [], "history": []}


def load(path: Path) -> dict:
    if not path.exists():
        return json.loads(json.dumps(EMPTY))
    return json.loads(path.read_text())


def save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def due_words(state: dict, today: date, limit: int) -> list[dict]:
    due = [w for w in state["words"] if date.fromisoformat(w["next_review"]) <= today]
    due.sort(key=lambda w: w["next_review"])
    return due[:limit]


def context(state: dict, today: date, max_review: int) -> dict:
    """What the agent needs to write today's edition without repeating itself."""
    history = state["history"]
    return {
        "today": today.isoformat(),
        "edition": state["edition"] + 1,
        "review_words": [
            {"word": w["word"], "meaning": w["meaning"]}
            for w in due_words(state, today, max_review)
        ],
        "known_words": [w["word"] for w in state["words"]],
        "recent_lessons": [h["lesson"] for h in history[-30:] if h.get("lesson")],
        "recent_speaking_prompts": [h["speaking"] for h in history[-30:] if h.get("speaking")],
        "yesterday_drill_answers": history[-1]["drill_answers"] if history else [],
    }


def record(state: dict, content: dict, today: date) -> dict:
    """Fold a finished edition into the state: add new words, advance reviews."""
    iso = today.isoformat()
    if any(h["date"] == iso for h in state["history"]):
        return state

    known = {w["word"].lower(): w for w in state["words"]}
    for item in content.get("review_words", []):
        w = known.get(item["word"].lower())
        if w:
            w["reps"] += 1
            step = INTERVALS[min(w["reps"], len(INTERVALS) - 1)]
            w["next_review"] = (today + timedelta(days=step)).isoformat()
    for item in content.get("words", []):
        if item["word"].lower() not in known:
            state["words"].append({
                "word": item["word"],
                "meaning": item["meaning"],
                "added": iso,
                "reps": 0,
                "next_review": (today + timedelta(days=INTERVALS[0])).isoformat(),
            })

    state["edition"] += 1
    state["streak_dates"].append(iso)
    state["history"].append({
        "date": iso,
        "edition": state["edition"],
        "lesson": (content.get("lesson") or {}).get("title"),
        "speaking": (content.get("speaking") or {}).get("prompt"),
        "drill_answers": (content.get("drill") or {}).get("answers", []),
    })
    return state
