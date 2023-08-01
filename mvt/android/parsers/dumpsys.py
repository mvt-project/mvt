# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from typing import Any, Dict, List


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
