from datetime import date

from daily_brief import state

DAY1, DAY2 = date(2026, 11, 2), date(2026, 11, 3)


def edition(introduced=(), reviewed=(), note="n", answers=("a",)):
    return {
        "learning": [{"subject": "German",
                      "introduced": [{"term": t, "meaning": t.upper()} for t in introduced],
                      "reviewed": list(reviewed), "note": note}],
        "covered": [note],
        "for_tomorrow": list(answers),
    }


def test_rebuild_replaces_the_days_record():
    st = state.record(state.empty(), edition(["arbeiten", "deshalb"], note="first", answers=["old"]), DAY1)
    st = state.record(st, edition(["arbeiten", "morgen"], note="second", answers=["new"]), DAY1)

    assert st["edition"] == 1
    assert st["streak_dates"] == ["2026-11-02"]
    assert [(e["edition"], e["for_tomorrow"]) for e in st["history"]] == [(1, ["new"])]
    german = st["subjects"]["German"]
    assert [i["term"] for i in german["items"]] == ["arbeiten", "morgen"]
    assert [n["note"] for n in german["notes"]] == ["second"]


def test_rebuild_does_not_double_count_reviews():
    st = state.record(state.empty(), edition(["arbeiten"]), DAY1)
    st = state.record(st, edition(reviewed=["arbeiten"]), DAY2)
    once = dict(st["subjects"]["German"]["items"][0])
    st = state.record(st, edition(reviewed=["arbeiten"]), DAY2)

    assert st["subjects"]["German"]["items"][0] == once
    assert st["edition"] == 2


def test_rebuild_without_the_review_rolls_it_back():
    st = state.record(state.empty(), edition(["arbeiten"]), DAY1)
    before = dict(st["subjects"]["German"]["items"][0])
    st = state.record(st, edition(reviewed=["arbeiten"]), DAY2)
    st = state.record(st, edition(), DAY2)

    assert st["subjects"]["German"]["items"][0] == before


def test_context_plans_a_rebuild_like_the_first_build():
    cfg = {"wishes": "German"}
    st = state.record(state.empty(), edition(["arbeiten"], answers=["day 1 answers"]), DAY1)
    first = state.context(st, None, cfg, DAY2)
    st = state.record(st, edition(["morgen"], answers=["day 2 answers"]), DAY2)
    again = state.context(st, None, cfg, DAY2)

    assert again["edition"] == first["edition"] == 2
    assert again["yesterday_for_tomorrow"] == ["day 1 answers"]
    assert again["subjects"]["German"]["known_terms"] == ["arbeiten"]
    assert len(st["history"]) == 2  # context leaves the saved state alone
