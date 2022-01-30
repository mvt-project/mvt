# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import operator
import sqlite3
from pathlib import Path

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from .base import IOSExtraction


class NetBase(IOSExtraction):
    """This class provides a base for DataUsage and NetUsage extraction modules."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def _extract_net_data(self):
        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                ZPROCESS.ZFIRSTTIMESTAMP,
                ZPROCESS.ZTIMESTAMP,
                ZPROCESS.ZPROCNAME,
                ZPROCESS.ZBUNDLENAME,
                ZPROCESS.Z_PK,
                ZLIVEUSAGE.ZWIFIIN,
                ZLIVEUSAGE.ZWIFIOUT,
                ZLIVEUSAGE.ZWWANIN,
                ZLIVEUSAGE.ZWWANOUT,
                ZLIVEUSAGE.Z_PK,
                ZLIVEUSAGE.ZHASPROCESS,
                ZLIVEUSAGE.ZTIMESTAMP
            FROM ZLIVEUSAGE
            LEFT JOIN ZPROCESS ON ZLIVEUSAGE.ZHASPROCESS = ZPROCESS.Z_PK
            UNION
            SELECT ZFIRSTTIMESTAMP, ZTIMESTAMP, ZPROCNAME, ZBUNDLENAME, Z_PK, NULL, NULL, NULL, NULL, NULL, NULL, NULL FROM ZPROCESS WHERE Z_PK NOT IN (SELECT ZHASPROCESS FROM ZLIVEUSAGE);
        """)

        for row in cur:
            # ZPROCESS records can be missing after the JOIN. Handle NULL timestamps.
            if row[0] and row[1]:
                first_isodate = convert_timestamp_to_iso(convert_mactime_to_unix(row[0]))
                isodate = convert_timestamp_to_iso(convert_mactime_to_unix(row[1]))
            else:
                first_isodate = row[0]
                isodate = row[1]

            if row[11]:
                live_timestamp = convert_timestamp_to_iso(convert_mactime_to_unix(row[11]))
            else:
                live_timestamp = ""

            self.results.append({
                "first_isodate": first_isodate,
                "isodate": isodate,
                "proc_name": row[2],
                "bundle_id": row[3],
                "proc_id": row[4],
                "wifi_in": row[5],
                "wifi_out": row[6],
                "wwan_in": row[7],
                "wwan_out": row[8],
                "live_id": row[9],
                "live_proc_id": row[10],
                "live_isodate": live_timestamp if row[10] else first_isodate,
            })

        cur.close()
        conn.close()

        self.log.info("Extracted information on %d processes", len(self.results))

    def serialize(self, record):
        record_data = f"{record['proc_name']} (Bundle ID: {record['bundle_id']}, ID: {record['proc_id']})"
        record_data_usage = record_data + f" WIFI IN: {record['wifi_in']}, WIFI OUT: {record['wifi_out']} - "  \
            f"WWAN IN: {record['wwan_in']}, WWAN OUT: {record['wwan_out']}"

        records = [{
            "timestamp": record["live_isodate"],
            "module": self.__class__.__name__,
            "event": "live_usage",
            "data": record_data_usage,
        }]

        # Only included first_usage and current_usage records when a ZPROCESS entry exists.
        if "MANIPULATED" not in record["proc_name"] and "MISSING" not in record["proc_name"] and record["live_proc_id"] is not None:
            records.extend([
                {
                    "timestamp": record["first_isodate"],
                    "module": self.__class__.__name__,
                    "event": "first_usage",
                    "data": record_data,
                },
                {
                    "timestamp": record["isodate"],
                    "module": self.__class__.__name__,
                    "event": "current_usage",
                    "data": record_data,
                }
            ])

        return records

    def _find_suspicious_processes(self):
        if not self.is_fs_dump:
            return

        if not self.results:
            return

        # If we are instructed to run fast, we skip this.
        if self.fast_mode:
            self.log.info("Flag --fast was enabled: skipping extended search for suspicious processes")
            return

        self.log.info("Extended search for suspicious processes ...")

        files = []
        for posix_path in Path(self.base_folder).rglob("*"):
            try:
                if not posix_path.is_file():
                    continue
            except PermissionError:
                continue

            files.append([posix_path.name, posix_path.__str__()])

        for proc in self.results:
            if not proc["bundle_id"]:
                self.log.debug("Found process with no Bundle ID with name: %s", proc["proc_name"])

                binary_path = None
                for file in files:
                    if proc["proc_name"] == file[0]:
                        binary_path = file[1]
                        break

                if binary_path:
                    self.log.debug("Located at %s", binary_path)
                else:
                    msg = f"Could not find the binary associated with the process with name {proc['proc_name']}"
                    if (proc["proc_name"] is None):
                        msg = f"Found process entry with empty 'proc_name' : {proc['live_proc_id']} at {proc['live_isodate']}"
                    elif len(proc["proc_name"]) == 16:
                        msg = msg + " (However, the process name might have been truncated in the database)"

                    self.log.warning(msg)
            if not proc["live_proc_id"]:
                self.log.info(f"Found process entry in ZPROCESS but not in ZLIVEUSAGE : {proc['proc_name']} at {proc['live_isodate']}")

    def check_manipulated(self):
        """Check for missing or manipulate DB entries"""
        # Don't show duplicates for each missing process.
        missing_process_cache = set()
        for result in sorted(self.results, key=operator.itemgetter("live_isodate")):
            if result["proc_id"]:
                continue

            # Avoid duplicate warnings for same process.
            if result["live_proc_id"] not in missing_process_cache:
                missing_process_cache.add(result["live_proc_id"])
                self.log.warning("Found manipulated process entry %s. Entry on %s",
                                 result["live_proc_id"], result["live_isodate"])

            # Set manipulated proc timestamp so it appears in timeline.
            result["first_isodate"] = result["isodate"] = result["live_isodate"]
            result["proc_name"] = "MANIPULATED [process record deleted]"
            self.detected.append(result)

    def find_deleted(self):
        """Identify process which may have been deleted from the DataUsage database"""
        results_by_proc = {proc["proc_id"]: proc for proc in self.results if proc["proc_id"]}
        all_proc_id = sorted(results_by_proc.keys())

        # Fix issue #108
        if not all_proc_id:
            return

        missing_procs, last_proc_id = {}, None
        for proc_id in range(min(all_proc_id), max(all_proc_id)):
            if proc_id not in all_proc_id:
                previous_proc = results_by_proc[last_proc_id]
                self.log.info("Missing process %d. Previous process at \"%s\" (%s)",
                              proc_id, previous_proc["first_isodate"], previous_proc["proc_name"])

                missing_procs[proc_id] = {
                    "proc_id": proc_id,
                    "prev_proc_id": last_proc_id,
                    "prev_proc_name": previous_proc["proc_name"],
                    "prev_proc_bundle": previous_proc["bundle_id"],
                    "prev_proc_first": previous_proc["first_isodate"],
                }
            else:
                last_proc_id = proc_id

        # Add a placeholder entry for the missing processes.
        for proc_id, proc in missing_procs.items():
            # Set default DataUsage keys.
            result = {key: None for key in self.results[0].keys()}
            result["first_isodate"] = result["isodate"] = result["live_isodate"] = proc["prev_proc_first"]
            result["proc_name"] = "MISSING [follows {}]".format(proc["prev_proc_name"])
            result["proc_id"] = result["live_proc_id"] = proc["proc_id"]
            result["bundle_id"] = None

            self.results.append(result)

        self.results = sorted(self.results, key=operator.itemgetter("first_isodate"))

    def check_indicators(self):
        # Check for manipulated process records.
        # TODO: Catching KeyError for live_isodate for retro-compatibility.
        #       This is not very good.
        try:
            self.check_manipulated()
            self.find_deleted()
        except KeyError:
            pass

        if not self.indicators:
            return

        for result in self.results:
            try:
                proc_name = result["proc_name"]
            except KeyError:
                continue

            # Process ID may be empty if process records have been manipulated.
            if not result["proc_id"]:
                continue

            ioc = self.indicators.check_process(proc_name)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
