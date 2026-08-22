# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from typing import Any

from .artifact import AndroidArtifact


class DumpsysAccessibilityArtifact(AndroidArtifact):
    def check_indicators(self) -> None:
        for result in self.results:
            if self.indicators:
                ioc_match = self.indicators.check_app_id(result["package_name"])
                if ioc_match:
                    self.alertstore.critical(
                        ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                    )
                    continue

            self.alertstore.medium(
                f'Found accessibility service: "{result["component"]}"',
                "",
                result,
            )

    def parse(self, content: str) -> None:
        """
        Parse the Dumpsys Accessibility section/
        Adds results to self.results (List[Dict[str, str]])

        :param content: content of the accessibility section (string)
        """

        self.results: list[dict[str, Any]] = []
        services: dict[tuple[int | None, str], dict] = {}
        user_id: int | None = None
        state: str | None = None

        for line in content.splitlines():
            user_match = re.search(r"attributes:\{id=(\d+)", line)
            if user_match:
                user_id = int(user_match.group(1))

            stripped = line.strip()
            state_match = re.match(
                r"(?i)(installed|enabled|binding|bound|crashed) services\s*:\s*\{(.*)",
                stripped,
            )
            if state_match:
                state = state_match.group(1).lower()
                inline = state_match.group(2)
                for component in re.findall(
                    r"\{?([\w.$-]+/[\w.$-]+)(?:\s+\(A11yTool\))?\}?", inline
                ):
                    service = services.setdefault(
                        (user_id, component), self._new_service(component, user_id)
                    )
                    service[self._state_field(state)] = True
                    service["accessibility_tool"] = "(A11yTool)" in inline
                continue

            if not state:
                continue
            if stripped == "}" or stripped.startswith("AccessibilityInputFilter"):
                state = None
                continue
            component_match = re.search(
                r"(?:\d+\s*:\s*)?([\w.$-]+/[\w.$-]+)(?:\s+\(A11yTool\))?",
                stripped,
            )
            if component_match:
                component = component_match.group(1)
                service = services.setdefault(
                    (user_id, component), self._new_service(component, user_id)
                )
                service[self._state_field(state)] = True
                service["accessibility_tool"] = "(A11yTool)" in stripped

        self.results.extend(services.values())

    @staticmethod
    def _state_field(state: str) -> str:
        return {"binding": "binding", "bound": "bound"}.get(state, state)

    @staticmethod
    def _new_service(component: str, user_id: int | None) -> dict:
        package_name, service_name = component.split("/", 1)
        return {
            "user_id": user_id,
            "component": component,
            "package_name": package_name,
            "service_name": service_name,
            "installed": False,
            "enabled": False,
            "binding": False,
            "bound": False,
            "crashed": False,
            "accessibility_tool": False,
        }
