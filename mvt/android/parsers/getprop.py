# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re


def parse_getprop(output):
    results = {}
    rxp = re.compile(r"\[(.+?)\]: \[(.+?)\]")

    for line in output.splitlines():
        line = line.strip()
        if line == "":
            continue

        matches = re.findall(rxp, line)
        if not matches or len(matches[0]) != 2:
            continue

        key = matches[0][0]
        value = matches[0][1]
        results[key] = value

    return results
