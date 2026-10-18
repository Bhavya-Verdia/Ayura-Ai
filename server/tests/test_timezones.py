"""The device timezone a browser sends must be one the server can resolve.

Chrome in India reports ``Asia/Calcutta`` (ICU's canonical id), not
``Asia/Kolkata``. The production image is Debian 13, whose ``tzdata`` moved the
legacy names into ``tzdata-legacy``, so ``ZoneInfo("Asia/Calcutta")`` raised and
the onboarding save — which sends the device timezone — came back 422 for every
such user. Nobody completed onboarding from 2026-09-22 until this was found on
2026-10-18. The fix is the ``tzdata`` package pinned in requirements.txt, which
zoneinfo falls back to when the system database lacks a zone.

A developer's Mac (or any system with the legacy links) resolves these names on
its own, which is how this passed every local check. So each test here hides the
system database first: what is left is the pinned package, as in production.
"""
import zoneinfo

import pytest
from pydantic import ValidationError

from routes.reminders import _validate_tz
from schemas.user_schema import UserProfileUpdate

# Legacy ids that browsers still report, one per region with users.
LEGACY = ["Asia/Calcutta", "Asia/Katmandu", "Asia/Saigon", "US/Eastern", "Europe/Kiev", "America/Buenos_Aires"]


@pytest.fixture(autouse=True)
def only_the_pinned_package():
    zoneinfo.reset_tzpath([])
    zoneinfo.ZoneInfo.clear_cache()
    yield
    zoneinfo.reset_tzpath()
    zoneinfo.ZoneInfo.clear_cache()


def test_the_package_is_installed():
    import tzdata  # noqa: F401 — requirements.txt must keep it


@pytest.mark.parametrize("tz", ["Asia/Kolkata", *LEGACY])
def test_onboarding_accepts_the_timezone_a_browser_reports(tz):
    assert UserProfileUpdate(timezone=tz).timezone == tz


@pytest.mark.parametrize("tz", ["Asia/Kolkata", *LEGACY])
def test_reminders_accept_the_timezone_a_browser_reports(tz):
    assert _validate_tz(tz) == tz


@pytest.mark.parametrize("tz", ["Mars/Base", "Asia/Calcuta", "IST"])
def test_a_timezone_that_does_not_exist_is_still_refused(tz):
    with pytest.raises(ValidationError):
        UserProfileUpdate(timezone=tz)
