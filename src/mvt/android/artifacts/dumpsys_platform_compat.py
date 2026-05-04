# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

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
            if not line.startswith("ChangeId(168419799; name=DOWNSCALED;"):
                continue

            if line.strip() == "":
                break

            # Look for rawOverrides field
            if "rawOverrides={" in line:
                # Extract the content inside the braces for rawOverrides
                overrides_field = line.split("rawOverrides={", 1)[1].split("};", 1)[0]

                for entry in overrides_field.split(", "):
                    # Extract app name
                    uninstall_app = entry.split("=")[0].strip()

                    self.results.append({"package_name": uninstall_app})
