"""Gym analytics send training facts, never health answers.

`client/src/lib/analytics.js` is a privacy contract: event properties are
counts, enums and booleans you could show a stranger. The gym check-in asks
where it hurts and about chest pain — this fails if any gym analytics call
names one of those answers among its properties.
"""
import re
from pathlib import Path

_VIEWS = Path(__file__).resolve().parents[2] / "client" / "src" / "components" / "planViews"
_FORBIDDEN = re.compile(r"pain|flag|injur|unwell|condition|symptom|medical|dosha|pregnan|"
                        r"reason|note|exercise_name|kg\b", re.I)


def _calls(text):
    for m in re.finditer(r"\btrack(?:Once)?\(", text):
        depth, i = 0, m.end() - 1
        while i < len(text):
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            if depth == 0:
                yield text[m.start():i + 1]
                break
            i += 1


def test_no_gym_analytics_call_carries_a_health_answer():
    calls = [c for p in _VIEWS.glob("Gym*.jsx") for c in _calls(p.read_text())]
    assert len(calls) >= 8, "the gym events moved; point this test at them"
    for call in calls:
        props = call.split("EVENTS.", 1)[1]
        assert not _FORBIDDEN.search(props), call


def test_the_guard_can_fire():
    bad = "track(EVENTS.GYM_CHECKIN_SUBMITTED, { week, pain_areas: pain })"
    assert _FORBIDDEN.search(next(_calls(bad)).split("EVENTS.", 1)[1])
