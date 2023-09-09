# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact


class DumpsysPackageActivitiesArtifact(AndroidArtifact):
    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for activity in self.results:
            ioc = self.indicators.check_app_id(activity["package_name"])
            if ioc:
                activity["matched_indicator"] = ioc
                self.detected.append(activity)
                continue

    def parse(self, content: str):
        """
        Parse the Dumpsys Package section for activities
        Adds results to self.results

        :param content: content of the package section (string)
        """
        self.results = []

        in_activity_resolver_table = False
        in_non_data_actions = False
        intent = None
        for line in content.splitlines():
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
            if (
                line.startswith(" " * 6)
                and not line.startswith(" " * 8)
                and ":" in line
            ):
                intent = line.strip().replace(":", "")
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

            self.results.append(
                {
                    "intent": intent,
                    "package_name": package_name,
                    "activity": activity,
                }
            )
