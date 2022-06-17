# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

import requests

log = logging.getLogger(__name__)

MVT_VT_API_KEY = "MVT_VT_API_KEY"


class VTNoKey(Exception):
    pass


class VTQuotaExceeded(Exception):
    pass


def virustotal_lookup(file_hash: str):
    if MVT_VT_API_KEY not in os.environ:
        raise VTNoKey("No VirusTotal API key provided: to use VirusTotal lookups please provide your API key with `export MVT_VT_API_KEY=<key>`")

    headers = {
        "User-Agent": "VirusTotal",
        "Content-Type": "application/json",
        "x-apikey": os.environ[MVT_VT_API_KEY],
    }
    res = requests.get(f"https://www.virustotal.com/api/v3/files/{file_hash}", headers=headers)

    if res.status_code == 200:
        report = res.json()
        return report["data"]
    elif res.status_code == 404:
        log.info("Could not find results for file with hash %s", file_hash)
    elif res.status_code == 429:
        raise VTQuotaExceeded("You have exceeded the quota for your VirusTotal API key")
    else:
        raise Exception("Unexpected response from VirusTotal: %s", res.status_code)

    return None
