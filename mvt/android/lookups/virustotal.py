# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

import requests
from rich.console import Console
from rich.progress import track
from rich.table import Table
from rich.text import Text

log = logging.getLogger(__name__)


def get_virustotal_report(hashes):
    apikey = "233f22e200ca5822bd91103043ccac138b910db79f29af5616a9afe8b6f215ad"
    url = f"https://www.virustotal.com/partners/sysinternals/file-reports?apikey={apikey}"

    items = []
    for sha256 in hashes:
        items.append({
            "autostart_location": "",
            "autostart_entry": "",
            "hash": sha256,
            "local_name": "",
            "creation_datetime": "",
        })
    headers = {"User-Agent": "VirusTotal", "Content-Type": "application/json"}
    res = requests.post(url, headers=headers, json=items)

    if res.status_code == 200:
        report = res.json()
        return report["data"]
    else:
        log.error("Unexpected response from VirusTotal: %s", res.status_code)
        return None


def virustotal_lookup(packages):
    # NOTE: This is temporary, until we resolved the issue.
    log.error("Unfortunately VirusTotal lookup is disabled until further notice, due to unresolved issues with the API service.")
    return

    log.info("Looking up all extracted files on VirusTotal (www.virustotal.com)")

    unique_hashes = []
    for package in packages:
        for file in package.get("files", []):
            if file["sha256"] not in unique_hashes:
                unique_hashes.append(file["sha256"])

    total_unique_hashes = len(unique_hashes)

    detections = {}

    def virustotal_query(batch):
        report = get_virustotal_report(batch)
        if not report:
            return

        for entry in report:
            if entry["hash"] not in detections and entry["found"] is True:
                detections[entry["hash"]] = entry["detection_ratio"]

    batch = []
    for i in track(range(total_unique_hashes), description=f"Looking up {total_unique_hashes} files..."):
        file_hash = unique_hashes[i]
        batch.append(file_hash)
        if len(batch) == 25:
            virustotal_query(batch)
            batch = []

    if batch:
        virustotal_query(batch)

    table = Table(title="VirusTotal Packages Detections")
    table.add_column("Package name")
    table.add_column("File path")
    table.add_column("Detections")

    for package in packages:
        for file in package.get("files", []):
            row = [package["package_name"], file["path"]]

            if file["sha256"] in detections:
                detection = detections[file["sha256"]]
                positives = detection.split("/")[0]
                if int(positives) > 0:
                    row.append(Text(detection, "red bold"))
                else:
                    row.append(detection)
            else:
                row.append("not found")

            table.add_row(*row)

    console = Console()
    console.print(table)
