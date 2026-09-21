"""Coruna artifact checks shared by backups, filesystems and metadata listings.

Structures documented by iVerify on 2026-09-15:
https://www.iverify.com/blog/proliferation-of-coruna-and-darksword
"""

import hashlib
import json
import math
import plistlib
import re
import stat
from collections import defaultdict
from pathlib import Path
from typing import Optional
from xml.parsers.expat import ExpatError

from mvt.common.alerts import AlertStore

from .paths import backup_device_path, normalize_ios_path

_PHOTO_STATE = re.compile(
    r"/private/var/mobile/Library/Preferences/com\.apple\.[0-9a-fA-F]{16}\.plist"
)
_DEVICE_CACHE = re.compile(
    r"/private/var/mobile/Containers/Data/Application/"
    r"(?P<container>[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})"
    r"/Documents/\.devcache"
)
MAX_ARTIFACT_SIZE = 1024 * 1024


def coruna_path_artifact(path: str, domain: Optional[str] = None) -> Optional[dict]:
    """Return a scoped candidate, never a verdict based on a basename alone."""
    if domain is not None:
        relative = path.replace("\\", "/")
        if relative == "Documents/.devcache" and domain.startswith("AppDomain-"):
            return {"kind": "device-cache", "container": domain}
        path = backup_device_path(domain, relative) or ""
        if not path:
            return None
    path = normalize_ios_path(path)
    if _PHOTO_STATE.fullmatch(path):
        return {"kind": "photo-state"}
    match = _DEVICE_CACHE.fullmatch(path)
    if match:
        return {"kind": "device-cache", "container": match["container"].lower()}
    return None


def inspect_coruna_artifact(file_path: str, artifact: dict) -> dict:
    """Enrich a candidate without exporting photo paths or device identifiers."""
    result = dict(artifact)
    try:
        with open(file_path, "rb") as handle:
            raw = handle.read(MAX_ARTIFACT_SIZE + 1)
        if len(raw) > MAX_ARTIFACT_SIZE:
            return {**result, "content_status": "too-large"}
        try:
            data = plistlib.loads(raw)
        except (ValueError, plistlib.InvalidFileException, ExpatError):
            data = json.loads(raw)
    except (OSError, ValueError, UnicodeError, OverflowError):
        return {**result, "content_status": "unavailable"}

    matched = False
    if isinstance(data, dict):
        if artifact["kind"] == "photo-state":
            photo = data.get("LastProcessedFilePath")
            timestamp = data.get("LastProcessedTimestamp")
            matched = (
                isinstance(photo, str)
                and normalize_ios_path(photo).startswith(
                    "/private/var/mobile/Media/DCIM/"
                )
                and isinstance(timestamp, (int, float))
                and not isinstance(timestamp, bool)
                and (isinstance(timestamp, int) or math.isfinite(timestamp))
                and timestamp > 0
            )
        elif artifact["kind"] == "device-cache":
            keys = ("ecid", "gci", "unique-id")
            matched = data.get("exp") == "plasma" and all(
                isinstance(data.get(key), str) and data[key].strip() for key in keys
            )
            if matched:
                identifiers = {key: data[key] for key in keys}
                result["identifier_sha256"] = hashlib.sha256(
                    json.dumps(identifiers, sort_keys=True).encode()
                ).hexdigest()
    result["content_status"] = "matched" if matched else "unmatched"
    return result


def enrich_coruna_record(record: dict, file_path: Optional[str]) -> None:
    artifact = coruna_path_artifact(
        record.get("relative_path", record.get("path", "")), record.get("domain")
    )
    if artifact:
        record["coruna_artifact"] = (
            inspect_coruna_artifact(file_path, artifact) if file_path else artifact
        )


def alert_coruna_record(record: dict, alertstore: AlertStore) -> None:
    if record.get("is_directory") or record.get("flags") == 2:
        return
    mode = record.get("mode")
    if isinstance(mode, int) and not stat.S_ISREG(mode):
        return
    artifact = record.get("coruna_artifact")
    if not artifact:
        artifact = coruna_path_artifact(
            record.get("relative_path", record.get("path", "")), record.get("domain")
        )
    if not artifact:
        return
    path = record.get("relative_path", record.get("path", ""))
    timestamp = record.get("modified", record.get("isodate", ""))
    if artifact.get("content_status") == "matched":
        alertstore.high(
            f"Coruna {artifact['kind']} artifact with matching content structure: {path}",
            timestamp,
            record,
        )
    else:
        alertstore.medium(
            f"Possible Coruna {artifact['kind']} artifact at {path}; "
            "path match without corroborating content",
            timestamp,
            record,
        )


def correlate_coruna_records(records: list, alertstore: AlertStore) -> None:
    groups: dict[str, dict[str, dict]] = defaultdict(dict)
    for record in records:
        artifact = record.get("coruna_artifact", {})
        if (
            artifact.get("kind") != "device-cache"
            or artifact.get("content_status") != "matched"
            or not artifact.get("container")
        ):
            continue
        fingerprint = artifact.get("identifier_sha256")
        if fingerprint:
            groups[fingerprint][artifact["container"]] = record
    for fingerprint, containers in groups.items():
        if len(containers) < 2:
            continue
        alertstore.high(
            f"Matching Coruna device identifiers in {len(containers)} application containers",
            "",
            {"identifier_sha256": fingerprint, "containers": sorted(containers)},
        )


def contained_regular_file(root: str, file_path: str) -> bool:
    """Do not read symlinks or paths outside the supplied acquisition."""
    path = Path(file_path)
    try:
        return (
            not path.is_symlink()
            and path.is_file()
            and path.resolve().is_relative_to(Path(root).resolve())
        )
    except (OSError, RuntimeError, ValueError):
        return False
