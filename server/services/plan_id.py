"""One way to name a plan.

A plan id is plan_history's ``_id``. It used to be ``{feature}_{user}_{epoch seconds}``,
so two plans for one user inside one second were a DuplicateKeyError — a 500 after
the work was done. Routine edits rebuild in milliseconds with no model call and hit
it on production; any engine that answers from rules alone can do the same.
"""
import uuid
from datetime import datetime, timezone


def new_plan_id(feature: str, user_id) -> str:
    stamp = int(datetime.now(timezone.utc).timestamp())
    return f"{feature}_{user_id}_{stamp}_{uuid.uuid4().hex[:8]}"
