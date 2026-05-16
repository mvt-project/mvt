# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re

from .artifact import AndroidArtifact


class DumpsysAccessibilityArtifact(AndroidArtifact):
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

    def parse(self, content: str) -> None:
        """
        Parse the Dumpsys Accessibility section.
        Adds results to self.results (List[Dict[str, Any]])

        :param content: content of the accessibility section (string)
        """

        # Parse installed services
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
                    "enabled": False,
                }
            )

        # Parse enabled services from both old and new formats.
        #
        # Old format (multi-line block):
        #   enabled services: {
        #     0 : com.example/.MyService
        #   }
        #
        # New format (single line, AOSP >= 14):
        #   Enabled services:{{com.example/com.example.MyService}, {com.other/com.other.Svc}}
        enabled_services = set()

        in_enabled = False
        for line in content.splitlines():
            stripped = line.strip()

            if in_enabled:
                if stripped == "}":
                    in_enabled = False
                    continue
                service = line.split(":")[1].strip()
                enabled_services.add(service)
                continue

            if re.match(r"enabled services:\s*\{\s*$", stripped, re.IGNORECASE):
                # Old multi-line format: "enabled services: {"
                in_enabled = True
                continue

            if re.match(r"enabled services:\s*\{", stripped, re.IGNORECASE):
                # New single-line format: "Enabled services:{{pkg/svc}, {pkg2/svc2}}"
                matches = re.finditer(r"\{([^{}]+)\}", stripped)
                for match in matches:
                    enabled_services.add(match.group(1).strip())

        # Mark installed services that are enabled.
        # Installed service names may include trailing annotations like
        # "(A11yTool)" that are absent from the enabled services list,
        # so strip annotations before comparing.
        def _strip_annotation(s: str) -> str:
            return re.sub(r"\s+\(.*?\)\s*$", "", s)

        installed_stripped = {
            _strip_annotation(r["service"]): r for r in self.results
        }
        for enabled in enabled_services:
            if enabled in installed_stripped:
                installed_stripped[enabled]["enabled"] = True

        # Add enabled services not found in the installed list
        for service in enabled_services:
            if service not in installed_stripped:
                package_name, _, _ = service.partition("/")
                self.results.append(
                    {
                        "package_name": package_name,
                        "service": service,
                        "enabled": True,
                    }
                )
