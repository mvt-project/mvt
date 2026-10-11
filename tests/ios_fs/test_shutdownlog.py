# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
# https://license.mvt.re/1.1/

from mvt.common.module import run_module
from mvt.ios.modules.fs.shutdownlog import ShutdownLog


def _shutdown_log_entry(pid: int, client: str, timestamp: int) -> str:
    return (
        f"remaining client pid: {pid} ({client})\n"
        f"SIGTERM: [{timestamp}]\n"
    )


class TestShutdownLog:
    def test_discovers_rotated_shutdown_logs(self, tmp_path):
        diagnostics_path = tmp_path / "private/var/db/diagnostics"
        diagnostics_path.mkdir(parents=True)
        (diagnostics_path / "shutdown.log").write_text(
            _shutdown_log_entry(100, "/usr/libexec/first", 1_700_000_000),
            encoding="utf-8",
        )
        (diagnostics_path / "shutdown.0.log").write_text(
            _shutdown_log_entry(200, "/usr/libexec/second", 1_700_000_001),
            encoding="utf-8",
        )

        module = ShutdownLog(target_path=str(tmp_path))
        run_module(module)

        assert {result["client"] for result in module.results} == {
            "/usr/libexec/first",
            "/usr/libexec/second",
        }

    def test_file_path_indicator_matches_client_with_trailing_uuid(
        self, indicators_factory
    ):
        executable_path = "/usr/sbin/filecoordinationd"
        client = f"{executable_path}/123e4567-e89b-12d3-a456-426614174000"
        module = ShutdownLog(
            results=[
                {
                    "isodate": "2023-11-14 22:13:20.000000",
                    "pid": "100",
                    "client": client,
                    "delay": 0.0,
                    "times_delayed": 0,
                }
            ]
        )
        module.indicators = indicators_factory(file_paths=[executable_path])

        module.check_indicators()

        assert len(module.alertstore.alerts) == 1
        assert module.alertstore.alerts[0].matched_indicator.value == executable_path
