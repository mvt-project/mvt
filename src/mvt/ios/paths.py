"""Compare device paths independently of the analysis host and backup layout."""

import posixpath
from typing import Optional

from mvt.common.indicators import IndicatorMatch, Indicators


def normalize_ios_path(path: str) -> str:
    path = posixpath.normpath("/" + path.replace("\\", "/").lstrip("/"))
    if path == "/var" or path.startswith("/var/"):
        return "/private" + path
    if path == "/tmp" or path.startswith("/tmp/"):
        return "/private" + path
    return path


def ios_path_variants(path: str) -> tuple[str, ...]:
    path = normalize_ios_path(path)
    if path.startswith(("/private/var/", "/private/tmp/")):
        return path, path[len("/private") :]
    return (path,)


def backup_device_path(domain: str, relative_path: str) -> Optional[str]:
    """Map only domains with a known fixed root; app UUIDs are not in Manifest.db."""
    roots = {
        "HomeDomain": "/private/var/mobile",
        "CameraRollDomain": "/private/var/mobile",
        "MediaDomain": "/private/var/mobile/Media",
        "RootDomain": "/private/var/root",
        "WirelessDomain": "/private/var/wireless",
    }
    root = roots.get(domain)
    relative_path = relative_path.replace("\\", "/")
    if not root or relative_path.startswith("/") or ".." in relative_path.split("/"):
        return None
    return normalize_ios_path(root + "/" + relative_path)


def check_ios_path(indicators: Indicators, path: str) -> Optional[IndicatorMatch]:
    for candidate in ios_path_variants(path):
        match = indicators.check_file_path(candidate)
        if match:
            return match
    return None
