# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""The dump's own installed-service count must survive into the artifact.

Most builds never print the `installed services: {…}` block; they state `installedServiceCount=N` in the user's `attributes:{…}` line and
list nothing. Dropping that number makes an artifact that says "no
accessibility services" about a dump that said there are five.
"""

from mvt.android.artifacts.dumpsys_accessibility import DumpsysAccessibilityArtifact
from mvt.common.alerts import AlertLevel

AOSP_NO_LIST = """\
ACCESSIBILITY MANAGER (dumpsys accessibility)
User state[
     attributes:{id=0, touchExplorationEnabled=false, installedServiceCount=5}
     Bound services:{}
     Enabled services:{}
     Binding services:{}
     Crashed services:{}
"""

ONE_UI_WITH_LIST = """\
ACCESSIBILITY MANAGER (dumpsys accessibility)
User state[attributes:{id=0, installedServiceCount=2}
  installed services: {
    0 : com.example.app/com.example.app.Service
    1 : com.other.app/.Helper
  }
  enabled services: {
  }
"""

TWO_USERS = """\
ACCESSIBILITY MANAGER (dumpsys accessibility)
User state[attributes:{id=0, installedServiceCount=1}
  installed services: {
    0 : com.example.app/com.example.app.Service
  }
User state[attributes:{id=95, installedServiceCount=3}
     Enabled services:{}
"""

ZERO_COUNT = """\
ACCESSIBILITY MANAGER (dumpsys accessibility)
User state[attributes:{id=0, installedServiceCount=0}
     Enabled services:{}
"""


def _parse(content):
    artifact = DumpsysAccessibilityArtifact()
    artifact.results = []
    artifact.parse(content)
    return artifact


class TestAccessibilityInstalledServiceCount:
    def test_stated_count_without_a_list_is_kept(self):
        artifact = _parse(AOSP_NO_LIST)
        assert len(artifact.results) == 1
        record = artifact.results[0]
        assert record["installed_service_count"] == 5
        assert record["component"] is None
        # Every state flag stays unknown: the dump named no service to which a
        # state could belong.
        assert record["installed"] is None
        assert record["enabled"] is None

    def test_a_stated_count_is_reported_as_low(self):
        artifact = _parse(AOSP_NO_LIST)
        artifact.check_indicators()
        alerts = artifact.alertstore.alerts
        assert len(alerts) == 1
        # A count is a coverage statement, not a running service: it must not
        # compete with a service the dump says is enabled.
        assert alerts[0].level == AlertLevel.LOW
        assert "does not list their component names" in alerts[0].message
        assert "5 installed" in alerts[0].message

    def test_a_listed_user_carries_the_count_on_each_service(self):
        artifact = _parse(ONE_UI_WITH_LIST)
        assert len(artifact.results) == 2
        assert {record["installed_service_count"] for record in artifact.results} == {2}
        assert all(record["component"] for record in artifact.results)

    def test_only_the_unlisted_user_gets_a_count_record(self):
        artifact = _parse(TWO_USERS)
        listed = [record for record in artifact.results if record["component"]]
        unlisted = [record for record in artifact.results if not record["component"]]
        assert [record["user_id"] for record in listed] == [0]
        assert [record["user_id"] for record in unlisted] == [95]
        assert unlisted[0]["installed_service_count"] == 3

    def test_a_zero_count_adds_nothing(self):
        # "Zero installed" is a negative result the empty section already
        # states; a record for it would be noise.
        assert _parse(ZERO_COUNT).results == []
