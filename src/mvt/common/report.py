# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2025 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Build a self-contained HTML report from the results folder of a check.

The report only reads what a check already wrote to its results folder
(info.json, alerts.json, timeline.csv and the JSON output of each module), so
it can be generated at any time after the analysis, on any machine, and it
never changes the results themselves. The page embeds all of its data, styles
and scripts and loads nothing from the network: it can be opened offline and
shared as a single file.
"""

import base64
import csv
import json
import logging
import os
import re
from datetime import datetime
from importlib import resources
from typing import Any, Optional

from .utils import get_sha256_from_file_path
from .version import MVT_VERSION

log = logging.getLogger(__name__)

REPORT_FILE_NAME = "report.html"

# The timeline of a full filesystem dump can hold millions of events. The page
# stays usable with a few hundred thousand rows; beyond that it embeds the
# first ones in chronological order and says how many it left out.
MAX_TIMELINE_ROWS = 200_000

# Files a check writes next to the module results, which are not module results.
_NON_MODULE_FILES = {"info.json", "alerts.json", "urls.json"}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")

# Fields of a record that most commonly carry the time of the event, in the
# order in which they are preferred when an alert has no time of its own.
_TIME_FIELDS = (
    "isodate",
    "timestamp",
    "event_time",
    "first_install_time",
    "last_update_time",
    "modified",
    "created",
)

# Device properties shown on the report, from the modules that record them.
# Identifiers such as the serial number or the IMEI are left out on purpose:
# the report is meant to be shared with whoever helps with the investigation.
_IOS_DEVICE_FIELDS = (
    ("Model", "Product Type"),
    ("iOS version", "Product Version"),
    ("Build", "Build Version"),
    ("Device name", "Device Name"),
    ("Last backup", "Last Backup Date"),
)
_ANDROID_DEVICE_FIELDS = (
    ("Manufacturer", "ro.product.manufacturer"),
    ("Model", "ro.product.model"),
    ("Android version", "ro.build.version.release"),
    ("Security patch", "ro.build.version.security_patch"),
    ("Build", "ro.build.display.id"),
)


def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        log.warning("Unable to read %s: %s", path, exc)
        return None


def _infer_time(event: Any) -> Optional[str]:
    """Return the time of a record that an alert about it did not carry."""
    if not isinstance(event, dict):
        return None

    for field in _TIME_FIELDS:
        value = event.get(field)
        if isinstance(value, str) and _DATE_RE.match(value):
            return value

    for key, value in event.items():
        if (
            isinstance(value, str)
            and _DATE_RE.match(value)
            and ("time" in key.lower() or "date" in key.lower())
        ):
            return value

    return None


def _load_alerts(results_path: str) -> list[dict[str, Any]]:
    alerts = _read_json(os.path.join(results_path, "alerts.json"))
    if not isinstance(alerts, list):
        return []

    loaded = []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue

        event = alert.get("event")
        time = alert.get("event_time") or None
        time_source = "alert" if time else None
        if not time:
            time = _infer_time(event)
            time_source = "record" if time else None

        loaded.append(
            {
                "level": alert.get("level", "INFORMATIONAL"),
                "module": alert.get("module", ""),
                "message": alert.get("message", ""),
                "time": time,
                "time_source": time_source,
                "indicator": alert.get("matched_indicator"),
                "event": event,
            }
        )

    return loaded


def _load_timeline(results_path: str) -> dict[str, Any]:
    timeline_path = os.path.join(results_path, "timeline.csv")
    timeline: dict[str, Any] = {"timezone": None, "rows": [], "omitted": 0}
    if not os.path.isfile(timeline_path):
        return timeline

    with open(timeline_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, escapechar="\\")
        for row in reader:
            # Timelines written on Windows carry an empty row after each line.
            if not row:
                continue

            if timeline["timezone"] is None:
                timeline["timezone"] = "UTC" if row[0].startswith("UTC") else "local"
                continue

            if len(timeline["rows"]) >= MAX_TIMELINE_ROWS:
                timeline["omitted"] += 1
                continue

            timeline["rows"].append((row + ["", "", "", ""])[:4])

    return timeline


def _load_modules(
    results_path: str, alerts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    detections: dict[str, int] = {}
    for alert in alerts:
        detections[alert["module"]] = detections.get(alert["module"], 0) + 1

    modules = []
    for file_name in sorted(os.listdir(results_path)):
        if not file_name.endswith(".json") or file_name in _NON_MODULE_FILES:
            continue
        if file_name.endswith("_detected.json"):
            continue

        slug = file_name[: -len(".json")]
        results = _read_json(os.path.join(results_path, file_name))
        records = len(results) if isinstance(results, (list, dict)) else 0
        modules.append(
            {
                "name": slug,
                "file": file_name,
                "records": records,
                "detections": detections.pop(slug, 0),
            }
        )

    # Modules that raised alerts without storing results of their own.
    for slug, count in sorted(detections.items()):
        modules.append({"name": slug, "file": None, "records": 0, "detections": count})

    return modules


def _load_device(results_path: str) -> tuple[Optional[str], list[list[str]]]:
    backup_info = _read_json_if_exists(results_path, "backup_info.json")
    if isinstance(backup_info, dict):
        return "ios", [
            [label, str(backup_info[key])]
            for label, key in _IOS_DEVICE_FIELDS
            if backup_info.get(key)
        ]

    for file_name in ("aqf_get_prop.json", "dumpsys_get_prop.json"):
        properties = _read_json_if_exists(results_path, file_name)
        if not isinstance(properties, list):
            continue

        values = {
            prop.get("name"): prop.get("value")
            for prop in properties
            if isinstance(prop, dict)
        }
        return "android", [
            [label, str(values[key])]
            for label, key in _ANDROID_DEVICE_FIELDS
            if values.get(key)
        ]

    file_names = os.listdir(results_path)
    if "manifest.json" in file_names or any(
        name.startswith(("sysdiagnose", "shutdown")) for name in file_names
    ):
        return "ios", []
    if any(
        name.startswith(
            ("aqf_", "dumpsys_", "connect_event", "dns_event", "security_event")
        )
        for name in file_names
    ):
        return "android", []

    return None, []


def _read_json_if_exists(results_path: str, file_name: str) -> Any:
    path = os.path.join(results_path, file_name)
    if not os.path.isfile(path):
        return None
    return _read_json(path)


def collect_report_data(results_path: str, report_dir: str) -> dict[str, Any]:
    """Gather everything the report shows from a results folder.

    :param results_path: Folder a check stored its results to
    :param report_dir: Folder the report will be written to, so that the links
        to the result files can be made relative to it

    """
    info_path = os.path.join(results_path, "info.json")
    info = _read_json(info_path) if os.path.isfile(info_path) else None
    alerts = _load_alerts(results_path)
    platform, device = _load_device(results_path)
    urls = _read_json_if_exists(results_path, "urls.json")

    results_link = os.path.relpath(os.path.abspath(results_path), report_dir)
    results_link = "" if results_link == "." else results_link.replace(os.sep, "/")

    return {
        "report_version": 1,
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mvt_version": MVT_VERSION,
        "platform": platform,
        "results_path": os.path.abspath(results_path),
        "results_link": results_link,
        "info": info if isinstance(info, dict) else None,
        "info_sha256": get_sha256_from_file_path(info_path) if info else None,
        "device": device,
        "alerts": alerts,
        "timeline": _load_timeline(results_path),
        "modules": _load_modules(results_path, alerts),
        "urls": urls if isinstance(urls, list) else [],
    }


def _font_faces() -> str:
    """Return the @font-face rules of the report typeface, embedded as data.

    Atkinson Hyperlegible is licensed under the SIL Open Font License 1.1,
    whose text is in report_fonts/OFL.txt.
    """
    fonts = resources.files("mvt.common").joinpath("report_fonts")
    faces = []
    for weight in (400, 700):
        data = fonts.joinpath(f"atkinson-hyperlegible-{weight}.woff2").read_bytes()
        faces.append(
            "@font-face { font-family: 'Atkinson Hyperlegible'; "
            f"font-weight: {weight}; font-style: normal; font-display: swap; "
            "src: url(data:font/woff2;base64,"
            f"{base64.b64encode(data).decode('ascii')}) format('woff2'); }}"
        )
    return "\n".join(faces)


def render_report(data: dict[str, Any]) -> str:
    template = (
        resources.files("mvt.common")
        .joinpath("report_template.html")
        .read_text(encoding="utf-8")
    )
    template = template.replace("/*__MVT_REPORT_FONTS__*/", _font_faces(), 1)
    # The data is embedded in a <script> element: escaping "<" keeps a value
    # such as "</script>" in an SMS from closing the element early.
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("<", "\\u003c")
    return template.replace("/*__MVT_REPORT_DATA__*/null", payload, 1)


def generate_report(results_path: str, output_path: Optional[str] = None) -> str:
    """Write the HTML report of a results folder and return its path.

    :param results_path: Folder a check stored its results to
    :param output_path: Path of the report file, by default report.html inside
        the results folder

    """
    if not output_path:
        output_path = os.path.join(results_path, REPORT_FILE_NAME)
    elif os.path.isdir(output_path):
        output_path = os.path.join(output_path, REPORT_FILE_NAME)

    report_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(report_dir, exist_ok=True)

    data = collect_report_data(results_path, report_dir)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(render_report(data))

    return output_path
