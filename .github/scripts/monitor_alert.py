"""Decide whether a failing monitor run should alert, so an outage sends an email
when it starts and then at most once an hour, not every ten minutes.

The alert is the run failing: GitHub emails a scheduled workflow's failure to the
account that last changed its schedule. The repo is public, so an issue would
announce the outage to anyone; a failed run is seen only by the owner.

State lives in a JSON file the workflow carries between runs in the Actions
cache: {"failing_since": iso, "last_alert": iso}. Usage:

    python monitor_alert.py <state.json> <ok|fail>    → prints alert=true|false
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

REMIND_EVERY = timedelta(hours=1)


def decide(state: dict, ok: bool, now: datetime) -> tuple[dict, bool, str]:
    if ok:
        note = (f"Recovered — had been failing since {state['failing_since']}." if state.get("failing_since") else "")
        return {}, False, note
    since = state.get("failing_since")
    last = state.get("last_alert")
    if not since:
        return {"failing_since": now.isoformat(), "last_alert": now.isoformat()}, True, "Failure started: alerting."
    if not last or now - datetime.fromisoformat(last) >= REMIND_EVERY:
        return {**state, "last_alert": now.isoformat()}, True, f"Still failing since {since}: hourly reminder."
    return state, False, f"Still failing since {since}; alerted at {last}, next reminder within the hour."


def main():
    path, result = sys.argv[1], sys.argv[2]
    try:
        state = json.load(open(path))
    except (OSError, ValueError):
        state = {}
    new, alert, note = decide(state, result == "ok", datetime.now(timezone.utc))
    json.dump(new, open(path, "w"))
    print(note)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"alert={'true' if alert else 'false'}\nnote={note}\n")


if __name__ == "__main__":
    main()
