"""A password reset or change ends every session that existed before it.

Found on production 2026-10-18: a session logged in before a password reset
could still refresh and read the profile afterwards, because the reset changed
the hash and nothing else. Someone resetting because their account was taken
over left the intruder signed in for the refresh token's 7 days.
"""
from datetime import datetime, timedelta, timezone

import pytest

from services.auth_service import end_other_sessions, token_predates_password_change

CHANGED = datetime(2026, 10, 19, 6, 0, 0, tzinfo=timezone.utc)


def _claims(at: datetime) -> dict:
    return {"sub": "u1", "iat": int(at.timestamp())}


def test_a_token_from_before_the_change_is_refused():
    assert token_predates_password_change(_claims(CHANGED - timedelta(minutes=5)), {"password_changed_at": CHANGED})


def test_a_token_issued_at_or_after_the_change_is_accepted():
    # The device that changed the password is re-issued a token in that same second.
    assert not token_predates_password_change(_claims(CHANGED), {"password_changed_at": CHANGED})
    assert not token_predates_password_change(_claims(CHANGED + timedelta(seconds=1)), {"password_changed_at": CHANGED})


def test_an_account_that_never_changed_its_password_is_unaffected():
    assert not token_predates_password_change(_claims(CHANGED), {})


def test_a_naive_stored_timestamp_is_read_as_utc():
    # Motor returns naive datetimes unless tz_aware is set.
    naive = CHANGED.replace(tzinfo=None)
    assert token_predates_password_change(_claims(CHANGED - timedelta(seconds=30)), {"password_changed_at": naive})


class _Coll:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.updates = []

    async def update_one(self, q, u):
        self.updates.append((q, u))

    async def update_many(self, q, u):
        n = 0
        for d in self.docs:
            if all(d.get(k) == v for k, v in q.items()):
                d.update(u["$set"]); n += 1
        self.updates.append((q, u, n))


class _DB:
    def __init__(self):
        self.users = _Coll()
        self.refresh_tokens = _Coll([
            {"user_id": "u1", "jti": "a", "revoked_at": None},
            {"user_id": "u1", "jti": "b", "revoked_at": None},
            {"user_id": "someone-else", "jti": "c", "revoked_at": None},
        ])


@pytest.mark.asyncio
async def test_ending_sessions_revokes_every_refresh_token_of_that_user_only():
    db = _DB()
    stamp = await end_other_sessions(db, "u1")
    assert [t["revoked_at"] is not None for t in db.refresh_tokens.docs] == [True, True, False]
    assert db.users.updates[0] == ({"_id": "u1"}, {"$set": {"password_changed_at": stamp}})
    assert stamp.microsecond == 0     # seconds, the resolution a JWT iat carries
