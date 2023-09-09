# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact


class DumpsysAccessibilityArtifact(AndroidArtifact):
    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result["package_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def parse(self, content: str) -> None:
        """
        Parse the Dumpsys Accessibility section/
        Adds results to self.results (List[Dict[str, str]])

        :param content: content of the accessibility section (string)
        """
        in_services = False
        for line in content.splitlines():
            if line.strip().startswith("installed services:"):
                in_services = True
                continue

            if not in_services:
                continue

            if line.strip() == "}":
                break

            service = line.split(":")[1].strip()

            self.results.append(
                {
                    "package_name": service.split("/")[0],
                    "service": service,
                }
            )
