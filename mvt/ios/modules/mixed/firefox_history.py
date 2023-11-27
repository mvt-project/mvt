# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso

from ..base import IOSExtraction

FIREFOX_HISTORY_BACKUP_IDS = [
    "2e57c396a35b0d1bcbc624725002d98bd61d142b",
]
FIREFOX_HISTORY_ROOT_PATHS = [
    "private/var/mobile/profile.profile/browser.db",
]


class FirefoxHistory(IOSExtraction):
    """This module extracts all Firefox visits and tries to detect potential
    network injection attacks.


    """

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
            "event": "firefox_history",
            "data": f"Firefox visit with ID {record['id']} to URL: {record['url']}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domain(result["url"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=FIREFOX_HISTORY_BACKUP_IDS, root_paths=FIREFOX_HISTORY_ROOT_PATHS
        )
        self.log.info("Found Firefox history database at path: %s", self.file_path)

        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                visits.id,
                visits.date/1000000,
                history.url,
                history.title,
                visits.is_local,
                visits.type
            FROM visits, history
            WHERE visits.siteID = history.id;
        """
        )

        for row in cur:
            self.results.append(
                {
                    "id": row[0],
                    "isodate": convert_unix_to_iso(row[1]),
                    "url": row[2],
                    "title": row[3],
                    "i1000000s_local": row[4],
                    "type": row[5],
                }
            )

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d history items", len(self.results))
