# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import sqlite3

from ..base import IOSExtraction


class CacheFiles(IOSExtraction):

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        records = []
        for item in self.results[record]:
            records.append({
                "timestamp": item["isodate"],
                "module": self.__class__.__name__,
                "event": "cache_response",
                "data": f"{record} recorded visit to URL {item['url']}"
            })

        return records

    def check_indicators(self):
        if not self.indicators:
            return

        self.detected = {}
        for key, values in self.results.items():
            for value in values:
                ioc = self.indicators.check_domain(value["url"])
                if ioc:
                    value["matched_indicator"] = ioc
                    if key not in self.detected:
                        self.detected[key] = [value, ]
                    else:
                        self.detected[key].append(value)

    def _process_cache_file(self, file_path):
        self.log.info("Processing cache file at path: %s", file_path)

        conn = sqlite3.connect(file_path)
        cur = conn.cursor()

        try:
            cur.execute("SELECT * FROM cfurl_cache_response;")
        except sqlite3.OperationalError:
            return

        key_name = os.path.relpath(file_path, self.base_folder)
        if key_name not in self.results:
            self.results[key_name] = []

        for row in cur:
            self.results[key_name].append({
                "entry_id": row[0],
                "version": row[1],
                "hash_value": row[2],
                "storage_policy": row[3],
                "url": row[4],
                "isodate": row[5],
            })

    def run(self):
        self.results = {}
        for root, dirs, files in os.walk(self.base_folder):
            for file_name in files:
                if file_name != "Cache.db":
                    continue

                file_path = os.path.join(root, file_name)
                self._process_cache_file(file_path)
