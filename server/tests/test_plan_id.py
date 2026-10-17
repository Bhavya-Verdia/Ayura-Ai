"""Plan ids are plan_history's _id, so two plans in one second must not share one."""
import re
from pathlib import Path

from services.plan_id import new_plan_id


def test_two_ids_in_one_second_differ():
    ids = {new_plan_id("gym", "u1") for _ in range(50)}
    assert len(ids) == 50
    assert all(re.fullmatch(r"gym_u1_\d+_[0-9a-f]{8}", i) for i in ids)


def test_no_engine_names_a_plan_by_the_second():
    # Every engine had `f"{feature}_{user}_{int(...timestamp())}"`. Routine hit the
    # DuplicateKeyError on production first only because it rebuilds fastest.
    services = Path(__file__).resolve().parent.parent / "services"
    offenders = []
    for path in services.glob("*.py"):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if "plan_id" in line and "timestamp()" in line:
                offenders.append(f"{path.name}:{n}")
    assert not offenders, f"use services.plan_id.new_plan_id: {offenders}"
