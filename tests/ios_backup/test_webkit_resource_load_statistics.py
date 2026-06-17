# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3

from mvt.common.module import run_module
from mvt.ios.modules.mixed.webkit_resource_load_statistics import (
    WebkitResourceLoadStatistics,
)

from ..utils import get_ios_backup_folder


class TestWebkitResourceLoadStatisticsModule:
    def test_webkit(self):
        m = WebkitResourceLoadStatistics(target_path=get_ios_backup_folder())
        m.is_backup = True
        run_module(m)
        assert len(m.results) == 2
        assert len(m.timeline) == 2
        assert len(m.alertstore.alerts) == 0

        results = {result["registrable_domain"]: result for result in m.results}
        assert results["google.com"]["most_recent_user_interaction_time"] > 0
        assert "most_recent_user_interaction_time_isodate" in results["google.com"]
        assert results["gstatic.com"]["most_recent_user_interaction_time"] == -1.0
        assert (
            "most_recent_user_interaction_time_isodate"
            not in results["gstatic.com"]
        )
        assert all(
            "most_recent_web_push_interaction_time" not in result
            for result in m.results
        )

    def test_webkit_full_timestamp_schema(self, tmp_path):
        db_path = tmp_path / "observations.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE ObservedDomains (
                domainID INTEGER PRIMARY KEY,
                registrableDomain TEXT NOT NULL,
                lastSeen REAL NOT NULL,
                hadUserInteraction INTEGER NOT NULL,
                mostRecentUserInteractionTime REAL NOT NULL,
                mostRecentWebPushInteractionTime REAL NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT INTO ObservedDomains VALUES (?, ?, ?, ?, ?, ?);
            """,
            (1, "example.com", 1634560250.0, 1, 1634560030.0, -1.0),
        )
        conn.commit()
        conn.close()

        m = WebkitResourceLoadStatistics(target_path=str(tmp_path))
        m._process_observations_db(str(db_path), "", "observations.db")

        assert len(m.results) == 1
        result = m.results[0]
        assert result["most_recent_user_interaction_time"] == 1634560030.0
        assert "most_recent_user_interaction_time_isodate" in result
        assert result["most_recent_web_push_interaction_time"] == -1.0
        assert "most_recent_web_push_interaction_time_isodate" not in result
