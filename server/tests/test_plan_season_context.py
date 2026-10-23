"""A plan says which Ritu it was built for, so the screen can say when it has passed.

A yoga plan built on 13 August still read "Monsoon / Vata season" in Sharad, with
nothing on screen to say the season had moved on.
"""

from datetime import date, datetime, timezone

import routes.plans as plans
from engine.seasonal import get_current_season


def test_a_plan_from_before_the_stamp_takes_its_season_from_its_date():
    doc = {"generated_at": datetime(2026, 8, 13, 16, 48, tzinfo=timezone.utc), "plan_data": {}}
    ctx = plans._season_context(doc)
    assert ctx["built_for"] == get_current_season(date(2026, 8, 13)).name.lower()
    assert ctx["now"] == get_current_season().name.lower()


def test_the_stamped_season_wins_over_the_date():
    doc = {"generated_at": "2026-08-13T16:48:47", "plan_data": {"season": "Sharad"}}
    assert plans._season_context(doc)["built_for"] == "sharad"


def test_no_date_and_no_stamp_is_no_context():
    assert plans._season_context({"plan_data": {}}) is None


def test_history_attaches_it_to_every_plan():
    import inspect

    assert '"season_context": _season_context(p)' in inspect.getsource(plans.get_plan_history)
