# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json

from mvt.common.command import Command


class TestCommand:
    def test_store_alerts_handles_bytes(self, tmp_path):
        cmd = Command(results_path=str(tmp_path))
        cmd.alertstore.medium(
            "bytes event",
            "",
            {"payload": b"\xa8\xa9"},
        )

        cmd._store_alerts()

        alerts = json.loads((tmp_path / "alerts.json").read_text())
        assert alerts[0]["event"]["payload"] == "\\xa8\\xa9"
