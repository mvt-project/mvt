# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from datetime import datetime
from typing import Any, Dict, List

from mvt.common.utils import convert_datetime_to_iso


def parse_dumpsys_battery_daily(output: str) -> list:
    results = []
    daily = None
    daily_updates = []
    for line in output.splitlines():
        if line.startswith("  Daily from "):
            if len(daily_updates) > 0:
                results.extend(daily_updates)
                daily_updates = []

            timeframe = line[13:].strip()
            date_from, date_to = timeframe.strip(":").split(" to ", 1)
            daily = {"from": date_from[0:10], "to": date_to[0:10]}
            continue

        if not daily:
            continue

        if not line.strip().startswith("Update "):
            continue

        line = line.strip().replace("Update ", "")
        package_name, vers = line.split(" ", 1)
        vers_nr = vers.split("=", 1)[1]

        already_seen = False
        for update in daily_updates:
            if package_name == update["package_name"] and vers_nr == update["vers"]:
                already_seen = True
                break

        if not already_seen:
            daily_updates.append(
                {
                    "action": "update",
                    "from": daily["from"],
                    "to": daily["to"],
                    "package_name": package_name,
                    "vers": vers_nr,
                }
            )

    if len(daily_updates) > 0:
        results.extend(daily_updates)

    return results


def parse_dumpsys_battery_history(output: str) -> List[Dict[str, Any]]:
    results = []

    for line in output.splitlines():
        if line.startswith("Battery History "):
            continue

        if line.strip() == "":
            break

        time_elapsed = line.strip().split(" ", 1)[0]

        event = ""
        if line.find("+job") > 0:
            event = "start_job"
            uid = line[line.find("+job") + 5 : line.find(":")]
            service = line[line.find(":") + 1 :].strip('"')
            package_name = service.split("/")[0]
        elif line.find("-job") > 0:
            event = "end_job"
            uid = line[line.find("-job") + 5 : line.find(":")]
            service = line[line.find(":") + 1 :].strip('"')
            package_name = service.split("/")[0]
        elif line.find("+running +wake_lock=") > 0:
            uid = line[line.find("+running +wake_lock=") + 21 : line.find(":")]
            event = "wake"
            service = (
                line[line.find("*walarm*:") + 9 :].split(" ")[0].strip('"').strip()
            )
            if service == "" or "/" not in service:
                continue

            package_name = service.split("/")[0]
        elif (line.find("+top=") > 0) or (line.find("-top") > 0):
            if line.find("+top=") > 0:
                event = "start_top"
                top_pos = line.find("+top=")
            else:
                event = "end_top"
                top_pos = line.find("-top=")
            colon_pos = top_pos + line[top_pos:].find(":")
            uid = line[top_pos + 5 : colon_pos]
            service = ""
            package_name = line[colon_pos + 1 :].strip('"')
        else:
            continue

        results.append(
            {
                "time_elapsed": time_elapsed,
                "event": event,
                "uid": uid,
                "package_name": package_name,
                "service": service,
            }
        )

    return results


def parse_dumpsys_dbinfo(output: str) -> List[Dict[str, Any]]:
    results = []

    rxp = re.compile(
        r".*\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})\].*\[Pid:\((\d+)\)\](\w+).*sql\=\"(.+?)\""
    )  # pylint: disable=line-too-long
    rxp_no_pid = re.compile(
        r".*\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})\][ ]{1}(\w+).*sql\=\"(.+?)\""
    )  # pylint: disable=line-too-long

    pool = None
    in_operations = False
    for line in output.splitlines():
        if line.startswith("Connection pool for "):
            pool = line.replace("Connection pool for ", "").rstrip(":")

        if not pool:
            continue

        if line.strip() == "Most recently executed operations:":
            in_operations = True
            continue

        if not in_operations:
            continue

        if not line.startswith("        "):
            in_operations = False
            pool = None
            continue

        matches = rxp.findall(line)
        if not matches:
            matches = rxp_no_pid.findall(line)
            if not matches:
                continue

            match = matches[0]
            results.append(
                {
                    "isodate": match[0],
                    "action": match[1],
                    "sql": match[2],
                    "path": pool,
                }
            )
        else:
            match = matches[0]
            results.append(
                {
                    "isodate": match[0],
                    "pid": match[1],
                    "action": match[2],
                    "sql": match[3],
                    "path": pool,
                }
            )

    return results


def parse_dumpsys_receiver_resolver_table(output: str) -> Dict[str, Any]:
    results = {}

    in_receiver_resolver_table = False
    in_non_data_actions = False
    intent = None
    for line in output.splitlines():
        if line.startswith("Receiver Resolver Table:"):
            in_receiver_resolver_table = True
            continue

        if not in_receiver_resolver_table:
            continue

        if line.startswith("  Non-Data Actions:"):
            in_non_data_actions = True
            continue

        if not in_non_data_actions:
            continue

        # If we hit an empty line, the Non-Data Actions section should be
        # finished.
        if line.strip() == "":
            break

        # We detect the action name.
        if line.startswith(" " * 6) and not line.startswith(" " * 8) and ":" in line:
            intent = line.strip().replace(":", "")
            results[intent] = []
            continue

        # If we are not in an intent block yet, skip.
        if not intent:
            continue

        # If we are in a block but the line does not start with 8 spaces
        # it means the block ended a new one started, so we reset and
        # continue.
        if not line.startswith(" " * 8):
            intent = None
            continue

        # If we got this far, we are processing receivers for the
        # activities we are interested in.
        receiver = line.strip().split(" ")[1]
        package_name = receiver.split("/")[0]

        results[intent].append(
            {
                "package_name": package_name,
                "receiver": receiver,
            }
        )

    return results


def parse_dumpsys_appops(output: str) -> List[Dict[str, Any]]:
    results = []
    perm = {}
    package = {}
    entry = {}
    uid = None
    in_packages = False

    for line in output.splitlines():
        if line.startswith("  Uid 0:"):
            in_packages = True

        if not in_packages:
            continue

        if line.startswith("  Uid "):
            uid = line[6:-1]
            if entry:
                perm["entries"].append(entry)
                entry = {}

            if package:
                if perm:
                    package["permissions"].append(perm)

                perm = {}
                results.append(package)
            package = {}
            continue

        if line.startswith("    Package "):
            if entry:
                perm["entries"].append(entry)
                entry = {}

            if package:
                if perm:
                    package["permissions"].append(perm)

                perm = {}
                results.append(package)

            package = {
                "package_name": line[12:-1],
                "permissions": [],
                "uid": uid,
            }
            continue

        if package and line.startswith("      ") and line[6] != " ":
            if entry:
                perm["entries"].append(entry)
                entry = {}
            if perm:
                package["permissions"].append(perm)
                perm = {}

            perm["name"] = line.split()[0]
            perm["entries"] = []
            if len(line.split()) > 1:
                perm["access"] = line.split()[1][1:-2]

            continue

        if line.startswith("          "):
            # Permission entry like:
            # Reject: [fg-s]2021-05-19 22:02:52.054 (-314d1h25m2s33ms)
            if entry:
                perm["entries"].append(entry)
                entry = {}

            entry["access"] = line.split(":")[0].strip()
            entry["type"] = line[line.find("[") + 1 : line.find("]")]

            try:
                entry["timestamp"] = convert_datetime_to_iso(
                    datetime.strptime(
                        line[line.find("]") + 1 : line.find("(")].strip(),
                        "%Y-%m-%d %H:%M:%S.%f",
                    )
                )
            except ValueError:
                # Invalid date format
                pass

        if line.strip() == "":
            break

    if entry:
        perm["entries"].append(entry)
    if perm:
        package["permissions"].append(perm)
    if package:
        results.append(package)

    return results


def parse_dumpsys_package_for_details(output: str) -> Dict[str, Any]:
    """
    Parse one entry of a dumpsys package information
    """
    details = {
        "uid": "",
        "version_name": "",
        "version_code": "",
        "timestamp": "",
        "first_install_time": "",
        "last_update_time": "",
        "permissions": [],
        "requested_permissions": [],
    }

    in_install_permissions = False
    in_runtime_permissions = False
    in_declared_permissions = False
    in_requested_permissions = True
    for line in output.splitlines():
        if in_install_permissions:
            if line.startswith(" " * 4) and not line.startswith(" " * 6):
                in_install_permissions = False
            else:
                lineinfo = line.strip().split(":")
                permission = lineinfo[0]
                granted = None
                if "granted=" in lineinfo[1]:
                    granted = "granted=true" in lineinfo[1]

                details["permissions"].append(
                    {"name": permission, "granted": granted, "type": "install"}
                )

        if in_runtime_permissions:
            if not line.startswith(" " * 8):
                in_runtime_permissions = False
            else:
                lineinfo = line.strip().split(":")
                permission = lineinfo[0]
                granted = None
                if "granted=" in lineinfo[1]:
                    granted = "granted=true" in lineinfo[1]

                details["permissions"].append(
                    {"name": permission, "granted": granted, "type": "runtime"}
                )

        if in_declared_permissions:
            if not line.startswith(" " * 6):
                in_declared_permissions = False
            else:
                permission = line.strip().split(":")[0]
                details["permissions"].append({"name": permission, "type": "declared"})
        if in_requested_permissions:
            if not line.startswith(" " * 6):
                in_requested_permissions = False
            else:
                details["requested_permissions"].append(line.strip())

        if line.strip().startswith("userId="):
            details["uid"] = line.split("=")[1].strip()
        elif line.strip().startswith("versionName="):
            details["version_name"] = line.split("=")[1].strip()
        elif line.strip().startswith("versionCode="):
            details["version_code"] = line.split("=", 1)[1].strip()
        elif line.strip().startswith("timeStamp="):
            details["timestamp"] = line.split("=")[1].strip()
        elif line.strip().startswith("firstInstallTime="):
            details["first_install_time"] = line.split("=")[1].strip()
        elif line.strip().startswith("lastUpdateTime="):
            details["last_update_time"] = line.split("=")[1].strip()
        elif line.strip() == "install permissions:":
            in_install_permissions = True
        elif line.strip() == "runtime permissions:":
            in_runtime_permissions = True
        elif line.strip() == "declared permissions:":
            in_declared_permissions = True
        elif line.strip() == "requested permissions:":
            in_requested_permissions = True

    return details


def parse_dumpsys_packages(output: str) -> List[Dict[str, Any]]:
    """
    Parse the dumpsys package service data
    """
    pkg_rxp = re.compile(r"  Package \[(.+?)\].*")

    results = []
    package_name = None
    package = {}
    lines = []
    for line in output.splitlines():
        if line.startswith("  Package ["):
            if len(lines) > 0:
                details = parse_dumpsys_package_for_details("\n".join(lines))
                package.update(details)
                results.append(package)
                lines = []
                package = {}

            matches = pkg_rxp.findall(line)
            if not matches:
                continue

            package_name = matches[0]
            package["package_name"] = package_name
            continue

        if not package_name:
            continue

        lines.append(line)

    if len(lines) > 0:
        details = parse_dumpsys_package_for_details("\n".join(lines))
        package.update(details)
        results.append(package)

    return results
