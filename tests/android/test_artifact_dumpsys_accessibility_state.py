# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""Installed is not the same as enabled, and the dump says which.

Two things this guards:

  * a section the dump never printed must read as None ("not stated"), not as
    False ("not enabled");
  * the alert must name the state, instead of firing identically on a device
    where nothing is switched on and one where something is bound.
"""

from types import SimpleNamespace

from mvt.android.artifacts.dumpsys_accessibility import DumpsysAccessibilityArtifact
from mvt.common.alerts import AlertLevel

from ..utils import get_artifact

NO_STATE_SECTIONS = """\
ACCESSIBILITY MANAGER (dumpsys accessibility)
User state[attributes:{id=0, currentUser=true}
  installed services: {
    0 : com.example.app/com.example.app.Service
  }
"""

ENABLED_BLOCK = """\
ACCESSIBILITY MANAGER (dumpsys accessibility)
User state[attributes:{id=0, currentUser=true}
  installed services: {
    0 : com.example.app/com.example.app.Service
    1 : com.other.app/.Helper
  }
  enabled services: {
    0 : com.other.app/.Helper
  }
  bound services:{
    0 : com.other.app/.Helper
  }
"""

# User 0 prints only `installed services`, user 10 only `Enabled services`.
# Neither section speaks for the other user.
TWO_USERS_DIFFERENT_SECTIONS = """\
ACCESSIBILITY MANAGER (dumpsys accessibility)
User state[attributes:{id=0, currentUser=true}
  installed services: {
    0 : com.example.app/com.example.app.Service
  }
User state[attributes:{id=10, currentUser=false}
     Enabled services:{{com.other.app/.Helper}}
"""


class _IndicatorsMatching:
    """Minimal stand-in: matches one package id, like the STIX2 loader would."""

    def __init__(self, package_name: str) -> None:
        self.package_name = package_name

    def check_app_id(self, app_id):
        if app_id != self.package_name:
            return None
        return SimpleNamespace(
            message=f"Found a known suspicious app: {app_id}", ioc={"value": app_id}
        )


class TestAccessibilityServiceState:
    def _parse(self, content):
        artifact = DumpsysAccessibilityArtifact()
        artifact.results = []
        artifact.parse(content)
        return {r["component"]: r for r in artifact.results}

    def test_absent_sections_leave_the_state_unknown(self):
        # None, not False: a build that does not print the sections says
        # nothing about what is enabled, and that must not read as "nothing".
        state = self._parse(NO_STATE_SECTIONS)[
            "com.example.app/com.example.app.Service"
        ]
        assert state["installed"] is True
        assert state["enabled"] is None
        assert state["bound"] is None

    def test_enabled_and_bound_are_attributed_per_service(self):
        results = self._parse(ENABLED_BLOCK)
        installed_only = results["com.example.app/com.example.app.Service"]
        active = results["com.other.app/.Helper"]
        assert (installed_only["enabled"], installed_only["bound"]) == (False, False)
        assert (active["enabled"], active["bound"]) == (True, True)

    def test_alert_message_carries_the_state(self):
        artifact = DumpsysAccessibilityArtifact()
        artifact.results = []
        with open(get_artifact("android_data/dumpsys_accessibility.txt")) as handle:
            artifact.parse(handle.read())
        artifact.check_indicators()
        assert artifact.alertstore.alerts
        assert all("installed" in alert.message for alert in artifact.alertstore.alerts)

    def test_a_switched_off_service_is_low_and_a_running_one_medium(self):
        # A service the dump says is OFF still reaches the analyst, but must not
        # compete with one that is actually bound. "Not stated" is not "off".
        artifact = DumpsysAccessibilityArtifact()
        artifact.results = []
        artifact.parse(ENABLED_BLOCK)
        artifact.check_indicators()
        by_level = {}
        for alert in artifact.alertstore.alerts:
            by_level.setdefault(alert.level, []).append(alert.message)
        assert artifact.alertstore.count(AlertLevel.LOW) == 1
        assert artifact.alertstore.count(AlertLevel.MEDIUM) == 1
        assert "com.example.app" in by_level[AlertLevel.LOW][0]
        assert "com.other.app" in by_level[AlertLevel.MEDIUM][0]

    def test_an_unstated_enabled_state_stays_medium(self):
        artifact = DumpsysAccessibilityArtifact()
        artifact.results = []
        artifact.parse(NO_STATE_SECTIONS)
        artifact.check_indicators()
        assert artifact.alertstore.count(AlertLevel.MEDIUM) == 1
        assert artifact.alertstore.count(AlertLevel.LOW) == 0

    def test_a_disabled_service_is_still_matched_against_indicators(self):
        # The state decides the severity of an ordinary finding, never whether
        # the package is compared with the IOC feeds.
        artifact = DumpsysAccessibilityArtifact()
        artifact.results = []
        artifact.parse(ENABLED_BLOCK)
        artifact.indicators = _IndicatorsMatching("com.example.app")
        artifact.check_indicators()
        assert artifact.alertstore.count(AlertLevel.CRITICAL) == 1
        assert artifact.alertstore.count(AlertLevel.LOW) == 0

    def test_printed_sections_are_tracked_per_user(self):
        artifact = DumpsysAccessibilityArtifact()
        artifact.results = []
        artifact.parse(TWO_USERS_DIFFERENT_SECTIONS)
        by_user = {r["user_id"]: r for r in artifact.results}
        # User 0's enabled state is not stated, so it is unknown, not off.
        assert (by_user[0]["installed"], by_user[0]["enabled"]) == (True, None)
        # User 10's installed state is not stated either.
        assert (by_user[10]["installed"], by_user[10]["enabled"]) == (None, True)

        artifact.check_indicators()
        assert artifact.alertstore.count(AlertLevel.LOW) == 0
        assert artifact.alertstore.count(AlertLevel.MEDIUM) == 2
        assert not any(
            "installed, not enabled" in alert.message
            for alert in artifact.alertstore.alerts
        )
