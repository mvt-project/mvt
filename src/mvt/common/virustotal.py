# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Any, Optional

import requests

from .config import settings

log = logging.getLogger(__name__)


class VTNoKey(Exception):
    pass


class VTQuotaExceeded(Exception):
    pass


def virustotal_lookup(file_hash: str) -> Optional[dict[str, Any]]:
    if not settings.VT_API_KEY:
        raise VTNoKey(
            "No VirusTotal API key provided: to use VirusTotal lookups please set "
            "MVT_VT_API_KEY or VT_API_KEY in the MVT configuration file"
        )

    headers = {
        "User-Agent": "VirusTotal",
        "Content-Type": "application/json",
        "x-apikey": settings.VT_API_KEY,
    }
    res = requests.get(
        f"https://www.virustotal.com/api/v3/files/{file_hash}",
        headers=headers,
        timeout=settings.NETWORK_TIMEOUT,
    )

    if res.status_code == 200:
        report = res.json()
        return report["data"]

    if res.status_code == 404:
        log.info("Could not find results for file with hash %s", file_hash)
    elif res.status_code == 429:
        raise VTQuotaExceeded("You have exceeded the quota for your VirusTotal API key")
    else:
        raise RuntimeError(f"Unexpected response from VirusTotal: {res.status_code}")

    return None
