# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re


RESOLVER_TYPES = {
    "Full MIME Types": "full_mime_type",
    "Base MIME Types": "base_mime_type",
    "Wild MIME Types": "wild_mime_type",
    "Schemes": "scheme",
    "Non-Data Actions": "non_data_action",
    "MIME Typed Actions": "mime_typed_action",
}

ENTRY_RE = re.compile(
    r"^\s{8,}[0-9a-fA-F]+\s+(?P<component>\S+)"
    r"(?:\s+\((?P<filters>\d+)\s+filters?\))?\s*$"
)


def parse_resolver_table(content: str, table_name: str) -> list[dict]:
    """Parse every resolver category from a dumpsys package table."""
    results: list[dict] = []
    in_table = False
    resolver_type: str | None = None
    key: str | None = None

    for line in content.splitlines():
        if line.startswith(f"{table_name} Resolver Table:"):
            in_table = True
            continue
        if not in_table:
            continue

        if line and not line.startswith(" "):
            break

        section_match = re.match(r"^ {2}([^ ].*):\s*$", line)
        if section_match:
            resolver_type = RESOLVER_TYPES.get(section_match.group(1))
            key = None
            continue
        if resolver_type is None:
            continue

        key_match = re.match(r"^ {6,}([^ ].*):\s*$", line)
        if key_match:
            key = key_match.group(1)
            continue
        if key is None:
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue
        component = entry_match.group("component")
        results.append(
            {
                "resolver_type": resolver_type,
                "key": key,
                "package_name": component.split("/", 1)[0],
                "component": component,
                "filter_count": int(entry_match.group("filters") or 1),
            }
        )

    return results
