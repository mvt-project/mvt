# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from datetime import datetime
from typing import Optional, Union

from mvt.ios.versions import find_version_by_build

from ..base import IOSExtraction
from .analytics import Analytics


class AnalyticsIOSVersions(IOSExtraction):
    """This module leverages the Analytics module in order to extract
    a timeline of build numbers from the private/var/Keychains/Analytics/*.db
    files."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def serialize(self, record: dict) -> Union[dict, list]:
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

            isodate = result.get("isodate", None)
            if not isodate:
                continue

            if build not in builds.keys():
                builds[build] = isodate
                continue

            result_dt = datetime.strptime(isodate, dt_format)
            cur_dt = datetime.strptime(builds[build], dt_format)

            if result_dt < cur_dt:
                builds[build] = isodate

        for build, isodate in builds.items():
            version = find_version_by_build(build)

            self.results.append(
                {
                    "isodate": isodate,
                    "build": build,
                    "version": version,
                }
            )

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
        for result in self.results:
            self.log.info(
                "iOS version %s (%s) first appeared on %s",
                result["version"],
                result["build"],
                result["isodate"],
            )
