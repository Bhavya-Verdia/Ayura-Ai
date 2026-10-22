"""A check-in suggests rebuilding plans; it never rebuilds them itself.

One check-in regenerated diet, yoga and medicines in the background (three billed
generations) and replaced a diet plan built twenty minutes earlier with a new four
weeks, orphaning its meal logs. Found on production, 2026-10-22."""

import inspect

import routes.checkin as checkin


def test_the_weekly_checkin_schedules_no_plan_generation():
    src = inspect.getsource(checkin.submit_weekly_checkin)
    assert "apply_chat_side_effects" not in src
    assert "add_task" not in src


def test_the_response_offers_the_plans_instead():
    fields = checkin.WeeklyCheckinResponse.model_fields
    assert "suggested_plans" in fields and "adapted_plans" not in fields
