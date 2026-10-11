# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re

from .artifact import AndroidArtifact


class DumpsysPlatformCompatArtifact(AndroidArtifact):
    """
    Parser for uninstalled apps listed in platform_compat section.
    """

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc_match = self.indicators.check_app_id(result["package_name"])
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )
                continue

    def parse(self, data: str) -> None:
        for line in data.splitlines():
            match = re.match(r"ChangeId\((\d+);\s*(.*)\)$", line.strip())
            if not match or "rawOverrides={" not in line:
                continue
            body = match.group(2)
            name_match = re.search(r"(?:^|;\s*)name=([^;]+)", body)
            state = (
                "enabled"
                if re.search(r"(?:^|;\s*)enabled(?:;|$)", body)
                else "disabled"
            )
            overridable = bool(re.search(r"(?:^|;\s*)overridable(?:;|$)", body))
            overrides_field = body.split("rawOverrides={", 1)[1].split("}", 1)[0]
            for entry in overrides_field.split(","):
                package_name, separator, raw_value = entry.strip().partition("=")
                if not separator:
                    continue
                value: bool | int | str
                if raw_value in ("true", "false"):
                    value = raw_value == "true"
                else:
                    try:
                        value = int(raw_value)
                    except ValueError:
                        value = raw_value
                self.results.append(
                    {
                        "change_id": int(match.group(1)),
                        "change_name": name_match.group(1) if name_match else None,
                        "change_state": state,
                        "overridable": overridable,
                        "package_name": package_name,
                        "override_value": value,
                    }
                )
