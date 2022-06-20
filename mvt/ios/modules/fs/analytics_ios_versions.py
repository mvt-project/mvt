# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from datetime import datetime

from mvt.ios.versions import find_version_by_build

from ..base import IOSExtraction
from .analytics import Analytics


class AnalyticsIOSVersions(IOSExtraction):
    """This module leverages the Analytics module in order to extract
    a timeline of build numbers from the private/var/Keychains/Analytics/*.db
    files."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "analytics_ios_version",
            "data": f"Seen iOS version {record['version']} ({record['build']})",
        }

    def run(self):
        anl = Analytics(target_path=self.target_path, log=self.log)
        anl.process_analytics_dbs()

        dt_format = "%Y-%m-%d %H:%M:%S.%f"

        builds = {}
        for result in anl.results:
            build = result.get("build")
            if not build:
                continue

            ts = result.get("isodate", None)
            if not ts:
                continue

            if build not in builds.keys():
                builds[build] = ts
                continue

            result_dt = datetime.strptime(ts, dt_format)
            cur_dt = datetime.strptime(builds[build], dt_format)

            if result_dt < cur_dt:
                builds[build] = ts

        for build, ts in builds.items():
            version = find_version_by_build(build)

            self.results.append({
                "isodate": ts,
                "build": build,
                "version": version,
            })

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
        for result in self.results:
            self.log.info("iOS version %s (%s) first appeared on %s",
                          result["version"], result["build"], result["isodate"])
