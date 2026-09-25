# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from typing import Any

from .artifact import AndroidArtifact


class DumpsysAccessibilityArtifact(AndroidArtifact):
    # One list for both record shapes — a service record and a count-only
    # record must stay the same shape.
    _FIELDS = (
        "user_id",
        "component",
        "package_name",
        "service_name",
        "installed",
        "enabled",
        "binding",
        "bound",
        "crashed",
        "accessibility_tool",
        "installed_service_count",
        "unnamed_service_count",
    )

    def check_indicators(self) -> None:
        for result in self.results:
            # A stated count the dump does not back with component names is a
            # coverage statement, not a service: low, but not silent.
            if not result.get("component"):
                stated = result["installed_service_count"]
                unnamed = result["unnamed_service_count"]
                if unnamed == stated:
                    detail = "does not list their component names"
                else:
                    detail = (
                        f"lists the component names of only {stated - unnamed} "
                        f"of them ({unnamed} unnamed)"
                    )
                self.alertstore.low(
                    f"The accessibility dump states {stated} installed "
                    f"service(s) for user {result['user_id']} but {detail}",
                    "",
                    result,
                )
                continue

            if self.indicators:
                ioc_match = self.indicators.check_app_id(result["package_name"])
                if ioc_match:
                    self.alertstore.critical(
                        ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                    )
                    continue

            # Installed is not enabled. A service can sit installed for years
            # without ever being switched on, and that is the difference this
            # channel is read for — an alert that says only "found" makes every
            # device look equally exposed. A service the dump says is switched
            # OFF is reported LOW, so it still reaches the analyst without
            # competing with one that is actually running; a dump that does not
            # state the enabled state stays MEDIUM, because "not stated" is not
            # "not enabled".
            message = (
                f'Found accessibility service: "{result["component"]}" '
                f"({self._describe_state(result)})"
            )
            if result.get("enabled") is False and not result.get("bound"):
                self.alertstore.low(message, "", result)
            else:
                self.alertstore.medium(message, "", result)

    def parse(self, content: str) -> None:
        """
        Parse the Dumpsys Accessibility section/
        Adds results to self.results (List[Dict[str, str]])

        :param content: content of the accessibility section (string)
        """

        self.results: list[dict[str, Any]] = []
        services: dict[tuple[int | None, str], dict] = {}
        # Which state sections the dump printed, per user: one user's printed
        # `enabled services` says nothing about another user's.
        seen_states: dict[int | None, set[str]] = {}
        # `installedServiceCount=N` from the user's `attributes:{…}` line is on
        # most builds the only statement about installed services in the dump:
        # few print the `installed services: {…}` block.
        installed_counts: dict[int | None, int] = {}
        user_id: int | None = None
        state: str | None = None

        for line in content.splitlines():
            user_match = re.search(r"attributes:\{id=(\d+)", line)
            if user_match:
                user_id = int(user_match.group(1))

            count_match = re.search(r"installedServiceCount=(\d+)", line)
            if count_match:
                installed_counts[user_id] = int(count_match.group(1))

            stripped = line.strip()
            state_match = re.match(
                r"(?i)(installed|enabled|binding|bound|crashed) services\s*:\s*\{(.*)",
                stripped,
            )
            if state_match:
                state = state_match.group(1).lower()
                seen_states.setdefault(user_id, set()).add(self._state_field(state))
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

        # A section that was never printed is NOT the same as one printed
        # empty: the first says nothing, the second says nothing is enabled.
        # Defaulting every flag to False would turn "not stated" into "not
        # enabled". Flags for sections this dump never printed stay None.
        named: dict[int | None, int] = {}
        for (service_user, _component), service in services.items():
            printed = seen_states.get(service_user, set())
            for state in ("installed", "enabled", "binding", "bound", "crashed"):
                if self._state_field(state) not in printed:
                    service[self._state_field(state)] = None
            service["installed_service_count"] = installed_counts.get(service_user)
            named[service_user] = named.get(service_user, 0) + 1

        self.results.extend(services.values())

        # A stated count the named services do not add up to would leave no
        # trace of the rest: the module would log "a total of 0" about a dump
        # that said five, or "a total of 1" about one that said two.
        for count_user, count in installed_counts.items():
            unnamed = count - named.get(count_user, 0)
            if unnamed > 0:
                self.results.append(self._new_unlisted(count_user, count, unnamed))

    @staticmethod
    def _describe_state(result: dict) -> str:
        if result.get("bound"):
            return "enabled and bound"
        if result.get("enabled"):
            return "enabled"
        if result.get("enabled") is None:
            return "installed, enabled state not stated"
        return "installed, not enabled"

    @staticmethod
    def _state_field(state: str) -> str:
        return {"binding": "binding", "bound": "bound"}.get(state, state)

    @staticmethod
    def _new_unlisted(user_id: int | None, count: int, unnamed: int) -> dict:
        """The dump's own count for a user, and how many of those services it
        did not name.

        Every other field stays unknown: the dump named no service to carry it.
        """
        record: dict[str, Any] = dict.fromkeys(DumpsysAccessibilityArtifact._FIELDS)
        record["user_id"] = user_id
        record["installed_service_count"] = count
        record["unnamed_service_count"] = unnamed
        return record

    @staticmethod
    def _new_service(component: str, user_id: int | None) -> dict:
        record: dict[str, Any] = dict.fromkeys(
            DumpsysAccessibilityArtifact._FIELDS, False
        )
        record["user_id"] = user_id
        record["component"] = component
        record["package_name"], record["service_name"] = component.split("/", 1)
        # Filled in after parsing: the count is per user.
        record["installed_service_count"] = None
        record["unnamed_service_count"] = None
        return record
