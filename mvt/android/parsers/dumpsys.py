# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re


def parse_dumpsys_accessibility(output):
    results = []

    in_services = False
    for line in output.splitlines():
        if line.strip().startswith("installed services:"):
            in_services = True
            continue

        if not in_services:
            continue

        if line.strip() == "}":
            break

        service = line.split(":")[1].strip()

        results.append({
            "package_name": service.split("/")[0],
            "service": service,
        })

    return results


def parse_dumpsys_activity_resolver_table(output):
    results = {}

    in_activity_resolver_table = False
    in_non_data_actions = False
    intent = None
    for line in output.splitlines():
        if line.startswith("Activity Resolver Table:"):
            in_activity_resolver_table = True
            continue

        if not in_activity_resolver_table:
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
        activity = line.strip().split(" ")[1]
        package_name = activity.split("/")[0]

        results[intent].append({
            "package_name": package_name,
            "activity": activity,
        })

    return results


def parse_dumpsys_battery_daily(output):
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
            daily_updates.append({
                "action": "update",
                "from": daily["from"],
                "to": daily["to"],
                "package_name": package_name,
                "vers": vers_nr,
            })

    if len(daily_updates) > 0:
        results.extend(daily_updates)

    return results


def parse_dumpsys_battery_history(output):
    results = []

    for line in output.splitlines():
        if line.strip() == "":
            break

        time_elapsed, rest = line.strip().split(" ", 1)

        start = line.find(" 100 ")
        if start == -1:
            continue

        line = line[start+5:]

        event = ""
        if line.startswith("+job"):
            event = "start_job"
        elif line.startswith("-job"):
            event = "end_job"
        elif line.startswith("+running +wake_lock="):
            event = "wake"
        else:
            continue

        if event in ["start_job", "end_job"]:
            uid = line[line.find("=")+1:line.find(":")]
            service = line[line.find(":")+1:].strip('"')
            package_name = service.split("/")[0]
        elif event == "wake":
            uid = line[line.find("=")+1:line.find(":")]
            service = line[line.find("*walarm*:")+9:].split(" ")[0].strip('"').strip()
            if service == "" or "/" not in service:
                continue

            package_name = service.split("/")[0]
        else:
            continue

        results.append({
            "time_elapsed": time_elapsed,
            "event": event,
            "uid": uid,
            "package_name": package_name,
            "service": service,
        })

    return results


def parse_dumpsys_dbinfo(output):
    results = []

    rxp = re.compile(r'.*\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})\].*\[Pid:\((\d+)\)\](\w+).*sql\=\"(.+?)\".*path\=(.*?$)')

    in_operations = False
    for line in output.splitlines():
        if line.strip() == "Most recently executed operations:":
            in_operations = True
            continue

        if not in_operations:
            continue

        if not line.startswith("        "):
            in_operations = False
            continue

        matches = rxp.findall(line)
        if not matches:
            continue

        match = matches[0]
        results.append({
            "isodate": match[0],
            "pid": match[1],
            "action": match[2],
            "sql": match[3],
            "path": match[4],
        })

    return results


def parse_dumpsys_receiver_resolver_table(output):
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

        results[intent].append({
            "package_name": package_name,
            "receiver": receiver,
        })

    return results
