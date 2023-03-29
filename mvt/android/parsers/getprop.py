# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from typing import Dict, List


def parse_getprop(output: str) -> List[Dict[str, str]]:
    results = []
    rxp = re.compile(r"\[(.+?)\]: \[(.+?)\]")

    for line in output.splitlines():
        line = line.strip()
        if line == "":
            continue

        matches = re.findall(rxp, line)
        if not matches or len(matches[0]) != 2:
            continue

        entry = {
            "name": matches[0][0],
            "value": matches[0][1]
        }
        results.append(entry)

    return results
